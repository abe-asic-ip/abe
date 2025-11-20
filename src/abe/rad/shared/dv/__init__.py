# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/__init__.py

"""Shared design verification infrastructure for RAD modules.

This package provides a comprehensive set of base classes and utilities for
building UVM-style testbenches using cocotb and pyuvm. These shared components
are used across all RAD module testbenches to ensure consistency and reduce
code duplication.

Base Classes:
- BaseEnv: Top-level testbench environment
- BaseTest: Test case framework
- BaseAgent: Agent containing driver, monitor, and sequencer
- BaseDriver: Component for driving DUT inputs
- BaseMonitor: Generic monitor base class
- BaseMonitorIn: Input interface monitor
- BaseMonitorOut: Output interface monitor
- BaseSequencer: Sequence controller
- BaseSequence: Test sequence definition
- BaseItem: Transaction item base class
- BaseRefModel: Reference model for golden behavior
- BaseSb: Scoreboard for DUT vs reference comparison
- BaseSbComparator: Scoreboard comparison component
- BaseSbPredictor: Scoreboard prediction component
- BaseCoverage: Functional coverage collection

Clock and Reset Infrastructure:
- BaseClockDriver: Clock generation component
- BaseClockMixin: Mixin for clock-aware components
- BaseResetDriver: Reset generation component
- BaseResetMonitor: Reset monitoring component
- BaseResetSink: Reset handling component
- BaseResetItem: Reset transaction item

Utilities:
- utils_dv: Design verification utility functions
- utils_cli: Command-line interface utilities

All RAD testbenches inherit from these base classes to leverage common
functionality and maintain a consistent verification methodology.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

from abe import __version__

from . import utils_cli, utils_dv
from .base_agent import BaseAgent
from .base_clock_driver import BaseClockDriver
from .base_clock_mixin import BaseClockMixin
from .base_coverage import BaseCoverage
from .base_driver import BaseDriver
from .base_env import BaseEnv
from .base_item import BaseItem
from .base_monitor import BaseMonitor
from .base_monitor_in import BaseMonitorIn
from .base_monitor_out import BaseMonitorOut
from .base_ref_model import BaseRefModel
from .base_reset_driver import BaseResetDriver
from .base_reset_item import BaseResetItem
from .base_reset_monitor import BaseResetMonitor
from .base_reset_sink import BaseResetSink
from .base_sb import BaseSb
from .base_sb_comparator import BaseSbComparator
from .base_sb_predictor import BaseSbPredictor
from .base_sequence import BaseSequence
from .base_sequencer import BaseSequencer
from .base_test import BaseTest

__all__ = (
    "BaseAgent",
    "BaseClockDriver",
    "BaseClockMixin",
    "BaseCoverage",
    "BaseDriver",
    "BaseEnv",
    "BaseItem",
    "BaseMonitor",
    "BaseMonitorIn",
    "BaseMonitorOut",
    "BaseRefModel",
    "BaseResetDriver",
    "BaseResetItem",
    "BaseResetMonitor",
    "BaseResetSink",
    "BaseSb",
    "BaseSbComparator",
    "BaseSbPredictor",
    "BaseSequence",
    "BaseSequencer",
    "BaseTest",
    "utils_dv",
    "utils_cli",
    "__version__",
)
