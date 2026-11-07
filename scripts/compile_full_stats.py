from pathlib import Path
#!/usr/bin/env python3
"""
Compile comprehensive statistics from apr/OSS_FRAME.extracted and apr/c4004_chip.gds.
"""
import os
import re
import json
from collections import Counter, defaultdict

WORKSPACE = str(Path(__file__).resolve().parent.parent)
EXTRACTED_PATH = os.path.join(WORKSPACE, "apr/OSS_FRAME.extracted")
OUT_JSON = str(Path(__file__).resolve().parent.parent / "openroad/extracted_full_stats.json"


def analyze_extracted():
    with open(EXTRACTED_PATH, "r") as f:
        raw_lines = f.readlines()

    joined = []
    for line in raw_lines:
        s = line.rstrip("\r\n")
        if s.startswith("+") and joined:
            joined[-1] += " " + s[1:].strip()
        else:
            joined.append(s)

    subckts = {}
    cur = None
    for line in joined:
        s = line.strip()
        if not s or s.startswith("*"):
            continue
        parts = s.split()
        h = parts[0].upper()
        if h == ".SUBCKT":
            cur = parts[1]
            subckts[cur] = {
                "ports": parts[2:],
                "devs": Counter(),
                "fingers": Counter(),
                "gate_width_um": Counter(),
                "subs": Counter(),
                "nets": set(parts[2:]),
            }
        elif h == ".ENDS":
            cur = None
        elif cur is not None:
            if h.startswith("XM"):
                model = parts[5]
                nets = parts[1:5]
                subckts[cur]["devs"][model] += 1
                subckts[cur]["nets"].update(nets)
                w_um = 0.0
                for p in parts[6:]:
                    if p.upper().startswith("W=") and p.endswith("u"):
                        w_um = float(p.split("=", 1)[1][:-1])
                fingers = int(round(w_um / 50.0)) if w_um >= 100.0 else 1
                subckts[cur]["fingers"][model] += fingers
                subckts[cur]["gate_width_um"][model] += w_um
            elif h.startswith("D"):
                model = parts[3]
                nets = parts[1:3]
                subckts[cur]["devs"][model] += 1
                subckts[cur]["fingers"][model] += 1
                subckts[cur]["nets"].update(nets)
            elif h.startswith("X"):
                cname = parts[-1]
                nets = parts[1:-1]
                subckts[cur]["subs"][cname] += 1
                subckts[cur]["nets"].update(nets)

    def get_totals(name):
        info = subckts[name]
        devs = Counter(info["devs"])
        fingers = Counter(info["fingers"])
        gw = Counter(info["gate_width_um"])
        int_nets = len(info["nets"]) - len(info["ports"])
        for c, cnt in info["subs"].items():
            cd, cf, cgw, cn = get_totals(c)
            for k, v in cd.items():
                devs[k] += v * cnt
            for k, v in cf.items():
                fingers[k] += v * cnt
            for k, v in cgw.items():
                gw[k] += v * cnt
            int_nets += cn * cnt
        return devs, fingers, gw, int_nets

    top_devs, top_fingers, top_gw, top_int_nets = get_totals("OSS_FRAME")
    top_total_nets = top_int_nets + len(subckts["OSS_FRAME"]["nets"])

    # Breakdown inside c4004_core
    core_info = subckts["c4004_core"]
    stdcell_table = []
    logic_cells_total = 0
    logic_pmos = 0
    logic_nmos = 0
    decap_cells_total = 0
    decap_pmos = 0
    decap_nmos = 0

    for cname, cnt in sorted(core_info["subs"].items(), key=lambda x: (-x[1], x[0])):
        if cname == "SRAM128":
            continue
        cd, cf, cgw, cn = get_totals(cname)
        p_cnt = cd.get("PMOS", 0)
        n_cnt = cd.get("NMOS", 0)
        tot_mos = (p_cnt + n_cnt) * cnt
        stdcell_table.append({
            "cell": cname,
            "instances": cnt,
            "pmos_per_cell": p_cnt,
            "nmos_per_cell": n_cnt,
            "mos_per_cell": p_cnt + n_cnt,
            "total_pmos": p_cnt * cnt,
            "total_nmos": n_cnt * cnt,
            "total_mos": tot_mos,
        })
        if cname.startswith("FILL"):
            decap_cells_total += cnt
            decap_pmos += p_cnt * cnt
            decap_nmos += n_cnt * cnt
        else:
            logic_cells_total += cnt
            logic_pmos += p_cnt * cnt
            logic_nmos += n_cnt * cnt

    sram_d, sram_f, sram_gw, sram_in = get_totals("SRAM128")
    dio_d, dio_f, dio_gw, dio_in = get_totals("OSS_ESD_5V_DIO")
    vdd_d, vdd_f, vdd_gw, vdd_in = get_totals("OSS_ESD_5V_VDD")
    vss_d, vss_f, vss_gw, vss_in = get_totals("OSS_ESD_5V_VSS")

    summary = {
        "top_cell": "OSS_FRAME",
        "total_subckt_definitions": len(subckts),
        "chip_totals_extracted": {
            "PMOS": top_devs["PMOS"],
            "NMOS": top_devs["NMOS"],
            "NMOSE": top_devs["NMOSE"],
            "total_mosfets": top_devs["PMOS"] + top_devs["NMOS"] + top_devs["NMOSE"],
            "DN_diodes": top_devs["DN"],
            "total_devices": sum(top_devs.values()),
            "total_fingers_uncombined": sum(top_fingers.values()),
            "total_mosfet_fingers": top_fingers["PMOS"] + top_fingers["NMOS"] + top_fingers["NMOSE"],
            "total_flat_nets": top_total_nets,
            "top_level_nets": len(subckts["OSS_FRAME"]["nets"]),
            "top_level_ports": len(subckts["OSS_FRAME"]["ports"]),
            "c4004_core_nets": len(core_info["nets"]),
            "c4004_core_ports": len(core_info["ports"]),
            "sram128_top_nets": len(subckts["SRAM128"]["nets"]),
            "sram128_flat_internal_nets": sram_in,
        },
        "block_breakdown": {
            "stdcell_logic": {
                "cell_types": len([x for x in stdcell_table if not x["cell"].startswith("FILL")]),
                "instances": logic_cells_total,
                "PMOS": logic_pmos,
                "NMOS": logic_nmos,
                "total_devices": logic_pmos + logic_nmos,
            },
            "stdcell_decap_fillers": {
                "cell_types": 2,
                "FILL2_instances": core_info["subs"]["FILL2"],
                "FILL3_instances": core_info["subs"]["FILL3"],
                "instances": decap_cells_total,
                "PMOS": decap_pmos,
                "NMOS": decap_nmos,
                "total_devices": decap_pmos + decap_nmos,
            },
            "sram128_macro": {
                "instances": 1,
                "SRAM_32x4": dict(subckts["SRAM_32x4"]["devs"]),
                "SRAM_SA4": dict(subckts["SRAM_SA4"]["devs"]),
                "SRAM_WD4": dict(subckts["SRAM_WD4"]["devs"]),
                "SRAM128_top_PDEC_ADB": dict(subckts["SRAM128"]["devs"]),
                "PMOS": sram_d["PMOS"],
                "NMOS": sram_d["NMOS"],
                "total_devices": sum(sram_d.values()),
            },
            "io_pad_ring": {
                "OSS_ESD_5V_DIO_instances": 14,
                "OSS_ESD_5V_VDD_instances": 1,
                "OSS_ESD_5V_VSS_instances": 1,
                "total_pad_cells": 16,
                "PMOS_extracted": dio_d["PMOS"] * 14 + vdd_d["PMOS"] + vss_d["PMOS"],
                "NMOS_extracted": dio_d["NMOS"] * 14,
                "NMOSE_extracted": dio_d["NMOSE"] * 14 + vdd_d["NMOSE"] + vss_d["NMOSE"],
                "DN_diodes": dio_d["DN"] * 14,
                "total_extracted_devices": sum(dio_d.values()) * 14 + sum(vdd_d.values()) + sum(vss_d.values()),
                "total_physical_fingers": sum(dio_f.values()) * 14 + sum(vdd_f.values()) + sum(vss_f.values()),
            },
        },
        "stdcell_table": stdcell_table,
    }

    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary["chip_totals_extracted"], indent=2))
    print(json.dumps(summary["block_breakdown"], indent=2))


if __name__ == "__main__":
    analyze_extracted()
