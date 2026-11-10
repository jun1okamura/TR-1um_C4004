import os
import re
import pya

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STDCELL_GDS = os.path.join(BASE_DIR, "module/STDCELL/TR-1um_STDCELL.gds")
STDCELL_LEF = os.path.join(BASE_DIR, "module/STDCELL/TR-1um_cells.lef")
SRAM_GDS    = os.path.join(BASE_DIR, "module/SRAM128/SRAM128.gds")
SRAM_LEF    = os.path.join(BASE_DIR, "module/SRAM128/SRAM128.lef")

OUT_TECH_LEF  = os.path.join(BASE_DIR, "openroad/TR-1um_tech_clean.lef")
OUT_CELLS_LEF = os.path.join(BASE_DIR, "openroad/TR-1um_cells_m2only.lef")
OUT_SRAM_LEF  = os.path.join(BASE_DIR, "openroad/SRAM128_clean.lef")

os.makedirs(os.path.join(BASE_DIR, "openroad"), exist_ok=True)

tech_lef_content = """VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS
  DATABASE MICRONS 1000 ;
END UNITS

MANUFACTURINGGRID 0.05 ;

LAYER METAL1
  TYPE ROUTING ;
  DIRECTION HORIZONTAL ;
  PITCH 5.4 ;
  OFFSET 2.7 ;
  WIDTH 2.0 ;
  SPACING 1.6 ;
END METAL1

LAYER VIA1
  TYPE CUT ;
  SPACING 1.6 ;
END VIA1

LAYER METAL2
  TYPE ROUTING ;
  DIRECTION VERTICAL ;
  PITCH 5.4 ;
  OFFSET 2.7 ;
  WIDTH 3.4 ;
  SPACING 2.0 ;
END METAL2

VIA V1_1x1 DEFAULT
  LAYER METAL1 ;
    RECT -1.7 -1.7 1.7 1.7 ;
  LAYER VIA1 ;
    RECT -0.7 -0.7 0.7 0.7 ;
  LAYER METAL2 ;
    RECT -1.7 -1.7 1.7 1.7 ;
END V1_1x1

SITE TR1UM
  CLASS CORE ;
  SYMMETRY Y ;
  SIZE 5.4 BY 59.4 ;
END TR1UM

END LIBRARY
"""
with open(OUT_TECH_LEF, "w") as f:
    f.write(tech_lef_content)
print(f"Wrote {OUT_TECH_LEF}")

ly_std = pya.Layout()
ly_std.read(STDCELL_GDS)
dbu_std = ly_std.dbu
li_m2_std = ly_std.find_layer(20, 0)

OUTPUT_PINS = {"Y", "Q", "QB"}
INTERNAL_PINS = {"CKB", "CKP", "QM", "QS"}

with open(STDCELL_LEF, "r") as f:
    raw_cells_lef = f.read()

macro_blocks = re.findall(r"(MACRO\s+(\S+).*?END\s+\2)", raw_cells_lef, flags=re.DOTALL)

out_lines = [
    "VERSION 5.8 ;",
    'BUSBITCHARS "[]" ;',
    'DIVIDERCHAR "/" ;',
    ""
]

