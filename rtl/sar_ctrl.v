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

`ifdef FORMAL
    // ---- formal properties (ignored by synthesis and simulation) ----
    // power-on state is the reset state; inputs rst, ce and comp stay completely free
    initial begin state = S0; r = 4'b0; dout = 4'b0; end
    reg f_past = 1'b0;
    always @(posedge clk) f_past <= 1'b1;
    reg [3:0] f_c;                       // comparator decision captured in S1..S4
    always @(posedge clk) if (!rst && ce) begin
        if (state == S1) f_c[3] <= comp;
        if (state == S2) f_c[2] <= comp;
        if (state == S3) f_c[1] <= comp;
        if (state == S4) f_c[0] <= comp;
    end
    always @(*) begin
        assert (state <= S5);                          // 110 and 111 are never reached
        assert (!(sample && eoc));
        assert (set == 4'b0000 || set == 4'b1000 || set == 4'b0100 || set == 4'b0010 || set == 4'b0001);
        // invariants that make the proof inductive: bits decided so far are in r, the rest are still 0
        if (state == S1) assert (r == 4'b0000);
        if (state >= S2) assert (r[3] == f_c[3]);
        if (state == S2) assert (r[2:0] == 3'b000);
        if (state >= S3) assert (r[2] == f_c[2]);
        if (state == S3) assert (r[1:0] == 2'b00);
        if (state >= S4) assert (r[1] == f_c[1]);
        if (state == S4) assert (r[0] == 1'b0);
        if (state == S5) assert (r[0] == f_c[0]);
        if (eoc) assert (r == f_c);                    // register holds exactly what the comparator decided
    end
    always @(posedge clk) if (f_past) begin
        if ($past(rst))                assert (state == S0 && r == 4'b0 && dout == 4'b0);
        if (!$past(rst) && !$past(ce)) assert (state == $past(state) && r == $past(r) && dout == $past(dout));
        if (!$past(rst) && $past(ce))  assert (state == ($past(state) == S5 ? S0 : $past(state) + 3'd1));
        if (!$past(rst) && $past(ce) && $past(eoc)) assert (dout == $past(r));
        if (!$past(rst) && !($past(ce) && $past(eoc))) assert (dout == $past(dout));
    end
`endif
endmodule
