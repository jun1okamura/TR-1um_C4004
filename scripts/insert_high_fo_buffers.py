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
        flags=re.MULTILINE | re.DOTALL,
    )
    insts = []
    for m in inst_pattern.finditer(text):
        ctype = m.group(1)
        if ctype in ("module", "input", "output", "inout", "wire", "assign"):
            continue
        iname = m.group(2)
        body = m.group(3)
        conns = {}
        for pm in re.finditer(r"\.(\w+)\(\s*([^\)]+?)\s*\)", body):
            conns[pm.group(1)] = sanitize_net(pm.group(2))
        insts.append({"type": ctype, "name": iname, "conns": conns})

    return wires, insts


wires, insts = parse_verilog(RAW_V)
print(f"Loaded {len(insts)} instances from {RAW_V}")

# -------------------------------------------------------------------------
# 0. Identify & Rename Dedicated Edge-Anchored Output FFs, Pure-DFFRB
#    SRAM128 Capture FFs (sram_lat[0..3]), Clone West d_hiz FF + BUF_X2,
#    and Replace Slow NOR3 sram_ce Gate with Fast INV_X2 + NAND2 + INV_X2
# -------------------------------------------------------------------------
ANCHORED_Q_MAP = {
    "d_out[0]":  "u_ff_dout0",
    "d_out[1]":  "u_ff_dout1",
    "d_out[2]":  "u_ff_dout2",
    "d_out[3]":  "u_ff_dout3",
    "d_oe":      "u_ff_doe",
    "sync":      "u_ff_sync",
    "cm_rom":    "u_ff_cmrom",
    "cm_ram[0]": "u_ff_cmram0",
    "cm_ram[1]": "u_ff_cmram1",
    "cm_ram[2]": "u_ff_cmram2",
    "cm_ram[3]": "u_ff_cmram3",
}
SRAM_LAT_D_MAP = {
    "sram_do[0]": "u_ff_sram_lat0",
    "sram_do[1]": "u_ff_sram_lat1",
    "sram_do[2]": "u_ff_sram_lat2",
    "sram_do[3]": "u_ff_sram_lat3",
}

doe_ff_inst = None
sram_idle_ff_inst = None
sram_wen_ff_inst = None
sram_ce_nor3 = None

for inst in insts:
    if inst["type"] == "DFFRB":
        q_net = inst["conns"].get("Q", "")
        d_net = inst["conns"].get("D", "")
        if q_net in ANCHORED_Q_MAP:
            inst["name"] = ANCHORED_Q_MAP[q_net]
            if q_net == "d_oe":
                doe_ff_inst = inst
        elif d_net in SRAM_LAT_D_MAP:
            inst["name"] = SRAM_LAT_D_MAP[d_net]
        elif q_net == "sram_idle_q":
            inst["name"] = "u_ff_sram_idle"
            sram_idle_ff_inst = inst
        elif q_net == "sram_we_n_q":
            inst["name"] = "u_ff_sram_wen"
            sram_wen_ff_inst = inst
    elif inst["conns"].get("Y") == "sram_ce":
        sram_ce_nor3 = inst

assert doe_ff_inst is not None, "Could not find DFFRB driving d_oe!"
assert sram_idle_ff_inst is not None, "Could not find DFFRB driving sram_idle_q!"
assert sram_wen_ff_inst is not None, "Could not find DFFRB driving sram_we_n_q!"
assert sram_ce_nor3 is not None and sram_ce_nor3["type"] == "NOR3", "Expected NOR3 driving sram_ce!"

# Buffer sram_we (66.6 fF SRAM128.WR pin) with dedicated BUF_X2 (+1.4 ns WR hold margin after CE fall)
sram_wen_ff_inst["conns"]["QB"] = "sram_we_pre"
wires.add("sram_we_pre")
insts.append({
    "type": "BUF_X2",
    "name": "u_buf_sram_we",
    "conns": {"A": "sram_we_pre", "Y": "sram_we"},
})

