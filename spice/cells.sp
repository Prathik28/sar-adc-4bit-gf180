* ---- Cell library mirroring the Cadence design: every device W = 2u ----
* GF180MCU 3.3 V devices; L = 0.28u is the minimum length of this process
.param wn=2u wp=2u ll=0.28u

.subckt INV a y vdd vss
XMN y a vss vss nmos_3p3 W={wn} L={ll}
XMP y a vdd vdd pmos_3p3 W={wp} L={ll}
.ends

.subckt NAND2 a b y vdd vss
XMN1 y a n1 vss nmos_3p3 W={wn} L={ll}
XMN2 n1 b vss vss nmos_3p3 W={wn} L={ll}
XMP1 y a vdd vdd pmos_3p3 W={wp} L={ll}
XMP2 y b vdd vdd pmos_3p3 W={wp} L={ll}
.ends

.subckt NOR2 a b y vdd vss
XMN1 y a vss vss nmos_3p3 W={wn} L={ll}
XMN2 y b vss vss nmos_3p3 W={wn} L={ll}
XMP1 y a p1 vdd pmos_3p3 W={wp} L={ll}
XMP2 p1 b vdd vdd pmos_3p3 W={wp} L={ll}
.ends

.subckt AND2 a b y vdd vss
X1 a b n vdd vss NAND2
X2 n y vdd vss INV
.ends

.subckt OR2 a b y vdd vss
X1 a b n vdd vss NOR2
X2 n y vdd vss INV
.ends

* transmission gate: conducts when en=1 (nmos gate) / enb=0 (pmos gate)
.subckt TG x y en enb vdd vss
XMN x en y vss nmos_3p3 W={wn} L={ll}
XMP x enb y vdd pmos_3p3 W={wp} L={ll}
.ends

* master-slave positive-edge D flip-flop, same structure as Figure 5.4
* master transparent while CLK = 0, slave transparent while CLK = 1
.subckt DFF d clk q qb vdd vss
XI5 clk clkb vdd vss INV
XT1 d a clkb clk vdd vss TG
XI0 a b vdd vss INV
XI1 b c1 vdd vss INV
XT2 c1 a clk clkb vdd vss TG
XT3 b c clk clkb vdd vss TG
XI2 c q vdd vss INV
XI4 q qb vdd vss INV
XT4 qb c clkb clk vdd vss TG
.ends

* 3-bit FSM register
.subckt FSMREG d0 d1 d2 clk q0 q0b q1 q1b q2 q2b vdd vss
XF0 d0 clk q0 q0b vdd vss DFF
XF1 d1 clk q1 q1b vdd vss DFF
XF2 d2 clk q2 q2b vdd vss DFF
.ends

* next-state logic exactly as built (Figure 6.3)
.subckt NSL_ASBUILT q0 q1 q2 d0 d1 d2 vdd vss
XI0 q0 d0 vdd vss INV
XI1 q1 q1n vdd vss INV
XI2 q1n q0 t2 vdd vss AND2
XI3 q1 d0 t3 vdd vss AND2
XI4 t2 t3 d1 vdd vss OR2
XI5 q1 q0 t5 vdd vss AND2
XI6 q2 d0 t6 vdd vss AND2
XI7 t6 t5 d2 vdd vss OR2
.ends

* corrected next-state logic: D1 = Q2'(Q1 xor Q0), plus active-high synchronous reset
.subckt NSL_FIXED q0 q1 q2 rst d0 d1 d2 vdd vss
XI0 q0 q0n vdd vss INV
XI1 q1 q1n vdd vss INV
XIR rst rstn vdd vss INV
XIQ2 q2 q2n vdd vss INV
XI2 q1n q0 t2 vdd vss AND2
XI3 q1 q0n t3 vdd vss AND2
XI4 t2 t3 x1 vdd vss OR2
XI8 x1 q2n x1g vdd vss AND2
XI5 q1 q0 t5 vdd vss AND2
XI6 q2 q0n t6 vdd vss AND2
XI7 t6 t5 x2 vdd vss OR2
XR0 q0n rstn d0 vdd vss AND2
XR1 x1g rstn d1 vdd vss AND2
XR2 x2 rstn d2 vdd vss AND2
.ends

* output logic exactly as built (Figure 6.5)
.subckt OUTL q0 q1 q2 setb3 setb2 setb1 setb0 eoc vdd vss
XI0 q2 q2b vdd vss INV
XI1 q1 q1b vdd vss INV
XI2 q0 q0b vdd vss INV
XI3 q2b q1b a3 vdd vss AND2
XI4 a3 q0 setb3 vdd vss AND2
XI5 q2b q0b a5 vdd vss AND2
XI6 a5 q1 setb2 vdd vss AND2
XI7 q2b q0 a7 vdd vss AND2
XI8 a7 q1 setb1 vdd vss AND2
XI9 q2 q1b a9 vdd vss AND2
XI10 a9 q0b setb0 vdd vss AND2
XI11 q2 q1b a11 vdd vss AND2
XI12 a11 q0 eoc vdd vss AND2
.ends
