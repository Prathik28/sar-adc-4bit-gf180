#!/usr/bin/env python3
"""Spectre/gpdk180 port of mc_comparator.py: Monte Carlo of the StrongARM comparator input-referred offset.

Each seed is one Spectre `montecarlo variations=mismatch numruns=1 seed=S` iteration on the gpdk180 `stat`
model section (per-device mismatch of tox, dvth, dl, dw, cj..., NOT area-scaled: gpdk180's statistics are
generic).  The differential input is stepped from -60 mV to +60 mV in 1 mV steps, one evaluation per 20 ns
clock; the offset is where the buffered SR-latch output flips.  Supply 1.8 V, VCM 0.9 V, 27 C.

Corners: the kit only has a mismatch (`stat`) section for the typical process.  For ff/ss/fs/sf the corner's
process parameters (from the kit's own nmos1.scs/pmos1.scs `fast`/`slow` sections) are re-assigned on top of
the `stat` section, so the mismatch sigma is the typical one around the shifted corner centre.

usage: spectre_mc_comparator.py [N_seeds=100] [-j 12] [--corner typical|ff|ss|fs|sf]
"""
import subprocess, sys, os, pathlib, json, re
import numpy as np
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import spectre_gen as G
import spectre_analyze as A

MODELS = os.environ["GPDK180_MODELS"]
CORNER = sys.argv[sys.argv.index("--corner") + 1] if "--corner" in sys.argv else "typical"
TAG = "" if CORNER == "typical" else f"_{CORNER}"
W = ROOT / "build/spectre/mc_cmp"; W.mkdir(parents=True, exist_ok=True)
VDD = 1.8
DV = 0.060; STEP = 0.001; P = 20.0
steps = np.round(np.arange(-DV, DV + STEP / 2, STEP), 6)
SECTION = {"typical": ("nom", "nom"), "ff": ("fast", "fast"), "ss": ("slow", "slow"), "fs": ("fast", "slow"), "sf": ("slow", "fast")}


def corner_params(fname, section):
    txt = pathlib.Path(MODELS, fname).read_text()
    blk = txt.split(f"section {section}")[1].split("include")[0]
    return " ".join(re.findall(r"^\s*parameters\s+(.*)$", blk, flags=re.M))


def dev(name, nodes, kind, w):
    return (f"{name} ({nodes}) {kind} w={w} l=ll as=({w})*dl ad=({w})*dl ps=2*(({w})+dl) pd=2*(({w})+dl)")


def netlist():
    cells, _ = G.translate(pathlib.Path(ROOT / "spice/cells.sp").read_text(), False)
    pts = [f"0 {VDD / 2 + steps[0]}"]
    for k, dv in enumerate(steps):
        if k:
            t = P * k
            pts += [f"{(t + 1) * 1e-9:.6g} {VDD / 2 + steps[k - 1]:.6f}", f"{(t + 1.5) * 1e-9:.6g} {VDD / 2 + dv:.6f}"]
    n, p = SECTION[CORNER]
    over = ""
    if CORNER != "typical":
        over = f"parameters {corner_params('nmos1.scs', n)}\nparameters {corner_params('pmos1.scs', p)}\n"
    body = "\n".join([
        "// comparator offset Monte Carlo (gpdk180, Spectre)", "simulator lang=spectre", "global 0",
        f'include "{MODELS}/gpdk.scs" section=stat', over.rstrip(),
        "parameters wn=2u wp=2u ll=0.18u dl=0.5u",
        f"VDD (vdd 0) vsource dc={VDD}",
        f"VCK (clkc 0) vsource type=pulse val0=0 val1={VDD} delay=5n rise=100p fall=100p width=9.9n period=20n",
        *cells,
        "VP (inp 0) vsource type=pwl file=\"vp.pwl\"", f"VN (inn 0) vsource dc={VDD / 2}",
        dev("XM0", "tail clkc 0 0", "nmos1", "8u"), dev("XM1", "p inp tail 0", "nmos1", "8u"),
        dev("XM2", "q inn tail 0", "nmos1", "8u"), dev("XM3", "outn outp p 0", "nmos1", "4u"),
        dev("XM4", "outp outn q 0", "nmos1", "4u"), dev("XM5", "outn outp vdd vdd", "pmos1", "4u"),
        dev("XM6", "outp outn vdd vdd", "pmos1", "4u"), dev("XS1", "outn clkc vdd vdd", "pmos1", "2u"),
        dev("XS2", "outp clkc vdd vdd", "pmos1", "2u"), dev("XS3", "p clkc vdd vdd", "pmos1", "2u"),
        dev("XS4", "q clkc vdd vdd", "pmos1", "2u"),
        "XB1 (outn outnb vdd 0) INV", "XB2 (outp outpb vdd 0) INV",
        "XL1 (outpb compb comp vdd 0) NOR2", "XL2 (outnb comp compb vdd 0) NOR2",
        "simulatorOptions options temp=27 tnom=27" + (" redefinedparams=ignore" if CORNER != "typical" else "")])
    return body, pts