# Split d_oe (South edge) and d_hiz (West edge) into two edge-anchored DFFRBs
doe_ff_inst["conns"]["QB"] = "doe_qb_unused"
wires.update(["doe_qb_unused", "dhiz_q_unused", "d_hiz_pre"])
insts.append({
    "type": "DFFRB",
    "name": "u_ff_dhiz",
    "conns": {
        "CK": doe_ff_inst["conns"]["CK"],
        "D": doe_ff_inst["conns"]["D"],
        "Q": "dhiz_q_unused",
        "QB": "d_hiz_pre",
        "RSTB": doe_ff_inst["conns"]["RSTB"],
    },
})
insts.append({
    "type": "BUF_X2",
    "name": "u_buf_dhiz",
    "conns": {"A": "d_hiz_pre", "Y": "d_hiz"},
})

# Replace slow 3-series-PMOS NOR3 on sram_ce with fast NOR2(en) + NAND2(en, ~clk) + INV_X2
ce_en_bars = [n for p, n in sram_ce_nor3["conns"].items() if p in ("A", "B", "C") and n != "clk"]
assert len(ce_en_bars) == 2, f"Unexpected sram_ce NOR3 inputs: {sram_ce_nor3['conns']}"
# Bypass redundant INV_X1(sram_ce_en) if one of ce_en_bars is ~sram_ce_en (== sram_idle_q)
sram_ce_en_net = sram_idle_ff_inst["conns"].get("QB", "")
redundant_inv = None
for idx_c, bar_net in enumerate(ce_en_bars):
    for cand in insts:
        if cand["type"] == "INV_X1" and cand["conns"].get("Y") == bar_net and cand["conns"].get("A") == sram_ce_en_net:
            ce_en_bars[idx_c] = "sram_idle_q"
            redundant_inv = cand
            break
insts = [inst for inst in insts if inst is not sram_ce_nor3 and inst is not redundant_inv]
wires.update(["sram_en_ok", "clk_n_ce", "sram_ce_n"])
insts.append({
    "type": "NOR2",
    "name": "u_sram_en",
    "conns": {"A": ce_en_bars[0], "B": ce_en_bars[1], "Y": "sram_en_ok"},
})
insts.append({
    "type": "INV_X2",
    "name": "u_clk_inv_ce",
    "conns": {"A": "clk_root", "Y": "clk_n_ce"},
})
insts.append({
    "type": "NAND2",
    "name": "u_sram_ce_nand",
    "conns": {"A": "sram_en_ok", "B": "clk_n_ce", "Y": "sram_ce_n"},
})
insts.append({
    "type": "INV_X2",
    "name": "u_sram_ce_drv",
    "conns": {"A": "sram_ce_n", "Y": "sram_ce"},
})

# -------------------------------------------------------------------------
# 1. Fold MUX2 + DFFRB -> MUXDFFRB on Internal FFs Only
#    Keep Edge-Anchored Output FFs (u_ff_*), SRAM128 Capture FFs, and
#    Anchored SRAM Control FFs as pure DFFRBs!
# -------------------------------------------------------------------------
KEEP_PURE_DFFRB = (
    set(ANCHORED_Q_MAP.values())
    | {"u_ff_dhiz", "u_ff_sram_idle", "u_ff_sram_wen"}
    | set(SRAM_LAT_D_MAP.values())
)

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
    if inst["type"] == "DFFRB" and inst["name"] not in KEEP_PURE_DFFRB:
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
print(f"Folded {muxdff_count} MUX2+DFFRB pairs into MUXDFFRB (kept {len(KEEP_PURE_DFFRB)} pure DFFRBs)")

# -------------------------------------------------------------------------
# 2. Insert Schmitt-Trigger BUFTH on all 7 Primary Inputs & Upgrade rst_n INV
# -------------------------------------------------------------------------
primary_inputs = [
    ("clk",     "clk_in_th",  "u_bufth_clk"),
    ("rst",     "rst_in_th",  "u_bufth_rst"),
    ("test",    "test_in_th", "u_bufth_test"),
    ("d_in[0]", "din0_in_th", "u_bufth_din0"),
    ("d_in[1]", "din1_in_th", "u_bufth_din1"),
    ("d_in[2]", "din2_in_th", "u_bufth_din2"),
    ("d_in[3]", "din3_in_th", "u_bufth_din3"),
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
        "conns": {"A": orig, "Y": new_net},
    })

