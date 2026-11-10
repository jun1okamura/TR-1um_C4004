#!/usr/bin/env python3
"""
Generate full-chip LVS reference SPICE netlists:
  - apr/c4004_chip.spice        (top .SUBCKT OSS_FRAME)
  - src/tr_1um_jun1okamura.cir  (top .SUBCKT tr_1um_jun1okamura)
from:
  - openroad/c4004_core_syn.v   (gate-level Verilog netlist of c4004_core)
  - openroad/c4004_core_placed.def (FILL3 / FILL2 decap instances)
  - module/STDCELL/simulation/*.spice (golden standard cell SPICE models)
  - macro/pad subcircuits (SRAM128, OSS_ESD_5V_*)
"""

import os
import re
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERILOG_PATH = os.path.join(BASE_DIR, "openroad", "c4004_core_syn.v")
PLACED_DEF_PATH = os.path.join(BASE_DIR, "openroad", "c4004_core_placed.def")
STDCELL_SPICE_DIR = os.path.join(BASE_DIR, "module", "STDCELL", "simulation")
EXTRACTED_PATH = os.path.join(BASE_DIR, "apr", "OSS_FRAME.extracted")

OUT_CHIP_SPICE = os.path.join(BASE_DIR, "apr", "c4004_chip.spice")
OUT_SUB_CIR = os.path.join(BASE_DIR, "src", "tr_1um_jun1okamura.cir")


def parse_spice_subckts(spice_text):
    """Parse .subckt/.ends blocks and return dict[name -> (pins_list, full_block_text)]."""
    subckts = {}
    lines = spice_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^\.subckt\b", line, re.IGNORECASE):
            block_lines = [lines[i]]
            header = line
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("+"):
                header += " " + lines[i].lstrip()[1:].strip()
                block_lines.append(lines[i])
                i += 1
            tokens = header.split()
            name = tokens[1]
            pins = tokens[2:]
            while i < len(lines):
                block_lines.append(lines[i])
                if re.match(r"^\.ends\b", lines[i].strip(), re.IGNORECASE):
                    i += 1
                    break
                i += 1
            subckts[name] = (pins, "\n".join(block_lines))
        else:
            i += 1
    return subckts


def load_library_subckts():
    """Load golden standard cell SPICE models + macro/pad subckts."""
    subckts = {}
    # 1. Load all standard cell SPICE files from module/STDCELL/simulation/*.spice
    for sp_file in sorted(glob.glob(os.path.join(STDCELL_SPICE_DIR, "*.spice"))):
        with open(sp_file, "r") as f:
            parsed = parse_spice_subckts(f.read())
            subckts.update(parsed)

    # 2. Load macro (SRAM128 + SRAM_*) and pad (OSS_ESD_5V_* + OSS_*) subckts
    ref_ext = EXTRACTED_PATH if os.path.exists(EXTRACTED_PATH) else "/Users/okamura/Dropbox/98_LSI_Design/TR-1um_C4004/src/tr_1um_jun1okamura.cir"
    if os.path.exists(ref_ext):
        with open(ref_ext, "r") as f:
            ext_text = re.sub(r"(?m)^XM", "M", f.read())
            ext_subckts = parse_spice_subckts(ext_text)
        for name, val in ext_subckts.items():
            if name.startswith("SRAM") or name.startswith("BIT_") or name.startswith("OSS_ESD_") or name.startswith("OSS_NCH_") or name.startswith("OSS_PCH_") or name.startswith("OSS_DRV"):
                subckts[name] = val
    return subckts


def parse_def_fillers(def_path):
    """Return list of (inst_name, cell_type) for FILL* cells in placed DEF."""
    fillers = []
    with open(def_path, "r") as f:
        in_comp = False
        for line in f:
            s = line.strip()
            if s.startswith("COMPONENTS "):
                in_comp = True
                continue
            if in_comp and s.startswith("END COMPONENTS"):
                break
            if in_comp and s.startswith("- "):
                parts = s.split()
                if len(parts) >= 3:
                    inst_name = parts[1]
                    cell_type = parts[2]
                    if cell_type.startswith("FILL"):
                        fillers.append((inst_name, cell_type))
    return fillers


