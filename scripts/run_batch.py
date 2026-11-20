#!/usr/bin/env python3
"""Run a named set of ngspice jobs in parallel.   usage: run_batch.py pvt|enob|fine [-j 6]
Netlists, logs and wrdata files go to build/spice/runs/."""
import subprocess, sys, pathlib, os
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = os.environ.get("GF180_MODELS", str(ROOT.parent / "tools/globalfoundries-pdk-libs-gf180mcu_fd_pr/models/ngspice"))
RUNS = ROOT / "build/spice/runs"; RUNS.mkdir(parents=True, exist_ok=True)

def pvt_jobs():
    # (name, corner, temp, vdd)
    J = [("tt_27_2.0", "typical", 27, 2.0)]
    J += [(f"{c}_27_2.0", c, 27, 2.0) for c in ("ff", "ss", "fs", "sf")]
    J += [("tt_m40_2.0", "typical", -40, 2.0), ("tt_125_2.0", "typical", 125, 2.0),
          ("tt_27_1.8", "typical", 27, 1.8), ("tt_27_2.2", "typical", 27, 2.2),
          ("ss_125_1.8", "ss", 125, 1.8), ("ff_m40_2.2", "ff", -40, 2.2)]
    return [(n, ["--corner", c, "--temp", str(t), "--vdd", str(v), "--vin", "ramp:64"]) for n, c, t, v in J]

def enob_jobs():
    return [("sine_13_128", ["--vin", "sine:13:128"])]

def fine_jobs():
    # 256-step ramp over the full range in 4 chunks of 64 (typical, 27 C, 2 V): 1/16 LSB resolution
    return [(f"fine_q{i}", ["--vin", f"rampr:64:{i / 4}:{(i + 1) / 4}"]) for i in range(4)]

def run(job):
    name, args = job
    sp, txt, log = RUNS / f"{name}.sp", RUNS / f"{name}.txt", RUNS / f"{name}.log"
    subprocess.run([sys.executable, str(ROOT / "scripts/adc_gen.py"), "--models", MODELS,
                    "--out", str(sp), "--data", str(txt)] + args, check=True)
    with open(log, "w") as lf:
        subprocess.run(["ngspice", "-b", str(sp)], stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT / "build/spice")
    print("done", name, flush=True)

if __name__ == "__main__":
    which = sys.argv[1]; j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 6
    jobs = {"pvt": pvt_jobs, "enob": enob_jobs, "fine": fine_jobs}[which]()
    with ThreadPoolExecutor(j) as ex: list(ex.map(run, jobs))
    print("all done")
