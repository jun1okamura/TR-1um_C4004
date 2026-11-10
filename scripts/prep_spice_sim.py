#!/usr/bin/env python3
"""
Convert KLayout extracted netlist (apr/OSS_FRAME.extracted) into an ngspice-ready
post-layout simulation netlist (apr/OSS_FRAME_sim.spice), and report full-chip
device/cell/net statistics.
"""

import os
import re
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_PATH = os.path.join(BASE_DIR, "apr", "OSS_FRAME.extracted")
SIM_OUT_PATH = os.path.join(BASE_DIR, "apr", "OSS_FRAME_sim.spice")


def join_continuation_lines(raw_lines):
    joined = []
    for line in raw_lines:
        s = line.strip()
        if not s or s.startswith("*"):
            continue
        if s.startswith("+") and joined:
            joined[-1] += " " + s[1:].strip()
        else:
            joined.append(s)
    return joined


def convert_extracted_for_ngspice(ext_path, out_path):
    with open(ext_path, "r") as f:
        raw_lines = f.read().splitlines()

    joined = join_continuation_lines(raw_lines)
    out_lines = [
        "* Post-Layout Extracted Netlist of OSS_FRAME prepared for ngspice",
    ]

    for line in joined:
        # Clean KLayout escaped identifiers: \$ -> _n_, | -> _
        clean = line.replace("\\$", "_n_").replace("$", "_d_").replace("|", "_")

        # Convert MOSFET lines starting with XM to direct M devices using *_mst models
        if re.match(r"^XM", clean):
            clean = re.sub(r"^XM", "M", clean)
            clean = re.sub(r"\bPMOS\b", "PMOS_mst", clean)
            clean = re.sub(r"\bNMOS\b", "NMOS_mst", clean)
            clean = re.sub(r"\bNMOSE\b", "MNE_mst", clean)

            # Check if W >= 100u and split into W=50u M=fingers, scaling AS/AD/PS/PD by 1/fingers
            m_w = re.search(r"\bW=([0-9.]+)u\b", clean)
            if m_w:
                w_val = float(m_w.group(1))
                if w_val >= 100.0:
                    fingers = int(round(w_val / 50.0))
                    w_each = w_val / fingers
                    clean = re.sub(r"\bW=[0-9.]+u\b", f"W={w_each:g}u M={fingers}", clean)
                    for param, unit in [("AS", "p"), ("AD", "p"), ("PS", "u"), ("PD", "u")]:
                        mp = re.search(rf"\b{param}=([0-9.]+){unit}\b", clean)
                        if mp:
                            val = float(mp.group(1)) / fingers
                            clean = re.sub(rf"\b{param}=[0-9.]+{unit}\b", f"{param}={val:.4g}{unit}", clean)
        elif re.match(r"^D", clean):
            clean = re.sub(r"\bA=([0-9.]+p)\b", r"AREA=\1", clean)
            clean = re.sub(r"\bP=([0-9.]+u)\b", r"PJ=\1", clean)

        out_lines.append(clean)

    with open(out_path, "w") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"Wrote {out_path} ({len(out_lines)} lines)")


def compute_hierarchical_stats(ext_path):
    """Compute exact flat transistor/diode counts across the full chip from OSS_FRAME.extracted."""
    with open(ext_path, "r") as f:
        raw_lines = f.read().splitlines()
    joined = join_continuation_lines(raw_lines)

    subckts = {}
    i = 0
    while i < len(joined):
        s = joined[i]
        if s.startswith(".SUBCKT "):
            name = s.split()[1]
            body = []
            i += 1
            while i < len(joined):
                if joined[i].startswith(".ENDS"):
                    i += 1
                    break
                body.append(joined[i])
                i += 1
            subckts[name] = body
        else:
            i += 1

    def count_in_subckt(name, count_fingers=False):
        counts = Counter()
        for stmt in subckts.get(name, []):
            tokens = stmt.split()
            if stmt.startswith("XM"):
                model = tokens[5]
                mult = 1
                if count_fingers:
                    m_w = re.search(r"\bW=([0-9.]+)u\b", stmt)
                    if m_w:
                        w_val = float(m_w.group(1))
                        if w_val >= 100.0:
                            mult = int(round(w_val / 50.0))
                counts[model] += mult
            elif stmt.startswith("D"):
                model = tokens[3]
                counts[model] += 1
            elif stmt.startswith("X"):
                child = tokens[-1]
                child_counts = count_in_subckt(child, count_fingers=count_fingers)
                for k, v in child_counts.items():
                    counts[k] += v
        return counts

    chip_comb = count_in_subckt("OSS_FRAME", count_fingers=False)
    chip_fing = count_in_subckt("OSS_FRAME", count_fingers=True)
    core_comb = count_in_subckt("c4004_core", count_fingers=False)
    sram_comb = count_in_subckt("SRAM128", count_fingers=False)
    print("=== Extracted Device Counts (Combined Parallel Devices) ===")
    print("Full Chip (OSS_FRAME):", dict(chip_comb), "Total MOSFETs:", chip_comb["PMOS"] + chip_comb["NMOS"] + chip_comb["NMOSE"])
    print("Core (c4004_core):    ", dict(core_comb), "Total MOSFETs:", core_comb["PMOS"] + core_comb["NMOS"] + core_comb["NMOSE"])
    print("SRAM128 macro:        ", dict(sram_comb), "Total MOSFETs:", sram_comb["PMOS"] + sram_comb["NMOS"])
    print("=== Extracted Device Counts (With Multi-Finger Pad Split M=) ===")
    print("Full Chip (OSS_FRAME):", dict(chip_fing), "Total MOSFETs:", chip_fing["PMOS"] + chip_fing["NMOS"] + chip_fing["NMOSE"])


if __name__ == "__main__":
    convert_extracted_for_ngspice(EXT_PATH, SIM_OUT_PATH)
    compute_hierarchical_stats(EXT_PATH)
