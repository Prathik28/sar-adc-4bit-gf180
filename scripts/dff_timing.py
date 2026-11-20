#!/usr/bin/env python3
"""Setup time, hold time and clock-to-Q of the master-slave D flip-flop (spice/cells.sp, DFF)
with the GF180MCU models: typical corner, 27 C, VDD 2 V, 20 fF load on Q and Q_b, 100 ps edges.
D is delayed relative to the clock (the fix for open issue 5 of the report: coincident edges).
usage: dff_timing.py"""
import subprocess, re, os, pathlib, json
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = os.environ.get("GF180_MODELS", str(ROOT.parent / "tools/globalfoundries-pdk-libs-gf180mcu_fd_pr/models/ngspice"))
W = ROOT / "build/spice/dff"; W.mkdir(parents=True, exist_ok=True)
HEAD = f"""* DFF timing
.include {MODELS}/design.ngspice
.lib {MODELS}/sm141064.ngspice typical
.param sw_stat_global=0 sw_stat_mismatch=0
.include {ROOT}/spice/cells.sp
VDD vdd 0 2
VCK clk 0 pulse(0 2 10n 100p 100p 9.9n 40n)
XF d clk q qb vdd 0 DFF
CQ q 0 20f
CQB qb 0 20f
"""
EDGE = 50.05   # ns: 50 % point of the second rising clock edge (clk rises 10n+0.1n*0.5 ... every 40 ns)

def sim(name, d_src, probe):
    sp = W / f"{name}.sp"
    sp.write_text(HEAD + d_src + f"\n.control\ntran 5p 85n\n{probe}\n.endc\n.end\n")
    r = subprocess.run(["ngspice", "-b", str(sp)], capture_output=True, text=True)
    return r.stdout + r.stderr

def val(txt, key):
    m = re.search(rf"^{key}\s*=\s*([-+0-9.e]+)", txt, re.M)
    return float(m.group(1)) if m else float("nan")

def setup_point(tsu_ps):   # D rises tsu before the edge; q starts at 0
    t = EDGE - tsu_ps / 1000
    return tsu_ps, val(sim(f"su_{tsu_ps}", f"VD d 0 pwl(0 0 {t:.4f}n 0 {t + 0.1:.4f}n 2)", "meas tran qv FIND v(q) AT=80n"), "qv") > 1.0

def hold_point(th_ps):     # D=1 until th after the edge, then falls; captured value should stay 1
    t = EDGE + th_ps / 1000
    return th_ps, val(sim(f"ho_{th_ps}", f"VD d 0 pwl(0 2 {t:.4f}n 2 {t + 0.1:.4f}n 0)", "meas tran qv FIND v(q) AT=80n"), "qv") > 1.0

def edge_search(fn, lo, hi, step):
    """first point (scanning lo..hi) where the captured result is True / False boundary; returns list"""
    with ThreadPoolExecutor(4) as ex:
        return list(ex.map(fn, range(lo, hi + 1, step)))

if __name__ == "__main__":
    su = edge_search(setup_point, -200, 300, 20)
    ho = edge_search(hold_point, -300, 200, 20)
    # setup: smallest tsu such that D (rising) is captured; hold: smallest th such that old D (=1) is kept
    tsu = min(t for t, ok in su if ok and all(o for tt, o in su if tt >= t))
    th = min(t for t, ok in ho if ok and all(o for tt, o in ho if tt >= t))
    dr = "VD d 0 pwl(0 0 30n 0 30.1n 2 70n 2 70.1n 0)"
    txt = sim("tcq", dr, "meas tran tcq_r TRIG v(clk) VAL=1 RISE=2 TARG v(q) VAL=1 RISE=1\n"
                         "meas tran tcq_f TRIG v(clk) VAL=1 RISE=3 TARG v(q) VAL=1 FALL=1")
    # tcq_f needs the 3rd edge at 90 ns; extend run
    sp = W / "tcq.sp"; sp.write_text(sp.read_text().replace("tran 5p 85n", "tran 5p 110n"))
    txt = subprocess.run(["ngspice", "-b", str(sp)], capture_output=True, text=True).stdout
    out = {"setup_ps": tsu, "hold_ps": th, "tcq_rise_ps": 1e12 * val(txt, "tcq_r"), "tcq_fall_ps": 1e12 * val(txt, "tcq_f"),
           "scan_step_ps": 20, "setup_scan": su, "hold_scan": ho}
    print(json.dumps({k: v for k, v in out.items() if "scan" not in k or k == "scan_step_ps"}, indent=1))
    (ROOT / "results/dff_timing.json").write_text(json.dumps(out, indent=1))
