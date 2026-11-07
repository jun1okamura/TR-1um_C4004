#!/usr/bin/env python3
import re, heapq
from collections import defaultdict
from pathlib import Path

OR_DIR = str(Path(__file__).resolve().parent.parent / "openroad"
def_path = f"{OR_DIR}/routed_tap2.def"
def_txt = open(def_path).read()
lef_txt = open(f"{OR_DIR}/TR-1um_cells_m2only.lef").read()

N = 340
ROW_YS = [59400, 237600, 415800, 594000, 772200, 950400, 1128600, 1306800, 1485000]
TAP_XS = [21600, 615600, 1215000, 1809000]
m1_wire_occ, m1_via_occ, m2_occ = defaultdict(set), defaultdict(set), defaultdict(set)
m1_blocked_j = {j for j in range(N) if any(ry + 1100 - 3500 < 2700 + j*5400 < ry + 58300 + 3500 for ry in ROW_YS)}
sram_m1_obs = (334800, 1596000, 1500900, 1781600)

def mark_box(occ, x0, y0, x1, y1, net, rx, ry):
    px, py = rx + 1800, ry + 1800
    i0 = max(0, (x0 - px - 2700) // 5400 + 1)
    i1 = min(N - 1, (x1 + px - 1 - 2700) // 5400)
    j0 = max(0, (y0 - py - 2700) // 5400 + 1)
    j1 = min(N - 1, (y1 + py - 1 - 2700) // 5400)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            occ[(i, j)].add(net)

mark_box(m1_wire_occ, *sram_m1_obs, "INST:u_sram", 900, 900)
mark_box(m1_via_occ,  *sram_m1_obs, "INST:u_sram", 1700, 1700)
mark_box(m2_occ,      *sram_m1_obs, "INST:u_sram", 1700, 1700)
for sy0, sy1 in ((1596000, 1604800), (1772800, 1781600)):
    mark_box(m1_wire_occ, 1497500, sy0, 1835000, sy1, "PWR_SRAM_M1", 900, 900)
    mark_box(m1_via_occ,  1497500, sy0, 1835000, sy1, "PWR_SRAM_M1", 1700, 1700)

for tx in TAP_XS:
    mark_box(m2_occ, tx + 1000, 60500, tx + 9800, 1543300, f"TAP2:{tx}", 1700, 1700)
    mark_box(m1_via_occ, tx + 1000, 60500, tx + 9800, 1543300, f"TAP2:{tx}", 1700, 1700)

macro_pin_m2 = defaultdict(lambda: defaultdict(list))
macro_obs_m2 = defaultdict(list)
for m in re.finditer(r"MACRO\s+(\S+)(.*?)END\s+\1", lef_txt, re.S):
    mname, body = m.group(1), m.group(2)
    for pm in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", body, re.S):
        pname, pbody = pm.group(1), pm.group(2)
        for lm in re.finditer(r"LAYER\s+METAL2\s*;\s*((?:RECT\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s*;\s*)+)", pbody):
            for rm in re.finditer(r"RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", lm.group(1)):
                macro_pin_m2[mname][pname].append(tuple(int(round(float(rm.group(k))*1000)) for k in range(1, 5)))
    obs_m = re.search(r"OBS\s+(.*?)END", body, re.S)
    if obs_m:
        for lm in re.finditer(r"LAYER\s+METAL2\s*;\s*((?:RECT\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s*;\s*)+)", obs_m.group(1)):
            for rm in re.finditer(r"RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", lm.group(1)):
                macro_obs_m2[mname].append(tuple(int(round(float(rm.group(k))*1000)) for k in range(1, 5)))

inst_pin_net = {}
net_cell_pins = defaultdict(list)
nets_sec = def_txt.split("NETS")[1].split("END NETS")[0]
for nm in re.finditer(r"-\s+(\S+)\s+(.*?)\+\s+USE", nets_sec, re.S):
    nname = nm.group(1)
    for inst, pin in re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", nm.group(2)):
        if inst != "PIN":
            inst_pin_net[(inst, pin)] = nname
            net_cell_pins[nname].append((inst, pin))

# Move u_inv_doe from (712800, 594000) (where s=133 conflicts with _0287_) to (918000, 59400) in Row 1:
def_txt = def_txt.replace(
    "- u_inv_doe INV_X2 + PLACED ( 712800 594000 ) N ;",
    "- u_inv_doe INV_X2 + PLACED ( 918000 59400 ) N ;"
)

comp_sec = def_txt.split("COMPONENTS")[1].split("END COMPONENTS")[0]
inst_pos = {}
inst_cell = {}
for m in re.finditer(r"-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)", comp_sec):
    inst, cell, cx, cy = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    inst_pos[inst] = (cx, cy)
    inst_cell[inst] = cell
    for pname, rects in macro_pin_m2[cell].items():
        owner = inst_pin_net.get((inst, pname), f"INST:{inst}:{pname}")
        for x0, y0, x1, y1 in rects:
            mark_box(m2_occ, cx+x0, cy+y0, cx+x1, cy+y1, owner, 1700, 1700)
    for x0, y0, x1, y1 in macro_obs_m2[cell]:
        mark_box(m2_occ, cx+x0, cy+y0, cx+x1, cy+y1, f"OBS:{inst}", 1700, 1700)

# Reserve power / tie tracks:
for i in range(338, N):
    for j in list(range(0, 187)) + list(range(274, N)):
        m2_occ[(i, j)].add("PWR_RIGHT")
        m1_via_occ[(i, j)].add("PWR_RIGHT")
for ry in ROW_YS:
    if ry not in (1128600, 1306800):
        mark_box(m1_wire_occ, 1809000, ry + 1100, 1835000, ry + 3700, "PWR_RIGHT_M1", 900, 900)
        mark_box(m1_via_occ,  1809000, ry + 1100, 1835000, ry + 3700, "PWR_RIGHT_M1", 1700, 1700)
        mark_box(m1_wire_occ, 1809000, ry + 55700, 1829600, ry + 58300, "PWR_RIGHT_M1", 900, 900)
        mark_box(m1_via_occ,  1809000, ry + 55700, 1829600, ry + 58300, "PWR_RIGHT_M1", 1700, 1700)
# Top M1 VDD bus at j >= 336 (y >= 1816000)
for i in range(N):
    for j in range(336, N):
        m1_wire_occ[(i, j)].add("PWR_TOP")
        m1_via_occ[(i, j)].add("PWR_TOP")
# Bottom VDD tie tracks:
# HIZ7 (x=340000): TAP2 col 0 VDD M2 at i=5 (x=29700) down to j=2 (y=13500), M1 at j=2 (i=5..63), M2 at i=63 (j=0..2)
for j in range(0, 12):
    m2_occ[(5, j)].add("PWR_BOT_HIZ7")
for i in range(5, 64):
    m1_wire_occ[(i, 2)].add("PWR_BOT_HIZ7")
    m1_via_occ[(i, 2)].add("PWR_BOT_HIZ7")
for j in range(0, 3):
    m2_occ[(63, j)].add("PWR_BOT_HIZ7")
    m1_via_occ[(63, j)].add("PWR_BOT_HIZ7")
# HIZ10 (x=1500000): free vertical M2 column i=276 (x=1493100) for j=0..22
for j in range(0, 23):
    m2_occ[(276, j)].add("PWR_BOT_HIZ10")
    m1_via_occ[(276, j)].add("PWR_BOT_HIZ10")
# Left vertical M2 trunk at i=1 (x=8100) for d_hiz (j=62..279)
for j in range(62, 279):
    m2_occ[(1, j)].add("d_hiz")
    m1_via_occ[(1, j)].add("d_hiz")

b_nets_full_ripup = {
    "test", "sync", "d_oe", "_0037_",
    "cm_ram[0]", "cm_ram[1]", "cm_ram[2]"
}

partial_ripup = {
    "rst": [
        ("METAL2", 288900, 1700, 288900, 13500),
        ("METAL1", 288900, 13500, 299700, 13500),
        ("METAL2", 299700, 2700, 299700, 13500),
        ("METAL1", 299700, 2700, 683100, 2700),
        ("METAL2", 683100, 2700, 683100, 24300),
    ],
    "_0321_": [
        ("METAL2", 926100, 45900, 926100, 137700),
    ],
    "cyc2": [
        ("METAL1", 94500, 1066500, 207900, 1066500),
        ("METAL2", 207900, 1066500, 207900, 1217700),
        ("METAL1", 180900, 1217700, 207900, 1217700),
        ("METAL2", 180900, 1158300, 180900, 1217700),
    ],
    "_0274_": [
        ("METAL1", 818100, 1098900, 855900, 1098900),
        ("METAL2", 855900, 1098900, 855900, 1223100),
        ("METAL1", 845100, 1223100, 855900, 1223100),
    ],
    "_0390_": [
        ("METAL1", 1309500, 1088100, 1363500, 1088100),
        ("METAL2", 1309500, 1088100, 1309500, 1271700),
        ("METAL1", 1282500, 1271700, 1309500, 1271700),
        ("METAL2", 1293300, 1093500, 1293300, 1104300),
        ("METAL1", 1293300, 1104300, 1309500, 1104300),
    ],
    "n_0125_bf1": [
        ("METAL1", 1244700, 877500, 1287900, 877500),
        ("METAL2", 1287900, 877500, 1287900, 1120500),
        ("METAL1", 1185300, 1120500, 1287900, 1120500),
    ],
    "_0077_": [
        ("METAL1", 1142100, 1190700, 1563300, 1190700),
    ],
    "cm_ram[3]": [
        ("METAL1", 1833300, 1401300, 1839100, 1401300),
    ],
    "cm_rom": [
        ("METAL2", 1557900, 1833300, 1557900, 1838300),
        ("METAL1", 1557900, 1833300, 1568700, 1833300),
        ("METAL2", 1568700, 1476900, 1568700, 1833300),
    ],
    "clk": [
        ("METAL2", 299700, 1827900, 299700, 1838300),
        ("METAL1", 299700, 1827900, 1655100, 1827900),
        ("METAL2", 1655100, 1271700, 1655100, 1827900),
    ],
    "d_hiz": [
        ("METAL1", 56700, 710100, 715500, 710100),
        ("METAL2", 56700, 710100, 56700, 888300),
        ("METAL1", 900, 888300, 56700, 888300),
    ],
    "d_in[0]": [
        ("METAL1", 900, 332100, 2700, 332100),
        ("METAL2", 2700, 332100, 2700, 526500),
    ],
    "d_in[1]": [
        ("METAL1", 900, 688500, 2700, 688500),
        ("METAL2", 2700, 688500, 2700, 715500),
    ],
    "d_in[2]": [
        ("METAL1", 900, 1044900, 72900, 1044900),
        ("METAL2", 72900, 877500, 72900, 1044900),
        ("METAL1", 72900, 877500, 456300, 877500),
    ],
    "d_in[3]": [
        ("METAL1", 900, 1401300, 2700, 1401300),
        ("METAL2", 2700, 1077300, 2700, 1401300),
    ],
    "d_out[0]": [
        ("METAL1", 900, 353700, 8100, 353700),
        ("METAL2", 8100, 353700, 8100, 899100),
        ("METAL1", 8100, 899100, 429300, 899100),
    ],
    "d_out[1]": [
        ("METAL1", 900, 710100, 13500, 710100),
        ("METAL2", 13500, 710100, 13500, 720900),
        ("METAL1", 13500, 720900, 229500, 720900),
    ],
    "d_out[2]": [
        ("METAL1", 900, 1066500, 2700, 1066500),
        ("METAL2", 2700, 1066500, 2700, 1071900),
    ],
    "d_out[3]": [
        ("METAL1", 900, 1422900, 8100, 1422900),
        ("METAL2", 8100, 1266300, 8100, 1422900),
        ("METAL1", 8100, 1266300, 391500, 1266300),
    ],
}

net_segs = defaultdict(list)
net_vias = defaultdict(list)
for nm in re.finditer(r"-\s+(\S+)\s+.*?;", nets_sec, re.S):
    nname = nm.group(1)
    if nname in b_nets_full_ripup:
        continue
    rset = set(partial_ripup.get(nname, []))
    for sm in re.finditer(r"(METAL1|METAL2)\s+\(\s*(\d+)\s+(\d+)(?:\s+\d+)?\s*\)\s+\(\s*(\*|\d+)\s+(\*|\d+)", nm.group(0)):
        ly, x1, y1, x2s, y2s = sm.group(1), int(sm.group(2)), int(sm.group(3)), sm.group(4), sm.group(5)
        x2, y2 = (x1 if x2s == "*" else int(x2s)), (y1 if y2s == "*" else int(y2s))
        xlo, xhi, ylo, yhi = min(x1,x2), max(x1,x2), min(y1,y2), max(y1,y2)
        if (ly, xlo, ylo, xhi, yhi) in rset:
            continue
        if nname in ("d_in[0]", "d_in[1]", "d_in[3]", "d_out[2]") and ly == "METAL1" and xlo == 2700 and xhi > 13500:
            xlo = 13500
        net_segs[nname].append((1 if ly == "METAL1" else 2, xlo, ylo, xhi, yhi))
        if ly == "METAL1":
            mark_box(m1_wire_occ, xlo - 900, ylo - 900, xhi + 900, yhi + 900, nname, 900, 900)
            mark_box(m1_via_occ,  xlo - 900, ylo - 900, xhi + 900, yhi + 900, nname, 900, 900)
        else:
            mark_box(m2_occ, xlo - 1700, ylo - 1700, xhi + 1700, yhi + 1700, nname, 1700, 1700)
    for vm in re.finditer(r"METAL1\s+\(\s*(\d+)\s+(\d+)\s*\)\s+V1_1x1", nm.group(0)):
        vx, vy = int(vm.group(1)), int(vm.group(2))
        has_m1 = any(sly == 1 and x0 <= vx <= x1 and y0 <= vy <= y1 for (sly, x0, y0, x1, y1) in net_segs[nname])
        has_m2 = any(sly == 2 and x0 <= vx <= x1 and y0 <= vy <= y1 for (sly, x0, y0, x1, y1) in net_segs[nname])
        if (any(x0 <= vx <= x1 and y0 <= vy <= y1 for (_, x0, y0, x1, y1) in rset) or (nname in ("d_in[0]", "d_in[1]", "d_in[3]", "d_out[2]") and vx == 2700)) and not (has_m1 and has_m2):
            continue
        net_vias[nname].append((vx, vy))
        mark_box(m1_wire_occ, vx - 1700, vy - 1700, vx + 1700, vy + 1700, nname, 900, 900)
        mark_box(m1_via_occ,  vx - 1700, vy - 1700, vx + 1700, vy + 1700, nname, 900, 900)

def get_component_nodes(net, seed_xy):
    segs = net_segs[net]
    vias = net_vias[net]
    sx, sy = seed_xy
    vis_seg = set()
    q = [idx for idx, (_, x0, y0, x1, y1) in enumerate(segs) if x0 - 500 <= sx <= x1 + 500 and y0 - 500 <= sy <= y1 + 500]
    vis_seg.update(q)
    while q:
        u = q.pop()
        ly_a, ax0, ay0, ax1, ay1 = segs[u]
        for v, (ly_b, bx0, by0, bx1, by1) in enumerate(segs):
            if v in vis_seg:
                continue
            if ly_a == ly_b:
                conn = not (ax1 + 500 < bx0 or bx1 + 500 < ax0 or ay1 + 500 < by0 or by1 + 500 < ay0)
            else:
                conn = any(ax0 - 500 <= vx <= ax1 + 500 and ay0 - 500 <= vy <= ay1 + 500 and bx0 - 500 <= vx <= bx1 + 500 and by0 - 500 <= vy <= by1 + 500 for (vx, vy) in vias)
            if conn:
                vis_seg.add(v)
                q.append(v)
    nodes = set()
    for u in vis_seg:
        ly, x0, y0, x1, y1 = segs[u]
        if ly == 1 and (y0 - 2700) % 5400 == 0:
            j = (y0 - 2700) // 5400
            if j not in m1_blocked_j:
                for x in range(x0, x1 + 1, 5400):
                    if (x - 2700) % 5400 == 0:
                        i = (x - 2700) // 5400
                        nodes.add((1, i, j))
        elif ly == 2 and (x0 - 2700) % 5400 == 0:
            i = (x0 - 2700) // 5400
            j0 = max(0, round((y0 - 2700) / 5400))
            j1 = min(N - 1, round((y1 - 2700) / 5400))
            for j in range(j0, j1 + 1):
                nodes.add((2, i, j))
    return nodes

def dijkstra_multi(net, s_nodes, t_nodes, min_i=2, max_i=337, min_j=1, max_j=334):
    pq = [(0, ly, i, j) for (ly, i, j) in s_nodes]
    heapq.heapify(pq)
    dist = {node: 0 for node in s_nodes}
    parent = {}
    while pq:
        d, ly, i, j = heapq.heappop(pq)
        if (ly, i, j) in t_nodes:
            path = []
            cur = (ly, i, j)
            while cur in parent:
                path.append(cur)
                cur = parent[cur]
            path.append(cur)
            return list(reversed(path))
        if d > dist.get((ly, i, j), 1e18): continue
        if ly == 1:
            for ni in (i-1, i+1):
                if min_i <= ni <= max_i and j not in m1_blocked_j and not (m1_wire_occ.get((ni,j),set()) - {net}):
                    nd = d + 1
                    if nd < dist.get((1,ni,j), 1e18):
                        dist[(1,ni,j)] = nd; parent[(1,ni,j)] = (ly,i,j); heapq.heappush(pq, (nd,1,ni,j))
            for nj in (j-1, j+1):
                if min_j <= nj <= max_j and j not in m1_blocked_j and nj not in m1_blocked_j and not (m1_wire_occ.get((i,nj),set()) - {net}):
                    nd = d + 3
                    if nd < dist.get((1,i,nj), 1e18):
                        dist[(1,i,nj)] = nd; parent[(1,i,nj)] = (ly,i,j); heapq.heappush(pq, (nd,1,i,nj))
        else:
            for nj in (j-1, j+1):
                if min_j <= nj <= max_j and not (m2_occ.get((i,nj),set()) - {net}):
                    nd = d + 1
                    if nd < dist.get((2,i,nj), 1e18):
                        dist[(2,i,nj)] = nd; parent[(2,i,nj)] = (ly,i,j); heapq.heappush(pq, (nd,2,i,nj))
            for ni in (i-1, i+1):
                if min_i <= ni <= max_i and not (m2_occ.get((ni,j),set()) - {net}):
                    nd = d + 3
                    if nd < dist.get((2,ni,j), 1e18):
                        dist[(2,ni,j)] = nd; parent[(2,ni,j)] = (ly,i,j); heapq.heappush(pq, (nd,2,ni,j))
        other = 3 - ly
        if min_i <= i <= max_i and min_j <= j <= max_j and j not in m1_blocked_j and not ((m1_via_occ.get((i,j),set()) | m2_occ.get((i,j),set())) - {net}):
            nd = d + 5
            if nd < dist.get((other,i,j), 1e18):
                dist[(other,i,j)] = nd; parent[(other,i,j)] = (ly,i,j); heapq.heappush(pq, (nd,other,i,j))
    print(f"  FAILED {net}: len(dist)={len(dist)} j_range=({min(j for _,_,j in dist)},{max(j for _,_,j in dist)})")
    return None

def commit_path(net, p, extra_segs=None, extra_vias=None):
    for idx, (ly, i, j) in enumerate(p):
        if ly == 1:
            m1_wire_occ[(i,j)].add(net); m1_via_occ[(i,j)].add(net)
        else:
            m2_occ[(i,j)].add(net)
        if idx + 1 < len(p) and p[idx+1][0] != ly:
            m1_wire_occ[(i,j)].add(net); m1_via_occ[(i,j)].add(net); m2_occ[(i,j)].add(net)
    vias = set(net_vias[net])
    if extra_vias:
        vias.update(extra_vias)
    for idx in (0, len(p) - 1):
        ly, i, j = p[idx]
        x, y = 2700 + i * 5400, 2700 + j * 5400
        other_ly = 3 - ly
        if any(s_ly == other_ly and x0 <= x <= x1 and y0 <= y <= y1 for (s_ly, x0, y0, x1, y1) in net_segs[net]):
            vias.add((x, y))
    segs = []
    cur_ly, i0, j0 = p[0]
    i_prev, j_prev = i0, j0
    for idx in range(1, len(p)):
        ly, i, j = p[idx]
        if ly != cur_ly:
            if (i_prev, j_prev) != (i0, j0):
                x1, y1 = 2700 + i0 * 5400, 2700 + j0 * 5400
                x2, y2 = 2700 + i_prev * 5400, 2700 + j_prev * 5400
                segs.append((cur_ly, min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)))
            vias.add((2700 + i * 5400, 2700 + j * 5400))
            cur_ly, i0, j0 = ly, i, j
        elif i != i0 and j != j0:
            x1, y1 = 2700 + i0 * 5400, 2700 + j0 * 5400
            x2, y2 = 2700 + i_prev * 5400, 2700 + j_prev * 5400
            segs.append((cur_ly, min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)))
            i0, j0 = i_prev, j_prev
        i_prev, j_prev = i, j
    if (i_prev, j_prev) != (i0, j0):
        x1, y1 = 2700 + i0 * 5400, 2700 + j0 * 5400
        x2, y2 = 2700 + i_prev * 5400, 2700 + j_prev * 5400
        segs.append((cur_ly, min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)))
    if extra_segs:
        segs.extend(extra_segs)
    net_segs[net].extend(segs)
    net_vias[net] = sorted(vias)

def cell_pin_node(inst, pname):
    cx, cy = inst_pos[inst]
    x0, y0, x1, y1 = macro_pin_m2[inst_cell[inst]][pname][0]
    px, py = (cx + x0 + cx + x1) // 2, (cy + y0 + cy + y1) // 2
    return {(2, (px + 500 - 2700) // 5400, (py + 500 - 2700) // 5400)}

def first_cell_pin(net):
    inst, pname = net_cell_pins[net][0]
    return cell_pin_node(inst, pname)

boundary_jobs = [
    ("cm_ram[0]", first_cell_pin("cm_ram[0]"), (1, 334, 55),  [(1, 1806300, 299700, 1839100, 299700)], []),
    ("cm_ram[1]", first_cell_pin("cm_ram[1]"), (1, 334, 137), [(1, 1806300, 742500, 1839100, 742500)], []),
    ("cm_ram[2]", first_cell_pin("cm_ram[2]"), (1, 334, 203), [(1, 1806300, 1098900, 1839100, 1098900)], []),
    ("cm_ram[3]", {(2, 339, 259)},             (1, 334, 287), [(1, 1806300, 1552500, 1839100, 1552500), (2, 1839100, 1541700, 1839100, 1552500)], []),
    ("cm_rom",    (1568700, 1476900),          (2, 285, 335), [(2, 1541700, 1811700, 1541700, 1838300)], []),
    ("rst",       (683100, 24300),             (2, 72, 1),    [(2, 391500, 1700, 391500, 8100)], []),
    ("d_oe",      first_cell_pin("d_oe"),      (2, 203, 1),   [(2, 1098900, 1700, 1098900, 8100)], []),
    ("test",      first_cell_pin("test"),      (2, 268, 1),   [(2, 1449900, 1700, 1449900, 8100)], []),
    ("sync",      first_cell_pin("sync"),      (2, 55, 334),  [(2, 299700, 1806300, 299700, 1838300)], []),
    ("d_out[0]",  (429300, 899100),            (1, 2, 55),    [(1, 900, 299700, 13500, 299700)], []),
    ("d_in[0]",   (1709100, 526500),           (1, 2, 72),    [(1, 900, 391500, 13500, 391500)], []),
    ("d_in[1]",   (726300, 715500),            (1, 2, 121),   [(1, 900, 656100, 13500, 656100)], []),
    ("d_out[1]",  (229500, 720900),            (1, 2, 137),   [(1, 900, 742500, 13500, 742500)], []),
    ("d_out[2]",  (13500, 1071900),            (1, 2, 203),   [(1, 900, 1098900, 13500, 1098900)], []),
    ("d_in[2]",   (456300, 877500),            (1, 2, 220),   [(1, 900, 1190700, 13500, 1190700)], []),
    ("d_in[3]",   (1687500, 1077300),          (1, 2, 268),   [(1, 900, 1449900, 13500, 1449900)], []),
    ("d_out[3]",  (391500, 1266300),           (1, 2, 286),   [(1, 900, 1547100, 13500, 1547100)], []),
    ("clk",       (1655100, 1271700),          (2, 120, 334), [(2, 650700, 1806300, 650700, 1838300)], []),
]
for net, _, (tly, ti, tj), ex_segs, ex_vias in boundary_jobs:
    if tly == 1:
        m1_wire_occ[(ti, tj)].add(net); m1_via_occ[(ti, tj)].add(net)
        m2_occ[(ti, tj)].add(net)
        if ti == 2:
            for ii in range(2, 8):
                if not m1_wire_occ.get((ii, tj)):
                    m1_wire_occ[(ii, tj)].add(net); m1_via_occ[(ii, tj)].add(net)
            if tj == 72:
                m2_occ[(2, 71)].add(net)
                for ii in range(2, 8):
                    if not m1_wire_occ.get((ii, 71)):
                        m1_wire_occ[(ii, 71)].add(net); m1_via_occ[(ii, 71)].add(net)
        else:
            for ii in range(332, 335):
                if not m1_wire_occ.get((ii, tj)):
                    m1_wire_occ[(ii, tj)].add(net); m1_via_occ[(ii, tj)].add(net)
    else:
        m2_occ[(ti, tj)].add(net)
        adj_j = tj + 1 if tj < 10 else tj - 1
        m2_occ[(ti, adj_j)].add(net)
    for sly, xlo, ylo, xhi, yhi in ex_segs:
        if sly == 1:
            mark_box(m1_wire_occ, xlo - 900, ylo - 900, xhi + 900, yhi + 900, net, 900, 900)
            mark_box(m1_via_occ,  xlo - 900, ylo - 900, xhi + 900, yhi + 900, net, 900, 900)
        else:
            mark_box(m2_occ, xlo - 1700, ylo - 1700, xhi + 1700, yhi + 1700, net, 1700, 1700)
    for vx, vy in ex_vias:
        mark_box(m1_wire_occ, vx - 1700, vy - 1700, vx + 1700, vy + 1700, net, 900, 900)
        mark_box(m1_via_occ,  vx - 1700, vy - 1700, vx + 1700, vy + 1700, net, 900, 900)

# 1. Route d_hiz
s_nodes_hiz = get_component_nodes("d_hiz", (715500, 623700))
t_nodes_hiz = {(1, 2, j) for j in range(62, 278) if j not in m1_blocked_j and not (m1_wire_occ.get((2, j), set()) - {"d_hiz"})}
p_hiz = dijkstra_multi("d_hiz", s_nodes_hiz, t_nodes_hiz, 2, 337, 2, 334)
print(f"Boundary {'d_hiz':12s}: len={len(p_hiz) if p_hiz else None}, end={p_hiz[-1] if p_hiz else None}")
assert p_hiz is not None
_, _, j_hit = p_hiz[-1]
extra_segs_hiz = [
    (1, 8100, 2700 + j_hit*5400, 13500, 2700 + j_hit*5400),
    (2, 8100, 337500, 8100, 1498500),
    (1, 900, 337500, 8100, 337500),
]
extra_vias_hiz = [(8100, 2700 + j_hit*5400), (8100, 337500)]
commit_path("d_hiz", p_hiz, extra_segs_hiz, extra_vias_hiz)

# 2. Route internal partial-ripup nets FIRST
internal_jobs = [
    ("_0321_",     (926100, 45900),   (882900, 137700),  2, 337, 1, 334),
    ("cyc2",       {(2, 33, 214)},     (94500, 1066500),  2, 337, 1, 214),
    ("_0274_",     (818100, 1098900),  (845100, 1223100),  2, 337, 1, 334),
    ("_0037_",     cell_pin_node(*net_cell_pins["_0037_"][0]), cell_pin_node(*net_cell_pins["_0037_"][1]), 2, 337, 1, 214),
    ("_0390_",     (1363500, 1088100), (1282500, 1271700), 2, 337, 1, 334),
    ("_0390_",     (769500, 1093500),  (1363500, 1088100), 2, 337, 1, 334),
    ("n_0125_bf1", (1244700, 877500),  (1185300, 1120500), 2, 337, 1, 207),
    ("_0077_",     (1142100, 1190700), (1439100, 1217700), 2, 337, 220, 334),
    ("_0077_",     (1439100, 1217700), (1563300, 1190700), 2, 337, 220, 334),
]
for net, s_xy, t_xy, mi, ma, mj, mb in internal_jobs:
    s_nodes = get_component_nodes(net, (2700 + next(iter(s_xy))[1]*5400, 2700 + next(iter(s_xy))[2]*5400)) | s_xy if isinstance(s_xy, set) else get_component_nodes(net, s_xy)
    t_nodes = get_component_nodes(net, (2700 + next(iter(t_xy))[1]*5400, 2700 + next(iter(t_xy))[2]*5400)) | t_xy if isinstance(t_xy, set) else get_component_nodes(net, t_xy)
    p = dijkstra_multi(net, s_nodes, t_nodes, mi, ma, mj, mb)
    print(f"Internal   {net:10s}: len={len(p) if p else None}")
    assert p is not None, f"Failed {net}"
    commit_path(net, p)

# 3. Route boundary_jobs
for net, src_spec, t_node, ex_segs, ex_vias in boundary_jobs:
    s_nodes = src_spec if isinstance(src_spec, set) else get_component_nodes(net, src_spec)
    min_i_b = 2
    max_i_b = 339 if net == "cm_ram[3]" else 337
    min_j_b = 220 if net in ("sync", "clk", "cm_rom", "cm_ram[3]", "d_out[3]") else 1
    max_j_b = 207 if net == "d_out[2]" else 335
    p = dijkstra_multi(net, s_nodes, {t_node}, min_i_b, max_i_b, min_j_b, max_j_b)
    print(f"Boundary   {net:10s}: len={len(p) if p else None}")
    assert p is not None, f"Failed {net}"
    commit_path(net, p, ex_segs, ex_vias)

p_hiz_doe = dijkstra_multi("d_hiz", get_component_nodes("d_hiz", (715500, 623700)), cell_pin_node("u_inv_doe", "A"), 2, 337, 1, 334)
print(f"Internal   {'d_hiz->doe':10s}: len={len(p_hiz_doe) if p_hiz_doe else None}")
assert p_hiz_doe is not None
commit_path("d_hiz", p_hiz_doe)

# Update PINS section in DEF:
pin_coords = {
    "d_out[0]": ("METAL1", 900, 900, 900, 299700),
    "d_hiz":    ("METAL1", 900, 900, 900, 337500),
    "d_in[0]":  ("METAL1", 900, 900, 900, 391500),
    "d_in[1]":  ("METAL1", 900, 900, 900, 656100),
    "d_out[1]": ("METAL1", 900, 900, 900, 742500),
    "d_out[2]": ("METAL1", 900, 900, 900, 1098900),
    "d_in[2]":  ("METAL1", 900, 900, 900, 1190700),
    "d_in[3]":  ("METAL1", 900, 900, 900, 1449900),
    "d_out[3]": ("METAL1", 900, 900, 900, 1547100),
    "cm_ram[0]": ("METAL1", 900, 900, 1839100, 299700),
    "cm_ram[1]": ("METAL1", 900, 900, 1839100, 742500),
    "cm_ram[2]": ("METAL1", 900, 900, 1839100, 1098900),
    "cm_ram[3]": ("METAL2", 1700, 1700, 1839100, 1541700),
    "rst":    ("METAL2", 1700, 1700, 391500, 1700),
    "d_oe":   ("METAL2", 1700, 1700, 1098900, 1700),
    "test":   ("METAL2", 1700, 1700, 1449900, 1700),
    "sync":   ("METAL2", 1700, 1700, 299700, 1838300),
    "clk":    ("METAL2", 1700, 1700, 650700, 1838300),
    "cm_rom": ("METAL2", 1700, 1700, 1541700, 1838300),
}

new_def = def_txt
for pname, (ly, hw, hh, px, py) in pin_coords.items():
    pat = rf"(-\s+{re.escape(pname)}\s+\+\s+NET\s+{re.escape(pname)}.*?LAYER\s+)\S+\s+\(\s*[-\d]+\s+[-\d]+\s*\)\s+\(\s*[-\d]+\s+[-\d]+\s*\)\s*\+\s*(?:PLACED|FIXED)\s+\(\s*[-\d]+\s+[-\d]+\s*\)\s+N"
    rep = rf"\g<1>{ly} ( -{hw} -{hh} ) ( {hw} {hh} ) + FIXED ( {px} {py} ) N"
    new_def, cnt = re.subn(pat, rep, new_def, flags=re.S)
    assert cnt == 1, f"Pin replace failed for {pname}"

pre_nets, post_nets = new_def.split("\nNETS ", 1)
post_nets = "\nNETS " + post_nets
modified_nets = set(partial_ripup.keys()) | b_nets_full_ripup
for net in sorted(modified_nets):
    m = re.search(rf"(-\s+{re.escape(net)}\s+.*?\+\s+USE\s+\S+\n).*?;", post_nets, re.S)
    assert m is not None, f"Net {net} not found"
    hdr = m.group(1)
    lines = []
    for idx, (ly, x0, y0, x1, y1) in enumerate(net_segs[net]):
        kw = "+ ROUTED" if idx == 0 else "NEW"
        ly_str = "METAL1" if ly == 1 else "METAL2"
        if x0 == x1:
            lines.append(f"      {kw} {ly_str} ( {x0} {y0} ) ( * {y1} )")
        else:
            lines.append(f"      {kw} {ly_str} ( {x0} {y0} ) ( {x1} * )")
    for vx, vy in net_vias[net]:
        lines.append(f"      NEW METAL1 ( {vx} {vy} ) V1_1x1")
    lines[-1] += " ;"
    post_nets = post_nets[:m.start()] + hdr + "\n".join(lines) + post_nets[m.end():]
new_def = pre_nets + post_nets

out_def = f"{OR_DIR}/routed_tap2_gio_exact.def"
Path(out_def).write_text(new_def)
Path(str(Path(__file__).resolve().parent.parent / "apr/c4004_core_4edge_routed.def").write_text(new_def)
print("Wrote", out_def, "and apr/c4004_core_4edge_routed.def")
