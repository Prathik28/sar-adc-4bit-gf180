"""Subset of the GF180MCU (3.3 V) design rules, taken from the published Design Manual, section 7
(https://gf180mcu-pdk.readthedocs.io, Physical Verification, 7.0 Layout Rule Description).

This is NOT the foundry's signoff deck (that needs KLayout's Ruby engine). It checks width, space,
area, contact and well rules for the layers used by this project. Gate length, source/drain
extension and poly end cap come from the foundry's own device generators and are not re-checked.
Units: um.
"""
import klayout.db as db

LAYERS = dict(nwell=(21, 0), comp=(22, 0), poly=(30, 0), pplus=(31, 0), nplus=(32, 0),
              contact=(33, 0), m1=(34, 0), via1=(35, 0), m2=(36, 0), via2=(38, 0), m3=(42, 0), via3=(40, 0), m4=(46, 0))
UM = 1000  # database units per um


def _reg(ly, cell, key):
    r = db.Region(cell.begin_shapes_rec(ly.layer(*LAYERS[key])))
    r.merge()
    return r


def run(ly, cell):
    """Return a list of (rule, number of violations, Region of markers)."""
    comp, poly, nplus, pplus, nwell, co, m1, m2 = (_reg(ly, cell, k) for k in
                                                   "comp poly nplus pplus nwell contact m1 m2".split())
    ncomp, pcomp = comp & nplus, comp & pplus
    gate = poly & comp
    out = []

    def add(name, region):
        out.append((name, region.count(), region))

    def width(name, reg, w):
        add(name, reg.width_check(round(w * UM)).polygons())

    def space(name, reg, s):
        add(name, reg.space_check(round(s * UM)).polygons())

    def small(reg, min_area_um2):
        r = db.Region()
        for q in reg.each():
            if q.area() < min_area_um2 * UM * UM:
                r.insert(q)
        return r

    def near(a, b, d):
        """parts of b closer than d to a (a and b must not already overlap)"""
        return a.sized(round(d * UM) - 1) & b

    width("DF.1a COMP width >= 0.22", comp, 0.22)
    space("DF.3a COMP space >= 0.28", comp, 0.28)
    add("DF.9 COMP area >= 0.2025", small(comp, 0.2025))
    add("DF.12 COMP not covered by Nplus or Pplus", comp - nplus - pplus)

    width("PL.1 Poly width >= 0.18", poly, 0.18)
    space("PL.3a Poly space >= 0.24", poly, 0.24)

    width("NP.1 Nplus width >= 0.4", nplus, 0.4)
    space("NP.2 Nplus space >= 0.4", nplus, 0.4)
    width("PP.1 Pplus width >= 0.4", pplus, 0.4)
    space("PP.2 Pplus space >= 0.4", pplus, 0.4)
    add("NP/PP overlap (not allowed)", nplus & pplus)
    add("NP.3a Nplus to PCOMP space >= 0.16", near(pcomp, nplus, 0.16))
    add("PP.3a Pplus to NCOMP space >= 0.16", near(ncomp, pplus, 0.16))
    add("NP.5b Nplus extension beyond NCOMP >= 0.16", ncomp.sized(round(0.16 * UM)) - nplus)
    add("PP.5b Pplus extension beyond PCOMP >= 0.16", pcomp.sized(round(0.16 * UM)) - pplus)

    width("NW.1a Nwell width >= 0.86", nwell, 0.86)
    space("NW.2a Nwell space >= 0.6", nwell, 0.6)
    add("DF.16 NCOMP outside Nwell to Nwell space >= 0.43", near(ncomp - nwell, nwell, 0.43))
    add("DF.17 PCOMP outside Nwell to Nwell space >= 0.12", near(pcomp - nwell, nwell, 0.12))
    add("DF.4d Nwell overlap of NCOMP >= 0.12", (ncomp & nwell).sized(round(0.12 * UM)) - nwell)
    add("DF.4c Nwell overlap of PCOMP >= 0.43", (pcomp & nwell).sized(round(0.43 * UM)) - nwell)

    side = round(0.22 * UM)
    bad_size = db.Region()
    for p in co.each():
        b = p.bbox()
        if b.width() != side or b.height() != side:
            bad_size.insert(p)
    add("CO.1 contact size == 0.22", bad_size)
    space("CO.2a contact space >= 0.25", co, 0.25)
    add("CO.11 contact on field oxide", co - comp - poly)
    add("CO.4 COMP overlap of contact >= 0.07", co.interacting(comp).sized(round(0.07 * UM)) - comp)
    add("CO.3 Poly overlap of contact >= 0.07", co.interacting(poly).sized(round(0.07 * UM)) - poly)
    add("CO.10 contact on gate", co & gate)
    add("CO.7 contact to gate space >= 0.15", near(gate, co.interacting(comp), 0.15))
    add("CO.8 poly contact to COMP space >= 0.17", near(comp, co.interacting(poly) - comp, 0.17))
    add("contact not covered by Metal1", co - m1)

    width("M1.1 Metal1 width >= 0.23", m1, 0.23)
    space("M1.2a Metal1 space >= 0.23", m1, 0.23)
    add("M1.3 Metal1 area >= 0.1444", small(m1, 0.1444))
    # via1..via3 and Metal2..Metal4 (Vn.1 size 0.26, Vn.2a space 0.26, Mn.1 width 0.28, Mn.2a space 0.28, Mn.3 area 0.1444)
    vside = round(0.26 * UM)
    metals = {"m1": m1, "m2": m2, "m3": _reg(ly, cell, "m3"), "m4": _reg(ly, cell, "m4")}
    for name, lo, hi in (("via1", "m1", "m2"), ("via2", "m2", "m3"), ("via3", "m3", "m4")):
        v = _reg(ly, cell, name)
        bad_v = db.Region()
        for q in v.each():
            b = q.bbox()
            if b.width() != vside or b.height() != vside:
                bad_v.insert(q)
        add(f"V.1 {name} size == 0.26", bad_v)
        space(f"V.2a {name} space >= 0.26", v, 0.26)
        add(f"V.3 {lo} overlap of {name} >= 0.06", v.sized(round(0.06 * UM)) - metals[lo])
        add(f"V.4 {hi} overlap of {name} >= 0.06", v.sized(round(0.06 * UM)) - metals[hi])
    for name in ("m2", "m3", "m4"):
        width(f"M.1 {name} width >= 0.28", metals[name], 0.28)
        space(f"M.2a {name} space >= 0.28", metals[name], 0.28)
        add(f"M.3 {name} area >= 0.1444", small(metals[name], 0.1444))
    return out


def report(ly, cell):
    res = run(ly, cell)
    bad = [(n, c) for n, c, _ in res if c]
    for n, c in bad:
        print(f"  VIOLATION {n}: {c}")
    print(f"  DRC subset: {len(res)} rules checked, {len(bad)} violated")
    return res
