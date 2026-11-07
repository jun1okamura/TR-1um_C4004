#!/usr/bin/env python3
"""
Convert TR-1um_cells.lef into clean RECT-decomposed LEFs for OpenROAD:
1. TR-1um_cells_grt.lef: Signal pins on LAYER METAL1 (so FastRoute uses METAL1+METAL2 and finishes in 0.00s)
2. TR-1um_cells_drt.lef: Signal pins on LAYER METAL1 and LAYER METAL2 (so TritonRoute sees the M1+M2 pin pads)
Also:
- Decomposes all Manhattan POLYGON shapes into exact non-overlapping RECT shapes.
- Moves internal SPICE nodes (CKB, CKP, QM, QS) into OBS LAYER METAL1.
- Adds PIN vdd / PIN vss rectangles into OBS LAYER METAL1 so signal wires never short against power rails.
- Sets accurate DIRECTION INPUT / OUTPUT from Liberty.
"""
import re
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent.parent
STDCELL_DIR = Path(str(Path(__file__).resolve().parent.parent / "module/STDCELL")
OUT_DIR = SCRATCH / "or_test"

def parse_lib_directions(lib_path: Path):
    text = lib_path.read_text()
    dirs = {}
    for cm in re.finditer(r'cell\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{(.*?)\n  \}', text, re.S):
        cname, cbody = cm.group(1), cm.group(2)
        dirs[cname] = {}
        for pm in re.finditer(r'pin\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{([^}]*)\}', cbody, re.S):
            pname, pbody = pm.group(1), pm.group(2)
            dm = re.search(r'direction\s*:\s*(input|output|inout)\s*;', pbody)
            if dm:
                dirs[cname][pname] = dm.group(1).upper()
    return dirs

def point_in_manhattan_poly(px, py, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            # vertical or slanted edge crossing py
            x_int = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < x_int:
                inside = not inside
    return inside

def decompose_polygons_to_rects(polys, existing_rects):
    """Decompose a list of Manhattan polygons + existing rects into clean horizontal-merged vertical-merged rects."""
    xs = set()
    ys = set()
    for pts in polys:
        for x, y in pts:
            xs.add(round(x, 3))
            ys.add(round(y, 3))
    for x1, y1, x2, y2 in existing_rects:
        xs.update([round(x1, 3), round(x2, 3)])
        ys.update([round(y1, 3), round(y2, 3)])
    xs = sorted(xs)
    ys = sorted(ys)
    if len(xs) < 2 or len(ys) < 2:
        return []

    nx = len(xs) - 1
    ny = len(ys) - 1
    grid = [[False] * nx for _ in range(ny)]

    for j in range(ny):
        ymid = 0.5 * (ys[j] + ys[j + 1])
        for i in range(nx):
            xmid = 0.5 * (xs[i] + xs[i + 1])
            val = False
            for rx1, ry1, rx2, ry2 in existing_rects:
                if rx1 <= xmid <= rx2 and ry1 <= ymid <= ry2:
                    val = True
                    break
            if not val:
                for pts in polys:
                    if point_in_manhattan_poly(xmid, ymid, pts):
                        val = True
                        break
            grid[j][i] = val

    # First merge horizontally per y-row
    row_spans = []
    for j in range(ny):
        spans = []
        i = 0
        while i < nx:
            if grid[j][i]:
                i_start = i
                while i < nx and grid[j][i]:
                    i += 1
                spans.append((xs[i_start], xs[i]))
            else:
                i += 1
        row_spans.append((ys[j], ys[j + 1], spans))

    # Merge vertically identical x-spans across adjacent y-rows
    active = {}  # (x1, x2) -> [y_start, y_end]
    final_rects = []
    for y1, y2, spans in row_spans:
        span_set = set(spans)
        for sp in list(active.keys()):
            if sp not in span_set:
                vy1, vy2 = active.pop(sp)
                final_rects.append((sp[0], vy1, sp[1], vy2))
        for sp in spans:
            if sp in active:
                active[sp][1] = y2
            else:
                active[sp] = [y1, y2]
    for sp, (vy1, vy2) in active.items():
        final_rects.append((sp[0], vy1, sp[1], vy2))

    return final_rects

def parse_shapes_from_port(port_text):
    """Return dict layer -> (list_of_polys, list_of_rects)"""
    layers = {}
    cur_layer = None
    for line in port_text.splitlines():
        s = line.strip()
        m_lay = re.match(r'LAYER\s+(\S+)\s*;', s)
        if m_lay:
            cur_layer = m_lay.group(1)
            layers.setdefault(cur_layer, ([], []))
            continue
        m_rect = re.match(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;', s)
        if m_rect and cur_layer:
            x1, y1, x2, y2 = map(float, m_rect.groups())
            layers[cur_layer][1].append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            continue
        m_poly = re.match(r'POLYGON\s+(.*?)\s*;', s)
        if m_poly and cur_layer:
            nums = list(map(float, m_poly.group(1).split()))
            pts = [(nums[k], nums[k + 1]) for k in range(0, len(nums), 2)]
            if len(pts) > 1 and pts[0] == pts[-1]:
                pts = pts[:-1]
            layers[cur_layer][0].append(pts)
    return layers

def build_lefs():
    lib_dirs = parse_lib_directions(STDCELL_DIR / "tr1um_typ_5v0_25c.lib")
    raw_lef = (STDCELL_DIR / "TR-1um_cells.lef").read_text()

    macro_pattern = re.compile(r'(MACRO\s+([A-Za-z0-9_]+)\s*\n.*?END\s+\2)', re.S)
    grt_macros = []
    drt_macros = []

    internal_pins = {"CKB", "CKP", "QM", "QS"}

    for mm in macro_pattern.finditer(raw_lef):
        m_text, m_name = mm.group(1), mm.group(2)
        c_dirs = lib_dirs.get(m_name, {})

        # Extract header before first PIN or OBS
        first_pin = re.search(r'\n\s*(PIN|OBS)\b', m_text)
        header = m_text[:first_pin.start()] if first_pin else m_text

        # Extract all PIN blocks
        pin_pattern = re.compile(r'  PIN\s+([A-Za-z0-9_]+)\s*\n(.*?)\n  END\s+\1', re.S)
        obs_pattern = re.compile(r'  OBS\s*\n(.*?)\n  END', re.S)

        obs_m1_polys = []
        obs_m1_rects = []
        obs_m2_polys = []
        obs_m2_rects = []

        for om in obs_pattern.finditer(m_text):
            layers = parse_shapes_from_port(om.group(1))
            if "METAL1" in layers:
                obs_m1_polys.extend(layers["METAL1"][0])
                obs_m1_rects.extend(layers["METAL1"][1])
            if "METAL2" in layers:
                obs_m2_polys.extend(layers["METAL2"][0])
                obs_m2_rects.extend(layers["METAL2"][1])

        pins_grt_str = []
        pins_drt_str = []
        signal_pin_rects = []

        for pm in pin_pattern.finditer(m_text):
            pname, pbody = pm.group(1), pm.group(2)
            layers = parse_shapes_from_port(pbody)

            if pname in internal_pins:
                for lay, (polys, rects) in layers.items():
                    obs_m1_polys.extend(polys)
                    obs_m1_rects.extend(rects)
                continue

            if pname.lower() in ("vdd", "vss"):
                # Keep power pin definition AND add its shapes to OBS METAL1 so signal nets never cross vdd/vss rails!
                p_rects = []
                for lay, (polys, rects) in layers.items():
                    decomposed = decompose_polygons_to_rects(polys, rects)
                    p_rects.extend(decomposed)
                    obs_m1_rects.extend(decomposed)
                use_type = "POWER" if pname.lower() == "vdd" else "GROUND"
                p_lines = [
                    f"  PIN {pname}",
                    f"    DIRECTION INOUT ;",
                    f"    USE {use_type} ;",
                    f"    PORT",
                    f"      LAYER METAL1 ;",
                ]
                for x1, y1, x2, y2 in p_rects:
                    p_lines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
                p_lines.extend(["    END", f"  END {pname}"])
                p_block = "\n".join(p_lines)
                pins_grt_str.append(p_block)
                pins_drt_str.append(p_block)
                continue

            # Signal pin
            p_dir = c_dirs.get(pname, "INOUT")
            p_rects = []
            for lay, (polys, rects) in layers.items():
                p_rects.extend(decompose_polygons_to_rects(polys, rects))
            signal_pin_rects.extend(p_rects)

            # GRT version: LAYER METAL1 only
            g_lines = [
                f"  PIN {pname}",
                f"    DIRECTION {p_dir} ;",
                f"    USE SIGNAL ;",
                f"    PORT",
                f"      LAYER METAL1 ;",
            ]
            for x1, y1, x2, y2 in p_rects:
                g_lines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
            g_lines.extend(["    END", f"  END {pname}"])
            pins_grt_str.append("\n".join(g_lines))

            # DRT version: LAYER METAL1 and LAYER METAL2
            d_lines = [
                f"  PIN {pname}",
                f"    DIRECTION {p_dir} ;",
                f"    USE SIGNAL ;",
                f"    PORT",
                f"      LAYER METAL1 ;",
            ]
            for x1, y1, x2, y2 in p_rects:
                d_lines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
            d_lines.append("      LAYER METAL2 ;")
            for x1, y1, x2, y2 in p_rects:
                d_lines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
            d_lines.extend(["    END", f"  END {pname}"])
            pins_drt_str.append("\n".join(d_lines))

        # Decompose OBS METAL1 into rectangles, subtracting signal_pin_rects so OBS never overlaps signal pins!
        all_obs_m1 = decompose_polygons_to_rects(obs_m1_polys, obs_m1_rects)
        # Subtract signal_pin_rects (with 0.0 margin so exact pin rect is free on METAL1, or keep OBS outside pin rect)
        # Wait: in TR-1um_cells.lef, OBS METAL1 already had cutouts around the 3.4x3.4 signal pin pads (or touched their edges).
        # Let's check if any all_obs_m1 overlaps signal_pin_rects and subtract if needed:
        clean_obs_m1 = subtract_rects(all_obs_m1, signal_pin_rects)
        clean_obs_m2 = decompose_polygons_to_rects(obs_m2_polys, obs_m2_rects)

        obs_lines = ["  OBS"]
        if clean_obs_m1:
            obs_lines.append("    LAYER METAL1 ;")
            for x1, y1, x2, y2 in clean_obs_m1:
                obs_lines.append(f"      RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
        if clean_obs_m2:
            obs_lines.append("    LAYER METAL2 ;")
            for x1, y1, x2, y2 in clean_obs_m2:
                obs_lines.append(f"      RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
        obs_lines.append("  END")
        obs_block = "\n".join(obs_lines)

        grt_macros.append(header + "\n" + "\n".join(pins_grt_str) + "\n" + obs_block + f"\nEND {m_name}")
        drt_macros.append(header + "\n" + "\n".join(pins_drt_str) + "\n" + obs_block + f"\nEND {m_name}")

    header_top = "VERSION 5.7 ;\nBUSBITCHARS \"[]\" ;\nDIVIDERCHAR \"/\" ;\n\n"
    footer_bot = "\n\nEND LIBRARY\n"
    (OUT_DIR / "TR-1um_cells_grt.lef").write_text(header_top + "\n\n".join(grt_macros) + footer_bot)
    (OUT_DIR / "TR-1um_cells_drt.lef").write_text(header_top + "\n\n".join(drt_macros) + footer_bot)
    print(f"Generated {len(grt_macros)} macros in TR-1um_cells_grt.lef and TR-1um_cells_drt.lef")

def subtract_rects(base_rects, cut_rects):
    if not base_rects:
        return []
    if not cut_rects:
        return base_rects
    xs = set()
    ys = set()
    for x1, y1, x2, y2 in base_rects + cut_rects:
        xs.update([round(x1, 3), round(x2, 3)])
        ys.update([round(y1, 3), round(y2, 3)])
    xs = sorted(xs)
    ys = sorted(ys)
    nx, ny = len(xs) - 1, len(ys) - 1
    grid = [[False] * nx for _ in range(ny)]
    for j in range(ny):
        ymid = 0.5 * (ys[j] + ys[j + 1])
        for i in range(nx):
            xmid = 0.5 * (xs[i] + xs[i + 1])
            in_base = any(rx1 <= xmid <= rx2 and ry1 <= ymid <= ry2 for rx1, ry1, rx2, ry2 in base_rects)
            if in_base:
                in_cut = any(cx1 <= xmid <= cx2 and cy1 <= ymid <= cy2 for cx1, cy1, cx2, cy2 in cut_rects)
                grid[j][i] = not in_cut
    row_spans = []
    for j in range(ny):
        spans = []
        i = 0
        while i < nx:
            if grid[j][i]:
                i_start = i
                while i < nx and grid[j][i]:
                    i += 1
                spans.append((xs[i_start], xs[i]))
            else:
                i += 1
        row_spans.append((ys[j], ys[j + 1], spans))
    active = {}
    final_rects = []
    for y1, y2, spans in row_spans:
        span_set = set(spans)
        for sp in list(active.keys()):
            if sp not in span_set:
                vy1, vy2 = active.pop(sp)
                final_rects.append((sp[0], vy1, sp[1], vy2))
        for sp in spans:
            if sp in active:
                active[sp][1] = y2
            else:
                active[sp] = [y1, y2]
    for sp, (vy1, vy2) in active.items():
        final_rects.append((sp[0], vy1, sp[1], vy2))
    return final_rects

if __name__ == "__main__":
    build_lefs()
