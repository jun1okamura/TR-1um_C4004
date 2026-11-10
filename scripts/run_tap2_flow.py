import os
import re
import json
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN_V          = os.path.join(BASE_DIR, "openroad/c4004_core_syn.v")
CELL_INFO_JSON = os.path.join(BASE_DIR, "module/STDCELL/cell_info.json")
ROW_MAP_JSON   = os.path.join(BASE_DIR, "openroad/ff_row_map.json")
OUT_DEF        = os.path.join(BASE_DIR, "openroad/c4004_core_placed.def")
GPL_DEF        = os.path.join(BASE_DIR, "openroad/gpl_coords.def")

with open(CELL_INFO_JSON, "r") as f:
    CELL_INFO = json.load(f)

OUTPUT_PIN_NAMES = {"Y", "Q", "QB", "DO"}

# -------------------------------------------------------------------------
# 1. Floorplan Geometry Constants (DBU = 1000 per micron) - Trial 06
#    11 Rows (3,575 sites!) with Row Pitch = 145.8 um (27 tracks, 86.4 um = 16-track channels)
#    and SRAM128 shifted East to (345.6 um, 1614.6 um)!
# -------------------------------------------------------------------------
DBU = 1000
SITE_W = 5.4
ROW_H  = 59.4
NUM_ROWS = 11
ROW_PITCH = 145.8
ROW_YS = [round(27.0 + r * ROW_PITCH, 4) for r in range(NUM_ROWS)]

TAP_XS = [21.6, 615.6, 1215.0, 1809.0]
SEGMENTS = [
    (32.4,   615.6,  108),  # Seg 0 (Left):   108 sites
    (626.4,  1215.0, 109),  # Seg 1 (Center): 109 sites
    (1225.8, 1809.0, 108),  # Seg 2 (Right):  108 sites
]

SRAM_X = 340.2
SRAM_Y = 1614.6

CORE_PINS = [
    # North edge (LAYER METAL2)
    ("clk",       "INPUT",  "METAL2",  281.8, 1795.0,  285.2, 1808.0),
    ("sync",      "OUTPUT", "METAL2",  298.0, 1795.0,  301.4, 1815.0),
    ("cm_rom",    "OUTPUT", "METAL2", 1540.0, 1795.0, 1543.4, 1815.0),
    # South edge (LAYER METAL2)
    ("rst",       "INPUT",  "METAL2",  389.8,   10.0,  393.2,   25.0),
    ("d_oe",      "OUTPUT", "METAL2", 1097.2,   10.0, 1100.6,   25.0),
    ("test",      "INPUT",  "METAL2", 1448.2,   10.0, 1451.6,   25.0),
    # West edge (LAYER METAL1 in 145.8um-pitch 11-row inter-row channels)
    ("d_out[0]",  "OUTPUT", "METAL1",   35.0,  304.1,   45.0,  306.1),
    ("d_hiz",     "OUTPUT", "METAL1",   35.0,  287.9,   45.0,  289.9),
    ("d_in[0]",   "INPUT",  "METAL1",   35.0,  422.9,   45.0,  424.9),
    ("d_in[1]",   "INPUT",  "METAL1",   35.0,  698.3,   45.0,  700.3),
    ("d_out[1]",  "OUTPUT", "METAL1",   35.0,  730.7,   45.0,  732.7),
    ("d_out[2]",  "OUTPUT", "METAL1",   35.0, 1124.9,   45.0, 1126.9),
    ("d_in[2]",   "INPUT",  "METAL1",   35.0, 1162.7,   45.0, 1164.7),
    ("d_in[3]",   "INPUT",  "METAL1",   35.0, 1421.9,   45.0, 1423.9),
    ("d_out[3]",  "OUTPUT", "METAL1",   35.0, 1567.7,   45.0, 1569.7),
    # East edge (LAYER METAL1 in 145.8um-pitch 11-row inter-row channels)
    ("cm_ram[0]", "OUTPUT", "METAL1", 1795.0,  304.1, 1805.0,  306.1),
    ("cm_ram[1]", "OUTPUT", "METAL1", 1795.0,  730.7, 1805.0,  732.7),
    ("cm_ram[2]", "OUTPUT", "METAL1", 1795.0, 1124.9, 1805.0, 1126.9),
    ("cm_ram[3]", "OUTPUT", "METAL1", 1795.0, 1567.7, 1805.0, 1569.7),
]

