"""Transmission gate TGW (spice/adc_130b.sp: NMOS and PMOS, W = 8 um, L = 0.28 um) built from the
foundry's NMOS/PMOS generators. NMOS on the left, PMOS (in its n-well) on the right.

 x link : Metal2 bar over the top of both devices (two via1)
 y link : Metal1 bar below both devices
 en pad : below the NMOS gate; enb pad: above the PMOS gate
 taps   : P+ substrate tap left of the NMOS (pin vss), N+ well tap right of the PMOS (pin vdd)
Pins: x, y, en, enb, vss, vdd.   Run: python tgate.py  (rule subset + LVS, writes tgw.gds)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import pdkcells as p
import drc_lite, lvs_lite

U = 1000
W = 8.0
XP = 2.1          # x position of the PMOS


def build(w=W):
    ly = db.Layout(); ly.dbu = 0.001
    top = ly.create_cell("TGW")
    li = {k: ly.layer(*v) for k, v in drc_lite.LAYERS.items()}
    box = lambda layer, x0, y0, x1, y1: top.shapes(li[layer]).insert(
        db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))
    n = p.nmos(ly, w=w); pm = p.pmos(ly, w=w)
    top.insert(db.CellInstArray(n.cell_index(), db.Trans(0, 0)))
    top.insert(db.CellInstArray(pm.cell_index(), db.Trans(round(XP * U), 0)))

    # --- en pad below the NMOS gate
    box("poly", 0.44, -0.65, 0.72, -0.22)
    box("poly", 0.22, -1.25, 0.72, -0.65)
    box("contact", 0.29, -1.08, 0.51, -0.86)
    box("m1", 0.17, -1.15, 0.57, -0.75)
    # --- enb pad above the PMOS gate
    xg = XP
    box("poly", xg + 0.44, w + 0.22, xg + 0.72, w + 0.85)
    box("poly", xg + 0.22, w + 0.85, xg + 0.72, w + 1.45)
    box("contact", xg + 0.29, w + 1.02, xg + 0.51, w + 1.24)
    box("m1", xg + 0.17, w + 0.95, xg + 0.57, w + 1.35)
    # --- y link: Metal1 bar under both devices, joined to the right-hand strips (x 0.8..1.17)
    box("m1", 0.80, -0.80, 1.17, 0.0)
    box("m1", 0.80, -0.80, XP + 1.17, -0.40)
    box("m1", XP + 0.80, -0.80, XP + 1.17, 0.0)
    # --- x link: strips (left of each device) extended up, via1, Metal2 bar
    for x0 in (0.0, XP):
        box("m1", x0 - 0.04, w, x0 + 0.40, w + 0.56)
        box("via1", x0 + 0.06, w + 0.20, x0 + 0.32, w + 0.46)
    box("m2", 0.0, w + 0.14, XP + 0.38, w + 0.52)
    # --- substrate tap (left) and well tap (right)
    ym = w / 2
    box("comp", -1.10, ym - 0.25, -0.60, ym + 0.25); box("pplus", -1.26, ym - 0.41, -0.44, ym + 0.41)
    box("contact", -0.96, ym - 0.11, -0.74, ym + 0.11); box("m1", -1.10, ym - 0.25, -0.60, ym + 0.25)
    xt = XP + 1.66
    box("comp", xt, ym - 0.25, xt + 0.50, ym + 0.25); box("nplus", xt - 0.16, ym - 0.41, xt + 0.66, ym + 0.41)
    box("contact", xt + 0.14, ym - 0.11, xt + 0.36, ym + 0.11); box("m1", xt, ym - 0.25, xt + 0.50, ym + 0.25)
    box("nwell", XP - 0.43, -0.43, xt + 0.78, w + 0.43)
    top.flatten(True)
    pins = {"x": (0.19, ym), "y": (1.0, ym), "en": (0.37, -0.95), "enb": (XP + 0.37, w + 1.15),
            "vss": (-0.85, ym), "vdd": (xt + 0.25, ym)}
    return ly, top, pins


def reference(w=W):
    return lvs_lite.schematic("TGW", [("N", "x", "y", "en", w), ("P", "x", "y", "enb", w)], None)


def main():
    ly, top, pins = build()
    print("TGW: bbox", top.bbox())
    drc_lite.report(ly, top)
    ok = lvs_lite.compare(ly, top, reference(), "TGW", pins)
    ly.write(str(pathlib.Path(__file__).resolve().parent / "tgw.gds"))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
