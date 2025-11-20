# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/__init__.py

"""Shared components and utilities for RAD modules.

This package contains reusable components, utilities, and infrastructure
that are shared across multiple RAD (Reusable Analog/Digital) IP modules.

Subpackages:
- dv: Shared design verification infrastructure (base classes, utilities)
- rtl: Shared RTL components and utilities

The shared DV infrastructure provides UVM-style base classes for building
testbenches with cocotb and pyuvm, ensuring consistency across all RAD
module verification efforts.
"""
