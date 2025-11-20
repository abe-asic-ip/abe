# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: Makefile

.DEFAULT_GOAL := help
MK_DIR := mk

-include $(sort $(wildcard $(MK_DIR)/*.mk))

.PHONY: help
help:
	@echo ""
	@echo "Available help targets:"
	@echo ""
	@echo "  make py-help         # Show Python help"
	@echo "  make rtl-help        # Show RTL help"
	@echo "  make synth-help      # Show Synthesis help"
	@echo "  make formal-help     # Show Formal help"
	@echo "  make dv-help         # Show DV help"
	@echo "  make docs-help       # Show Documentation help"
	@echo "  make uarch-pq-help   # Show Packet Quantization help"
	@echo "  make uarch-fd-help   # Show Fifo Depth help"
	@echo "  make all-help        # Show all help targets"

.PHONY: all-help
all-help: py-help rtl-help synth-help formal-help dv-help docs-help uarch-pq-help uarch-fd-help
	@echo ""

.PHONY: checkmake
checkmake:
	@checkmake --config checkmake.ini Makefile $(MK_DIR)/*.mk

.PHONY: repo-clean
repo-clean:
	@echo "Cleaning repo outputs"
	@rm -rf *.log

.PHONY: clean
clean: repo-clean

.PHONY: repo-test
repo-test:
	@echo "Test repo - not implemented yet"

.PHONY: test
test: repo-test

.PHONY: repo-all
repo-all:
	@echo "All repo - not implemented yet"

.PHONY: all
all: repo-all
