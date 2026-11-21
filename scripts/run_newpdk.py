#!/usr/bin/env python3
"""Run the MIM corner jobs (plus controls) against the newer GF180MCU ngspice models.
usage: run_newpdk.py NEW_MODELS_DIR [-j 5]     (NEW_MODELS_DIR = .../models/ngspice of the newer PDK checkout)
Netlists, logs and wrdata files go to build/spice_newpdk/runs/."""
import subprocess, sys, pathlib, shutil, re
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = sys.argv[1]
W = ROOT / "build/spice_newpdk"; RUNS = W / "runs"; RUNS.mkdir(parents=True, exist_ok=True)
for f in (ROOT / "spice").glob("*.sp"):          # device names of the newer PDK
    (W / f.name).write_text(f.read_text().replace("nmos_3p3", "nfet_03v3").replace("pmos_3p3", "pfet_03v3"))
(W / "models.sp").write_text("* unused: adc_gen.py writes the model lines\n")
JOBS = [("mim_NN_27_2.0", ["--mim", "--corner", "typical", "--temp", "27", "--vdd", "2.0", "--vin", "ramp:64"]),
        ("mim_ss_125_1.8", ["--mim", "--corner", "ss", "--temp", "125", "--vdd", "1.8", "--vin", "ramp:64"]),
        ("mim_ff_m40_2.2", ["--mim", "--corner", "ff", "--temp", "-40", "--vdd", "2.2", "--vin", "ramp:64"]),
        ("nomim_ss_125_1.8", ["--corner", "ss", "--temp", "125", "--vdd", "1.8", "--vin", "ramp:64"]),
        ("nomim_ff_m40_2.2", ["--corner", "ff", "--temp", "-40", "--vdd", "2.2", "--vin", "ramp:64"])]
def run(job):
    n, args = job; sp, txt, log = RUNS / f"{n}.sp", RUNS / f"{n}.txt", RUNS / f"{n}.log"
    subprocess.run([sys.executable, str(ROOT / "scripts/adc_gen.py"), "--models", MODELS, "--pdk-rev", "new",
                    "--out", str(sp), "--data", str(txt)] + args, check=True)
    with open(log, "w") as lf:
        r = subprocess.run(["ngspice", "-b", str(sp)], stdout=lf, stderr=subprocess.STDOUT, cwd=W)
    print("done" if "aborted" not in log.read_text() else "ABORTED", n, flush=True)
if __name__ == "__main__":
    j = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 5
    with ThreadPoolExecutor(j) as ex: list(ex.map(run, JOBS))
    print("all done")
