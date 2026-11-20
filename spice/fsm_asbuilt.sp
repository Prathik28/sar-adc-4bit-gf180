* complete FSM, mode=asbuilt
.include models.sp
.include cells.sp
VDD vdd 0 2
VCK clk 0 pulse(0 2 10n 100p 100p 9.9n 20n)
XN q0 q1 q2 d0 d1 d2 vdd 0 NSL_ASBUILT
XR d0 d1 d2 clk q0 q0b q1 q1b q2 q2b vdd 0 FSMREG
XO q0 q1 q2 setb3 setb2 setb1 setb0 eoc vdd 0 OUTL
R0 q0b 0 10meg
R1 q1b 0 10meg
R2 q2b 0 10meg
RL3 setb3 0 10meg
RL2 setb2 0 10meg
RL1 setb1 0 10meg
RL0 setb0 0 10meg
RLE eoc 0 10meg
.ic v(xr.xf0.c)=2 v(xr.xf1.c)=2 v(xr.xf2.c)=2 v(xr.xf0.a)=2 v(xr.xf1.a)=0 v(xr.xf2.a)=2
.control
tran 10p 450n
wrdata fsm_asbuilt.txt v(clk) v(q0) v(q1) v(q2) v(setb3) v(setb2) v(setb1) v(setb0) v(eoc) v(q0b) v(q1b) v(q2b)
.endc
.end
