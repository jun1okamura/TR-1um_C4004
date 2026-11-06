// Top-level Intel 4004 (C4004) wrapper modeling the 14 signal pads of OSS_FRAME_GIO
// (plus VDD and VSS = 16 pins total)

`timescale 1ns/1ps

module c4004_top (
    input  wire       clk,
    input  wire       rst,
    input  wire       test,
    inout  wire [3:0] D,
    output wire       d_oe,
    output wire       sync,
    output wire       cm_rom,
    output wire [3:0] cm_ram
);
    wire [3:0] d_in  = D;
    wire [3:0] d_out;
    wire       d_hiz;

    // OSS_ESD_5V_DIO behavior: HIZ = 0 drives PAD = OUT, HIZ = 1 is High-Z
    assign D = d_hiz ? 4'bzzzz : d_out;

    c4004_core u_core (
        .clk    (clk),
        .rst    (rst),
        .test   (test),
        .d_in   (d_in),
        .d_out  (d_out),
        .d_oe   (d_oe),
        .d_hiz  (d_hiz),
        .sync   (sync),
        .cm_rom (cm_rom),
        .cm_ram (cm_ram)
    );
endmodule
