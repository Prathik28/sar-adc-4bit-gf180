* corrected FSM with the decoder outputs next to a re-timed EOC (open issue 3 of the report)
* eoc   : combinational decode of the state register (OUTL), as built
* eoc_r : the same decode applied to the NEXT state (D inputs) and registered in a DFF, so it
*         changes only at a clock edge, high exactly in S5, and cannot glitch
.include models.sp
.include cells.sp
VDD vdd 0 2
VCK clk 0 pulse(0 2 10n 100p 100p 9.9n 20n)
XN q0 q1 q2 rst d0 d1 d2 vdd 0 NSL_FIXED
VRST rst 0 pwl(0 2 25n 2 25.1n 0)
XR d0 d1 d2 clk q0 q0b q1 q1b q2 q2b vdd 0 FSMREG
XO q0 q1 q2 setb3 setb2 setb1 setb0 eoc vdd 0 OUTL
* re-timed EOC: next state == 101
XRI d1 d1n vdd 0 INV
XRA d2 d1n ea vdd 0 AND2
XRB ea d0 eoc_d vdd 0 AND2
XRF eoc_d clk eoc_r eoc_rb vdd 0 DFF
* realistic loads: 20 fF on every decoder output
CL3 setb3 0 20f
CL2 setb2 0 20f
CL1 setb1 0 20f
CL0 setb0 0 20f
CLE eoc 0 20f
CLR eoc_r 0 20f
R0 q0b 0 10meg
R1 q1b 0 10meg
R2 q2b 0 10meg
R3 eoc_rb 0 10meg
.control
tran 10p 450n
wrdata fsm_eocreg.txt v(clk) v(q0) v(q1) v(q2) v(setb3) v(setb2) v(setb1) v(setb0) v(eoc) v(eoc_r)
.endc
.end