# -------------------------------------------------------------------------
# 2. Parse Synthesized & Buffered Netlist + RePlAce Analytical Coordinates
# -------------------------------------------------------------------------
def parse_syn_v(path):
    with open(path, "r") as f:
        text = f.read()
    inst_pattern = re.compile(r"^\s*(\S+)\s+(\S+)\s*\((.*?)\)\s*;", flags=re.MULTILINE)
    insts = []
    for m in inst_pattern.finditer(text):
        ctype, iname, body = m.group(1), m.group(2), m.group(3)
        if ctype in ("module", "input", "output", "wire"):
            continue
        conns = {}
        for pm in re.finditer(r"\.(\w+)\(\s*([^\)]+?)\s*\)", body):
            conns[pm.group(1)] = pm.group(2).strip()
        insts.append({"type": ctype, "name": iname, "conns": conns})
    return insts

insts = parse_syn_v(SYN_V)
inst_by_name = {inst["name"]: inst for inst in insts}

cell_xy = {}
if os.path.exists(GPL_DEF):
    with open(GPL_DEF, "r") as f:
        gpl_txt = f.read()
    for m in re.finditer(r"^\s*-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)", gpl_txt, flags=re.MULTILINE):
        iname, ctype, x_dbu, y_dbu = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        cell_xy[iname] = (x_dbu / 1000.0, y_dbu / 1000.0)
    print(f"Loaded {len(cell_xy)} analytical cell coordinates from {GPL_DEF}")
else:
    for inst in insts:
        if inst["type"] != "SRAM128":
            cell_xy[inst["name"]] = (920.0, 745.2)

# -------------------------------------------------------------------------
# 3. Assign FFs & BUFTHs to 11 Rows by Y Coordinate & Re-group High-FO Sinks
# -------------------------------------------------------------------------
BUFTH_FIXED_ROW_X = {
    "u_bufth_rst":   (0,   391.5),
    "u_bufth_test":  (0,  1449.9),
    "u_bufth_din0":  (2,    40.0),
    "u_bufth_din1":  (4,    40.0),
    "u_bufth_din2":  (7,    40.0),
    "u_bufth_din3":  (9,    40.0),
    "u_bufth_clk":   (10,  283.5),
}
for bname, (br, bx) in BUFTH_FIXED_ROW_X.items():
    if bname in inst_by_name:
        cell_xy[bname] = (bx, ROW_YS[br])

# Anchor u_buf_dhiz and _1071_ near West d_hiz pin (Row 2 at Y = 318.6 um, X = 45.0 / 50.0 um),
# _1072_ and u_buf_doe near South d_oe pin (Row 0 Segment 1 East at X = 960.0 / 965.0 um -> legalized ~1100 um!),
# _1101_ and _1102_ (NOR2 driving sram_ce directly from clk_in_th) at Row 10 East (X = 1480.0 / 1495.0 um) below SRAM128.CE,
# and place reg_buf[3:0] (_1143_.._1146_) + u_rb_mux0..3 in their analytical rows (Row 3/4) shifted East (X = 950..1050 um)
# toward SRAM128.DO[3:0] without perturbing any of the 41 flip-flop row buckets!
if "u_buf_dhiz" in inst_by_name:
    cell_xy["u_buf_dhiz"] = (45.0, ROW_YS[2])
if "_1071_" in inst_by_name:
    cell_xy["_1071_"] = (50.0, ROW_YS[2])
if "_1072_" in inst_by_name:
    cell_xy["_1072_"] = (960.0, ROW_YS[0])
if "u_buf_doe" in inst_by_name:
    cell_xy["u_buf_doe"] = (965.0, ROW_YS[0])
if "u_n_a123" in inst_by_name:
    cell_xy["u_n_a123"] = (550.0, ROW_YS[2])
if "u_n_x23_oe" in inst_by_name:
    cell_xy["u_n_x23_oe"] = (650.0, ROW_YS[4])
