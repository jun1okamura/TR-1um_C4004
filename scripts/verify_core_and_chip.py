from pathlib import Path
import pya as db

CHIP_GDS = str(Path(__file__).resolve().parent.parent / "apr/c4004_chip.gds"
CORE_GDS = str(Path(__file__).resolve().parent.parent / "apr/c4004_core_routed.gds"

ly = db.Layout()
ly.read(CHIP_GDS)
top = ly.cell("OSS_FRAME")
assert top is not None

li_m1 = ly.layer(13, 0)
li_v1 = ly.layer(19, 0)
li_m2 = ly.layer(20, 0)
li_nw = ly.layer(140, 0)

print("=== 1. Back-End DRC Check on c4004_chip.gds (OSS_FRAME) ===")
r_m1 = db.Region(top.begin_shapes_rec(li_m1)).merged()
r_v1 = db.Region(top.begin_shapes_rec(li_v1))
r_v1_m = r_v1.merged()
r_m2 = db.Region(top.begin_shapes_rec(li_m2)).merged()

# Check overlapping V1 cuts:
v1_overlap = r_v1.ac_overlap() if hasattr(r_v1, "ac_overlap") else (r_v1.count() - r_v1_m.count())
print(f"V1 total shapes={r_v1.count()}, merged={r_v1_m.count()}")

m1_w = r_m1.width_check(1800)
m1_s = r_m1.space_check(1400)
m2_w = r_m2.width_check(3000)
m2_s = r_m2.space_check(2000)
v1_s = r_v1_m.space_check(1500)
v1_enc_m1 = r_v1_m.enclosed_check(r_m1, 1000)
v1_enc_m2 = r_v1_m.enclosed_check(r_m2, 1000)
v1_out_m1 = r_v1_m - r_m1
v1_out_m2 = r_v1_m - r_m2

# Additional PDK rules (rules.py / 10_pdk_facts.md):
li_po = ly.layer(14, 0)
li_mask = ly.layer(63, 0)
li_scrb = ly.layer(80, 0)
li_gc = ly.layer(8, 1)
li_gr = ly.layer(8, 2)
li_co = ly.layer(11, 0)
r_excl = (db.Region(top.begin_shapes_rec(li_mask)) + db.Region(top.begin_shapes_rec(li_scrb))).merged()
r_po = db.Region(top.begin_shapes_rec(li_po)).merged() - r_excl
r_m1_c = r_m1 - r_excl
r_m2_c = r_m2 - r_excl
r_v1_c = r_v1_m - r_excl
r_ga = (db.Region(top.begin_shapes_rec(li_gc)) + db.Region(top.begin_shapes_rec(li_gr))).merged() - r_excl
r_co = db.Region(top.begin_shapes_rec(li_co)).merged() - r_excl

# M1.SW: wide M1 (> 10.0 um) requires 2.0 um spacing to adjacent M1
r_m1w = r_m1_c.sized(-5000).merged().sized(5000).merged()
m1_sw = r_m1_c.space_check(2000).polygons().interacting(r_m1w)

# M1.W3 / M2.W3: max width 45.0 um (excluding PO pad areas)
r_m1_nopad = r_m1_c - r_m1_c.interacting(r_po)
r_m2_nopad = r_m2_c - r_m2_c.interacting(r_po)
m1_wmax = r_m1_nopad.sized(-22500).sized(22500)
m2_wmax = r_m2_nopad.sized(-22500).sized(22500)

# V1.GA (< 1.2 um) and V1.CO (< 1.0 um)
v1_ga = r_v1_c.separation_check(r_ga, 1200)
v1_co = r_v1_c.separation_check(r_co, 1000)
v1_ga_ov = r_v1_c & r_ga
v1_co_ov = r_v1_c & r_co

# V1 cut size (must be 1.4 x 1.4 um outside PO)
r_v1_nopad = r_v1_c - r_v1_c.interacting(r_po)
v1_bad_size = [p.bbox() for p in r_v1_nopad.each() if p.bbox().width() != 1400 or p.bbox().height() != 1400]

for name, pairs in [
    ("M1.W (<1.8um)", m1_w),
    ("M1.S (<1.4um)", m1_s),
    ("M2.W (<3.0um)", m2_w),
    ("M2.S (<2.0um)", m2_s),
    ("V1.S (<1.5um)", v1_s),
    ("V1.enc.M1 (<1.0um)", v1_enc_m1),
    ("V1.enc.M2 (<1.0um)", v1_enc_m2),
]:
    cnt = pairs.size()
    print(f"  {name:20s}: {cnt} violations")
    if cnt > 0:
        for idx, ep in enumerate(pairs.each()):
            if idx < 10:
                print(f"    -> {ep.bbox()}")
print(f"  V1 outside M1       : {v1_out_m1.count()}")
print(f"  V1 outside M2       : {v1_out_m2.count()}")
print(f"  M1.SW (wide M1 <2um): {m1_sw.count()}")
if m1_sw.count() > 0:
    for p in m1_sw.each():
        print(f"    -> M1.SW at {p.bbox()}")
print(f"  M1.W3 (>45um)       : {m1_wmax.count()}")
if m1_wmax.count() > 0:
    for p in m1_wmax.each():
        print(f"    -> M1.W3 at {p.bbox()}")
print(f"  M2.W3 (>45um)       : {m2_wmax.count()}")
print(f"  V1.GA (<1.2um)      : {v1_ga.size() + v1_ga_ov.count()}")
print(f"  V1.CO (<1.0um)      : {v1_co.size() + v1_co_ov.count()}")
if v1_co.size() + v1_co_ov.count() > 0:
    for ep in v1_co.each():
        print(f"    -> V1.CO sep at {ep.bbox()}")
    for p in v1_co_ov.each():
        print(f"    -> V1.CO ov  at {p.bbox()}")
print(f"  V1 cut != 1.4um     : {len(v1_bad_size)}")

print("\n=== 2. Connectivity Verification (LayoutToNetlist) on c4004_chip.gds ===")
l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
m1_l = l2n.make_layer(li_m1, "m1")
v1_l = l2n.make_layer(li_v1, "v1")
m2_l = l2n.make_layer(li_m2, "m2")
l2n.connect(m1_l)
l2n.connect(v1_l)
l2n.connect(m2_l)
l2n.connect(m1_l, v1_l)
l2n.connect(v1_l, m2_l)
l2n.extract_netlist()

def net_at(layer_reg, x_um, y_um):
    n = l2n.probe_net(layer_reg, db.DPoint(x_um, y_um))
    return n.expanded_name() if n else None

vdd_net = net_at(m2_l, 200.0, 1040.0)
vss_net = net_at(m2_l, -200.0, -1040.0)
vss_m1_pad = net_at(m1_l, -200.0, -1040.0)
print(f"VDD bondpad net: {vdd_net}")
print(f"VSS bondpad net (M2 at -200,-1040): {vss_net}, (M1 at -200,-1040): {vss_m1_pad}")
assert vdd_net is not None and vss_net is not None and vdd_net != vss_net and vss_net == vss_m1_pad, "VDD/VSS short or open!"

# Check all 9 rows' VDD and GND M1 rails (in chip coords = core_coords - 920.0)
ROW_YS_UM = [59.4, 237.6, 415.8, 594.0, 772.2, 950.4, 1128.6, 1306.8, 1485.0]
for idx, ry in enumerate(ROW_YS_UM):
    r_vdd = net_at(m1_l, 0.0, ry + 57.0 - 920.0)
    r_gnd = net_at(m1_l, 0.0, ry + 2.4 - 920.0)
    print(f"  Row {idx+1} (y={ry:6.1f}): VDD={r_vdd == vdd_net} ({r_vdd}), GND={r_gnd == vss_net} ({r_gnd})")

# Check u_sram power bars (in chip coords)
for label, y_core, exp_net in [
    ("SRAM_VSS_BOT", 1597.7, vss_net),
    ("SRAM_VDD_BOT", 1603.1, vdd_net),
    ("SRAM_VDD_TOP", 1774.5, vdd_net),
    ("SRAM_VSS_TOP", 1779.9, vss_net),
]:
    n = net_at(m1_l, 0.0, y_core - 920.0)
    print(f"  {label:14s}: ok={n == exp_net} ({n})")

# Check HIZ / OUT ties:
for label, x_c, y_c, exp_net in [
    ("HIZ1 (VDD)",  700.0, 1841.7, vdd_net),
    ("HIZ7 (VDD)",  340.0,   -1.7, vdd_net),
    ("HIZ10(VDD)", 1500.0,   -1.7, vdd_net),
    ("OUT1 (VSS)",  740.0, 1841.7, vss_net),
    ("HIZ2 (VSS)",  340.0, 1841.7, vss_net),
    ("HIZ15(VSS)", 1500.0, 1841.7, vss_net),
    ("OUT7 (VSS)",  300.0,   -1.7, vss_net),
    ("HIZ9 (VSS)", 1140.0,   -1.7, vss_net),
    ("OUT10(VSS)", 1540.0,   -1.7, vss_net),
    ("HIZ11(VSS)", 1841.7,  340.0, vss_net),
    ("HIZ12(VSS)", 1841.7,  700.0, vss_net),
    ("HIZ13(VSS)", 1841.7, 1140.0, vss_net),
    ("HIZ14(VSS)", 1841.7, 1500.0, vss_net),
]:
    n = net_at(m2_l, x_c - 920.0, y_c - 920.0)
    print(f"  Tie {label:12s}: ok={n == exp_net} ({n})")

# Check HIZ3..6 (d_hiz) and all 18 signal terminals dynamically against DEF component locations!
import re
def_txt = open(str(Path(__file__).resolve().parent.parent / "apr/c4004_core_4edge_routed.def").read()
lef_txt = open(str(Path(__file__).resolve().parent.parent / "openroad/TR-1um_cells_m2only.lef").read()
macro_pin_m2 = {}
for m in re.finditer(r"MACRO\s+(\S+)(.*?)END\s+\1", lef_txt, re.S):
    mname, body = m.group(1), m.group(2)
    macro_pin_m2[mname] = {}
    for pm in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", body, re.S):
        pname, pbody = pm.group(1), pm.group(2)
        rm = re.search(r"LAYER\s+METAL2\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", pbody)
        if rm:
            macro_pin_m2[mname][pname] = tuple(float(rm.group(k)) for k in range(1, 5))

comp_sec = def_txt.split("COMPONENTS")[1].split("END COMPONENTS")[0]
inst_xy = {}
inst_cell = {}
for m in re.finditer(r"-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)", comp_sec):
    inst_xy[m.group(1)] = (int(m.group(3)) / 1000.0, int(m.group(4)) / 1000.0)
    inst_cell[m.group(1)] = m.group(2)

nets_sec = def_txt.split("NETS")[1].split("END NETS")[0]
net_first_pin = {}
for nm in re.finditer(r"-\s+(\S+)\s+(.*?)\+\s+USE", nets_sec, re.S):
    nname = nm.group(1)
    for inst, pin in re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", nm.group(2)):
        if inst != "PIN":
            net_first_pin[nname] = (inst, pin)
            break

def net_pin_xy(nname):
    inst, pin = net_first_pin[nname]
    ix, iy = inst_xy[inst]
    x0, y0, x1, y1 = macro_pin_m2[inst_cell[inst]][pin]
    return (ix + 0.5 * (x0 + x1), iy + 0.5 * (y0 + y1))

hiz_nets = [net_at(m2_l, -1.7 - 920.0, y_c - 920.0) for y_c in (340.0, 700.0, 1140.0, 1500.0)]
dhiz_x, dhiz_y = net_pin_xy("d_hiz")
dhiz_core = net_at(m2_l, dhiz_x - 920.0, dhiz_y - 920.0)
print(f"  d_hiz (HIZ6..3)  : nets={hiz_nets}, core_pin={dhiz_core}, all_match={len(set(hiz_nets + [dhiz_core])) == 1}")
assert len(set(hiz_nets + [dhiz_core])) == 1 and dhiz_core is not None

sig_checks = [
    ("clk",        650.0, 1841.7, *net_pin_xy("clk")),
    ("sync",       300.0, 1841.7, *net_pin_xy("sync")),
    ("cm_rom",    1540.0, 1841.7, *net_pin_xy("cm_rom")),
    ("rst",        390.0,   -1.7, *net_pin_xy("rst")),
    ("d_oe",      1100.0,   -1.7, *net_pin_xy("d_oe")),
    ("test",      1450.0,   -1.7, *net_pin_xy("test")),
    ("cm_ram[0]", 1841.7,  300.0, *net_pin_xy("cm_ram[0]")),
    ("cm_ram[1]", 1841.7,  740.0, *net_pin_xy("cm_ram[1]")),
    ("cm_ram[2]", 1841.7, 1100.0, *net_pin_xy("cm_ram[2]")),
    ("cm_ram[3]", 1841.7, 1540.0, *net_pin_xy("cm_ram[3]")),
    ("d_out[0]",    -1.7,  300.0, *net_pin_xy("d_out[0]")),
    ("d_in[0]",     -1.7,  390.0, *net_pin_xy("d_in[0]")),
    ("d_in[1]",     -1.7,  650.0, *net_pin_xy("d_in[1]")),
    ("d_out[1]",    -1.7,  740.0, *net_pin_xy("d_out[1]")),
    ("d_out[2]",    -1.7, 1100.0, *net_pin_xy("d_out[2]")),
    ("d_in[2]",     -1.7, 1190.0, *net_pin_xy("d_in[2]")),
    ("d_in[3]",     -1.7, 1450.0, *net_pin_xy("d_in[3]")),
    ("d_out[3]",    -1.7, 1540.0, *net_pin_xy("d_out[3]")),
]
seen_sig_nets = set()
for sname, px, py, cx, cy in sig_checks:
    npad = net_at(m2_l, px - 920.0, py - 920.0)
    ncell = net_at(m2_l, cx - 920.0, cy - 920.0)
    ok = (npad is not None and npad == ncell and npad not in (vdd_net, vss_net) and npad not in seen_sig_nets)
    seen_sig_nets.add(npad)
    print(f"  Sig {sname:10s}: pad={npad}, cell={ncell}, ok={ok}")
    assert ok, f"Signal {sname} failed connectivity check!"

# Also verify TAP2 columns' M2 straps are connected to VDD and VSS!
for tx_um in (21.6, 615.6, 1215.0, 1809.0):
    n_gnd = net_at(m2_l, tx_um + 2.7 - 920.0, 500.0 - 920.0)
    n_vdd = net_at(m2_l, tx_um + 8.1 - 920.0, 500.0 - 920.0)
    print(f"  TAP2 col x={tx_um:6.1f}um: GND_ok={n_gnd == vss_net} ({n_gnd}), VDD_ok={n_vdd == vdd_net} ({n_vdd})")
    assert n_gnd == vss_net and n_vdd == vdd_net, f"TAP2 col {tx_um} power mismatch!"

# Check WN spacing rules (WN.S1 < 4.0um, WN.AN < 6.0um):
li_an = ly.layer(3, 2)
li_dn = ly.layer(5, 1)
r_wn = db.Region(top.begin_shapes_rec(li_nw)).merged() - r_excl
r_an = (db.Region(top.begin_shapes_rec(li_an)) + db.Region(top.begin_shapes_rec(li_dn))).merged() - r_excl
r_an_out_wn = r_an - r_wn
wn_s1 = r_wn.space_check(4000)
wn_an = r_wn.separation_check(r_an_out_wn, 6000)
print(f"  WN.S1 (<4.0um)      : {wn_s1.size()}")
print(f"  WN.AN (<6.0um)      : {wn_an.size()}")
assert wn_s1.size() == 0 and wn_an.size() == 0, "WN DRC violation!"

# Check ERR01 (50nm manufacturing grid on all 12 layers) and ERR00 (PTECT overlap):
offgrid_cnt = 0
for lnum, ldt in [(140,0),(3,1),(3,2),(3,3),(3,4),(8,1),(8,2),(11,0),(13,0),(19,0),(20,0),(14,0)]:
    r_ly = db.Region(top.begin_shapes_rec(ly.layer(lnum, ldt))) - r_excl
    for p in r_ly.each():
        for pt in p.each_point_hull():
            if pt.x % 50 != 0 or pt.y % 50 != 0:
                offgrid_cnt += 1
print(f"  ERR01 (offgrid 50nm): {offgrid_cnt}")
assert offgrid_cnt == 0, "Offgrid violation!"

r_ptect = db.Region(top.begin_shapes_rec(ly.layer(63, 1))) - r_excl
err00_cnt = (r_ptect & (r_v1_c + r_m2_c + r_po)).count()
print(f"  ERR00 (PTECT ovlp)  : {err00_cnt}")
assert err00_cnt == 0, "ERR00 violation!"


