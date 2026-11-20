"""Generate the complete 4-bit SAR ADC netlist (transistor level except ideal caps and sources).
usage: python3 adc_gen.py <vin_mode> <tstop_ns> <outfile.txt>
vin_mode: a float (DC input) or 'ramp:N' (N-step staircase over 0..2 V, one step per conversion)
"""
import sys
vin_mode, tstop, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
T = 120  # ns per conversion (6 x 20 ns)

if vin_mode.startswith('ramp'):
    n = int(vin_mode.split(':')[1])
    pts = ['0 0']
    for k in range(n):
        v = (k + 0.5) * 2.0 / n
        t0 = T * k + 2
        pts.append(f'{t0}n {pts[-1].split()[1]}')
        pts.append(f'{t0 + 0.5}n {v:.6f}')
    vin = 'VIN vin 0 pwl(' + ' '.join(pts) + ')'
else:
    vin = f'VIN vin 0 {float(vin_mode)}'

net = f"""* complete 4-bit SAR ADC
.include models.sp
.include cells.sp
.param cu=25f
VDD vdd 0 2
VREF vref 0 2
VCM vcm 0 1
VCK clk 0 pulse(0 2 10n 100p 100p 9.9n 20n)
VRST rst 0 pwl(0 2 25n 2 25.1n 0)
{vin}

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
"""
for k in range(4):
    net += f"""XSN{k} setb{k} setn{k} vdd 0 INV
XMA{k} setb{k} comp ma{k} vdd 0 AND2
XMB{k} setn{k} r{k} mb{k} vdd 0 AND2
XMO{k} ma{k} mb{k} mo{k} vdd 0 OR2
XMC{k} mo{k} s0n dr{k} vdd 0 AND2
XRF{k} dr{k} clk r{k} r{k}b vdd 0 DFF
* DAC code bit = R or SET
XDO{k} r{k} setb{k} dac{k} vdd 0 OR2
XUP{k} s0n dac{k} upb{k} vdd 0 NAND2
XDN{k} s0 dac{k} dn{k} vdd 0 NOR2
"""
net += """
* ---------------- capacitive DAC + bottom-plate sampling ----------------
* top plate sampled to VCM while PH_T = S0 & CLK; bottom plates track VIN for all of S0
XTT top vcm pht phtb vdd 0 TGW
"""
w = {3: 8, 2: 4, 1: 2, 0: 1}
for k in range(4):
    net += f"""C{k} top b{k} {{{w[k]}*cu}}
XSI{k} vin b{k} s0 s0n vdd 0 TGW
XSR{k} b{k} upb{k} vref vdd pmos_3p3 W=4u L=0.28u
XSG{k} b{k} dn{k} 0 0 nmos_3p3 W=4u L=0.28u
"""
net += """CT top bt {cu}
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
"""
net += f"""tran 20p {tstop}n
wrdata {out} v(clk) v(vin) v(top) v(comp) v(q0) v(q1) v(q2) v(setb3) v(setb2) v(setb1) v(setb0) v(eoc) v(r3) v(r2) v(r1) v(r0) v(dac3) v(dac2) v(dac1) v(dac0) v(outp) v(outn) v(s0) v(pht)
.endc
.end
"""
print(net)
