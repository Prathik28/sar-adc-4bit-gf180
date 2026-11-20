* Point these at your local copy of the GF180MCU models:
* https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr  (models/ngspice)
.include design.ngspice
.lib sm141064.ngspice typical
.param sw_stat_global=0 sw_stat_mismatch=0
