#!/usr/bin/env python3
"""Reproduce Chapter 8 FSM results: state sequence of the three FSM variants.
usage (from repo root): scripts/analyze_fsm.py   -- runs ngspice on build/spice/fsm_*.sp"""
import subprocess, sys, json, pathlib
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
B = ROOT / "build/spice"
out = {}
for name, label in (("fsm_asbuilt", "as built (equations from the reference report)"),
                    ("fsm_asbuilt1k", "as built + 1 kOhm loads on Q_b"),
                    ("fsm_fixed", "corrected D1 + synchronous reset")):
    subprocess.run(["ngspice", "-b", f"{name}.sp"], cwd=B, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    a = np.loadtxt(B / f"{name}.txt"); t = a[:, 0]
    v = {n: a[:, 2 * i + 1] for i, n in enumerate("clk q0 q1 q2 setb3 setb2 setb1 setb0 eoc q0b q1b q2b".split())}
    seq = []
    for k in range(22):
        tq = (10 + 20 * (k + 1) - 1) * 1e-9      # just before each rising edge: state of cycle k
        if tq > t[-1]: break
        b = lambda n: int(np.interp(tq, t, v[n]) > 1.0)
        seq.append(f"{b('q2')}{b('q1')}{b('q0')}")
    out[name] = {"label": label, "states": seq}
    print(f"{label}:\n  " + " ".join(seq))
(ROOT / "results/fsm_state_sequences.json").write_text(json.dumps(out, indent=1))
