#!/usr/bin/env python3
"""Behavioural Monte Carlo of unit-capacitor mismatch in the 4-bit charge-redistribution DAC.

Model (matches spice/adc_130b.sp: C0..C3 = 1,2,4,8 unit caps, one extra unit cap CT to ground):
a code decision is  Vin * Ctot > Vref * sum(b_i * C_i),  Ctot = sum(C_i) + CT  (the top-plate
parasitic cancels).  Each capacitor made of n unit caps has relative sigma = sigma_u / sqrt(n).
The real SAR binary search is run on a dense input grid; DNL and INL come from the code
transitions.  sigma_u is an ASSUMPTION: the netlist uses ideal capacitors, so this is not a
PDK result.  usage: mc_cap_dac.py [trials=5000]
"""
import sys, json, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
rng = np.random.default_rng(20261121)
N, VREF = 4, 1.0
trials = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
vin = (np.arange(8192) + 0.5) / 8192 * VREF            # dense grid, 0.5 resolution of 1/8192 FS
LSB = VREF / 2 ** N

def sar(vin, C, Ctot):
    code = np.zeros(vin.shape, int)
    for b in range(N - 1, -1, -1):
        trial = code | (1 << b)
        w = sum(((trial >> i) & 1) * C[i] for i in range(N))
        code = np.where(vin * Ctot > VREF * w, trial, code)
    return code

def run(sigma_u):
    worst_dnl, worst_inl, miss = [], [], 0
    for _ in range(trials):
        n = np.array([1, 2, 4, 8, 1])
        c = n * (1 + rng.normal(0, sigma_u, 5) / np.sqrt(n))
        C, Ctot = c[:4], c.sum()
        code = sar(vin, C, Ctot)
        # transition voltage into each code k = first input producing code >= k
        T = np.array([vin[np.argmax(code >= k)] if (code >= k).any() else np.nan for k in range(1, 2 ** N)])
        present = np.isin(np.arange(2 ** N), code)
        if not present.all(): miss += 1
        ideal = np.arange(1, 2 ** N) * LSB
        dnl = np.diff(T) / LSB - 1                      # codes 1..14
        inl = (T - ideal) / LSB
        worst_dnl.append(np.nanmax(np.abs(dnl))); worst_inl.append(np.nanmax(np.abs(inl)))
    wd, wi = np.array(worst_dnl), np.array(worst_inl)
    return {"sigma_u_pct": 100 * sigma_u, "trials": trials,
            "yield_DNL<0.5LSB": float((wd < 0.5).mean()), "yield_INL<0.5LSB": float((wi < 0.5).mean()),
            "yield_no_missing_codes": 1 - miss / trials,
            "median_worst_DNL": float(np.median(wd)), "p99_worst_DNL": float(np.percentile(wd, 99)),
            "median_worst_INL": float(np.median(wi)), "p99_worst_INL": float(np.percentile(wi, 99))}

res = [run(s) for s in (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05)]
for r in res: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results/mc_cap_mismatch.json").write_text(json.dumps(res, indent=1))
