# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/60-dv.mk

.PHONY: dv-help
dv-help:
	@echo ""
	@echo "DV:"
	@echo ""
	@echo "  make dv DESIGN=<design> TEST=<test>      # Run single test in dv/tests/<test>/"
	@echo "  make dv-regress-design DESIGN=<design>   # Run all tests in <design>/dv/dv_regress.yaml"
	@echo "  make dv-regress-all                      # Run all tests in **/dv_regress.yaml"
	@echo "  make dv-report                           # Report test results"
	@echo "  make dv-regress-design-and-report        # Run all tests in <design>/dv/dv_regress.yaml, then report"
	@echo "  make dv-regress-all-and-report           # Run all tests in **/dv_regress.yaml, then report"
	@echo "  make dv-test                             # Same as dv-regress-all-and-report, without activating .venv"

.PHONY: dv
dv: check-design check-test
	$(DV) --design=$(DESIGN) --test=$(TEST) --outdir=$(DV_OUTDIR) $(DV_OPTS)

.PHONY: dv-regress-design
dv-regress-design: check-design
	$(DV_REGRESS) --file=$(DESIGN_DIR)/dv/dv_regress.yaml --outdir=$(DV_OUTDIR) $(DV_REGRESS_OPTS)

.PHONY: dv-regress-all
dv-regress-all:
	$(DV_REGRESS_ALL) --outdir=$(DV_OUTDIR) $(DV_REGRESS_ALL_OPTS)

.PHONY: dv-report
dv-report:
	@$(DV_REPORT) --outdir=$(DV_OUTDIR) $(DV_REPORT_OPTS)

.PHONY: dv-regress-design-and-report
dv-regress-design-and-report: dv-regress-design dv-report

.PHONY: dv-regress-all-and-report
dv-regress-all-and-report: dv-regress-all dv-report

.PHONY: dv-clean
dv-clean:
	@echo "Cleaning dv outputs"
	@rm -rf out_dv*

.PHONY: clean
clean: dv-clean

# Run every regression and report. The venv is put on PATH so the dv commands are
# found even when the venv is not activated.
.PHONY: dv-test
dv-test: py-ensure-venv
	@PATH="$(CURDIR)/$(BIN):$$PATH" $(MAKE) --no-print-directory dv-regress-all-and-report

.PHONY: test
test: dv-test

.PHONY: dv-all
dv-all:
	@echo "All dv - not implemented yet"

.PHONY: all
all: dv-all
