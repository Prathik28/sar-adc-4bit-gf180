"""Capacitor DAC array: 16 identical unit capacitors (foundry MIM generator, 3.31 um square, 25 fF in the
model) in a 4 x 4 grid. Bits are grouped by row and joined with Metal3 (bottom plates):

    row 3 (top):    B3 B3 B3 B3      B3 = 8 units (rows 2 and 3 joined at the left)
    row 2:          B3 B3 B3 B3
    row 1:          B2 B2 B2 B2      B2 = 4 units
    row 0 (bottom): B1 B1 B0 BT      B1 = 2 units, B0 = 1 unit, BT = 1 dummy unit (CT in the schematic)

All top plates are tied together with Metal4 straps (net "top"). Unit cells make the ratios exact by
construction (the PDK model's capacitance is not proportional to area: see results/layout_cap_shapes.json).
Checks: net structure (unit count per bottom net, one top net), Metal3 / Metal4 width and space.
Not included: dummy ring, parasitics from routing, matching beyond the grouping.
Run: python caparray.py   (writes caparray.gds and caparray_layout.png)
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import pdkcells as p

U = 1000
S = 3.31                     # top plate side
PITCH = 4.9                  # plate-to-plate pitch: M3 plates are S + 1.2 wide, so the gap is 0.39 um
UNIT_FF = 24.959             # measured with ngspice on mimcap_typical (3.31 x 3.31 um)
M3, M4, FUSE = (42, 0), (46, 0), (75, 0)
GRID = [["B1", "B1", "B0", "BT"], ["B2"] * 4, ["B3"] * 4, ["B3"] * 4]   # rows from the bottom
EXPECT = {"B0": 1, "B1": 2, "B2": 4, "B3": 8, "BT": 1}


def build():
    ly = db.Layout(); ly.dbu = 0.001
    top = ly.create_cell("CAPARRAY")
    unit = p.mimcap(ly, S, "M4")
    l3, l4 = ly.layer(*M3), ly.layer(*M4)
    box = lambda l, x0, y0, x1, y1: top.shapes(l).insert(db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))
    for r, row in enumerate(GRID):
        for c, bit in enumerate(row):
            top.insert(db.CellInstArray(unit.cell_index(), db.Trans(round(c * PITCH * U), round(r * PITCH * U))))
    for r, row in enumerate(GRID):
        y = r * PITCH
        for c in range(4):
            x = c * PITCH
            if c < 3:
                box(l4, x + S - 0.1, y + 1.0, x + PITCH + 0.1, y + 2.3)             # top plates, Metal4 strap to the right
                if row[c] == row[c + 1]:
                    box(l3, x + S + 0.5, y + 0.5, x + PITCH - 0.5 + 0.2, y + 2.8)   # same bit: Metal3 bridge to the right
            if r < 3:
                box(l4, x + 1.0, y + S - 0.1, x + 2.3, y + PITCH + 0.1)             # Metal4 strap upwards
    box(l3, 0.5, 2 * PITCH + S + 0.5, 2.8, 3 * PITCH - 0.5 + 0.2)                   # join B3 rows 2 and 3 at the left
    top.flatten(True)
    return ly, top


def analyse(ly, top):
    l3, l4, lf = (db.Region(top.begin_shapes_rec(ly.layer(*L))) for L in (M3, M4, FUSE))
    for r in (l3, l4): r.merge()
    um = 1000
    res = {"unit_cells": lf.merged().count(), "checks": {}}
    # bottom nets: merged Metal3 polygons; count the unit top plates (fusetop boxes) inside each
    groups = []
    for poly in l3.each():
        n = sum(1 for f in lf.merged().each() if db.Region(poly).interacting(db.Region(f)).count())
        groups.append((n, poly.bbox()))
    groups.sort(key=lambda g: (g[1].bottom, g[1].left))
    res["bottom_nets_units"] = sorted(n for n, _ in groups)
    ok_nets = res["bottom_nets_units"] == sorted(EXPECT.values())
    res["top_net_polygons"] = l4.count()
    ok_top = l4.count() == 1
    w3 = l3.width_check(round(0.28 * um)).polygons().count(); s3 = l3.space_check(round(0.28 * um)).polygons().count()
    w4 = l4.width_check(round(0.28 * um)).polygons().count(); s4 = l4.space_check(round(0.28 * um)).polygons().count()
    res["checks"] = {"bottom nets have 8/4/2/1/1 units": ok_nets, "single top net": ok_top,
                     "M3 width >= 0.28": w3 == 0, "M3 space >= 0.28": s3 == 0, "M4 width >= 0.28": w4 == 0, "M4 space >= 0.28": s4 == 0}
    nets = {}
    for bit, n in EXPECT.items():
        nets[bit] = {"units": n, "C_fF": round(n * UNIT_FF, 2)}
    res["capacitance_model_fF"] = nets
    res["total_fF"] = round(16 * UNIT_FF, 1)
    res["array_size_um"] = [round(ly.top_cell().bbox().width() / U, 2), round(ly.top_cell().bbox().height() / U, 2)]
    return res


def main():
    ly, top = build()
    res = analyse(ly, top)
    print(json.dumps(res, indent=1))
    here = pathlib.Path(__file__).resolve().parent
    ly.write(str(here / "caparray.gds"))
    (here.parent / "results" / "layout_caparray.json").write_text(json.dumps(res, indent=1))
    return all(res["checks"].values())


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
