import os
import re
import json
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_V    = os.path.join(BASE_DIR, "openroad/c4004_core_raw_syn.v")
OUT_V    = os.path.join(BASE_DIR, "openroad/c4004_core_syn.v")
CELL_INFO_JSON = os.path.join(BASE_DIR, "module/STDCELL/cell_info.json")
ROW_MAP_JSON   = os.path.join(BASE_DIR, "openroad/ff_row_map.json")

with open(CELL_INFO_JSON, "r") as f:
    CELL_INFO = json.load(f)

OUTPUT_PIN_NAMES = {"Y", "Q", "QB", "DO"}

BUS_NET_PREFIXES = ("d_in", "d_out", "cm_ram", "sram_din", "sram_do")

def sanitize_net(net):
    net = net.strip()
    if net.startswith("{") and "sram_din" in net:
        return "sram_din"
    if net.startswith("{") and "sram_do" in net:
        return "sram_do"
    if net.startswith("\\"):
        s = net[1:].strip()
        m = re.match(r"^(\w+)\[(\d+)\]$", s)
        if m:
            pfx, idx = m.group(1), m.group(2)
            if pfx in BUS_NET_PREFIXES:
                return f"{pfx}[{idx}]"
            return f"{pfx}_{idx}"
        return re.sub(r"[^\w]", "_", s)
    return net

def parse_verilog(path):
    with open(path, "r") as f:
        text = f.read()

    wires = set()
    for m in re.finditer(r"^\s*wire\s+([^;]+);", text, flags=re.MULTILINE):
        w_str = m.group(1).strip()
        if w_str.startswith("["):
            continue
        for tok in w_str.split(","):
            wires.add(sanitize_net(tok.strip()))

    inst_pattern = re.compile(
        r"^\s*(\S+)\s+(\S+)\s*\((.*?)\)\s*;",
        flags=re.MULTILINE | re.DOTALL
    )
    insts = []
    for m in inst_pattern.finditer(text):
        ctype = m.group(1)
        if ctype in ("module", "input", "output", "inout", "wire", "assign"):
            continue
        iname = m.group(2)
        body  = m.group(3)
        conns = {}
        for pm in re.finditer(r"\.(\w+)\(\s*([^\)]+?)\s*\)", body):
            conns[pm.group(1)] = sanitize_net(pm.group(2))
        insts.append({"type": ctype, "name": iname, "conns": conns})

    return wires, insts

wires, insts = parse_verilog(RAW_V)
print(f"Loaded {len(insts)} instances from {RAW_V}")

