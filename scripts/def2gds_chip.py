#!/usr/bin/env python3
"""
Convert OpenROAD routed DEF (apr/c4004_core_routed.def) into:
  1. apr/c4004_core.gds          (top cell: c4004_core)
  2. apr/c4004_chip.gds          (top cell: OSS_FRAME)
  3. src/tr_1um_jun1okamura.gds  (top cell: tr_1um_jun1okamura)
Includes full-chip power mesh (4x TAP2 M2 straps across 11 rows, SRAM128 left & right VDD/VSS
at X=345.6 um, Y=1614.6 um, left & right TAP2 VDD to North P16 VDDPAD, multi-point 4-side VSS bridges to
OSS_FRAME_GIO M2 VSS ring) and 16-pad signal/control routing.
"""

import os
import re
import pya

TRIAL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_PATH = os.path.join(TRIAL_DIR, "apr", "c4004_core_routed.def")
STDCELL_GDS = os.path.join(TRIAL_DIR, "module", "STDCELL", "TR-1um_STDCELL.gds")
SRAM_GDS = os.path.join(TRIAL_DIR, "module", "SRAM128", "SRAM128.gds")
FRAME_GDS = os.path.join(TRIAL_DIR, "TR-1um", "libs.tech", "klayout", "libraries", "TR-1um_frame_25x25.gds")

OUT_CORE_GDS = os.path.join(TRIAL_DIR, "apr", "c4004_core.gds")
OUT_CHIP_GDS = os.path.join(TRIAL_DIR, "apr", "c4004_chip.gds")
OUT_SUB_GDS = os.path.join(TRIAL_DIR, "src", "tr_1um_jun1okamura.gds")
OUT_IP62_GDS = os.path.join(TRIAL_DIR, "src", "IP62_jun1okamura.gds")

# SRAM128 LEF has FOREIGN SRAM128 82.100 90.100 ;
SRAM_FOREIGN_DX = 82100
SRAM_FOREIGN_DY = 90100

# Core origin inside OSS_FRAME (-920.0 um, -920.0 um)
CORE_OFFSET_X = -920000
CORE_OFFSET_Y = -920000


def add_box(cell, layer_idx, x1, y1, x2, y2):
    cell.shapes(layer_idx).insert(pya.Box(int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))))


def add_via1(cell, li_m1, li_v1, li_m2, vx, vy):
    vx, vy = int(round(vx)), int(round(vy))
    cell.shapes(li_m1).insert(pya.Box(vx - 1700, vy - 1700, vx + 1700, vy + 1700))
    cell.shapes(li_v1).insert(pya.Box(vx - 700, vy - 700, vx + 700, vy + 700))
    cell.shapes(li_m2).insert(pya.Box(vx - 1700, vy - 1700, vx + 1700, vy + 1700))


