#!/usr/bin/env python3
"""
Generate and run in parallel post-layout full-chip ngspice simulations on
apr/OSS_FRAME_sim.spice (with 1.0 pF load on all pads):
  - Test 1: ALU/ACC instructions (LDM, IAC, RAL, CMA, WRR) & DCL (cm_ram[3:0])
  - Test 2: SRAM128 Index Register File (FIM, LD, ADD, INC, SRC, WRR)
  - Test 3: SRAM128 Stack (JMS, BBL) & JCN (test pin branch)
  - Test 4: Clock Frequency Sweep (2 MHz .. 12 MHz) for FMAX, t_pd, and power
"""

import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APR_DIR = os.path.join(BASE_DIR, "apr")
MODELS_DIR = os.path.join(BASE_DIR, "TR-1um", "libs.tech", "spice", "models")
SIM_NETLIST = os.path.join(APR_DIR, "OSS_FRAME_sim.spice")
NGSPICE_BIN = "/opt/homebrew/bin/ngspice"


def build_pwl_clk(num_steps, T_ns, tr_ns):
    """
    Build PWL points for clk (P1):
      - step 0: [0, 1*T): 0V
      - step k >= 1: [k*T, (k+0.5)*T) = 5V, [(k+0.5)*T, (k+1)*T) = 0V
    """
    pts = [(0.0, 0.0), (T_ns - tr_ns, 0.0)]
    for k in range(1, num_steps + 1):
        t_rise = k * T_ns
        t_fall = (k + 0.5) * T_ns
        pts.append((t_rise, 5.0))
        pts.append((t_fall - tr_ns, 5.0))
        pts.append((t_fall, 0.0))
        pts.append(((k + 1.0) * T_ns - tr_ns, 0.0))
    return " ".join(f"{t:.3f}n {v:.1f}" for t, v in pts)


def build_bus_pwl(inst_bytes, T_ns, tr_ns):
    """
    Given list of instruction bytes [(opr, opa), ...], build PWL waveforms for:
      - drv_en: 1.0 during M1..M2 [(8*i + 3.15)*T .. (8*i + 5.05)*T], else 0.0
      - rom_d0..rom_d3: 5.0V/0.0V during M1 (opr) and M2 (opa)
    """
    en_pts = [(0.0, 0.0)]
    d_pts = {b: [(0.0, 0.0)] for b in range(4)}

    for i, (m1_nib, m2_nib) in enumerate(inst_bytes):
        t_m1_start = (8 * i + 3.15) * T_ns
        t_m2_start = (8 * i + 4.10) * T_ns
        t_m2_end = (8 * i + 5.05) * T_ns

        en_pts.append((t_m1_start - tr_ns, 0.0))
        en_pts.append((t_m1_start, 1.0))
        en_pts.append((t_m2_end - tr_ns, 1.0))
        en_pts.append((t_m2_end, 0.0))

        for b in range(4):
            v1 = 5.0 if ((m1_nib >> b) & 1) else 0.0
            v2 = 5.0 if ((m2_nib >> b) & 1) else 0.0
            d_pts[b].append((t_m1_start - tr_ns, 0.0))
            d_pts[b].append((t_m1_start, v1))
            d_pts[b].append((t_m2_start - tr_ns, v1))
            d_pts[b].append((t_m2_start, v2))
            d_pts[b].append((t_m2_end - tr_ns, v2))
            d_pts[b].append((t_m2_end, 0.0))

    en_str = " ".join(f"{t:.3f}n {v:.1f}" for t, v in en_pts)
    d_strs = {b: " ".join(f"{t:.3f}n {v:.1f}" for t, v in d_pts[b]) for b in range(4)}
    return en_str, d_strs


