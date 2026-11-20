// N-bit SAR ADC control logic: generalisation of sar_ctrl (N = 4 reproduces it exactly).
// States: S0 = sample, S1..SN = test bit N-1 .. 0 (MSB first), S(N+1) = end of conversion.
// One conversion takes N + 2 clock-enable pulses.
`timescale 1ns/1ps
module sar_ctrl_n #(
    parameter N = 4
) (
    input  wire         clk,
    input  wire         rst,      // synchronous, active high
    input  wire         ce,       // clock enable: one SAR step per ce pulse
    input  wire         comp,     // 1 when Vin >= Vdac
    output wire         sample,   // high in S0: S/H tracks the input
    output wire [N-1:0] dac,      // code applied to the DAC
    output wire         eoc,      // high in S(N+1): dout is valid
    output reg  [N-1:0] dout      // converted result, updated at the end of S(N+1)
);
    localparam SW = $clog2(N + 2);
    localparam [SW-1:0] LAST = N + 1;

    reg [SW-1:0] state;
    reg [N-1:0]  r;               // SAR register

    wire testing = (state != 0) && (state != LAST) && (state <= N);
    // one-hot SET line of the bit under test: state k tests bit N-k
    wire [N-1:0] set = testing ? ({{(N-1){1'b0}}, 1'b1} << (N - state)) : {N{1'b0}};

    assign sample = (state == 0);
    assign eoc    = (state == LAST);
    assign dac    = r | set;

    // next state: count up to LAST, then return to S0; any unused code also returns to S0
    wire [SW-1:0] next = (state >= LAST) ? {SW{1'b0}} : state + 1'b1;

    always @(posedge clk) begin
        if (rst) begin
            state <= 0;
            r     <= {N{1'b0}};
            dout  <= {N{1'b0}};
        end else if (ce) begin
            state <= next;
            if (sample) r <= {N{1'b0}};
            else        r <= (set & {N{comp}}) | (~set & r);
            if (eoc)    dout <= r;
        end
    end
endmodule
