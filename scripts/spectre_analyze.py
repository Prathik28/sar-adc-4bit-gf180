#!/usr/bin/env python3
"""Parser and post-processing for the Spectre/gpdk180 runs (counterpart of analyze.py + spicelib.py).

Reads Spectre nutascii (SPICE3 raw ascii) transient results and decodes the SAR conversions exactly as
spicelib.conversions() does, with VDD and the LSB taken from the run (LSB = VDD/16).
usage: spectre_analyze.py pvt|fine|enob|mim|noise|mm
All outputs go to results/gpdk180/ (gpdk180 results, not GF180).
"""
import sys, json, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "build/spectre/runs"
RES = ROOT / "results/gpdk180"


def load_raw(path):
    """Return (t, {name: array}) from a Spectre nutascii file."""
    with open(path) as f:
        lines = f.read().split("\n")
    starts = [k for k, l in enumerate(lines) if l.startswith("Plotname:")]
    lines = lines[starts[-1]:]          # Monte Carlo files hold a nominal plot first; use the last plot
    nv = npts = None
    names = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("No. Variables:"):
            nv = int(s.split(":")[1])
        elif s.startswith("No. Points:"):
            npts = int(s.split(":")[1])
        elif s.startswith("Variables:"):
            parts = s.split()
            names.append(parts[2])
            for k in range(nv - 1):
                i += 1
                names.append(lines[i].split()[1])
        elif s.startswith("Values:"):
            i += 1
            break
        i += 1
    data = np.array(" ".join(lines[i:]).split(), dtype=float)
    data = data[: (len(data) // (nv + 1)) * (nv + 1)].reshape(-1, nv + 1)[:, 1:]
    assert len(data) == npts, (len(data), npts)
    t = data[:, 0]
    return t, {n: data[:, k] for k, n in enumerate(names) if k > 0}


def at(t, y, tq):
    return np.interp(tq, t, y)


def conversions(t, s, vdd):
    """List of (t_eoc_end, code, vin_at_sample), one per end-of-conversion window (same rule as spicelib)."""
    thr = vdd / 2
    eoc = s["eoc"] > thr
    out = []
    i = 1
    while i < len(t):
        if eoc[i] and not eoc[i - 1]:
            j = i
            while j < len(t) and eoc[j]:
                j += 1
            te = t[j - 1] if j < len(t) else t[-1]
            tq = te - 1.0e-9
            code = sum(int(at(t, s[f"r{b}"], tq) > thr) << b for b in range(4))
            k = i
            while k > 0 and not (s["s0"][k] > thr and s["s0"][k - 1] <= thr):
                k -= 1
            m = k
            while m < len(t) and s["s0"][m] > thr:
                m += 1
            vin = at(t, s["vin"], t[m - 1] - 0.2e-9) if m <= len(t) else float("nan")
            out.append((te, code, vin))
            i = j
        else:
            i += 1
    return out


def rawpath(name):
    return RUNS / name / f"{name}.raw"


def run_conv(name, vdd):
    t, s = load_raw(rawpath(name))
    return conversions(t, s, vdd)


def ramp_metrics(name, vdd, n_steps):
    conv = run_conv(name, vdd)
    codes = np.array([c for _, c, _ in conv]); vin = np.array([v for _, _, v in conv])
    lsb = vdd / 16
    ideal = np.minimum(np.floor(vin / lsb).astype(int), 15)
    err = codes - ideal
    T = []
    for k in range(1, 16):
        above = np.nonzero(codes >= k)[0]
        if len(above) == 0:
            T.append(np.nan); continue
        i = above[0]
        T.append((vin[i] + vin[i - 1]) / 2 if i > 0 else vin[i])
    T = np.array(T)
    return {"conversions": int(len(codes)), "expected_steps": n_steps, "codes_seen": int(len(set(codes))),
            "monotonic": bool((np.diff(codes) >= 0).all()), "steps_with_code_error": int((err != 0).sum()),
            "max_abs_code_error_lsb": int(np.abs(err).max()),
            "dnl_max_abs_lsb": float(np.nanmax(np.abs(np.diff(T) / lsb - 1))),
            "inl_max_abs_lsb": float(np.nanmax(np.abs((T - np.arange(1, 16) * lsb) / lsb))),
            "estimate_resolution_lsb": float((vdd / n_steps) / lsb)}, codes, vin, T


def sndr(codes, cycles):
    n = len(codes); x = codes - codes.mean()
    X = np.abs(np.fft.rfft(x)) ** 2 / n ** 2
    sig = X[cycles]; X2 = X.copy(); X2[0] = 0; X2[cycles] = 0
    s = 10 * np.log10(sig / X2[1:].sum())
    return s, (s - 1.76) / 6.02, 10 * np.log10(sig / X2[1:].max())


def do_fine(prefix="fine", out="ramp256_typical.json", vdd=1.8):
    vin_all, codes_all = [], []
    for i in range(4):
        for _, c, v in run_conv(f"{prefix}_q{i}", vdd):
            codes_all.append(c); vin_all.append(v)
    vin = np.array(vin_all); codes = np.array(codes_all); lsb = vdd / 16
    T = []
    for k in range(1, 16):
        above = np.nonzero(codes >= k)[0]; i = above[0]; T.append((vin[i] + vin[i - 1]) / 2)
    T = np.array(T); dnl = np.diff(T) / lsb - 1; inl_abs = (T - np.arange(1, 16) * lsb) / lsb
    x = np.arange(1, 16); fit = np.polyval(np.polyfit(x, T / lsb, 1), x); inl_fit = T / lsb - fit
    m = {"pdk": "gpdk180", "tool": "Spectre", "vdd": vdd, "lsb_V": lsb, "steps": int(len(codes)),
         "monotonic": bool((np.diff(codes) >= 0).all()), "codes_seen": int(len(set(codes))), "resolution_lsb": 1 / 16,
         "transitions_V": T.tolist(), "dnl_lsb": dnl.tolist(), "inl_vs_ideal_lsb": inl_abs.tolist(),
         "inl_best_fit_lsb": inl_fit.tolist(), "dnl_max_abs": float(np.abs(dnl).max()),
         "inl_vs_ideal_max_abs": float(np.abs(inl_abs).max()), "inl_best_fit_max_abs": float(np.abs(inl_fit).max()),
         "offset_lsb_first_transition": float(inl_abs[0]), "gain_error_lsb_last_transition": float(inl_abs[-1])}
    print({k: v for k, v in m.items() if not isinstance(v, list)})
    (RES / out).write_text(json.dumps(m, indent=1))


def do_pvt():
    jobs = [("NN_27_1.8", "typical", 27, 1.8), ("FF_27_1.8", "ff", 27, 1.8), ("SS_27_1.8", "ss", 27, 1.8),
            ("FS_27_1.8", "fs", 27, 1.8), ("SF_27_1.8", "sf", 27, 1.8), ("NN_m40_1.8", "typical", -40, 1.8),
            ("NN_125_1.8", "typical", 125, 1.8), ("NN_27_1.62", "typical", 27, 1.62), ("NN_27_1.98", "typical", 27, 1.98),
            ("SS_125_1.62", "ss", 125, 1.62), ("FF_m40_1.98", "ff", -40, 1.98)]
    rows = []
    for name, c, temp, vdd in jobs:
        if not rawpath(name).exists():
            continue
        m, *_ = ramp_metrics(name, vdd, 64); rows.append({"corner": c, "temp_C": temp, "vdd": vdd, **m})
    (RES / "pvt_ramp64.json").write_text(json.dumps(rows, indent=1))
    md = ["| corner | T (C) | VDD (V) | conversions | codes seen | monotonic | steps with code error | max code error (LSB) | max abs DNL (LSB) | max abs INL (LSB) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['corner']} | {r['temp_C']} | {r['vdd']} | {r['conversions']} | {r['codes_seen']}/16 | "
                  f"{'yes' if r['monotonic'] else 'NO'} | {r['steps_with_code_error']} | {r['max_abs_code_error_lsb']} | "
                  f"{r['dnl_max_abs_lsb']:.3f} | {r['inl_max_abs_lsb']:.3f} |")
    (RES / "pvt_ramp64.md").write_text("\n".join(md) + "\n"); print("\n".join(md))


def do_enob(vdd=1.8):
    cycles, n = 13, 128
    codes = np.array([c for _, c, _ in run_conv("sine_13_128", vdd)])[:n].astype(float)
    sn, en, sf = sndr(codes, cycles)
    k = np.arange(n); ideals = []
    for p in np.linspace(0, 2 * np.pi, 361):
        v = vdd / 2 + 0.49 * vdd * np.sin(2 * np.pi * cycles * k / n + p)
        ideals.append(sndr(np.minimum(np.floor(v / (vdd / 16)), 15), cycles))
    ideal = np.array(ideals)
    out = {"pdk": "gpdk180", "tool": "Spectre", "samples": int(len(codes)), "cycles": cycles, "fs_MSps": 1 / 120e-9 / 1e6,
           "fin_MHz": cycles / (n * 120e-9) / 1e6, "SNDR_dB": float(sn), "ENOB": float(en), "SFDR_dB": float(sf),
           "ideal_4bit_SNDR_dB_mean": float(ideal[:, 0].mean()), "ideal_4bit_ENOB_mean": float(ideal[:, 1].mean()),
           "ideal_4bit_ENOB_min": float(ideal[:, 1].min()), "ideal_4bit_ENOB_max": float(ideal[:, 1].max()),
           "codes": codes.astype(int).tolist()}
    print({k: v for k, v in out.items() if k != "codes"}); (RES / "sine_enob.json").write_text(json.dumps(out, indent=1))


def do_mim(vdd=1.8):
    print("MIM caps, typical 27 C, 1.8 V, 256-step ramp"); do_fine("mimfine", "ramp256_typical_mim.json")
    rows = []
    for name, v in (("mim_ss_125_1.62", 1.62), ("mim_ff_m40_1.98", 1.98)):
        if rawpath(name).exists():
            m, *_ = ramp_metrics(name, v, 64); rows.append({"run": name, **m}); print(name, m)
    (RES / "pvt_ramp64_mim.json").write_text(json.dumps(rows, indent=1))


def do_noise(vdd=1.8):
    cycles, n = 13, 128
    rng = np.random.default_rng(1); k = np.arange(n); rows = []
    lsb = vdd / 16
    for s in (0.1, 0.5, 2, 5, 10, 20):
        if not rawpath(f"noise_{s}").exists():
            continue
        codes = np.array([c for _, c, _ in run_conv(f"noise_{s}", vdd)])[:n].astype(float)
        sn, en, sf = sndr(codes, cycles)
        ideal = []
        for _ in range(300):
            v = vdd / 2 + 0.49 * vdd * np.sin(2 * np.pi * cycles * k / n + rng.uniform(0, 6.283)) + rng.normal(0, s * 1e-3, n)
            ideal.append(sndr(np.clip(np.floor(v / lsb), 0, 15), cycles)[:2])
        ideal = np.array(ideal)
        rows.append({"noise_mV_rms": s, "noise_lsb_rms": s * 1e-3 / lsb, "SNDR_dB": float(sn), "ENOB": float(en),
                     "SFDR_dB": float(sf), "ideal_quantiser_with_same_noise_SNDR_dB": float(ideal[:, 0].mean()),
                     "ideal_quantiser_ENOB": float(ideal[:, 1].mean())})
    out = {"pdk": "gpdk180", "tool": "Spectre", "kTC_rms_mV_for_400fF": (1.380649e-23 * 300.15 / (16 * 25e-15)) ** 0.5 * 1e3,
           "rows": rows}
    print(json.dumps(out, indent=1)); (RES / "noise_sensitivity.json").write_text(json.dumps(out, indent=1))


def do_mm(vdd=1.8):
    rows = []
    for d in sorted(RUNS.glob("mm_*")):
        _, corner, seed = d.name.split("_")
        if not rawpath(d.name).exists():
            continue
        m, *_ = ramp_metrics(d.name, vdd, 64); rows.append({"corner": corner, "seed": int(seed), **m})
    (RES / "mismatch_converter_ramp64.json").write_text(json.dumps(rows, indent=1))
    md = ["| corner | seed | codes seen | monotonic | steps with code error | max code error (LSB) |", "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['corner']} | {r['seed']} | {r['codes_seen']}/16 | {'yes' if r['monotonic'] else 'NO'} | "
                  f"{r['steps_with_code_error']} | {r['max_abs_code_error_lsb']} |")
    (RES / "mismatch_converter_ramp64.md").write_text("\n".join(md) + "\n"); print("\n".join(md))


if __name__ == "__main__":
    RES.mkdir(parents=True, exist_ok=True)
    {"pvt": do_pvt, "fine": do_fine, "enob": do_enob, "mim": do_mim, "noise": do_noise, "mm": do_mm}[sys.argv[1]]()
