#!/usr/bin/env python3
"""Post-process the ngspice runs: transfer curve / DNL / INL, PVT table, sine-wave SNDR / ENOB,
and plots.  usage: analyze.py ramp|pvt|enob|plots"""
import sys, json, pathlib
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import spicelib as L

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build/spice"; RES = ROOT / "results"; RES.mkdir(exist_ok=True)


def ramp_metrics(path, vdd, n_steps):
    t, s = L.load(path)
    conv = L.conversions(t, s, thr=vdd / 2)
    codes = np.array([c for _, c, _ in conv]); vin = np.array([v for _, _, v in conv])
    lsb = vdd / 16
    ideal = np.minimum(np.floor(vin / lsb).astype(int), 15)
    err = codes - ideal
    # transition into code k: midpoint between the last step below k and the first step at or above k
    T = []
    for k in range(1, 16):
        above = np.nonzero(codes >= k)[0]
        if len(above) == 0: T.append(np.nan); continue
        i = above[0]
        T.append((vin[i] + vin[i - 1]) / 2 if i > 0 else vin[i])
    T = np.array(T)
    step_lsb = (vdd / n_steps) / lsb          # input step in LSB = resolution of the estimates
    return {"conversions": int(len(codes)), "expected_steps": n_steps,
            "codes_seen": int(len(set(codes))), "monotonic": bool((np.diff(codes) >= 0).all()),
            "steps_with_code_error": int((err != 0).sum()), "max_abs_code_error_lsb": int(np.abs(err).max()),
            "dnl_max_abs_lsb": float(np.nanmax(np.abs(np.diff(T) / lsb - 1))),
            "inl_max_abs_lsb": float(np.nanmax(np.abs((T - np.arange(1, 16) * lsb) / lsb))),
            "estimate_resolution_lsb": float(step_lsb)}, codes, vin, T


def do_ramp():
    m, codes, vin, T = ramp_metrics(BUILD / "adc_rampb.txt", 2.0, 128)
    print(json.dumps(m, indent=1)); (RES / "ramp128_typical.json").write_text(json.dumps(m | {"codes": codes.tolist(), "vin": vin.tolist(), "T": T.tolist()}, indent=1))


def do_fine(prefix="fine", out="ramp256_typical.json"):
    """256-step ramp (4 chunks of 64, 1/16 LSB per step): transition voltages, DNL and INL."""
    vin_all, codes_all = [], []
    for i in range(4):
        t, s = L.load(BUILD / f"runs/{prefix}_q{i}.txt")
        for _, c, v in L.conversions(t, s):
            codes_all.append(c); vin_all.append(v)
    vin = np.array(vin_all); codes = np.array(codes_all); lsb = 0.125
    T = []
    for k in range(1, 16):
        above = np.nonzero(codes >= k)[0]
        i = above[0]; T.append((vin[i] + vin[i - 1]) / 2)
    T = np.array(T); dnl = np.diff(T) / lsb - 1; inl_abs = (T - np.arange(1, 16) * lsb) / lsb
    # endpoint-fit INL (remove offset and gain error)
    x = np.arange(1, 16); fit = np.polyval(np.polyfit(x, T / lsb, 1), x); inl_fit = T / lsb - fit
    m = {"steps": int(len(codes)), "monotonic": bool((np.diff(codes) >= 0).all()), "codes_seen": int(len(set(codes))),
         "resolution_lsb": 1 / 16, "transitions_V": T.tolist(), "dnl_lsb": dnl.tolist(),
         "inl_vs_ideal_lsb": inl_abs.tolist(), "inl_best_fit_lsb": inl_fit.tolist(),
         "dnl_max_abs": float(np.abs(dnl).max()), "inl_vs_ideal_max_abs": float(np.abs(inl_abs).max()),
         "inl_best_fit_max_abs": float(np.abs(inl_fit).max()),
         "offset_lsb_first_transition": float(inl_abs[0]), "gain_error_lsb_last_transition": float(inl_abs[-1])}
    print({k: v for k, v in m.items() if not isinstance(v, list)}); (RES / out).write_text(json.dumps(m, indent=1))


def do_mim():
    print("MIM caps, typical 27 C, 2 V, 256-step ramp"); do_fine("mimfine", "ramp256_typical_mim.json")
    rows = []
    for name, vdd in (("mim_ss_125_1.8", 1.8), ("mim_ff_m40_2.2", 2.2)):
        m, *_ = ramp_metrics(BUILD / f"runs/{name}.txt", vdd, 64); rows.append({"run": name, **m}); print(name, m)
    (RES / "pvt_ramp64_mim.json").write_text(json.dumps(rows, indent=1))