def parse_def(def_path):
    with open(def_path, "r") as f:
        text = f.read()

    # 1. COMPONENTS
    comp_sec = text.split("COMPONENTS ")[1].split("END COMPONENTS")[0]
    components = []
    for line in comp_sec.splitlines():
        line = line.strip()
        if line.startswith("- "):
            parts = line.split()
            inst_name = parts[1]
            macro_name = parts[2]
            idx = parts.index("(")
            x = int(parts[idx + 1])
            y = int(parts[idx + 2])
            orient = parts[idx + 4]
            components.append((inst_name, macro_name, x, y, orient))

    # 2. PINS
    pins_sec = text.split("PINS ")[1].split("END PINS")[0]
    pins = []
    for pb in pins_sec.split("- ")[1:]:
        lines = [l.strip() for l in pb.strip().splitlines()]
        pname = lines[0].split()[0]
        layer = None
        rect = None
        fixed = None
        for l in lines:
            if l.startswith("+ LAYER"):
                parts = l.split()
                layer = parts[2]
                rect = (int(parts[4]), int(parts[5]), int(parts[8]), int(parts[9]))
            elif l.startswith("+ FIXED"):
                parts = l.split()
                fixed = (int(parts[3]), int(parts[4]))
        if layer and rect and fixed:
            pins.append((pname, layer, fixed[0] + rect[0], fixed[1] + rect[1], fixed[0] + rect[2], fixed[1] + rect[3]))

    # 3. NETS
    nets_sec = text.split("NETS ")[1].split("END NETS")[0]
    m1_rects = []
    m2_rects = []
    v1_pts = []
    net_blocks = re.split(r'\n\s*-\s+', "\n" + nets_sec)[1:]
    for nb in net_blocks:
        for line in nb.splitlines():
            line = line.strip()
            if not (line.startswith("+ ROUTED") or line.startswith("NEW")):
                continue
            tokens = line.replace("+", "").replace("ROUTED", "").replace("NEW", "").replace(";", "").split()
            layer = tokens[0]
            idx = 1
            pts = []
            last_x, last_y = None, None
            while idx < len(tokens):
                if tokens[idx] == "(":
                    tx = tokens[idx + 1]
                    ty = tokens[idx + 2]
                    x = last_x if tx == "*" else int(tx)
                    y = last_y if ty == "*" else int(ty)
                    last_x, last_y = x, y
                    if tokens[idx + 3] != ")":
                        ext = int(tokens[idx + 3])
                        idx += 5
                    else:
                        ext = None
                        idx += 4
                    pts.append((x, y, ext))
                else:
                    if last_x is not None:
                        v1_pts.append((last_x, last_y))
                    idx += 1
            hw = 1000 if layer == "METAL1" else 1700
            for i in range(len(pts) - 1):
                x1, y1, e1 = pts[i]
                x2, y2, e2 = pts[i + 1]
                ext1 = hw if e1 is None else e1
                ext2 = hw if e2 is None else e2
                if x1 == x2:
                    if y1 <= y2:
                        by1, by2 = y1 - ext1, y2 + ext2
                    else:
                        by1, by2 = y2 - ext2, y1 + ext1
                    bx1, bx2 = x1 - hw, x1 + hw
                else:
                    if x1 <= x2:
                        bx1, bx2 = x1 - ext1, x2 + ext2
                    else:
                        bx1, bx2 = x2 - ext2, x1 + ext1
                    by1, by2 = y1 - hw, y1 + hw
                if layer == "METAL1":
                    m1_rects.append((bx1, by1, bx2, by2))
                elif layer == "METAL2":
                    m2_rects.append((bx1, by1, bx2, by2))

    return components, pins, m1_rects, m2_rects, v1_pts


