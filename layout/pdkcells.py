"""Loads the official GF180MCU KLayout device generators (draw_nmos, draw_pmos, draw_mimcap) with the
standalone klayout Python module standing in for `pya`, so devices are drawn by the foundry's own code."""
import sys, os, pathlib, importlib.util
import klayout.db as db
sys.modules.setdefault("pya", db)
PDK = os.environ.get("GF180_PR", str(pathlib.Path(__file__).resolve().parents[2] / "tools/globalfoundries-pdk-libs-gf180mcu_fd_pr"))
CELLS = pathlib.Path(PDK) / "cells/klayout/pymacros/cells"

def _load(name):
    spec = importlib.util.spec_from_file_location(name, CELLS / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

draw_mos = _load("draw_mos")
draw_mimcap = _load("draw_mimcap")

def nmos(layout, w, l=0.28, nf=1, ld=0.44, bulk="None"):
    return draw_mos.draw_nmos(layout, l, w, ld, nf, 0.36, bulk, "3.3V", 0, 0)

def pmos(layout, w, l=0.28, nf=1, ld=0.44, bulk="None"):
    return draw_mos.draw_pmos(layout, l, w, ld, nf, 0.36, bulk, "3.3V", 0, 0)

def mimcap(layout, size, metal_level="M4"):
    return draw_mimcap.draw_mimcap(layout, size, size, "MIM-B", metal_level)
