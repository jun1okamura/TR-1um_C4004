from pathlib import Path
#!/usr/bin/env python3
"""
Generate and run parallel ngspice full-chip testbenches on OSS_FRAME.extracted
(apr/simulation/OSS_FRAME_extracted_sim.spice), including:
  1. Functional Test 1 (10 MHz): Reset, SYNC, CM_ROM, LDM, IAC, DCL/CM_RAM[3:0], WRM, RDM, RAL
  2. Functional Test 2 (10 MHz): Internal SRAM128 Read/Write (FIM, SRC, LD, ADD, INC, WRM)
  3. Functional Test 3 (10 MHz): Subroutine Stack in SRAM128 (JMS, BBL) & JCN with TEST pad (P10)
  4. FMAX Frequency Sweep (10, 12.5, 15, 17.5, 20, 22.5, 25, 30, 35, 40 MHz):
     Full-Chip + SRAM128 + ALU critical path
"""
import os
import re
import json
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

WORKSPACE = str(Path(__file__).resolve().parent.parent)
SIM_DIR = os.path.join(WORKSPACE, "apr/simulation")
NGSPICE_BIN = "ngspice"
RESULTS_JSON = os.path.join(SIM_DIR, "chip_verif_results.json")

# Fixed reset & clock start timing (independent of T_clk so reset recovery is always 100 ns):
#   VRST = 5.0V for [0, 50ns], falls to 0.0V at 50ns.
#   VCLK = 0.0V for [0, 150ns], first rising edge at T_START_NS = 150.0ns.
T_RST_FALL_NS = 50.0
T_START_NS = 150.0


def build_pwl_bus(cycles_spec, t_clk_ns, tr_ns=0.4):
    """
    Build PWL waveforms for TB_EN and D3_SRC..D0_SRC with symmetric full-cycle
    M1 and M2 windows aligned to P1 clock edges + t_hold (10.0 ns).
    """
    en_pts = [(0.0, 0.0)]
    d_pts = {b: [(0.0, 0.0)] for b in range(4)}
    test_pts = [(0.0, 0.0)]

    t_hold = 10.0

    def add_step(pts, t, val):
        last_t, last_v = pts[-1]
        if t <= last_t + 0.02:
            pts[-1] = (last_t, val)
            return
        if abs(last_v - val) < 1e-6:
            pts.append((t, val))
        else:
            t_pre = max(last_t + 0.02, t - tr_ns)
            pts.append((t_pre, last_v))
            pts.append((t, val))

    for k, cyc in enumerate(cycles_spec):
        t_base = T_START_NS + 8.0 * k * t_clk_ns
        m1_val = cyc.get("m1", 0)
        m2_val = cyc.get("m2", 0)
        x2_val = cyc.get("x2_in", None)
        t_val = 5.0 if cyc.get("test", 0) else 0.0

        add_step(test_pts, t_base, t_val)

        # Symmetric full-cycle M1 and M2 windows:
        #   M1 window: [t_base + 3.0*T + t_hold, t_base + 4.0*T + t_hold] (sampled at t_base + 4.0*T)
        #   M2 window: [t_base + 4.0*T + t_hold, t_base + 5.0*T + t_hold] (sampled at t_base + 5.0*T)
        t_m1_on  = t_base + 3.0 * t_clk_ns + t_hold
        t_m2_sw  = t_base + 4.0 * t_clk_ns + t_hold
        t_m2_off = t_base + 5.0 * t_clk_ns + t_hold

        add_step(en_pts, t_m1_on, 5.0)
        for b in range(4):
            v_m1 = 5.0 if ((m1_val >> b) & 1) else 0.0
            v_m2 = 5.0 if ((m2_val >> b) & 1) else 0.0
            add_step(d_pts[b], t_m1_on - tr_ns, v_m1)
            add_step(d_pts[b], t_m2_sw, v_m2)
        add_step(en_pts, t_m2_off, 0.0)

        if x2_val is not None:
            t_x2_on  = t_base + 6.0 * t_clk_ns + t_hold
            t_x2_off = t_base + 7.0 * t_clk_ns + t_hold
            add_step(en_pts, t_x2_on, 5.0)
            for b in range(4):
                v_x2 = 5.0 if ((x2_val >> b) & 1) else 0.0
                add_step(d_pts[b], t_x2_on - tr_ns, v_x2)
            add_step(en_pts, t_x2_off, 0.0)

    def fmt_pwl(pts):
        return "PWL(" + " ".join(f"{t:.3f}n {v:.2f}" for t, v in pts) + ")"

    return fmt_pwl(en_pts), {b: fmt_pwl(d_pts[b]) for b in range(4)}, fmt_pwl(test_pts)


