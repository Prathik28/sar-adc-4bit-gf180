"""Capacitor DAC as a single row of 16 identical unit capacitors (same foundry MIM generator and unit cell as
caparray.py), ordered B3 x8, B2 x4, B1 x2, B0, BT, so that every bottom-plate group touches the lower edge and
can be wired straight down to the analog block. Metal3 bridges join the plates of a group; Metal4 straps join all
top plates, and one Metal4 stub brings the top net down to the lower edge.
Pins (x, y) are returned for the top level: bottoms start on the plate's Metal3 (level 'm3'), the top net on a via3.
Run: python caprow.py  (structure and metal-spacing checks, writes caprow.gds)
"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import pdkcells as p

U = 1000
S = 3.31
PITCH = 4.9
M3, M4, FUSE = (42, 0), (46, 0), (75, 0)
ORDER = ["B3"] * 8 + ["B2"] * 4 + ["B1"] * 2 + ["B0", "BT"]
EXPECT = {"B0": 1, "B1": 2, "B2": 4, "B3": 8, "BT": 1}
UNIT_FF = 24.959


def build():
    ly = db.Layout(); ly.dbu = 0.001
    top = ly.create_cell("CAPROW")
    unit = p.mimcap(ly, S, "M4")
    l3, l4, lv3 = ly.layer(*M3), ly.layer(*M4), ly.layer(40, 0)
    box = lambda l, x0, y0, x1, y1: top.shapes(l).insert(db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))
    for c, bit in enumerate(ORDER):
        top.insert(db.CellInstArray(unit.cell_index(), db.Trans(round(c * PITCH * U), 0)))
    for c in range(15):
        x = c * PITCH
        box(l4, x + S - 0.1, 1.0, x + PITCH + 0.1, 2.3)                        # top plates joined
        if ORDER[c] == ORDER[c + 1]:
            box(l3, x + S + 0.5, 0.5, x + PITCH - 0.5 + 0.2, 2.8)              # same group: Metal3 bridge
    # top-net stub: between plates 0 and 1, down below the plates, via3 + Metal3 pad
    xs = S + (PITCH - S) / 2 - 0.0                                              # centre of the gap between plates 0 and 1 (x = 4.105)
    box(l4, xs - 0.19, -1.39, xs + 0.19, 2.3)
    box(lv3, xs - 0.13, -1.32, xs + 0.13, -1.06); box(l3, xs - 0.19, -1.39, xs + 0.19, -0.99)
    top.flatten(True)
    # pins: one per bottom group (centre of its first plate's lower edge) and the top net
    pins = {}
    seen = set()
    for c, bit in enumerate(ORDER):
        if bit not in seen:
            seen.add(bit)
            pins[bit] = dict(x=c * PITCH + (S + 1.2) / 2 - 0.6, y=-0.6, level="m3")
    pins["top"] = dict(x=xs, y=-1.2, level="via3")
    return ly, top, pins


def analyse(ly, top):
    l3, l4, lf = (db.Region(top.begin_shapes_rec(ly.layer(*L))) for L in (M3, M4, FUSE))
    for r in (l3, l4): r.merge()
    lfm = lf.merged()
    um = 1000
    per_poly = [sum(1 for f in lfm.each() if db.Region(poly).interacting(db.Region(f)).count()) for poly in l3.each()]
    units = sorted(n for n in per_poly if n)                       # plates; the one polygon without a plate is the top-net stub pad
    stub_pads = sum(1 for n in per_poly if not n)
    checks = {"bottom nets have 8/4/2/1/1 units": units == sorted(EXPECT.values()), "single top net": l4.count() == 1, "one stub pad": stub_pads == 1,
              "M3 width >= 0.28": l3.width_check(round(0.28 * um)).polygons().count() == 0,
              "M3 space >= 0.28": l3.space_check(round(0.28 * um)).polygons().count() == 0,
              "M4 width >= 0.28": l4.width_check(round(0.28 * um)).polygons().count() == 0,
              "M4 space >= 0.28": l4.space_check(round(0.28 * um)).polygons().count() == 0}
    return dict(unit_cells=lfm.count(), bottom_nets_units=units, top_net_polygons=l4.count(), checks=checks,
                size_um=[round(top.bbox().width() / U, 2), round(top.bbox().height() / U, 2)], total_fF=round(16 * UNIT_FF, 1))


if __name__ == "__main__":
    ly, top, pins = build()
    res = analyse(ly, top)
    print(json.dumps(res, indent=1))
    ly.write(str(pathlib.Path(__file__).resolve().parent / "caprow.gds"))
    sys.exit(0 if all(res["checks"].values()) else 1)
