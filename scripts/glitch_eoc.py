#!/usr/bin/env python3
"""Decoder glitch study (open issue 3): combinational EOC / SET lines vs the re-timed EOC.
For every clock cycle the expected (steady) value of each output is decoded from the state register
at the end of the cycle; a glitch is an excursion past VDD/2 away from that value during the cycle.
usage: glitch_eoc.py   (needs build/spice from scripts/setup_spice.sh)"""
import subprocess, json, pathlib
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
B = ROOT / "build/spice"; VDD = 2.0; HALF = VDD / 2
def run(NET):
    subprocess.run(["ngspice", "-b", NET], cwd=B, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    a = np.loadtxt(B / "fsm_eocreg.txt"); t = a[:, 0]
    v = {n: a[:, 2 * i + 1] for i, n in enumerate("clk q0 q1 q2 setb3 setb2 setb1 setb0 eoc eoc_r".split())}
    dec = {"setb3": lambda s: s == 1, "setb2": lambda s: s == 2, "setb1": lambda s: s == 3, "setb0": lambda s: s == 4,
           "eoc": lambda s: s == 5, "eoc_r": lambda s: s == 5}
    res = {n: {"spurious_pulses": 0, "peak_dev_V": 0.0, "max_pulse_ps": 0.0, "cycles_checked": 0} for n in dec}
    prev = {}
    for k in range(3, 22):                                 # skip reset
        t0, t1 = (10 + 20 * k) * 1e-9, (10 + 20 * (k + 1)) * 1e-9
        te = t1 - 0.5e-9
        q = lambda n: int(np.interp(te, t, v[n]) > HALF)
        s = (q("q2") << 2) | (q("q1") << 1) | q("q0")
        m = (t >= t0) & (t < t1)
        for n, f in dec.items():
            want = bool(f(s)); w = v[n][m]; tt = t[m]
            cross = tt[1:][np.diff((w > HALF).astype(int)) != 0]
            if n in prev:                                  # first cycle only seeds the previous value
                expect_change = int(prev[n] != want)
                extra = len(cross) - expect_change
                r = res[n]; r["cycles_checked"] += 1
                if extra > 0:
                    r["spurious_pulses"] += extra // 2 + extra % 2
                    r["max_pulse_ps"] = max(r["max_pulse_ps"], float((cross[1] - cross[0]) * 1e12) if len(cross) > 1 else 0.0)
                if not expect_change:                      # steady cycle: how far did the output move?
                    r["peak_dev_V"] = max(r["peak_dev_V"], float(np.abs(w - (VDD if want else 0.0)).max()))
            prev[n] = want
    return res

if __name__ == "__main__":
    src = (ROOT / "spice/fsm_eocreg.sp").read_text()
    (B / "fsm_eocreg_unloaded.sp").write_text("\n".join(l for l in src.splitlines() if not l.startswith("CL")).replace("fsm_eocreg.txt", "fsm_eocreg.txt"))
    out = {}
    for label, net in (("loaded_20fF", "../../spice/fsm_eocreg.sp"), ("unloaded_10Mohm_as_in_report", "fsm_eocreg_unloaded.sp")):
        print(label)
        out[label] = run(net)
        for n, r in out[label].items(): print(f"  {n:6s} {r}")
    (ROOT / "results/eoc_glitch.json").write_text(json.dumps(out, indent=1))
