# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/50-formal.mk

.PHONY: formal-help
formal-help:
	@echo ""
	@echo "Formal:"
	@echo ""
	@echo "  make DESIGN=<design> formal              # Formal prove"
	@echo "  make DESIGN=<design> formal-cover        # Formal cover"
	@echo "  make formal-test                         # Formal prove and cover for every design"

.PHONY: formal
formal: check-design
	@echo "==> formal prove"
	sby -f -d $(FORMAL_OUT_DIR) $(FORMAL_DIR)/$(DESIGN).sby

.PHONY: formal-cover
formal-cover: check-design
	@echo "==> formal cover"
	sby -f -d $(FORMAL_OUT_DIR)_cover $(FORMAL_DIR)/$(DESIGN)_cover.sby

.PHONY: formal-clean
formal-clean:
	@echo "Cleaning formal outputs"
	@rm -rf out_formal

.PHONY: clean
clean: formal-clean

# Prove and cover every design that has a formal directory. All designs run, and
# the target fails if any did. Output is shown only for a design that fails.
.PHONY: formal-test
formal-test:
	@rc=0; for d in $(RAD_ROOT)/*/formal ; do \
	  [ -d "$$d" ] || continue; \
	  b=$${d%/formal}; b=$${b##*/}; \
	  log=$$(mktemp); \
	  if $(MAKE) -s DESIGN="$$b" formal formal-cover >"$$log" 2>&1; then \
	    echo "formal PASS: $$b (prove, cover)"; \
	  else \
	    cat "$$log"; echo "formal FAIL: $$b"; rc=1; \
	  fi; \
	  rm -f "$$log"; \
	done; exit $$rc

.PHONY: test
test: formal-test

.PHONY: formal-all
formal-all:
	@echo "All formal - not implemented yet"

.PHONY: all
all: formal-all
