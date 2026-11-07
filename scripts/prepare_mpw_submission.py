#!/usr/bin/env python3
"""
Prepare OpenSUSI TR-1um MPW submission files in src/:
  - src/tr_1um_jun1okamura.gds (top cell: tr_1um_jun1okamura instantiating OSS_FRAME)
  - src/tr_1um_jun1okamura.cir (top subcircuit: tr_1um_jun1okamura instantiating OSS_FRAME)
and verify pre-check criteria (top cell name, DBU=0.001, bbox=(-1250,-1250;1250,1250), OSS_FRAME presence).
"""

from pathlib import Path
import pya

REPO_DIR = Path(str(Path(__file__).resolve().parent.parent))
APR_GDS = REPO_DIR / "apr" / "c4004_chip.gds"
APR_SPICE = REPO_DIR / "apr" / "c4004_chip.spice"
SRC_DIR = REPO_DIR / "src"

TOP_NAME = "tr_1um_jun1okamura"
OUT_GDS = SRC_DIR / f"{TOP_NAME}.gds"
OUT_CIR = SRC_DIR / f"{TOP_NAME}.cir"

# 1. Build src/tr_1um_jun1okamura.gds wrapping OSS_FRAME at (0,0) with top-level pad labels on 49/0
ly = pya.Layout()
ly.read(str(APR_GDS))
assert abs(ly.dbu - 0.001) < 1e-9

oss_frame = ly.cell("OSS_FRAME")
assert oss_frame is not None, "OSS_FRAME cell not found in apr/c4004_chip.gds"

top_cell = ly.create_cell(TOP_NAME)
top_cell.insert(pya.CellInstArray(oss_frame.cell_index(), pya.Trans(0, 0)))

# Copy top-level pad center text labels on M2 (49/0) into top_cell so LVS sees top-level ports
li_m2 = ly.layer(49, 0)
PAD_LABELS = [
    ("P1", -200000, 1040000),
    ("P2", -600000, 1040000),
    ("P3", -1040000, 600000),
    ("P4", -1040000, 200000),
    ("P5", -1040000, -200000),
    ("P6", -1040000, -600000),
    ("P7", -600000, -1040000),
    ("VSS", -200000, -1040000),
    ("P9", 200000, -1040000),
    ("P10", 600000, -1040000),
    ("P11", 1040000, -600000),
    ("P12", 1040000, -200000),
    ("P13", 1040000, 200000),
    ("P14", 1040000, 600000),
    ("P15", 600000, 1040000),
    ("VDD", 200000, 1040000),
]
for pname, px, py in PAD_LABELS:
    top_cell.shapes(li_m2).insert(pya.Text(pname, pya.Trans(px, py)))

ly.write(str(OUT_GDS))

# 2. Verify pre_check.py conditions on OUT_GDS
ly_chk = pya.Layout()
ly_chk.read(str(OUT_GDS))
top_cells = list(ly_chk.top_cells())
assert len(top_cells) == 1 and top_cells[0].name == TOP_NAME, f"Expected single top cell {TOP_NAME}, got {[c.name for c in top_cells]}"
bbox = top_cells[0].dbbox()
assert abs(bbox.p1.x - (-1250.0)) < 1e-6 and abs(bbox.p1.y - (-1250.0)) < 1e-6
assert abs(bbox.p2.x - 1250.0) < 1e-6 and abs(bbox.p2.y - 1250.0) < 1e-6
assert any(c.name in {"OSS_FRAME", "OSS_FRAME_TEG"} for c in ly_chk.each_cell())
print(f"OK: {OUT_GDS.name} passed all pre-check rules: top={TOP_NAME}, dbu={ly_chk.dbu}, bbox={bbox}")

# 3. Build src/tr_1um_jun1okamura.cir wrapping OSS_FRAME
spice_txt = APR_SPICE.read_text()
wrapper_subckt = f"""
.subckt {TOP_NAME} P1 P2 P3 P4 P5 P6 P7 VSS P9 P10 P11 P12 P13 P14 P15 VDD
XFRAME P1 P2 P3 P4 P5 P6 P7 VSS P9 P10 P11 P12 P13 P14 P15 VDD OSS_FRAME
.ends {TOP_NAME}
"""
OUT_CIR.write_text(spice_txt.rstrip() + "\n" + wrapper_subckt)
print(f"OK: Wrote {OUT_CIR.name} ({len(OUT_CIR.read_text().splitlines())} lines)")

# 4. Verify KLayout LVS on src/tr_1um_jun1okamura.gds vs src/tr_1um_jun1okamura.cir
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import klayout_extract
import pya as db

l2n = klayout_extract.build(str(OUT_GDS), TOP_NAME, flat=False)
nl = l2n.netlist()
nl.make_top_level_pins()
nl.combine_devices()
nl.purge()
nl.purge_nets()

ref = db.Netlist()
ref.read(str(OUT_CIR), db.NetlistSpiceReader())
ref.combine_devices()
ref.purge()
ref.purge_nets()

c_nl = {c.name.upper(): c.name for c in nl.each_circuit()}
c_ref = {c.name.upper(): c.name for c in ref.each_circuit()}
for k in list(c_nl.keys()):
    if k not in c_ref:
        nl.flatten_circuit(c_nl[k])
for k in list(c_ref.keys()):
    if k not in c_nl:
        ref.flatten_circuit(c_ref[k])
nl.combine_devices()
ref.combine_devices()

cmp = db.NetlistComparer()
for cname in ("NAND2_X1", "NAND3_X1", "NOR2_X1", "NOR3_X1"):
    c = ref.circuit_by_name(cname)
    if c is not None:
        pids = [p.id() for p in c.each_pin() if p.name().startswith("A") or p.name() in ("A", "B", "C")]
        if len(pids) >= 2:
            cmp.same_pins(c, pids)

match = cmp.compare(nl, ref)
top_l = nl.circuit_by_name(TOP_NAME)
top_s = ref.circuit_by_name(TOP_NAME)
l_pins = sorted([p.name() for p in top_l.each_pin()])
s_pins = sorted([p.name() for p in top_s.each_pin()])
print(f"OK: LVS Match for {TOP_NAME} = {match}")
print(f"  Layout {TOP_NAME} pins ({len(l_pins)}): {l_pins}")
print(f"  Schem  {TOP_NAME} pins ({len(s_pins)}): {s_pins}")
assert match and l_pins == s_pins

