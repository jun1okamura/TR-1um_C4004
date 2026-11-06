// Intel 4004 Compatible Single-Phase CMOS CPU Core (C4004) for OpenSUSI TR-1um
// Target Library: TR-1um_APRtools/stdcell/v59_4 + module/SRAM128 (32w x 4b 6T SRAM)
//
// Design Rules (reference/06_design_policy.md & 09_work_memo.md):
//   1. Single-phase clock (clk). 8 states per machine cycle: A1..A3, M1..M2, X1..X3.
//   2. No internal tri-state buses. D[3:0] split into d_in[3:0], d_out[3:0], d_hiz.
//      (d_hiz = 1: High-Z/input mode; d_hiz = 0: output drive mode, matching OSS_ESD_5V_DIO.HIZ)
//   3. Single-port SRAM128 macro stores:
//        - A[4:0] = 0x00..0x0F: 16 x 4-bit Scratchpad Index Registers (R0..R15)
//        - A[4:0] = 0x10..0x1F: Subroutine Return Address Stack (3 nibbles x 4 levels)
//      Active 12-bit Program Counter (pc[11:0]) is held in FFs so each state performs
//      at most 1 SRAM access (CE = ~clk & sram_ce_en), with zero port conflicts.

`timescale 1ns/1ps

module c4004_core (
    input  wire       clk,
    input  wire       rst,
    input  wire       test,
    input  wire [3:0] d_in,
    output reg  [3:0] d_out,
    output wire       d_oe,
    output wire       d_hiz,
    output wire       sync,
    output wire       cm_rom,
    output wire [3:0] cm_ram
);

    wire rst_n = ~rst;

    // =========================================================================
    // 1. Machine Cycle State Definitions (8 states / machine cycle)
    // =========================================================================
    localparam [2:0] ST_A1 = 3'd0,
                     ST_A2 = 3'd1,
                     ST_A3 = 3'd2,
                     ST_M1 = 3'd3,
                     ST_M2 = 3'd4,
                     ST_X1 = 3'd5,
                     ST_X2 = 3'd6,
                     ST_X3 = 3'd7;

    reg [2:0]  state;
    reg        cyc2;       // 1 = 2nd machine cycle of 2-cycle instruction
    reg [3:0]  opr;        // Instruction Opcode (M1)
    reg [3:0]  opa;        // Instruction Modifier (M2)
    reg [3:0]  acc;        // 4-bit Accumulator
    reg        cy;         // Carry / Link flag
    reg [11:0] pc;         // Active 12-bit Program Counter
    reg [1:0]  sp;         // 2-bit Stack Pointer
    reg [2:0]  dcl;        // 3-bit Command Control register (DCL)
    reg [3:0]  tmp;        // Shared 4-bit buffer (FIN/FIM/SRC/XCH/INC/ISZ)
    reg        pc_cy;      // Carry propagation FF across A1 -> A2 -> A3
    reg        take_lat;   // Latched branch condition for JCN / ISZ in cycle 2

    // =========================================================================
    // 2. Instruction Decode Signals
    // =========================================================================
    wire is_jcn = (opr == 4'h1);
    wire is_fim = (opr == 4'h2) && (~opa[0]);
    wire is_src = (opr == 4'h2) && ( opa[0]);
    wire is_fin = (opr == 4'h3) && (~opa[0]);
    wire is_jin = (opr == 4'h3) && ( opa[0]);
    wire is_jun = (opr == 4'h4);
    wire is_jms = (opr == 4'h5);
    wire is_inc = (opr == 4'h6);
    wire is_isz = (opr == 4'h7);
    wire is_add = (opr == 4'h8);
    wire is_sub = (opr == 4'h9);
    wire is_ld  = (opr == 4'hA);
    wire is_xch = (opr == 4'hB);
    wire is_bbl = (opr == 4'hC);
    wire is_ldm = (opr == 4'hD);
    wire is_ior = (opr == 4'hE);
    wire is_acc = (opr == 4'hF);

    wire is_2cyc_op = is_jcn | is_fim | is_fin | is_jun | is_jms | is_isz;

    // JCN condition evaluation: opa = {C1(invert), C2(acc==0), C3(cy==1), C4(test==1)}
    wire jcn_cond = (opa[2] & (acc == 4'd0)) | (opa[1] & cy) | (opa[0] & test);
    wire jcn_take = opa[3] ^ jcn_cond;

    // Whether Cycle 2 M1/M2 updates PC[7:0] with target address {a2, a1}
    wire cyc2_jump_take = cyc2 & (is_jun | is_jms | ((is_jcn | is_isz) & take_lat));

    // =========================================================================
    // 3. Shared 4-bit Adder / Incrementer (PC+1, INC/ISZ, ADD/SUB, ADM/SBM, IAC/DAC/DAA)
    // =========================================================================
    wire [3:0] sram_do;

    wire [3:0] pc_nib = (state == ST_A1) ? pc[3:0]  :
                        (state == ST_A2) ? pc[7:4]  : pc[11:8];

    reg  [3:0] alu_a;
    reg  [3:0] alu_b;
    reg        alu_cin;

    always @(*) begin
        if (state == ST_A1 || state == ST_A2 || state == ST_A3) begin
            alu_a   = pc_nib;
            alu_b   = 4'h0;
            alu_cin = (state == ST_A1) ? 1'b1 : pc_cy;
        end else if (state == ST_X1) begin
            if (is_inc || is_isz) begin
                alu_a   = sram_do;
                alu_b   = 4'h0;
                alu_cin = 1'b1;
            end else if (is_add) begin
                alu_a   = acc;
                alu_b   = sram_do;
                alu_cin = cy;
            end else if (is_sub) begin
                alu_a   = acc;
                alu_b   = ~sram_do;
                alu_cin = ~cy;
            end else if (is_acc && opa == 4'h8) begin // DAC: acc + 15
                alu_a   = acc;
                alu_b   = 4'hF;
                alu_cin = 1'b0;
            end else if (is_acc && opa == 4'hB) begin // DAA: acc + 6
                alu_a   = acc;
                alu_b   = 4'd6;
                alu_cin = 1'b0;
            end else begin                            // IAC: acc + 1
                alu_a   = acc;
                alu_b   = 4'h0;
                alu_cin = 1'b1;
            end
        end else begin
            // ST_X2: ADM (opa==4'hB) or SBM (opa==4'h8)
            alu_a   = acc;
            alu_b   = (opa == 4'h8) ? (~d_in) : d_in;
            alu_cin = (opa == 4'h8) ? (~cy)   : cy;
        end
    end

    wire [4:0] alu_res  = {1'b0, alu_a} + {1'b0, alu_b} + {4'b0000, alu_cin};
    wire [3:0] alu_sum  = alu_res[3:0];
    wire       alu_cout = alu_res[4];

    // KBP (Keyboard Process) truth table
    reg [3:0] kbp_val;
    always @(*) begin
        case (acc)
            4'b0000: kbp_val = 4'd0;
            4'b0001: kbp_val = 4'd1;
            4'b0010: kbp_val = 4'd2;
            4'b0100: kbp_val = 4'd3;
            4'b1000: kbp_val = 4'd4;
            default: kbp_val = 4'hF;
        endcase
    end

    // DAA condition: adjust if cy == 1 or acc > 9
    wire daa_adj = cy | (acc > 4'd9);

    // =========================================================================
    // 4. SRAM128 Control & Address Generation (1 access per state on negedge clk)
    // =========================================================================
    // Stack nibbles for BBL in X1(5)->0, X2(6)->1, X3(7)->2: state[1:0] - 2'd1
    wire [1:0] bbl_nib = state[1:0] - 2'd1;

    reg        sram_ce_en;
    reg        sram_wr;
    reg  [4:0] sram_addr;

    always @(*) begin
        sram_ce_en = 1'b0;
        sram_wr    = 1'b0;
        sram_addr  = {1'b0, opa};

        case (state)
            ST_A1, ST_A2, ST_A3: begin
                // JMS Cycle 2 pushes return address (pc_inc) to stack at SP
                if (cyc2 && is_jms) begin
                    sram_ce_en = 1'b1;
                    sram_wr    = 1'b1;
                    sram_addr  = {1'b1, state[1:0], sp};
                end
            end

            ST_M2: begin
                // FIM / FIN Cycle 2 writes high nibble (tmp = d2) to R[2P]
                if (cyc2 && (is_fim || is_fin)) begin
                    sram_ce_en = 1'b1;
                    sram_wr    = 1'b1;
                    sram_addr  = {1'b0, opa[3:1], 1'b0};
                end
            end

            ST_X1: begin
                if (cyc2) begin
                    // FIM / FIN Cycle 2 writes low nibble (tmp = d1) to R[2P+1]
                    if (is_fim || is_fin) begin
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b1;
                        sram_addr  = {1'b0, opa[3:1], 1'b1};
                    end
                end else begin
                    if (is_bbl) begin
                        // Read return PC[3:0] from Stack
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = {1'b1, bbl_nib, sp};
                    end else if (is_fin) begin
                        // FIN Cycle 1 X1: Read R[0]
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = 5'h00;
                    end else if (is_src || is_jin) begin
                        // SRC / JIN X1: Read R[2P]
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = {1'b0, opa[3:1], 1'b0};
                    end else if (is_inc || is_isz || is_add || is_sub || is_ld || is_xch) begin
                        // Single register read R[r]
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = {1'b0, opa};
                    end
                end
            end

            ST_X2: begin
                if (!cyc2) begin
                    if (is_bbl) begin
                        // Read return PC[7:4] from Stack
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = {1'b1, bbl_nib, sp};
                    end else if (is_fin) begin
                        // FIN Cycle 1 X2: Read R[1]
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = 5'h01;
                    end else if (is_src || is_jin) begin
                        // SRC / JIN X2: Read R[2P+1]
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b0;
                        sram_addr  = {1'b0, opa[3:1], 1'b1};
                    end else if (is_inc || is_isz || is_xch) begin
                        // Write back updated R[r] from tmp
                        sram_ce_en = 1'b1;
                        sram_wr    = 1'b1;
                        sram_addr  = {1'b0, opa};
                    end
                end
            end

            ST_X3: begin
                if (!cyc2 && is_bbl) begin
                    // Read return PC[11:8] from Stack
                    sram_ce_en = 1'b1;
                    sram_wr    = 1'b0;
                    sram_addr  = {1'b1, bbl_nib, sp};
                end
            end

            default: ;
        endcase
    end

    // Write data is pc_inc (alu_sum) during A1..A3 (state[2]==0), and tmp during M2..X2 (state[2]==1)
    wire [3:0] sram_din = state[2] ? tmp : alu_sum;
    wire       sram_ce  = (~clk) & rst_n & sram_ce_en;

    SRAM128 u_sram (
        .CE  (sram_ce),
        .WR  (sram_wr),
        .A0  (sram_addr[0]),
        .A1  (sram_addr[1]),
        .A2  (sram_addr[2]),
        .A3  (sram_addr[3]),
        .A4  (sram_addr[4]),
        .DIN (sram_din),
        .DO  (sram_do)
    );

    // =========================================================================
    // 5. Sequential State & Register Updates (Single-phase posedge clk)
    // =========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= ST_X3;
            cyc2     <= 1'b0;
            opr      <= 4'h0;
            opa      <= 4'h0;
            acc      <= 4'h0;
            cy       <= 1'b0;
            pc       <= 12'h000;
            sp       <= 2'd0;
            dcl      <= 3'd0;
            tmp      <= 4'h0;
            pc_cy    <= 1'b0;
            take_lat <= 1'b0;
        end else begin
            state <= state + 3'd1;

            case (state)
                ST_A1: begin
                    if (!(cyc2 && is_fin)) begin
                        pc[3:0] <= alu_sum;
                        pc_cy   <= alu_cout;
                    end
                end

                ST_A2: begin
                    if (!(cyc2 && is_fin)) begin
                        pc[7:4] <= alu_sum;
                        pc_cy   <= alu_cout;
                    end
                end

                ST_A3: begin
                    if (!(cyc2 && is_fin)) begin
                        pc[11:8] <= alu_sum;
                    end
                end

                ST_M1: begin
                    if (!cyc2) begin
                        opr <= d_in;
                    end else begin
                        if (is_fim || is_fin) begin
                            tmp <= d_in;
                        end
                        if (cyc2_jump_take) begin
                            pc[7:4] <= d_in;
                        end
                    end
                end

                ST_M2: begin
                    if (!cyc2) begin
                        opa <= d_in;
                        if (opr == 4'hC) begin // BBL: pre-decrement SP and load d4 into ACC
                            sp  <= sp - 2'd1;
                            acc <= d_in;
                        end else if (opr == 4'hD) begin // LDM: load d4 into ACC
                            acc <= d_in;
                        end
                    end else begin
                        if (is_fim || is_fin) begin
                            tmp <= d_in;
                        end
                        if (cyc2_jump_take) begin
                            pc[3:0] <= d_in;
                            if (is_jun || is_jms) begin
                                pc[11:8] <= opa;
                            end
                            if (is_jms) begin
                                sp <= sp + 2'd1;
                            end
                        end
                    end
                end

                ST_X1: begin
                    if (!cyc2) begin
                        if (is_jcn) begin
                            take_lat <= jcn_take;
                        end else if (is_fin || is_src) begin
                            tmp <= sram_do; // R[0] for FIN, R[2P] for SRC
                        end else if (is_jin || is_bbl) begin
                            if (is_jin) begin
                                pc[7:4] <= sram_do; // R[2P] -> PC[7:4]
                            end else begin
                                pc[3:0] <= sram_do; // Stack NIB0 -> PC[3:0]
                            end
                        end else if (is_inc || is_isz) begin
                            tmp      <= alu_sum;
                            take_lat <= ~alu_cout; // 1 if sram_do + 1 != 0
                        end else if (is_add || is_sub) begin
                            acc <= alu_sum;
                            cy  <= alu_cout;
                        end else if (is_ld) begin
                            acc <= sram_do;
                        end else if (is_xch) begin
                            tmp <= acc;
                            acc <= sram_do;
                        end else if (is_acc) begin
                            case (opa)
                                4'h0: begin acc <= 4'h0; cy <= 1'b0; end           // CLB
                                4'h1: begin cy  <= 1'b0; end                       // CLC
                                4'h2: begin acc <= alu_sum; cy <= alu_cout; end    // IAC
                                4'h3: begin cy  <= ~cy; end                        // CMC
                                4'h4: begin acc <= ~acc; end                       // CMA
                                4'h5: begin {cy, acc} <= {acc, cy}; end            // RAL
                                4'h6: begin {acc, cy} <= {cy, acc}; end            // RAR
                                4'h7: begin acc <= {3'b000, cy}; cy <= 1'b0; end   // TCC
                                4'h8: begin acc <= alu_sum; cy <= alu_cout; end    // DAC
                                4'h9: begin acc <= cy ? 4'd10 : 4'd9; cy <= 1'b0; end // TCS
                                4'hA: begin cy  <= 1'b1; end                       // STC
                                4'hB: begin if (daa_adj) begin acc <= alu_sum; cy <= 1'b1; end end // DAA
                                4'hC: begin acc <= kbp_val; end                    // KBP
                                4'hD: begin dcl <= acc[2:0]; end                   // DCL
                                default: ;
                            endcase
                        end
                    end
                end

                ST_X2: begin
                    if (!cyc2) begin
                        if (is_src) begin
                            tmp <= sram_do; // R[2P+1] for SRC X3 output
                        end else if (is_jin) begin
                            pc[3:0] <= sram_do; // R[2P+1] -> PC[3:0]
                        end else if (is_bbl) begin
                            pc[7:4] <= sram_do; // Stack NIB1 -> PC[7:4]
                        end else if (is_ior && opa[3]) begin
                            // I/O & RAM read instructions (SBM, RDM, RDR, ADM, RD0..RD3)
                            if (opa == 4'h8 || opa == 4'hB) begin // SBM / ADM
                                acc <= alu_sum;
                                cy  <= alu_cout;
                            end else begin                        // RDM / RDR / RD0..RD3
                                acc <= d_in;
                            end
                        end
                    end
                end

                ST_X3: begin
                    if (!cyc2) begin
                        if (is_bbl) begin
                            pc[11:8] <= sram_do; // Stack NIB2 -> PC[11:8]
                        end
                        cyc2 <= is_2cyc_op;
                    end else begin
                        cyc2 <= 1'b0;
                    end
                end
            endcase
        end
    end

    // =========================================================================
    // 6. External Bus (D[3:0], d_oe, d_hiz, SYNC, CM_ROM, CM_RAM[3:0] - Positive Logic)
    // =========================================================================
    assign sync = (state == ST_X3);

    // DCL bank decoding: 000 -> bank 0, otherwise {dcl[2:0], 1'b0}
    wire [3:0] cm_ram_sel = (dcl == 3'b000) ? 4'b0001 : {dcl, 1'b0};

    // CM_ROM asserted in A3, in M2 for I/O instructions, and in X2 for SRC
    wire cm_rom_en = (state == ST_A3) ||
                     ((state == ST_M2) && (!cyc2) && (opr == 4'hE)) ||
                     ((state == ST_X2) && (!cyc2) && is_src);
    assign cm_rom = cm_rom_en;

    // CM_RAM[3:0] asserted in M2 for RAM/IO instructions, and in X2 for SRC
    wire cm_ram_en = ((state == ST_M2) && (!cyc2) && (opr == 4'hE)) ||
                     ((state == ST_X2) && (!cyc2) && is_src);
    assign cm_ram = cm_ram_en ? cm_ram_sel : 4'b0000;

    // Data bus output & Hi-Z control (d_hiz = 0 / d_oe = 1 when driving D[3:0])
    wire d_drive = (state == ST_A1) || (state == ST_A2) || (state == ST_A3) ||
                   ((state == ST_X2) && (!cyc2) && (is_src || (is_ior && (~opa[3])))) ||
                   ((state == ST_X3) && (!cyc2) && is_src);
    assign d_oe  = d_drive;
    assign d_hiz = ~d_drive;

    always @(*) begin
        case (state)
            ST_A1:   d_out = (cyc2 && is_fin) ? sram_do : pc[3:0];
            ST_A2:   d_out = (cyc2 && is_fin) ? tmp     : pc[7:4];
            ST_A3:   d_out = pc[11:8];
            ST_X2:   d_out = is_src ? tmp : acc;
            ST_X3:   d_out = tmp;
            default: d_out = 4'h0;
        endcase
    end

endmodule
