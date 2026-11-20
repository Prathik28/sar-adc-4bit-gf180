// Cross-check: RTL controller vs the gate-level mirror of the transistor-level logic,
// driven by the same random comparator stream. Also checks recovery from the unused states.
`timescale 1ns/1ps
module tb_equiv;
    reg clk = 0, rst = 1, comp = 0;
    wire        sample_r, eoc_r, sample_g, eoc_g;
    wire [3:0]  dac_r, dout_r, dac_g, r_g;
    integer cyc = 0, errors = 0, i, conv = 0;
    reg cmp_en = 1;                 // off during the deliberate unused-state injections

    sar_ctrl  rtl (.clk(clk), .rst(rst), .ce(1'b1), .comp(comp), .sample(sample_r),
                   .dac(dac_r), .eoc(eoc_r), .dout(dout_r));
    sar_gates gts (.clk(clk), .rst(rst), .comp(comp), .sample(sample_g), .eoc(eoc_g),
                   .dac(dac_g), .r_out(r_g));

    always #10 clk = ~clk;

    // compare just before every rising edge (outputs are stable), skipping the first conversion
    // because the transistor-level SAR register is not reset (it clears itself in S0)
    always @(negedge clk) if (!rst && cyc > 8 && cmp_en) begin
        if (sample_r !== sample_g || eoc_r !== eoc_g || dac_r !== dac_g) begin
            errors = errors + 1;
            $display("MISMATCH cycle %0d: sample %b/%b eoc %b/%b dac %b/%b",
                     cyc, sample_r, sample_g, eoc_r, eoc_g, dac_r, dac_g);
        end
        if (sample_r && dout_r !== r_g) begin       // result of the previous conversion
            errors = errors + 1;
            $display("MISMATCH cycle %0d: dout %b vs gate R %b", cyc, dout_r, r_g);
        end
        if (eoc_r) conv = conv + 1;
    end
    always @(posedge clk) cyc = cyc + 1;

    task check_recovery(input [2:0] code);
        integer n; reg seen_s0_r, seen_eoc_g, seen_s0_g;
        begin
            @(negedge clk);
            rtl.state = code; { gts.q2, gts.q1, gts.q0 } = code;
            seen_s0_r = 0; seen_s0_g = 0; seen_eoc_g = 0;
            for (n = 0; n < 4; n = n + 1) begin
                @(negedge clk);
                if (sample_r) seen_s0_r = 1;
                if (sample_g) seen_s0_g = 1;
                if (eoc_g) seen_eoc_g = 1;
            end
            $display("unused state %b: RTL back in S0 after <=4 cycles: %b | gate-level: %b (via EOC: %b)",
                     code, seen_s0_r, seen_s0_g, seen_eoc_g);
            if (!(seen_s0_r && seen_s0_g)) errors = errors + 1;
        end
    endtask

    initial begin
        repeat (2) @(posedge clk); rst = 0;
        for (i = 0; i < 20000; i = i + 1) begin
            @(posedge clk); #1 comp = $random;       // random comparator decisions
        end
        $display("random phase: %0d cycles, %0d conversions compared", cyc, conv);
        // the two implementations recover differently from unused codes (110 -> S0 in the RTL,
        // 110 -> S5 -> S0 in the gates), so lock-step comparison is off from here on
        cmp_en = 0;
        check_recovery(3'b110);
        check_recovery(3'b111);
        $display("%0d errors", errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
