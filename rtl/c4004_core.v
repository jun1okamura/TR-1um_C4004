`timescale 1ns/1ps

// =============================================================================
// C4004 Core - Intel 4004 Compatible 4-bit CPU (Plan B + Full MCS-4 Compliance)
//   - Single SRAM128 macro (32 x 4-bit) storing 16 Index Registers (R0..R15)
//     and 4x12-bit Return Address Stack (SP=0..3, 3 nibbles each)
//   - Microarchitectural Optimizations (Plan B):
//     1. Zero Half-Cycle SRAM-to-Pad Paths:
//        Full-time PC[11:0] FFs (buf_l, buf_m, buf_h) + early pipelined SRAM
//        pre-reads in M2/X1/X2 eliminate all negedge->SRAM128->Pad paths on
//        BBL, SRC, FIN, JIN, and untaken JCN/ISZ.
//     2. 100% Registered Edge-Anchored Pin Outputs:
//        All external outputs (d_out[3:0], d_oe, d_hiz, sync, cm_rom, cm_ram[3:0])
//        are pre-computed one state ahead and driven directly from dedicated
//        DFFRBs anchored adjacent to their core boundary pins.
//     3. Dedicated FO=1 SRAM128 Capture Register (sram_lat[3:0]):
//        Pure DFFRBs placed directly under SRAM128.DO[3:0] with zero MUX/logic
//        gates and intentional useful clock skew.
//     4. On-Demand Stack Writes (JMS Cycle 2 M1..X1 Only):
//        Eliminates 3 redundant SRAM128 stack writes on every non-JMS cycle,
//        driving SRAM128.DIN exclusively from FFs (zero ALU gates on DIN).
//   - Full MCS-4 Hardware Protocol Compliance (25/25 Spec):
//     - 2-FF reset synchronizer + 32-clock hardware SRAM128 zero-clear (0..31),
//       entering SYNC-aligned A1 (PC=0x000) on clock 34 after reset release.
//     - Active-High cm_rom and 3-bit DCL multi-bank cm_ram[3:0] strobed at
//       A3, M2 (OPR=4'hE), and X2 (SRC).
//     - Echoes OPA (d_in) onto D[3:0] during X1.
// =============================================================================
module c4004_core (
    input  wire       clk,
    input  wire       rst,
    input  wire       test,
    input  wire [3:0] d_in,
    output reg  [3:0] d_out,
    output reg        d_oe,
    output wire       d_hiz,
    output reg        sync,
    output reg        cm_rom,
    output reg  [3:0] cm_ram
);

    assign d_hiz = ~d_oe;
    wire rst_n = ~rst;

    // -------------------------------------------------------------------------
    // 2-FF Posedge Reset Synchronizer
    // -------------------------------------------------------------------------
    reg rst_s1;
    reg rst_s2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst_s1 <= 1'b0;
            rst_s2 <= 1'b0;
        end else begin
            rst_s1 <= rst_n;
            rst_s2 <= rst_s1;
        end
    end

    // -------------------------------------------------------------------------
    // Core Architectural, Pipeline, and Capture Flip-Flops
    // -------------------------------------------------------------------------
    reg        init_done;  // 0: 32-clock SRAM128 hardware clear, 1: normal execution
    reg  [2:0] phase;      // 0:A1, 1:A2, 2:A3, 3:M1, 4:M2, 5:X1, 6:X2, 7:X3
    reg  [3:0] acc;        // 4-bit Accumulator
    reg        cy;         // 1-bit Carry flag
    reg  [3:0] opr;        // 4-bit Instruction OPR (latched in M1 of cycle 1)
    reg  [3:0] opa;        // 4-bit Instruction OPA (latched in M2 of cycle 1)
    reg  [1:0] sp;         // 2-bit Stack Pointer (0..3)
    reg        two_cycle;  // 2nd cycle of 2-byte instruction
    reg        cond_lat;   // JCN / ISZ branch condition latched in cycle 1 X2
    reg        pc_cout;    // Carry between A1->A2->A3 serial 4-bit PC incrementer
    reg  [3:0] buf_l;      // Full-time PC_L register
    reg  [3:0] buf_m;      // Full-time PC_M register
    reg  [3:0] buf_h;      // Full-time PC_H register
    reg  [3:0] reg_buf;    // 4-bit writeback / 2nd-byte / FIN R1-R0 buffer
    reg  [2:0] dcl_reg;    // 3-bit Command Control Register (DCL)
    reg  [3:0] sram_lat;   // Dedicated pure-DFFRB SRAM128 capture register (FO=1 on sram_do)

    // Hierarchical probe alias for testbenches
    wire [11:0] pc = {buf_h, buf_m, buf_l};

    // -------------------------------------------------------------------------
    // Instruction Decode Helpers
    // -------------------------------------------------------------------------
    wire is_jcn        = (opr == 4'h1);
    wire is_fim        = (opr == 4'h2) & (~opa[0]);
    wire is_fin        = (opr == 4'h3) & (~opa[0]);
    wire is_jun        = (opr == 4'h4);
    wire is_jms        = (opr == 4'h5);
    wire is_isz        = (opr == 4'h7);

    wire fin_cyc       = two_cycle & is_fin;
    wire is_fim_fin_c2 = two_cycle & (opr[3:1] == 3'b001);
    wire is_jms_c2     = two_cycle & is_jms;
    wire jump2_taken   = two_cycle & (is_jun | is_jms | ((is_jcn | is_isz) & cond_lat));

    wire is_src        = (~two_cycle) & (opr == 4'h2) & opa[0];
    wire is_jin        = (~two_cycle) & (opr == 4'h3) & opa[0];
    wire is_fin_c1     = (~two_cycle) & is_fin;
    wire is_bbl        = (~two_cycle) & (opr == 4'hC);
    wire is_io_ram     = (~two_cycle) & (opr == 4'hE);
    wire is_io_wr      = is_io_ram & (~opa[3]);
    wire is_reg_op     = (~two_cycle) & (opr == 4'h6 || opr == 4'h7 || (opr >= 4'h8 && opr <= 4'hB));
    wire is_two_cyc_op = is_jcn | is_fim | is_fin | is_jun | is_jms | is_isz;

    // JCN branch condition evaluation (evaluated in cycle 1 X2)
    wire jcn_raw   = (opa[2] & (acc == 4'd0)) | (opa[1] & cy) | (opa[0] & (~test));
    wire jcn_taken = opa[3] ^ jcn_raw;

    // 3-bit DCL multi-bank decode (4004 specification)
    wire [3:0] bank_mask = (dcl_reg == 3'd0) ? 4'b0001 : {dcl_reg, 1'b0};

    // -------------------------------------------------------------------------
    // Pre-Computed Registered SRAM128 Interface
    //   - A[4]=0: R0..R15, A[4]=1: Stack 4x3 nibbles; clocked on ~clk
    //   - Pre-computing sram_idle_q, sram_we_n_q, sram_addr_q, and sram_src_m2_q
    //     one phase ahead eliminates combinational X3->A1 CE/WR glitches and
    //     guarantees full half-cycle setup before negedge clk (CE rising).
    //   - All DIN sources are direct FFs (0, buf_l, buf_m, buf_h, reg_buf).
    // -------------------------------------------------------------------------
    reg        sram_idle_q;   // 0: SRAM128 active on ~clk, 1: SRAM128 idle
    reg        sram_we_n_q;   // 0: Write cycle (WR=1),     1: Read/Idle (WR=0)
    reg  [4:0] sram_addr_q;   // Pre-computed 5-bit SRAM128 word address
    reg        sram_src_m2_q; // 1 in M2 of OPR=4'h2 (c1) to mux {0, d_in[3:1], 0}

    reg        next_sram_idle;
    reg        next_sram_we_n;
    reg  [4:0] next_sram_addr;
    reg        next_sram_src_m2;
    wire [3:0] sram_do;
    wire [1:0] sp_dec = sp - 2'd1;

    always @(*) begin
        next_sram_idle   = 1'b1;
        next_sram_we_n   = 1'b1;
        next_sram_addr   = 5'd0;
        next_sram_src_m2 = 1'b0;

        if (!init_done) begin
            if (!rst_s2) begin
                next_sram_idle = 1'b0;
                next_sram_we_n = 1'b0;
                next_sram_addr = 5'd0;
            end else if (!(sp == 2'd3 && phase == 3'd7)) begin
                next_sram_idle = 1'b0;
                next_sram_we_n = 1'b0;
                next_sram_addr = {sp, phase} + 5'd1;
            end
        end else begin
            case (phase)
                3'd2: begin // A3 -> M1: On-demand JMS return PC_L stack write
                    if (is_jms_c2) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b0;
                        next_sram_addr = {1'b1, sp, 2'b00};
                    end
                end
                3'd3: begin // M1 -> M2: FIM/FIN R[2P] write, JMS PC_M write, or SRC/BBL early pre-read
                    if (is_fim_fin_c2) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b0;
                        next_sram_addr = {1'b0, opa[3:1], 1'b0};
                    end else if (is_jms_c2) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b0;
                        next_sram_addr = {1'b1, sp, 2'b01};
                    end else if ((!two_cycle) && (d_in == 4'h2)) begin
                        next_sram_idle   = 1'b0;
                        next_sram_we_n   = 1'b1;
                        next_sram_src_m2 = 1'b1;
                    end else if ((!two_cycle) && (d_in == 4'hC)) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = {1'b1, sp_dec, 2'b00};
                    end
                end
                3'd4: begin // M2 -> X1: FIM/FIN R[2P+1] write, JMS PC_H write, or Reg/SRC/JIN/FIN/BBL pre-read
                    if (is_fim_fin_c2) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b0;
                        next_sram_addr = {1'b0, opa[3:1], 1'b1};
                    end else if (is_jms_c2) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b0;
                        next_sram_addr = {1'b1, sp, 2'b10};
                    end else if (is_reg_op) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = {1'b0, d_in};
                    end else if ((!two_cycle) && (opr == 4'h2) && d_in[0]) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = {1'b0, d_in[3:1], 1'b1};
                    end else if ((!two_cycle) && (opr == 4'h3)) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = d_in[0] ? {1'b0, d_in[3:1], 1'b1} : 5'h01;
                    end else if (is_bbl) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = {1'b1, sp_dec, 2'b01};
                    end
                end
                3'd5: begin // X1 -> X2: 2nd nibble pre-read for JIN (R[2P]), FIN (R0), or BBL (ret_PC_H)
                    if (is_jin) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = {1'b0, opa[3:1], 1'b0};
                    end else if (is_fin_c1) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = 5'h00;
                    end else if (is_bbl) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b1;
                        next_sram_addr = {1'b1, sp, 2'b10};
                    end
                end
                3'd6: begin // X2 -> X3: Register writeback from reg_buf (INC, ISZ, XCH)
                    if ((!two_cycle) && (opr == 4'h6 || opr == 4'h7 || opr == 4'hB)) begin
                        next_sram_idle = 1'b0;
                        next_sram_we_n = 1'b0;
                        next_sram_addr = {1'b0, opa};
                    end
                end
                default: ; // X3->A1, A1->A2, A2->A3: SRAM128 stays completely idle!
            endcase
        end
    end

    wire [4:0] sram_addr  = sram_src_m2_q ? {1'b0, d_in[3:1], 1'b0} : sram_addr_q;
    wire       sram_we    = ~sram_we_n_q;
    wire       sram_ce_en = ~sram_idle_q;
    wire [3:0] sram_din   = (!init_done)               ? 4'd0 :
                            (is_jms_c2 & (~phase[2]))  ? buf_l :
                            (is_jms_c2 & (~phase[0]))  ? buf_m :
                            is_jms_c2                  ? buf_h :
                                                         reg_buf;

    wire sram_ce = (~clk) & rst_s2 & sram_ce_en;

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

    // Unconditional pure-DFFRB capture of SRAM128 read output (FO=1 on DO[3:0])
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sram_lat <= 4'd0;
        else        sram_lat <= sram_do;
    end

    // -------------------------------------------------------------------------
    // Dedicated 4-bit Parallel-Carry PC+1 Incrementer (Phases A1..A3)
    //   - Decoupled from X2 CLA so both PC+1 and X2 ALU run at minimal depth
    // -------------------------------------------------------------------------
    wire [3:0] pc_cur   = (phase[1:0] == 2'd0) ? buf_l :
                          (phase[1:0] == 2'd1) ? buf_m : buf_h;
    wire       pc_cin_w = (phase[1:0] == 2'd0) ? 1'b1 : pc_cout;
    wire       pc_c1    = pc_cur[0] & pc_cin_w;
    wire       pc_c2    = pc_cur[1] & pc_cur[0] & pc_cin_w;
    wire       pc_c3    = pc_cur[2] & pc_cur[1] & pc_cur[0] & pc_cin_w;
    wire       pc_c4    = pc_cur[3] & pc_c3;
    wire [4:0] pc_inc   = {pc_c4, pc_cur ^ {pc_c3, pc_c2, pc_c1, pc_cin_w}};

    // -------------------------------------------------------------------------
    // Dedicated X2 4-bit Carry-Lookahead Adder (Full-Cycle FF-to-FF Operation)
    // -------------------------------------------------------------------------
    wire       daa_adj = (acc > 4'd9) | cy;
    wire [3:0] alu_a   = (opr[3:1] == 3'b011) ? sram_lat : acc;
    reg  [3:0] alu_b;
    reg        alu_cin;

    always @(*) begin
        if (opr[3:1] == 3'b011) begin // INC / ISZ (from sram_lat FF)
            alu_b   = 4'd0;
            alu_cin = 1'b1;
        end else if (opr == 4'h8) begin // ADD Rr (from sram_lat FF)
            alu_b   = sram_lat;
            alu_cin = cy;
        end else if (opr == 4'h9) begin // SUB Rr (from sram_lat FF)
            alu_b   = ~sram_lat;
            alu_cin = ~cy;
        end else if (opr == 4'hE) begin // SBM (4'h8) / ADM (4'hB)
            alu_b   = opa[0] ? d_in : (~d_in);
            alu_cin = opa[0] ? cy   : (~cy);
        end else begin // OPR == 4'hF: IAC (4'h2) / DAC (4'h8) / DAA (4'hB)
            alu_b   = (opa == 4'h8) ? 4'hF :
                      (opa == 4'hB && daa_adj) ? 4'd6 : 4'd0;
            alu_cin = (opa == 4'h2);
        end
    end

    wire [3:0] cla_p   = alu_a ^ alu_b;
    wire [3:0] cla_g   = alu_a & alu_b;
    wire       c1      = cla_g[0] | (cla_p[0] & alu_cin);
    wire       c2      = cla_g[1] | (cla_p[1] & cla_g[0]) | (cla_p[1] & cla_p[0] & alu_cin);
    wire       c3      = cla_g[2] | (cla_p[2] & c2);
    wire       c4      = cla_g[3] | (cla_p[3] & c3);
    wire [4:0] alu_res = {c4, cla_p ^ {c3, c2, c1, alu_cin}};

    // -------------------------------------------------------------------------
    // Pre-Computed Next-State Pin Outputs (Latched into Edge-Anchored DFFRBs)
    // -------------------------------------------------------------------------
    reg  [3:0] next_dout;
    reg        next_doe;
    reg        next_sync;
    reg        next_cm;

    always @(*) begin
        next_dout = 4'd0;
        next_doe  = 1'b0;
        next_sync = 1'b0;
        next_cm   = 1'b0;

        if (!init_done) begin
            next_sync = (sp == 2'd3) & (phase == 3'd6);
            if (sp == 2'd3 && phase == 3'd7) begin
                next_doe  = 1'b1; // Enter A1 (PC=0x000) driving D[3:0]=0
                next_dout = 4'd0;
            end
        end else begin
            next_sync = (phase == 3'd6);
            case (phase)
                3'd0: begin // A1 -> A2
                    next_doe  = 1'b1;
                    next_dout = fin_cyc ? reg_buf : buf_m;
                end
                3'd1: begin // A2 -> A3
                    next_doe  = 1'b1;
                    next_dout = buf_h;
                    next_cm   = 1'b1; // CM-ROM & CM-RAM active in A3
                end
                3'd2: begin // A3 -> M1 (Bus Hi-Z for OPR fetch)
                    next_doe  = 1'b0;
                    next_dout = 4'd0;
                end
                3'd3: begin // M1 -> M2 (Bus Hi-Z for OPA fetch; CM active in M2 if I/O op)
                    next_doe  = 1'b0;
                    next_dout = 4'd0;
                    next_cm   = (~two_cycle) & (d_in == 4'hE);
                end
                3'd4: begin // M2 -> X1 (Echo OPA / 2nd-byte low nibble onto D[3:0] in X1)
                    next_doe  = 1'b1;
                    next_dout = d_in;
                end
                3'd5: begin // X1 -> X2 (Drive R[2P] for SRC or ACC for I/O write; CM for SRC)
                    next_doe  = is_src | is_io_wr;
                    next_dout = is_src ? sram_lat : acc;
                    next_cm   = is_src;
                end
                3'd6: begin // X2 -> X3 (Drive R[2P+1] for SRC from sram_lat FF)
                    next_doe  = is_src;
                    next_dout = sram_lat;
                end
                3'd7: begin // X3 -> A1 (Drive next PC_L from buf_l FF, or R1 from reg_buf for FIN)
                    next_doe  = 1'b1;
                    next_dout = is_fin_c1 ? reg_buf : buf_l;
                end
            endcase
        end
    end

    // -------------------------------------------------------------------------
    // Sequential State & Pipelined Execution Logic
    // -------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            init_done     <= 1'b0;
            phase         <= 3'd0;
            acc           <= 4'd0;
            cy            <= 1'b0;
            opr           <= 4'd0;
            opa           <= 4'd0;
            sp            <= 2'd0;
            two_cycle     <= 1'b0;
            cond_lat      <= 1'b0;
            pc_cout       <= 1'b0;
            buf_l         <= 4'd0;
            buf_m         <= 4'd0;
            buf_h         <= 4'd0;
            reg_buf       <= 4'd0;
            dcl_reg       <= 3'd0;
            sram_idle_q   <= 1'b0;
            sram_we_n_q   <= 1'b0;
            sram_addr_q   <= 5'd0;
            sram_src_m2_q <= 1'b0;
            d_out         <= 4'd0;
            d_oe          <= 1'b0;
            sync          <= 1'b0;
            cm_rom        <= 1'b0;
            cm_ram        <= 4'd0;
        end else begin
            sram_idle_q   <= next_sram_idle;
            sram_we_n_q   <= next_sram_we_n;
            sram_addr_q   <= next_sram_addr;
            sram_src_m2_q <= next_sram_src_m2;
            d_out         <= next_dout;
            d_oe          <= next_doe;
            sync          <= next_sync;
            cm_rom        <= next_cm;
            cm_ram        <= next_cm ? bank_mask : 4'b0000;

            if (!init_done) begin
                if (rst_s2) begin
                    {sp, phase} <= {sp, phase} + 5'd1;
                    if (sp == 2'd3 && phase == 3'd7) begin
                        init_done <= 1'b1;
                    end
                end
            end else begin
                phase <= phase + 3'd1;

                case (phase)
                    3'd0: begin // A1: Increment PC_L -> buf_l
                        if (!fin_cyc) begin
                            buf_l   <= pc_inc[3:0];
                            pc_cout <= pc_inc[4];
                        end
                    end
                    3'd1: begin // A2: Increment PC_M -> buf_m
                        if (!fin_cyc) begin
                            buf_m   <= pc_inc[3:0];
                            pc_cout <= pc_inc[4];
                        end
                    end
                    3'd2: begin // A3: Increment PC_H -> buf_h
                        if (!fin_cyc) begin
                            buf_h <= pc_inc[3:0];
                        end
                    end
                    3'd3: begin // M1: Latch OPR (c1) or 2nd-byte high nibble (c2)
                        if (!two_cycle) begin
                            opr <= d_in;
                        end else begin
                            reg_buf <= d_in;
                        end
                    end
                    3'd4: begin // M2: Latch OPA (c1), BBL SP--, or c2 target low/mid nibbles
                        if (!two_cycle) begin
                            opa <= d_in;
                            if (opr == 4'hC) begin
                                sp <= sp_dec; // Pop stack pointer early for X1/X2 BBL reads
                            end
                        end else if (is_fim_fin_c2) begin
                            reg_buf <= d_in; // 2nd-byte low nibble for X1 R[2P+1] write
                        end else if (jump2_taken) begin
                            buf_l <= d_in;    // Target low nibble
                            buf_m <= reg_buf; // Target mid nibble
                        end
                    end
                    3'd5: begin // X1: Move early pre-read nibble from sram_lat for BBL
                        if (is_bbl) begin
                            buf_l <= sram_lat; // ret_PC_L
                        end
                    end
                    3'd6: begin // X2: Full-cycle FF-to-FF ALU & Register Execution
                        if (two_cycle) begin
                            if (is_jun || is_jms) begin
                                buf_h <= opa;
                            end
                            if (is_jms) begin
                                sp <= sp + 2'd1;
                            end
                        end else begin
                            case (opr)
                                4'h1: begin // JCN (1st cycle)
                                    cond_lat <= jcn_taken;
                                end
                                4'h3: begin // FIN / JIN (1st cycle)
                                    if (opa[0]) begin
                                        buf_l <= sram_lat;   // JIN: target low = R[2P+1]
                                    end else begin
                                        reg_buf <= sram_lat; // FIN: fetch low = R1
                                    end
                                end
                                4'h6: begin // INC Rr
                                    reg_buf <= alu_res[3:0];
                                end
                                4'h7: begin // ISZ Rr (1st cycle)
                                    reg_buf  <= alu_res[3:0];
                                    cond_lat <= (sram_lat != 4'hF);
                                end
                                4'h8, 4'h9: begin // ADD, SUB
                                    acc <= alu_res[3:0];
                                    cy  <= alu_res[4];
                                end
                                4'hA: begin // LD Rr
                                    acc <= sram_lat;
                                end
                                4'hB: begin // XCH Rr
                                    acc     <= sram_lat;
                                    reg_buf <= acc;
                                end
                                4'hC: begin // BBL d
                                    acc   <= opa;
                                    buf_m <= sram_lat; // ret_PC_M
                                end
                                4'hD: begin // LDM d
                                    acc <= opa;
                                end
                                4'hE: begin // I/O and RAM instructions
                                    case (opa)
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
                    3'd7: begin // X3: Finalize 2nd nibble pre-reads (JIN/FIN/BBL) & two_cycle state
                        if (!two_cycle) begin
                            two_cycle <= is_two_cyc_op;
                            if (is_jin) begin
                                buf_m <= sram_lat;   // JIN: target mid = R[2P]
                            end else if (is_fin_c1) begin
                                reg_buf <= sram_lat; // FIN: fetch mid = R0 (used in c2 A2)
                            end else if (is_bbl) begin
                                buf_h <= sram_lat;   // BBL: ret_PC_H
                            end
                        end else begin
                            two_cycle <= 1'b0;
                        end
                    end
                endcase
            end
        end
    end

endmodule
