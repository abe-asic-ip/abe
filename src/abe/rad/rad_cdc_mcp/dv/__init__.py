# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/__init__.py

"""Design verification testbench for rad_cdc_mcp.

This package contains a complete UVM-style testbench for verifying the
rad_cdc_mcp (clock domain crossing multi-cycle path) design using cocotb
and pyuvm.

Components:
- rad_cdc_mcp_env: Top-level UVM environment
- rad_cdc_mcp_driver: Drives input transactions
- rad_cdc_mcp_monitor_in: Monitors input interface
- rad_cdc_mcp_monitor_out: Monitors output interface
- rad_cdc_mcp_ref_model: Reference model for golden behavior
- rad_cdc_mcp_sb: Scoreboard for comparing DUT vs reference
- rad_cdc_mcp_sequence: Test sequences
- rad_cdc_mcp_item: Transaction item definition
- rad_cdc_mcp_coverage: Functional coverage collection
- rad_cdc_mcp_reset_sink: Reset handling component

To run tests:
    dv --design=rad_cdc_mcp --test=rad_cdc_mcp_env
    dv-regress --file=src/abe/rad/rad_cdc_mcp/dv/dv_regress.yaml
"""
