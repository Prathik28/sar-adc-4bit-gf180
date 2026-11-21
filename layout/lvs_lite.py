"""Layout versus schematic for the cells in this project, using KLayout's netlist extractor
(LayoutToNetlist) and netlist comparer. The extraction recipe is written here (the foundry LVS deck
needs KLayout's Ruby engine); it recognises MOS devices from poly over diffusion and nets through
contacts and Metal1. Reference netlists are built from the same device sizes as spice/cells.sp."""
import klayout.db as db


def extract(ly, cell, sub_boxes=None):
    """sub_boxes: list of db.Box (dbu) giving separate substrate regions, e.g. one per block, so that ground must be
    connected through metal between blocks; default is one region for the whole cell"""
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, cell, []))
    mk = lambda l, d: l2n.make_layer(ly.layer(l, d), f"L{l}_{d}")
    nwell, comp, poly, pplus, nplus, co, m1 = mk(21, 0), mk(22, 0), mk(30, 0), mk(31, 0), mk(32, 0), mk(33, 0), mk(34, 0)
    v1, m2, v2, m3, v3, m4 = mk(35, 0), mk(36, 0), mk(38, 0), mk(42, 0), mk(40, 0), mk(46, 0)
    v3 = v3 - mk(75, 0)          # via3 inside a MIM top plate (fusetop) lands on the plate, not on the Metal3 bottom plate
    ngate = poly & (comp & nplus)
    pgate = poly & (comp & pplus)
    nsd = (comp & nplus) - poly
    psd = (comp & pplus) - poly
    ntap = nsd & nwell
    ptap = psd - nwell
    nmos_sd = nsd - nwell
    pmos_sd = psd & nwell
    sub = l2n.make_layer("sub")
    boxes = sub_boxes if sub_boxes else [cell.bbox()]
    sub.insert(db.Region(boxes) - nwell)
    # devices
    l2n.extract_devices(db.DeviceExtractorMOS4Transistor("NMOS"), {"SD": nmos_sd, "G": ngate, "W": sub, "P": poly})
    l2n.extract_devices(db.DeviceExtractorMOS4Transistor("PMOS"), {"SD": pmos_sd, "G": pgate, "W": nwell, "P": poly})
    # connectivity
    for a, b in [(nmos_sd, co), (pmos_sd, co), (ptap, co), (ntap, co), (poly, co), (co, m1),
                 (sub, ptap), (nwell, ntap), (m1, v1), (v1, m2), (m2, v2), (v2, m3), (m3, v3), (v3, m4)]:
        l2n.connect(a, b)
    for a in (nmos_sd, pmos_sd, ptap, ntap, poly, co, m1, sub, nwell, v1, m2, v2, m3, v3, m4):
        l2n.connect(a)
    l2n.extract_netlist()
    return l2n, m1


def schematic_inverter(w):
    nl = db.Netlist()
    cn, cp = db.DeviceClassMOS4Transistor(), db.DeviceClassMOS4Transistor()
    cn.name, cp.name = "NMOS", "PMOS"
    nl.add(cn); nl.add(cp)
    c = db.Circuit(); c.name = "INV"; nl.add(c)
    a, y, vdd, vss = (c.create_net(n) for n in ("a", "y", "vdd", "vss"))
    for name, cls, d, b in (("MN", cn, vss, vss), ("MP", cp, vdd, vdd)):
        dev = c.create_device(cls, name)
        dev.connect_terminal(cls.terminal_id("S"), d); dev.connect_terminal(cls.terminal_id("D"), y)
        dev.connect_terminal(cls.terminal_id("G"), a); dev.connect_terminal(cls.terminal_id("B"), b)
        dev.set_parameter(cls.parameter_id("W"), w); dev.set_parameter(cls.parameter_id("L"), 0.28)
    return nl


def compare(ly, cell, ref, circuit, pins, sub_boxes=None):
    """Extract `cell`, pin the nets found at the given Metal1 locations (um) to the reference
    nets of the same name (what text labels do in a signoff flow), and compare with `ref`."""
    l2n, m1 = extract(ly, cell, sub_boxes)
    ext = l2n.netlist()
    print("  extracted netlist:\n" + "\n".join("   " + ln for ln in str(ext).splitlines()))
    cmp_ = db.NetlistComparer()
    cmp_.max_depth = 0
    ec, rc = ext.circuit_by_name(circuit), ref.circuit_by_name(circuit)
    for name, loc in pins.items():
        x, y = loc[0], loc[1]
        layer = l2n.layer_by_name(loc[2]) if len(loc) > 2 else m1          # loc[2]: layer name such as "L42_0" (Metal3)
        net = l2n.probe_net(layer, db.DPoint(x, y))
        if net is None:
            print(f"  LVS: no Metal1 net at pin {name} ({x}, {y})")
            return False
        rnet = rc.net_by_name(name)
        if net.terminal_count() != rnet.terminal_count():
            print(f"  LVS: pin {name} touches {net.terminal_count()} device terminals, schematic has {rnet.terminal_count()}")
            return False
        cmp_.same_nets(ec, rc, net, rnet)
    ok = cmp_.compare(ext, ref)
    print("  LVS (layout vs schematic):", "MATCH" if ok else "MISMATCH")
    return ok


def compare_inverter(ly, cell, w, ytop=None):
    yp = w + 0.96
    ytop = yp + w
    pins = {"a": (0.37, w + 0.45), "y": (0.98, 1.0), "vss": (1.0, -0.6), "vdd": (1.0, ytop + 0.6)}
    return compare(ly, cell, schematic_inverter(w), "INV", pins)


def schematic(name, devices, pins):
    """devices: list of (kind 'N'|'P', source, drain, gate, w_um). Bulk is vss for N, vdd for P."""
    nl = db.Netlist()
    cn, cp = db.DeviceClassMOS4Transistor(), db.DeviceClassMOS4Transistor()
    cn.name, cp.name = "NMOS", "PMOS"
    nl.add(cn); nl.add(cp)
    c = db.Circuit(); c.name = name; nl.add(c)
    nets = {}
    def net(n):
        if n not in nets: nets[n] = c.create_net(n)
        return nets[n]
    for i, (kind, s, d, g, w) in enumerate(devices):
        cls = cn if kind == "N" else cp
        dev = c.create_device(cls, f"M{i}")
        for t, n in (("S", s), ("D", d), ("G", g), ("B", "vss" if kind == "N" else "vdd")):
            dev.connect_terminal(cls.terminal_id(t), net(n))
        dev.set_parameter(cls.parameter_id("W"), w); dev.set_parameter(cls.parameter_id("L"), 0.28)
    return nl
