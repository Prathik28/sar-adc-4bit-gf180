# Digital verification of the SAR ADC controller (needs Icarus Verilog; Yosys and Verilator optional)
SIM  = build
RTL  = rtl/sar_ctrl.v
.PHONY: layout formal all digital sim_4bit sim_nbit equiv lint synth post_synth clean
all: digital

digital: sim_4bit sim_nbit equiv lint synth post_synth

$(SIM):
	mkdir -p $(SIM)

sim_4bit: $(SIM)            ## original 4-bit self-checking test (65 conversions)
	iverilog -g2012 -o $(SIM)/tb_sar.vvp tb/tb_sar.v rtl/sar_ctrl.v && vvp $(SIM)/tb_sar.vvp | tail -3

sim_nbit: $(SIM)            ## generalised N-bit controller, N = 4, 8, 10
	for n in 4 8 10; do \
	  iverilog -g2012 -P tb_sar_n.N=$$n -o $(SIM)/tb_sar_n$$n.vvp tb/tb_sar_n.v rtl/sar_ctrl_n.v && \
	  vvp $(SIM)/tb_sar_n$$n.vvp | grep -E "conversions|PASS|FAIL"; done

equiv: $(SIM)               ## RTL vs gate-level mirror of the transistor-level logic
	iverilog -g2012 -o $(SIM)/tb_equiv.vvp tb/tb_equiv.v rtl/sar_ctrl.v rtl/sar_gates.v && vvp $(SIM)/tb_equiv.vvp | grep -v finish

lint:
	verilator --lint-only -Wall -Wno-DECLFILENAME --top-module sar_ctrl   rtl/sar_ctrl.v
	verilator --lint-only -Wall -Wno-DECLFILENAME --top-module sar_ctrl_n rtl/sar_ctrl_n.v
	verilator --lint-only -Wall -Wno-DECLFILENAME --top-module sar_gates  rtl/sar_gates.v

synth: $(SIM)               ## Artix-7 mapping (Basys 3) and generic gates
	yosys -q -p "read_verilog rtl/sar_ctrl.v rtl/fpga_top.v; synth_xilinx -top fpga_top -family xc7; tee -o results/yosys_xilinx_fpga_top.txt stat"
	yosys -q -p "read_verilog rtl/sar_ctrl.v; synth -top sar_ctrl -flatten; write_verilog -noattr $(SIM)/sar_ctrl_syn.v; tee -o results/yosys_generic_sar_ctrl.txt stat"

post_synth: synth           ## re-run the 4-bit test on the synthesised netlist
	iverilog -g2012 -o $(SIM)/post.vvp tb/tb_sar.v $(SIM)/sar_ctrl_syn.v && vvp $(SIM)/post.vvp | tail -2

clean:
	rm -rf $(SIM) tb_sar.vcd

formal:                     ## SymbiYosys proofs (needs sby, yosys, z3)
	for t in ctrl adc equiv; do sby -f formal/$$t.sby; done

layout:                     ## layout cells: rule subset + LVS (needs the klayout Python module and the PDK checkout)
	python layout/inverter.py && python layout/gates.py && python layout/tgate.py && python layout/caparray.py && python layout/router.py && python layout/analog.py && python layout/caprow.py && python layout/top.py