# Upgrade rst_n inverter to INV_X2
ff_insts = [inst for inst in insts if inst["type"] in ("DFFRB", "MUXDFFRB", "DFFS", "EDFFRB")]
rst_n_net = ff_insts[0]["conns"]["RSTB"]
for inst in insts:
    if inst["type"] == "INV_X1" and inst["conns"].get("Y") == rst_n_net:
        inst["type"] = "INV_X2"
        inst["name"] = "u_inv_rst_n"

print(f"Total Flip-Flops: {len(ff_insts)}")

# -------------------------------------------------------------------------
# 3. Build Low-Skew Unloaded Clock Tree + Useful Skew on sram_lat[0..3]
#    - u_bufth_clk (FO=3 local): drives u_clk_io_w, u_clk_io_e, u_clk_root
#    - u_clk_io_w (FO=6): drives West/NW output FFs in 1 stage (min t_pd!)
#    - u_clk_io_e (FO=6): drives East/South output FFs in 1 stage (min t_pd!)
#    - u_clk_root (FO=7): drives u_clk_buf_r1..r6 + u_clk_inv_ce
#    - u_clk_sram_lat1..3 (3x BUF_X2 chain from clk_buf_r6): +2.5 ns useful skew
#      on u_ff_sram_lat0..3.CK!
# -------------------------------------------------------------------------
IO_W_FFS = {"u_ff_dout0", "u_ff_dhiz", "u_ff_dout1", "u_ff_dout2", "u_ff_dout3", "u_ff_sync"}
IO_E_FFS = {"u_ff_doe", "u_ff_cmram0", "u_ff_cmram1", "u_ff_cmram2", "u_ff_cmram3", "u_ff_cmrom"}
SRAM_LAT_FFS = {"u_ff_sram_lat0", "u_ff_sram_lat1", "u_ff_sram_lat2", "u_ff_sram_lat3"}
SRAM_IDLE_FFS = {"u_ff_sram_idle"}

wires.update(["clk_io_w", "clk_io_e", "clk_root", "clk_sram_lat1", "clk_sram_lat2", "clk_sram_lat"])
insts.extend([
    {"type": "BUF_X2", "name": "u_clk_io_w",      "conns": {"A": "clk_in_th",     "Y": "clk_io_w"}},
    {"type": "BUF_X2", "name": "u_clk_io_e",      "conns": {"A": "clk_in_th",     "Y": "clk_io_e"}},
    {"type": "BUF_X2", "name": "u_clk_root",      "conns": {"A": "clk_in_th",     "Y": "clk_root"}},
    {"type": "BUF_X2", "name": "u_clk_sram_lat1", "conns": {"A": "clk_buf_r7",    "Y": "clk_sram_lat1"}},
    {"type": "BUF_X2", "name": "u_clk_sram_lat2", "conns": {"A": "clk_sram_lat1", "Y": "clk_sram_lat2"}},
    {"type": "BUF_X2", "name": "u_clk_sram_lat3", "conns": {"A": "clk_sram_lat2", "Y": "clk_sram_lat"}},
])

NUM_INTERNAL_CLK_BUFS = 7
for b_idx in range(NUM_INTERNAL_CLK_BUFS):
    c_net = f"clk_buf_r{b_idx+1}"
    wires.add(c_net)
    insts.append({
        "type": "BUF_X2",
        "name": f"u_clk_buf_r{b_idx+1}",
        "conns": {"A": "clk_root", "Y": c_net},
    })

NUM_RST_BUFS = 8
for r_idx in range(NUM_RST_BUFS):
    rn_net = f"rst_n_buf_r{r_idx+1}"
    wires.add(rn_net)
    insts.append({
        "type": "BUF_X2",
        "name": f"u_rst_buf_r{r_idx+1}",
        "conns": {"A": rst_n_net, "Y": rn_net},
    })

# Initial assignment of internal FFs across 7 clock buffers & all FFs + logic across 8 reset buffers
internal_ffs = [ff for ff in ff_insts if ff["name"] not in (IO_W_FFS | IO_E_FFS | SRAM_LAT_FFS | SRAM_IDLE_FFS)]
assert len(internal_ffs) == 50, f"Expected 50 internal FFs, got {len(internal_ffs)}"