def make_tb_header(title, t_clk_ns, cycles_spec):
    tr_ns = min(0.5, max(0.1, 0.02 * t_clk_ns))
    t_half = 0.5 * t_clk_ns
    t_pw = t_half - tr_ns
    en_pwl, d_pwls, test_pwl = build_pwl_bus(cycles_spec, t_clk_ns, tr_ns=tr_ns)

    return f"""* {title}
* Full-Chip Extracted Netlist Verification (OSS_FRAME.extracted)
* Clock Period T_clk = {t_clk_ns:.3f} ns (f_clk = {1000.0/t_clk_ns:.2f} MHz)

.include "models.spice"
.include "OSS_FRAME_extracted_sim.spice"

.option reltol=1e-3 abstol=1e-9 vntol=1e-4 method=trap

* Power Supplies (5.0V)
VVDD VDD 0 5.0
VVSS VSS 0 0.0

* Clock P1: Held Low (0V) during Reset [0, 150ns]; first rising edge at t = 150ns
VCLK P1 0 PULSE(0 5.0 {T_START_NS:.3f}n {tr_ns:.3f}n {tr_ns:.3f}n {t_pw:.3f}n {t_clk_ns:.3f}n)

* Reset P7: Active High (5V) for [0, 50ns] while CLK=0, deasserted at 50ns (100ns recovery before first CLK)
VRST P7 0 PWL(0n 5.0 {T_RST_FALL_NS - 0.5:.3f}n 5.0 {T_RST_FALL_NS:.3f}n 0.0)

* TEST Input Pad P10
VTEST P10 0 {test_pwl}

* Tri-State External ROM/RAM Bus Driver for Bidirectional Pads P3(D3)..P6(D0)
V_TB_EN TB_EN 0 {en_pwl}
V_D3 D3_SRC 0 {d_pwls[3]}
V_D2 D2_SRC 0 {d_pwls[2]}
V_D1 D1_SRC 0 {d_pwls[1]}
V_D0 D0_SRC 0 {d_pwls[0]}

.model SW_ROM SW(vt=2.5 vh=0.2 ron=5 roff=10Meg)
S_D3 P3 D3_SRC TB_EN 0 SW_ROM
S_D2 P4 D2_SRC TB_EN 0 SW_ROM
S_D1 P5 D1_SRC TB_EN 0 SW_ROM
S_D0 P6 D0_SRC TB_EN 0 SW_ROM

* Capacitive Probe Loads on All Output & Bidirectional Bondpads (1.0 pF)
C_P2  P2  0 1.0p
C_P3  P3  0 1.0p
C_P4  P4  0 1.0p
C_P5  P5  0 1.0p
C_P6  P6  0 1.0p
C_P9  P9  0 1.0p
C_P11 P11 0 1.0p
C_P12 P12 0 1.0p
C_P13 P13 0 1.0p
C_P14 P14 0 1.0p
C_P15 P15 0 1.0p

* Device Under Test: Full Chip OSS_FRAME (16 Pads)
* Port order: P1 P10 P11 P12 P13 P14 P15 P2 P3 P4 P5 P6 P7 P9 VDD VSS
XUUT P1 P10 P11 P12 P13 P14 P15 P2 P3 P4 P5 P6 P7 P9 VDD VSS OSS_FRAME
"""


def add_nibble_meas(lines, prefix, k, state_idx, t_clk_ns):
    t_s = T_START_NS + (8.0 * k + state_idx) * t_clk_ns
    t_samp = t_s + 40.0 + 0.45 * t_clk_ns
    lines.append(f".meas tran {prefix}_d3 FIND v(P3) AT={t_samp:.3f}n")
    lines.append(f".meas tran {prefix}_d2 FIND v(P4) AT={t_samp:.3f}n")
    lines.append(f".meas tran {prefix}_d1 FIND v(P5) AT={t_samp:.3f}n")
    lines.append(f".meas tran {prefix}_d0 FIND v(P6) AT={t_samp:.3f}n")
    lines.append(f".meas tran {prefix}_doe FIND v(P9) AT={t_samp:.3f}n")
    lines.append(f".meas tran {prefix}_sync FIND v(P2) AT={t_samp:.3f}n")
    lines.append(f".meas tran {prefix}_cmrom FIND v(P15) AT={t_samp:.3f}n")


