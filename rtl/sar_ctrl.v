// 4-bit SAR ADC control logic: corrected FSM + SAR register
// Same state assignment as the transistor-level design (S0..S5 = 000..101)
`timescale 1ns/1ps
module sar_ctrl (
    input  wire       clk,
    input  wire       rst,      // synchronous, active high
    input  wire       ce,       // clock enable: one SAR step per ce pulse
    input  wire       comp,     // 1 when Vin >= Vdac
    output wire       sample,   // high in S0: S/H tracks the input
    output wire [3:0] dac,      // code applied to the DAC
    output wire       eoc,      // high in S5: dout is valid
    output reg  [3:0] dout      // converted result, updated at the end of S5
);
    localparam S0 = 3'b000, S1 = 3'b001, S2 = 3'b010,
               S3 = 3'b011, S4 = 3'b100, S5 = 3'b101;

    reg [2:0] state, next;
    reg [3:0] r;                // SAR register R3..R0

    // next-state logic (corrected: S5 returns to S0, unused codes recover)
    always @(*) begin
        case (state)
            S0: next = S1;
            S1: next = S2;
            S2: next = S3;
            S3: next = S4;
            S4: next = S5;
            default: next = S0;   // S5 and the unused codes 110, 111
        endcase
    end

    // output decoding (Moore): one-hot SET lines
    wire [3:0] set = { state == S1, state == S2, state == S3, state == S4 };
    assign sample = (state == S0);
    assign eoc    = (state == S5);
    assign dac    = r | set;      // bit under test forced to 1

    // state register and SAR register
    always @(posedge clk) begin
        if (rst) begin
            state <= S0;
            r     <= 4'b0000;
            dout  <= 4'b0000;
        end else if (ce) begin
            state <= next;
            if (sample)   r <= 4'b0000;                         // clear for new conversion
            else          r <= (set & {4{comp}}) | (~set & r);  // keep or clear the tested bit
            if (eoc)      dout <= r;                            // output register
        end
    end
endmodule