if "_1101_" in inst_by_name:
    cell_xy["_1101_"] = (1480.0, ROW_YS[10])
if "_1102_" in inst_by_name:
    cell_xy["_1102_"] = (1495.0, ROW_YS[10])
if "u_rb_sram_sel_n" in inst_by_name:
    cell_xy["u_rb_sram_sel_n"] = (920.0, 900.0)
for idx_rb, (ff_rb, mux_rb, n2_rb, r_rb) in enumerate([
    ("_1143_", "u_rb_mux0", "_0824_", 6),
    ("_1144_", "u_rb_mux1", "_0830_", 6),
    ("_1145_", "u_rb_mux2", "_0836_", 7),
    ("_1146_", "u_rb_mux3", "_1011_", 7),
]):
    base_y = ROW_YS[r_rb]
    tx = 1240.0 + idx_rb * 35.0
    if ff_rb in inst_by_name:
        cell_xy[ff_rb] = (tx, base_y)
    if mux_rb in inst_by_name:
        cell_xy[mux_rb] = (tx - 10.0, base_y)
    if n2_rb in inst_by_name:
        cell_xy[n2_rb] = (tx - 20.0, base_y)

ff_insts = [inst for inst in insts if inst["type"] in ("DFFRB", "MUXDFFRB", "DFFS", "EDFFRB")]
ff_insts.sort(key=lambda inst: (cell_xy.get(inst["name"], (920.0, 745.2))[1], cell_xy.get(inst["name"], (920.0, 745.2))[0]))

ff_row_map = {}
row_ffs = defaultdict(list)
FF_TARGET_PER_ROW = [3, 2, 2, 4, 4, 4, 6, 6, 4, 3, 3]  # sum = 41 across 11 rows (Rows 0+1 = 5, Row 6 = 6, Rows 7+8 = 10, Rows 9+10 = 6 <= 10!)
idx = 0
for r, cnt in enumerate(FF_TARGET_PER_ROW):
    for _ in range(cnt):
        ff = ff_insts[idx]
        ff_row_map[ff["name"]] = r
        row_ffs[r].append(ff)
        cell_xy[ff["name"]] = (cell_xy.get(ff["name"], (920.0, ROW_YS[r]))[0], ROW_YS[r])
        idx += 1

for bname, (br, bx) in BUFTH_FIXED_ROW_X.items():
    if bname in inst_by_name:
        ff_row_map[bname] = br
if "u_buf_dhiz" in inst_by_name:
    ff_row_map["u_buf_dhiz"] = 2
if "_1071_" in inst_by_name:
    ff_row_map["_1071_"] = 2
if "u_n_a123" in inst_by_name:
    ff_row_map["u_n_a123"] = 2
if "u_n_x23_oe" in inst_by_name:
    ff_row_map["u_n_x23_oe"] = 4
if "_1072_" in inst_by_name:
    ff_row_map["_1072_"] = 0
if "u_buf_doe" in inst_by_name:
    ff_row_map["u_buf_doe"] = 0
if "_1101_" in inst_by_name:
    ff_row_map["_1101_"] = 10
if "_1102_" in inst_by_name:
    ff_row_map["_1102_"] = 10

NUM_CLK_BUFS = 8
for b_idx in range(NUM_CLK_BUFS):
    c_net = f"clk_buf_r{b_idx+1}"
    rn_net = f"rst_n_buf_r{b_idx+1}"
    if b_idx == 0:
        grp_ffs = row_ffs[0] + row_ffs[1]
        buf_row = 1
    elif b_idx <= 5:
        grp_ffs = row_ffs[b_idx + 1]
        buf_row = b_idx + 1
    elif b_idx == 6:
        grp_ffs = row_ffs[7] + row_ffs[8]
        buf_row = 8
    else:
        grp_ffs = row_ffs[9] + row_ffs[10]
        buf_row = 9
    xs = [cell_xy.get(ff["name"], (920.0, ROW_YS[buf_row]))[0] for ff in grp_ffs]
    avg_x = sum(xs) / len(xs) if xs else 920.0
    cell_xy[f"u_clk_buf_r{b_idx+1}"] = (avg_x, ROW_YS[buf_row])
    cell_xy[f"u_rst_buf_r{b_idx+1}"] = (avg_x, ROW_YS[buf_row])
    ff_row_map[f"u_clk_buf_r{b_idx+1}"] = buf_row
    ff_row_map[f"u_rst_buf_r{b_idx+1}"] = buf_row
    for ff in grp_ffs:
        ff["conns"]["CK"] = c_net
        if "RSTB" in ff["conns"]:
            ff["conns"]["RSTB"] = rn_net