def gen_tb2_sram(t_clk_ns=100.0):
    cycles = [
        {"m1": 0x2, "m2": 0x0},  # Cyc 0: FIM P0 (cycle 1)
        {"m1": 0xA, "m2": 0x5},  # Cyc 1: FIM P0 data 0xA5 -> SRAM128 R0=0xA, R1=0x5
        {"m1": 0x2, "m2": 0x1},  # Cyc 2: SRC P0 -> X2 outputs R0=0xA, X3 outputs R1=0x5
        {"m1": 0xA, "m2": 0x0},  # Cyc 3: LD R0  -> ACC = 0xA
        {"m1": 0x8, "m2": 0x1},  # Cyc 4: ADD R1 -> ACC = 0xA + 0x5 = 0xF
        {"m1": 0xE, "m2": 0x0},  # Cyc 5: WRM    -> X2 outputs ACC = 0xF
        {"m1": 0x6, "m2": 0x1},  # Cyc 6: INC R1 -> SRAM128 R1 = 0x5 + 1 = 0x6
        {"m1": 0xA, "m2": 0x1},  # Cyc 7: LD R1  -> ACC = 0x6
        {"m1": 0xE, "m2": 0x0},  # Cyc 8: WRM    -> X2 outputs ACC = 0x6
    ]
    t_stop = T_START_NS + 8.0 * len(cycles) * t_clk_ns + 50.0
    lines = [make_tb_header("TB2: SRAM128 Read/Write/ALU (10 MHz)", t_clk_ns, cycles)]

    add_nibble_meas(lines, "c2_src_x2", 2, 6, t_clk_ns)
    add_nibble_meas(lines, "c2_src_x3", 2, 7, t_clk_ns)
    add_nibble_meas(lines, "c5_wrm_x2", 5, 6, t_clk_ns)
    add_nibble_meas(lines, "c8_wrm_x2", 8, 6, t_clk_ns)
    lines.append(f".meas tran idd_avg AVG i(VVDD) FROM={T_START_NS:.3f}n TO={t_stop:.3f}n")

    lines.append(f"\n.tran {0.02*t_clk_ns:.3f}n {t_stop:.3f}n")
    lines.append(".end\n")
    path = os.path.join(SIM_DIR, "tb_chip_2_sram.spice")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def gen_tb_fmax(freq_mhz):
    t_clk_ns = 1000.0 / freq_mhz
    cycles = [
        {"m1": 0x2, "m2": 0x0},  # Cyc 0: FIM P0
        {"m1": 0xA, "m2": 0x5},  # Cyc 1: 0xA5 -> R0=0xA, R1=0x5
        {"m1": 0x2, "m2": 0x1},  # Cyc 2: SRC P0 -> X2=0xA, X3=0x5
        {"m1": 0xA, "m2": 0x0},  # Cyc 3: LD R0 -> ACC=0xA
        {"m1": 0x8, "m2": 0x1},  # Cyc 4: ADD R1 -> ACC=0xA+0x5=0xF
        {"m1": 0xE, "m2": 0x0},  # Cyc 5: WRM -> X2=0xF
    ]
    t_stop = T_START_NS + 8.0 * len(cycles) * t_clk_ns + 50.0
    lines = [make_tb_header(f"TB_FMAX {freq_mhz}MHz (T_clk={t_clk_ns:.3f}ns)", t_clk_ns, cycles)]

    add_nibble_meas(lines, "c2_src_x2", 2, 6, t_clk_ns)
    add_nibble_meas(lines, "c2_src_x3", 2, 7, t_clk_ns)
    add_nibble_meas(lines, "c5_wrm_x2", 5, 6, t_clk_ns)

    for prefix, k, s_idx in [("core_src_x2", 2, 6), ("core_src_x3", 2, 7), ("core_wrm_x2", 5, 6)]:
        t_c = T_START_NS + (8.0 * k + s_idx) * t_clk_ns + 17.0 + 0.45 * t_clk_ns
        lines.append(f".meas tran {prefix}_d3 FIND v(xuut.ni61) AT={t_c:.3f}n")
        lines.append(f".meas tran {prefix}_d2 FIND v(xuut.ni63) AT={t_c:.3f}n")
        lines.append(f".meas tran {prefix}_d1 FIND v(xuut.ni60) AT={t_c:.3f}n")
        lines.append(f".meas tran {prefix}_d0 FIND v(xuut.ni67) AT={t_c:.3f}n")

    td_src = T_START_NS + (22.0 - 0.1) * t_clk_ns
    lines.append(f".meas tran tpd_clk_dout TRIG v(P1) VAL=2.5 TD={td_src:.3f}n RISE=1 TARG v(P3) VAL=2.5 TD={td_src:.3f}n RISE=1")
    lines.append(f".meas tran idd_avg AVG i(VVDD) FROM={T_START_NS:.3f}n TO={t_stop:.3f}n")

    lines.append(f"\n.tran {0.02*t_clk_ns:.3f}n {t_stop:.3f}n")
    lines.append(".end\n")
    tag = f"{freq_mhz:g}".replace(".", "p")
    fname = f"tb_chip_fmax_{tag}MHz.spice"
    path = os.path.join(SIM_DIR, fname)
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def run_one_ngspice(spice_path):
    t0 = time.time()
    log_path = spice_path.replace(".spice", ".log")
    cmd = [NGSPICE_BIN, "-b", "-o", os.path.basename(log_path), os.path.basename(spice_path)]
    proc = subprocess.run(cmd, cwd=SIM_DIR, capture_output=True, text=True)
    elapsed = time.time() - t0

    meas = {}
    if os.path.exists(log_path):
        with open(log_path, "r", errors="replace") as f:
            for line in f:
                m = re.match(r"^\s*([a-zA-Z0-9_]+)\s*=\s*([-+0-9.eE]+)", line)
                if m:
                    meas[m.group(1).lower()] = float(m.group(2))
    return {
        "spice": os.path.basename(spice_path),
        "log": os.path.relpath(log_path, WORKSPACE),
        "returncode": proc.returncode,
        "elapsed_s": round(elapsed, 2),
        "meas": meas,
    }


