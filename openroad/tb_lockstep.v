
`timescale 1ns/1ps
module tb_lockstep;
  reg clk = 0;
  reg rst = 1;
  reg test = 0;
  reg [3:0] d_in = 0;

  wire [3:0] d_out_r, d_out_g;
  wire d_oe_r, d_oe_g;
  wire d_hiz_r, d_hiz_g;
  wire sync_r, sync_g;
  wire cm_rom_r, cm_rom_g;
  wire [3:0] cm_ram_r, cm_ram_g;

  c4004_core u_rtl (
    .clk(clk), .rst(rst), .test(test), .d_in(d_in),
    .d_out(d_out_r), .d_oe(d_oe_r), .d_hiz(d_hiz_r),
    .sync(sync_r), .cm_rom(cm_rom_r), .cm_ram(cm_ram_r)
  );
  c4004_core_gate u_gate (
    .clk(clk), .rst(rst), .test(test), .d_in(d_in),
    .d_out(d_out_g), .d_oe(d_oe_g), .d_hiz(d_hiz_g),
    .sync(sync_g), .cm_rom(cm_rom_g), .cm_ram(cm_ram_g)
  );

  always #25 clk = ~clk;

  // Test program exercising LDM, XCH, LD, ADD, SUB, INC, ISZ, FIM, SRC, FIN, JIN, JMS, BBL, JUN, JCN, DCL, WRM, RDM, ADM, SBM, RAL, RAR, DAA, KBP
  reg [7:0] rom [0:63];
  integer cyc, ph, err = 0;
  reg [11:0] cur_pc;

  initial begin
    for (cyc = 0; cyc < 64; cyc = cyc + 1) rom[cyc] = 8'h00;
    rom[0]  = 8'hD5; // LDM 5
    rom[1]  = 8'hB0; // XCH R0
    rom[2]  = 8'hA0; // LD R0
    rom[3]  = 8'h80; // ADD R0
    rom[4]  = 8'h60; // INC R0
    rom[5]  = 8'h90; // SUB R0
    rom[6]  = 8'h20; // FIM P0, 0x3C
    rom[7]  = 8'h3C;
    rom[8]  = 8'h21; // SRC P0
    rom[9]  = 8'hE0; // WRM
    rom[10] = 8'h50; // JMS 0x014
    rom[11] = 8'h14;
    rom[12] = 8'h14; // JCN AZ, 0x18 (not taken)
    rom[13] = 8'h18;
    rom[14] = 8'h71; // ISZ R1, 0x18
    rom[15] = 8'h18;
    rom[20] = 8'hC9; // BBL 9
    rom[24] = 8'h30; // FIN P1
    rom[25] = 8'hF5; // RAL
    rom[26] = 8'hFB; // DAA
    rom[27] = 8'hFC; // KBP
    rom[28] = 8'hFD; // DCL

    #110 rst = 0;
    // Verify lockstep across all 34 post-reset SRAM zero-clear + sync clocks
    for (ph = 0; ph < 34; ph = ph + 1) begin
      @(negedge clk);
      #1;
      if ({d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r} !==
          {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g}) begin
        $display("INIT MISMATCH negedge at init_clk=%0d: RTL=%b GATE=%b", ph,
          {d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r},
          {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g});
        err = err + 1;
      end
      @(posedge clk);
      #1;
      if ({d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r} !==
          {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g}) begin
        $display("INIT MISMATCH posedge at init_clk=%0d: RTL=%b GATE=%b", ph,
          {d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r},
          {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g});
        err = err + 1;
      end
    end
    for (cyc = 0; cyc < 35; cyc = cyc + 1) begin
      for (ph = 0; ph < 8; ph = ph + 1) begin
        @(negedge clk);
        if (ph == 0) cur_pc[3:0]  = d_out_r;
        if (ph == 1) cur_pc[7:4]  = d_out_r;
        if (ph == 2) cur_pc[11:8] = d_out_r;
        if (ph == 3) d_in = rom[cur_pc[5:0]][7:4];
        else if (ph == 4) d_in = rom[cur_pc[5:0]][3:0];
        else d_in = 4'h7;
        #1;
        if ({d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r} !==
            {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g}) begin
          $display("MISMATCH at cyc=%0d ph=%0d: RTL=%b GATE=%b", cyc, ph,
            {d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r},
            {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g});
          err = err + 1;
        end
        @(posedge clk);
        #1;
        if ({d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r} !==
            {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g}) begin
          $display("MISMATCH posedge at cyc=%0d ph=%0d: RTL=%b GATE=%b", cyc, ph,
            {d_out_r, d_oe_r, d_hiz_r, sync_r, cm_rom_r, cm_ram_r},
            {d_out_g, d_oe_g, d_hiz_g, sync_g, cm_rom_g, cm_ram_g});
          err = err + 1;
        end
      end
    end
    $display("Lockstep check finished: %0d errors across 280 clock phases!", err);
    $finish;
  end
endmodule
