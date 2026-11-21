"""Reads spice/cells.sp and spice/adc_130b.sp and flattens the digital part of the converter into leaf
cells (INV, NAND2, NOR2, TG), so a layout can be compared with the netlist that was actually simulated.
Ground ("0") is renamed vss. Internal nets get hierarchical names (instance path + local net)."""
import re, pathlib

SPICE = pathlib.Path(__file__).resolve().parent.parent / "spice"
LEAF = {"INV", "NAND2", "NOR2", "TG"}
DIGITAL = LEAF | {"AND2", "OR2", "DFF", "NSL_FIXED", "NSL_ASBUILT", "FSMREG", "OUTL"}


def _lines(text):
    out = []
    for ln in text.splitlines():
        ln = ln.split("*", 1)[0].strip() if ln.lstrip().startswith("*") else ln.strip()
        if ln:
            out.append(ln)
    return out


def parse_subckts(text):
    defs, cur = {}, None
    for ln in _lines(text):
        low = ln.lower()
        if low.startswith(".subckt"):
            t = ln.split()
            cur = {"ports": t[2:], "insts": []}
            defs[t[1]] = cur
        elif low.startswith(".ends"):
            cur = None
        elif cur is not None and ln[0] in "Xx":
            t = ln.split()
            if "nmos_3p3" in t or "pmos_3p3" in t:
                continue                       # transistor inside a leaf cell: leaf cells are used as black boxes
            cur["insts"].append((t[0], t[1:-1], t[-1]))
    return defs


def top_instances(text):
    """X lines that appear outside any .subckt"""
    out, inside = [], False
    for ln in _lines(text):
        low = ln.lower()
        if low.startswith(".subckt"):
            inside = True
        elif low.startswith(".ends"):
            inside = False
        elif not inside and ln[0] in "Xx":
            t = ln.split()
            if "=" in t[-1] or t[-1].lower() in ("nmos_3p3", "pmos_3p3") or any(x in ("nmos_3p3", "pmos_3p3") for x in t):
                continue                       # a bare transistor (analog part)
            out.append((t[0], t[1:-1], t[-1]))
    return out


def flatten(inst_name, nets, kind, defs, prefix, netmap_global=("vdd", "vss", "0")):
    """returns list of (path, kind, nets) for leaf cells"""
    if kind in LEAF:
        return [(prefix + inst_name, kind, nets)]
    d = defs[kind]
    local = dict(zip(d["ports"], nets))
    res = []
    for iname, inets, ikind in d["insts"]:
        mapped = []
        for n in inets:
            if n in local:
                mapped.append(local[n])
            elif n in netmap_global:
                mapped.append(n)
            else:
                mapped.append(f"{prefix}{inst_name}.{n}")
        res += flatten(iname, mapped, ikind, defs, prefix + inst_name + ".", netmap_global)
    return res


def digital_core():
    cells = parse_subckts((SPICE / "cells.sp").read_text())
    top = top_instances((SPICE / "adc_130b.sp").read_text())
    leaves = []
    for name, nets, kind in top:
        if kind in DIGITAL:
            nets = ["vss" if n == "0" else n for n in nets]
            leaves += flatten(name, nets, kind, cells, "")
    leaves = [(p, k, ["vss" if n == "0" else n for n in ns]) for p, k, ns in leaves]
    return leaves


PINS = {"INV": ["a", "y", "vdd", "vss"], "NAND2": ["a", "b", "y", "vdd", "vss"], "NOR2": ["a", "b", "y", "vdd", "vss"],
        "TG": ["x", "y", "en", "enb", "vdd", "vss"]}


if __name__ == "__main__":
    import collections
    lv = digital_core()
    print(len(lv), "leaf cells:", dict(collections.Counter(k for _, k, _ in lv)))
    nets = collections.Counter(n for _, _, ns in lv for n in ns)
    print(len(nets), "nets;", sum(1 for n, c in nets.items() if c == 1), "with a single pin:", [n for n, c in nets.items() if c == 1][:12])
