# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/__init__.py

"""ABE: A Better Environment for Open-Source ASIC IP Development.

ABE is a comprehensive framework for hardware design, verification, and
microarchitecture analysis. It provides reusable IP, verification infrastructure,
and analytical tools to accelerate hardware development.

Main Components:

rad (Reusable Analog/Digital):
    Collection of verified RTL IP modules with formal verification properties
    and UVM-style testbenches. Includes:
    - Asynchronous FIFOs
    - Clock domain crossing components
    - Shared verification infrastructure and DV tools

uarch (Microarchitecture):
    Analytical tools for microarchitecture modeling and optimization:
    - FIFO depth calculation for various flow control protocols
    - Packet quantization analysis
    - Performance trade-off modeling

utils:
    Common utilities used across the framework

For more information, see the project documentation and individual module
docstrings.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

try:
    __version__ = pkg_version("abe")
except PackageNotFoundError:
    __version__ = "0+local"