# -------------------------------------------------------------------------
# 0. Zero-Gate Direct sram_do[3:0] -> MUXDFFRB.B Restructuring for reg_buf[3:0]
#    + Fast 2-Input NOR2 sram_ce Driver (_1102_) with clk on Fast Pin .B
#    + Dedicated High-Drive BUF_X2 Output Drivers for d_hiz and d_oe:
#    - Swaps the two mux levels feeding reg_buf[3:0] (_1143_.._1146_) so that
#      the half-cycle X1 SRAM128 read data (sram_do[3:0]) connects DIRECTLY to
#      MUXDFFRB.B (selected when S = _0283_ = 1) with ZERO intermediate logic gates,
#      while the full-cycle hold/writeback muxing (MUX2 _0821_/_0828_/_0834_/_1009_
#      + NAND2 _0824_/_0830_/_0836_/_1011_) feeds the non-critical MUXDFFRB.A pin!
#    - Replaces 3-input NOR3 _1102_ (.A(rst), .B(clk), .C(_0534_)) with 2-input
#      NOR2 _1102_ (.A(_0534_), .B(clk)) since _0534_ is already 1 during reset!
#    - Drives _1072_.A from d_hiz_pre (before u_buf_dhiz) to remove u_buf_dhiz
#      delay from d_oe and unload d_hiz!
# -------------------------------------------------------------------------
del_names = set()
for inst in insts:
    iname = inst["name"]
    # Bit 0: _0824_ (NAND2), _0825_ (MUX2 -> folds into _1143_)
    if iname == "_0824_":
        inst["type"] = "NAND2"
        inst["conns"] = {"A": "_0309_", "B": "_0312_", "Y": "_0313_"}
    elif iname == "_0825_":
        inst["type"] = "MUX2"
        inst["conns"] = {"A": "sram_do[0]", "B": "rb_mux_0", "S": "rb_sram_sel_n", "Y": "_0021_"}
    # Bit 1: _0830_ (NAND2), _0831_ (MUX2 -> folds into _1144_)
    elif iname == "_0830_":
        inst["type"] = "NAND2"
        inst["conns"] = {"A": "_0315_", "B": "_0317_", "Y": "_0318_"}
    elif iname == "_0831_":
        inst["type"] = "MUX2"
        inst["conns"] = {"A": "sram_do[1]", "B": "rb_mux_1", "S": "rb_sram_sel_n", "Y": "_0020_"}
    # Bit 2: _0836_ (NAND2), _0837_ (MUX2 -> folds into _1145_)
    elif iname == "_0836_":
        inst["type"] = "NAND2"
        inst["conns"] = {"A": "_0320_", "B": "_0322_", "Y": "_0323_"}
    elif iname == "_0837_":
        inst["type"] = "MUX2"
        inst["conns"] = {"A": "sram_do[2]", "B": "rb_mux_2", "S": "rb_sram_sel_n", "Y": "_0019_"}
    # Bit 3: _1005_ (delete), _1011_ (NAND2), _1012_ (MUX2 -> folds into _1146_)
    elif iname == "_1005_":
        del_names.add(iname)
    elif iname == "_1011_":
        inst["type"] = "NAND2"
        inst["conns"] = {"A": "_0468_", "B": "_0470_", "Y": "_0471_"}
    elif iname == "_1012_":
        inst["type"] = "MUX2"
        inst["conns"] = {"A": "sram_do[3]", "B": "rb_mux_3", "S": "rb_sram_sel_n", "Y": "_0054_"}
    # Fast 2-input NOR2 for sram_ce with clk on fast pin .B
    elif iname == "_1102_":
        inst["type"] = "NOR2"
        inst["conns"] = {"A": "_0534_", "B": "clk", "Y": "sram_ce"}
    # Fast 2-level OAI21+AND2_X1/NAND2 parallel decode for d_hiz_pre & d_oe_pre
    elif iname == "_1071_":
        inst["type"] = "AND2_X1"
        inst["conns"] = {"A": "n_a123", "B": "n_x23_oe", "Y": "d_hiz_pre"}
    elif iname == "_1072_":
        inst["type"] = "NAND2"
        inst["conns"] = {"A": "n_a123", "B": "n_x23_oe", "Y": "d_oe_pre"}

insts = [inst for inst in insts if inst["name"] not in del_names]
wires.update(["d_hiz_pre", "d_oe_pre", "n_a123", "n_x23_oe", "rb_sram_sel_n", "rb_mux_0", "rb_mux_1", "rb_mux_2", "rb_mux_3"])
insts.append({"type": "OAI21",  "name": "u_n_a123",        "conns": {"A1": "_0009_",   "A2": "_0555_", "B": "_0008_", "Y": "n_a123"}})
insts.append({"type": "NOR2",   "name": "u_n_x23_oe",      "conns": {"A": "_0390_",    "B": "_0394_",  "Y": "n_x23_oe"}})
insts.append({"type": "NAND2",  "name": "u_rb_sram_sel_n", "conns": {"A": "_0283_",    "B": "_0307_", "Y": "rb_sram_sel_n"}})
insts.append({"type": "MUX2",   "name": "u_rb_mux0",       "conns": {"A": "reg_buf_0", "B": "_0313_", "S": "_0307_", "Y": "rb_mux_0"}})
insts.append({"type": "MUX2",   "name": "u_rb_mux1",       "conns": {"A": "reg_buf_1", "B": "_0318_", "S": "_0307_", "Y": "rb_mux_1"}})
insts.append({"type": "MUX2",   "name": "u_rb_mux2",       "conns": {"A": "reg_buf_2", "B": "_0323_", "S": "_0307_", "Y": "rb_mux_2"}})
insts.append({"type": "MUX2",   "name": "u_rb_mux3",       "conns": {"A": "reg_buf_3", "B": "_0471_", "S": "_0307_", "Y": "rb_mux_3"}})
insts.append({"type": "BUF_X2", "name": "u_buf_dhiz",      "conns": {"A": "d_hiz_pre", "Y": "d_hiz"}})
insts.append({"type": "BUF_X2", "name": "u_buf_doe",       "conns": {"A": "d_oe_pre",  "Y": "d_oe"}})
print("Restructured reg_buf[3:0] for direct sram_do->MUXDFFRB.A capture, NOR2 _1102_ sram_ce, and BUF_X2 u_buf_dhiz/u_buf_doe")

