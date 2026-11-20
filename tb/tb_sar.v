// Self-checking testbench with an ideal analog model of S/H, DAC and comparator
`timescale 1ns/1ps
module tb_sar;
    reg clk = 0, rst = 1;
    real vin, vhold, vdac;
    real VREF = 2.0;
    wire sample, eoc; wire [3:0] dac, dout;
    reg comp;
    integer k, errors = 0, expected;

    sar_ctrl dut(.clk(clk), .rst(rst), .ce(1'b1), .comp(comp), .sample(sample), .dac(dac), .eoc(eoc), .dout(dout));

    always #10 clk = ~clk;                                   // 50 MHz
    always @(*) vdac = VREF * dac / 16.0;                    // ideal 4-bit DAC
    always @(negedge clk) begin                              // S/H holds at the end of S0
        if (sample) vhold = vin;
        comp = (vhold >= vdac);                              // comparator decides mid-cycle
    end

    initial begin
        $dumpfile("tb_sar.vcd"); $dumpvars(0, tb_sar);
        vin = 0.0; vhold = 0.0; comp = 0;
        repeat (2) @(posedge clk); rst = 0;
        for (k = 0; k < 64; k = k + 1) begin
            vin = (k + 0.5) * VREF / 64.0;                   // 64-step ramp
            @(posedge eoc); @(posedge clk); #1;              // dout updates at end of S5
            expected = $floor(vin / (VREF / 16.0));
            if (dout !== expected) begin
                errors = errors + 1;
                $display("MISMATCH vin=%0.4f dout=%0d expected=%0d", vin, dout, expected);
            end
            if (k % 8 == 0) $display("vin = %0.4f V -> code %b (%0d)", vin, dout, dout);
        end
        vin = 1.30; @(posedge eoc); @(posedge clk); #1;
        $display("vin = 1.3000 V -> code %b (%0d)", dout, dout);
        $display("%0d conversions checked, %0d errors", 65, errors);
        $finish;
    end
endmodule
