// Basys 3 prototype: SAR logic in the FPGA, R-2R DAC and comparator on a breadboard via Pmod JA
`timescale 1ns/1ps
module fpga_top (
    input  wire       clk,        // 100 MHz board clock (W5)
    input  wire       btnC,       // reset
    input  wire       comp_in,    // comparator output from the breadboard (JA7)
    output wire [3:0] dac_out,    // to the R-2R ladder (JA1..JA4)
    output wire       sample_out, // to the sample-and-hold control (JA8)
    output wire [3:0] led,        // converted code
    output wire       led_eoc     // end of conversion (LD15)
);
    // 100 MHz / 1000 = one SAR step every 10 us, slow enough for a discrete comparator and R-2R ladder
    reg [9:0] div = 0;
    wire ce = (div == 10'd999);
    always @(posedge clk) div <= ce ? 10'd0 : div + 10'd1;

    // two-flip-flop synchroniser for the asynchronous comparator signal
    reg c1 = 0, c2 = 0;
    always @(posedge clk) begin c1 <= comp_in; c2 <= c1; end

    wire [3:0] dout;
    sar_ctrl u_sar (.clk(clk), .rst(btnC), .ce(ce), .comp(c2),
                    .sample(sample_out), .dac(dac_out), .eoc(led_eoc), .dout(dout));
    assign led = dout;
endmodule