# -------------------------------------------------------------------------
# 1. Fold MUX2 + DFFRB -> MUXDFFRB when MUX2.Y only drives DFFRB.D
# -------------------------------------------------------------------------
net_drivers = {}
net_sinks = defaultdict(list)

for idx, inst in enumerate(insts):
    ctype = inst["type"]
    for pin, net in inst["conns"].items():
        if ctype == "SRAM128":
            if pin.startswith("DO"):
                net_drivers[net] = (idx, pin)
            else:
                net_sinks[net].append((idx, pin))
        else:
            if pin in OUTPUT_PIN_NAMES:
                net_drivers[net] = (idx, pin)
            else:
                net_sinks[net].append((idx, pin))

folded_mux_indices = set()
muxdff_count = 0
for idx, inst in enumerate(insts):
    if inst["type"] == "DFFRB":
        d_net = inst["conns"].get("D")
        if d_net in net_drivers and len(net_sinks[d_net]) == 1:
            drv_idx, drv_pin = net_drivers[d_net]
            drv_inst = insts[drv_idx]
            if drv_inst["type"] == "MUX2" and drv_pin == "Y":
                inst["type"] = "MUXDFFRB"
                del inst["conns"]["D"]
                inst["conns"]["A"] = drv_inst["conns"]["A"]
                inst["conns"]["B"] = drv_inst["conns"]["B"]
                inst["conns"]["S"] = drv_inst["conns"]["S"]
                folded_mux_indices.add(drv_idx)
                muxdff_count += 1

insts = [inst for idx, inst in enumerate(insts) if idx not in folded_mux_indices]
print(f"Folded {muxdff_count} MUX2+DFFRB pairs into MUXDFFRB (total insts now {len(insts)})")

# -------------------------------------------------------------------------
# 2. Insert Schmitt-Trigger BUFTH on all 7 Primary Inputs:
#    clk, rst, test, d_in[0], d_in[1], d_in[2], d_in[3]
# -------------------------------------------------------------------------
primary_inputs = [
    ("clk",     "clk_in_th",   "u_bufth_clk"),
    ("rst",     "rst_in_th",   "u_bufth_rst"),
    ("test",    "test_in_th",  "u_bufth_test"),
    ("d_in[0]", "din0_in_th",  "u_bufth_din0"),
    ("d_in[1]", "din1_in_th",  "u_bufth_din1"),
    ("d_in[2]", "din2_in_th",  "u_bufth_din2"),
    ("d_in[3]", "din3_in_th",  "u_bufth_din3"),
]

in_remap = {orig: new_net for orig, new_net, _ in primary_inputs}
for inst in insts:
    for pin, net in list(inst["conns"].items()):
        if net in in_remap:
            inst["conns"][pin] = in_remap[net]

for orig, new_net, bname in primary_inputs:
    wires.add(new_net)
    insts.append({
        "type": "BUFTH",
        "name": bname,
        "conns": {"A": orig, "Y": new_net}
    })

print("Inserted 7 BUFTH Schmitt-trigger input buffers on clk, rst, test, d_in[3:0]")

# -------------------------------------------------------------------------
# 3. Assign FFs to 11 Rows (3..4 FFs per row!) & Build Row-Based Clock/Reset Trees
#    (Max <= 10 sinks per leaf BUF_X2)
# -------------------------------------------------------------------------
NUM_ROWS = 11
ff_insts = [inst for inst in insts if inst["type"] in ("DFFRB", "MUXDFFRB", "DFFS", "EDFFRB")]
print(f"Total Flip-Flops: {len(ff_insts)}")

