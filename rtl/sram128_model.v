// Behavioral Verilog model of module/SRAM128 (32 word x 4 bit 6T SRAM macro)
// Matches pin names and behavior of module/SRAM128/SRAM128.{lef,lib,spice}:
//   - CE = 0: Bitline precharge
//   - posedge CE with WR = 0: Read addressed word into internal SA output latch DO[3:0]
//   - posedge CE with WR = 1: Write DIN[3:0] into addressed word (DO[3:0] holds previous value)

`timescale 1ns/1ps

module SRAM128 (
    input  wire       CE,
    input  wire       WR,
    input  wire       A0,
    input  wire       A1,
    input  wire       A2,
    input  wire       A3,
    input  wire       A4,
    input  wire [3:0] DIN,
    output reg  [3:0] DO
);
    reg [3:0] mem [0:31];
    wire [4:0] addr = {A4, A3, A2, A1, A0};

    integer i;
    initial begin
        DO = 4'h0;
        for (i = 0; i < 32; i = i + 1) begin
            mem[i] = 4'h0;
        end
    end

    always @(posedge CE) begin
        if (WR) begin
            mem[addr] <= DIN;
        end else begin
            DO <= mem[addr];
        end
    end
endmodule
