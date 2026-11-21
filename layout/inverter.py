"""Inverter layout (INV in spice/cells.sp: W = 2 um, L = 0.28 um) built from the foundry's own
NMOS/PMOS generators, plus a gate contact, rails, and substrate / well taps.
Checks: rule subset (drc_lite) and layout-versus-schematic (lvs_lite). Writes inverter.gds.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import pdkcells as p
import drc_lite, lvs_lite

U = 1000
W = 2.0
TOPCELL = "INV"


def build(w=W):
    ly = db.Layout(); ly.dbu = 0.001
    top = ly.create_cell(TOPCELL)
    li = {k: ly.layer(*v) for k, v in drc_lite.LAYERS.items()}
    box = lambda layer, x0, y0, x1, y1: top.shapes(li[layer]).insert(db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))
    wu = round(w * U)

    yp = w + 0.96                                   # PMOS channel bottom
    n = p.nmos(ly, w=w); pm = p.pmos(ly, w=w)
    top.insert(db.CellInstArray(n.cell_index(), db.Trans(0, 0)))
    top.insert(db.CellInstArray(pm.cell_index(), db.Trans(0, round(yp * U))))

    ytop = yp + w
    # shared gate: one poly line through both devices, widened into a pad between them for the contact
    box("poly", 0.44, -0.22, 0.72, ytop + 0.22)
    box("poly", 0.22, w + 0.15, 0.72, w + 0.75)
    box("contact", 0.29, w + 0.32, 0.51, w + 0.54)
    box("m1", 0.17, w + 0.25, 0.57, w + 0.65)       # input pad "a"
    # output: join the two drain strips (x 0.8 .. 1.17)
    box("m1", 0.80, w - 0.01, 1.17, yp + 0.01)
    # rails and source straps
    box("m1", -0.01, -0.80, 2.45, -0.40)            # VSS
    box("m1", -0.01, -0.80, 0.37, 0.0)
    box("m1", -0.01, ytop + 0.40, 2.45, ytop + 0.80)   # VDD
    box("m1", -0.01, ytop, 0.37, ytop + 0.80)
    # substrate tap (P+ in p-substrate) on the VSS rail
    tx0 = 1.90
    box("comp", tx0, -0.85, tx0 + 0.50, -0.35); box("pplus", tx0 - 0.16, -1.01, tx0 + 0.66, -0.19)
    box("contact", tx0 + 0.14, -0.71, tx0 + 0.36, -0.49)
    # well tap (N+ in n-well) on the VDD rail
    ty = ytop + 0.38
    box("comp", tx0, ty, tx0 + 0.50, ty + 0.50); box("nplus", tx0 - 0.16, ty - 0.16, tx0 + 0.66, ty + 0.66)
    box("contact", tx0 + 0.14, ty + 0.14, tx0 + 0.36, ty + 0.36)
    box("nwell", -0.43, yp - 0.43, 2.70, ytop + 1.10)
    top.flatten(True)                                # flat cell: devices, wires and taps in one cell
    return ly, top


def main():
    ly, top = build()
    print("INV layout:", top.bbox())
    drc_lite.report(ly, top)
    ok = lvs_lite.compare_inverter(ly, top, w=W)
    ly.write(str(pathlib.Path(__file__).resolve().parent / "inverter.gds"))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
