// Self-checking testbench for sar_ctrl_n with an ideal S/H, DAC and comparator.
// Run: iverilog -g2012 -P tb_sar_n.N=8 -o t tb_sar_n.v ../rtl/sar_ctrl_n.v && vvp t
`timescale 1ns/1ps
module tb_sar_n;
    parameter N = 4;
    parameter STEPS = 4 << N;            // ramp steps (4 per code)
    real VREF = 2.0;
    reg clk = 0, rst = 1;
    real vin, vhold, vdac, lsb;
    wire sample, eoc; wire [N-1:0] dac, dout;
    reg comp;
    integer k, errors = 0, expected, seen;
    reg [(1<<N)-1:0] hit;

    sar_ctrl_n #(.N(N)) dut (.clk(clk), .rst(rst), .ce(1'b1), .comp(comp),
                             .sample(sample), .dac(dac), .eoc(eoc), .dout(dout));
    always #10 clk = ~clk;
    always @(*) vdac = VREF * dac / (1.0 * (1 << N));
    always @(negedge clk) begin
        if (sample) vhold = vin;
        comp = (vhold >= vdac);
    end

    initial begin
        lsb = VREF / (1 << N); hit = 0; vin = 0; vhold = 0; comp = 0;
        repeat (2) @(posedge clk); rst = 0;
        for (k = 0; k < STEPS; k = k + 1) begin
            vin = (k + 0.5) * VREF / STEPS;
            @(posedge eoc); @(posedge clk); #1;
            expected = $floor(vin / lsb);
            if (dout !== expected) begin
                errors = errors + 1;
                $display("MISMATCH N=%0d vin=%0.5f dout=%0d expected=%0d", N, vin, dout, expected);
            end
            hit[dout] = 1'b1;
        end
        seen = 0;
        for (k = 0; k < (1 << N); k = k + 1) seen = seen + hit[k];
        $display("N=%0d: %0d conversions, %0d errors, %0d of %0d codes seen, %0d cycles per conversion",
                 N, STEPS, errors, seen, 1 << N, N + 2);
        if (errors == 0 && seen == (1 << N)) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
