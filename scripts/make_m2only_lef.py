#!/usr/bin/env python3
"""
Generate TR-1um_cells_m2only.lef where:
1. Every standard cell has FULL-CELL OBS LAYER METAL1 (RECT 0.000 0.000 <width> 59.400)
   so NO M1 signal routing or M1 pin access is ever allowed over a standard cell!
2. All signal pins (PIN A, B, Y, etc.) are ONLY on LAYER METAL2.
3. Internal probe labels (CKB, CKP, QM, QS) are omitted from PINs.
4. Pin directions (INPUT / OUTPUT) are set from tr1um_typ_5v0_25c.lib.
5. Existing OBS LAYER METAL2 shapes (if any) are decomposed into clean RECTs.
"""
import re
from pathlib import Path
from make_clean_lefs import parse_lib_directions, parse_shapes_from_port, decompose_polygons_to_rects

SCRATCH = Path(__file__).resolve().parent.parent
STDCELL_DIR = Path(str(Path(__file__).resolve().parent.parent / "module/STDCELL")
OUT_DIR = SCRATCH / "or_test"

def main():
    lib_dirs = parse_lib_directions(STDCELL_DIR / "tr1um_typ_5v0_25c.lib")
    raw_lef = (STDCELL_DIR / "TR-1um_cells.lef").read_text()

    macro_pattern = re.compile(r'(MACRO\s+([A-Za-z0-9_]+)\s*\n.*?END\s+\2)', re.S)
    macros_out = []
    internal_pins = {"CKB", "CKP", "QM", "QS"}

    for mm in macro_pattern.finditer(raw_lef):
        m_text, m_name = mm.group(1), mm.group(2)
        c_dirs = lib_dirs.get(m_name, {})

        size_m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', m_text)
        w, h = float(size_m.group(1)), float(size_m.group(2))

        first_pin = re.search(r'\n\s*(PIN|OBS)\b', m_text)
        header = m_text[:first_pin.start()] if first_pin else m_text

        pin_pattern = re.compile(r'  PIN\s+([A-Za-z0-9_]+)\s*\n(.*?)\n  END\s+\1', re.S)
        obs_pattern = re.compile(r'  OBS\s*\n(.*?)\n  END', re.S)

        obs_m2_polys = []
        obs_m2_rects = []
        for om in obs_pattern.finditer(m_text):
            layers = parse_shapes_from_port(om.group(1))
            if "METAL2" in layers:
                obs_m2_polys.extend(layers["METAL2"][0])
                obs_m2_rects.extend(layers["METAL2"][1])

        pins_str = []
        for pm in pin_pattern.finditer(m_text):
            pname, pbody = pm.group(1), pm.group(2)
            if pname in internal_pins:
                continue
            layers = parse_shapes_from_port(pbody)
            if pname.lower() in ("vdd", "vss"):
                # Power/ground pins on METAL1 (covered by full-cell OBS LAYER METAL1 for signals)
                p_rects = []
                for lay, (polys, rects) in layers.items():
                    p_rects.extend(decompose_polygons_to_rects(polys, rects))
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
                pins_str.append("\n".join(p_lines))
                continue

            # Signal pin: ONLY on LAYER METAL2
            p_dir = c_dirs.get(pname, "INOUT")
            p_rects = []
            for lay, (polys, rects) in layers.items():
                p_rects.extend(decompose_polygons_to_rects(polys, rects))
            p_lines = [
                f"  PIN {pname}",
                f"    DIRECTION {p_dir} ;",
                f"    USE SIGNAL ;",
                f"    PORT",
                f"      LAYER METAL2 ;",
            ]
            for x1, y1, x2, y2 in p_rects:
                p_lines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
            p_lines.extend(["    END", f"  END {pname}"])
            pins_str.append("\n".join(p_lines))

        clean_obs_m2 = decompose_polygons_to_rects(obs_m2_polys, obs_m2_rects)
        y_obs_min = 1.1 if abs(h - 59.4) < 0.1 else 0.0
        y_obs_max = (h - 1.1) if abs(h - 59.4) < 0.1 else h
        obs_lines = [
            "  OBS",
            "    LAYER METAL1 ;",
            f"      RECT 0.000 {y_obs_min:.3f} {w:.3f} {y_obs_max:.3f} ;",
        ]
        if clean_obs_m2:
            obs_lines.append("    LAYER METAL2 ;")
            for x1, y1, x2, y2 in clean_obs_m2:
                obs_lines.append(f"      RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
        obs_lines.append("  END")

        macros_out.append(header + "\n" + "\n".join(pins_str) + "\n" + "\n".join(obs_lines) + f"\nEND {m_name}")

    out_path = OUT_DIR / "TR-1um_cells_m2only.lef"
    out_path.write_text("VERSION 5.7 ;\nBUSBITCHARS \"[]\" ;\nDIVIDERCHAR \"/\" ;\n\n" + "\n\n".join(macros_out) + "\n\nEND LIBRARY\n")
    print(f"Wrote {out_path} with {len(macros_out)} macros (Full-cell M1 OBS, M2-only signal pins).")

if __name__ == "__main__":
    main()
