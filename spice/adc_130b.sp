* complete 4-bit SAR ADC
.include models.sp
.include cells.sp
.param cu=25f
VDD vdd 0 2
VREF vref 0 2
VCM vcm 0 1
VCK clk 0 pulse(0 2 10n 100p 100p 9.9n 20n)
VRST rst 0 pwl(0 2 25n 2 25.1n 0)
VIN vin 0 1.3

* ---------------- control FSM (corrected) ----------------
XN q0 q1 q2 rst d0 d1 d2 vdd 0 NSL_FIXED
XR d0 d1 d2 clk q0 q0b q1 q1b q2 q2b vdd 0 FSMREG
XO q0 q1 q2 setb3 setb2 setb1 setb0 eoc vdd 0 OUTL
* sample state S0 = Q2'Q1'Q0' and its phases
XS0a q2b q1b s0a vdd 0 AND2
XS0b s0a q0b s0 vdd 0 AND2
XS0n s0 s0n vdd 0 INV
XPT s0 clk pht vdd 0 AND2
XPTn pht phtb vdd 0 INV
XCKB clk clkc vdd 0 INV

* ---------------- SAR register: D = S0' (SET ? COMP : R) ----------------
XSN0 setb0 setn0 vdd 0 INV
XMA0 setb0 comp ma0 vdd 0 AND2
XMB0 setn0 r0 mb0 vdd 0 AND2
XMO0 ma0 mb0 mo0 vdd 0 OR2
XMC0 mo0 s0n dr0 vdd 0 AND2
XRF0 dr0 clk r0 r0b vdd 0 DFF
* DAC code bit = R or SET
XDO0 r0 setb0 dac0 vdd 0 OR2
XUP0 s0n dac0 upb0 vdd 0 NAND2
XDN0 s0 dac0 dn0 vdd 0 NOR2
XSN1 setb1 setn1 vdd 0 INV
XMA1 setb1 comp ma1 vdd 0 AND2
XMB1 setn1 r1 mb1 vdd 0 AND2
XMO1 ma1 mb1 mo1 vdd 0 OR2
XMC1 mo1 s0n dr1 vdd 0 AND2
XRF1 dr1 clk r1 r1b vdd 0 DFF
* DAC code bit = R or SET
XDO1 r1 setb1 dac1 vdd 0 OR2
XUP1 s0n dac1 upb1 vdd 0 NAND2
XDN1 s0 dac1 dn1 vdd 0 NOR2
XSN2 setb2 setn2 vdd 0 INV
XMA2 setb2 comp ma2 vdd 0 AND2
XMB2 setn2 r2 mb2 vdd 0 AND2
XMO2 ma2 mb2 mo2 vdd 0 OR2
XMC2 mo2 s0n dr2 vdd 0 AND2
XRF2 dr2 clk r2 r2b vdd 0 DFF
* DAC code bit = R or SET
XDO2 r2 setb2 dac2 vdd 0 OR2
XUP2 s0n dac2 upb2 vdd 0 NAND2
XDN2 s0 dac2 dn2 vdd 0 NOR2
XSN3 setb3 setn3 vdd 0 INV
XMA3 setb3 comp ma3 vdd 0 AND2
XMB3 setn3 r3 mb3 vdd 0 AND2
XMO3 ma3 mb3 mo3 vdd 0 OR2
XMC3 mo3 s0n dr3 vdd 0 AND2
XRF3 dr3 clk r3 r3b vdd 0 DFF
* DAC code bit = R or SET
XDO3 r3 setb3 dac3 vdd 0 OR2
XUP3 s0n dac3 upb3 vdd 0 NAND2
XDN3 s0 dac3 dn3 vdd 0 NOR2

* ---------------- capacitive DAC + bottom-plate sampling ----------------
* top plate sampled to VCM while PH_T = S0 & CLK; bottom plates track VIN for all of S0
XTT top vcm pht phtb vdd 0 TGW
C0 top b0 {1*cu}
XSI0 vin b0 s0 s0n vdd 0 TGW
XSR0 b0 upb0 vref vdd pmos_3p3 W=4u L=0.28u
XSG0 b0 dn0 0 0 nmos_3p3 W=4u L=0.28u
C1 top b1 {2*cu}
XSI1 vin b1 s0 s0n vdd 0 TGW
XSR1 b1 upb1 vref vdd pmos_3p3 W=4u L=0.28u
XSG1 b1 dn1 0 0 nmos_3p3 W=4u L=0.28u
C2 top b2 {4*cu}
XSI2 vin b2 s0 s0n vdd 0 TGW
XSR2 b2 upb2 vref vdd pmos_3p3 W=4u L=0.28u
XSG2 b2 dn2 0 0 nmos_3p3 W=4u L=0.28u
C3 top b3 {8*cu}
XSI3 vin b3 s0 s0n vdd 0 TGW
XSR3 b3 upb3 vref vdd pmos_3p3 W=4u L=0.28u
XSG3 b3 dn3 0 0 nmos_3p3 W=4u L=0.28u
CT top bt {cu}
XSIT vin bt s0 s0n vdd 0 TGW
XSGT bt s0n 0 0 nmos_3p3 W=4u L=0.28u
* parasitic on the top plate (wiring + comparator input)
CPT top 0 20f

* ---------------- StrongARM latch comparator + SR latch ----------------
* evaluates while CLK is low (clkc high); COMP = 1 when VCM > top, i.e. VIN >= VDAC
XM0 tail clkc 0 0 nmos_3p3 W=8u L=0.28u
XM1 p vcm tail 0 nmos_3p3 W=8u L=0.28u
XM2 q top tail 0 nmos_3p3 W=8u L=0.28u
XM3 outn outp p 0 nmos_3p3 W=4u L=0.28u
XM4 outp outn q 0 nmos_3p3 W=4u L=0.28u
XM5 outn outp vdd vdd pmos_3p3 W=4u L=0.28u
XM6 outp outn vdd vdd pmos_3p3 W=4u L=0.28u
XS1 outn clkc vdd vdd pmos_3p3 W=2u L=0.28u
XS2 outp clkc vdd vdd pmos_3p3 W=2u L=0.28u
XS3 p clkc vdd vdd pmos_3p3 W=2u L=0.28u
XS4 q clkc vdd vdd pmos_3p3 W=2u L=0.28u
XB1 outn outnb vdd 0 INV
XB2 outp outpb vdd 0 INV
XL1 outnb comp compb vdd 0 NOR2
XL2 outpb compb comp vdd 0 NOR2

.subckt TGW x y en enb vdd vss
XMN x en y vss nmos_3p3 W=8u L=0.28u
XMP x enb y vdd pmos_3p3 W=8u L=0.28u
.ends
.options method=gear
.control
tran 20p 260.0n
wrdata adc_130b.txt v(clk) v(vin) v(top) v(comp) v(q0) v(q1) v(q2) v(setb3) v(setb2) v(setb1) v(setb0) v(eoc) v(r3) v(r2) v(r1) v(r0) v(dac3) v(dac2) v(dac1) v(dac0) v(outp) v(outn) v(s0) v(pht)
.endc
.end

