import json
import math
import os
import random
import re
import subprocess
import tempfile
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN_V          = os.path.join(BASE_DIR, "openroad/c4004_core_syn.v")
CELL_INFO_JSON = os.path.join(BASE_DIR, "module/STDCELL/cell_info.json")
ROW_MAP_JSON   = os.path.join(BASE_DIR, "openroad/ff_row_map.json")
OUT_DEF        = os.path.join(BASE_DIR, "openroad/c4004_core_placed.def")
SRAM_LEF       = os.path.join(BASE_DIR, "openroad/SRAM128_clean.lef")
TECH_LEF       = os.path.join(BASE_DIR, "openroad/TR-1um_tech_clean.lef")
CELLS_LEF      = os.path.join(BASE_DIR, "openroad/TR-1um_cells_grt_m1.lef")

with open(CELL_INFO_JSON, "r") as f:
    CELL_INFO = json.load(f)

OUTPUT_PIN_NAMES = {"Y", "Q", "QB", "DO"}

# -------------------------------------------------------------------------
# 1. Floorplan Geometry Constants (DBU = 1000 per micron)
#    11 Rows (3,575 sites) with Row Pitch = 145.8 um (27 tracks, 16-track M1 channels)
#    and SRAM128 at (340.2 um, 1614.6 um)
# -------------------------------------------------------------------------
DBU = 1000
SITE_W = 5.4
ROW_H  = 59.4
NUM_ROWS = 11
ROW_PITCH = 145.8
ROW_YS = [round(27.0 + r * ROW_PITCH, 4) for r in range(NUM_ROWS)]

