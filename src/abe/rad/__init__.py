# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/__init__.py

"""RAD (Reusable Analog/Digital) IP library.

This package contains a collection of reusable RTL designs with associated
verification infrastructure, including formal verification properties and
UVM-style testbenches.

Modules:
- rad_async_fifo: Asynchronous FIFO with Gray code pointers
- rad_cdc_sync: Clock domain crossing synchronizer
- rad_cdc_mcp: Clock domain crossing multi-cycle path
- rad_template: Template for creating new RAD modules

Subpackages:
- tools: DV command-line tools (dv, dv-regress, dv-report, etc.)
- shared: Shared utilities and components across RAD modules

Each module typically contains:
- rtl/: SystemVerilog RTL implementation
- formal/: Formal verification properties and tests
- dv/: Design verification testbench (cocotb/pyuvm)
"""
