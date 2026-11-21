"""Cells for the analog block: single transistors of any width (comparator, DAC switches) and the 8 um
sampling transmission gate. Every cell carries its own substrate or well tap and exposes its pins on Metal1 pads
(the router adds the via stacks). Pin x positions are at least 0.66 um apart so the Metal3 wires never touch.
Same box-list format as stdcells.py."""

def dev(typ, w):
    """one NMOS or PMOS (L = 0.28 um): pins S (left strip), D (right strip), G, B (own tap)"""
    b, pins, probe = [], {}, {}
    t = w + 0.22
    b += [("poly", 0.44, -0.22, 0.72, t)]
    # gate: poly goes up and to the right, pad at x 1.5 .. 1.9
    b += [("poly", 0.44, t, 0.72, w + 0.65), ("poly", 0.44, w + 0.15, 1.95, w + 0.65 + 0.0), ("poly", 1.45, w + 0.15, 1.95, w + 0.75),
          ("contact", 1.59, w + 0.32, 1.81, w + 0.54), ("m1", 1.50, w + 0.25, 1.90, w + 0.65)]
    # S / D pads on top of the strips
    b += [("m1", -0.03, w - 0.01, 0.37, w + 0.45), ("m1", 0.78, w - 0.01, 1.18, w + 0.45)]
    # tap
    if typ == "n":
        b += [("comp", 2.30, 0.50, 2.80, 1.00), ("pplus", 2.14, 0.34, 2.96, 1.16), ("contact", 2.44, 0.64, 2.66, 0.86), ("m1", 2.30, 0.50, 2.80, 1.00)]
        x0, x1 = -0.17, 2.96
    else:
        b += [("comp", 2.30, 0.50, 2.80, 1.00), ("nplus", 2.14, 0.34, 2.96, 1.16), ("contact", 2.44, 0.64, 2.66, 0.86), ("m1", 2.30, 0.50, 2.80, 1.00),
              ("nwell", -0.43, -0.43, 3.30, w + 0.43)]
        x0, x1 = -0.43, 3.30
    pins["S"] = dict(level="m1", x=0.17, y=w + 0.25); probe["S"] = (0.17, w + 0.25)
    pins["D"] = dict(level="m1", x=0.98, y=w + 0.25); probe["D"] = (0.98, w + 0.25)
    pins["G"] = dict(level="m1", x=1.70, y=w + 0.45); probe["G"] = (1.70, w + 0.45)
    pins["B"] = dict(level="m1", x=2.55, y=0.75); probe["B"] = (2.55, 0.75)
    return dict(boxes=b, devices=[(typ, 0, 0, 1, w)], pins=pins, probe=probe, x0=x0, x1=x1)


def tgw(w=8.0):
    """transmission gate, NMOS left, PMOS right in its own n-well. x link on Metal2 over the top, y link on Metal1 below.
    en pad bottom-left, enb pad top (above the PMOS gate), well tap then substrate tap on the right."""
    XP = 2.1
    b = []
    # en pad: bottom left
    b += [("poly", 0.44, -0.65, 0.72, -0.22), ("poly", -0.80, -1.25, 0.72, -0.65),
          ("contact", -0.59, -1.08, -0.37, -0.86), ("m1", -0.68, -1.15, -0.28, -0.75)]
    # enb pad above the PMOS gate
    b += [("poly", XP + 0.44, w + 0.22, XP + 0.72, w + 0.85), ("poly", XP + 0.22, w + 0.85, XP + 0.72, w + 1.45),
          ("contact", XP + 0.29, w + 1.02, XP + 0.51, w + 1.24), ("m1", XP + 0.17, w + 0.95, XP + 0.57, w + 1.35)]
    # y link (Metal1 under both devices)
    b += [("m1", 0.80, -0.80, 1.17, 0.0), ("m1", 0.80, -0.80, XP + 1.17, -0.40), ("m1", XP + 0.80, -0.80, XP + 1.17, 0.0)]
    # x link (strips extended up, via1, Metal2 bar)
    for x0 in (0.0, XP):
        b += [("m1", x0 - 0.04, w, x0 + 0.40, w + 0.56), ("via1", x0 + 0.06, w + 0.20, x0 + 0.32, w + 0.46)]
    b += [("m2", 0.0, w + 0.14, XP + 0.38, w + 0.52)]
    ym = w / 2
    b += [("m1", -0.03, ym - 0.2, 0.37, ym + 0.2), ("m1", 0.78, ym - 0.2, 1.18, ym + 0.2)]     # via landing pads on the x / y strips
    # n-well, well tap (right of the PMOS), substrate tap (further right, outside the well)
    xt = XP + 1.66
    b += [("comp", xt, ym - 0.25, xt + 0.50, ym + 0.25), ("nplus", xt - 0.16, ym - 0.41, xt + 0.66, ym + 0.41),
          ("contact", xt + 0.14, ym - 0.11, xt + 0.36, ym + 0.11), ("m1", xt, ym - 0.25, xt + 0.50, ym + 0.25),
          ("nwell", XP - 0.43, -0.43, xt + 0.78, w + 0.43)]
    xs = xt + 1.35
    b += [("comp", xs, ym - 0.25, xs + 0.50, ym + 0.25), ("pplus", xs - 0.16, ym - 0.41, xs + 0.66, ym + 0.41),
          ("contact", xs + 0.14, ym - 0.11, xs + 0.36, ym + 0.11), ("m1", xs, ym - 0.25, xs + 0.50, ym + 0.25)]
    pins = dict(x=dict(level="m1", x=0.17, y=ym), y=dict(level="m1", x=0.98, y=ym), en=dict(level="m1", x=-0.48, y=-0.95),
                enb=dict(level="m1", x=XP + 0.37, y=w + 1.15), vdd=dict(level="m1", x=xt + 0.25, y=ym), vss=dict(level="m1", x=xs + 0.25, y=ym))
    probe = {k: (v["x"], v["y"]) for k, v in pins.items()}
    return dict(boxes=b, devices=[("n", 0, 0, 1, w), ("p", XP, 0, 1, w)], pins=pins, probe=probe, x0=-0.96, x1=xs + 0.68)
