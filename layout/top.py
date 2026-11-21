"""Top level of the 4-bit SAR ADC layout: digital core (left), analog block (right of a connection channel),
capacitor row (above the analog block). Nets that appear in both the digital and the analog block are joined in
dedicated columns between the blocks (Metal4 stubs from each block's track, a Metal3 vertical, via3 at both ends);
the capacitor row is wired down to the analog tracks. External nets (vin, vref, vcm, rst, clk, eoc, ...) are not
brought to a pad ring.
Run: python top.py   (rule subset on the whole layout + LVS against the simulated netlist; writes adc4.gds)
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import klayout.db as db
import router, analog, caprow, lvs_lite, drc_lite, stdcells

U = 1000
COL_PITCH = 0.8
CHANNEL = 8.0


def copy_in(dst_ly, dst_cell, src_ly, src_cell, dx, dy):
    for l in src_ly.layer_indexes():
        info = src_ly.get_info(l)
        reg = db.Region(src_cell.begin_shapes_rec(l))
        if reg.is_empty():
            continue
        reg.transform(db.Trans(round(dx * U), round(dy * U)))
        dst_cell.shapes(dst_ly.layer(info.layer, info.datatype)).insert(reg)


def build(verbose=True, channel=True, caps=True):
    dig = router.build(verbose=False, rail_pins=True)
    ana = analog.build(verbose=False, track0=max(dig["tracks"].values()) + 3.0)   # all analog tracks above all digital tracks
    cly, ctop, cpins = caprow.build()
    drow, arow = dig["row"], ana["row"]

    ly = db.Layout(); ly.dbu = 0.001
    top = ly.create_cell("ADC4")
    box = lambda layer, x0, y0, x1, y1: top.shapes(ly.layer(*drc_lite.LAYERS[layer])).insert(
        db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U)))

    shared = sorted(set(dig["tracks"]) & set(ana["tracks"]))
    xg0 = drow.x1 + 3.0
    ADX = xg0 + COL_PITCH * len(shared) + 3.0 - arow.x0          # analog block x offset
    copy_in(ly, top, drow.ly, drow.top, 0, 0)
    copy_in(ly, top, arow.ly, arow.top, ADX, 0)

    # --- digital <-> analog: one column per shared net
    for k, n in (enumerate(shared) if channel else []):
        xg = xg0 + COL_PITCH * k
        yd, ya = dig["tracks"][n], ana["tracks"][n]
        dmax = max(q["x"] for q in dig["pins"][n]) + 0.19
        amin = min(q["x"] for q in ana["pins"][n]) + ADX - 0.19
        box("m4", dmax - 0.38, yd - 0.19, xg + 0.19, yd + 0.19)
        box("m4", xg - 0.19, ya - 0.19, amin + 0.38, ya + 0.19)
        box("m3", xg - 0.14, min(yd, ya) - 0.19, xg + 0.14, max(yd, ya) + 0.19)
        for y in (yd, ya):
            box("via3", xg - 0.13, y - 0.13, xg + 0.13, y + 0.13)
            box("m3", xg - 0.19, y - 0.19, xg + 0.19, y + 0.19)

    # --- capacitor row above the analog tracks; find an x offset where its wires clear the analog Metal3 verticals
    ytop_tracks = max(ana["tracks"].values())
    CY = ytop_tracks + 6.0
    verticals = []                                              # (x, ylo, yhi) of analog pin wires, in top coordinates
    for n, ps in ana["pins"].items():
        for q in ps:
            verticals.append((q["x"] + ADX, q["y"] - 0.19, ana["tracks"][n] + 0.19))
    names = {"B0": "b0", "B1": "b1", "B2": "b2", "B3": "b3", "BT": "bt", "top": "top"}
    ax0, ax1 = arow.x0 + ADX, arow.x1 + ADX
    best = None
    for step in range(0, int((ax1 - ax0 - 78.0) / 0.1)):
        cx = ax0 + 2.0 + 0.1 * step
        ok = True
        for pin, net in names.items():
            xp = cx + cpins[pin]["x"]
            yb = ana["tracks"][net]
            for vx, vlo, vhi in verticals:
                if vhi >= yb - 0.19 and vlo <= CY and abs(vx - xp) < 0.70:
                    ok = False; break
            if not ok: break
        if ok:
            best = cx; break
    if best is None:
        raise RuntimeError("no clear x position for the capacitor row")
    cx = best
    copy_in(ly, top, cly, ctop, cx, CY)
    cap_pin_xy = {}
    for pin, net in (names.items() if caps else []):
        q = cpins[pin]; xp = cx + q["x"]; y0 = CY + q["y"]; yb = ana["tracks"][net]
        if q["level"] == "m3":
            box("m3", xp - 0.14, yb - 0.19, xp + 0.14, y0 + 0.3)       # wire overlaps the plate's Metal3
        else:
            box("m3", xp - 0.14, yb - 0.19, xp + 0.14, y0 + 0.19)      # wire continues from the stub pad
        box("m3", xp - 0.19, yb - 0.19, xp + 0.19, yb + 0.19)
        box("via3", xp - 0.13, yb - 0.13, xp + 0.13, yb + 0.13)
        # make sure the analog trunk of that net reaches the wire
        xs = [q2["x"] + ADX for q2 in ana["pins"][net]]
        lo, hi = min(xs) - 0.19, max(xs) + 0.19
        if xp - 0.19 < lo: box("m4", xp - 0.19, yb - 0.19, lo + 0.38, yb + 0.19)
        if xp + 0.19 > hi: box("m4", hi - 0.38, yb - 0.19, xp + 0.19, yb + 0.19)
        cap_pin_xy[net] = (xp, y0)
    top.flatten(True)
    info = dict(ly=ly, top=top, dig=dig, ana=ana, ADX=ADX, shared=shared, cx=cx, CY=CY, cap_pins=cap_pin_xy)
    if verbose:
        print(f"top: digital {len(dig['leaves'])} cells + analog {ana['count']} cells + 16 capacitors; "
              f"{len(shared)} nets shared between blocks; capacitor row at x = {cx:.1f}, y = {CY:.1f}; "
              f"layout {top.bbox().width() / U:.0f} x {top.bbox().height() / U:.0f} um")
    return info


def sub_boxes(info):
    """one substrate region per block (digital core, analog block, capacitor row), so ground has to be wired between them"""
    ADX = info["ADX"]; d, a = info["dig"]["row"], info["ana"]["row"]
    bb = lambda x0, y0, x1, y1: db.Box(round(x0 * U), round(y0 * U), round(x1 * U), round(y1 * U))
    return [bb(d.x0 - 1, -3, d.x1 + 1, max(info["dig"]["tracks"].values()) + 2),
            bb(a.x0 + ADX - 1, -3, a.x1 + ADX + 1, max(info["ana"]["tracks"].values()) + 2)]


def check(info):
    ly, top, ADX = info["ly"], info["top"], info["ADX"]
    dig, ana = info["dig"], info["ana"]
    res = drc_lite.report(ly, top)
    devs = router.ref_devices(dig["leaves"]) + ana["ref"]
    ref = lvs_lite.schematic("ADC4", devs, None)
    pins = {}
    for n, ps in dig["pins"].items():
        pins[n] = ps[0]["probe"]
    for n, ps in ana["pins"].items():
        if n not in pins:
            pins[n] = (ps[0]["probe"][0] + ADX, ps[0]["probe"][1])
    ok_l = lvs_lite.compare(ly, top, ref, "ADC4", pins, sub_boxes(info))
    # capacitor pins must sit on the same extracted net as the matching analog pin
    l2n, m1 = lvs_lite.extract(ly, top, sub_boxes(info))
    same = {}
    for net, (x, y) in info["cap_pins"].items():
        layer = l2n.layer_by_name("L40_0" if net == "top" else "L42_0")
        yy = y + (0.0 if net == "top" else 0.3)
        a = l2n.probe_net(l2n.layer_by_name("L42_0") if net != "top" else l2n.layer_by_name("L46_0"), db.DPoint(x, yy if net != "top" else y + 1.0))
        p = pins[net]
        b = l2n.probe_net(m1, db.DPoint(p[0], p[1]))
        same[net] = bool(a is not None and b is not None and a.expanded_name() == b.expanded_name())
    print("  capacitor pins on the same net as their switches / comparator:", same)
    return all(c == 0 for _, c, _ in res), ok_l, all(same.values())


if __name__ == "__main__":
    info = build()
    d_ok, l_ok, c_ok = check(info)
    info["ly"].write(str(pathlib.Path(__file__).resolve().parent / "adc4.gds"))
    sys.exit(0 if (d_ok and l_ok and c_ok) else 1)
