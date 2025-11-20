# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/40-synth.mk

.PHONY: synth-help
synth-help:
	@echo ""
	@echo "Synthesis:"
	@echo ""
	@echo "  make DESIGN=<design> synth               # sv2v + Yosys stat"
	@echo "  make DESIGN=<design> synth-report        # Summarize Yosys stat"
	@echo "  make DESIGN=<design> synth-dot           # Show -format dot"

$(SYNTH_OUT_DIR):
	@mkdir -p $(SYNTH_OUT_DIR)

$(SYNTH_OUT_DIR)/$(DESIGN).v: | $(SYNTH_OUT_DIR)
ifeq ($(wildcard $(SV_SRCLIST)),)
	sv2v $(SV2V_FLAGS) $(INCFLAGS_SV2V) $(DEFFLAGS_SV2V) $(SV_SRCS) > $(SYNTH_OUT_DIR)/$(DESIGN).v
else
	files="$(shell bash src/abe/rad/tools/flatten_srclist.sh $(SV_SRCLIST) | tr '\n' ' ')"; \
	echo "sv2v file list: $$files"; \
	sv2v $(SV2V_FLAGS) $(INCFLAGS_SV2V) $(DEFFLAGS_SV2V) $$files > $(SYNTH_OUT_DIR)/$(DESIGN).v
endif

.PHONY: synth
synth: check-design $(SYNTH_OUT_DIR)/$(DESIGN).v
	@echo "==> Yosys synth/stat"
	yosys -l $(SYNTH_OUT_DIR)/yosys.log \
		-p "read_verilog -sv -D SYNTHESIS $(SYNTH_OUT_DIR)/$(DESIGN).v; \
		hierarchy -check -top $(DESIGN); \
		proc; opt; fsm; opt; memory; opt; \
		tee -o $(SYNTH_STAT_TXT) stat -width; \
		write_verilog -noexpr -attr2comment $(SYNTH_NET_V); \
		write_json -compat-int $(SYNTH_NET_JSON)"

.PHONY: synth-report
synth-report: check-design
	@echo "==> Yosys stat -width"
	@cat $(SYNTH_STAT_TXT)

.PHONY: synth-dot
synth-dot: check-design $(SYNTH_OUT_DIR)/$(DESIGN).v
	@echo "==> Yosys show (dot/svg)"
	yosys \
		-p "read_verilog -sv -D SYNTHESIS $(SYNTH_OUT_DIR)/$(DESIGN).v; \
		hierarchy -check -top $(DESIGN); \
		proc; opt; fsm; opt; memory; opt; \
		show -format dot -viewer none -prefix $(SYNTH_OUT_DIR)/$(DESIGN)"

.PHONY: synth-clean
synth-clean:
	@echo "Cleaning synth outputs"
	@rm -rf out_synth

.PHONY: clean
clean: synth-clean

.PHONY: synth-test
synth-test:
	@echo "Test synth - not implemented yet"

.PHONY: test
test: synth-test

.PHONY: synth-all
synth-all:
	@echo "All synth - not implemented yet"

.PHONY: all
all: synth-all
