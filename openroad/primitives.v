
`timescale 1ns/1ps
module INV_X1(input A, output Y); assign Y = ~A; endmodule
module INV_X2(input A, output Y); assign Y = ~A; endmodule
module BUF_X1(input A, output Y); assign Y = A; endmodule
module BUF_X2(input A, output Y); assign Y = A; endmodule
module BUFTH(input A, output Y); assign Y = A; endmodule
module NAND2(input A, B, output Y); assign Y = ~(A & B); endmodule
module NAND3(input A, B, C, output Y); assign Y = ~(A & B & C); endmodule
module NAND4(input A, B, C, D, output Y); assign Y = ~(A & B & C & D); endmodule
module NOR2(input A, B, output Y); assign Y = ~(A | B); endmodule
module NOR3(input A, B, C, output Y); assign Y = ~(A | B | C); endmodule
module NOR4(input A, B, C, D, output Y); assign Y = ~(A | B | C | D); endmodule
module AND2_X1(input A, B, output Y); assign Y = A & B; endmodule
module AND3_X1(input A, B, C, output Y); assign Y = A & B & C; endmodule
module AND4_X1(input A, B, C, D, output Y); assign Y = A & B & C & D; endmodule
module OR2(input A, B, output Y); assign Y = A | B; endmodule
module OR3(input A, B, C, output Y); assign Y = A | B | C; endmodule
module OR4(input A, B, C, D, output Y); assign Y = A | B | C | D; endmodule
module XOR2(input A, B, output Y); assign Y = A ^ B; endmodule
module XNOR2(input A, B, output Y); assign Y = ~(A ^ B); endmodule
module AOI21(input A1, A2, B, output Y); assign Y = ~((A1 & A2) | B); endmodule
module AOI22(input A1, A2, B1, B2, output Y); assign Y = ~((A1 & A2) | (B1 & B2)); endmodule
module OAI21(input A1, A2, B, output Y); assign Y = ~((A1 | A2) & B); endmodule
module OAI22(input A1, A2, B1, B2, output Y); assign Y = ~((A1 | A2) & (B1 | B2)); endmodule
module MUX2(input A, B, S, output Y); assign Y = S ? B : A; endmodule
module DFFRB(input CK, D, RSTB, output reg Q, output QB);
  assign QB = ~Q;
  always @(posedge CK or negedge RSTB)
    if (!RSTB) Q <= 1'b0;
    else Q <= D;
endmodule
module MUXDFFRB(input CK, A, B, S, RSTB, output reg Q, output QB);
  assign QB = ~Q;
  always @(posedge CK or negedge RSTB)
    if (!RSTB) Q <= 1'b0;
    else Q <= (S ? B : A);
endmodule
module SRAM128(input A0, A1, A2, A3, A4, CE, WR, input [3:0] DIN, output reg [3:0] DO);
  reg [3:0] mem [0:31];
  integer i;
  initial begin for (i=0; i<32; i=i+1) mem[i] = 4'h0; DO = 4'h0; end
  wire [4:0] addr = {A4, A3, A2, A1, A0};
  always @(*) begin
    if (CE) begin
      if (WR) mem[addr] = DIN;
      else DO = mem[addr];
    end
  end
endmodule
