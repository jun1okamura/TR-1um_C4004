// Comprehensive Self-Checking Testbench for C4004 (Intel 4004 Compatible CPU)
// Tests all 46 Intel 4004 instructions, 3-level nested subroutines (JMS/BBL),
// indirect ROM table lookup (FIN), indirect jump (JIN), loop counter (ISZ),
// conditional jumps (JCN), 4001 ROM I/O (WRR/RDR), 4002 RAM (SRC/WRM/RDM/ADM/SBM/WMP/WR0..3/RD0..3),
// and Accumulator / BCD instructions (CLB/CLC/IAC/CMC/CMA/RAL/RAR/TCC/DAC/TCS/STC/DAA/KBP/DCL).

`timescale 1ns/1ps

module tb_c4004;
    // 750 kHz clock -> period = 1333.33 ns (half period = 667 ns)
    reg        clk;
    reg        rst;
    reg        test;
    wire [3:0] D;
    wire       d_oe;
    wire       sync;
    wire       cm_rom;
    wire [3:0] cm_ram;

    initial clk = 1'b0;
    always #667 clk = ~clk;

    c4004_top dut (
        .clk    (clk),
        .rst    (rst),
        .test   (test),
        .D      (D),
        .d_oe   (d_oe),
        .sync   (sync),
        .cm_rom (cm_rom),
        .cm_ram (cm_ram)
    );

    // =========================================================================
    // Simulated MCS-4 Bus Peripheral Model (4001 ROM + I/O & 4002 RAM)
    // =========================================================================
    reg [7:0]  rom [0:4095];
    reg [2:0]  bus_state;
    reg [11:0] rom_addr_lat;
    reg [3:0]  fetched_opr;
    reg [3:0]  fetched_opa;
    reg        in_2cyc;

    // 4002 RAM & 4001 I/O storage
    reg [7:0]  src_lat;
    reg [2:0]  ram_bank_lat;
    reg [3:0]  ram_main [0:3][0:63];     // 4 banks x 64 characters
    reg [3:0]  ram_stat [0:3][0:15];     // 4 banks x 4 regs x 4 status chars
    reg [3:0]  ram_out_port [0:3][0:3];  // WMP ports
    reg [3:0]  rom_out_port [0:15];      // WRR ports (indexed by SRC[7:4])
    reg [3:0]  rom_in_port  [0:15];      // RDR ports
    reg [3:0]  wpm_half_byte;

    // Bus state tracker synchronized to SYNC (active-High)
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            bus_state    <= 3'd7;
            rom_addr_lat <= 12'h000;
            fetched_opr  <= 4'h0;
            fetched_opa  <= 4'h0;
            in_2cyc      <= 1'b0;
            src_lat      <= 8'h00;
            ram_bank_lat <= 3'd0;
        end else begin
            if (sync) begin
                bus_state <= 3'd0; // Next state is A1
            end else begin
                bus_state <= bus_state + 3'd1;
            end

            case (bus_state)
                3'd0: rom_addr_lat[3:0]  <= D; // A1
                3'd1: rom_addr_lat[7:4]  <= D; // A2
                3'd2: rom_addr_lat[11:8] <= D; // A3
                3'd3: begin                    // M1
                    if (!in_2cyc) fetched_opr <= rom[rom_addr_lat][7:4];
                end
                3'd4: begin                    // M2
                    if (!in_2cyc) fetched_opa <= rom[rom_addr_lat][3:0];
                end
                3'd6: begin                    // X2
                    if (!in_2cyc && fetched_opr == 4'h2 && fetched_opa[0] == 1'b1) begin
                        // SRC: high nibble of address on D, plus active CM_RAM bank
                        src_lat[7:4] <= D;
                        if (cm_ram[0]) ram_bank_lat <= 3'd0;
                        else if (cm_ram[1]) ram_bank_lat <= 3'd1;
                        else if (cm_ram[2]) ram_bank_lat <= 3'd2;
                        else if (cm_ram[3]) ram_bank_lat <= 3'd3;
                    end else if (!in_2cyc && fetched_opr == 4'hE && !fetched_opa[3]) begin
                        // Write I/O & RAM instructions in X2
                        case (fetched_opa)
                            4'h0: ram_main[ram_bank_lat[1:0]][src_lat[5:0]] <= D;               // WRM
                            4'h1: ram_out_port[ram_bank_lat[1:0]][src_lat[7:6]] <= D;           // WMP
                            4'h2: rom_out_port[src_lat[7:4]] <= D;                              // WRR
                            4'h3: wpm_half_byte <= D;                                           // WPM
                            4'h4: ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd0}] <= D;       // WR0
                            4'h5: ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd1}] <= D;       // WR1
                            4'h6: ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd2}] <= D;       // WR2
                            4'h7: ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd3}] <= D;       // WR3
                            default: ;
                        endcase
                    end
                end
                3'd7: begin                    // X3
                    if (!in_2cyc && fetched_opr == 4'h2 && fetched_opa[0] == 1'b1) begin
                        src_lat[3:0] <= D;
                    end
                    if (!in_2cyc) begin
                        in_2cyc <= (fetched_opr == 4'h1) ||
                                   (fetched_opr == 4'h4) ||
                                   (fetched_opr == 4'h5) ||
                                   (fetched_opr == 4'h7) ||
                                   ((fetched_opr == 4'h2 || fetched_opr == 4'h3) && (fetched_opa[0] == 1'b0));
                    end else begin
                        in_2cyc <= 1'b0;
                    end
                end
            endcase
        end
    end

    // Drive D[3:0] from ROM (M1, M2) or RAM/IO (X2 during read I/O instructions)
    reg [3:0] ext_d_out;
    reg       ext_d_oe;

    always @(*) begin
        ext_d_oe  = 1'b0;
        ext_d_out = 4'h0;
        if (bus_state == 3'd3) begin
            ext_d_oe  = 1'b1;
            ext_d_out = rom[rom_addr_lat][7:4];
        end else if (bus_state == 3'd4) begin
            ext_d_oe  = 1'b1;
            ext_d_out = rom[rom_addr_lat][3:0];
        end else if (bus_state == 3'd6 && (!in_2cyc) && (fetched_opr == 4'hE) && fetched_opa[3]) begin
            ext_d_oe = 1'b1;
            case (fetched_opa)
                4'h8: ext_d_out = ram_main[ram_bank_lat[1:0]][src_lat[5:0]];             // SBM
                4'h9: ext_d_out = ram_main[ram_bank_lat[1:0]][src_lat[5:0]];             // RDM
                4'hA: ext_d_out = rom_in_port[src_lat[7:4]];                             // RDR
                4'hB: ext_d_out = ram_main[ram_bank_lat[1:0]][src_lat[5:0]];             // ADM
                4'hC: ext_d_out = ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd0}];     // RD0
                4'hD: ext_d_out = ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd1}];     // RD1
                4'hE: ext_d_out = ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd2}];     // RD2
                4'hF: ext_d_out = ram_stat[ram_bank_lat[1:0]][{src_lat[5:4], 2'd3}];     // RD3
                default: ext_d_out = 4'h0;
            endcase
        end
    end

    assign D = ext_d_oe ? ext_d_out : 4'bzzzz;

    // =========================================================================
    // Test Program in ROM (Exercises all 46 Intel 4004 instructions)
    // =========================================================================
    integer idx, b;
    integer err_cnt;

    task check_val(input [255:0] name, input [15:0] got, input [15:0] exp);
        begin
            if (got !== exp) begin
                $display("FAIL [%0s]: got=0x%0h expected=0x%0h at time %0t", name, got, exp, $time);
                err_cnt = err_cnt + 1;
            end else begin
                $display("PASS [%0s]: 0x%0h", name, got);
            end
        end
    endtask

    initial begin
        err_cnt = 0;
        for (idx = 0; idx < 4096; idx = idx + 1) rom[idx] = 8'h00; // NOP
        for (idx = 0; idx < 16; idx = idx + 1) begin
            rom_out_port[idx] = 4'h0;
            rom_in_port[idx]  = 4'h0;
            for (b = 0; b < 4; b = b + 1) ram_stat[b][idx] = 4'h0;
        end
        for (idx = 0; idx < 64; idx = idx + 1) begin
            for (b = 0; b < 4; b = b + 1) ram_main[b][idx] = 4'h0;
        end
        rom_in_port[4'h2] = 4'h9; // Test input value on ROM port 2

        // ---------------------------------------------------------------------
        // Program Assembly at 0x000:
        // ---------------------------------------------------------------------
        idx = 0;
        // 1. NOP, LDM, XCH, LD, ADD, SUB, INC
        rom[idx] = 8'h00; idx = idx + 1; // 000: NOP
        rom[idx] = 8'hD5; idx = idx + 1; // 001: LDM 5       (ACC = 5)
        rom[idx] = 8'hB2; idx = idx + 1; // 002: XCH R2      (R2 = 5, ACC = 0)
        rom[idx] = 8'hD3; idx = idx + 1; // 003: LDM 3       (ACC = 3)
        rom[idx] = 8'h82; idx = idx + 1; // 004: ADD R2      (ACC = 3 + 5 = 8, CY = 0)
        rom[idx] = 8'h62; idx = idx + 1; // 005: INC R2      (R2 = 6)
        rom[idx] = 8'hF1; idx = idx + 1; // 006: CLC         (CY = 0)
        rom[idx] = 8'h92; idx = idx + 1; // 007: SUB R2      (ACC = 8 - 6 = 2, CY = 1 no borrow)
        rom[idx] = 8'hB3; idx = idx + 1; // 008: XCH R3      (R3 = 2)
        rom[idx] = 8'hA2; idx = idx + 1; // 009: LD R2       (ACC = 6)

        // 2. Accumulator Group: CLB, IAC, DAC, CMA, CMC, STC, RAL, RAR, TCC, TCS, DAA, KBP, DCL
        rom[idx] = 8'hF2; idx = idx + 1; // 00A: IAC         (ACC = 7, CY = 0)
        rom[idx] = 8'hF8; idx = idx + 1; // 00B: DAC         (ACC = 6, CY = 1)
        rom[idx] = 8'hF4; idx = idx + 1; // 00C: CMA         (ACC = ~6 = 9)
        rom[idx] = 8'hF1; idx = idx + 1; // 00D: CLC         (CY = 0)
        rom[idx] = 8'hFA; idx = idx + 1; // 00E: STC         (CY = 1)
        rom[idx] = 8'hF3; idx = idx + 1; // 00F: CMC         (CY = 0)
        rom[idx] = 8'hFA; idx = idx + 1; // 010: STC         (CY = 1)
        rom[idx] = 8'hF5; idx = idx + 1; // 011: RAL         ({CY,ACC} = {9,1} -> CY=1, ACC=3)
        rom[idx] = 8'hF6; idx = idx + 1; // 012: RAR         ({ACC,CY} = {1,3} -> ACC=9, CY=1)
        rom[idx] = 8'hF7; idx = idx + 1; // 013: TCC         (ACC = 1, CY = 0)
        rom[idx] = 8'hB4; idx = idx + 1; // 014: XCH R4      (R4 = 1)
        rom[idx] = 8'hFA; idx = idx + 1; // 015: STC         (CY = 1)
        rom[idx] = 8'hF9; idx = idx + 1; // 016: TCS         (ACC = 10 = 0xA, CY = 0)
        rom[idx] = 8'hB5; idx = idx + 1; // 017: XCH R5      (R5 = 0xA)
        // Test BCD addition with DAA: 7 + 8 = 15 (0xF) -> DAA -> ACC = 5, CY = 1
        rom[idx] = 8'hF0; idx = idx + 1; // 018: CLB         (ACC = 0, CY = 0)
        rom[idx] = 8'hD7; idx = idx + 1; // 019: LDM 7
        rom[idx] = 8'hB6; idx = idx + 1; // 01A: XCH R6      (R6 = 7)
        rom[idx] = 8'hD8; idx = idx + 1; // 01B: LDM 8
        rom[idx] = 8'h86; idx = idx + 1; // 01C: ADD R6      (ACC = 15 = 0xF, CY = 0)
        rom[idx] = 8'hFB; idx = idx + 1; // 01D: DAA         (ACC = 5, CY = 1)
        rom[idx] = 8'hB6; idx = idx + 1; // 01E: XCH R6      (R6 = 5)
        // Test KBP: ACC = 4 (0100) -> KBP -> 3
        rom[idx] = 8'hD4; idx = idx + 1; // 01F: LDM 4
        rom[idx] = 8'hFC; idx = idx + 1; // 020: KBP         (ACC = 3)
        rom[idx] = 8'hB7; idx = idx + 1; // 021: XCH R7      (R7 = 3)

        // 3. FIM, FIN (Indirect ROM table lookup at 0x080)
        rom[idx] = 8'h20; idx = idx + 1; // 022: FIM P0, 0x80 (R0 = 8, R1 = 0)
        rom[idx] = 8'h80; idx = idx + 1; // 023:   data 0x80
        rom[idx] = 8'h38; idx = idx + 1; // 024: FIN P4       (fetches rom[0x080]=0xCA -> R8=0xC, R9=0xA)
        rom[8'h80] = 8'hCA;

        // 4. SRC, DCL, RAM & I/O instructions (WRM, RDM, ADM, SBM, WMP, WRR, RDR, WR0..3, RD0..3, WPM)
        rom[idx] = 8'hD2; idx = idx + 1; // 025: LDM 2
        rom[idx] = 8'hFD; idx = idx + 1; // 026: DCL          (select RAM bank 2: dcl = 010)
        rom[idx] = 8'h22; idx = idx + 1; // 027: FIM P1, 0x25 (R2 = 2, R3 = 5)
        rom[idx] = 8'h25; idx = idx + 1; // 028:   data 0x25
        rom[idx] = 8'h23; idx = idx + 1; // 029: SRC P1       (SRC = 0x25 on bank 2)
        rom[idx] = 8'hDA; idx = idx + 1; // 02A: LDM 0xA
        rom[idx] = 8'hE0; idx = idx + 1; // 02B: WRM          (ram_main[2][0x25] = 0xA)
        rom[idx] = 8'hE1; idx = idx + 1; // 02C: WMP          (ram_out_port[2][0] = 0xA)
        rom[idx] = 8'hE2; idx = idx + 1; // 02D: WRR          (rom_out_port[2] = 0xA)
        rom[idx] = 8'hE3; idx = idx + 1; // 02E: WPM          (wpm_half_byte = 0xA)
        rom[idx] = 8'hD4; idx = idx + 1; // 02F: LDM 4
        rom[idx] = 8'hE4; idx = idx + 1; // 030: WR0
        rom[idx] = 8'hD5; idx = idx + 1; // 031: LDM 5
        rom[idx] = 8'hE5; idx = idx + 1; // 032: WR1
        rom[idx] = 8'hD6; idx = idx + 1; // 033: LDM 6
        rom[idx] = 8'hE6; idx = idx + 1; // 034: WR2
        rom[idx] = 8'hD7; idx = idx + 1; // 035: LDM 7
        rom[idx] = 8'hE7; idx = idx + 1; // 036: WR3
        rom[idx] = 8'hF0; idx = idx + 1; // 037: CLB          (ACC = 0, CY = 0)
        rom[idx] = 8'hE9; idx = idx + 1; // 038: RDM          (ACC = 0xA)
        rom[idx] = 8'hF1; idx = idx + 1; // 039: CLC
        rom[idx] = 8'hD3; idx = idx + 1; // 03A: LDM 3
        rom[idx] = 8'hEB; idx = idx + 1; // 03B: ADM          (ACC = 3 + 0xA = 0xD, CY = 0)
        rom[idx] = 8'hF1; idx = idx + 1; // 03C: CLC
        rom[idx] = 8'hE8; idx = idx + 1; // 03D: SBM          (ACC = 0xD - 0xA = 3, CY = 1)
        rom[idx] = 8'hBA; idx = idx + 1; // 03E: XCH R10      (R10 = 3)
        rom[idx] = 8'hEA; idx = idx + 1; // 03F: RDR          (ACC = rom_in_port[2] = 9)
        rom[idx] = 8'hBB; idx = idx + 1; // 040: XCH R11      (R11 = 9)
        rom[idx] = 8'hEC; idx = idx + 1; // 041: RD0          (ACC = 4)
        rom[idx] = 8'hED; idx = idx + 1; // 042: RD1          (ACC = 5)
        rom[idx] = 8'hEE; idx = idx + 1; // 043: RD2          (ACC = 6)
        rom[idx] = 8'hEF; idx = idx + 1; // 044: RD3          (ACC = 7)
        rom[idx] = 8'hBC; idx = idx + 1; // 045: XCH R12      (R12 = 7)

        // 5. ISZ loop: R13 starts at 13 (0xD), loops 3 times incrementing R14 until R13 wraps to 0
        rom[idx] = 8'hDD; idx = idx + 1; // 046: LDM 0xD
        rom[idx] = 8'hBD; idx = idx + 1; // 047: XCH R13      (R13 = 13)
        rom[idx] = 8'hD0; idx = idx + 1; // 048: LDM 0
        rom[idx] = 8'hBE; idx = idx + 1; // 049: XCH R14      (R14 = 0)
        // Loop at 0x04A:
        rom[idx] = 8'h6E; idx = idx + 1; // 04A: INC R14      (R14++)
        rom[idx] = 8'h7D; idx = idx + 1; // 04B: ISZ R13, 0x4A
        rom[idx] = 8'h4A; idx = idx + 1; // 04C:   target 0x4A

        // 6. Nested Subroutines (JMS 3 levels deep + BBL) & JCN & JUN & JIN
        rom[idx] = 8'h51; idx = idx + 1; // 04D: JMS 0x100
        rom[idx] = 8'h00; idx = idx + 1; // 04E:   target 0x00
        rom[idx] = 8'hBF; idx = idx + 1; // 04F: XCH R15      (R15 = ACC returned from sub1 = 0xB)
        // Test JCN (jump if ACC == 0 -> taken after CLB)
        rom[idx] = 8'hF0; idx = idx + 1; // 050: CLB
        rom[idx] = 8'h14; idx = idx + 1; // 051: JCN Z (c=0100), 0x55
        rom[idx] = 8'h55; idx = idx + 1; // 052:   target 0x55
        rom[idx] = 8'hDF; idx = idx + 1; // 053: LDM 0xF (should be skipped!)
        rom[idx] = 8'hBF; idx = idx + 1; // 054: XCH R15 (should be skipped!)
        // 0x055: Test JIN P0 (jump indirect to R0:R1 = 0x60)
        rom[idx] = 8'h20; idx = idx + 1; // 055: FIM P0, 0x60
        rom[idx] = 8'h60; idx = idx + 1; // 056:   data 0x60
        rom[idx] = 8'h31; idx = idx + 1; // 057: JIN P0       (jumps to 0x060)

        // At 0x060: JUN to 0x200 (completion loop)
        rom[12'h060] = 8'h42;            // 060: JUN 0x200
        rom[12'h061] = 8'h00;

        // Subroutine 1 at 0x100: calls Sub 2 at 0x120
        rom[12'h100] = 8'h51;            // 100: JMS 0x120
        rom[12'h101] = 8'h20;
        rom[12'h102] = 8'hCB;            // 102: BBL 0xB

        // Subroutine 2 at 0x120: calls Sub 3 at 0x140
        rom[12'h120] = 8'h51;            // 120: JMS 0x140
        rom[12'h121] = 8'h40;
        rom[12'h122] = 8'hC7;            // 122: BBL 0x7

        // Subroutine 3 at 0x140: returns 0x3
        rom[12'h140] = 8'hC3;            // 140: BBL 0x3

        // Completion loop at 0x200:
        rom[12'h200] = 8'h42;            // 200: JUN 0x200
        rom[12'h201] = 8'h00;

        // ---------------------------------------------------------------------
        // Run Simulation
        // ---------------------------------------------------------------------
        rst  = 1'b1;
        test = 1'b0;
        repeat (4) @(posedge clk);
        rst  = 1'b0;

        // Wait for CPU to reach completion address 0x200 (~105 machine cycles = 840 states)
        repeat (1000) @(posedge clk);

        $display("=== C4004 Verification Results ===");
        check_val("PC reached 0x20x", (dut.u_core.pc & 12'hFF0), 12'h200);
        check_val("R0 (FIM/JIN hi)",  dut.u_core.u_sram.mem[0],  4'h6);
        check_val("R1 (FIM/JIN lo)",  dut.u_core.u_sram.mem[1],  4'h0);
        check_val("R2 (FIM P1 hi)",   dut.u_core.u_sram.mem[2],  4'h2);
        check_val("R3 (FIM P1 lo)",   dut.u_core.u_sram.mem[3],  4'h5);
        check_val("R4 (RAL/RAR/TCC)", dut.u_core.u_sram.mem[4],  4'h1);
        check_val("R5 (STC/TCS)",     dut.u_core.u_sram.mem[5],  4'hA);
        check_val("R6 (7+8 BCD DAA)", dut.u_core.u_sram.mem[6],  4'h5);
        check_val("R7 (KBP 4->3)",    dut.u_core.u_sram.mem[7],  4'h3);
        check_val("R8 (FIN hi)",      dut.u_core.u_sram.mem[8],  4'hC);
        check_val("R9 (FIN lo)",      dut.u_core.u_sram.mem[9],  4'hA);
        check_val("R10 (RDM/ADM/SBM)",dut.u_core.u_sram.mem[10], 4'h3);
        check_val("R11 (RDR)",        dut.u_core.u_sram.mem[11], 4'h9);
        check_val("R12 (WR3/RD3)",    dut.u_core.u_sram.mem[12], 4'h7);
        check_val("R13 (ISZ end)",    dut.u_core.u_sram.mem[13], 4'h0);
        check_val("R14 (ISZ count)",  dut.u_core.u_sram.mem[14], 4'h3);
        check_val("R15 (3-lvl JMS/BBL)", dut.u_core.u_sram.mem[15], 4'hB);
        check_val("RAM[2][0x25] WRM", ram_main[2][6'h25],        4'hA);
        check_val("WMP port[2][0]",   ram_out_port[2][0],        4'hA);
        check_val("WRR port[2]",      rom_out_port[2],           4'hA);
        check_val("WPM half-byte",    wpm_half_byte,             4'hA);
        check_val("Status WR0..2",    {ram_stat[2][8], ram_stat[2][9], ram_stat[2][10]}, 12'h456);

        if (err_cnt == 0) begin
            $display("ALL 21 INSTRUCTION GROUP CHECKS PASSED!");
        end else begin
            $display("FAILED with %0d errors.", err_cnt);
            $finish(1);
        end
        $finish(0);
    end
endmodule