def make_common_deck(title, inst_bytes, T_ns, test_pin_v=5.0, meas_lines=None):
    num_inst = len(inst_bytes)
    num_steps = 8 * num_inst
    t_stop = num_steps * T_ns
    tr_ns = max(0.2, min(2.0, T_ns * 0.02))
    t_step = max(0.5, T_ns / 80.0)

    clk_pwl = build_pwl_clk(num_steps, T_ns, tr_ns)
    en_pwl, d_pwls = build_bus_pwl(inst_bytes, T_ns, tr_ns)
    t_rst_fall = 0.25 * T_ns

    deck = [
        f"* {title}",
        ".param vthMP=0 vthMN=0 vthMPE=0 vthMNE=0 magRR=1 magRS=1 magCSIO=1",
        f".include \"{os.path.join(MODELS_DIR, 'models_IP62_cap_v5p1.lib')}\"",
        f".include \"{os.path.join(MODELS_DIR, 'models_IP62_diode_v2.lib')}\"",
        f".include \"{os.path.join(MODELS_DIR, 'models_IP62_mos_v2.lib')}\"",
        f".include \"{os.path.join(MODELS_DIR, 'models_IP62_res_v5.lib')}\"",
        f".include \"{SIM_NETLIST}\"",
        "",
        ".options reltol=1e-3 abstol=1e-9 vntol=1e-3 method=trap",
        "",
        "* Power supplies",
        "VVDD VDD 0 5.0",
        "VVSS VSS 0 0.0",
        "",
        "* DUT: Full-chip extracted netlist OSS_FRAME",
        "* Pin order: P1 P10 P11 P12 P13 P14 P15 P2 P3 P4 P5 P6 P7 P9 VDD VSS",
        "Xchip P1 P10 P11 P12 P13 P14 P15 P2 P3 P4 P5 P6 P7 P9 VDD VSS OSS_FRAME",
        "",
        "* 1.0 pF load capacitance on all 14 signal pads",
        "CP1  P1  0 1.0p",
        "CP2  P2  0 1.0p",
        "CP3  P3  0 1.0p",
        "CP4  P4  0 1.0p",
        "CP5  P5  0 1.0p",
        "CP6  P6  0 1.0p",
        "CP7  P7  0 1.0p",
        "CP9  P9  0 1.0p",
        "CP10 P10 0 1.0p",
        "CP11 P11 0 1.0p",
        "CP12 P12 0 1.0p",
        "CP13 P13 0 1.0p",
        "CP14 P14 0 1.0p",
        "CP15 P15 0 1.0p",
        "",
        "* Input stimulus on P1 (clk), P7 (rst), P10 (test)",
        f"VP1  P1  0 PWL({clk_pwl})",
        f"VP7  P7  0 PWL(0 5.0 {t_rst_fall:.3f}n 5.0 {t_rst_fall + tr_ns:.3f}n 0.0)",
        f"VP10 P10 0 {test_pin_v:.1f}",
        "",
        "* Bidirectional Data Bus D[3:0] (P3=D3, P4=D2, P5=D1, P6=D0) tri-state ROM/RAM driver",
        f"Vdrv_en drv_en 0 PWL({en_pwl})",
        f"Vrom_d0 rom_d0 0 PWL({d_pwls[0]})",
        f"Vrom_d1 rom_d1 0 PWL({d_pwls[1]})",
        f"Vrom_d2 rom_d2 0 PWL({d_pwls[2]})",
        f"Vrom_d3 rom_d3 0 PWL({d_pwls[3]})",
        "Bd0 P6 0 I = V(drv_en) * (V(P6) - V(rom_d0)) / 50.0",
        "Bd1 P5 0 I = V(drv_en) * (V(P5) - V(rom_d1)) / 50.0",
        "Bd2 P4 0 I = V(drv_en) * (V(P4) - V(rom_d2)) / 50.0",
        "Bd3 P3 0 I = V(drv_en) * (V(P3) - V(rom_d3)) / 50.0",
        "",
        f".tran {t_step:.3f}n {t_stop:.3f}n",
    ]
    if meas_lines:
        deck.extend(meas_lines)
    deck.extend([
        ".end",
        ""
    ])
    return "\n".join(deck)


def sample_nib_meas(prefix, step_idx, T_ns):
    """Generate .meas commands to sample P6(D0), P5(D1), P4(D2), P3(D3), P9(d_oe) at (step_idx + 0.9)*T."""
    t_samp = (step_idx + 0.9) * T_ns
    return [
        f".meas tran {prefix}_d0 FIND v(P6) AT={t_samp:.3f}n",
        f".meas tran {prefix}_d1 FIND v(P5) AT={t_samp:.3f}n",
        f".meas tran {prefix}_d2 FIND v(P4) AT={t_samp:.3f}n",
        f".meas tran {prefix}_d3 FIND v(P3) AT={t_samp:.3f}n",
        f".meas tran {prefix}_doe FIND v(P9) AT={t_samp:.3f}n",
    ]


