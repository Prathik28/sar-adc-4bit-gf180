#!/usr/bin/env python3
"""Monte Carlo of the StrongARM comparator input-referred offset with the GF180MCU mismatch models.

Each seed gets its own random threshold shifts (delvto = mis_vth * sw_stat_mismatch, Pelgrom-style,
per device).  The differential input is stepped from -DV to +DV in 1 mV steps, one evaluation per
20 ns clock; the offset is where the buffered SR-latch output flips.  Corner: typical, 27 C, VDD 2 V.

usage: mc_comparator.py [N_seeds=200] [-j 4]
"""
import subprocess, sys, os, pathlib, json
import numpy as np
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = os.environ.get("GF180_MODELS", str(ROOT.parent / "tools/globalfoundries-pdk-libs-gf180mcu_fd_pr/models/ngspice"))
W = ROOT / "build/spice/mc_cmp"; W.mkdir(parents=True, exist_ok=True)
DV = 0.060; STEP = 0.001; P = 20.0  # volts, volts, ns
steps = np.round(np.arange(-DV, DV + STEP / 2, STEP), 6)

def netlist(seed, data):
    pts = [f"0 {1 + steps[0]}"]
    for k, dv in enumerate(steps):
        t = P * k
        if k:
            pts += [f"{t + 1}n {1 + steps[k - 1]}", f"{t + 1.5}n {1 + dv}"]
    return f"""* comparator offset Monte Carlo, seed {seed}
.include {MODELS}/design.ngspice
.lib {MODELS}/sm141064.ngspice typical
.param sw_stat_global=0 sw_stat_mismatch=1
.option seed={seed}
.include {ROOT}/spice/cells.sp
VDD vdd 0 2
VCK clkc 0 pulse(0 2 5n 100p 100p 9.9n 20n)
VP inp 0 pwl({' '.join(pts)})
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
XB1 outn outnb vdd 0 INV
XB2 outp outpb vdd 0 INV
XL1 outpb compb comp vdd 0 NOR2
XL2 outnb comp compb vdd 0 NOR2
.control
tran 20p {P * len(steps) + 5}n
wrdata {data} v(clkc) v(comp)
.endc
.end
"""

def one(seed):
    sp, dat = W / f"s{seed}.sp", W / f"s{seed}.txt"
    sp.write_text(netlist(seed, dat))
    subprocess.run(["ngspice", "-b", str(sp)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    a = np.loadtxt(dat); t, comp = a[:, 0], a[:, 3]
    dec = np.array([np.interp((P * k + 14) * 1e-9, t, comp) > 1.0 for k in range(len(steps))])
    flips = np.nonzero(dec[1:] != dec[:-1])[0]
    off = float("nan") if len(flips) != 1 else (steps[flips[0]] + steps[flips[0] + 1]) / 2
    dat.unlink(); sp.unlink()
    return seed, off, len(flips), bool(dec[0]), bool(dec[-1])

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 4
    with ThreadPoolExecutor(j) as ex: res = list(ex.map(one, range(1, n + 1)))
    off = np.array([r[1] for r in res]); ok = ~np.isnan(off)
    out = {"n": n, "valid": int(ok.sum()), "mean_mV": 1e3 * off[ok].mean(), "sigma_mV": 1e3 * off[ok].std(ddof=1),
           "min_mV": 1e3 * off[ok].min(), "max_mV": 1e3 * off[ok].max(), "step_mV": 1e3 * STEP,
           "bad_seeds": [r[0] for r in res if np.isnan(r[1])]}
    print(json.dumps(out, indent=1))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/mc_comparator_offset.json").write_text(json.dumps(out | {"offsets_V": [None if np.isnan(x) else x for x in off]}, indent=1))
