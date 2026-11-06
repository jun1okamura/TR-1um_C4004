import re
from collections import defaultdict
import pya as db

STDCELL_GDS = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/module/STDCELL/TR-1um_STDCELL.gds"
FRAME_GDS = "/Users/okamura/.gemini/antigravity/brain/1f9962ab-4eaa-4573-b984-223fab1c8e03/scratch/TR-1um_frame_25x25.gds"
SRAM_GDS = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/module/SRAM128/SRAM128.gds"
DEF_PATH = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/apr/c4004_core_4edge_routed.def"
CORE_GDS_OUT = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/apr/c4004_core_routed.gds"
CHIP_GDS_OUT = "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/apr/c4004_chip.gds"

ROW_YS = [59400, 237600, 415800, 594000, 772200, 950400, 1128600, 1306800, 1485000]

def build_core_and_chip():
    ly = db.Layout()
    ly.dbu = 0.001
    ly.read(STDCELL_GDS)
    ly.read(SRAM_GDS)

    core = ly.create_cell("c4004_core")
    def_txt = open(DEF_PATH).read()

    # 1. Place components and track occupied sites per row
    occ_sites = defaultdict(set)
    comp_sec = def_txt.split("COMPONENTS")[1].split("END COMPONENTS")[0]
    comp_count = 0
    for m in re.finditer(r"-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)\s+N", comp_sec):
        inst, cell_name, cx, cy = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        cobj = ly.cell(cell_name)
        assert cobj is not None, f"Cell {cell_name} not found"
        if cell_name == "SRAM128":
            core.insert(db.CellInstArray(cobj.cell_index(), db.Trans(0, False, cx + 82100, cy + 90100)))
        else:
            core.insert(db.CellInstArray(cobj.cell_index(), db.Trans(0, False, cx, cy)))
            m1_b = db.Region(cobj.begin_shapes_rec(ly.layer(13, 0))).bbox()
            nsites = m1_b.width() // 5400
            s0 = cx // 5400
            for s in range(s0, s0 + nsites):
                occ_sites[cy].add(s)
        comp_count += 1

    # 2. Place 4 vertical TAP2 columns (left edge, 2 inner columns dividing into 3 equal segments, right edge)
    TAP_XS = [21600, 615600, 1215000, 1809000]
    tap_cell = ly.cell("TAP2")
    tap_count = 0
    for ry in ROW_YS:
        for tx in TAP_XS:
            core.insert(db.CellInstArray(tap_cell.cell_index(), db.Trans(0, False, tx, ry)))
            s0 = tx // 5400
            occ_sites[ry].add(s0)
            occ_sites[ry].add(s0 + 1)
            tap_count += 1

    # 3. Fill empty sites in x = 21600 .. 1819800 (sites 4 .. 336) with FILL3, FILL2, and FILL1
    #    Rule: Any contiguous empty space wider than FILL1 (>= 2 sites) is filled with FILL3 or FILL2 (zero FILL1 used in L>=2!).
    fill3_cell = ly.cell("FILL3")
    fill2_cell = ly.cell("FILL2")
    fill1_cell = ly.cell("FILL1")
    fill_counts = {3: 0, 2: 0, 1: 0}
    for ry in ROW_YS:
        s = 4
        while s <= 336:
            if s in occ_sites[ry]:
                s += 1
                continue
            s_end = s
            while s_end <= 336 and s_end not in occ_sites[ry]:
                s_end += 1
            rem = s_end - s
            cur_s = s
            while rem > 0:
                if rem == 4:
                    core.insert(db.CellInstArray(fill2_cell.cell_index(), db.Trans(0, False, cur_s * 5400, ry)))
                    core.insert(db.CellInstArray(fill2_cell.cell_index(), db.Trans(0, False, (cur_s + 2) * 5400, ry)))
                    fill_counts[2] += 2
                    cur_s += 4
                    rem = 0
                elif rem >= 3:
                    core.insert(db.CellInstArray(fill3_cell.cell_index(), db.Trans(0, False, cur_s * 5400, ry)))
                    fill_counts[3] += 1
                    cur_s += 3
                    rem -= 3
                elif rem == 2:
                    core.insert(db.CellInstArray(fill2_cell.cell_index(), db.Trans(0, False, cur_s * 5400, ry)))
                    fill_counts[2] += 1
                    cur_s += 2
                    rem -= 2
                else:
                    core.insert(db.CellInstArray(fill1_cell.cell_index(), db.Trans(0, False, cur_s * 5400, ry)))
                    fill_counts[1] += 1
                    cur_s += 1
                    rem -= 1
            s = s_end
    print(f"Placed {comp_count} components, {tap_count} TAP2 cells, and fillers: FILL3={fill_counts[3]}, FILL2={fill_counts[2]}, FILL1={fill_counts[1]}.")

    li_m1 = ly.layer(13, 0)
    li_v1 = ly.layer(19, 0)
    li_m2 = ly.layer(20, 0)

    # Fast spatial hash for V1 centers to avoid duplicate/too-close V1 cuts
    v1_grid = defaultdict(list)
    for p in db.Region(core.begin_shapes_rec(li_v1)).merged().each():
        b = p.bbox()
        cx, cy = (b.left + b.right) // 2, (b.bottom + b.top) // 2
        v1_grid[(cx // 3000, cy // 3000)].append((cx, cy))

    def add_m1_box(x0, y0, x1, y1):
        core.shapes(li_m1).insert(db.Box(min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1)))

    def add_m2_box(x0, y0, x1, y1):
        core.shapes(li_m2).insert(db.Box(min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1)))

    def add_via1(vx, vy):
        add_m1_box(vx - 1700, vy - 1700, vx + 1700, vy + 1700)
        add_m2_box(vx - 1700, vy - 1700, vx + 1700, vy + 1700)
        gx, gy = vx // 3000, vy // 3000
        for ix in (gx - 1, gx, gx + 1):
            for iy in (gy - 1, gy, gy + 1):
                for ox, oy in v1_grid.get((ix, iy), ()):
                    if abs(vx - ox) < 3200 and abs(vy - oy) < 3200:
                        return
        core.shapes(li_v1).insert(db.Box(vx - 700, vy - 700, vx + 700, vy + 700))
        v1_grid[(gx, gy)].append((vx, vy))

    # 3. Draw signal routing from DEF NETS
    nets_sec = def_txt.split("NETS")[1].split("END NETS")[0]
    seg_count, via_count = 0, 0
    for nm in re.finditer(r"-\s+(\S+)\s+.*?;", nets_sec, re.S):
        nname = nm.group(1)
        for sm in re.finditer(r"(METAL1|METAL2)\s+\(\s*(\d+)\s+(\d+)(?:\s+\d+)?\s*\)\s+\(\s*(\*|\d+)\s+(\*|\d+)", nm.group(0)):
            ly_s, x1, y1, x2s, y2s = sm.group(1), int(sm.group(2)), int(sm.group(3)), sm.group(4), sm.group(5)
            x2, y2 = (x1 if x2s == "*" else int(x2s)), (y1 if y2s == "*" else int(y2s))
            xlo, xhi, ylo, yhi = min(x1,x2), max(x1,x2), min(y1,y2), max(y1,y2)
            if nname in ("_0157_", "acc_1_bf0"):
                if ylo == 2700: ylo = 4000
                if yhi == 2700: yhi = 4000
            if nname == "cm_ram[3]" and xhi >= 1838000 and ylo >= 1540000:
                continue
            if ly_s == "METAL1":
                add_m1_box(xlo - 900, ylo - 900, xhi + 900, yhi + 900)
            else:
                # Clip top/bottom M2 pins at y = 4400 .. 1835600 so M2 edge is at y = 2700 .. 1837300 (>=2.7um from frame wall)
                by0 = max(2700, ylo - 1700)
                by1 = min(1837300, yhi + 1700)
                if by0 < by1:
                    add_m2_box(xlo - 1700, by0, xhi + 1700, by1)
            seg_count += 1
        for vm in re.finditer(r"METAL1\s+\(\s*(\d+)\s+(\d+)\s*\)\s+V1_1x1", nm.group(0)):
            vx, vy = int(vm.group(1)), int(vm.group(2))
            if nname in ("_0157_", "acc_1_bf0") and vy == 2700:
                vy = 4000
            if nname == "cm_ram[3]" and vx >= 1838000 and vy >= 1540000:
                continue
            add_via1(vx, vy)
            via_count += 1

    # Planar M1 right-edge connection for cm_ram[3] from (1806300, 1552500) to (1840000, 1540000):
    add_m1_box(1806300 - 900, 1552500 - 900, 1837000 + 900, 1552500 + 900)
    add_m1_box(1837000 - 900, 1540000 - 900, 1837000 + 900, 1552500 + 900)
    add_m1_box(1837000 - 900, 1540000 - 900, 1840000, 1540000 + 900)

    # 4. Add Core Power Grid (VDD and VSS) + Vertical TAP2 M2 Power Straps + OSS_FRAME_GIO Pad Tie-offs & Edge Bridges
    # 4a. Continuous vertical M2 power straps across all 9 rows for the 4 TAP2 columns:
    #     - All 4 TAP2 VSS M2 straps extend down to y = 0 (connecting directly to OSS_FRAME_GIO bottom M2 VSS wall).
    #     - Leftmost (tx=21600) and rightmost (tx=1809000) TAP2 VSS M2 straps extend all the way up to y = 1840000 (top M2 VSS wall).
    #     - Leftmost (tx=21600) TAP2 VDD M2 strap extends from y = 11800 up to y = 1821000 (connecting to Top VDD M1 bus -> VDDPAD).
    #     - Inner TAP2 columns connect up to u_sram bottom VSS/VDD bars where clear (col 1 VDD to 1604800, col 2 VSS/VDD to 1599400/1604800).
    for tx in TAP_XS:
        vss_y1 = 1840000 if tx in (21600, 1809000) else (1599400 if tx == 1215000 else 1543300)
        vdd_y0 = 11800 if tx == 21600 else 60500
        vdd_y1 = 1821000 if tx == 21600 else (1604800 if tx in (615600, 1215000) else 1543300)
        add_m2_box(tx + 1000, 0, tx + 4400, vss_y1)       # GND (VSS) vertical M2 strap
        add_m2_box(tx + 6400, vdd_y0, tx + 9800, vdd_y1)  # VDD vertical M2 strap

    # Right-side vertical M2 power columns (also extended to y = 0 and y = 1840000 to tie into OSS_FRAME_GIO bottom/top M2 VSS walls):
    add_m2_box(1826200, 55000, 1829600, 832000)
    add_m2_box(1826200, 1540300, 1829600, 1821000)
    add_m2_box(1831600, 0, 1835000, 954500)
    add_m2_box(1831600, 1485700, 1835000, 1840000)

    # 4b. Connect standard-cell rows' GND (VSS) and VDD M1 rails to left/right M2 columns AND OSS_FRAME_GIO M2 VSS walls (x=0, x=1840000):
    for ry in ROW_YS:
        # Left side: extend all 9 rows' VSS M1 rails to x=1000, add VIA1 at x=2700, and bridge M2 (0..4400) to OSS_FRAME_GIO left M2 VSS wall
        add_m1_box(1000, ry + 1100, 26000, ry + 3700)
        add_via1(2700, ry + 2400)
        add_m2_box(0, ry + 700, 4400, ry + 4100)

        # Right side: extend VSS M1 rails to right VSS M2 column (1833300) and bridge M2 (1831600..1840000) to OSS_FRAME_GIO right M2 VSS wall
        if ry <= 950400 or ry == 1485000:
            add_m1_box(1809000, ry + 1100, 1835000, ry + 3700)
            add_via1(1833300, ry + 2400)
            add_m2_box(1831600, ry + 700, 1840000, ry + 4100)
        if ry <= 772200 or ry == 1485000:
            add_m1_box(1809000, ry + 55700, 1829600, ry + 58300)
            add_via1(1827900, ry + 57000)
    # Tie HIZ13 (x=1840000, y=1140000) directly on M1 into Row 19 (ry=1128600) GND M1 rail:
    add_m1_box(1809000, 1128600 + 1100, 1840000, 1128600 + 3700)
    add_m1_box(1836600, 1128600 + 1100, 1840000, 1140000 + 1700)

    # 4c. Connect BOTH left-side (x=334800..338200) and right-side (x=1497500..1500900) M1 power bars of u_sram
    #     to the core TAP2 VDD/VSS straps, right-side M2 power columns, and left/right OSS_FRAME_GIO M2 VSS walls:
    # Left side of u_sram -> TAP2 col 0 (tx=21600: VSS=24300, VDD=29700) + left OSS_FRAME_GIO M2 VSS wall (x=0..4400):
    add_m1_box(1000, 1596000, 338200, 1599400)
    add_via1(24300, 1597700)
    add_via1(2700, 1597700)
    add_m2_box(0, 1596000, 4400, 1599400)

    add_m1_box(28000, 1601400, 338200, 1604800)
    add_via1(29700, 1603100)

    add_m1_box(28000, 1772800, 338200, 1776200)
    add_via1(29700, 1774500)

    add_m1_box(1000, 1778200, 338200, 1781600)
    add_via1(24300, 1779900)
    add_via1(2700, 1779900)
    add_m2_box(0, 1778200, 4400, 1781600)

    # Inner TAP2 columns (col 1 tx=615600, col 2 tx=1215000) -> u_sram bottom VSS/VDD bars:
    add_via1(623700, 1603100)
    add_via1(1217700, 1597700)
    add_via1(1223100, 1603100)

    # Right side of u_sram -> TAP2 col 3 (tx=1809000: VSS=1811700), right M2 columns (VDD=1827900, VSS=1833300), and right M2 VSS wall:
    add_m1_box(1497500, 1596000, 1835000, 1599400)
    add_via1(1811700, 1597700)
    add_via1(1833300, 1597700)
    add_m2_box(1831600, 1596000, 1840000, 1599400)

    add_m1_box(1497500, 1601400, 1829600, 1604800)
    add_via1(1827900, 1603100)

    add_m1_box(1497500, 1772800, 1829600, 1776200)
    add_via1(1827900, 1774500)

    add_m1_box(1497500, 1778200, 1835000, 1781600)
    add_via1(1811700, 1779900)
    add_via1(1833300, 1779900)
    add_m2_box(1831600, 1778200, 1840000, 1781600)

    # 4d. Top VDD M1 bus (y = 1816000..1821000) from left TAP2 VDD (x = 28000) to right VDD column (x = 1829600):
    add_m1_box(28000, 1816000, 1829600, 1821000)
    add_via1(29700, 1818500)
    add_via1(1827900, 1818500)
    # Connect HIZ1 (x = 700000, y = 1840000) directly on M1 to Top VDD M1 bus:
    add_m1_box(700000 - 1700, 1816000, 700000 + 1700, 1841700)
    # Connect OSS_FRAME_GIO top VDD M1 strap (x = 970000..1270000, y = 1840000) directly on M1 to Top VDD M1 bus:
    # Keep x = 970000..1270000 seamlessly across y = 1816000..1845000 so there is no step notch at x = 970000/1270000!
    add_m1_box(970000, 1816000, 1270000, 1845000)

    # 4e. Top GND (VSS) pad ties: tie HIZ2 (340000), OUT1 (740000), HIZ15 (1500000) directly into adjacent OSS_FRAME_GIO top VSS M2 wall (y = 1840000..1843400):
    add_m2_box(340000 - 1700, 1840000, 350000, 1843400)
    add_m2_box(740000 - 1700, 1840000, 750000, 1843400)
    add_m2_box(1490000, 1840000, 1500000 + 1700, 1843400)

    # 4f. Bottom VDD ties to HIZ7 (x = 340000) and HIZ10 (x = 1500000):
    # HIZ7: extend TAP2 col 0 VDD M2 strap (x = 29700) down to y = 13500, run M1 at y = 13500 to x = 342900, and M2 down to (340000, 0):
    add_m2_box(28000, 13500 - 1700, 31400, 60500)
    add_via1(29700, 13500)
    add_m1_box(29700 - 1700, 13500 - 900, 342900 + 1700, 13500 + 900)
    add_via1(342900, 13500)
    add_m2_box(342900 - 1700, 2000, 342900 + 1700, 13500 + 1700)
    add_m2_box(340000 - 1700, 2000, 342900 + 1700, 5000)
    add_m2_box(340000 - 1700, 0, 340000 + 1700, 5000)

    # HIZ10: from Row 1 VDD rail at x = 1493100 (i = 276) down to (1500000, 0):
    add_m1_box(1493100 - 1700, 115700, 1493100 + 1700, 120700)
    add_via1(1493100, 119000)
    add_m2_box(1493100 - 1700, 2000, 1493100 + 1700, 119000 + 1700)
    add_m2_box(1493100 - 1700, 2000, 1500000 + 1700, 5000)
    add_m2_box(1500000 - 1700, 0, 1500000 + 1700, 5000)

    # 4g. Bottom GND (VSS) pad ties: tie OUT7 (300000), HIZ9 (1140000), OUT10 (1540000) directly into adjacent OSS_FRAME_GIO bottom VSS M2 wall (y = -3400..0):
    add_m2_box(290000, -3400, 300000 + 1700, 0)
    add_m2_box(1140000 - 1700, -3400, 1150000, 0)
    add_m2_box(1540000 - 1700, -3400, 1550000, 0)

    # 4h. Right GND (VSS) horizontal M1 ties from right VSS M2 column (1833300) to HIZ11 (340000), HIZ12 (700000), HIZ14 (1500000):
    for gy in (340000, 700000, 1500000):
        add_via1(1833300, gy)
        add_m1_box(1833300 - 1700, gy - 1700, 1840000, gy + 1700)
    for wy in (520000, 920000):
        add_m2_box(1831600, wy - 5000, 1840000, wy + 5000)

    # 4i. Left d_hiz branches from x = 8100 M2 trunk to HIZ6 (340000), HIZ5 (700000), HIZ4 (1140000), HIZ3 (1500000):
    add_m2_box(8100 - 1700, 337500 - 1700, 8100 + 1700, 1500000 + 1700)
    for hy in (340000, 700000, 1140000, 1500000):
        add_via1(8100, hy)
        add_m1_box(0, hy - 1700, 8100 + 1700, hy + 1700)

    # 4j. Exact boundary alignment stubs at x=0, x=1840000, y=0, y=1840000:
    left_align = [
        (299700, 300000), (391500, 390000), (656100, 650000), (742500, 740000),
        (1098900, 1100000), (1190700, 1190000), (1449900, 1450000), (1547100, 1540000)
    ]
    for y_grid, y_pad in left_align:
        add_m1_box(0, min(y_grid - 900, y_pad - 1700), 2700, max(y_grid + 900, y_pad + 1700))

    for y_grid, y_pad in [(299700, 300000), (742500, 740000), (1098900, 1100000), (1540000, 1540000)]:
        add_m1_box(1837300, min(y_grid - 900, y_pad - 1700), 1840000, max(y_grid + 900, y_pad + 1700))

    # Bottom (y=0): rst (391500->390000), d_oe (1098900->1100000), test (1449900->1450000):
    add_m2_box(390000 - 1700, 1900, 391500 + 1700, 4900)
    add_m2_box(390000 - 1700, 0, 390000 + 1700, 4900)

    # For d_oe (x_grid=1098900, x_pad=1100000): keep M2 at x=1098900+-1700 down to y=2700,
    # and bridge on M2 [1098000, 1101700] at y=0..4400 (>=2.0um right of x=1096000 wall AND >=2.0um below y=6400)!
    add_m2_box(1098000, 0, 1100000 + 1700, 4400)

    add_m2_box(1449900 - 1700, 1900, 1450000 + 1700, 4900)
    add_m2_box(1450000 - 1700, 0, 1450000 + 1700, 4900)

    # Top (y=1840000): keep shifted bridge at y=1834800..1837800 (width 3.0um, >=2.2um from y=1840000 wall)!
    for x_grid, x_pad in [(299700, 300000), (650700, 650000), (1541700, 1540000)]:
        add_m2_box(min(x_grid - 1700, x_pad - 1700), 1834800, max(x_grid + 1700, x_pad + 1700), 1837800)
        add_m2_box(x_pad - 1700, 1834800, x_pad + 1700, 1840000)

    ly.write(CORE_GDS_OUT)
    print(f"Wrote {CORE_GDS_OUT} (segs={seg_count}, vias={via_count})")

    # 5. Assemble Top-Level Chip in OSS_FRAME_GIO
    chip_ly = db.Layout()
    chip_ly.dbu = 0.001
    chip_ly.read(FRAME_GDS)

    opts = db.LoadLayoutOptions()
    opts.cell_conflict_resolution = db.LoadLayoutOptions.CellConflictResolution.RenameCell
    chip_ly.read(CORE_GDS_OUT, opts)

    frame_cell = chip_ly.cell("OSS_FRAME_GIO")
    core_in_chip = chip_ly.cell("c4004_core")
    assert frame_cell is not None and core_in_chip is not None

    frame_cell.insert(db.CellInstArray(core_in_chip.cell_index(), db.Trans(0, False, -920000, -920000)))

    for tc in list(chip_ly.top_cells()):
        if tc.cell_index() != frame_cell.cell_index():
            chip_ly.prune_cell(tc.cell_index(), -1)
    frame_cell.name = "OSS_FRAME"

    li_m2pin_c = chip_ly.layer(49, 1)
    li_txm2_c = chip_ly.layer(49, 0)
    # Remove internal pad-ring macro pin labels (HIZ1..15, OUT1..15) from top cell OSS_FRAME
    # so top-level ports of OSS_FRAME are strictly the 16 bondpads (P1..P7, VSS, P9..P15, VDD)
    # without multi-label port name concatenation ('HIZ1,HIZ10,HIZ7,VDD' vs 'VDD').
    valid_top_labels = {
        "P1", "P2", "P3", "P4", "P5", "P6", "P7", "VSS",
        "P9", "P10", "P11", "P12", "P13", "P14", "P15", "VDD"
    }
    kept_texts = []
    for s in frame_cell.shapes(li_txm2_c).each():
        if s.is_text() and s.text.string in valid_top_labels:
            kept_texts.append(s.text)
    frame_cell.shapes(li_txm2_c).clear()
    for t in kept_texts:
        frame_cell.shapes(li_txm2_c).insert(t)

    top_pads = [
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
    for pname, px, py in top_pads:
        pbox = db.Box(px - 10000, py - 10000, px + 10000, py + 10000)
        frame_cell.shapes(li_m2pin_c).insert(pbox)

    chip_ly.write(CHIP_GDS_OUT)
    print(f"Wrote {CHIP_GDS_OUT}")

build_core_and_chip()