def build_core_and_power_shapes(core_cell, layout, components, pins, m1_rects, m2_rects, v1_pts, include_frame_bridges=True):
    li_m1 = layout.layer(13, 0)
    li_v1 = layout.layer(19, 0)
    li_m2 = layout.layer(20, 0)

    l_std = pya.Layout()
    l_std.read(STDCELL_GDS)
    l_sram = pya.Layout()
    l_sram.read(SRAM_GDS)

    copied_cells = {}

    def get_or_copy_cell(macro_name):
        if macro_name in copied_cells:
            return copied_cells[macro_name]
        src_l = l_sram if macro_name == "SRAM128" else l_std
        src_c = src_l.cell(macro_name)
        if src_c is None:
            raise RuntimeError(f"Cell {macro_name} not found in GDS libraries")
        dst_c = layout.create_cell(macro_name)
        dst_c.copy_tree(src_c)
        if macro_name == "SRAM128":
            dst_c.flatten(True)
        copied_cells[macro_name] = dst_c
        return dst_c

    for inst_name, macro_name, x, y, orient in components:
        c = get_or_copy_cell(macro_name)
        if macro_name == "SRAM128":
            gx = x + SRAM_FOREIGN_DX
            gy = y + SRAM_FOREIGN_DY
        else:
            gx, gy = x, y
        core_cell.insert(pya.CellInstArray(c.cell_index(), pya.Trans(0, False, gx, gy)))

    for bx1, by1, bx2, by2 in m1_rects:
        add_box(core_cell, li_m1, bx1, by1, bx2, by2)
    for bx1, by1, bx2, by2 in m2_rects:
        add_box(core_cell, li_m2, bx1, by1, bx2, by2)
    for vx, vy in v1_pts:
        add_via1(core_cell, li_m1, li_v1, li_m2, vx, vy)

    for pname, layer, bx1, by1, bx2, by2 in pins:
        li = li_m1 if layer == "METAL1" else li_m2
        add_box(core_cell, li, bx1, by1, bx2, by2)

    # =========================================================================
    # Power Mesh & Pad Frame Connections (in Core DBU = nm) - Trial 06 (11 Rows, Pitch=145.8, SRAM=(345.6, 1614.6))
    # =========================================================================
    y_south_vss = -10000 if include_frame_bridges else 0
    y_north_vss = 1850000 if include_frame_bridges else 1840000
    x_west_vss = -10000 if include_frame_bridges else 0
    x_east_vss = 1850000 if include_frame_bridges else 1840000

    # 1. 4 Columns of TAP2 Vertical M2 Straps (VSS and VDD) across 11 Rows (top of Row 10 = 1544.4 um)
    # Col 0 (West, tap_x = 21600): VSS = 22600..26000, VDD = 28000..31400
    add_box(core_cell, li_m2, 22600, y_south_vss, 26000, y_north_vss)
    add_box(core_cell, li_m2, 28000, 3600, 31400, 1834000)

    # Col 1 (Center-Left, tap_x = 615600): VSS = 616600..620000, VDD = 622000..625400
    add_box(core_cell, li_m2, 616600, y_south_vss, 620000, 1544400)
    add_box(core_cell, li_m2, 622000, 27000, 625400, 1544400)

    # Col 2 (Center-Right, tap_x = 1215000): VSS = 1216000..1219400, VDD = 1221400..1224800
    add_box(core_cell, li_m2, 1216000, y_south_vss, 1219400, 1544400)
    add_box(core_cell, li_m2, 1221400, 27000, 1224800, 1544400)

    # Col 3 (East, tap_x = 1809000): VSS = 1810000..1813400, VDD = 1815400..1818800
    add_box(core_cell, li_m2, 1810000, y_south_vss, 1813400, y_north_vss)
    add_box(core_cell, li_m2, 1815400, 3600, 1818800, 1834000)

    # 2. SRAM128 (placed at X = 340.2 um, Y = 1614.6 um) Left & Right VDD and VSS M1 Rails + V1 Vias
    # Bottom-Left VSS (1614.6..1618.0) & VDD (1620.0..1623.4)
    add_box(core_cell, li_m1, 22600, 1614600, 343600, 1618000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 24300, 1616300)
    add_box(core_cell, li_m1, 28000, 1620000, 343600, 1623400)
    add_via1(core_cell, li_m1, li_v1, li_m2, 29700, 1621700)

    # Top-Left VDD (1791.4..1794.8) & VSS (1796.8..1800.2)
    add_box(core_cell, li_m1, 28000, 1791400, 343600, 1794800)
    add_via1(core_cell, li_m1, li_v1, li_m2, 29700, 1793100)
    add_box(core_cell, li_m1, 22600, 1796800, 343600, 1800200)
    add_via1(core_cell, li_m1, li_v1, li_m2, 24300, 1798500)

    # Bottom-Right VSS (1614.6..1618.0) & VDD (1620.0..1623.4)
    add_box(core_cell, li_m1, 1502900, 1614600, 1813400, 1618000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1811700, 1616300)
    add_box(core_cell, li_m1, 1502900, 1620000, 1818800, 1623400)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1817100, 1621700)

    # Top-Right VDD (1791.4..1794.8) & VSS (1796.8..1800.2)
    add_box(core_cell, li_m1, 1502900, 1791400, 1818800, 1794800)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1817100, 1793100)
    add_box(core_cell, li_m1, 1502900, 1796800, 1813400, 1800200)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1811700, 1798500)

    # Extra vertical M2 VDD straps from SRAM128 Top VDD rail (1791.4..1794.8) to North VDD M1 bus (1826.0..1834.0)
    for x_vdd in [100000, 1700000]:
        add_box(core_cell, li_m2, x_vdd, 1791400, x_vdd + 3400, 1834000)
        add_via1(core_cell, li_m1, li_v1, li_m2, x_vdd + 1700, 1793100)
        add_via1(core_cell, li_m1, li_v1, li_m2, x_vdd + 1700, 1828000)
        add_via1(core_cell, li_m1, li_v1, li_m2, x_vdd + 1700, 1832000)

    # Extra vertical M2 VSS straps from SRAM128 Top VSS rail (1796.8..1800.2) to North OSS_FRAME_GIO M2 VSS ring
    for x_vss in [150000, 1650000]:
        add_box(core_cell, li_m2, x_vss, 1796800, x_vss + 3400, y_north_vss)
        add_via1(core_cell, li_m1, li_v1, li_m2, x_vss + 1700, 1798500)

    # 3. North VDD M1 Bus (y = 1826.0..1834.0, width = 8.0 um) connecting West & East TAP2 VDD to P16 (VDDPAD)
    add_box(core_cell, li_m1, 28000, 1826000, 1818800, 1834000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 29700, 1828000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 29700, 1832000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1817100, 1828000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1817100, 1832000)

    if include_frame_bridges:
        # 13 x 8.0um-wide M1 fingers connecting North VDD M1 bus (y=1826..1834) to P16 M1 bar (x=970..1270, y=1840..1854)
        for xf in range(990000, 1240000, 20000):
            add_box(core_cell, li_m1, xf, 1826000, xf + 8000, 1844000)

        # 4. West & East Multi-Point VSS Bridges to OSS_FRAME_GIO M2 VSS Ring
        for y_vss in [27000, 172800, 1614600, 1796800]:
            add_box(core_cell, li_m2, x_west_vss, y_vss, 26000, y_vss + 3400)
        for y_vss in [27000, 172800, 464400, 756000, 1339200, 1614600, 1796800]:
            add_box(core_cell, li_m1, 1810000, y_vss, 1836700, y_vss + 3400)
            add_via1(core_cell, li_m1, li_v1, li_m2, 1835000, y_vss + 1700)
            add_box(core_cell, li_m2, 1833300, y_vss, x_east_vss, y_vss + 3400)

    # 5. South VDD M1 Segments (y = 3.6..7.0) for HIZ7 (x=338.3..341.7) and HIZ10 (x=1498.3..1501.7)
    add_box(core_cell, li_m1, 28000, 3600, 341700, 7000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 29700, 5300)
    add_box(core_cell, li_m1, 1498300, 3600, 1818800, 7000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1817100, 5300)

    if not include_frame_bridges:
        return

    # =========================================================================
    # 6. 16-Pad Signal, Output, and HIZ Connections
    # =========================================================================
    # --- NORTH PADS: P2 (sync, Out), P1 (clk, In), P15 (cm_rom, Out) ---
    add_box(core_cell, li_m2, 298000, 1795000, 301400, 1843400)
    add_box(core_cell, li_m2, 334000, 1840000, 346000, 1843400)

    add_box(core_cell, li_m2, 648300, 1818000, 651700, 1843400)
    add_box(core_cell, li_m1, 281800, 1818000, 651700, 1821400)
    add_via1(core_cell, li_m1, li_v1, li_m2, 650000, 1819700)
    add_via1(core_cell, li_m1, li_v1, li_m2, 283500, 1819700)
    add_box(core_cell, li_m2, 281800, 1795000, 285200, 1821400)
    add_box(core_cell, li_m1, 698300, 1826000, 701700, 1843400)
    add_box(core_cell, li_m2, 734000, 1840000, 746000, 1843400)

    add_box(core_cell, li_m2, 1538300, 1795000, 1543400, 1820000)
    add_box(core_cell, li_m2, 1538300, 1795000, 1541700, 1843400)
    add_box(core_cell, li_m2, 1494000, 1840000, 1506000, 1843400)

    # --- SOUTH PADS: P7 (rst, In), P8 (VSS), P9 (d_oe, Out), P10 (test, In) ---
    add_box(core_cell, li_m1, 388300, -3400, 391700, 6000)
    add_box(core_cell, li_m1, 388300, 2600, 393200, 6000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 391500, 4300)
    add_box(core_cell, li_m2, 389800, 2600, 393200, 25000)
    add_box(core_cell, li_m1, 338300, -3400, 341700, 7000)
    add_box(core_cell, li_m2, 294000, -3400, 306000, 0)

    add_box(core_cell, li_m2, 1097200, 2600, 1100600, 25000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1098900, 4300)
    add_box(core_cell, li_m1, 1097200, 2600, 1101700, 6000)
    add_box(core_cell, li_m1, 1098300, -3400, 1101700, 6000)
    add_box(core_cell, li_m2, 1134000, -3400, 1146000, 0)

    add_box(core_cell, li_m1, 1448300, -3400, 1451700, 6000)
    add_box(core_cell, li_m1, 1448200, 2600, 1451700, 6000)
    add_via1(core_cell, li_m1, li_v1, li_m2, 1449900, 4300)
    add_box(core_cell, li_m2, 1448200, 2600, 1451600, 25000)
    add_box(core_cell, li_m1, 1498300, -3400, 1501700, 7000)
    add_box(core_cell, li_m2, 1534000, -3400, 1546000, 0)

    # --- WEST PADS: P6 (D[0]), P5 (D[1]), P4 (D[2]), P3 (D[3]) ---
    # Shared d_hiz vertical M2 bus at x = 6.0..9.4 (center x = 7.7), y = 287.2..1501.7
    add_box(core_cell, li_m2, 6000, 287200, 9400, 1501700)
    add_box(core_cell, li_m1, 6000, 287200, 45000, 290600)
    add_via1(core_cell, li_m1, li_v1, li_m2, 7700, 288900)
    add_box(core_cell, li_m1, -3400, 338300, 9400, 341700)
    add_via1(core_cell, li_m1, li_v1, li_m2, 7700, 340000)
    for y_hiz in [700000, 1140000, 1500000]:
        add_box(core_cell, li_m1, -3400, y_hiz - 1700, 9400, y_hiz + 1700)
        add_via1(core_cell, li_m1, li_v1, li_m2, 7700, y_hiz)

    # P6 (D[0]):
    # d_out[0] (35.0..45.0, 304.1..306.1) -> OUT6 (-3.4..0.0, 298.3..301.7)
    add_box(core_cell, li_m1, 13000, 304100, 45000, 306100)
    add_box(core_cell, li_m1, 13000, 298300, 16400, 306100)
    add_box(core_cell, li_m1, -3400, 298300, 16400, 301700)
    # d_in[0] (35.0..45.0, 422.9..424.9) -> P6 (-3.4..0.0, 388.3..391.7)
    add_box(core_cell, li_m1, 13000, 422900, 45000, 424900)
    add_box(core_cell, li_m1, 13000, 388300, 16400, 424900)
    add_box(core_cell, li_m1, -3400, 388300, 16400, 391700)

    # P5 (D[1]):
    # d_in[1] (35.0..45.0, 698.3..700.3) -> P5 (-3.4..0.0, 648.3..651.7)
    add_box(core_cell, li_m1, 13000, 698300, 45000, 700300)
    add_box(core_cell, li_m1, 13000, 648300, 16400, 700300)
    add_box(core_cell, li_m1, -3400, 648300, 16400, 651700)
    # d_out[1] (35.0..45.0, 730.7..732.7) -> OUT5 (-3.4..0.0, 738.3..741.7)
    add_box(core_cell, li_m1, 13000, 730700, 45000, 732700)
    add_box(core_cell, li_m1, 13000, 730700, 16400, 741700)
    add_box(core_cell, li_m1, -3400, 738300, 16400, 741700)

    # P4 (D[2]):
    # d_out[2] (35.0..45.0, 1124.9..1126.9) -> OUT4 (-3.4..0.0, 1098.3..1101.7)
    add_box(core_cell, li_m1, 13000, 1124900, 45000, 1126900)
    add_box(core_cell, li_m1, 13000, 1098300, 16400, 1126900)
    add_box(core_cell, li_m1, -3400, 1098300, 16400, 1101700)
    # d_in[2] (35.0..45.0, 1162.7..1164.7) -> P4 (-3.4..0.0, 1188.3..1191.7)
    add_box(core_cell, li_m1, 13000, 1162700, 45000, 1164700)
    add_box(core_cell, li_m1, 13000, 1162700, 16400, 1191700)
    add_box(core_cell, li_m1, -3400, 1188300, 16400, 1191700)

    # P3 (D[3]):
    # d_in[3] (35.0..45.0, 1421.9..1423.9) -> P3 (-3.4..0.0, 1448.3..1451.7)
    add_box(core_cell, li_m1, 13000, 1421900, 45000, 1423900)
    add_box(core_cell, li_m1, 13000, 1421900, 16400, 1451700)
    add_box(core_cell, li_m1, -3400, 1448300, 16400, 1451700)
    # d_out[3] (35.0..45.0, 1567.7..1569.7) -> OUT3 (-3.4..0.0, 1538.3..1541.7)
    add_box(core_cell, li_m1, 13000, 1567700, 45000, 1569700)
    add_box(core_cell, li_m1, 13000, 1538300, 16400, 1569700)
    add_box(core_cell, li_m1, -3400, 1538300, 16400, 1541700)

    # --- EAST PADS: P11 (cm_ram[0]), P12 (cm_ram[1]), P13 (cm_ram[2]), P14 (cm_ram[3]) ---
    add_box(core_cell, li_m1, 1795000, 304100, 1828400, 306100)
    add_box(core_cell, li_m1, 1825000, 298300, 1828400, 306100)
    add_box(core_cell, li_m1, 1825000, 298300, 1843400, 301700)
    add_box(core_cell, li_m2, 1840000, 334000, 1843400, 346000)

    add_box(core_cell, li_m1, 1795000, 730700, 1828400, 732700)
    add_box(core_cell, li_m1, 1825000, 730700, 1828400, 741700)
    add_box(core_cell, li_m1, 1825000, 738300, 1843400, 741700)
    add_box(core_cell, li_m2, 1840000, 694000, 1843400, 706000)

    add_box(core_cell, li_m1, 1795000, 1124900, 1828400, 1126900)
    add_box(core_cell, li_m1, 1825000, 1098300, 1828400, 1126900)
    add_box(core_cell, li_m1, 1825000, 1098300, 1843400, 1101700)
    add_box(core_cell, li_m2, 1840000, 1134000, 1843400, 1146000)

    add_box(core_cell, li_m1, 1795000, 1567700, 1828400, 1569700)
    add_box(core_cell, li_m1, 1825000, 1538300, 1828400, 1569700)
    add_box(core_cell, li_m1, 1825000, 1538300, 1843400, 1541700)
    add_box(core_cell, li_m2, 1840000, 1494000, 1843400, 1506000)


