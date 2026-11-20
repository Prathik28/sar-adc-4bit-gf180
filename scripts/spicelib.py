"""Helpers to read ngspice wrdata output and decode SAR ADC conversions."""
import numpy as np

SIGNALS = "clk vin top comp q0 q1 q2 setb3 setb2 setb1 setb0 eoc r3 r2 r1 r0 dac3 dac2 dac1 dac0 outp outn s0 pht".split()
VDD = 2.0


def load(path, names=SIGNALS):
    """wrdata writes (time, value) column pairs, one pair per vector."""
    a = np.loadtxt(path)
    t = a[:, 0]
    return t, {n: a[:, 2 * i + 1] for i, n in enumerate(names)}


def at(t, y, tq):
    return np.interp(tq, t, y)


def conversions(t, s, thr=VDD / 2):
    """Return a list of (t_eoc_end, code, vin_at_sample) -- one per end-of-conversion window.
    The code is read from the SAR register just before EOC (S5) ends."""
    eoc = s["eoc"] > thr
    out = []
    i = 1
    while i < len(t):
        if eoc[i] and not eoc[i - 1]:
            j = i
            while j < len(t) and eoc[j]:
                j += 1
            te = t[j - 1] if j < len(t) else t[-1]
            tq = te - 1.0e-9          # 1 ns before the end of S5
            code = sum(int(at(t, s[f"r{b}"], tq) > thr) << b for b in range(4))
            # input voltage held during the preceding S0 (sampled on the falling edge of S0)
            k = i
            while k > 0 and not (s["s0"][k] > thr and s["s0"][k - 1] <= thr):
                k -= 1
            # vin at the end of the S0 window (just before s0 falls)
            m = k
            while m < len(t) and s["s0"][m] > thr:
                m += 1
            vin = at(t, s["vin"], t[m - 1] - 0.2e-9) if m <= len(t) else float("nan")
            out.append((te, code, vin))
            i = j
        else:
            i += 1
    return out
