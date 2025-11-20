# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/__init__.py

"""Design verification testbench for rad_async_fifo.

This package contains a complete UVM-style testbench for verifying the
rad_async_fifo (asynchronous FIFO) design using cocotb and pyuvm.

Components:
- rad_async_fifo_env: Top-level UVM environment
- rad_async_fifo_driver: Drives write-side transactions
- rad_async_fifo_monitor_in: Monitors write-side interface
- rad_async_fifo_monitor_out: Monitors read-side interface
- rad_async_fifo_ref_model: Reference model for golden behavior
- rad_async_fifo_sb: Scoreboard for comparing DUT vs reference
- rad_async_fifo_sequence: Test sequences
- rad_async_fifo_item: Transaction item definition
- rad_async_fifo_coverage: Functional coverage collection
- rad_async_fifo_reset_sink: Reset handling component

To run tests:
    dv --design=rad_async_fifo --test=rad_async_fifo_env
    dv-regress --file=src/abe/rad/rad_async_fifo/dv/dv_regress.yaml
"""
