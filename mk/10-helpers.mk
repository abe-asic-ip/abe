# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/10-helpers.mk

.PHONY: deps
deps: deps-design deps-formal

.PHONY: deps-design
deps-design:
	@command -v verible-verilog-format >/dev/null || { echo "Missing verible-verilog-format"; exit 1; }
	@command -v verible-verilog-lint   >/dev/null || { echo "Missing verible-verilog-lint"; exit 1; }
	@command -v verilator              >/dev/null || { echo "Missing verilator"; exit 1; }
	@command -v sv2v                   >/dev/null || { echo "Missing sv2v"; exit 1; }
	@command -v yosys                  >/dev/null || { echo "Missing yosys"; exit 1; }
	@command -v dot                    >/dev/null || { echo "Missing dot (Graphviz)"; exit 1; }
	@echo "All design deps found."

.PHONY: deps-formal
deps-formal:
	@command -v sby           >/dev/null || { echo "Missing sby (SymbiYosys)"; exit 1; }
	@command -v yosys-smtbmc  >/dev/null || { echo "Missing yosys-smtbmc"; exit 1; }
	@if command -v boolector >/dev/null || command -v z3 >/dev/null || command -v yices-smt2 >/dev/null; then \
	  true; \
	else \
	  echo "Missing SMT solver (install one of: boolector, z3, yices-smt2)"; exit 1; \
	fi
	@echo "All formal deps found."

.PHONY: check-design
check-design:
	@if [ "$(DESIGN)" = "undefined" ] || [ -z "$(DESIGN)" ]; then \
		echo "ERROR: Please specify DESIGN=<design>"; \
	  exit 2; \
	fi

.PHONY: check-test
check-test:
	@if [ "$(TEST)" = "undefined" ] || [ -z "$(TEST)" ]; then \
		echo "ERROR: Please specify TEST=<test>"; \
	  exit 2; \
	fi

.PHONY: tree
tree: check-design
	@echo "DESIGN=$(DESIGN)"
	@echo "RTL_DIR=$(RTL_DIR)"
	@echo "SV_SRCLIST=$(SV_SRCLIST)"
	@echo "SV_FILES=$(SV_FILES)"
	@echo "INC_DIRS=$(INC_DIRS)"
	@echo "DEFINES_LIST=$(DEFINES_LIST)"
	@echo "FORMAL_DIR=$(FORMAL_DIR)"
	@echo "SYNTH_OUT_DIR=$(SYNTH_OUT_DIR)"
	@echo "FORMAL_OUT_DIR=$(FORMAL_OUT_DIR)"

.PHONY: helpers-clean
helpers-clean:
	@echo "Cleaning helpers outputs"

.PHONY: clean
clean: helpers-clean

.PHONY: helpers-test
helpers-test:
	@echo "Test helpers - not implemented yet"

.PHONY: test
test: helpers-test

.PHONY: helpers-all
helpers-all:
	@echo "All helpers - not implemented yet"

.PHONY: all
all: helpers-all
