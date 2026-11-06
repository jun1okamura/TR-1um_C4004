#!/usr/bin/env python3
"""
insert_high_fo_buffers.py

1. Row-aware buffer tree insertion for clk_buf (FO=41) and rst_n_buf (FO=38):
   - Inserts one BUF_X2 per active placement row (9 rows: ROW_1, 4, 7, 10, 13, 16, 19, 22, 25)
     using the actual placed row locations from placed_widech.def.
   - Each row buffer drives ONLY the sinks in that row (FO = 2..10, max <= 10).
   - The root net (clk_buf / rst_n_buf) drives only the 9 row buffers (FO = 9).
2. 2-way spatial split with BUF_X2 for all unbuffered nets with FO >= 8:
   - Splits sinks sorted by (row_y, x) into 2 local branches (FO = 4..5 each),
     each driven by a BUF_X2 cell.
3. Outputs both:
   - /Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/syn/c4004_core_buffered.v (with VDD/GND pins)
   - /Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/c4004_core_buffered_or.v (for OpenROAD)
"""

import json
import re
from collections import defaultdict

DEF_PATH = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/routed_widech_strict.def"
IN_OR_V = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/c4004_core_or.v"
OUT_OR_V = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/c4004_core_buffered_or.v"
IN_SYN_V = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/syn/c4004_core_bufth.v"
OUT_SYN_V = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/syn/c4004_core_buffered.v"
OUT_POS_TCL = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/openroad/buffered_target_pos.tcl"

with open(DEF_PATH) as f:
    def_text = f.read()

comp_sec = def_text.split("COMPONENTS ")[1].split("END COMPONENTS")[0]
inst_pos = {}
for m in re.finditer(r"-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)", comp_sec):
    inst_pos[m.group(1)] = (m.group(2), int(m.group(3)) / 1000.0, int(m.group(4)) / 1000.0)

with open(IN_OR_V) as f:
    v_or = f.read()

out_pins = {"Y", "Q", "QN", "QB"}
fanout = defaultdict(list)
drivers = {}

for m in re.finditer(r"(\w+)\s+(\w+)\s*\((.*?)\);", v_or, re.S):
    cell, inst, body = m.group(1), m.group(2), m.group(3)
    if cell == "SRAM128":
        for i in range(4):
            drivers[f"sram_do[{i}]"] = ("SRAM128", inst, f"DO[{i}]")
        continue
    for pm in re.finditer(r"\.(\w+)\(\s*([^)]+?)\s*\)", body):
        pin, net = pm.group(1), pm.group(2)
        if pin in out_pins:
            drivers[net] = (cell, inst, pin)
        else:
            c, x, y = inst_pos.get(inst, (cell, 0.0, 0.0))
            row_idx = int(round(y / 59.4))
            fanout[net].append((row_idx, y, x, inst, cell, pin))

# Build redirection plan: {(inst, pin): new_net}
redirects = {}
new_bufs = []  # [(buf_inst_name, in_net, out_net, target_row_idx, target_x)]
new_wires = []

# 1. Row-aware buffers for clk_buf and rst_n_buf
for root_net in ["clk_buf", "rst_n_buf"]:
    by_row = defaultdict(list)
    for row_idx, y, x, inst, cell, pin in fanout[root_net]:
        # Keep _1042_ (NOR2 for sram_ce = ~clk & rst_n & sram_ce_en) on the balanced row clock tree too!
        by_row[row_idx].append((x, inst, cell, pin))
    for r in sorted(by_row):
        sinks = sorted(by_row[r])
        bnet = f"{root_net}_r{r}"
        binst = f"u_buf_{root_net}_r{r}"
        avg_x = sum(item[0] for item in sinks) / len(sinks)
        new_wires.append(bnet)
        new_bufs.append((binst, root_net, bnet, r, avg_x))
        for x, inst, cell, pin in sinks:
            redirects[(inst, pin)] = bnet
        print(f"[Row Buffer] {binst}: {root_net} -> {bnet} (row {r}, FO={len(sinks)}, avg_x={avg_x:.1f})")