def decode_nibble(meas_dict, prefix):
    val = 0
    for b in range(4):
        v = meas_dict.get(f"{prefix}_d{b}", 0.0)
        if v > 2.5:
            val |= (1 << b)
    doe = meas_dict.get(f"{prefix}_doe", 0.0)
    return val, doe


def generate_test1(T_ns=1000.0):
    # Test 1: ALU/ACC & DCL
    # Inst 0: LDM 5 (D5) -> ACC=5
    # Inst 1: IAC   (F2) -> ACC=6
    # Inst 2: RAL   (F5) -> ACC=12 (0xC), CY=0
    # Inst 3: CMA   (F4) -> ACC=3 (0x3)
    # Inst 4: WRR   (E2) -> X2 (step 38) outputs ACC=3 on D[3:0]
    # Inst 5: DCL   (FD) -> dcl_reg = 3 (CM_RAM2=0V, CM_RAM1=0V? Wait: dcl_reg=3'b011 -> bank_sel={0,1,1,0} -> cm_ram=1001)
    # Inst 6: NOP   (00) -> A3 (step 50) checks P14..P11
    insts = [
        (0xD, 0x5),
        (0xF, 0x2),
        (0xF, 0x5),
        (0xF, 0x4),
        (0xE, 0x2),
        (0xF, 0xD),
        (0x0, 0x0),
    ]
    meas = []
    meas.extend(sample_nib_meas("wrr_acc", 8 * 4 + 6, T_ns))
    t_a3 = (8 * 6 + 2 + 0.9) * T_ns
    t_x3 = (8 * 0 + 7 + 0.9) * T_ns
    meas.extend([
        f".meas tran cmram0 FIND v(P11) AT={t_a3:.3f}n",
        f".meas tran cmram1 FIND v(P12) AT={t_a3:.3f}n",
        f".meas tran cmram2 FIND v(P13) AT={t_a3:.3f}n",
        f".meas tran cmram3 FIND v(P14) AT={t_a3:.3f}n",
        f".meas tran cmrom_a3 FIND v(P15) AT={t_a3:.3f}n",
        f".meas tran sync_x3 FIND v(P2) AT={t_x3:.3f}n",
    ])
    sp_path = os.path.join(APR_DIR, "sim_test1_alu.sp")
    with open(sp_path, "w") as f:
        f.write(make_common_deck("Test 1: ALU/ACC & DCL", insts, T_ns, test_pin_v=5.0, meas_lines=meas))
    return sp_path


def generate_test2(T_ns=1000.0):
    # Test 2: SRAM128 Index Registers
    # Inst 0 & 1: FIM P0, 0xA5 (20, A5) -> R0=0xA, R1=0x5 written to SRAM128
    # Inst 2: LD R0  (A0) -> ACC = 0xA
    # Inst 3: ADD R1 (81) -> ACC = 0xA + 0x5 = 0xF
    # Inst 4: INC R1 (61) -> R1 = 0x6 written to SRAM128
    # Inst 5: SRC P0 (21) -> X2 (step 46) outputs R0=0xA, X3 (step 47) outputs R1=0x6
    # Inst 6: WRR    (E2) -> X2 (step 54) outputs ACC=0xF
    insts = [
        (0x2, 0x0),
        (0xA, 0x5),
        (0xA, 0x0),
        (0x8, 0x1),
        (0x6, 0x1),
        (0x2, 0x1),
        (0xE, 0x2),
    ]
    meas = []
    meas.extend(sample_nib_meas("src_r0", 8 * 5 + 6, T_ns))
    meas.extend(sample_nib_meas("src_r1", 8 * 5 + 7, T_ns))
    meas.extend(sample_nib_meas("wrr_acc", 8 * 6 + 6, T_ns))
    sp_path = os.path.join(APR_DIR, "sim_test2_sram.sp")
    with open(sp_path, "w") as f:
        f.write(make_common_deck("Test 2: SRAM128 Index Regs", insts, T_ns, test_pin_v=5.0, meas_lines=meas))
    return sp_path