with open(ROW_MAP_JSON, "w") as f:
    json.dump(ff_row_map, f, indent=2)

# Re-group High-Fanout Buffer Sinks by Analytical X Coordinate (Left vs Right)
fobuf_by_drv = defaultdict(list)
for inst in insts:
    if inst["name"].startswith("u_fobuf_"):
        drv_net = inst["conns"]["A"]
        fobuf_by_drv[drv_net].append(inst)

for drv_net, buf_list in fobuf_by_drv.items():
    if len(buf_list) < 2:
        continue
    b_nets = {b["conns"]["Y"] for b in buf_list}
    sinks = []
    for inst in insts:
        if inst["type"] == "SRAM128":
            continue
        for p, n in inst["conns"].items():
            if p not in OUTPUT_PIN_NAMES and n in b_nets:
                sx, sy = cell_xy.get(inst["name"], (920.0, 745.2))
                sinks.append((sx, sy, inst, p))
    sinks.sort(key=lambda item: (item[0], item[1]))
    chunk_size = (len(sinks) + len(buf_list) - 1) // len(buf_list)
    for g_idx, b_inst in enumerate(buf_list):
        b_net = b_inst["conns"]["Y"]
        grp = sinks[g_idx * chunk_size : (g_idx + 1) * chunk_size]
        if grp:
            avg_x = sum(item[0] for item in grp) / len(grp)
            avg_y = sum(item[1] for item in grp) / len(grp)
            cell_xy[b_inst["name"]] = (avg_x, avg_y)
            for _, _, s_inst, s_pin in grp:
                s_inst["conns"][s_pin] = b_net

with open(SYN_V, "r") as f:
    orig_v_text = f.read()
header_part = orig_v_text.split("  INV_X1 ")[0]
v_out_lines = [header_part.rstrip()]
for inst in insts:
    ctype = inst["type"]
    iname = inst["name"]
    c_strs = [f".{k}({v})" for k, v in inst["conns"].items()]
    v_out_lines.append(f"  {ctype} {iname} ( " + ", ".join(c_strs) + " );")
v_out_lines.append("endmodule\n")
with open(SYN_V, "w") as f:
    f.write("\n".join(v_out_lines))
print("Updated FF row clock/reset assignment and high-FO X grouping in c4004_core_syn.v")

# -------------------------------------------------------------------------
# 4. Legalize into 11 Rows x 3 Segments by Nearest RePlAce Coordinates (tx, ty)
#    Every segment reserves >= 2 filler sites (0 FILL1!)
# -------------------------------------------------------------------------
FREE_M2_BY_TYPE = {
    "MUXDFFRB": 11, "DFFRB": 7, "DFFS": 7, "DFF": 8, "EDFFRB": 12,
    "BUFTH": 4, "DEL1": 4, "MUX2": 2, "XOR2": 2, "XNOR2": 2,
    "AND2_X1": 1, "AND3_X1": 1, "AND4_X1": 1,
    "OR2": 1, "OR3": 1, "OR4": 1,
    "BUF_X1": 1, "BUF_X2": 1,
    "FILL3": 3, "FILL2": 2, "FILL1": 1,
}

def get_pin_m2(ctype):
    w = int(CELL_INFO[ctype]["sites"])
    return w - FREE_M2_BY_TYPE.get(ctype, 0)

# Total sites = 2847 across 11 rows -> ~258.8 sites/row (leave ~66.2 sites/row for FILL3/FILL2!)
ROW_SITE_CAP = [265, 262, 260, 256, 254, 254, 256, 260, 262, 265, 270]  # sum = 2864 >= 2847, lower density in middle rows!
row_insts = defaultdict(list)
row_used = [0] * NUM_ROWS
placed_names = set()