def main():
    components, pins, m1_rects, m2_rects, v1_pts = parse_def(DEF_PATH)
    print(f"Loaded DEF: {len(components)} components, {len(pins)} pins, {len(m1_rects)} M1, {len(m2_rects)} M2, {len(v1_pts)} V1.")

    lay_core = pya.Layout()
    lay_core.dbu = 0.001
    c_core_only = lay_core.create_cell("c4004_core")
    build_core_and_power_shapes(c_core_only, lay_core, components, pins, m1_rects, m2_rects, v1_pts, include_frame_bridges=False)
    lay_core.write(OUT_CORE_GDS)
    print(f"Wrote {OUT_CORE_GDS}")

    lay_chip = pya.Layout()
    lay_chip.dbu = 0.001

    l_frame = pya.Layout()
    l_frame.read(FRAME_GDS)
    src_gio = l_frame.cell("OSS_FRAME_GIO")

    c_frame = lay_chip.create_cell("OSS_FRAME")
    c_frame.copy_tree(src_gio)

    li_txt = lay_chip.layer(49, 0)
    c_frame.shapes(li_txt).clear()
    pad_labels = [
        ("P1",  -200000,  1040000),
        ("P2",  -600000,  1040000),
        ("P3", -1040000,   600000),
        ("P4", -1040000,   200000),
        ("P5", -1040000,  -200000),
        ("P6", -1040000,  -600000),
        ("P7",  -600000, -1040000),
        ("VSS", -200000, -1040000),
        ("P9",   200000, -1040000),
        ("P10",  600000, -1040000),
        ("P11", 1040000,  -600000),
        ("P12", 1040000,  -200000),
        ("P13", 1040000,   200000),
        ("P14", 1040000,   600000),
        ("P15",  600000,  1040000),
        ("VDD",  200000,  1040000),
    ]
    for name, px, py in pad_labels:
        c_frame.shapes(li_txt).insert(pya.Text(name, pya.Trans(px, py)))

    c_core = lay_chip.create_cell("c4004_core")
    build_core_and_power_shapes(c_core, lay_chip, components, pins, m1_rects, m2_rects, v1_pts, include_frame_bridges=True)
    c_frame.insert(pya.CellInstArray(c_core.cell_index(), pya.Trans(0, False, CORE_OFFSET_X, CORE_OFFSET_Y)))

    lay_chip.write(OUT_CHIP_GDS)
    print(f"Wrote {OUT_CHIP_GDS}")

    c_sub = lay_chip.create_cell("tr_1um_jun1okamura")
    c_sub.insert(pya.CellInstArray(c_frame.cell_index(), pya.Trans(0, False, 0, 0)))
    for name, px, py in pad_labels:
        c_sub.shapes(li_txt).insert(pya.Text(name, pya.Trans(px, py)))

    lay_chip.write(OUT_SUB_GDS)
    print(f"Wrote {OUT_SUB_GDS}")
    lay_chip.write(OUT_IP62_GDS)
    print(f"Wrote {OUT_IP62_GDS}")


if __name__ == "__main__":
    main()
