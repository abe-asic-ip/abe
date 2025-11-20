# SPDX-FileCopyrightText: 2025 Hugh Walsh
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

.PHONY: formal-test
formal-test:
	@echo "Test formal - not implemented yet"

.PHONY: test
test: formal-test

.PHONY: formal-all
formal-all:
	@echo "All formal - not implemented yet"

.PHONY: all
all: formal-all
