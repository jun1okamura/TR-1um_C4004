`timescale 1ns/1ps

// =============================================================================
// C4004 Core - Intel 4004 Compatible 4-bit CPU (Trial 06 Architecture)
//   - Single SRAM128 macro (32 x 4-bit) storing 16 Index Registers (R0..R15)
//     and 4x12-bit Stack/PC File (SP=0..3, 3 nibbles each)
//   - Trial 06 Microarchitectural Optimizations:
//     1. Dedicated High-Drive BUF_X2 Buffers on D_HIZ, D_OE, and SRAM128.CE:
//        Eliminates the high-resistance 4-series-PMOS NOR4 _1071_ and 1x-drive
//        INV_X1 _1072_ driving the 2-mm M1/M2 d_hiz/d_oe pad distribution network!
//        Dedicated BUF_X2 drivers (u_buf_dhiz placed at West d_hiz pin and
//        u_buf_doe placed at South d_oe pin) slash bus turnaround delay in M1.
//     2. Non-Stop Shadow PC Bypass (pc_init_n stays 0 across all Reg/ALU/FIM/SRC
//        instructions; buf_l/buf_m/buf_h exclusively hold PC+1)
//     3. Symmetric 4-bit NAND3 + MUXDFFRB X1 Pre-Read Pipeline (reg_buf[3:0])
//     4. Explicit 4-bit Carry-Lookahead Adder (CLA) operating FF-to-FF over a
//        full clock period (1.0 * T_clk) in X2
// =============================================================================
module c4004_core (
    input  wire       clk,
    input  wire       rst,
    input  wire       test,
    input  wire [3:0] d_in,
    output reg  [3:0] d_out,
    output reg        d_oe,
    output wire       d_hiz,
    output wire       sync,
    output wire       cm_rom,
    output wire [3:0] cm_ram
);

    assign d_hiz = ~d_oe;
    wire rst_n = ~rst;

    // -------------------------------------------------------------------------
    // Core Architectural & Pipeline Flip-Flops (41 FFs total)
    // -------------------------------------------------------------------------
    reg  [2:0] phase;      // 0:A1, 1:A2, 2:A3, 3:M1, 4:M2, 5:X1, 6:X2, 7:X3
    reg  [3:0] acc;        // 4-bit Accumulator
    reg        cy;         // 1-bit Carry flag
    reg  [3:0] opr;        // 4-bit Instruction OPR (latched in M1 of cycle 1)
    reg  [3:0] opa;        // 4-bit Instruction OPA (latched in M2 of cycle 1)
    reg  [1:0] sp;         // 2-bit Stack Pointer (0..3)
    reg        two_cycle;  // 2nd cycle of 2-byte instruction
    reg        pc_init_n;  // 0: drive PC directly from buf_l/m/h FFs, 1: read PC from SRAM128
    reg        isz_taken;  // ISZ branch taken flag from cycle 1
    reg        pc_cout;    // Carry between A1->A2->A3 serial 4-bit PC incrementer
    reg  [3:0] buf_l;      // Dedicated Shadow PC_L (or FIN address low nibble)
    reg  [3:0] buf_m;      // Dedicated Shadow PC_M (or FIN address mid nibble)
    reg  [3:0] buf_h;      // Dedicated Shadow PC_H
    reg  [3:0] reg_buf;    // Dedicated 4-bit Pipeline Reg: unconditional X1 SRAM pre-read & 2nd-byte buffer!
    reg  [2:0] dcl_reg;    // 3-bit Command Control Register (DCL)
    reg        wpm_half;   // 1-bit WPM half-byte toggle

    // Instruction decode helpers
    wire fin_cyc       = two_cycle & (opr == 4'h3);
    wire is_fim_fin_c2 = two_cycle & (opr[3:1] == 3'b001);
    wire is_src        = (~two_cycle) & (opr == 4'h2) & opa[0];
    wire is_jin        = (~two_cycle) & (opr == 4'h3) & opa[0];
    wire is_fin_c1     = (~two_cycle) & (opr == 4'h3) & (~opa[0]);
    wire is_io_ram     = (~two_cycle) & (opr == 4'hE);
    wire is_io_wr      = is_io_ram & (~opa[3]);
    wire is_reg_op     = (~two_cycle) & (opr == 4'h6 || opr == 4'h7 || (opr >= 4'h8 && opr <= 4'hB));

    // JCN branch condition evaluation
    wire jcn_raw   = (opa[2] & (acc == 4'd0)) | (opa[1] & cy) | (opa[0] & (~test));
    wire jcn_taken = opa[3] ^ jcn_raw;

    // -------------------------------------------------------------------------
    // SRAM128 Interface (A[4]=0: R0..R15, A[4]=1: Stack 4x3 nibbles)
    //   - SRAM128 is clocked on ~clk (falling edge of clk = mid-cycle)
    //   - Address, DI, WE, CE are set up in the first half of the cycle
    // -------------------------------------------------------------------------
    reg  [4:0] sram_addr;
    reg  [3:0] sram_din;
    reg        sram_we;
    reg        sram_ce_en;
    wire [3:0] sram_do;

    always @(*) begin
        sram_addr  = {1'b1, sp, 2'b00};
        sram_din   = buf_l;
        sram_we    = 1'b0;
        sram_ce_en = 1'b1;

        case (phase)
            3'd0: begin // A1: Read PC_L (only needed when pc_init_n == 1)
                sram_addr  = {1'b1, sp, 2'b00};
                sram_we    = 1'b0;
                sram_ce_en = pc_init_n & (~fin_cyc);
            end
            3'd1: begin // A2: Read PC_M (only needed when pc_init_n == 1)
                sram_addr  = {1'b1, sp, 2'b01};
                sram_we    = 1'b0;
                sram_ce_en = pc_init_n & (~fin_cyc);
            end
            3'd2: begin // A3: Read PC_H (only needed when pc_init_n == 1)
                sram_addr  = {1'b1, sp, 2'b10};
                sram_we    = 1'b0;
                sram_ce_en = pc_init_n;
            end
            3'd3: begin // M1: Write PC_L + 1
                sram_addr  = {1'b1, sp, 2'b00};
                sram_din   = buf_l;
                sram_we    = ~fin_cyc;
                sram_ce_en = ~fin_cyc;
            end
            3'd4: begin // M2: Write R[2P] early for FIM/FIN cycle 2, else Write PC_M + c
                if (is_fim_fin_c2) begin
                    sram_addr  = {1'b0, opa[3:1], 1'b0};
                    sram_din   = reg_buf;
                    sram_we    = 1'b1;
                    sram_ce_en = 1'b1;
                end else begin
                    sram_addr  = {1'b1, sp, 2'b01};
                    sram_din   = buf_m;
                    sram_we    = ~fin_cyc;
                    sram_ce_en = ~fin_cyc;
                end
            end
            3'd5: begin // X1: Write R[2P+1] early for FIM/FIN cycle 2, or Pre-Read Index Reg into reg_buf!
                if (is_fim_fin_c2) begin
                    sram_addr  = {1'b0, opa[3:1], 1'b1};
                    sram_din   = reg_buf;
                    sram_we    = 1'b1;
                    sram_ce_en = 1'b1;
                end else if (is_fin_c1) begin
                    sram_addr  = 5'h00; // Pre-read R0 for FIN
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b1;
                end else if (is_src || is_jin) begin
                    sram_addr  = {1'b0, opa[3:1], 1'b0}; // Pre-read R[2P] for SRC / JIN
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b1;
                end else if (is_reg_op) begin
                    sram_addr  = {1'b0, opa}; // Pre-read R[opa] into reg_buf!
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b1;
                end else begin
                    sram_addr  = {1'b1, sp, 2'b10}; // Write PC_H + c for non-reg ops
                    sram_din   = buf_h;
                    sram_we    = ~fin_cyc;
                    sram_ce_en = ~fin_cyc;
                end
            end
            3'd6: begin // X2: Write PC_M + c (for FIM c2) or Write PC_H + c (for reg_op / SRC / FIN / JIN)
                if (two_cycle && (opr == 4'h2)) begin
                    sram_addr  = {1'b1, sp, 2'b01};
                    sram_din   = buf_m;
                    sram_we    = 1'b1;
                    sram_ce_en = 1'b1;
                end else if (is_reg_op || is_src || is_jin || is_fin_c1) begin
                    sram_addr  = {1'b1, sp, 2'b10};
                    sram_din   = buf_h;
                    sram_we    = 1'b1;
                    sram_ce_en = 1'b1;
                end else begin
                    sram_addr  = {1'b1, sp, 2'b10};
                    sram_din   = buf_h;
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b0;
                end
            end
            3'd7: begin // X3: Write PC_H + c (for FIM c2), Register Writeback (from reg_buf), or 2nd Nibble Read
                if (two_cycle && (opr == 4'h2)) begin
                    sram_addr  = {1'b1, sp, 2'b10}; // Write PC_H + c to stack for FIM c2
                    sram_din   = buf_h;
                    sram_we    = 1'b1;
                    sram_ce_en = 1'b1;
                end else if (is_fin_c1) begin
                    sram_addr  = 5'h01; // Read R1
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b1;
                end else if (is_src || is_jin) begin
                    sram_addr  = {1'b0, opa[3:1], 1'b1}; // Read R[2P+1]
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b1;
                end else if ((~two_cycle) && (opr == 4'h6 || opr == 4'h7 || opr == 4'hB)) begin
                    sram_addr  = {1'b0, opa}; // Write R[opa] from reg_buf for INC, ISZ, XCH!
                    sram_din   = reg_buf;
                    sram_we    = 1'b1;
                    sram_ce_en = 1'b1;
                end else begin
                    sram_addr  = {1'b0, opa};
                    sram_we    = 1'b0;
                    sram_ce_en = 1'b0;
                end
            end
        endcase
    end

    wire sram_ce = (~clk) & rst_n & sram_ce_en;

    SRAM128 u_sram (
        .A0  (sram_addr[0]),
        .A1  (sram_addr[1]),
        .A2  (sram_addr[2]),
        .A3  (sram_addr[3]),
        .A4  (sram_addr[4]),
        .CE  (sram_ce),
        .WR  (sram_we),
        .DIN (sram_din),
        .DO  (sram_do)
    );

    // -------------------------------------------------------------------------
    // Unified 4-bit Carry-Lookahead Adder:
    //   - Phase A1..A3 (0..2): Serial PC+1 incrementer
    //   - Phase X2     (6):    Full-cycle FF-to-FF ALU using reg_buf (latched from SRAM in X1!)
    // -------------------------------------------------------------------------
    wire [3:0] cur_pc_l = (fin_cyc | (~pc_init_n)) ? buf_l : sram_do;
    wire [3:0] cur_pc_m = (fin_cyc | (~pc_init_n)) ? buf_m : sram_do;
    wire [3:0] cur_pc_h = (~pc_init_n)             ? buf_h : sram_do;

    wire       daa_adj  = (acc > 4'd9) | cy;
    reg  [3:0] alu_a;
    reg  [3:0] alu_b;
    reg        alu_cin;

    always @(*) begin
        if (!phase[2]) begin
            alu_a   = (phase[1:0] == 2'd0) ? cur_pc_l :
                      (phase[1:0] == 2'd1) ? cur_pc_m : cur_pc_h;
            alu_b   = 4'd0;
            alu_cin = (phase[1:0] == 2'd0) ? 1'b1 : pc_cout;
        end else if (opr[3:1] == 3'b011) begin // INC / ISZ (computed in X2 from reg_buf FF!)
            alu_a   = reg_buf;
            alu_b   = 4'd0;
            alu_cin = 1'b1;
        end else if (opr == 4'h8) begin // ADD Rr (computed in X2 from reg_buf FF!)
            alu_a   = acc;
            alu_b   = reg_buf;
            alu_cin = cy;
        end else if (opr == 4'h9) begin // SUB Rr (computed in X2 from reg_buf FF!)
            alu_a   = acc;
            alu_b   = ~reg_buf;
            alu_cin = ~cy;
        end else if (opr == 4'hE) begin // SBM (4'h8) / ADM (4'hB)
            alu_a   = acc;
            alu_b   = opa[0] ? d_in : (~d_in);
            alu_cin = opa[0] ? cy   : (~cy);
        end else begin // OPR == 4'hF: IAC (4'h2) / DAC (4'h8) / DAA (4'hB)
            alu_a   = acc;
            alu_b   = (opa == 4'h8) ? 4'hF :
                      (opa == 4'hB && daa_adj) ? 4'd6 : 4'd0;
            alu_cin = (opa == 4'h2);
        end
    end

    // Explicit Carry-Lookahead Logic
    wire [3:0] cla_p = alu_a ^ alu_b;
    wire [3:0] cla_g = alu_a & alu_b;
    wire       c1    = cla_g[0] | (cla_p[0] & alu_cin);
    wire       c2    = cla_g[1] | (cla_p[1] & cla_g[0]) | (cla_p[1] & cla_p[0] & alu_cin);
    wire       c3    = cla_g[2] | (cla_p[2] & c2);
    wire       c4    = cla_g[3] | (cla_p[3] & c3);
    wire [4:0] alu_res = {c4, cla_p ^ {c3, c2, c1, alu_cin}};

    // -------------------------------------------------------------------------
    // Data Bus Output Multiplexer (d_out, d_oe) & External Control Signals
    //   Notice: In X2 (phase 6), SRC outputs reg_buf directly from FF at posedge clk!
    // -------------------------------------------------------------------------
    always @(*) begin
        d_oe  = 1'b0;
        d_out = 4'd0;
        case (phase)
            3'd0: begin
                d_oe  = 1'b1;
                d_out = cur_pc_l;
            end
            3'd1: begin
                d_oe  = 1'b1;
                d_out = cur_pc_m;
            end
            3'd2: begin
                d_oe  = 1'b1;
                d_out = cur_pc_h;
            end
            3'd6: begin
                if (is_src) begin
                    d_oe  = 1'b1;
                    d_out = reg_buf; // Driven directly from reg_buf FF at posedge clk!
                end else if (is_io_wr) begin
                    d_oe  = 1'b1;
                    d_out = acc;
                end
            end
            3'd7: begin
                if (is_src) begin
                    d_oe  = 1'b1;
                    d_out = sram_do;
                end
            end
            default: begin
                d_oe  = 1'b0;
                d_out = 4'd0;
            end
        endcase
    end

    assign sync   = (phase == 3'd7);
    assign cm_rom = ~((phase == 3'd2) || ((phase == 3'd6) && is_io_ram && (opa == 4'h2 || opa == 4'h3 || opa == 4'hA)));

    // DCL bank decode (active-low during A3 and during X2 for SRC/IO_RAM/DCL)
    wire cm_ram_active = (phase == 3'd2) ||
                         ((phase == 3'd6) && (~two_cycle) && (is_src || is_io_ram || (opr == 4'hF && opa == 4'hD)));
    wire [3:0] bank_sel = {dcl_reg[2], dcl_reg[1], dcl_reg[0], (dcl_reg == 3'b000)};
    assign cm_ram = cm_ram_active ? (~bank_sel) : 4'b1111;

    // -------------------------------------------------------------------------
    // Sequential State & Pipelined Execution Logic
    // -------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase     <= 3'd0;
            acc       <= 4'd0;
            cy        <= 1'b0;
            opr       <= 4'd0;
            opa       <= 4'd0;
            sp        <= 2'd0;
            two_cycle <= 1'b0;
            pc_init_n <= 1'b0;
            isz_taken <= 1'b0;
            pc_cout   <= 1'b0;
            buf_l     <= 4'd0;
            buf_m     <= 4'd0;
            buf_h     <= 4'd0;
            reg_buf   <= 4'd0;
            dcl_reg   <= 3'd0;
            wpm_half  <= 1'b0;
        end else begin
            phase <= phase + 3'd1;

            case (phase)
                3'd0: begin // A1
                    if (!fin_cyc) begin
                        buf_l   <= alu_res[3:0];
                        pc_cout <= alu_res[4];
                    end
                end
                3'd1: begin // A2
                    if (!fin_cyc) begin
                        buf_m   <= alu_res[3:0];
                        pc_cout <= alu_res[4];
                    end
                end
                3'd2: begin // A3
                    if (!fin_cyc) begin
                        buf_h     <= alu_res[3:0];
                        pc_init_n <= 1'b0; // buf_l/m/h always hold valid PC+1!
                    end
                end
                3'd3: begin // M1
                    if (!two_cycle) begin
                        opr <= d_in;
                    end else begin
                        reg_buf <= d_in; // Latch 2nd-byte high nibble into reg_buf (buf_l/m/h stay untouched!)
                        if (!is_fim_fin_c2) begin
                            pc_init_n <= 1'b1; // Default for untaken JCN/ISZ
                        end
                    end
                end
                3'd4: begin // M2
                    if (!two_cycle) begin
                        opa <= d_in;
                    end else if (is_fim_fin_c2) begin
                        reg_buf <= d_in; // Latch 2nd-byte low nibble into reg_buf (R[2P] written in M2!)
                    end else begin
                        buf_m <= d_in;   // Second byte low nibble for JCN/JUN/JMS/ISZ
                    end
                end
                3'd5: begin // X1: Latch Pre-Read SRAM128 Index Reg into reg_buf (buf_l stays untouched!)
                    if (is_fin_c1 || is_jin) begin
                        buf_m <= sram_do; // R0 (for FIN) or R[2P] (for JIN)
                    end else if (is_reg_op || is_src) begin
                        reg_buf <= sram_do; // R[opa] (for ALU/LD/XCH/INC/ISZ) or R[2P] (for SRC) -> buf_l untouched!
                    end
                end
                3'd6: begin // X2: Execute ALU / Register Ops over FULL Clock Period from reg_buf!
                    if (!two_cycle) begin
                        case (opr)
                            4'h6: begin // INC Rr
                                reg_buf <= alu_res[3:0];
                            end
                            4'h7: begin // ISZ Rr (1st cycle)
                                reg_buf   <= alu_res[3:0];
                                isz_taken <= (reg_buf != 4'hF);
                            end
                            4'h8, 4'h9: begin // ADD, SUB
                                acc <= alu_res[3:0];
                                cy  <= alu_res[4];
                            end
                            4'hA: begin // LD Rr
                                acc <= reg_buf;
                            end
                            4'hB: begin // XCH Rr
                                acc     <= reg_buf;
                                reg_buf <= acc;
                            end
                            4'hC: begin // BBL d
                                sp        <= sp - 2'd1;
                                acc       <= opa;
                                pc_init_n <= 1'b1; // Load return PC from stack in next A1..A3
                            end
                            4'hD: begin // LDM d
                                acc <= opa;
                            end
                            4'hE: begin // I/O and RAM instructions
                                case (opa)
                                    4'h3: wpm_half <= ~wpm_half;
                                    4'h8, 4'hB: begin // SBM, ADM
                                        acc <= alu_res[3:0];
                                        cy  <= alu_res[4];
                                    end
                                    4'h9, 4'hA, 4'hC, 4'hD, 4'hE, 4'hF: begin // RDM, RDR, RD0..RD3
                                        acc <= d_in;
                                    end
                                    default: ;
                                endcase
                            end
                            4'hF: begin // Accumulator Group instructions
                                case (opa)
                                    4'h0: begin // CLB
                                        acc <= 4'd0;
                                        cy  <= 1'b0;
                                    end
                                    4'h1: cy  <= 1'b0;       // CLC
                                    4'h2, 4'h8: begin        // IAC, DAC
                                        acc <= alu_res[3:0];
                                        cy  <= alu_res[4];
                                    end
                                    4'h3: cy  <= ~cy;        // CMC
                                    4'h4: acc <= ~acc;       // CMA
                                    4'h5: begin              // RAL
                                        acc <= {acc[2:0], cy};
                                        cy  <= acc[3];
                                    end
                                    4'h6: begin              // RAR
                                        acc <= {cy, acc[3:1]};
                                        cy  <= acc[0];
                                    end
                                    4'h7: begin              // TCC
                                        acc <= {3'b000, cy};
                                        cy  <= 1'b0;
                                    end
                                    4'h9: begin              // TCS
                                        acc <= cy ? 4'd10 : 4'd9;
                                        cy  <= 1'b0;
                                    end
                                    4'hA: cy  <= 1'b1;       // STC
                                    4'hB: begin              // DAA
                                        acc <= alu_res[3:0];
                                        if (alu_res[4]) cy <= 1'b1;
                                    end
                                    4'hC: begin              // KBP
                                        case (acc)
                                            4'b0000: acc <= 4'd0;
                                            4'b0001: acc <= 4'd1;
                                            4'b0010: acc <= 4'd2;
                                            4'b0100: acc <= 4'd3;
                                            4'b1000: acc <= 4'd4;
                                            default: acc <= 4'hF;
                                        endcase
                                    end
                                    4'hD: dcl_reg <= acc[2:0]; // DCL
                                    default: ;
                                endcase
                            end
                            default: ;
                        endcase
                    end
                end
                3'd7: begin // X3: 2nd Nibble Read/Write & Two-Cycle Branch Commit
                    if (!two_cycle) begin
                        if ((opr == 4'h1) ||
                            (opr == 4'h2 && !opa[0]) ||
                            (opr == 4'h3 && !opa[0]) ||
                            (opr == 4'h4) ||
                            (opr == 4'h5) ||
                            (opr == 4'h7)) begin
                            two_cycle <= 1'b1;
                        end
                        if (opr == 4'h3) begin // FIN (read R1) or JIN (read R[2P+1])
                            buf_l <= sram_do;
                            if (opa[0]) begin // JIN jumps to {PC_H, R[2P], R[2P+1]}
                                pc_init_n <= 1'b0;
                            end else begin
                                pc_init_n <= 1'b1; // FIN cycle 2 A3 reads PC_H from SRAM128
                            end
                        end
                    end else begin
                        two_cycle <= 1'b0;
                        case (opr)
                            4'h1: begin // JCN cycle 2
                                if (jcn_taken) begin
                                    buf_l     <= buf_m;
                                    buf_m     <= reg_buf;
                                    pc_init_n <= 1'b0;
                                end
                            end
                            4'h4: begin // JUN cycle 2
                                buf_l     <= buf_m;
                                buf_m     <= reg_buf;
                                buf_h     <= opa;
                                pc_init_n <= 1'b0;
                            end
                            4'h5: begin // JMS cycle 2
                                sp        <= sp + 2'd1;
                                buf_l     <= buf_m;
                                buf_m     <= reg_buf;
                                buf_h     <= opa;
                                pc_init_n <= 1'b0;
                            end
                            4'h7: begin // ISZ cycle 2
                                if (isz_taken) begin
                                    buf_l     <= buf_m;
                                    buf_m     <= reg_buf;
                                    pc_init_n <= 1'b0;
                                end
                            end
                            default: ;
                        endcase
                    end
                end
            endcase
        end
    end

endmodule