def one(seed):
    d = W / f"{CORNER}_s{seed}"; d.mkdir(exist_ok=True)
    body, pts = netlist()
    # pwl file: one "time value" pair per line
    lines = []
    for q in pts:
        t, v = q.split(); lines.append(f"{float(t):.6g} {v}")
    (d / "vp.pwl").write_text("\n".join(lines) + "\n")
    tstop = P * len(steps) + 5
    (d / "cmp.scs").write_text(body + f"\nmc montecarlo seed={seed} numruns=1 variations=mismatch donominal=no "
                               f"savefamilyplots=no {{\n  tran tran stop={tstop}n errpreset=conservative maxstep=100p\n}}\n"
                               "save clkc comp\n")
    r = subprocess.run(["spectre", "-format", "nutascii", "-raw", "cmp.raw", "cmp.scs"], cwd=d,
                       stdout=open(d / "cmp.log", "w"), stderr=subprocess.STDOUT)
    if r.returncode != 0:
        return seed, float("nan"), -1, False, False
    t, s = A.load_raw(d / "cmp.raw")
    dec = np.array([np.interp((P * k + 14) * 1e-9, t, s["comp"]) > VDD / 2 for k in range(len(steps))])
    flips = np.nonzero(dec[1:] != dec[:-1])[0]
    off = float("nan") if len(flips) != 1 else (steps[flips[0]] + steps[flips[0] + 1]) / 2
    for f in d.iterdir():
        if f.name.endswith((".raw", ".pwl")):
            f.unlink()
    return seed, off, len(flips), bool(dec[0]), bool(dec[-1])


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else 100
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 12
    with ThreadPoolExecutor(j) as ex:
        res = list(ex.map(one, range(1, n + 1)))
    off = np.array([r[1] for r in res]); ok = ~np.isnan(off)
    out = {"pdk": "gpdk180", "tool": "Spectre", "vdd": VDD, "corner": CORNER, "n": n, "valid": int(ok.sum()),
           "mean_mV": float(1e3 * off[ok].mean()) if ok.any() else None,
           "sigma_mV": float(1e3 * off[ok].std(ddof=1)) if ok.sum() > 1 else None,
           "min_mV": float(1e3 * off[ok].min()) if ok.any() else None,
           "max_mV": float(1e3 * off[ok].max()) if ok.any() else None, "step_mV": 1e3 * STEP,
           "bad_seeds": [int(r[0]) for r in res if np.isnan(r[1])]}
    print(json.dumps(out, indent=1))
    rd = ROOT / "results/gpdk180"; rd.mkdir(parents=True, exist_ok=True)
    (rd / f"mc_comparator_offset{TAG}.json").write_text(
        json.dumps(out | {"offsets_V": [None if np.isnan(x) else float(x) for x in off]}, indent=1))
