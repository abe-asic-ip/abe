# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/80-uarch-pq.mk

.PHONY: uarch-pq-help
uarch-pq-help:
	@echo ""
	@echo "Uarch pkt_quantize:"
	@echo ""
	@echo "  make uarch-pq-default                    # run packet quantization (default args)"
	@echo "  make uarch-pq-custom                     # run packet quantization (custom args)"

.PHONY: uarch-pq-default
uarch-pq-default:
	@pkt-quantize

.PHONY: uarch-pq-custom
uarch-pq-custom:
	@pkt-quantize --bus-width 128 --clk-freq 1e9 --min-cycles 2 --min-size 64 --max-size 512

.PHONY: uarch-pq-clean
uarch-pq-clean:
	@echo "Cleaning uarch-pq outputs"
	@rm -rf out_uarch_pkt_quantize

.PHONY: clean
clean: uarch-pq-clean

.PHONY: uarch-pq-test
uarch-pq-test:
	@echo "Test uarch-pq - not implemented yet"

.PHONY: test
test: uarch-pq-test

.PHONY: uarch-pq-all
uarch-pq-all:
	@echo "All uarch-pq - not implemented yet"

.PHONY: all
all: uarch-pq-all