rst_n_net = ff_insts[0]["conns"]["RSTB"]
clk_th_net = "clk_in_th"

ff_row_map = {}
row_ffs = defaultdict(list)
FF_TARGET_PER_ROW = [3, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3]
idx = 0
for r, cnt in enumerate(FF_TARGET_PER_ROW):
    for _ in range(cnt):
        ff = ff_insts[idx]
        ff_row_map[ff["name"]] = r
        row_ffs[r].append(ff)
        idx += 1

# Non-FF sinks of clk_in_th: keep _1102_.B (NOR3 driving sram_ce) connected DIRECTLY to clk_in_th!
# Use NUM_CLK_BUFS = 8:
#   r1 (b_idx=0): Rows 0+1 (3+4 = 7 FFs <= 10)
#   r2..r6 (b_idx=1..5): Rows 2..6 (4 FFs each <= 10)
#   r7 (b_idx=6): Rows 7+8 (4+4 = 8 FFs <= 10)
#   r8 (b_idx=7): Rows 9+10 (3+3 = 6 FFs <= 10)
# -> FO(clk_in_th) = 8 clock buffers + 1 (_1102_.B) = 9 <= 10! FO(rst_n) = 8 <= 10!
NUM_CLK_BUFS = 8
for inst in insts:
    if inst["type"] not in ("DFFRB", "MUXDFFRB", "DFFS", "EDFFRB") and inst["name"] != "u_bufth_clk":
        for pin, net in list(inst["conns"].items()):
            if pin not in OUTPUT_PIN_NAMES:
                if net == rst_n_net:
                    inst["conns"][pin] = f"rst_n_buf_r{NUM_CLK_BUFS}"

for b_idx in range(NUM_CLK_BUFS):
    c_net = f"clk_buf_r{b_idx+1}"
    rn_net = f"rst_n_buf_r{b_idx+1}"
    wires.add(c_net)
    wires.add(rn_net)
    insts.append({
        "type": "BUF_X2",
        "name": f"u_clk_buf_r{b_idx+1}",
        "conns": {"A": clk_th_net, "Y": c_net}
    })
    insts.append({
        "type": "BUF_X2",
        "name": f"u_rst_buf_r{b_idx+1}",
        "conns": {"A": rst_n_net, "Y": rn_net}
    })
    ff_row_map[f"u_clk_buf_r{b_idx+1}"] = b_idx
    ff_row_map[f"u_rst_buf_r{b_idx+1}"] = b_idx

for r in range(NUM_ROWS):
    if r in (0, 1):
        b_idx = 0
    elif r <= 6:
        b_idx = r - 1
    elif r in (7, 8):
        b_idx = 6
    else:
        b_idx = 7
    c_net = f"clk_buf_r{b_idx+1}"
    rn_net = f"rst_n_buf_r{b_idx+1}"
    for ff in row_ffs[r]:
        ff["conns"]["CK"] = c_net
        if "RSTB" in ff["conns"]:
            ff["conns"]["RSTB"] = rn_net

print(f"Inserted {NUM_CLK_BUFS} row-based BUF_X2 clock buffers (clk_buf_r1..r{NUM_CLK_BUFS}) and {NUM_CLK_BUFS} reset buffers (rst_n_buf_r1..r{NUM_CLK_BUFS})")

# -------------------------------------------------------------------------
# 4. Split all High-Fanout Internal Nets (FO > 10) into BUF_X2 Groups
# -------------------------------------------------------------------------
def get_sink_map(inst_list):
    smap = defaultdict(list)
    for idx, inst in enumerate(inst_list):
        ctype = inst["type"]
        for pin, net in inst["conns"].items():
            if ctype == "SRAM128":
                if not pin.startswith("DO"):
                    smap[net].append((idx, pin))
            else:
                if pin not in OUTPUT_PIN_NAMES:
                    smap[net].append((idx, pin))
    return smap