def do_noise():
    cycles, n = 13, 128
    rng = np.random.default_rng(1); k = np.arange(n); rows = []
    for s in (0.1, 0.5, 2, 5, 10, 20):
        f = BUILD / f"runs/noise_{s}.txt"
        if not f.exists(): continue
        t, sg = L.load(f); codes = np.array([c for _, c, _ in L.conversions(t, sg)])[:n].astype(float)
        sn, en, sf, _ = sndr(codes, cycles)
        # same noise on an ideal 4-bit quantiser (no other error), averaged over 300 noise draws and phases
        ideal = []
        for _ in range(300):
            v = 1.0 + 0.98 * np.sin(2 * np.pi * cycles * k / n + rng.uniform(0, 6.283)) + rng.normal(0, s * 1e-3, n)
            ideal.append(sndr(np.clip(np.floor(v / 0.125), 0, 15), cycles)[:2])
        ideal = np.array(ideal)
        rows.append({"noise_mV_rms": s, "noise_lsb_rms": s * 1e-3 / 0.125, "SNDR_dB": float(sn), "ENOB": float(en), "SFDR_dB": float(sf),
                     "ideal_quantiser_with_same_noise_SNDR_dB": float(ideal[:, 0].mean()), "ideal_quantiser_ENOB": float(ideal[:, 1].mean())})
    kT_C = (1.380649e-23 * 300.15 / (16 * 25e-15)) ** 0.5
    out = {"kTC_rms_mV_for_400fF": kT_C * 1e3, "rows": rows}
    print(json.dumps(out, indent=1)); (RES / "noise_sensitivity.json").write_text(json.dumps(out, indent=1))


def do_mm():
    rows = []
    for f in sorted((BUILD / "runs").glob("mm_*.txt")):
        _, corner, seed = f.stem.split("_")
        m, *_ = ramp_metrics(f, 2.0, 64); rows.append({"corner": corner, "seed": int(seed), **m})
    (RES / "mismatch_converter_ramp64.json").write_text(json.dumps(rows, indent=1))
    md = ["| corner | seed | codes seen | monotonic | steps with code error | max code error (LSB) |", "|---|---|---|---|---|---|"]
    for r in rows: md.append(f"| {r['corner']} | {r['seed']} | {r['codes_seen']}/16 | {'yes' if r['monotonic'] else 'NO'} | {r['steps_with_code_error']} | {r['max_abs_code_error_lsb']} |")
    (RES / "mismatch_converter_ramp64.md").write_text("\n".join(md) + "\n"); print("\n".join(md))


def do_pvt():
    rows = []
    for f in sorted((BUILD / "runs").glob("*_*_*.txt")):
        name = f.stem
        if name.startswith("sine"): continue
        corner, temp, vdd = name.split("_"); temp = int(temp.replace("m", "-")); vdd = float(vdd)
        m, *_ = ramp_metrics(f, vdd, 64)
        rows.append({"corner": corner, "temp_C": temp, "vdd": vdd, **m})
    order = {"tt": 0, "ff": 1, "ss": 2, "fs": 3, "sf": 4}
    rows.sort(key=lambda r: (order[r["corner"]], r["temp_C"], r["vdd"]))
    (RES / "pvt_ramp64.json").write_text(json.dumps(rows, indent=1))
    md = ["| corner | T (C) | VDD (V) | conversions | codes seen | monotonic | steps with code error | max code error (LSB) | max abs DNL (LSB) | max abs INL (LSB) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['corner']} | {r['temp_C']} | {r['vdd']} | {r['conversions']} | {r['codes_seen']}/16 | {'yes' if r['monotonic'] else 'NO'} | {r['steps_with_code_error']} | {r['max_abs_code_error_lsb']} | {r['dnl_max_abs_lsb']:.3f} | {r['inl_max_abs_lsb']:.3f} |")
    (RES / "pvt_ramp64.md").write_text("\n".join(md) + "\n"); print("\n".join(md))


def sndr(codes, cycles):
    n = len(codes); x = codes - codes.mean()
    X = np.abs(np.fft.rfft(x)) ** 2 / n ** 2
    sig = X[cycles]; X2 = X.copy(); X2[0] = 0; X2[cycles] = 0
    spur = np.delete(X2, [])  # all remaining bins
    sndr = 10 * np.log10(sig / X2[1:].sum())
    sfdr = 10 * np.log10(sig / X2[1:].max())
    return sndr, (sndr - 1.76) / 6.02, sfdr, X


