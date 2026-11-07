from pathlib import Path
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pya as db
import klayout_extract

FRAME_GDS = "TR-1um/libs.tech/klayout/libraries/TR-1um_frame_25x25.gds"
STDCELL_SPICE_DIR = str(Path(__file__).resolve().parent.parent / "module/STDCELL/simulation"
SRAM_SPICE = str(Path(__file__).resolve().parent.parent / "module/SRAM128/simulation/SRAM128.spice"
DEF_PATH = str(Path(__file__).resolve().parent.parent / "apr/c4004_core_4edge_routed.def"
CHIP_GDS = str(Path(__file__).resolve().parent.parent / "apr/c4004_chip.gds"
OUT_SPICE_SIM = str(Path(__file__).resolve().parent.parent / "apr/simulation/OSS_FRAME.spice"
OUT_SPICE_APR = str(Path(__file__).resolve().parent.parent / "apr/c4004_chip.spice"

# 1. Extract OSS_ESD_5V_DIO, OSS_ESD_5V_VSS, OSS_ESD_5V_VDD, and their child subcircuits from FRAME_GDS
def extract_frame_spice():
    tmp_sp = str(Path(__file__).resolve().parent.parent / "openroad/_tmp_frame.spice"
    l2n = klayout_extract.build(FRAME_GDS, "OSS_FRAME_GIO", flat=False)
    nl = l2n.netlist()
    nl.make_top_level_pins()
    nl.purge()
    nl.purge_nets()

    w = db.NetlistSpiceWriter()
    w.use_net_names = True
    nl.write(tmp_sp, w, "OSS_FRAME_GIO")
    txt = open(tmp_sp).read()
    # Keep all subcircuits EXCEPT OSS_FRAME_GIO itself, ordered from bottom (leaf) to top (OSS_ESD_5V_*)
    f_subckts = re.findall(r"(\.SUBCKT\s+(\S+)\s+.*?\.ENDS\s+\S+)", txt, flags=re.S | re.I)
    kept = [blk for blk, name in reversed(f_subckts) if name.upper() != "OSS_FRAME_GIO"]
    return "\n\n".join(kept)

def build_lvs_spice():
    frame_sp = extract_frame_spice()

    # Read stdcell spice files and record port order of each subcircuit
    stdcell_ports = {}
    stdcell_file_map = {}
    for fn in sorted(os.listdir(STDCELL_SPICE_DIR)):
        if not fn.endswith(".spice"):
            continue
        p = os.path.join(STDCELL_SPICE_DIR, fn)
        content = open(p).read()
        m = re.search(r"^\.subckt\s+(\S+)\s+(.*)$", content, flags=re.M | re.I)
        if m:
            cname = m.group(1)
            ports = m.group(2).split()
            stdcell_ports[cname] = ports
            stdcell_file_map[cname] = content.strip()

    # Read SRAM128.spice and reorder subcircuits so leaf subcircuits precede parent subcircuits
    sram_raw = open(SRAM_SPICE).read()
    sram_subckts = re.findall(r"(\.subckt\s+(\S+)\s+.*?\.ends[^\n]*)", sram_raw, flags=re.S | re.I)
    sram_top_blk = None
    sram_child_blks = []
    for blk, sname in sram_subckts:
        blk_fixed = re.sub(r"\.ends\s*$", f".ends {sname}", blk.strip(), flags=re.M)
        if sname == "SRAM128":
            m = re.search(r"^\.subckt\s+SRAM128\s+(.*)$", blk_fixed, flags=re.M | re.I)
            stdcell_ports["SRAM128"] = m.group(1).split()
            sram_top_blk = blk_fixed
        else:
            sram_child_blks.append(blk_fixed)
    sram_child_blks.reverse()

    # Parse DEF COMPONENTS and NETS
    def_txt = open(DEF_PATH).read()
    comp_sec = def_txt.split("COMPONENTS")[1].split("END COMPONENTS")[0]
    inst_cell = {}
    ROW_YS = [59400, 237600, 415800, 594000, 772200, 950400, 1128600, 1306800, 1485000]
    occ_sites = defaultdict(set)

    stdcell_ly = db.Layout()
    stdcell_ly.read(str(Path(__file__).resolve().parent.parent / "module/STDCELL/TR-1um_STDCELL.gds")

    for m in re.finditer(r"-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)\s+N", comp_sec):
        inst, cell_name, cx, cy = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        inst_cell[inst] = cell_name
        if cell_name != "SRAM128":
            cobj = stdcell_ly.cell(cell_name)
            m1_b = db.Region(cobj.begin_shapes_rec(stdcell_ly.layer(13, 0))).bbox()
            nsites = m1_b.width() // 5400
            s0 = cx // 5400
            for s in range(s0, s0 + nsites):
                occ_sites[cy].add(s)

    TAP_XS = [21600, 615600, 1215000, 1809000]
    for ry in ROW_YS:
        for tx in TAP_XS:
            s0 = tx // 5400
            occ_sites[ry].add(s0)
            occ_sites[ry].add(s0 + 1)

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
            while rem > 0:
                if rem == 4:
                    fill_counts[2] += 2
                    rem = 0
                elif rem >= 3:
                    fill_counts[3] += 1
                    rem -= 3
                elif rem == 2:
                    fill_counts[2] += 1
                    rem -= 2
                else:
                    fill_counts[1] += 1
                    rem -= 1
            s = s_end

    # Parse DEF NETS for instance pin connections
    nets_sec = def_txt.split("NETS")[1].split("END NETS")[0]
    inst_pins = defaultdict(dict)
    for nm in re.finditer(r"-\s+(\S+)\s+(.*?);", nets_sec, re.S):
        nname = nm.group(1)
        body = nm.group(2)
        for pm in re.finditer(r"\(\s*(\S+)\s+(\S+)\s*\)", body):
            iname, pname = pm.group(1), pm.group(2)
            if iname != "PIN":
                inst_pins[iname][pname] = nname

    # Build c4004_core subcircuit
    core_ports = [
        "clk", "sync", "d_out[3]", "d_in[3]", "d_in[2]", "d_out[2]",
        "rst", "d_oe", "test", "cm_ram[0]", "cm_ram[1]", "cm_ram[2]",
        "cm_ram[3]", "cm_rom", "d_hiz", "d_out[0]", "d_in[0]",
        "d_in[1]", "d_out[1]", "VDD", "VSS"
    ]
    core_lines = [f".subckt c4004_core {' '.join(core_ports)}"]
    nc_idx = 0
    for inst, cname in inst_cell.items():
        ports = stdcell_ports[cname]
        conns = []
        for p in ports:
            if p.upper() == "VDD":
                conns.append("VDD")
            elif p.upper() == "VSS":
                conns.append("VSS")
            elif p in inst_pins[inst]:
                conns.append(inst_pins[inst][p])
            else:
                nc_idx += 1
                conns.append(f"_nc_{inst}_{p}_{nc_idx}")
        core_lines.append(f"X{inst} {' '.join(conns)} {cname}")

    for i in range(fill_counts[3]):
        core_lines.append(f"XFILL3_{i} VDD VSS FILL3")
    for i in range(fill_counts[2]):
        core_lines.append(f"XFILL2_{i} VDD VSS FILL2")
    core_lines.append(".ends c4004_core")

    # Top cell OSS_FRAME directly instantiates the 14 OSS_ESD_5V_DIO cells, OSS_ESD_5V_VSS, OSS_ESD_5V_VDD, and c4004_core
    # Note: In OSS_ESD_5V_DIO (ports: PAD VDD HIZ OUT VSS), the input terminal IN is internally wired to PAD.
    # Therefore, input/bidir signals (clk=P1, d_in[3]=P3, d_in[2]=P4, d_in[1]=P5, d_in[0]=P6, rst=P7, test=P10) connect directly to P1, P3, P4, P5, P6, P7, P10!
    core_call_conns = [
        "P1",        # clk
        "sync",      # sync
        "d_out[3]",  # d_out[3]
        "P3",        # d_in[3]
        "P4",        # d_in[2]
        "d_out[2]",  # d_out[2]
        "P7",        # rst
        "d_oe",      # d_oe
        "P10",       # test
        "cm_ram[0]", # cm_ram[0]
        "cm_ram[1]", # cm_ram[1]
        "cm_ram[2]", # cm_ram[2]
        "cm_ram[3]", # cm_ram[3]
        "cm_rom",    # cm_rom
        "d_hiz",     # d_hiz
        "d_out[0]",  # d_out[0]
        "P6",        # d_in[0]
        "P5",        # d_in[1]
        "d_out[1]",  # d_out[1]
        "VDD",       # VDD
        "VSS",       # VSS
    ]
    top_lines = [
        ".subckt OSS_FRAME P1 P2 P3 P4 P5 P6 P7 VSS P9 P10 P11 P12 P13 P14 P15 VDD",
        "XDIO1  P1  VDD VDD   VSS       VSS OSS_ESD_5V_DIO",
        "XDIO2  P2  VDD VSS   sync      VSS OSS_ESD_5V_DIO",
        "XDIO3  P3  VDD d_hiz d_out[3]  VSS OSS_ESD_5V_DIO",
        "XDIO4  P4  VDD d_hiz d_out[2]  VSS OSS_ESD_5V_DIO",
        "XDIO5  P5  VDD d_hiz d_out[1]  VSS OSS_ESD_5V_DIO",
        "XDIO6  P6  VDD d_hiz d_out[0]  VSS OSS_ESD_5V_DIO",
        "XDIO7  P7  VDD VDD   VSS       VSS OSS_ESD_5V_DIO",
        "XVSS   VDD VSS                     OSS_ESD_5V_VSS",
        "XDIO9  P9  VDD VSS   d_oe      VSS OSS_ESD_5V_DIO",
        "XDIO10 P10 VDD VDD   VSS       VSS OSS_ESD_5V_DIO",
        "XDIO11 P11 VDD VSS   cm_ram[0] VSS OSS_ESD_5V_DIO",
        "XDIO12 P12 VDD VSS   cm_ram[1] VSS OSS_ESD_5V_DIO",
        "XDIO13 P13 VDD VSS   cm_ram[2] VSS OSS_ESD_5V_DIO",
        "XDIO14 P14 VDD VSS   cm_ram[3] VSS OSS_ESD_5V_DIO",
        "XDIO15 P15 VDD VSS   cm_rom    VSS OSS_ESD_5V_DIO",
        "XVDD   VDD VSS                     OSS_ESD_5V_VDD",
        f"XCORE {' '.join(core_call_conns)} c4004_core",
        ".ends OSS_FRAME",
    ]

    used_stdcells = sorted((set(inst_cell.values()) - {"SRAM128"}) | {"FILL2", "FILL3"})
    stdcell_blocks = [stdcell_file_map[c] for c in used_stdcells]

    full_spice = (
        "* C4004 Full-Chip LVS Source Netlist (including OSS_FRAME_GIO / OSS_ESD_5V_DIO, SRAM128, STDCELL, and FILL2/FILL3 decaps)\n\n"
        + frame_sp.strip() + "\n\n"
        + "\n\n".join(stdcell_blocks) + "\n\n"
        + "\n\n".join(sram_child_blks) + "\n\n"
        + sram_top_blk + "\n\n"
        + "\n".join(core_lines) + "\n\n"
        + "\n".join(top_lines) + "\n"
    )

    os.makedirs(os.path.dirname(OUT_SPICE_SIM), exist_ok=True)
    open(OUT_SPICE_SIM, "w").write(full_spice)
    open(OUT_SPICE_APR, "w").write(full_spice)
    print(f"Wrote {OUT_SPICE_SIM} and {OUT_SPICE_APR}")

    # Verify LVS using KLayout LayoutToNetlist + NetlistComparer
    print("Running full-chip KLayout LVS extraction and comparison on c4004_chip.gds (OSS_FRAME)...")
    l2n_chip = klayout_extract.build(CHIP_GDS, "OSS_FRAME", flat=False)
    nl_chip = l2n_chip.netlist()
    nl_chip.make_top_level_pins()
    nl_chip.combine_devices()
    nl_chip.purge()
    nl_chip.purge_nets()

    ref_chip = db.Netlist()
    ref_chip.read(OUT_SPICE_SIM, db.NetlistSpiceReader())
    ref_chip.combine_devices()
    ref_chip.purge()
    ref_chip.purge_nets()

    # Align unmatched intermediate subcircuits (just as KLayout LVS `align` does)
    c_nl = {c.name.upper(): c.name for c in nl_chip.each_circuit()}
    c_ref = {c.name.upper(): c.name for c in ref_chip.each_circuit()}
    for k in list(c_nl.keys()):
        if k not in c_ref:
            nl_chip.flatten_circuit(c_nl[k])
    for k in list(c_ref.keys()):
        if k not in c_nl:
            ref_chip.flatten_circuit(c_ref[k])
    nl_chip.combine_devices()
    ref_chip.combine_devices()

    cmp = db.NetlistComparer()
    # Pin equivalence on symmetric input gates (same as lvs_pnr.py)
    for cname in ("NAND2_X1", "NAND3_X1", "NOR2_X1", "NOR3_X1"):
        c = ref_chip.circuit_by_name(cname)
        if c is not None:
            pids = [p.id() for p in c.each_pin() if p.name().startswith("A") or p.name() in ("A", "B", "C")]
            if len(pids) >= 2:
                cmp.same_pins(c, pids)

    match = cmp.compare(nl_chip, ref_chip)
    print(f"=== FULL-CHIP LVS MATCH (hierarchical aligned): {match} ===")
    top_l = nl_chip.circuit_by_name("OSS_FRAME")
    top_s = ref_chip.circuit_by_name("OSS_FRAME")
    l_pins = sorted([p.name() for p in top_l.each_pin()])
    s_pins = sorted([p.name() for p in top_s.each_pin()])
    print(f"  Layout OSS_FRAME pins ({len(l_pins)}): {l_pins}")
    print(f"  Schem  OSS_FRAME pins ({len(s_pins)}): {s_pins}")
    assert l_pins == s_pins, f"Top-level pin name mismatch: {l_pins} vs {s_pins}"
    for c in nl_chip.each_circuit():
        nd = sum(1 for _ in c.each_device())
        ns = sum(1 for _ in c.each_subcircuit())
        nn = sum(1 for _ in c.each_net())
        print(f"  [Layout] {c.name:<18} devs={nd:>4} subckts={ns:>3} nets={nn:>4}")
    for c in ref_chip.each_circuit():
        nd = sum(1 for _ in c.each_device())
        ns = sum(1 for _ in c.each_subcircuit())
        nn = sum(1 for _ in c.each_net())
        print(f"  [Schem ] {c.name:<18} devs={nd:>4} subckts={ns:>3} nets={nn:>4}")

build_lvs_spice()