TAP_XS = [21.6, 615.6, 1215.0, 1809.0]
SEGMENTS = [
    (32.4,   615.6,  108),  # Seg 0 (West):   108 sites
    (626.4,  1215.0, 109),  # Seg 1 (Center): 109 sites
    (1225.8, 1809.0, 108),  # Seg 2 (East):   108 sites
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

ANCHORS = {
    "u_bufth_rst":     (0,  0,  367.2),
    "u_inv_rst_n":     (0,  0,  399.6),
    "u_ff_doe":        (0,  1, 1063.8),
    "u_bufth_test":    (0,  2, 1425.6),
    "u_ff_dhiz":       (2,  0,   32.4),
    "u_buf_dhiz":      (2,  0,   97.2),
    "u_ff_dout0":      (2,  0,  113.4),
    "u_ff_cmram0":     (2,  2, 1744.2),
    "u_bufth_din0":    (3,  0,   32.4),
    "u_bufth_din1":    (4,  0,   32.4),
    "u_ff_dout1":      (5,  0,   32.4),
    "u_ff_cmram1":     (5,  2, 1744.2),
    "u_ff_dout2":      (7,  0,   32.4),
    "u_ff_cmram2":     (7,  2, 1744.2),
    "u_bufth_din2":    (8,  0,   32.4),
    "u_bufth_din3":    (9,  0,   32.4),
    "u_clk_io_e":      (9,  0,  302.4),
    "u_buf_sram_we":   (9,  0,  340.2),
    "u_clk_sram_lat1": (9,  2, 1274.4),
    "u_clk_sram_lat2": (9,  2, 1290.6),
    "u_clk_sram_lat3": (9,  2, 1306.8),
    "u_ff_sram_idle":  (9,  2, 1414.8),
    "u_sram_en":       (9,  2, 1485.0),
    "u_clk_inv_ce":    (9,  2, 1517.4),
    "u_ff_dout3":      (10, 0,   32.4),
    "u_clk_io_w":      (10, 0,  259.2),
    "u_bufth_clk":     (10, 0,  275.4),
    "u_clk_root":      (10, 0,  307.8),
    "u_ff_sync":       (10, 0,  324.0),
    "u_ff_sram_lat0":  (10, 2, 1285.2),
    "u_ff_sram_lat1":  (10, 2, 1366.2),
    "u_ff_sram_lat2":  (10, 2, 1447.2),
    "u_sram_ce_nand":  (10, 2, 1528.2),
    "u_sram_ce_drv":   (10, 2, 1544.4),
    "u_ff_cmrom":      (10, 2, 1555.2),
    "u_ff_sram_lat3":  (10, 2, 1647.0),
    "u_ff_cmram3":     (10, 2, 1744.2),
}

WEST_EDGE_LOCKED = {nm for nm, (_, _, ax) in ANCHORS.items() if ax < 120.0}
EAST_EDGE_LOCKED = {nm for nm, (_, _, ax) in ANCHORS.items() if ax > 1730.0}
EDGE_LOCKED = WEST_EDGE_LOCKED | EAST_EDGE_LOCKED

# -------------------------------------------------------------------------
# 2. Parse Netlist & SRAM128 / Core Pin Coordinates
# -------------------------------------------------------------------------
with open(SYN_V, "r") as f:
    syn_text = f.read()

insts = []
for m in re.finditer(r"^\s*(\S+)\s+(\S+)\s*\((.*?)\)\s*;", syn_text, flags=re.MULTILINE):
    ctype, iname, body = m.group(1), m.group(2), m.group(3)
    if ctype in ("module", "input", "output", "wire"):
        continue
    conns = {pm.group(1): pm.group(2).strip() for pm in re.finditer(r"\.(\w+)\(\s*([^\)]+?)\s*\)", body)}
    w = 0 if ctype == "SRAM128" else int(CELL_INFO[ctype]["sites"])
    insts.append({"type": ctype, "name": iname, "conns": conns, "w": w})

inst_map = {x["name"]: x for x in insts}

pin_xy = {pname: ((x1 + x2) * 0.5, (y1 + y2) * 0.5) for pname, _, _, x1, y1, x2, y2 in CORE_PINS}
sram_pin_xy = {}
with open(SRAM_LEF, "r") as f:
    lef_txt = f.read()
for pm in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", lef_txt, flags=re.DOTALL):
    pnm = pm.group(1)
    rm = re.search(r"RECT\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)", pm.group(2))
    if rm:
        px = SRAM_X + 0.5 * (float(rm.group(1)) + float(rm.group(3)))
        py = SRAM_Y + 0.5 * (float(rm.group(2)) + float(rm.group(4)))
        sram_pin_xy[pnm] = (px, py)

# -------------------------------------------------------------------------
# 3. Unbiased Analytical Global Placement via OpenROAD (-density 0.52)
# -------------------------------------------------------------------------
fobuf_drv = {}
for inst in insts:
    if inst["name"].startswith("u_fobuf_"):
        fobuf_drv[inst["conns"]["Y"]] = inst["conns"]["A"]

with tempfile.TemporaryDirectory() as tmpd:
    gpl_in = os.path.join(tmpd, "gpl_in.def")
    gpl_out = os.path.join(tmpd, "gpl_out.def")
    gpl_tcl = os.path.join(tmpd, "run_gpl.tcl")

    lines = [
        "VERSION 5.8 ;",
        'DIVIDERCHAR "/" ;',
        'BUSBITCHARS "[]" ;',
        "DESIGN c4004_core ;",
        "UNITS DISTANCE MICRONS 1000 ;",
        "DIEAREA ( 0 0 ) ( 1840000 1840000 ) ;",
    ]
    for r, ry in enumerate(ROW_YS):
        lines.append(f"ROW ROW_{r} TR1UM 21600 {round(ry*DBU)} N DO 333 BY 1 STEP 5400 0 ;")
    lines += [
        "TRACKS X 2700 DO 340 STEP 5400 LAYER METAL1 ;",
        "TRACKS Y 2700 DO 340 STEP 5400 LAYER METAL1 ;",
        "TRACKS X 2700 DO 340 STEP 5400 LAYER METAL2 ;",
        "TRACKS Y 2700 DO 340 STEP 5400 LAYER METAL2 ;",
        f"COMPONENTS {len(insts) + 44} ;",
    ]
    for r, ry in enumerate(ROW_YS):
        for c_i, tx in enumerate(TAP_XS):
            lines.append(f"  - u_tap2_r{r}_c{c_i} TAP2 + FIXED ( {round(tx*DBU)} {round(ry*DBU)} ) N ;")
    for inst in insts:
        iname, ctype = inst["name"], inst["type"]
        if ctype == "SRAM128":
            lines.append(f"  - {iname} {ctype} + FIXED ( {round(SRAM_X*DBU)} {round(SRAM_Y*DBU)} ) N ;")
        elif iname in ANCHORS:
            ar, _, ax = ANCHORS[iname]
            lines.append(f"  - {iname} {ctype} + FIXED ( {round(ax*DBU)} {round(ROW_YS[ar]*DBU)} ) N ;")
        else:
            lines.append(f"  - {iname} {ctype} + UNPLACED ;")
    lines.append("END COMPONENTS")
    lines.append(f"PINS {len(CORE_PINS)} ;")
    for pname, pdir, player, x1, y1, x2, y2 in CORE_PINS:
        cx, cy = round((x1 + x2) * 0.5 * DBU), round((y1 + y2) * 0.5 * DBU)
        dx1, dy1 = round(x1 * DBU) - cx, round(y1 * DBU) - cy
        dx2, dy2 = round(x2 * DBU) - cx, round(y2 * DBU) - cy
        lines.append(f"  - {pname} + NET {pname} + DIRECTION {pdir} + USE SIGNAL")
        lines.append(f"    + PORT + LAYER {player} ( {dx1} {dy1} ) ( {dx2} {dy2} ) + FIXED ( {cx} {cy} ) N ;")
    lines.append("END PINS")

    def_nets = defaultdict(list)
    for pname, *_ in CORE_PINS:
        def_nets[pname].append(("PIN", pname))
    for inst in insts:
        iname, ctype = inst["name"], inst["type"]
        if ctype == "SRAM128":
            for p, n in inst["conns"].items():
                if p == "DIN":
                    for b in range(4):
                        def_nets[f"sram_din[{b}]"].append((iname, f"DIN[{b}]"))
                elif p == "DO":
                    for b in range(4):
                        def_nets[f"sram_do[{b}]"].append((iname, f"DO[{b}]"))
                else:
                    def_nets[n].append((iname, p))
        else:
            for p, n in inst["conns"].items():
                if p not in OUTPUT_PIN_NAMES:
                    if n.startswith("clk_buf_r") and iname not in ANCHORS:
                        n = "clk_root"
                    elif n.startswith("rst_n_buf_r"):
                        n = "rst_n"
                    elif n in fobuf_drv:
                        n = fobuf_drv[n]
                def_nets[n].append((iname, p))
    lines.append(f"NETS {len(def_nets)} ;")
    for nname, nconns in sorted(def_nets.items()):
        c_str = " ".join(f"( {i} {p} )" for i, p in nconns)
        lines.append(f"  - {nname} {c_str} + USE SIGNAL ;")
    lines.append("END NETS")
    lines.append("END DESIGN")
    with open(gpl_in, "w") as f:
        f.write("\n".join(lines) + "\n")

    with open(gpl_tcl, "w") as f:
        f.write(f"""
read_lef "{TECH_LEF}"
read_lef "{CELLS_LEF}"
read_lef "{SRAM_LEF}"
read_def "{gpl_in}"
global_placement -density 0.52
write_def "{gpl_out}"
exit
""")
    subprocess.run(["/usr/local/bin/openroad", "-exit", gpl_tcl], check=True, stdout=subprocess.DEVNULL)
    with open(gpl_out, "r") as f:
        gpl_txt = f.read()

gpl_xy = {}
for m in re.finditer(
    r"^\s*-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)",
    gpl_txt,
    flags=re.MULTILINE,
):
    nm, ct, xd, yd = m.group(1), m.group(2), int(m.group(3)) / 1000.0, int(m.group(4)) / 1000.0
    if nm in inst_map and ct != "SRAM128":
        gpl_xy[nm] = (xd + 0.5 * inst_map[nm]["w"] * SITE_W, yd + 29.7)

# -------------------------------------------------------------------------
# 4. Lagrangian Relaxation Segment Legalization + Spatial Buffer Grouping
# -------------------------------------------------------------------------
seg_cap = {}
for r in range(NUM_ROWS):
    for s in range(3):
        if r == 10 and s == 1:
            seg_cap[(r, s)] = 95
        elif r == 10 and s == 0:
            seg_cap[(r, s)] = 98
        elif 2 <= r <= 8:
            seg_cap[(r, s)] = SEGMENTS[s][2] - 9   # >= 9 filler sites (3x FILL3 M2 feedthroughs!)
        else:
            seg_cap[(r, s)] = SEGMENTS[s][2] - 6   # 102..103 sites (>= 6 filler sites -> 0 FILL1!)

anchor_used = {(r, s): 0 for r in range(NUM_ROWS) for s in range(3)}
for aname, (ar, aseg, _) in ANCHORS.items():
    anchor_used[(ar, aseg)] += inst_map[aname]["w"]

buf_special = {
    inst["name"] for inst in insts
    if inst["name"].startswith("u_clk_buf_r")
    or inst["name"].startswith("u_rst_buf_r")
    or inst["name"].startswith("u_fobuf_")
}
core_movables = [
    inst["name"] for inst in insts
    if inst["type"] != "SRAM128" and inst["name"] not in ANCHORS and inst["name"] not in buf_special
]


def disp_cost(nm, r, s):
    gx, gy = gpl_xy[nm]
    x0, x1, _ = SEGMENTS[s]
    hw = 0.5 * inst_map[nm]["w"] * SITE_W
    cx = min(max(gx, x0 + hw), x1 - hw)
    dx = abs(gx - cx)
    dy = abs(gy - (ROW_YS[r] + 29.7))
    return dx + 1.15 * dy + 0.002 * (dx * dx + dy * dy)


prices = {(r, s): 0.0 for r in range(NUM_ROWS) for s in range(3)}
for _ in range(80):
    used = dict(anchor_used)
    for nm in core_movables:
        w = inst_map[nm]["w"]
        best_rs = min(
            [(r, s) for r in range(NUM_ROWS) for s in range(3)],
            key=lambda rs: disp_cost(nm, rs[0], rs[1]) + w * prices[rs],
        )
        used[best_rs] += w
    max_over = 0
    for rs in prices:
        over = used[rs] - (seg_cap[rs] - 4)
        max_over = max(max_over, over)
        prices[rs] = max(0.0, prices[rs] + 0.8 * over)
    if max_over <= 0:
        break

seg_used = dict(anchor_used)
seg_list = defaultdict(list)
for aname, (ar, aseg, _) in ANCHORS.items():
    seg_list[(ar, aseg)].append(aname)


def regret(nm):
    w = inst_map[nm]["w"]
    costs = sorted(disp_cost(nm, r, s) + w * prices[(r, s)] for r in range(NUM_ROWS) for s in range(3))
    return costs[1] - costs[0]


core_movables.sort(key=lambda nm: -regret(nm))
cell_seg = {}
for nm in core_movables:
    w = inst_map[nm]["w"]
    best_rs = min(
        [(r, s) for r in range(NUM_ROWS) for s in range(3) if seg_used[(r, s)] + w <= seg_cap[(r, s)] - 3],
        key=lambda rs: disp_cost(nm, rs[0], rs[1]) + 0.5 * w * prices[rs],
    )
    cell_seg[nm] = best_rs
    seg_list[best_rs].append(nm)
    seg_used[best_rs] += w


def rewire_spatial_buffers(coord_map):
    # 1) Wire the 50 non-anchored internal FFs to u_clk_buf_r1..7 spatially (<= 8 sinks per buffer)
    internal_ffs = [
        inst for inst in insts
        if inst["type"] in ("DFFRB", "MUXDFFRB", "DFFS", "EDFFRB") and inst["name"] not in ANCHORS
    ]
    internal_ffs.sort(key=lambda inst: (round(coord_map[inst["name"]][1] / 250.0), coord_map[inst["name"]][0]))
    ff_chunks = [8, 8, 7, 7, 7, 7, 6]
    idx_ff = 0
    centroids = {}
    for b_i, csz in enumerate(ff_chunks):
        bname = f"u_clk_buf_r{b_i+1}"
        cnet = f"clk_buf_r{b_i+1}"
        grp = internal_ffs[idx_ff : idx_ff + csz]
        idx_ff += csz
        for ff in grp:
            ff["conns"]["CK"] = cnet
        pts = [coord_map[ff["name"]] for ff in grp]
        if b_i == 6:
            pts.append(coord_map["u_clk_sram_lat1"])
        centroids[bname] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    # 2) Wire reset sinks to u_rst_buf_r1..8 spatially (<= 9 sinks per buffer)
    rst_buf_names = {f"u_rst_buf_r{i+1}" for i in range(8)}
    rst_buf_nets = {f"rst_n_buf_r{i+1}" for i in range(8)}
    rst_sinks = []
    for inst in insts:
        if inst["name"] in rst_buf_names:
            continue
        for p, n in inst["conns"].items():
            if p not in OUTPUT_PIN_NAMES and n in rst_buf_nets:
                sx, sy = coord_map.get(inst["name"], (920.0, 745.2))
                rst_sinks.append((sy, sx, inst, p))
    rst_sinks.sort(key=lambda item: (round(item[0] / 300.0), item[1]))
    rst_chunk = (len(rst_sinks) + 7) // 8
    assert rst_chunk <= 10, f"Reset chunk {rst_chunk} > 10"
    for g_i in range(8):
        bname = f"u_rst_buf_r{g_i+1}"
        bnet = f"rst_n_buf_r{g_i+1}"
        grp = rst_sinks[g_i * rst_chunk : (g_i + 1) * rst_chunk]
        for _, _, s_inst, s_pin in grp:
            s_inst["conns"][s_pin] = bnet
        centroids[bname] = (sum(x[1] for x in grp) / len(grp), sum(x[0] for x in grp) / len(grp))

    # 3) Wire u_fobuf_* high-fanout sinks spatially
    fobuf_by_drv = defaultdict(list)
    for inst in insts:
        if inst["name"].startswith("u_fobuf_"):
            fobuf_by_drv[inst["conns"]["A"]].append(inst)

    for drv_net, buf_list in fobuf_by_drv.items():
        b_nets = {b["conns"]["Y"] for b in buf_list}
        sinks = []
        for inst in insts:
            if inst["type"] == "SRAM128" or inst["name"] in buf_special:
                continue
            for p, n in inst["conns"].items():
                if p not in OUTPUT_PIN_NAMES and n in b_nets:
                    sx, sy = coord_map.get(inst["name"], (920.0, 745.2))
                    sinks.append((sx, sy, inst, p))
        sinks.sort(key=lambda item: (round(item[1] / 500.0), item[0]))
        csz = (len(sinks) + len(buf_list) - 1) // len(buf_list)
        for g_idx, b_inst in enumerate(buf_list):
            b_net = b_inst["conns"]["Y"]
            grp = sinks[g_idx * csz : (g_idx + 1) * csz]
            if grp:
                for _, _, s_inst, s_pin in grp:
                    s_inst["conns"][s_pin] = b_net
                centroids[b_inst["name"]] = (sum(x[0] for x in grp) / len(grp), sum(x[1] for x in grp) / len(grp))
    return centroids


approx_xy = {}
for r in range(NUM_ROWS):
    for s in range(3):
        x0, x1, _ = SEGMENTS[s]
        ordered = sorted(seg_list[(r, s)], key=lambda nm: ANCHORS[nm][2] if nm in ANCHORS else gpl_xy[nm][0])
        for idx_i, nm in enumerate(ordered):
            fx = ANCHORS[nm][2] if nm in ANCHORS else x0 + (x1 - x0) * (idx_i + 0.5) / max(1, len(ordered))
            approx_xy[nm] = (fx, ROW_YS[r] + 29.7)

buf_centroids = rewire_spatial_buffers(approx_xy)
for bname, cxy in buf_centroids.items():
    gpl_xy[bname] = cxy

for bname in sorted(buf_special):
    w = inst_map[bname]["w"]
    best_rs = min(
        [(r, s) for r in range(NUM_ROWS) for s in range(3) if seg_used[(r, s)] + w <= seg_cap[(r, s)]],
        key=lambda rs: disp_cost(bname, rs[0], rs[1]),
    )
    cell_seg[bname] = best_rs
    seg_list[best_rs].append(bname)
    seg_used[best_rs] += w

movables = core_movables + sorted(buf_special)

for r in range(NUM_ROWS):
    for s in range(3):
        seg_list[(r, s)].sort(key=lambda nm: ANCHORS[nm][2] if nm in ANCHORS else gpl_xy[nm][0])


# -------------------------------------------------------------------------
# 5. Simulated Annealing + 2nd-Pass Buffer Re-Grouping + Greedy HPWL Polish
# -------------------------------------------------------------------------
def build_net_structures():
    nets = defaultdict(list)
    for pname in pin_xy:
        nets[pname].append(("PIN", pname))
    for inst in insts:
        iname = inst["name"]
        if inst["type"] == "SRAM128":
            for p, n in inst["conns"].items():
                if p == "DIN":
                    for b in range(4):
                        nets[f"sram_din[{b}]"].append(("SRAM", f"DIN[{b}]"))
                elif p == "DO":
                    for b in range(4):
                        nets[f"sram_do[{b}]"].append(("SRAM", f"DO[{b}]"))
                else:
                    nets[n].append(("SRAM", p))
        else:
            for p, n in inst["conns"].items():
                nets[n].append(("INST", iname))
    inst_nets = defaultdict(list)
    for nname, terms in nets.items():
        if len(terms) >= 2:
            for kind, ref in terms:
                if kind == "INST":
                    inst_nets[ref].append(nname)
    return nets, inst_nets


def update_segment_positions(r, s, pos):
    cy = ROW_YS[r] + 29.7
    x_start, _, cap = SEGMENTS[s]
    names = seg_list[(r, s)]
    gap_sites = cap - seg_used[(r, s)]
    west_locked = [nm for nm in names if nm in WEST_EDGE_LOCKED]
    east_locked = [nm for nm in names if nm in EAST_EDGE_LOCKED]
    west_locked.sort(key=lambda nm: ANCHORS[nm][2])
    east_locked.sort(key=lambda nm: ANCHORS[nm][2])
    mid = [nm for nm in names if nm not in EDGE_LOCKED]

    cur_site = 0
    for nm in west_locked:
        w = inst_map[nm]["w"]
        pos[nm] = (x_start + (cur_site + 0.5 * w) * SITE_W, cy)
        cur_site += w

    east_sites = sum(inst_map[nm]["w"] for nm in east_locked)
    for idx_m, nm in enumerate(mid):
        w = inst_map[nm]["w"]
        extra = (gap_sites * (idx_m + 1)) // (len(mid) + 1) - (gap_sites * idx_m) // (len(mid) + 1)
        cur_site += extra
        pos[nm] = (x_start + (cur_site + 0.5 * w) * SITE_W, cy)
        cur_site += w

    cur_site = cap - east_sites
    for nm in east_locked:
        w = inst_map[nm]["w"]
        pos[nm] = (x_start + (cur_site + 0.5 * w) * SITE_W, cy)
        cur_site += w


pos = {}
for r in range(NUM_ROWS):
    for s in range(3):
        update_segment_positions(r, s, pos)


def run_sa_optimization(nets, inst_nets, n_steps, t_init, seed=42):
    def net_hpwl(nname):
        xs, ys = [], []
        for kind, ref in nets[nname]:
            if kind == "PIN":
                x, y = pin_xy[ref]
            elif kind == "SRAM":
                x, y = sram_pin_xy.get(ref, (920.0, 1714.6))
            else:
                x, y = pos[ref]
            xs.append(x)
            ys.append(y)
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    def affected_hpwl(seg_pairs):
        nset = set()
        for r, s in seg_pairs:
            for nm in seg_list[(r, s)]:
                for nn in inst_nets[nm]:
                    nset.add(nn)
        return sum(net_hpwl(nn) for nn in nset), nset

    rng = random.Random(seed)
    all_rs = [(r, s) for r in range(NUM_ROWS) for s in range(3)]
    for step in range(n_steps):
        T = t_init * ((1.0 - step / (0.65 * n_steps)) ** 2) if (t_init > 0.0 and step < 0.65 * n_steps) else 0.0
        mv = rng.random()
        if mv < 0.35:
            nm = rng.choice(movables)
            r1, s1 = cell_seg[nm]
            if rng.random() < 0.3:
                r2, s2 = rng.choice(all_rs)
            else:
                r2 = max(0, min(NUM_ROWS - 1, r1 + rng.choice([-2, -1, 0, 1, 2])))
                s2 = max(0, min(2, s1 + rng.choice([-1, 0, 1])))
            if (r1, s1) == (r2, s2):
                continue
            w = inst_map[nm]["w"]
            if seg_used[(r2, s2)] + w > seg_cap[(r2, s2)]:
                continue
            old_h, nset = affected_hpwl([(r1, s1), (r2, s2)])
            old_l1, old_l2 = list(seg_list[(r1, s1)]), list(seg_list[(r2, s2)])
            seg_list[(r1, s1)].remove(nm)
            seg_list[(r2, s2)].insert(rng.randint(0, len(seg_list[(r2, s2)])), nm)
            seg_used[(r1, s1)] -= w
            seg_used[(r2, s2)] += w
            update_segment_positions(r1, s1, pos)
            update_segment_positions(r2, s2, pos)
            dh = sum(net_hpwl(nn) for nn in nset) - old_h
            if dh <= 0.0 or (T > 0.0 and rng.random() < math.exp(-dh / T)):
                cell_seg[nm] = (r2, s2)
            else:
                seg_list[(r1, s1)], seg_list[(r2, s2)] = old_l1, old_l2
                seg_used[(r1, s1)] += w
                seg_used[(r2, s2)] -= w
                update_segment_positions(r1, s1, pos)
                update_segment_positions(r2, s2, pos)
        elif mv < 0.72:
            nm1 = rng.choice(movables)
            r1, s1 = cell_seg[nm1]
            if rng.random() < 0.3:
                r2, s2 = rng.choice(all_rs)
            else:
                r2 = max(0, min(NUM_ROWS - 1, r1 + rng.choice([-2, -1, 0, 1, 2])))
                s2 = max(0, min(2, s1 + rng.choice([-1, 0, 1])))
            if (r1, s1) == (r2, s2):
                continue
            cand2 = [x for x in seg_list[(r2, s2)] if x not in ANCHORS]
            if not cand2:
                continue
            nm2 = rng.choice(cand2)
            w1, w2 = inst_map[nm1]["w"], inst_map[nm2]["w"]
            if seg_used[(r1, s1)] - w1 + w2 > seg_cap[(r1, s1)] or seg_used[(r2, s2)] - w2 + w1 > seg_cap[(r2, s2)]:
                continue
            old_h, nset = affected_hpwl([(r1, s1), (r2, s2)])
            old_l1, old_l2 = list(seg_list[(r1, s1)]), list(seg_list[(r2, s2)])
            i1, i2 = seg_list[(r1, s1)].index(nm1), seg_list[(r2, s2)].index(nm2)
            seg_list[(r1, s1)][i1] = nm2
            seg_list[(r2, s2)][i2] = nm1
            seg_used[(r1, s1)] += (w2 - w1)
            seg_used[(r2, s2)] += (w1 - w2)
            update_segment_positions(r1, s1, pos)
            update_segment_positions(r2, s2, pos)
            dh = sum(net_hpwl(nn) for nn in nset) - old_h
            if dh <= 0.0 or (T > 0.0 and rng.random() < math.exp(-dh / T)):
                cell_seg[nm1] = (r2, s2)
                cell_seg[nm2] = (r1, s1)
            else:
                seg_list[(r1, s1)], seg_list[(r2, s2)] = old_l1, old_l2
                seg_used[(r1, s1)] -= (w2 - w1)
                seg_used[(r2, s2)] -= (w1 - w2)
                update_segment_positions(r1, s1, pos)
                update_segment_positions(r2, s2, pos)
        else:
            # Intra-segment ordering swap (non-edge-locked cells can align directly under North/South/SRAM128 pins!)
            r1, s1 = rng.choice(all_rs)
            lst = seg_list[(r1, s1)]
            if len(lst) < 2:
                continue
            i1, i2 = rng.sample(range(len(lst)), 2)
            if lst[i1] in EDGE_LOCKED or lst[i2] in EDGE_LOCKED:
                continue
            old_h, nset = affected_hpwl([(r1, s1)])
            lst[i1], lst[i2] = lst[i2], lst[i1]
            update_segment_positions(r1, s1, pos)
            dh = sum(net_hpwl(nn) for nn in nset) - old_h
            if not (dh <= 0.0 or (T > 0.0 and rng.random() < math.exp(-dh / T))):
                lst[i1], lst[i2] = lst[i2], lst[i1]
                update_segment_positions(r1, s1, pos)

    return sum(net_hpwl(nn) for nn, terms in nets.items() if len(terms) >= 2)


nets, inst_nets = build_net_structures()
hpwl_pass1 = run_sa_optimization(nets, inst_nets, n_steps=80000, t_init=45.0, seed=42)
print(f"Pass-1 SA legalized center-HPWL: {hpwl_pass1:.1f} um")

# Pass 2: Re-cluster spatial clock/reset/high-FO buffers to post-SA cell locations & run final greedy polish!
rewire_spatial_buffers(pos)
nets, inst_nets = build_net_structures()
hpwl_pass2 = run_sa_optimization(nets, inst_nets, n_steps=35000, t_init=8.0, seed=101)
print(f"Pass-2 post-buffer-rewire legalized center-HPWL: {hpwl_pass2:.1f} um")

# Save updated spatial netlist to c4004_core_syn.v & ff_row_map.json
ff_row_map = {}
for r in range(NUM_ROWS):
    for s in range(3):
        for nm in seg_list[(r, s)]:
            if inst_map[nm]["type"] in ("DFFRB", "MUXDFFRB", "DFFS", "EDFFRB", "BUFTH") or nm in buf_special:
                ff_row_map[nm] = r
with open(ROW_MAP_JSON, "w") as f:
    json.dump(ff_row_map, f, indent=2)

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
all_used_nets = {net for inst in insts for net in inst["conns"].values()}
scalar_wires = sorted(all_used_nets - port_and_bus_nets)

v_out = [
    "// Synthesized and Buffered Gate-Level Netlist for c4004_core (Plan B + Full MCS-4 Spec)",
    "module c4004_core (",
    "  clk, rst, test, d_in, d_out, d_oe, d_hiz, sync, cm_rom, cm_ram",
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
    v_out.append(f"  wire {w};")
v_out.append("")
for inst in insts:
    c_strs = [f".{k}({v})" for k, v in inst["conns"].items()]
    v_out.append(f"  {inst['type']} {inst['name']} ( " + ", ".join(c_strs) + " );")
v_out.append("endmodule\n")
with open(SYN_V, "w") as f:
    f.write("\n".join(v_out))
print("Updated spatial clock/reset/high-FO assignment in c4004_core_syn.v")

# -------------------------------------------------------------------------
# 6. Decompose Remaining Gaps into FILL3 / FILL2 (0 FILL1!) & Write DEF
# -------------------------------------------------------------------------
FREE_M2_BY_TYPE = {
    "MUXDFFRB": 11, "DFFRB": 7, "DFFS": 7, "DFF": 8, "EDFFRB": 12,
    "BUFTH": 4, "DEL1": 4, "MUX2": 2, "XOR2": 2, "XNOR2": 2,
    "AND2_X1": 1, "AND3_X1": 1, "AND4_X1": 1,
    "OR2": 1, "OR3": 1, "OR4": 1,
    "BUF_X1": 1, "BUF_X2": 1,
    "FILL3": 3, "FILL2": 2, "FILL1": 1,
}


def decompose_fillers(gap_sites):
    assert gap_sites != 1 and gap_sites >= 2, f"Illegal gap {gap_sites}: FILL1 forbidden!"
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


placed_components = []
placed_components.append(("u_sram", "SRAM128", "FIXED", round(SRAM_X * DBU), round(SRAM_Y * DBU), "N"))

tap2_count = 0
for r in range(NUM_ROWS):
    ry = round(ROW_YS[r] * DBU)
    for c_idx, tx in enumerate(TAP_XS):
        placed_components.append((f"u_tap2_r{r}_c{c_idx}", "TAP2", "FIXED", round(tx * DBU), ry, "N"))
        tap2_count += 1

fill3_count = 0
fill2_count = 0

for r in range(NUM_ROWS):
    ry = round(ROW_YS[r] * DBU)
    for s in range(3):
        x_start, _, cap = SEGMENTS[s]
        names = seg_list[(r, s)]
        west_locked = sorted([nm for nm in names if nm in WEST_EDGE_LOCKED], key=lambda nm: ANCHORS[nm][2])
        east_locked = sorted([nm for nm in names if nm in EAST_EDGE_LOCKED], key=lambda nm: ANCHORS[nm][2])
        mid = [nm for nm in names if nm not in EDGE_LOCKED]
        ordered_names = west_locked + mid + east_locked

        gap = cap - seg_used[(r, s)]
        fillers = decompose_fillers(gap)
        merged_items = [("CELL", inst_map[nm]) for nm in ordered_names]

        min_ins = len(west_locked)
        max_ins = len(merged_items) - len(east_locked)

        # Insert FILL3 / FILL2 evenly & preferentially inside zero-M2-feedthrough cell runs
        for f_idx_ins, f_obj in enumerate(fillers):
            best_len = -1
            best_ins = min_ins + ((max_ins - min_ins) * (f_idx_ins + 1)) // (len(fillers) + 1)
            cur_run_sites = 0
            run_start = min_ins
            for idx_m in range(min_ins, max_ins):
                kind, obj = merged_items[idx_m]
                if kind == "CELL" and FREE_M2_BY_TYPE.get(obj["type"], 0) == 0:
                    if cur_run_sites == 0:
                        run_start = idx_m
                    cur_run_sites += obj["w"]
                    if cur_run_sites > best_len:
                        best_len = cur_run_sites
                        best_ins = (run_start + idx_m + 1) // 2
                else:
                    cur_run_sites = 0
            best_ins = max(min_ins, min(max_ins, best_ins))
            merged_items.insert(best_ins, ("FILL", f_obj))
            max_ins += 1

        cur_site = 0
        f_idx = 0
        for kind, obj in merged_items:
            if kind == "CELL":
                cx_dbu = round((x_start + cur_site * SITE_W) * DBU)
                placed_components.append((obj["name"], obj["type"], "PLACED", cx_dbu, ry, "N"))
                cur_site += obj["w"]
            else:
                ftype, fw = obj
                fx_dbu = round((x_start + cur_site * SITE_W) * DBU)
                placed_components.append((f"u_fill_r{r}_s{s}_{f_idx}", ftype, "FIXED", fx_dbu, ry, "N"))
                cur_site += fw
                if ftype == "FILL3":
                    fill3_count += 1
                else:
                    fill2_count += 1
                f_idx += 1
        assert cur_site == cap, f"Segment ({r}, {s}) site count {cur_site} != {cap}"

print(
    f"Placement complete: {len(insts)} logic/macro cells + {tap2_count} TAP2 + "
    f"{fill3_count} FILL3 + {fill2_count} FILL2 (0 FILL1!) = {len(placed_components)} total components"
)

def_lines = [
    "VERSION 5.8 ;",
    'DIVIDERCHAR "/" ;',
    'BUSBITCHARS "[]" ;',
    "DESIGN c4004_core ;",
    "UNITS DISTANCE MICRONS 1000 ;",
    "DIEAREA ( 0 0 ) ( 1840000 1840000 ) ;",
    "",
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
    def_lines.append("    + PORT")
    def_lines.append(f"      + LAYER {player} ( {dx1} {dy1} ) ( {dx2} {dy2} )")
    def_lines.append(f"      + FIXED ( {cx} {cy} ) N ;")
def_lines.append("END PINS")
def_lines.append("")

blockages = [
    ("METAL1",       0,       0,   31400, 1840000),
    ("METAL2",       0,       0,   31400, 1840000),
    ("METAL1", 1810000,       0, 1840000, 1840000),
    ("METAL2", 1810000,       0, 1840000, 1840000),
    ("METAL1",       0,       0, 1840000,    9000),
    ("METAL2",       0,       0, 1840000,    9000),
    ("METAL1",       0, 1816000, 1840000, 1840000),
    ("METAL2",       0, 1816000, 1840000, 1840000),
    ("METAL2",  616600,       0,  625400, 1546000),
    ("METAL2", 1216000,       0, 1224800, 1546000),
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