def do_enob():
    cycles, n = 13, 128
    t, s = L.load(BUILD / "runs/sine_13_128.txt")
    conv = L.conversions(t, s)
    codes = np.array([c for _, c, _ in conv])[:n].astype(float)
    sn, en, sf, X = sndr(codes, cycles)
    # ideal 4-bit quantiser on the same sine (same amplitude 0.49 VDD, offset VDD/2, same phase search)
    best = None
    k = np.arange(n); ph = np.linspace(0, 2 * np.pi, 361)
    ideals = []
    for p in ph:
        v = 1.0 + 0.98 * np.sin(2 * np.pi * cycles * k / n + p)
        ideals.append(sndr(np.minimum(np.floor(v / (2 / 16)), 15), cycles)[:3])
    ideal = np.array(ideals)
    out = {"samples": int(len(codes)), "cycles": cycles, "fs_MSps": 1 / 120e-9 / 1e6, "fin_MHz": cycles / (n * 120e-9) / 1e6,
           "SNDR_dB": float(sn), "ENOB": float(en), "SFDR_dB": float(sf),
           "ideal_4bit_SNDR_dB_mean": float(ideal[:, 0].mean()), "ideal_4bit_ENOB_mean": float(ideal[:, 1].mean()),
           "ideal_4bit_ENOB_min": float(ideal[:, 1].min()), "ideal_4bit_ENOB_max": float(ideal[:, 1].max()),
           "codes": codes.astype(int).tolist()}
    print({k: v for k, v in out.items() if k != "codes"}); (RES / "sine_enob.json").write_text(json.dumps(out, indent=1))


def do_plots():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    r = json.loads((RES / "ramp128_typical.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    ax[0].step(r["vin"], r["codes"], where="mid", label="ADC"); ax[0].plot(r["vin"], np.minimum(np.floor(np.array(r["vin"]) / 0.125), 15), "--", label="ideal")
    ax[0].set(xlabel="Vin (V)", ylabel="code", title="Transfer curve, 128-step ramp, typical 27 C"); ax[0].legend()
    T = np.array(r["T"]); lsb = 0.125
    ax[1].bar(range(1, 15), np.diff(T) / lsb - 1); ax[1].set(title="DNL (LSB)", xlabel="code"); ax[1].axhline(0.125, c="r", ls=":"); ax[1].axhline(-0.125, c="r", ls=":")
    ax[2].bar(range(1, 16), (T - np.arange(1, 16) * lsb) / lsb); ax[2].set(title="INL (LSB)", xlabel="code"); ax[2].axhline(0.125, c="r", ls=":"); ax[2].axhline(-0.125, c="r", ls=":")
    fig.tight_layout(); fig.savefig(RES / "ramp_dnl_inl.png", dpi=130)
    if (RES / "sine_enob.json").exists():
        e = json.loads((RES / "sine_enob.json").read_text()); c = np.array(e["codes"], float)
        X = np.abs(np.fft.rfft(c - c.mean())) ** 2; X = 10 * np.log10(X / X.max() + 1e-12)
        fig, ax = plt.subplots(1, 2, figsize=(11, 3.8)); ax[0].plot(c, ".-"); ax[0].set(title="Output codes, sine input", xlabel="sample")
        ax[1].bar(range(len(X)), np.maximum(X, -100) + 100, bottom=-100); ax[1].set(ylim=(-100, 5), title=f"Spectrum: SNDR {e['SNDR_dB']:.1f} dB, ENOB {e['ENOB']:.2f}", xlabel="bin", ylabel="dB rel. fundamental")
        fig.tight_layout(); fig.savefig(RES / "sine_spectrum.png", dpi=130)
    if (RES / "mc_comparator_offset.json").exists():
        m = json.loads((RES / "mc_comparator_offset.json").read_text()); o = np.array([x for x in m["offsets_V"] if x is not None]) * 1e3
        fig, ax = plt.subplots(figsize=(5.5, 3.8)); ax.hist(o, bins=20); ax.set(xlabel="input-referred offset (mV)", title=f"Comparator offset, {len(o)} seeds, sigma {o.std(ddof=1):.1f} mV")
        ax.axvline(62.5, c="r", ls=":"); ax.axvline(-62.5, c="r", ls=":"); fig.tight_layout(); fig.savefig(RES / "mc_comparator_offset.png", dpi=130)


if __name__ == "__main__":
    {"mim": do_mim, "noise": do_noise, "mm": do_mm, "fine": do_fine, "ramp": do_ramp, "pvt": do_pvt, "enob": do_enob, "plots": do_plots}[sys.argv[1]]()