for block, cell_name in macro_blocks:
    m_size = re.search(r"SIZE\s+([\d\.]+)\s+BY\s+([\d\.]+)\s*;", block)
    w_um = float(m_size.group(1))
    h_um = float(m_size.group(2))
    m_class = re.search(r"CLASS\s+([^;]+);", block)
    cls_str = m_class.group(1).strip() if m_class else "CORE"

    out_lines.append(f"MACRO {cell_name}")
    out_lines.append(f"  CLASS {cls_str} ;")
    out_lines.append(f"  FOREIGN {cell_name} 0.000 0.000 ;")
    out_lines.append("  ORIGIN 0.000 0.000 ;")
    out_lines.append(f"  SIZE {w_um:.3f} BY {h_um:.3f} ;")
    out_lines.append("  SYMMETRY X Y ;")
    out_lines.append("  SITE TR1UM ;")

    pin_blocks = re.findall(r"PIN\s+(\S+)(.*?)END\s+\1", block, flags=re.DOTALL)
    pin_m2_region = pya.Region()

    for pname, pbody in pin_blocks:
        if pname in INTERNAL_PINS:
            continue
        if pname.lower() in ("vdd", "vss"):
            continue
        m2_rects = []
        for lblock in re.findall(r"LAYER\s+METAL2\s*;(.*?)(?=LAYER|END)", pbody, flags=re.DOTALL):
            for r in re.findall(r"RECT\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)\s*;", lblock):
                x1, y1, x2, y2 = map(float, r)
                m2_rects.append((x1, y1, x2, y2))
                pin_m2_region.insert(pya.Box(
                    int(round(x1 / dbu_std)), int(round(y1 / dbu_std)),
                    int(round(x2 / dbu_std)), int(round(y2 / dbu_std))
                ))
        if not m2_rects:
            continue
        pdir = "OUTPUT" if pname in OUTPUT_PINS else "INPUT"
        out_lines.append(f"  PIN {pname}")
        out_lines.append(f"    DIRECTION {pdir} ;")
        out_lines.append("    USE SIGNAL ;")
        out_lines.append("    PORT")
        out_lines.append("      LAYER METAL2 ;")
        for x1, y1, x2, y2 in m2_rects:
            out_lines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
        out_lines.append("    END")
        out_lines.append(f"  END {pname}")

    out_lines.append("  PIN vdd")
    out_lines.append("    DIRECTION INOUT ;")
    out_lines.append("    USE POWER ;")
    out_lines.append("    SHAPE ABUTMENT ;")
    out_lines.append("    PORT")
    out_lines.append("      LAYER METAL1 ;")
    out_lines.append(f"        RECT 0.000 55.700 {w_um:.3f} 58.300 ;")
    out_lines.append("    END")
    out_lines.append("  END vdd")

    out_lines.append("  PIN vss")
    out_lines.append("    DIRECTION INOUT ;")
    out_lines.append("    USE GROUND ;")
    out_lines.append("    SHAPE ABUTMENT ;")
    out_lines.append("    PORT")
    out_lines.append("      LAYER METAL1 ;")
    out_lines.append(f"        RECT 0.000 1.100 {w_um:.3f} 3.700 ;")
    out_lines.append("    END")
    out_lines.append("  END vss")

    out_lines.append("  OBS")
    out_lines.append("    LAYER METAL1 ;")
    out_lines.append(f"      RECT 0.000 0.000 {w_um:.3f} {h_um:.3f} ;")
    out_lines.append("    LAYER VIA1 ;")
    out_lines.append(f"      RECT 0.000 0.000 {w_um:.3f} {h_um:.3f} ;")

    gds_cell = ly_std.cell(cell_name)
    if gds_cell is not None and li_m2_std is not None:
        all_m2 = pya.Region(gds_cell.begin_shapes_rec(li_m2_std))
        non_pin_m2 = all_m2 - pin_m2_region
        if not non_pin_m2.is_empty():
            out_lines.append("    LAYER METAL2 ;")
            for poly in non_pin_m2.each():
                b = poly.bbox()
                out_lines.append(
                    f"      RECT {b.left*dbu_std:.3f} {b.bottom*dbu_std:.3f} "
                    f"{b.right*dbu_std:.3f} {b.top*dbu_std:.3f} ;"
                )
    out_lines.append("  END")
    out_lines.append(f"END {cell_name}")
    out_lines.append("")

out_lines.append("END LIBRARY")
with open(OUT_CELLS_LEF, "w") as f:
    f.write("\n".join(out_lines) + "\n")
print(f"Wrote {OUT_CELLS_LEF} ({len(macro_blocks)} cells)")

ly_sram = pya.Layout()
ly_sram.read(SRAM_GDS)
top_sram = ly_sram.top_cell()
dbu_sram = ly_sram.dbu
ox, oy = 82.100, 90.100

with open(SRAM_LEF, "r") as f:
    raw_sram_lef = f.read()

pins_part = raw_sram_lef.split("    OBS")[0]
pins_part = pins_part.replace("MANUFACTURINGGRID 0.05 ;\n", "")
pins_part = pins_part.replace("LAYER M1 ;", "LAYER METAL1 ;")
pins_part = pins_part.replace("LAYER M2 ;", "LAYER METAL2 ;")
pins_part = pins_part.replace("LAYER V1 ;", "LAYER VIA1 ;")

li_m1_sram    = ly_sram.find_layer(13, 0)
li_m1pin_sram = ly_sram.find_layer(48, 1)
reg_m1    = pya.Region(top_sram.begin_shapes_rec(li_m1_sram))
reg_m1pin = pya.Region(top_sram.begin_shapes_rec(li_m1pin_sram))

reg_m1_obs = (reg_m1 - reg_m1pin).merged()

sram_obs_lines = [
    "    OBS",
    "        LAYER METAL1 ;",
    "            RECT 6.000 0.000 1160.000 185.600 ;"
]

left_right_clip = pya.Region()
left_right_clip.insert(pya.Box(int(round((-ox)/dbu_sram)), int(round((-oy)/dbu_sram)),
                               int(round((10.0-ox)/dbu_sram)), int(round((185.6-oy)/dbu_sram))))
left_right_clip.insert(pya.Box(int(round((1156.0-ox)/dbu_sram)), int(round((-oy)/dbu_sram)),
                               int(round((1166.1-ox)/dbu_sram)), int(round((185.6-oy)/dbu_sram))))

edge_m1_obs = (reg_m1_obs & left_right_clip)
for poly in edge_m1_obs.each():
    for tr in poly.decompose_trapezoids():
        b = tr.bbox()
        x1 = b.left * dbu_sram + ox
        y1 = b.bottom * dbu_sram + oy
        x2 = b.right * dbu_sram + ox
        y2 = b.top * dbu_sram + oy
        sram_obs_lines.append(f"            RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")

sram_obs_lines.extend([
    "        LAYER VIA1 ;",
    "            RECT 0.000 0.000 1166.100 185.600 ;",
    "        LAYER METAL2 ;",
    "            RECT 0.000 0.000 1166.100 185.600 ;",
    "    END",
    "END SRAM128",
    "",
    "END LIBRARY"
])

with open(OUT_SRAM_LEF, "w") as f:
    f.write(pins_part + "\n".join(sram_obs_lines) + "\n")
print(f"Wrote {OUT_SRAM_LEF}")