for iname, r0 in ff_row_map.items():
    inst = inst_by_name[iname]
    w = int(CELL_INFO[inst["type"]]["sites"])
    row_insts[r0].append(inst)
    row_used[r0] += w
    placed_names.add(iname)

rem_insts = [
    inst for inst in insts
    if inst["type"] != "SRAM128" and inst["name"] not in placed_names
]
rem_insts.sort(key=lambda inst: (
    cell_xy.get(inst["name"], (920.0, 745.2))[1],
    cell_xy.get(inst["name"], (920.0, 745.2))[0]
))

cur_r = 0
for inst in rem_insts:
    w = int(CELL_INFO[inst["type"]]["sites"])
    while cur_r < NUM_ROWS - 1 and (row_used[cur_r] + w > ROW_SITE_CAP[cur_r]):
        cur_r += 1
    if row_used[cur_r] + w > 312:
        best_r = min(
            [r for r in range(NUM_ROWS) if row_used[r] + w <= 312],
            key=lambda r: abs(r - cur_r)
        )
        row_insts[best_r].append(inst)
        row_used[best_r] += w
    else:
        row_insts[cur_r].append(inst)
        row_used[cur_r] += w
    placed_names.add(inst["name"])

seg_used = {(r, s): 0 for r in range(NUM_ROWS) for s in range(3)}
seg_pins = {(r, s): 0 for r in range(NUM_ROWS) for s in range(3)}
seg_cells = defaultdict(list)