def generate_test3(T_ns=1000.0):
    # Test 3: SRAM128 Stack (JMS/BBL) & JCN (test=0)
    # Inst 0 & 1: JMS 0x123 (51, 23) -> PC jumps to 0x123, return addr 0x002 saved in SRAM128 stack
    # Inst 2 (at PC=0x123): BBL 0x9 (C9) -> PC returns to 0x002 from SRAM128, ACC=0x9
    # Inst 3 & 4 (at PC=0x002): JCN C0=1(test==0), 0x45 (11, 45) -> taken since P10(test)=0V -> PC=0x045
    # Inst 5 (at PC=0x045): WRR (E2) -> X2 outputs ACC=0x9
    insts = [
        (0x5, 0x1),
        (0x2, 0x3),
        (0xC, 0x9),
        (0x1, 0x1),
        (0x4, 0x5),
        (0xE, 0x2),
    ]
    meas = []
    # Check PC=0x123 in Inst 2 A1, A2, A3 (steps 16, 17, 18)
    meas.extend(sample_nib_meas("jms_pcl", 8 * 2 + 0, T_ns))
    meas.extend(sample_nib_meas("jms_pcm", 8 * 2 + 1, T_ns))
    meas.extend(sample_nib_meas("jms_pch", 8 * 2 + 2, T_ns))
    # Check PC=0x002 in Inst 3 A1, A2, A3 (steps 24, 25, 26)
    meas.extend(sample_nib_meas("bbl_pcl", 8 * 3 + 0, T_ns))
    meas.extend(sample_nib_meas("bbl_pcm", 8 * 3 + 1, T_ns))
    meas.extend(sample_nib_meas("bbl_pch", 8 * 3 + 2, T_ns))
    # Check PC=0x045 in Inst 5 A1, A2, A3 (steps 40, 41, 42)
    meas.extend(sample_nib_meas("jcn_pcl", 8 * 5 + 0, T_ns))
    meas.extend(sample_nib_meas("jcn_pcm", 8 * 5 + 1, T_ns))
    meas.extend(sample_nib_meas("jcn_pch", 8 * 5 + 2, T_ns))
    # Check ACC=0x9 in Inst 5 X2 (step 46)
    meas.extend(sample_nib_meas("bbl_acc", 8 * 5 + 6, T_ns))

    sp_path = os.path.join(APR_DIR, "sim_test3_stack_jcn.sp")
    with open(sp_path, "w") as f:
        f.write(make_common_deck("Test 3: SRAM128 Stack & JCN", insts, T_ns, test_pin_v=0.0, meas_lines=meas))
    return sp_path


