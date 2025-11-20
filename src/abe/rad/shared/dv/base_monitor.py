# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_monitor.py

"""Base monitor with BFM sampling hook."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

import pyuvm

from . import utils_dv
from .base_clock_mixin import BaseClockMixin
from .base_item import BaseItem

T = TypeVar("T", bound=BaseItem)


class BaseMonitor(BaseClockMixin, pyuvm.uvm_monitor, Generic[T]):
    """Base monitor with clock synchronization and analysis port infrastructure.

    This monitor provides the foundation for observing DUT signals and publishing
    transactions. It integrates with the clock infrastructure via BaseClockMixin
    and manages the analysis port for broadcasting observed transactions.

    The monitor:
    - Maintains an analysis port for publishing transactions
    - Caches DUT and clock handles for efficient runtime access
    - Implements the standard monitor run loop pattern
    - Tracks the number of items observed

    Subclasses must implement:
        sample_dut_edge(): Wait for the appropriate sampling edge
        sample_dut(dut): Sample DUT signals and return a transaction

    Attributes:
        ap: Analysis port for broadcasting observed transactions
        item_count: Number of transactions observed (currently unused but available)

    Example:
        >>> class MyMonitor(BaseMonitor[MyItem]):
        ...     async def sample_dut_edge(self):
        ...         await self._clk.rising_edge
        ...         await ReadOnly()
        ...
        ...     async def sample_dut(self, dut):
        ...         item = MyItem()
        ...         item.data = self._get_val(dut.data.value)
        ...         return item
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self._clock_init_defaults()
        self.ap: pyuvm.uvm_analysis_port
        self.item_count: int = 0
        # Bind once to help hot paths
        self._get_val = utils_dv.get_signal_value_int

    def build_phase(self) -> None:
        self.logger.debug("build_phase begin")
        super().build_phase()
        self.ap = pyuvm.uvm_analysis_port("ap", self)
        self.logger.debug("build_phase end")

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        self._clock_pull_config()
        self._clock_bind_handles()
        self.logger.debug("end_of_elaboration_phase end")

    async def run_phase(self) -> None:
        self.logger.debug("run_phase begin")
        tr: T
        while True:
            tr = await self.sample_dut(self._dut)
            self.ap.write(tr)

    async def sample_dut_edge(self) -> None:
        """Wait until the edge to sample the DUT."""
        raise NotImplementedError("Implement sample_dut_edge here")

    async def sample_dut(self, dut: Any) -> T:
        """Return the next observed transaction (or None to skip)."""
        raise NotImplementedError("Implement sample_dut here")
