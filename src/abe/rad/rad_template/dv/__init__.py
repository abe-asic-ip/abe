# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/__init__.py

"""Template for design verification testbenches.

This package serves as a template for creating new DV testbenches using
cocotb and pyuvm. It is not meant to be used directly, but rather as a
starting point for generating new testbench scaffolds via dv-make-bench.

Template Components:
- template_driver: Template for driving DUT inputs
- template_monitor_in: Template for monitoring input interface
- template_monitor_out: Template for monitoring output interface
- template_ref_model: Template for reference model
- template_sequence: Template for test sequences
- template_item: Template for transaction item definition
- template_coverage: Template for functional coverage collection

To create a new testbench from this template:
    dv-make-bench <module_name> <author> [--year YEAR] [--force]

Example:
    dv-make-bench rad_my_module "John Doe" --year 2025

This will generate a complete testbench in src/abe/rad/rad_my_module/dv/
with all template placeholders replaced with appropriate module-specific names.
"""
