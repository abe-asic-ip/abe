# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/90-uarch-fd.mk

FD_OPTS ?=
FD_EXAMPLES := src/abe/uarch/fifo_depth_examples/

.PHONY: uarch-fd-help
uarch-fd-help:
	@echo ""
	@echo "Uarch fifo depth:"
	@echo ""
	@echo "  make uarch-fd-all.                       # Run all specifications in src/abe/uarch/examples/"

.PHONY: uarch-fd-most
uarch-fd-most:
	@fifo-depth $(FD_EXAMPLES)/cbfc*.yaml $(FD_OPTS)
	@fifo-depth $(FD_EXAMPLES)/replay*.yaml $(FD_OPTS)
	@fifo-depth $(FD_EXAMPLES)/rv*.yaml $(FD_OPTS)
	@fifo-depth $(FD_EXAMPLES)/xon_xoff_balanced.yaml $(FD_OPTS)
	@fifo-depth $(FD_EXAMPLES)/xon_xoff_flat.yaml $(FD_OPTS)

.PHONY: uarch-fd-all
uarch-fd-all: uarch-fd-most
	@fifo-depth $(FD_EXAMPLES)/xon_xoff_cdc.yaml $(FD_OPTS)
	@fifo-depth $(FD_EXAMPLES)/xon_xoff_layered.yaml $(FD_OPTS)

.PHONY: all
all: uarch-fd-all

.PHONY: uarch-fd-clean
uarch-fd-clean:
	@echo "Cleaning uarch-fd outputs"
	@rm -rf out_uarch_fd_*

.PHONY: clean
clean: uarch-fd-clean

.PHONY: uarch-fd-test
uarch-fd-test:
	@echo "Test uarch-fd - not implemented yet"

.PHONY: test
test: uarch-fd-test
