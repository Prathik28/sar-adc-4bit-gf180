// Gate-level mirror of the transistor-level digital core (spice/cells.sp and spice/adc_130b.sp):
// corrected next-state logic NSL_FIXED, output decoder OUTL, 3-bit state register and the SAR
// register D = S0' * (SET ? COMP : R). Used to cross-check the RTL (sar_ctrl.v) against the
// equations that were actually drawn at transistor level.
`timescale 1ns/1ps
module sar_gates (
    input  wire       clk,
    input  wire       rst,       // synchronous, active high (folded into the D inputs like NSL_FIXED)
    input  wire       comp,
    output wire       sample,    // S0
    output wire       eoc,       // S5
    output wire [3:0] dac,       // R | SET
    output wire [3:0] r_out
);
    reg  q0, q1, q2;             // FSMREG
    reg  [3:0] r;                // SAR register

    wire rstn = ~rst;
    // NSL_FIXED
    wire t2 = ~q1 & q0, t3 = q1 & ~q0, x1 = t2 | t3, x1g = x1 & ~q2;
    wire t5 = q1 & q0,  t6 = q2 & ~q0, x2 = t6 | t5;
    wire d0 = ~q0 & rstn, d1 = x1g & rstn, d2 = x2 & rstn;
    // OUTL
    wire [3:0] setb = { ~q2 & ~q1 &  q0,      // S1 -> SET_B3
                        ~q2 & ~q0 &  q1,      // S2 -> SET_B2
                        ~q2 &  q0 &  q1,      // S3 -> SET_B1
                         q2 & ~q1 & ~q0 };    // S4 -> SET_B0
    assign eoc    = q2 & ~q1 & q0;            // S5
    assign sample = ~q2 & ~q1 & ~q0;          // S0
    // SAR register
    wire [3:0] dr = ({4{~sample}}) & ((setb & {4{comp}}) | (~setb & r));
    assign dac   = r | setb;
    assign r_out = r;

    always @(posedge clk) begin
        q0 <= d0; q1 <= d1; q2 <= d2;
        r  <= dr;
    end

`ifdef FORMAL
    initial begin q0 = 1'b0; q1 = 1'b0; q2 = 1'b0; r = 4'b0; end
`endif
endmodule
