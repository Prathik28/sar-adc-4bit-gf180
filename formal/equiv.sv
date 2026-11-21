// RTL controller vs the gate-level mirror of the transistor-level logic: identical outputs for any
// comparator sequence after power-on reset (rst held low; the stale-register and unused-state
// differences only appear after a reset or an injected illegal state and are documented in the README).
module equiv (input wire clk, input wire comp);
    wire sample_r, eoc_r, sample_g, eoc_g;
    wire [3:0] dac_r, dout_r, dac_g, r_g;
    sar_ctrl  rtl (.clk(clk), .rst(1'b0), .ce(1'b1), .comp(comp), .sample(sample_r), .dac(dac_r), .eoc(eoc_r), .dout(dout_r));
    sar_gates gts (.clk(clk), .rst(1'b0), .comp(comp), .sample(sample_g), .eoc(eoc_g), .dac(dac_g), .r_out(r_g));
    always @(*) begin
        assert (sample_r == sample_g);
        assert (eoc_r == eoc_g);
        assert (dac_r == dac_g);
        if (sample_r) assert (dout_r == r_g);
    end
endmodule
