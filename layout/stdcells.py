"""Standard-height cells for the digital core: INV, NAND2, NOR2 and TG (W = 2 um, L = 0.28 um, as in
spice/cells.sp). All cells have NMOS row y = 0..2, PMOS row y = 3.8..5.8, and the Metal1 supply rails at
y = -0.8..-0.4 (vss) and 6.2..6.6 (vdd), which the row builder draws continuously. The n-well, the nplus /
pplus bands and the substrate / well taps are also drawn by the row builder (see router.py).

Each cell is a list of (layer, x0, y0, x1, y1) boxes in um, a list of device placements, and a pin table:
  pins[name] = dict(level='m1'|'m2', x, y)   -> where the via stack to Metal3 starts (centre)
  probe[name] = (x, y)                       -> a Metal1 point on the net (for LVS pin hints)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

W = 2.0
YP = 3.8            # PMOS channel bottom
YTOP = YP + W


def _pad(boxes, x0, y0):
    """gate pad: poly pad 0.5 x 0.6, contact, 0.4 x 0.4 Metal1 pad; (x0, y0) = lower-left of the Metal1 pad"""
    boxes += [("poly", x0 + 0.05, y0 - 0.10, x0 + 0.55, y0 + 0.50),
              ("contact", x0 + 0.12, y0 + 0.07, x0 + 0.34, y0 + 0.29),
              ("m1", x0, y0, x0 + 0.40, y0 + 0.40)]


def inv():
    b, dev, pins, probe = [], [("n", 0, 0, 1), ("p", 0, YP, 1)], {}, {}
    b += [("poly", 0.44, -0.22, 0.72, YTOP + 0.22)]
    _pad(b, 0.17, 2.25)
    b += [("m1", 0.80, W - 0.01, 1.17, YP + 0.01), ("m1", 0.80, 3.10, 1.20, 3.50)]       # drain bridge + pin pad
    b += [("m1", -0.01, -0.80, 0.37, 0.0), ("m1", -0.01, YTOP, 0.37, 6.60)]             # source straps to the rails
    pins["a"] = dict(level="m1", x=0.37, y=2.45); probe["a"] = (0.37, 2.45)
    pins["y"] = dict(level="m1", x=1.00, y=3.30); probe["y"] = (1.0, 3.30)
    return dict(boxes=b, devices=dev, pins=pins, probe=probe, x0=-0.17, x1=1.32, pitch=1.9, nets={"a": "a", "y": "y"})


def _two_finger(kind):
    nand = kind == "NAND2"
    b, dev, pins, probe = [], [("n", 0, 0, 2), ("p", 0, YP, 2)], {}, {}
    b += [("poly", 0.44, -0.22, 0.72, YTOP + 0.22), ("poly", 1.24, -0.22, 1.52, YTOP + 0.22)]
    py = W + 0.25 if nand else YP - 0.65                # gate pads: lower zone for NAND2, upper zone for NOR2
    _pad(b, 0.17, py)
    _pad(b, 0.97, py)
    b += [("m1", -0.01, -0.80, 0.37, 0.0), ("m1", -0.01, YTOP, 0.37, 6.60)]
    if nand:
        yj = YP - 0.50
        b += [("m1", 1.60, 1.99, 1.97, yj + 0.19), ("m1", 1.55, yj - 0.19, 2.02, yj + 0.19), ("m1", 0.74, yj - 0.19, 1.23, YP + 0.01),
              ("m1", 1.60, YTOP, 1.97, 6.60)]
    else:
        yj = W + 0.50
        b += [("m1", 0.74, W - 0.01, 1.23, yj + 0.19), ("m1", 1.60, yj - 0.19, 1.97, YP + 0.01), ("m1", 1.55, yj - 0.19, 2.02, yj + 0.19),
              ("m1", 1.60, -0.80, 1.97, 0.0)]
    b += [("via1", 1.655, yj - 0.13, 1.915, yj + 0.13), ("via1", 0.855, yj - 0.13, 1.115, yj + 0.13), ("m2", 0.795, yj - 0.19, 2.10, yj + 0.19)]
    pins["a"] = dict(level="m1", x=0.37, y=py + 0.2); probe["a"] = (0.37, py + 0.2)
    pins["b"] = dict(level="m1", x=1.17, y=py + 0.2); probe["b"] = (1.17, py + 0.2)
    pins["y"] = dict(level="m2", x=1.85, y=yj); probe["y"] = (1.78, W - 0.5 if nand else YP + 0.5)
    return dict(boxes=b, devices=dev, pins=pins, probe=probe, x0=-0.17, x1=2.12, pitch=2.7, nets={})


def nand2():
    return _two_finger("NAND2")


def nor2():
    return _two_finger("NOR2")


def tg():
    """stacked transmission gate: NMOS below, PMOS above, x link on the left strips, y link on the right strips;
    en pad to the left, enb pad to the right (poly runs under the bars)"""
    b, dev, pins, probe = [], [("n", 0, 0, 1), ("p", 0, YP, 1)], {}, {}
    b += [("poly", 0.44, -0.22, 0.72, 2.22),                     # NMOS gate (en)
          ("poly", 0.44, 2.22, 0.72, 2.80), ("poly", -0.80, 2.30, 0.72, 2.80),
          ("contact", -0.59, 2.45, -0.37, 2.67), ("m1", -0.68, 2.38, -0.28, 2.78),
          ("poly", 0.44, YP - 0.22, 0.72, YTOP + 0.22),          # PMOS gate (enb)
          ("poly", 0.44, 3.17, 0.72, YP - 0.22), ("poly", 0.44, 3.17, 1.92, 3.67),
          ("contact", 1.49, 3.37, 1.71, 3.59), ("m1", 1.43, 3.30, 1.83, 3.70)]
    b += [("m1", -0.01, W - 0.01, 0.37, YP + 0.01),               # x link
          ("m1", 0.80, W - 0.01, 1.17, YP + 0.01), ("m1", 0.78, 2.80, 1.18, 3.20)]   # y link + pin pad
    pins["x"] = dict(level="m1", x=0.18, y=3.0); probe["x"] = (0.18, 3.0)
    pins["y"] = dict(level="m1", x=0.98, y=3.0); probe["y"] = (0.98, 3.0)
    pins["en"] = dict(level="m1", x=-0.48, y=2.58); probe["en"] = (-0.48, 2.58)
    pins["enb"] = dict(level="m1", x=1.63, y=3.50); probe["enb"] = (1.63, 3.50)
    return dict(boxes=b, devices=dev, pins=pins, probe=probe, x0=-0.96, x1=2.08, pitch=3.3, nets={})


CELLS = {"INV": inv, "NAND2": nand2, "NOR2": nor2, "TG": tg}
