# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/__init__.py

"""Microarchitecture modeling and analysis tools.

This package provides analytical tools for microarchitecture design and
optimization, including FIFO depth calculation and packet quantization analysis.

Modules:

FIFO Depth Calculation:
- fifo_depth: Main CLI and orchestration for FIFO depth analysis
- fifo_depth_base: Base classes and common infrastructure
- fifo_depth_ready_valid: Ready/Valid protocol FIFO depth calculation
- fifo_depth_cbfc: Credit-based flow control FIFO depth calculation
- fifo_depth_xon_xoff: XON/XOFF flow control FIFO depth calculation
- fifo_depth_replay: Replay buffer FIFO depth calculation
- fifo_depth_cdc: Clock domain crossing adjustments for FIFO depth
- fifo_depth_utils: Utility functions for FIFO depth analysis
- fifo_depth_examples/: Example YAML configurations

Packet Quantization:
- pkt_quantize: Packet quantization analysis and modeling

These tools help designers make informed decisions about buffer sizing,
flow control mechanisms, and system performance trade-offs through
analytical modeling rather than simulation.
"""
