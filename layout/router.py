"""Row placer and router for the digital core.

* one row of standard cells (stdcells.py) with continuous Metal1 rails, one n-well, nplus / pplus bands
  and a substrate / well tap pair every TAP_EVERY um
* every signal net gets its own Metal4 track above the row; each pin reaches it through a via stack
  (via1 -> Metal2 pad -> via2 -> Metal3 pad) and a Metal3 vertical wire, then via3 to the trunk
Pitches are conservative (0.7 um between tracks) so that no design rule needs a special case.
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import pdkcells as p
import drc_lite, lvs_lite, stdcells

U = 1000
GAP_X = 0.45          # extra space between cells
TAP_EVERY = 16.0
TRACK0 = 7.8
TRACK_PITCH = 0.70
LAYER = dict(drc_lite.LAYERS)


class Row:
    def __init__(self):
        self.ly = db.Layout(); self.ly.dbu = 0.001
        self.top = self.ly.create_cell("DIGCORE")
        self.li = {k: self.ly.layer(*v) for k, v in LAYER.items()}
        self.pc = {("n", 1): p.nmos(self.ly, w=stdcells.W, nf=1), ("n", 2): p.nmos(self.ly, w=stdcells.W, nf=2),
                   ("p", 1): p.pmos(self.ly, w=stdcells.W, nf=1), ("p", 2): p.pmos(self.ly, w=stdcells.W, nf=2)}
        self.cursor = 0.0
        self.runs = []            # [x_start, x_end] of device runs between taps
        self.taps = []
        self.placed = []          # (path, kind, ox, cell)
        self.run_start = None

    def box(self, layer, x0, y0, x1, y1):
        self.top.shapes(self.li[layer]).insert(db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))

    def place_tap(self):
        ox = self.cursor + 0.16 + 0.5
        if self.run_start is not None:
            self.runs.append([self.run_start, self.cursor]); self.run_start = None
        self.box("comp", ox, -0.85, ox + 0.5, -0.35); self.box("pplus", ox - 0.16, -1.01, ox + 0.66, -0.19)
        self.box("contact", ox + 0.14, -0.71, ox + 0.36, -0.49)
        ty = stdcells.YTOP + 0.38
        self.box("comp", ox, ty, ox + 0.5, ty + 0.5); self.box("nplus", ox - 0.16, ty - 0.16, ox + 0.66, ty + 0.66)
        self.box("contact", ox + 0.14, ty + 0.14, ox + 0.36, ty + 0.36)
        self.taps.append(ox)
        self.cursor = ox + 0.66 + 0.5

    def place(self, path, kind, cell):
        if self.run_start is None:
            self.run_start = self.cursor
        ox = self.cursor - cell["x0"]
        for layer, x0, y0, x1, y1 in cell["boxes"]:
            self.box(layer, ox + x0, y0, ox + x1, y1)
        for typ, dx, dy, nf in cell["devices"]:
            self.top.insert(db.CellInstArray(self.pc[(typ, nf)].cell_index(), db.Trans(round((ox + dx) * U), round(dy * U))))
        self.placed.append((path, kind, ox, cell))
        self.cursor = ox + cell["x1"] + GAP_X

    def finish_row(self):
        if self.run_start is not None:
            self.runs.append([self.run_start, self.cursor - GAP_X]); self.run_start = None
        x0, x1 = min(r[0] for r in self.runs) - 0.3, max(r[1] for r in self.runs) + 0.3
        self.x0 = min(x0, min(t - 0.16 for t in self.taps) - 0.3); self.x1 = max(x1, max(t + 0.66 for t in self.taps) + 0.3)
        self.box("m1", self.x0, -0.80, self.x1, -0.40)                  # vss rail
        self.box("m1", self.x0, stdcells.YTOP + 0.40, self.x1, stdcells.YTOP + 0.80)   # vdd rail
        self.box("nwell", self.x0, stdcells.YP - 0.43, self.x1, 7.0)
        for a, b in self.runs:
            self.box("nplus", a - 0.1, -0.23, b + 0.1, 2.23)
            self.box("pplus", a - 0.1, stdcells.YP - 0.23, b + 0.1, stdcells.YTOP + 0.23)


def _stack(row, x, y, level):
    """via stack from a Metal1 pad (level m1) or from the Metal2 jog (level m2) up to a Metal3 pad"""
    if level == "m1":
        row.box("via1", x - 0.13, y - 0.13, x + 0.13, y + 0.13)
        row.box("m2", x - 0.19, y - 0.19, x + 0.19, y + 0.19)
    row.box("via2", x - 0.13, y - 0.13, x + 0.13, y + 0.13)
    row.box("m3", x - 0.19, y - 0.19, x + 0.19, y + 0.19)


def build(max_cells=None, verbose=True):
    leaves = __import__("spicenet").digital_core()
    if max_cells:
        leaves = leaves[:max_cells]
    row = Row()
    row.place_tap()
    since_tap = 0.0
    for path, kind, nets in leaves:
        cell = stdcells.CELLS[kind]()
        row.place(path, kind, cell)
        if row.cursor - (row.taps[-1] + 0.66) > TAP_EVERY:
            row.place_tap()
    row.place_tap()
    row.finish_row()

    # pin -> net map (layout pin names vs spice pin names)
    pins_of_net = collections.defaultdict(list)
    spice_pins = {"INV": ["a", "y"], "NAND2": ["a", "b", "y"], "NOR2": ["a", "b", "y"], "TG": ["x", "y", "en", "enb"]}
    swap = {"a": "b", "b": "a"}           # two-finger cells: the first poly column (pin a) is SPICE pin b
    by_path = {path: nets for path, kind, nets in leaves}
    for path, kind, ox, cell in row.placed:
        nets = by_path[path]
        sp = spice_pins[kind]
        for sname, net in zip(sp, nets[:len(sp)]):
            lname = swap.get(sname, sname) if kind in ("NAND2", "NOR2") else sname
            pin = cell["pins"][lname]; pr = cell["probe"][lname]
            pins_of_net[net].append(dict(x=ox + pin["x"], y=pin["y"], level=pin["level"], probe=(ox + pr[0], pr[1]), cell=path, pin=lname))
    sig = {n: ps for n, ps in pins_of_net.items() if n not in ("vdd", "vss")}
    order = sorted(sig, key=lambda n: min(q["x"] for q in sig[n]))
    tracks = {}
    for k, n in enumerate(order):
        y = TRACK0 + TRACK_PITCH * k
        tracks[n] = y
        xs = [q["x"] for q in sig[n]]
        for q in sig[n]:
            _stack(row, q["x"], q["y"], q["level"])
            row.box("m3", q["x"] - 0.14, q["y"], q["x"] + 0.14, y + 0.19)
            row.box("m3", q["x"] - 0.19, y - 0.19, q["x"] + 0.19, y + 0.19)
            row.box("via3", q["x"] - 0.13, y - 0.13, q["x"] + 0.13, y + 0.13)
        row.box("m4", min(xs) - 0.19, y - 0.19, max(xs) + 0.19, y + 0.19)
    row.top.flatten(True)
    info = dict(row=row, leaves=leaves, pins=pins_of_net, tracks=tracks)
    if verbose:
        print(f"{len(leaves)} cells, {len(sig)} signal nets, row {row.x1 - row.x0:.0f} um long, "
              f"{len(row.taps)} tap pairs, tracks up to y = {max(tracks.values()):.1f} um")
    return info


def reference(leaves):
    devs = []
    for path, kind, nets in leaves:
        if kind == "INV":
            a, y = nets[0], nets[1]
            devs += [("N", "vss", y, a, 2.0), ("P", "vdd", y, a, 2.0)]
        elif kind == "NAND2":
            a, b, y = nets[:3]; n1 = path + ".n1"
            devs += [("N", n1, y, a, 2.0), ("N", "vss", n1, b, 2.0), ("P", "vdd", y, a, 2.0), ("P", "vdd", y, b, 2.0)]
        elif kind == "NOR2":
            a, b, y = nets[:3]; p1 = path + ".p1"
            devs += [("N", "vss", y, a, 2.0), ("N", "vss", y, b, 2.0), ("P", p1, y, a, 2.0), ("P", "vdd", p1, b, 2.0)]
        elif kind == "TG":
            x, y, en, enb = nets[:4]
            devs += [("N", x, y, en, 2.0), ("P", x, y, enb, 2.0)]
    return lvs_lite.schematic("DIGCORE", devs, None)


def check(info, do_drc=True):
    row = info["row"]; ly, top = row.ly, row.top
    ok = True
    if do_drc:
        res = drc_lite.report(ly, top)
        ok = all(c == 0 for _, c, _ in res)
    ref = reference(info["leaves"])
    pins = {}
    for n, ps in info["pins"].items():
        pins[n] = ps[0]["probe"]
    pins["vss"] = ((row.x0 + row.x1) / 2, -0.6)
    pins["vdd"] = ((row.x0 + row.x1) / 2, stdcells.YTOP + 0.6)
    return ok, lvs_lite.compare(ly, top, ref, "DIGCORE", pins)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    info = build(n)
    d_ok, l_ok = check(info)
    row = info["row"]
    row.ly.write(str(pathlib.Path(__file__).resolve().parent / ("digcore.gds" if not n else f"digcore_{n}.gds")))
    sys.exit(0 if (d_ok and l_ok) else 1)
