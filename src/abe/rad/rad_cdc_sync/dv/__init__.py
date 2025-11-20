# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/__init__.py

"""Design verification testbench for rad_cdc_sync.

This package contains a UVM-style testbench for verifying the rad_cdc_sync
(clock domain crossing synchronizer) design using cocotb and pyuvm.

Components:
- rad_cdc_sync_driver: Drives input transactions
- rad_cdc_sync_monitor_in: Monitors input interface
- rad_cdc_sync_monitor_out: Monitors output interface
- rad_cdc_sync_ref_model: Reference model for golden behavior
- rad_cdc_sync_sequence: Test sequences
- rad_cdc_sync_item: Transaction item definition
- rad_cdc_sync_coverage: Functional coverage collection

To run tests:
    dv --design=rad_cdc_sync --test=test_rad_cdc_sync
    dv-regress --file=src/abe/rad/rad_cdc_sync/dv/dv_regress.yaml
"""