for r in range(NUM_ROWS):
    r_list = sorted(
        row_insts[r],
        key=lambda inst: (
            cell_xy.get(inst["name"], (920.0, ROW_YS[r]))[0],
            int(CELL_INFO[inst["type"]]["sites"])
        )
    )
    total_r_sites = sum(int(CELL_INFO[i["type"]]["sites"]) for i in r_list)
    s0_target = max(total_r_sites // 3, total_r_sites - 208)
    s1_target = max((total_r_sites - s0_target) // 2, total_r_sites - s0_target - 104)
    for inst in r_list:
        w = int(CELL_INFO[inst["type"]]["sites"])
        pm = get_pin_m2(inst["type"])
        if seg_used[(r, 0)] < s0_target and seg_used[(r, 0)] + w <= 106:
            bs = 0
        elif seg_used[(r, 1)] < s1_target and seg_used[(r, 1)] + w <= 107:
            bs = 1
        elif seg_used[(r, 2)] + w <= 106:
            bs = 2
        else:
            bs = max([0, 1, 2], key=lambda s: SEGMENTS[s][2] - seg_used[(r, s)])
        assert SEGMENTS[bs][2] - (seg_used[(r, bs)] + w) >= 2, f"Overflow in row {r} seg {bs}"
        seg_cells[(r, bs)].append(inst)
        seg_used[(r, bs)] += w
        seg_pins[(r, bs)] += pm

# -------------------------------------------------------------------------
# 5. Compute Exact X Coordinates & Insert TAP2 + FILL3 / FILL2 (0 FILL1!)
# -------------------------------------------------------------------------
placed_components = []
placed_components.append(("u_sram", "SRAM128", "FIXED", round(SRAM_X * DBU), round(SRAM_Y * DBU), "N"))

tap2_count = 0
for r in range(NUM_ROWS):
    ry = round(ROW_YS[r] * DBU)
    for c_idx, tx in enumerate(TAP_XS):
        tname = f"u_tap2_r{r}_c{c_idx}"
        placed_components.append((tname, "TAP2", "FIXED", round(tx * DBU), ry, "N"))
        tap2_count += 1

fill3_count = 0
fill2_count = 0

def decompose_fillers(gap_sites):
    res = []
    rem = gap_sites
    while rem > 0:
        if rem == 2:
            res.append(("FILL2", 2))
            rem -= 2
        elif rem == 4:
            res.append(("FILL2", 2))
            res.append(("FILL2", 2))
            rem -= 4
        else:
            res.append(("FILL3", 3))
            rem -= 3
    return res

for r in range(NUM_ROWS):
    ry = round(ROW_YS[r] * DBU)
    for s in range(3):
        x_start, x_end, cap = SEGMENTS[s]
        c_list = seg_cells[(r, s)]
        c_list.sort(key=lambda inst: cell_xy.get(inst["name"], (920.0, 0.0))[0])
        gap = cap - seg_used[(r, s)]
        fillers = decompose_fillers(gap)

        for idx in range(len(c_list) - 2):
            if (
                FREE_M2_BY_TYPE.get(c_list[idx]["type"], 0) == 0
                and FREE_M2_BY_TYPE.get(c_list[idx + 1]["type"], 0) == 0
                and FREE_M2_BY_TYPE.get(c_list[idx + 2]["type"], 0) == 0
            ):
                for look in range(idx + 3, min(len(c_list), idx + 7)):
                    ct_l = c_list[look]["type"]
                    if FREE_M2_BY_TYPE.get(ct_l, 0) > 0 and int(CELL_INFO[ct_l]["sites"]) <= 6:
                        c_list[idx + 2], c_list[look] = c_list[look], c_list[idx + 2]
                        break

        merged_items = [("CELL", inst) for inst in c_list]

        for f_obj in fillers:
            best_len = -1
            best_ins = len(merged_items)
            cur_run_sites = 0
            run_start = 0
            for idx, (kind, obj) in enumerate(merged_items):
                if kind == "CELL" and FREE_M2_BY_TYPE.get(obj["type"], 0) == 0:
                    if cur_run_sites == 0:
                        run_start = idx
                    cur_run_sites += int(CELL_INFO[obj["type"]]["sites"])
                    if cur_run_sites > best_len:
                        best_len = cur_run_sites
                        best_ins = (run_start + idx + 1) // 2
                else:
                    cur_run_sites = 0
            merged_items.insert(best_ins, ("FILL", f_obj))

        cur_site = 0
        f_idx = 0
        for kind, obj in merged_items:
            if kind == "CELL":
                inst = obj
                w = int(CELL_INFO[inst["type"]]["sites"])
                cx_dbu = round((x_start + cur_site * SITE_W) * DBU)
                placed_components.append((inst["name"], inst["type"], "PLACED", cx_dbu, ry, "N"))
                cur_site += w
            else:
                ftype, fw = obj
                fx_dbu = round((x_start + cur_site * SITE_W) * DBU)
                fname = f"u_fill_r{r}_s{s}_{f_idx}"
                placed_components.append((fname, ftype, "FIXED", fx_dbu, ry, "N"))
                cur_site += fw
                if ftype == "FILL3":
                    fill3_count += 1
                else:
                    fill2_count += 1
                f_idx += 1

        assert cur_site == cap

print(f"Placement complete: {len(insts)} logic/macro cells + {tap2_count} TAP2 + {fill3_count} FILL3 + {fill2_count} FILL2 (0 FILL1!) = {len(placed_components)} total components")

# -------------------------------------------------------------------------
# 6. Write DEF File (openroad/c4004_core_placed.def)
# -------------------------------------------------------------------------
def_lines = [
    "VERSION 5.8 ;",
    "DIVIDERCHAR \"/\" ;",
    "BUSBITCHARS \"[]\" ;",
    "DESIGN c4004_core ;",
    "UNITS DISTANCE MICRONS 1000 ;",
    "DIEAREA ( 0 0 ) ( 1840000 1840000 ) ;",
    ""
]

for r in range(NUM_ROWS):
    ry = round(ROW_YS[r] * DBU)
    def_lines.append(f"ROW ROW_{r} TR1UM 0 {ry} N DO 340 BY 1 STEP 5400 0 ;")
def_lines.append("")

def_lines.append("TRACKS X 2700 DO 340 STEP 5400 LAYER METAL1 ;")
def_lines.append("TRACKS Y 2700 DO 340 STEP 5400 LAYER METAL1 ;")
def_lines.append("TRACKS X 2700 DO 340 STEP 5400 LAYER METAL2 ;")
def_lines.append("TRACKS Y 2700 DO 340 STEP 5400 LAYER METAL2 ;")
def_lines.append("")

def_lines.append(f"COMPONENTS {len(placed_components)} ;")
for cname, ctype, status, x_dbu, y_dbu, orient in placed_components:
    def_lines.append(f"  - {cname} {ctype} + {status} ( {x_dbu} {y_dbu} ) {orient} ;")
def_lines.append("END COMPONENTS")
def_lines.append("")

def_lines.append(f"PINS {len(CORE_PINS)} ;")
for pname, pdir, player, x1, y1, x2, y2 in CORE_PINS:
    cx = round((x1 + x2) * 0.5 * DBU)
    cy = round((y1 + y2) * 0.5 * DBU)
    dx1 = round(x1 * DBU) - cx
    dy1 = round(y1 * DBU) - cy
    dx2 = round(x2 * DBU) - cx
    dy2 = round(y2 * DBU) - cy
    def_lines.append(f"  - {pname} + NET {pname} + DIRECTION {pdir} + USE SIGNAL")
    def_lines.append(f"    + PORT")
    def_lines.append(f"      + LAYER {player} ( {dx1} {dy1} ) ( {dx2} {dy2} )")
    def_lines.append(f"      + FIXED ( {cx} {cy} ) N ;")
def_lines.append("END PINS")
def_lines.append("")

# BLOCKAGES (Exact TAP2 M2 strap edges + SRAM128 at X = 345.6 um, Y = 1614.6 um)
blockages = [
    # Outer perimeter + Col 0 (x <= 31.4 um) & Col 3 (x >= 1810.0 um)
    ("METAL1",       0,       0,   31400, 1840000),
    ("METAL2",       0,       0,   31400, 1840000),
    ("METAL1", 1810000,       0, 1840000, 1840000),
    ("METAL2", 1810000,       0, 1840000, 1840000),
    ("METAL1",       0,       0, 1840000,    9000),
    ("METAL2",       0,       0, 1840000,    9000),
    ("METAL1",       0, 1816000, 1840000, 1840000),
    ("METAL2",       0, 1816000, 1840000, 1840000),
    # Protect middle TAP2 M2 columns: Col 1 (616.6..625.4 um) & Col 2 (1216.0..1224.8 um) up to y=1546.0 um
    ("METAL2",  616600,       0,  625400, 1546000),
    ("METAL2", 1216000,       0, 1224800, 1546000),
    # Protect SRAM128 Left & Right M1 VDD/VSS horizontal straps (Y = 1614.6..1623.4 and 1791.4..1800.2)
    ("METAL1",   21600, 1614600,  349000, 1623400),
    ("METAL1",   21600, 1791400,  349000, 1800200),
    ("METAL1", 1508300, 1614600, 1819800, 1623400),
    ("METAL1", 1508300, 1791400, 1819800, 1800200),
]
def_lines.append(f"BLOCKAGES {len(blockages)} ;")
for lay, x1, y1, x2, y2 in blockages:
    def_lines.append(f"  - LAYER {lay} RECT ( {x1} {y1} ) ( {x2} {y2} ) ;")
def_lines.append("END BLOCKAGES")
def_lines.append("")

final_nets = defaultdict(list)
for pname, *_ in CORE_PINS:
    final_nets[pname].append(("PIN", pname))

for inst in insts:
    iname = inst["name"]
    if inst["type"] == "SRAM128":
        for p, n in inst["conns"].items():
            if p == "DIN":
                for b in range(4):
                    final_nets[f"sram_din[{b}]"].append((iname, f"DIN[{b}]"))
            elif p == "DO":
                for b in range(4):
                    final_nets[f"sram_do[{b}]"].append((iname, f"DO[{b}]"))
            else:
                final_nets[n].append((iname, p))
    else:
        for p, n in inst["conns"].items():
            final_nets[n].append((iname, p))

def_lines.append(f"NETS {len(final_nets)} ;")
for net_name in sorted(final_nets.keys()):
    conns = final_nets[net_name]
    c_str = " ".join(f"( {iname} {pin} )" for iname, pin in conns)
    def_lines.append(f"  - {net_name} {c_str} + USE SIGNAL ;")
def_lines.append("END NETS")
def_lines.append("")
def_lines.append("END DESIGN")

with open(OUT_DEF, "w") as f:
    f.write("\n".join(def_lines) + "\n")
print(f"Wrote {OUT_DEF} with {len(final_nets)} signal nets")
