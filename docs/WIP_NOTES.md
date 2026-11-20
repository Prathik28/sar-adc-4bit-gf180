# Work in progress: extra verification (branch `wip-extra-verification`, not pushed)

Everything on `main` is already published. This branch holds the follow-up work that was stopped
part-way. Scripts below are written and smoke-tested on short runs; the long simulations were
interrupted, so none of their numbers are in the README yet.

## Done
- **EOC / decoder glitch study** (`spice/fsm_eocreg.sp`, `scripts/glitch_eoc.py`, `results/eoc_glitch.json`).
  With the report's 10 Mohm loads, SET_B1 shows 3 spurious full-rail pulses (up to 140 ps) in 18
  cycles. With 20 fF loads it is a sub-threshold 0.75 V spike. The combinational EOC never
  glitched; the re-timed EOC (flip-flop on the next-state decode) is clean but not required.
- Generator options added to `scripts/adc_gen.py`: `--mim` (PDK `mim_2p0fF` capacitors, 3.31 um
  unit cell = 25 fF) and `--noise <mV rms>` (series white-noise source with a 0.937 ns step; a 1 ns
  step collides with the clock edges and aborts the transient).
- `run_batch.py` job sets `mim`, `noise`, `mm`, `extra`; `analyze.py` modes `mim`, `noise`, `mm`;
  `mc_comparator.py --corner <c>` for per-corner offset Monte Carlo.

## Still to run (about 40 min on 6 cores)
```bash
scripts/setup_spice.sh                       # rebuild build/spice if it was deleted
python scripts/run_batch.py extra -j 6       # MIM caps, noise sweep (0.1..20 mV), converter mismatch
for c in ff ss fs sf; do python scripts/mc_comparator.py 100 -j 4 --corner $c; done
python scripts/analyze.py mim; python scripts/analyze.py noise; python scripts/analyze.py mm
```
Interrupted partial outputs (`mimfine_q1/q2`, `mim_ss_125_1.8`) in `build/spice/runs/` are
gitignored and can be reused or deleted.

## Then
- Add the new results and the glitch finding to the README (replace the matching "Not verified" bullets),
  note that the PDK has no per-instance MIM-cap mismatch (only a global skew), commit as Prathik Amte, push.
- Open items that need other tools: layout / extraction, Cadence gpdk180, Vivado and board.
