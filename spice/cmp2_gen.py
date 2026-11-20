import sys
dv=float(sys.argv[1]); buf=sys.argv[2]=='buf'
pre=-0.2 if dv>0 else 0.2   # first decision forced to the opposite result
latch = """XB1 outn outnb vdd 0 INV
XB2 outp outpb vdd 0 INV
XL1 outpb compb comp vdd 0 NOR2
XL2 outnb comp compb vdd 0 NOR2
""" if buf else """XL1 outn compb comp vdd 0 NAND2
XL2 outp comp compb vdd 0 NAND2
"""
print(f"""* comparator, two evaluations: forced opposite decision, then test dv
.include models.sp
.include cells.sp
VDD vdd 0 2
VCK clkc 0 pulse(0 2 5n 100p 100p 9.9n 20n)
VP inp 0 pwl(0 {1+pre} 20n {1+pre} 20.1n {1+dv})
VN inn 0 1
XM0 tail clkc 0 0 nmos_3p3 W=8u L=0.28u
XM1 p inp tail 0 nmos_3p3 W=8u L=0.28u
XM2 q inn tail 0 nmos_3p3 W=8u L=0.28u
XM3 outn outp p 0 nmos_3p3 W=4u L=0.28u
XM4 outp outn q 0 nmos_3p3 W=4u L=0.28u
XM5 outn outp vdd vdd pmos_3p3 W=4u L=0.28u
XM6 outp outn vdd vdd pmos_3p3 W=4u L=0.28u
XS1 outn clkc vdd vdd pmos_3p3 W=2u L=0.28u
XS2 outp clkc vdd vdd pmos_3p3 W=2u L=0.28u
XS3 p clkc vdd vdd pmos_3p3 W=2u L=0.28u
XS4 q clkc vdd vdd pmos_3p3 W=2u L=0.28u
{latch}
.control
tran 5p 36n
let vd = abs(v(outp)-v(outn))
meas tran tdec TRIG v(clkc) VAL=1 RISE=2 TARG vd VAL=1 RISE=2
meas tran c1 FIND v(comp) AT=14n
meas tran c2 FIND v(comp) AT=34n
meas tran ivdd INTEG i(VDD) from=24.9n to=36n
.endc
.end""")
