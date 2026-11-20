#!/usr/bin/env bash
# Prepare a work directory for the ngspice runs: copies the netlists and points models.sp at the
# GF180MCU models.  Usage: scripts/setup_spice.sh [path-to-models/ngspice]   (default: ../tools/...)
set -euo pipefail
cd "$(dirname "$0")/.."
M=${1:-${GF180_MODELS:-$(cd .. && pwd)/tools/globalfoundries-pdk-libs-gf180mcu_fd_pr/models/ngspice}}
[ -f "$M/sm141064.ngspice" ] || { echo "GF180 models not found in $M"; exit 1; }
mkdir -p build/spice && cp spice/*.sp spice/*.py build/spice/
cat > build/spice/models.sp <<EOM
* GF180MCU models (path set by scripts/setup_spice.sh)
.include $M/design.ngspice
.lib $M/sm141064.ngspice typical
.param sw_stat_global=0 sw_stat_mismatch=0
EOM
echo "models: $M"
