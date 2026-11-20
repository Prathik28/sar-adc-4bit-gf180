# Vivado batch flow for the Basys 3 prototype.  NOT RUN in this repository (no Vivado installed
# where this was written); the steps follow Section 11.5 of the project report.
# Usage:  vivado -mode batch -source fpga/build.tcl      (run from the repository root)
set part xc7a35tcpg236-1
create_project -force sar_adc_basys3 build/vivado -part $part
add_files      [list rtl/sar_ctrl.v rtl/fpga_top.v]
add_files -fileset sim_1 tb/tb_sar.v
add_files -fileset constrs_1 fpga/basys3_sar.xdc
set_property top fpga_top [current_fileset]
set_property top tb_sar   [get_filesets sim_1]
update_compile_order -fileset sources_1

# 1) behavioural simulation: expect "65 conversions checked, 0 errors"
launch_simulation -simset sim_1 -mode behavioral
run all
close_sim

# 2) synthesis, implementation, bitstream
launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
open_run impl_1
report_utilization    -file results/vivado_utilization.txt
report_timing_summary -file results/vivado_timing.txt
puts "Bitstream: build/vivado/sar_adc_basys3.runs/impl_1/fpga_top.bit"
