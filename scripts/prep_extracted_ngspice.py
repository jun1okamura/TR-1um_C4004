from pathlib import Path
#!/usr/bin/env python3
"""
Prepare OSS_FRAME.extracted for ngspice simulation (using native M devices for
PMOS_mst / NMOS_mst) and verify subcircuit port counts.
"""
import os
import re

WORKSPACE = str(Path(__file__).resolve().parent.parent)
EXTRACTED_PATH = os.path.join(WORKSPACE, "apr/OSS_FRAME.extracted")
SIM_DIR = os.path.join(WORKSPACE, "apr/simulation")
SIM_NETLIST_PATH = os.path.join(SIM_DIR, "OSS_FRAME_extracted_sim.spice")
MODELS_PATH = os.path.join(SIM_DIR, "models.spice")
IP62_LIB_SRC = "TR-1um/libs.tech/spice/models/models_IP62_mos_v2.lib"


def sanitize_token(tok):
    tok = tok.replace("\\$", "n")
    tok = tok.replace("$", "_")
    tok = re.sub(r"\[(\d+)\]", r"_\1", tok)
    tok = tok.replace("|", "_")
    return tok


def convert_extracted_for_ngspice(src_path, dst_path):
    with open(src_path, "r") as f:
        raw_lines = f.readlines()

    joined = []
    for line in raw_lines:
        s = line.rstrip("\r\n")
        if s.startswith("+") and joined:
            joined[-1] += " " + s[1:].strip()
        else:
            joined.append(s)

    subckt_ports = {}
    x_calls = []

    out_lines = [
        "* NGSPICE-ready full-chip extracted netlist from KLayout LVS (OSS_FRAME.extracted)",
        "* Source: apr/OSS_FRAME.extracted",
        ""
    ]

    cur_sub = None
    for line in joined:
        s = line.strip()
        if not s:
            out_lines.append("")
            continue
        if s.startswith("*"):
            out_lines.append(s)
            continue

        parts = s.split()
        head_up = parts[0].upper()

        if head_up == ".SUBCKT":
            sub_name = sanitize_token(parts[1])
            ports = [sanitize_token(p) for p in parts[2:]]
            cur_sub = sub_name
            subckt_ports[sub_name] = ports
            out_lines.append(f".SUBCKT {sub_name} " + " ".join(ports))
        elif head_up == ".ENDS":
            cur_sub = None
            if len(parts) > 1:
                out_lines.append(f".ENDS {sanitize_token(parts[1])}")
            else:
                out_lines.append(".ENDS")
        elif head_up.startswith("XM"):
            # Convert XM$id -> native M_id calling PMOS_mst or NMOS_mst directly
            inst_name = "M" + sanitize_token(parts[0][2:])
            d, g, src, b = [sanitize_token(p) for p in parts[1:5]]
            orig_model = parts[5].upper()
            model = "PMOS_mst" if orig_model.startswith("P") else "NMOS_mst"
            params = {}
            for p in parts[6:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k.upper()] = v

            w_str = params.get("W", "3.4u")
            if w_str.endswith("u"):
                w_um = float(w_str[:-1])
                if w_um >= 100.0:
                    m_val = int(round(w_um / 50.0))
                    w_each = w_um / m_val
                    params["W"] = f"{w_each:g}u"
                    for area_k in ("AS", "AD"):
                        if area_k in params and params[area_k].endswith("p"):
                            val = float(params[area_k][:-1]) / m_val
                            params[area_k] = f"{val:.4g}p"
                    for perim_k in ("PS", "PD"):
                        if perim_k in params and params[perim_k].endswith("u"):
                            val = float(params[perim_k][:-1]) / m_val
                            params[perim_k] = f"{val:.4g}u"
                    params["M"] = str(m_val)

            param_str = " ".join(f"{k}={v}" for k, v in params.items())
            out_lines.append(f"{inst_name} {d} {g} {src} {b} {model} {param_str}")
        elif head_up.startswith("D"):
            inst_name = sanitize_token(parts[0])
            n1, n2 = sanitize_token(parts[1]), sanitize_token(parts[2])
            model = parts[3]
            params = []
            for p in parts[4:]:
                if p.upper().startswith("A="):
                    params.append("AREA=" + p.split("=", 1)[1])
                elif p.upper().startswith("P="):
                    params.append("PJ=" + p.split("=", 1)[1])
                else:
                    params.append(p)
            out_lines.append(f"{inst_name} {n1} {n2} {model} " + " ".join(params))
        elif head_up.startswith("X"):
            inst_name = sanitize_token(parts[0])
            tokens = [sanitize_token(p) for p in parts[1:]]
            x_calls.append((cur_sub, inst_name, tokens[-1], len(tokens) - 1))
            out_lines.append(f"{inst_name} " + " ".join(tokens))
        else:
            out_lines.append(s)

    for parent, inst, child, n_args in x_calls:
        exp = len(subckt_ports.get(child, []))
        if n_args != exp:
            print(f"MISMATCH in {parent}.{inst} calling {child}: passed {n_args} nets, expected {exp}")

    with open(dst_path, "w") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"Wrote ngspice netlist: {dst_path} ({len(out_lines)} lines, verified {len(x_calls)} X-calls)")


def create_models_file(src_lib, dst_models):
    with open(src_lib, "r") as f:
        raw_lines = f.readlines()

    # Keep only .param and .model PMOS_mst / NMOS_mst lines (skip .subckt PMOS/NMOS)
    keep = []
    skip_sub = False
    for line in raw_lines:
        s = line.strip()
        if s.lower().startswith(".subckt"):
            skip_sub = True
            continue
        if s.lower().startswith(".ends"):
            skip_sub = False
            continue
        if not skip_sub:
            keep.append(line.rstrip("\r\n"))

    header = """* OpenSUSI TR-1um (IP62 5V 1um CMOS) BSIM3v3.3 + Diode Models for NGSPICE
* N+/P-well ESD Protection Diode Model (1um CMOS 5V)
.model DN D (IS=1e-14 RS=5 N=1.05 CJ0=7.44e-4 CJSW=2.3e-10 VJ=0.85 M=0.36 BV=14.0 IBV=1e-3)
"""
    with open(dst_models, "w") as f:
        f.write(header + "\n" + "\n".join(keep) + "\n")
    print(f"Wrote models file: {dst_models}")


if __name__ == "__main__":
    os.makedirs(SIM_DIR, exist_ok=True)
    convert_extracted_for_ngspice(EXTRACTED_PATH, SIM_NETLIST_PATH)
    create_models_file(IP62_LIB_SRC, MODELS_PATH)