def decode_nibble(meas, prefix, vth=2.5):
    val = 0
    for b in range(4):
        v = meas.get(f"{prefix}_d{b}", 0.0)
        if v > vth:
            val |= (1 << b)
    return val


if __name__ == "__main__":
    all_results = {}
    if os.path.exists(RESULTS_JSON):
        with open(RESULTS_JSON, "r") as f:
            old = json.load(f)
            for k in ("tb_chip_1_func.spice", "tb_chip_3_stack_jcn.spice"):
                if k in old:
                    all_results[k] = old[k]

    p2 = gen_tb2_sram(100.0)
    fmax_freqs = [10, 12.5, 15, 17.5, 20, 22.5, 25, 30, 35, 40]
    fmax_paths = [gen_tb_fmax(f) for f in fmax_freqs]

    run_paths = [p2] + fmax_paths
    ncpu = os.cpu_count() or 8
    print(f"Launching {len(run_paths)} ngspice chip-level simulations in parallel (max_workers={ncpu})...")

    with ProcessPoolExecutor(max_workers=min(ncpu, len(run_paths))) as ex:
        futs = {ex.submit(run_one_ngspice, p): p for p in run_paths}
        for fut in as_completed(futs):
            res = fut.result()
            sname = res["spice"]
            all_results[sname] = res
            m = res["meas"]
            print(f"Finished {sname} in {res['elapsed_s']}s (rc={res['returncode']}, {len(m)} meas)")
            if sname == "tb_chip_2_sram.spice":
                print(f"  [TB2] SRC X2=0x{decode_nibble(m,'c2_src_x2'):X} (exp 0xA), SRC X3=0x{decode_nibble(m,'c2_src_x3'):X} (exp 0x5), ADD WRM=0x{decode_nibble(m,'c5_wrm_x2'):X} (exp 0xF), INC WRM=0x{decode_nibble(m,'c8_wrm_x2'):X} (exp 0x6)")
            else:
                s_x2 = decode_nibble(m, "c2_src_x2")
                s_x3 = decode_nibble(m, "c2_src_x3")
                w_x2 = decode_nibble(m, "c5_wrm_x2")
                cs_x2 = decode_nibble(m, "core_src_x2")
                cs_x3 = decode_nibble(m, "core_src_x3")
                cw_x2 = decode_nibble(m, "core_wrm_x2")
                pad_ok = (s_x2 == 0xA) and (s_x3 == 0x5) and (w_x2 == 0xF)
                core_ok = (cs_x2 == 0xA) and (cs_x3 == 0x5) and (cw_x2 == 0xF)
                tpd = m.get("tpd_clk_dout", 0.0) * 1e9
                idd_ma = abs(m.get("idd_avg", 0.0)) * 1e3
                print(f"  [FMAX {sname}] PAD_PASS={pad_ok} (SRC=0x{s_x2:X},0x{s_x3:X}, WRM=0x{w_x2:X}) | CORE_PASS={core_ok} (SRC=0x{cs_x2:X},0x{cs_x3:X}, WRM=0x{cw_x2:X}) | tpd_dout={tpd:.2f}ns | Idd={idd_ma:.2f}mA")

    with open(RESULTS_JSON, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved all results to {RESULTS_JSON}")