def generate_test4_freq(freq_mhz):
    T_ns = 1000.0 / freq_mhz
    # Critical-path workload:
    # Inst 0 & 1: FIM P0, 0x97 (20, 97) -> writes R0=9, R1=7 to SRAM128
    # Inst 2: LD R0  (A0) -> reads R0=9 from SRAM128 into ACC
    # Inst 3: ADD R1 (81) -> reads R1=7 from SRAM128, 4-bit carry propagation 9+7 = 0, CY=1
    # Inst 4: RAL    (F5) -> ACC = 1, CY = 0
    # Inst 5: ADD R0 (80) -> reads R0=9 from SRAM128, 1+9 = 0xA, CY=0
    # Inst 6: WRR    (E2) -> outputs ACC=0xA in X2 (step 54), PC=0x006 in A1..A3 (steps 48..50)
    insts = [
        (0x2, 0x0),
        (0x9, 0x7),
        (0xA, 0x0),
        (0x8, 0x1),
        (0xF, 0x5),
        (0x8, 0x0),
        (0xE, 0x2),
    ]
    meas = []
    meas.extend(sample_nib_meas("pc6_l", 8 * 6 + 0, T_ns))
    meas.extend(sample_nib_meas("pc6_m", 8 * 6 + 1, T_ns))
    meas.extend(sample_nib_meas("pc6_h", 8 * 6 + 2, T_ns))
    meas.extend(sample_nib_meas("final_acc", 8 * 6 + 6, T_ns))

    # Measure propagation delays (clk=2.5V rising to output pad=2.5V crossing) & average supply current
    # 1. sync rising at step 7 (Inst 0 X3 starts at t = 7*T)
    t_s7 = 7.0 * T_ns
    # 2. cm_rom falling at step 2 (Inst 0 A3 starts at t = 2*T)
    t_s2 = 2.0 * T_ns
    # 3. d_oe falling at step 3 (Inst 0 M1 starts at t = 3*T)
    t_s3 = 3.0 * T_ns
    # 4. D0 (P6) rising at step 8 (Inst 1 A1, PC_L=1 starts at t = 8*T)
    t_s8 = 8.0 * T_ns

    t_start_avg = 1.0 * T_ns
    t_end_avg = 56.0 * T_ns
    meas.extend([
        f".meas tran tpd_sync TRIG v(P1) VAL=2.5 RISE=1 TD={t_s7 - 0.2*T_ns:.3f}n TARG v(P2) VAL=2.5 RISE=1 TD={t_s7 - 0.2*T_ns:.3f}n",
        f".meas tran tpd_cmrom TRIG v(P1) VAL=2.5 RISE=1 TD={t_s2 - 0.2*T_ns:.3f}n TARG v(P15) VAL=2.5 FALL=1 TD={t_s2 - 0.2*T_ns:.3f}n",
        f".meas tran tpd_cmram0 TRIG v(P1) VAL=2.5 RISE=1 TD={t_s2 - 0.2*T_ns:.3f}n TARG v(P11) VAL=2.5 FALL=1 TD={t_s2 - 0.2*T_ns:.3f}n",
        f".meas tran tpd_doe TRIG v(P1) VAL=2.5 RISE=1 TD={t_s3 - 0.2*T_ns:.3f}n TARG v(P9) VAL=2.5 FALL=1 TD={t_s3 - 0.2*T_ns:.3f}n",
        f".meas tran tpd_dout0 TRIG v(P1) VAL=2.5 RISE=1 TD={t_s8 - 0.2*T_ns:.3f}n TARG v(P6) VAL=2.5 RISE=1 TD={t_s8 - 0.2*T_ns:.3f}n",
        f".meas tran i_vdd_avg AVG i(VVDD) FROM={t_start_avg:.3f}n TO={t_end_avg:.3f}n",
    ])
    tag = f"{freq_mhz:g}MHz".replace(".", "p")
    sp_path = os.path.join(APR_DIR, f"sim_test4_{tag}.sp")
    with open(sp_path, "w") as f:
        f.write(make_common_deck(f"Test 4: FMAX Sweep @ {freq_mhz} MHz", insts, T_ns, test_pin_v=5.0, meas_lines=meas))
    return sp_path


def parse_log_meas(log_path):
    meas = {}
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            for line in f:
                m = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*([-+0-9.eE]+)", line)
                if m:
                    meas[m.group(1).lower()] = float(m.group(2))
    return meas


def run_one_spice(sp_path, force=False):
    log_path = sp_path.replace(".sp", ".log")
    if not force and os.path.exists(log_path):
        meas = parse_log_meas(log_path)
        if len(meas) >= 10:
            return sp_path, 0, meas
    res = subprocess.run(
        [NGSPICE_BIN, "-b", "-o", log_path, sp_path],
        capture_output=True,
        text=True,
    )
    meas = parse_log_meas(log_path)
    return sp_path, res.returncode, meas