# 2. 2-way spatial split for all unbuffered nets with FO >= 8
for net, loads in sorted(fanout.items(), key=lambda item: len(item[1]), reverse=True):
    if net in ("clk_buf", "rst_n_buf"):
        continue
    if len(loads) >= 8:
        drv = drivers.get(net, ("PORT", net, "IN"))
        if drv[0] not in ("BUF_X2", "BUFTH"):
            sorted_loads = sorted(loads)  # sorted by (row_idx, y, x)
            mid = len(sorted_loads) // 2
            groups = [sorted_loads[:mid], sorted_loads[mid:]]
            clean_net = re.sub(r"[^a-zA-Z0-9_]", "_", net).strip("_")
            if clean_net[0].isdigit():
                clean_net = "n_" + clean_net
            for gi, grp in enumerate(groups):
                bnet = f"{clean_net}_bf{gi}"
                binst = f"u_buf_{clean_net}_{gi}"
                med_row = grp[len(grp) // 2][0]
                avg_x = sum(item[2] for item in grp) / len(grp)
                new_wires.append(bnet)
                new_bufs.append((binst, net, bnet, med_row, avg_x))
                for row_idx, y, x, inst, cell, pin in grp:
                    redirects[(inst, pin)] = bnet
                print(f"[High-FO Buffer] {binst}: {net} ({drv[0]}) -> {bnet} (row {med_row}, FO={len(grp)}, avg_x={avg_x:.1f})")

def apply_modifications(src_text, include_power=False):
    # Apply pin redirections
    for (inst, pin), new_net in redirects.items():
        block_re = re.compile(r"(\b" + re.escape(inst) + r"\s*\(.*?\)\s*;)", re.S)
        bm = block_re.search(src_text)
        assert bm, f"Instance {inst} not found!"
        block = bm.group(1)
        pin_re = re.compile(r"(\." + re.escape(pin) + r"\s*\(\s*)([^()]*?)(\s*\))")
        new_block, n = pin_re.subn(lambda m2: m2.group(1) + new_net + m2.group(3), block, count=1)
        assert n == 1, f"Pin {inst}.{pin} not found in {block}"
        src_text = src_text[:bm.start()] + new_block + src_text[bm.end():]

    # Insert wire declarations before first cell instance
    wire_decl = "\n".join(f"  wire {w};" for w in new_wires) + "\n"
    first_inst = re.search(r"\n  [A-Z][A-Z0-9_]*\s+\S+\s*\(", src_text)
    assert first_inst
    src_text = src_text[:first_inst.start()] + "\n" + wire_decl + src_text[first_inst.start():]

    # Insert buffer instances before endmodule
    buf_lines = ["  // --- High-FO Buffer Trees (BUF_X2) ---"]
    for binst, in_net, out_net, r, avg_x in new_bufs:
        if include_power:
            buf_lines.append(f"  BUF_X2 {binst} (\n    .A({in_net}),\n    .GND(GND),\n    .VDD(VDD),\n    .Y({out_net})\n  );")
        else:
            buf_lines.append(f"  BUF_X2 {binst} (\n    .A({in_net}),\n    .Y({out_net})\n  );")
    end_idx = src_text.rindex("endmodule")
    src_text = src_text[:end_idx] + "\n".join(buf_lines) + "\nendmodule\n"
    return src_text

out_or_text = apply_modifications(v_or, include_power=False)
with open(OUT_OR_V, "w") as f:
    f.write(out_or_text)

with open(IN_SYN_V) as f:
    v_syn = f.read()
out_syn_text = apply_modifications(v_syn, include_power=True)
with open(OUT_SYN_V, "w") as f:
    f.write(out_syn_text)

# Write Tcl dict of {inst: {row_idx x_dbu}} for all original + new instances
tcl_lines = ["set fixed_row_x [dict create]"]
for inst, (cell, x_um, y_um) in inst_pos.items():
    if inst == "u_sram":
        continue
    r = int(round(y_um / 59.4))
    x_dbu = int(round(x_um * 1000))
    tcl_lines.append(f"dict set fixed_row_x {{{inst}}} [list {r} {x_dbu}]")
for binst, in_net, out_net, r, avg_x in new_bufs:
    x_dbu = int(round(avg_x * 1000))
    tcl_lines.append(f"dict set fixed_row_x {{{binst}}} [list {r} {x_dbu}]")
with open(OUT_POS_TCL, "w") as f:
    f.write("\n".join(tcl_lines) + "\n")

print(f"\nSuccessfully generated:")
print(f"  - {OUT_OR_V}")
print(f"  - {OUT_SYN_V}")
print(f"  - {OUT_POS_TCL}")
print(f"Total new BUF_X2 buffers inserted: {len(new_bufs)}")