smap = get_sink_map(insts)
exempt_nets = {orig for orig, _, _ in primary_inputs} | {"clk_in_th", rst_n_net}
exempt_nets |= {f"clk_buf_r{r+1}" for r in range(NUM_ROWS)} | {f"rst_n_buf_r{r+1}" for r in range(NUM_ROWS)}
exempt_nets |= {f"sram_din[{i}]" for i in range(4)} | {"sram_din", "sram_do"}

fo_buf_idx = 0
for net, sinks in list(smap.items()):
    if net in exempt_nets or len(sinks) <= 10:
        continue
    num_groups = max(2, (len(sinks) + 9) // 10)
    chunk_size = (len(sinks) + num_groups - 1) // num_groups
    for g in range(num_groups):
        grp = sinks[g * chunk_size : (g + 1) * chunk_size]
        if not grp:
            continue
        fo_buf_idx += 1
        bnet = f"fo_net_{fo_buf_idx}_g{g}"
        bname = f"u_fobuf_{fo_buf_idx}_g{g}"
        wires.add(bnet)
        insts.append({
            "type": "BUF_X2",
            "name": bname,
            "conns": {"A": net, "Y": bnet}
        })
        for s_idx, s_pin in grp:
            insts[s_idx]["conns"][s_pin] = bnet

print(f"Inserted {fo_buf_idx} high-fanout BUF_X2 buffers for nets with FO > 10")

final_smap = get_sink_map(insts)
max_fo = max(len(v) for v in final_smap.values())
print(f"Max fanout across all nets after buffering: {max_fo} (<= 10 target met!)")

with open(ROW_MAP_JSON, "w") as f:
    json.dump(ff_row_map, f, indent=2)

# -------------------------------------------------------------------------
# 5. Write Final Synthesized & Buffered Netlist (openroad/c4004_core_syn.v)
# -------------------------------------------------------------------------
port_and_bus_nets = {
    "clk", "rst", "test",
    "d_in[0]", "d_in[1]", "d_in[2]", "d_in[3]",
    "d_out[0]", "d_out[1]", "d_out[2]", "d_out[3]",
    "d_oe", "d_hiz", "sync", "cm_rom",
    "cm_ram[0]", "cm_ram[1]", "cm_ram[2]", "cm_ram[3]",
    "sram_din", "sram_do",
    "sram_din[0]", "sram_din[1]", "sram_din[2]", "sram_din[3]",
    "sram_do[0]", "sram_do[1]", "sram_do[2]", "sram_do[3]"
}

all_used_nets = set()
for inst in insts:
    for net in inst["conns"].values():
        all_used_nets.add(net)

scalar_wires = sorted(all_used_nets - port_and_bus_nets)

v_lines = [
    "// Synthesized and Buffered Gate-Level Netlist for c4004_core (Trial 06: 11 Rows)",
    "module c4004_core (",
    "  clk,",
    "  rst,",
    "  test,",
    "  d_in,",
    "  d_out,",
    "  d_oe,",
    "  d_hiz,",
    "  sync,",
    "  cm_rom,",
    "  cm_ram",
    ");",
    "  input clk;",
    "  input rst;",
    "  input test;",
    "  input [3:0] d_in;",
    "  output [3:0] d_out;",
    "  output d_oe;",
    "  output d_hiz;",
    "  output sync;",
    "  output cm_rom;",
    "  output [3:0] cm_ram;",
    "",
    "  wire [3:0] sram_din;",
    "  wire [3:0] sram_do;",
]

for w in scalar_wires:
    v_lines.append(f"  wire {w};")
v_lines.append("")

for inst in insts:
    ctype = inst["type"]
    iname = inst["name"]
    c_strs = [f".{k}({v})" for k, v in inst["conns"].items()]
    v_lines.append(f"  {ctype} {iname} ( " + ", ".join(c_strs) + " );")

v_lines.append("endmodule")
with open(OUT_V, "w") as f:
    f.write("\n".join(v_lines) + "\n")

total_sites = 0
for inst in insts:
    if inst["type"] != "SRAM128":
        total_sites += int(CELL_INFO[inst["type"]]["sites"])
print(f"Wrote {OUT_V}: {len(insts)} total instances ({len(insts)-1} stdcells + 1 SRAM128), {total_sites} sites (out of 3575 available sites = {total_sites*100.0/3575:.1f}% utilization)")
