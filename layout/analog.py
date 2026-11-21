"""Analog block: the StrongARM comparator, the four DAC reference switches (+ the dummy switch) and the six
8 um sampling transmission gates, taken from the transistor lines of spice/adc_130b.sp. Devices sit in one row,
each with its own tap, and are wired with the same Metal3 / Metal4 track router as the digital core.
The capacitors (C0..C3, CT, CPT) are not part of this block (see caparray.py).
Run: python analog.py    (rule subset + LVS against the netlist, writes analog.gds)
"""
import sys, re, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import router, stdcells, analog_cells, lvs_lite, drc_lite

SPICE = pathlib.Path(__file__).resolve().parent.parent / "spice" / "adc_130b.sp"


def parse():
    """transistors and TGW instances of the top level (analog part); returns (devices, tgws)"""
    devs, tgws = [], []
    for ln in SPICE.read_text().splitlines():
        t = ln.split()
        if not t or not t[0].startswith("X"):
            continue
        t = ["vss" if x == "0" else x for x in t]
        if "nmos_3p3" in t or "pmos_3p3" in t:
            d, g, s, b, model = t[1:6]
            w = float(re.search(r"W=([\d.]+)u", ln).group(1))
            devs.append((t[0], "n" if model == "nmos_3p3" else "p", d, g, s, b, w))
        elif t[-1] == "TGW":
            tgws.append((t[0],) + tuple(t[1:5]))
    return devs, tgws


def build(verbose=True, track0=12.5):
    devs, tgws = parse()
    saved = router.GAP_X
    router.GAP_X = 1.2
    row = router.Row(); row.top.name = "ANALOG"
    pins_of_net = collections.defaultdict(list)
    ref = []
    order = [("dev",) + d for d in devs if d[0].startswith("XM") or d[0].startswith("XS") and d[0][2] in "1234"] + \
            [("dev",) + d for d in devs if not (d[0].startswith("XM") or d[0].startswith("XS") and d[0][2] in "1234")] + \
            [("tg",) + t for t in tgws]
    for item in order:
        if item[0] == "dev":
            _, name, typ, d, g, s, b, w = item
            cell = analog_cells.dev(typ, w)
            row.place(name, "DEV", cell)
            ox = row.placed[-1][2]
            for pin, net in (("S", s), ("D", d), ("G", g), ("B", b)):
                q = cell["pins"][pin]; pr = cell["probe"][pin]
                pins_of_net[net].append(dict(x=ox + q["x"], y=q["y"], level=q["level"], probe=(ox + pr[0], pr[1]), cell=name, pin=pin))
            ref.append(("N" if typ == "n" else "P", s, d, g, w))
        else:
            _, name, x, y, en, enb = item
            cell = analog_cells.tgw()
            row.place(name, "TGW", cell)
            ox = row.placed[-1][2]
            for pin, net in (("x", x), ("y", y), ("en", en), ("enb", enb), ("vdd", "vdd"), ("vss", "vss")):
                q = cell["pins"][pin]; pr = cell["probe"][pin]
                pins_of_net[net].append(dict(x=ox + q["x"], y=q["y"], level=q["level"], probe=(ox + pr[0], pr[1]), cell=name, pin=pin))
            ref += [("N", x, y, en, 8.0), ("P", x, y, enb, 8.0)]
    router.GAP_X = saved
    row.x0 = min(ox + c["x0"] for _, _, ox, c in row.placed) - 0.5
    row.x1 = max(ox + c["x1"] for _, _, ox, c in row.placed) + 0.5
    tracks = router.route(row, pins_of_net, skip=(), track0=track0)
    row.top.flatten(True)
    info = dict(row=row, pins=pins_of_net, tracks=tracks, ref=ref, count=len(order))
    if verbose:
        print(f"{len(order)} analog cells ({len(devs)} transistors + {len(tgws)} transmission gates), "
              f"{len(tracks)} nets, {row.x1 - row.x0:.0f} um wide")
    return info


def check(info):
    row = info["row"]
    res = drc_lite.report(row.ly, row.top)
    ref = lvs_lite.schematic("ANALOG", info["ref"], None)
    pins = {n: ps[0]["probe"] for n, ps in info["pins"].items()}
    return all(c == 0 for _, c, _ in res), lvs_lite.compare(row.ly, row.top, ref, "ANALOG", pins)


if __name__ == "__main__":
    info = build()
    d_ok, l_ok = check(info)
    info["row"].ly.write(str(pathlib.Path(__file__).resolve().parent / "analog.gds"))
    sys.exit(0 if (d_ok and l_ok) else 1)