def parse_verilog_core(v_path):
    """Parse gate-level Verilog netlist of c4004_core."""
    instances = []
    with open(v_path, "r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("//") or s.startswith("module ") or s.startswith("endmodule"):
                continue
            if s.startswith(("input ", "output ", "wire ", ");")):
                continue
            m = re.match(r"^(\S+)\s+(\S+)\s*\((.*)\)\s*;$", s)
            if not m:
                continue
            cell_type, inst_name, ports_str = m.group(1), m.group(2), m.group(3)
            port_map = {}
            for pm in re.finditer(r"\.([A-Za-z0-9_\[\]]+)\s*\(\s*([^)]+?)\s*\)", ports_str):
                p_name = pm.group(1)
                net_name = pm.group(2)
                if cell_type == "SRAM128" and p_name in ("DIN", "DO"):
                    for bit in range(4):
                        port_map[f"{p_name}[{bit}]"] = f"{net_name}[{bit}]"
                else:
                    port_map[p_name] = net_name
            instances.append((cell_type, inst_name, port_map))
    return instances


def build_core_subckt(subckts, instances, fillers):
    """Build .SUBCKT c4004_core from Verilog instances + DEF fillers."""
    core_pins = [
        "clk", "rst", "test",
        "d_in[0]", "d_in[1]", "d_in[2]", "d_in[3]",
        "d_out[0]", "d_out[1]", "d_out[2]", "d_out[3]",
        "d_oe", "d_hiz", "sync", "cm_rom",
        "cm_ram[0]", "cm_ram[1]", "cm_ram[2]", "cm_ram[3]",
        "VDD", "VSS"
    ]
    lines = [
        "* Gate-level netlist of c4004_core generated from openroad/c4004_core_syn.v",
        ".SUBCKT c4004_core " + " ".join(core_pins)
    ]
    for cell_type, inst_name, port_map in instances:
        if cell_type not in subckts:
            raise KeyError(f"Cell {cell_type} not found in library subckts")
        pin_order, _ = subckts[cell_type]
        net_list = []
        for p in pin_order:
            pl = p.lower()
            if pl in ("vdd", "vdd|pad", "pad|vdd"):
                net_list.append("VDD")
            elif pl in ("vss", "gnd", "gnd|gnd", "pad|vss"):
                net_list.append("VSS")
            elif p in port_map:
                net_list.append(port_map[p])
            else:
                raise KeyError(f"Unmapped pin {p} on {cell_type} {inst_name}")
        clean_inst = re.sub(r"[^A-Za-z0-9_]", "_", inst_name)
        lines.append(f"X{clean_inst} {' '.join(net_list)} {cell_type}")

    for inst_name, cell_type in fillers:
        pin_order, _ = subckts[cell_type]
        net_list = ["VDD" if p.lower() == "vdd" else "VSS" for p in pin_order]
        clean_inst = re.sub(r"[^A-Za-z0-9_]", "_", inst_name)
        lines.append(f"X{clean_inst} {' '.join(net_list)} {cell_type}")

    lines.append(".ENDS c4004_core")
    return core_pins, "\n".join(lines)


def build_oss_frame_subckt(core_pins):
    """Build .SUBCKT OSS_FRAME matching rtl/c4004_top.v pad connections."""
    # OSS_ESD_5V_DIO pin order: PAD VDD HIZ OUT VSS
    # OSS_ESD_5V_VDD pin order: PAD|VDD VSS
    # OSS_ESD_5V_VSS pin order: VDD PAD|VSS
    top_pins = ["P1", "P10", "P11", "P12", "P13", "P14", "P15", "P2", "P3", "P4", "P5", "P6", "P7", "P9", "VDD", "VSS"]
    lines = [
        "* Full-chip padframe + core netlist matching rtl/c4004_top.v",
        ".SUBCKT OSS_FRAME " + " ".join(top_pins),
        "* Input pads (HIZ=VDD, OUT=VSS)",
        "XP1_CLK P1 VDD VDD VSS VSS OSS_ESD_5V_DIO",
        "XP7_RST P7 VDD VDD VSS VSS OSS_ESD_5V_DIO",
        "XP10_TEST P10 VDD VDD VSS VSS OSS_ESD_5V_DIO",
        "* Output pads (HIZ=VSS, OUT=core_sig)",
        "XP2_SYNC P2 VDD VSS net_sync VSS OSS_ESD_5V_DIO",
        "XP9_DOE P9 VDD VSS net_d_oe VSS OSS_ESD_5V_DIO",
        "XP11_CMRAM0 P11 VDD VSS net_cm_ram0 VSS OSS_ESD_5V_DIO",
        "XP12_CMRAM1 P12 VDD VSS net_cm_ram1 VSS OSS_ESD_5V_DIO",
        "XP13_CMRAM2 P13 VDD VSS net_cm_ram2 VSS OSS_ESD_5V_DIO",
        "XP14_CMRAM3 P14 VDD VSS net_cm_ram3 VSS OSS_ESD_5V_DIO",
        "XP15_CMROM P15 VDD VSS net_cm_rom VSS OSS_ESD_5V_DIO",
        "* Bidirectional Data Bus pads D[3:0] (PAD=core_d_in, HIZ=net_d_hiz, OUT=core_d_out)",
        "XP3_D3 P3 VDD net_d_hiz net_d_out3 VSS OSS_ESD_5V_DIO",
        "XP4_D2 P4 VDD net_d_hiz net_d_out2 VSS OSS_ESD_5V_DIO",
        "XP5_D1 P5 VDD net_d_hiz net_d_out1 VSS OSS_ESD_5V_DIO",
        "XP6_D0 P6 VDD net_d_hiz net_d_out0 VSS OSS_ESD_5V_DIO",
        "* Power pads",
        "XP16_VDD VDD VSS OSS_ESD_5V_VDD",
        "XP8_VSS VDD VSS OSS_ESD_5V_VSS",
    ]
    core_net_map = {
        "clk": "P1",
        "rst": "P7",
        "test": "P10",
        "d_in[0]": "P6",
        "d_in[1]": "P5",
        "d_in[2]": "P4",
        "d_in[3]": "P3",
        "d_out[0]": "net_d_out0",
        "d_out[1]": "net_d_out1",
        "d_out[2]": "net_d_out2",
        "d_out[3]": "net_d_out3",
        "d_oe": "net_d_oe",
        "d_hiz": "net_d_hiz",
        "sync": "net_sync",
        "cm_rom": "net_cm_rom",
        "cm_ram[0]": "net_cm_ram0",
        "cm_ram[1]": "net_cm_ram1",
        "cm_ram[2]": "net_cm_ram2",
        "cm_ram[3]": "net_cm_ram3",
        "VDD": "VDD",
        "VSS": "VSS",
    }
    core_conn = [core_net_map[p] for p in core_pins]
    lines.append("Xcore " + " ".join(core_conn) + " c4004_core")
    lines.append(".ENDS OSS_FRAME")
    return top_pins, "\n".join(lines)


def main():
    subckts = load_library_subckts()
    instances = parse_verilog_core(VERILOG_PATH)
    fillers = parse_def_fillers(PLACED_DEF_PATH)
    print(f"Loaded {len(subckts)} library/macro subcircuits, {len(instances)} Verilog instances, {len(fillers)} DEF fillers.")

    core_pins, core_subckt_txt = build_core_subckt(subckts, instances, fillers)
    top_pins, oss_frame_txt = build_oss_frame_subckt(core_pins)

    # Collect all referenced library subcircuits
    lib_blocks = []
    for name in sorted(subckts.keys()):
        lib_blocks.append(subckts[name][1])
    lib_txt = "\n\n".join(lib_blocks)

    # 1. Write apr/c4004_chip.spice (top = OSS_FRAME)
    chip_spice = "\n\n".join([
        "* LVS Reference Netlist for OSS_FRAME (c4004_chip.gds)",
        oss_frame_txt,
        core_subckt_txt,
        lib_txt,
        ""
    ])
    with open(OUT_CHIP_SPICE, "w") as f:
        f.write(chip_spice)
    print(f"Wrote {OUT_CHIP_SPICE}")

    sim_dir = os.path.join(BASE_DIR, "apr", "simulation")
    os.makedirs(sim_dir, exist_ok=True)
    oss_frame_sp = os.path.join(sim_dir, "OSS_FRAME.spice")
    with open(oss_frame_sp, "w") as f:
        f.write(chip_spice)
    print(f"Wrote {oss_frame_sp}")

    # 2. Write src/tr_1um_jun1okamura.cir (top = tr_1um_jun1okamura)
    wrapper_txt = "\n".join([
        "* Top-level submission wrapper netlist (tr_1um_jun1okamura.gds)",
        ".SUBCKT tr_1um_jun1okamura " + " ".join(top_pins),
        "Xframe " + " ".join(top_pins) + " OSS_FRAME",
        ".ENDS tr_1um_jun1okamura"
    ])
    sub_cir = "\n\n".join([
        "* LVS Reference Netlist for tr_1um_jun1okamura (src/tr_1um_jun1okamura.gds)",
        wrapper_txt,
        oss_frame_txt,
        core_subckt_txt,
        lib_txt,
        ""
    ])
    with open(OUT_SUB_CIR, "w") as f:
        f.write(sub_cir)
    print(f"Wrote {OUT_SUB_CIR}")

    src_sim_dir = os.path.join(BASE_DIR, "src", "simulation")
    os.makedirs(src_sim_dir, exist_ok=True)
    sub_sp = os.path.join(src_sim_dir, "tr_1um_jun1okamura.spice")
    with open(sub_sp, "w") as f:
        f.write(sub_cir)
    print(f"Wrote {sub_sp}")


if __name__ == "__main__":
    main()