def main():
    sp1 = generate_test1(1000.0)
    sp2 = generate_test2(1000.0)
    sp3 = generate_test3(1000.0)
    freqs = [1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 15.0, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0]
    sp4_list = [(f, generate_test4_freq(f)) for f in freqs]

    all_jobs = [(sp1, True), (sp2, True), (sp3, True)] + [(p, True) for f, p in sp4_list]
    print(f"Processing {len(all_jobs)} post-layout ngspice simulations...")

    results = {}
    with ProcessPoolExecutor(max_workers=12) as ex:
        fut_map = {ex.submit(run_one_spice, p, force): p for p, force in all_jobs}
        for fut in as_completed(fut_map):
            p, rc, meas = fut.result()
            results[p] = (rc, meas)
            print(f"Ready {os.path.basename(p)} (rc={rc}, {len(meas)} measurements)")

    # Report Test 1
    _, m1 = results[sp1]
    acc1, doe1 = decode_nibble(m1, "wrr_acc")
    cmram = [m1.get(f"cmram{i}", -1) for i in range(4)]
    print("\n=== Test 1: ALU/ACC & DCL (@ 1 MHz) ===")
    print(f"  WRR ACC output = 0x{acc1:X} (expected 0x3), d_oe = {doe1:.2f}V")
    print(f"  DCL cm_ram[3:0] = [{cmram[3]:.2f}V, {cmram[2]:.2f}V, {cmram[1]:.2f}V, {cmram[0]:.2f}V] (expected [5V, 0V, 0V, 5V])")
    print(f"  A3 cm_rom = {m1.get('cmrom_a3', -1):.2f}V (expected 0V), X3 sync = {m1.get('sync_x3', -1):.2f}V (expected 5V)")

    # Report Test 2
    _, m2 = results[sp2]
    r0_val, _ = decode_nibble(m2, "src_r0")
    r1_val, _ = decode_nibble(m2, "src_r1")
    acc2, _ = decode_nibble(m2, "wrr_acc")
    print("\n=== Test 2: SRAM128 Index Register File (@ 1 MHz) ===")
    print(f"  SRC R0 = 0x{r0_val:X} (expected 0xA), SRC R1 (after INC) = 0x{r1_val:X} (expected 0x6)")
    print(f"  WRR ACC (LD R0 + ADD R1) = 0x{acc2:X} (expected 0xF)")

    # Report Test 3
    _, m3 = results[sp3]
    jms_pc = (decode_nibble(m3, "jms_pch")[0] << 8) | (decode_nibble(m3, "jms_pcm")[0] << 4) | decode_nibble(m3, "jms_pcl")[0]
    bbl_pc = (decode_nibble(m3, "bbl_pch")[0] << 8) | (decode_nibble(m3, "bbl_pcm")[0] << 4) | decode_nibble(m3, "bbl_pcl")[0]
    jcn_pc = (decode_nibble(m3, "jcn_pch")[0] << 8) | (decode_nibble(m3, "jcn_pcm")[0] << 4) | decode_nibble(m3, "jcn_pcl")[0]
    bbl_acc, _ = decode_nibble(m3, "bbl_acc")
    print("\n=== Test 3: SRAM128 Stack (JMS/BBL) & JCN (@ 1 MHz) ===")
    print(f"  JMS Target PC = 0x{jms_pc:03X} (expected 0x123)")
    print(f"  BBL Return PC = 0x{bbl_pc:03X} (expected 0x002), BBL ACC = 0x{bbl_acc:X} (expected 0x9)")
    print(f"  JCN (test=0) Target PC = 0x{jcn_pc:03X} (expected 0x045)")

    # Report Test 4 Frequency Sweep
    print("\n=== Test 4: Post-Layout Frequency Sweep (FMAX, Delays, Power) ===")
    print(f"{'Freq(MHz)':>10} | {'Status':>6} | {'PC6':>5} | {'ACC':>4} | {'tpd_sync(ns)':>12} | {'tpd_cmrom(ns)':>13} | {'tpd_doe(ns)':>11} | {'tpd_dout(ns)':>12} | {'I_VDD(mA)':>10} | {'Power(mW)':>10}")
    print("-" * 118)
    for f, p in sp4_list:
        T_ns = 1000.0 / f
        _, mf = results[p]
        pc6 = (decode_nibble(mf, "pc6_h")[0] << 8) | (decode_nibble(mf, "pc6_m")[0] << 4) | decode_nibble(mf, "pc6_l")[0]
        accf, doef = decode_nibble(mf, "final_acc")
        ok = (pc6 == 0x006) and (accf == 0xA) and (doef > 2.5)
        status = "PASS" if ok else "FAIL"
        tsync = mf.get("tpd_sync", 0.0) * 1e9
        if tsync > 3.0 * T_ns:
            tsync -= 6.0 * T_ns
        tcmrom = mf.get("tpd_cmrom", 0.0) * 1e9
        if tcmrom > 0.8 * T_ns:
            tcmrom -= 1.0 * T_ns
        tdoe = mf.get("tpd_doe", 0.0) * 1e9
        if tdoe > 1.5 * T_ns:
            tdoe -= 2.0 * T_ns
        tdout = mf.get("tpd_dout0", 0.0) * 1e9
        if tdout > 3.5 * T_ns:
            tdout -= 7.0 * T_ns
        ivdd_ma = abs(mf.get("i_vdd_avg", 0.0)) * 1e3
        pwr_mw = ivdd_ma * 5.0
        print(f"{f:10.1f} | {status:>6} | 0x{pc6:03X} |  0x{accf:X} | {tsync:12.2f} | {tcmrom:13.2f} | {tdoe:11.2f} | {tdout:12.2f} | {ivdd_ma:10.3f} | {pwr_mw:10.3f}")


if __name__ == "__main__":
    main()
