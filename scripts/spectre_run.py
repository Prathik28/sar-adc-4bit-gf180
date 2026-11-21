#!/usr/bin/env python3
"""Run a named set of Spectre jobs (gpdk180) in parallel.   usage: spectre_run.py pvt|fine|enob|mim|noise|mm|all [-j 12]
Netlists, logs and raw results go to build/spectre/runs/<job>/.  Needs `spectre` on PATH, a valid license in the
environment and GPDK180_MODELS pointing at the folder with gpdk.scs (see spectre_gen.py)."""
import subprocess, sys, pathlib
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "build/spectre/runs"; RUNS.mkdir(parents=True, exist_ok=True)
PY = sys.executable


def pvt_jobs():
    J = [("NN_27_1.8", "NN", 27, 1.8)] + [(f"{c}_27_1.8", c, 27, 1.8) for c in ("FF", "SS", "FS", "SF")]
    J += [("NN_m40_1.8", "NN", -40, 1.8), ("NN_125_1.8", "NN", 125, 1.8), ("NN_27_1.62", "NN", 27, 1.62),
          ("NN_27_1.98", "NN", 27, 1.98), ("SS_125_1.62", "SS", 125, 1.62), ("FF_m40_1.98", "FF", -40, 1.98)]
    return [(n, ["--corner", c, "--temp", str(t), "--vdd", str(v), "--vin", "ramp:64"]) for n, c, t, v in J]


def enob_jobs():
    return [("sine_13_128", ["--vin", "sine:13:128"])]


def fine_jobs():
    return [(f"fine_q{i}", ["--vin", f"rampr:64:{i / 4}:{(i + 1) / 4}"]) for i in range(4)]


def mim_jobs():
    J = [(f"mimfine_q{i}", ["--mim", "--vin", f"rampr:64:{i / 4}:{(i + 1) / 4}"]) for i in range(4)]
    J += [("mim_ss_125_1.62", ["--mim", "--corner", "SS", "--temp", "125", "--vdd", "1.62", "--vin", "ramp:64"]),
          ("mim_ff_m40_1.98", ["--mim", "--corner", "FF", "--temp", "-40", "--vdd", "1.98", "--vin", "ramp:64"])]
    return J


def noise_jobs():
    return [(f"noise_{s}", ["--noise", str(s), "--vin", "sine:13:128"]) for s in (0.1, 0.5, 2, 5, 10, 20)]


def mm_jobs():   # whole-converter mismatch Monte Carlo (gpdk180 'stat' section, mismatch only), typical corner
    return [(f"mm_typical_{s}", ["--mc", str(s), "--vin", "ramp:64"]) for s in (1, 2, 3, 4)]


def run(job):
    name, args = job
    d = RUNS / name
    subprocess.run([PY, str(ROOT / "scripts/spectre_gen.py"), "--out", str(d), "--name", name] + args, check=True)
    with open(d / f"{name}.log", "w") as lf:
        r = subprocess.run(["spectre", "-format", "nutascii", "-raw", f"{name}.raw", f"{name}.scs"],
                           stdout=lf, stderr=subprocess.STDOUT, cwd=d)
    print("done" if r.returncode == 0 else f"FAILED({r.returncode})", name, flush=True)


if __name__ == "__main__":
    which = sys.argv[1]; j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 12
    sets = {"pvt": pvt_jobs, "enob": enob_jobs, "fine": fine_jobs, "mim": mim_jobs, "noise": noise_jobs, "mm": mm_jobs}
    jobs = sum((f() for f in sets.values()), []) if which == "all" else sets[which]()
    with ThreadPoolExecutor(j) as ex:
        list(ex.map(run, jobs))
    print("all done")
