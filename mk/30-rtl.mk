# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/30-rtl.mk

.PHONY: rtl-help
rtl-help:
	@echo ""
	@echo "RTL:"
	@echo ""
	@echo "  make DESIGN=<design> rtl-format          # Format *.sv files (uses .verible-format)"
	@echo "  make DESIGN=<design> rtl-lint-verible    # Verible lint (uses .rules.verible_lint)"
	@echo "  make DESIGN=<design> rtl-lint-verilator  # Verilator --lint-only"
	@echo "  make DESIGN=<design> rtl-lint            # All linters"
	@echo "  make DESIGN=<design> rtl-nice            # Formatter followed by both linters"
	@echo "  make rtl-format-all                      # Format all designs"
	@echo "  make rtl-lint-all                        # Lint all designs"

.PHONY: rtl-format
rtl-format: check-design
	@d="$(RTL_DIR)"; \
	[ -d "$$d" ] || { echo "No RTL dir: $$d"; exit 0; }; \
	find "$$d" -maxdepth 1 -type f \( -name '*.sv' -o -name '*.svh' \) \
	  -exec verible-verilog-format $(VERIBLE_FORMAT_FLAGS) $(STATIC_OPTS) {} +

.PHONY: rtl-lint-verible
rtl-lint-verible: check-design
ifeq ($(wildcard $(SV_SRCLIST)),)
	@verible-verilog-lint $(VERIBLE_LINT_FLAGS) $(STATIC_OPTS) $(SV_FILES)
else
	@files="$(shell bash src/abe/rad/tools/flatten_srclist.sh $(SV_SRCLIST) | tr '\n' ' ')"; \
	verible-verilog-lint $(VERIBLE_LINT_FLAGS) $(STATIC_OPTS) $$files
endif

.PHONY: rtl-lint-verilator
rtl-lint-verilator: check-design
	@verilator $(VERILATOR_LINT_FLAGS) $(INCFLAGS_CC) $(DEFFLAGS_CC) $(STATIC_OPTS) $(SV_FILES)

.PHONY: rtl-lint
rtl-lint: check-design rtl-lint-verible rtl-lint-verilator

.PHONY: rtl-nice
rtl-nice: check-design rtl-format rtl-lint

.PHONY: rtl-format-all
rtl-format-all:
	@for d in $(RAD_ROOT)/*/rtl ; do \
	  [ -d "$$d" ] || continue; \
	  find "$$d" -maxdepth 1 -type f \( -name '*.sv' -o -name '*.svh' \) \
	    -exec verible-verilog-format $(VERIBLE_FORMAT_FLAGS) $(STATIC_OPTS) {} + ; \
	  echo "formatted $$d"; \
	done

.PHONY: rtl-lint-all
rtl-lint-all:
	@for d in $(RAD_ROOT)/*/rtl ; do \
	[ -d "$$d" ] || continue; \
	b=$${d%/rtl}; b=$${b##*/}; \
	if [ "$$b" = "shared" ]; then continue; fi; \
	if [ -f "$$d/srclist.f" ] || [ -f "$$d/$$b.sv" ]; then \
		$(MAKE) -s rtl-lint DESIGN="$$b" || exit $$?; \
		echo "linted $$d"; \
	fi; \
done

.PHONY: rtl-clean
rtl-clean:
	@echo "Cleaning rtl outputs"

.PHONY: clean
clean: rtl-clean

.PHONY: rtl-test
rtl-test:
	@echo "Test rtl - not implemented yet"

.PHONY: test
test: rtl-test

.PHONY: rtl-all
rtl-all:
	@echo "All rtl - not implemented yet"

.PHONY: all
all: rtl-all