INT_CLK_COUNTS = [8, 8, 7, 7, 7, 7, 6]  # sum = 50
idx = 0
for b_idx, cnt in enumerate(INT_CLK_COUNTS):
    for _ in range(cnt):
        internal_ffs[idx]["conns"]["CK"] = f"clk_buf_r{b_idx+1}"
        idx += 1

for ff in ff_insts:
    fname = ff["name"]
    if fname in IO_W_FFS:
        ff["conns"]["CK"] = "clk_io_w"
    elif fname in IO_E_FFS:
        ff["conns"]["CK"] = "clk_io_e"
    elif fname in SRAM_LAT_FFS:
        ff["conns"]["CK"] = "clk_sram_lat"
    elif fname in SRAM_IDLE_FFS:
        ff["conns"]["CK"] = "clk_sram_lat1"

# Distribute rst_n sinks (59 FFs + any logic sink such as rst_s1.D) across u_rst_buf_r1..r8 (<= 8 sinks each)
rst_sinks = []
for inst in insts:
    if inst["name"].startswith("u_rst_buf_"):
        continue
    for pin, net in inst["conns"].items():
        if pin not in OUTPUT_PIN_NAMES and net == rst_n_net:
            rst_sinks.append((inst, pin))

for s_i, (s_inst, s_pin) in enumerate(rst_sinks):
    b_i = min(NUM_RST_BUFS - 1, (s_i * NUM_RST_BUFS) // len(rst_sinks))
    s_inst["conns"][s_pin] = f"rst_n_buf_r{b_i+1}"

# -------------------------------------------------------------------------
# 4. Split all High-Fanout Internal Nets (FO > 10) into BUF_X2 Groups
# -------------------------------------------------------------------------
def get_sink_map(inst_list):
    smap = defaultdict(list)
    for idx_i, inst in enumerate(inst_list):
        ctype = inst["type"]
        for pin, net in inst["conns"].items():
            if ctype == "SRAM128":
                if not pin.startswith("DO"):
                    smap[net].append((idx_i, pin))
            else:
                if pin not in OUTPUT_PIN_NAMES:
                    smap[net].append((idx_i, pin))
    return smap


smap = get_sink_map(insts)
exempt_nets = (
    {orig for orig, _, _ in primary_inputs}
    | {"clk_in_th", "clk_io_w", "clk_io_e", "clk_root", "clk_sram_lat", rst_n_net}
    | {f"clk_buf_r{i+1}" for i in range(NUM_INTERNAL_CLK_BUFS)}
    | {f"rst_n_buf_r{i+1}" for i in range(NUM_RST_BUFS)}
    | {f"sram_din[{i}]" for i in range(4)}
    | {"sram_din", "sram_do"}
)

MAX_FO = 15
fo_buf_idx = 0
for net, sinks in list(smap.items()):
    if net in exempt_nets or len(sinks) <= MAX_FO:
        continue
    num_groups = max(2, (len(sinks) + MAX_FO - 1) // MAX_FO)
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
            "conns": {"A": net, "Y": bnet},
        })
        for s_idx, s_pin in grp:
            insts[s_idx]["conns"][s_pin] = bnet

print(f"Inserted {fo_buf_idx} high-fanout BUF_X2 buffers for nets with FO > 10")

final_smap = get_sink_map(insts)
max_fo = max(len(v) for v in final_smap.values())
print(f"Max fanout across all nets after buffering: {max_fo} (<= {MAX_FO} target met!)")
assert max_fo <= MAX_FO, f"Max fanout {max_fo} exceeds {MAX_FO}!"

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
    "sram_do[0]", "sram_do[1]", "sram_do[2]", "sram_do[3]",
}

all_used_nets = set()
for inst in insts:
    for net in inst["conns"].values():
        all_used_nets.add(net)

scalar_wires = sorted(all_used_nets - port_and_bus_nets)

v_lines = [
    "// Synthesized and Buffered Gate-Level Netlist for c4004_core (Plan B + Full MCS-4 Spec)",
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

total_sites = sum(int(CELL_INFO[inst["type"]]["sites"]) for inst in insts if inst["type"] != "SRAM128")
print(
    f"Wrote {OUT_V}: {len(insts)} total instances ({len(insts)-1} stdcells + 1 SRAM128), "
    f"{total_sites} sites (out of 3575 available sites = {total_sites*100.0/3575:.1f}% utilization)"
)
