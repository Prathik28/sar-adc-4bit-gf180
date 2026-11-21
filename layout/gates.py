"""NAND2 and NOR2 layouts (cells.sp: W = 2 um, L = 0.28 um) from the foundry's two-finger NMOS/PMOS
generators. Both rows share diffusion: strips L, M, R at x = 0, 0.8, 1.6 um, gates G1 (between L and M)
and G2 (between M and R).

 NAND2: NMOS series  L = vss, M = floating mid node, R = y   | PMOS parallel L = R = vdd, M = y
 NOR2 : NMOS parallel L = R = vss, M = y                     | PMOS series  L = vdd, M = floating, R = y
The output is joined between the rows with a short Metal2 jog. Pins: g1, g2, y, vss, vdd.
Run: python gates.py   (draws both, checks the rule subset and LVS, writes nand2.gds / nor2.gds)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import pdkcells as p
import drc_lite, lvs_lite

U = 1000
W = 2.0
GAP = 1.8


def build(kind, w=W):
    ly = db.Layout(); ly.dbu = 0.001
    top = ly.create_cell(kind)
    li = {k: ly.layer(*v) for k, v in drc_lite.LAYERS.items()}
    box = lambda layer, x0, y0, x1, y1: top.shapes(li[layer]).insert(
        db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))
    yp = w + GAP                                    # PMOS channel bottom
    ytop = yp + w
    n = p.nmos(ly, w=w, nf=2); pm = p.pmos(ly, w=w, nf=2)
    top.insert(db.CellInstArray(n.cell_index(), db.Trans(0, 0)))
    top.insert(db.CellInstArray(pm.cell_index(), db.Trans(0, round(yp * U))))
    # gate lines through both rows
    box("poly", 0.44, -0.22, 0.72, ytop + 0.22)
    box("poly", 1.24, -0.22, 1.52, ytop + 0.22)

    nand = kind == "NAND2"
    # gate pads: NAND in the lower part of the gap (the jog is in the upper part), NOR the other way round
    py = w + 0.25 if nand else yp - 0.65
    for x0 in (0.0, 0.8):                           # pad of G1 at x 0.22.., pad of G2 at x 1.02..
        box("poly", x0 + 0.22, py - 0.10, x0 + 0.72, py + 0.50)
        box("contact", x0 + 0.29, py + 0.07, x0 + 0.51, py + 0.29)
        box("m1", x0 + 0.17, py, x0 + 0.57, py + 0.40)
    # (the second pad is shifted by 0.8: G2 pad poly x 1.02..1.52, contact 1.09..1.31, Metal1 0.97..1.37)

    # rails and the strips that feed them
    box("m1", -0.01, -0.80, 2.90, -0.40)            # VSS rail
    box("m1", -0.01, ytop + 0.40, 2.90, ytop + 0.80)  # VDD rail
    box("m1", -0.01, -0.80, 0.37, 0.0)              # nmos L strip -> vss
    box("m1", -0.01, ytop, 0.37, ytop + 0.80)       # pmos L strip -> vdd
    if nand:
        box("m1", 1.60, ytop, 1.97, ytop + 0.80)    # pmos R strip -> vdd
    else:
        box("m1", 1.60, -0.80, 1.97, 0.0)           # nmos R strip -> vss
    # output jog (via1 + Metal2)
    if nand:
        yj = yp - 0.50
        box("m1", 1.60, w - 0.01, 1.97, yj + 0.19)         # nmos R strip extended up to the jog
        box("m1", 1.55, yj - 0.19, 2.02, yj + 0.19)
        box("m1", 0.74, yj - 0.19, 1.23, yp + 0.01)  # pmos M strip extended down
        box("via1", 1.655, yj - 0.13, 1.915, yj + 0.13)
        box("via1", 0.855, yj - 0.13, 1.115, yj + 0.13)
        box("m2", 0.795, yj - 0.19, 1.975, yj + 0.19)
        ypin = (1.78, 1.0)
    else:
        yj = w + 0.50
        box("m1", 0.74, w - 0.01, 1.23, yj + 0.19)   # nmos M strip extended up
        box("m1", 1.60, yj - 0.19, 1.97, yp + 0.01)  # pmos R strip extended down
        box("m1", 1.55, yj - 0.19, 2.02, yj + 0.19)
        box("via1", 1.655, yj - 0.13, 1.915, yj + 0.13)
        box("via1", 0.855, yj - 0.13, 1.115, yj + 0.13)
        box("m2", 0.795, yj - 0.19, 1.975, yj + 0.19)
        ypin = (0.98, 1.0)
    # taps on the rails
    tx0 = 3.10
    box("comp", tx0, -0.85, tx0 + 0.50, -0.35); box("pplus", tx0 - 0.16, -1.01, tx0 + 0.66, -0.19)
    box("contact", tx0 + 0.14, -0.71, tx0 + 0.36, -0.49)
    ty = ytop + 0.38
    box("comp", tx0, ty, tx0 + 0.50, ty + 0.50); box("nplus", tx0 - 0.16, ty - 0.16, tx0 + 0.66, ty + 0.66)
    box("contact", tx0 + 0.14, ty + 0.14, tx0 + 0.36, ty + 0.36)
    box("m1", 2.90, -0.80, tx0 + 0.55, -0.40)
    box("m1", 2.90, ytop + 0.40, tx0 + 0.55, ytop + 0.80)
    box("nwell", -0.43, yp - 0.43, tx0 + 0.85, ytop + 1.10)
    top.flatten(True)
    pins = {"g1": (0.37, py + 0.2), "g2": (1.17, py + 0.2), "y": ypin, "vss": (1.0, -0.6), "vdd": (1.0, ytop + 0.6)}
    return ly, top, pins


def reference(kind, w=W):
    if kind == "NAND2":
        dev = [("N", "vss", "n1", "g1", w), ("N", "n1", "y", "g2", w),
               ("P", "vdd", "y", "g1", w), ("P", "vdd", "y", "g2", w)]
    else:
        dev = [("N", "vss", "y", "g1", w), ("N", "vss", "y", "g2", w),
               ("P", "vdd", "n1", "g1", w), ("P", "n1", "y", "g2", w)]
    return lvs_lite.schematic(kind, dev, None)


def check(kind):
    ly, top, pins = build(kind)
    print(f"{kind}: bbox {top.bbox()}")
    drc_lite.report(ly, top)
    ok = lvs_lite.compare(ly, top, reference(kind), kind, pins)
    ly.write(str(pathlib.Path(__file__).resolve().parent / f"{kind.lower()}.gds"))
    return ok


if __name__ == "__main__":
    results = [check(k) for k in ("NAND2", "NOR2")]
    sys.exit(0 if all(results) else 1)
