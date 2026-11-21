// End-to-end proof: controller + an ideal comparator and DAC (comp = Vin >= Vdac) must return Vin.
// vin is any constant 4-bit value; rst and ce are completely free.
module adc_model (input wire clk, input wire rst, input wire ce);
    (* anyconst *) wire [3:0] vin;           // any 4-bit input code, constant for the whole run
    wire sample, eoc;
    wire [3:0] dac, dout;
    wire comp = (vin >= dac);
    sar_ctrl dut (.clk(clk), .rst(rst), .ce(ce), .comp(comp), .sample(sample), .dac(dac), .eoc(eoc), .dout(dout));

    reg seen = 1'b0;
    always @(posedge clk) begin
        if (rst) seen <= 1'b0;
        else if (ce && eoc) seen <= 1'b1;     // a full conversion has been loaded into dout
    end
    always @(*) begin
        if (seen)   assert (dout == vin);     // ideal SAR gives back the input code
        // invariants for the induction proof: binary-search prefix of vin is decided
        if (dut.state == 3'd2) assert (dut.r[3] == vin[3]);
        if (dut.state == 3'd3) assert (dut.r[3:2] == vin[3:2]);
        if (dut.state == 3'd4) assert (dut.r[3:1] == vin[3:1]);
        if (dut.state == 3'd5) assert (dut.r == vin);
    end
endmodule
