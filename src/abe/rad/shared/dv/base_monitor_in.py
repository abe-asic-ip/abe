# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_monitor_in.py

"""Base monitor for DUT inputs."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from cocotb.triggers import ReadOnly

from .base_item import BaseItem
from .base_monitor import BaseMonitor

T = TypeVar("T", bound=BaseItem)


class BaseMonitorIn(BaseMonitor[T], Generic[T]):  # pylint: disable=too-many-ancestors
    """Monitor for observing DUT input signals.

    This monitor samples DUT inputs at the rising clock edge using the ReadOnly
    trigger to ensure all drivers have settled. This timing methodology is
    consistent with SystemVerilog's #1step sampling.

    Sampling Strategy:
        1. Wait for rising edge of clock
        2. Enter ReadOnly region (equivalent to SV #1step)
        3. Sample all input signals in a stable state

    This ensures that inputs are sampled after all drivers have applied their
    values but before any sequential logic updates.

    Subclasses must implement:
        sample_dut(dut): Sample DUT input signals and return a transaction

    Reference:
        C.E. Cummings, "Applying Stimulus & Sampling Outputs - UVM Verification
        Testing Techniques," SNUG 2016 (Austin)

    Example:
        >>> class MyInputMonitor(BaseMonitorIn[MyItem]):
        ...     async def sample_dut(self, dut):
        ...         await self.sample_dut_edge()
        ...         item = MyItem()
        ...         item.addr = self._get_val(dut.addr.value)
        ...         return item
    """

    async def sample_dut_edge(self) -> None:
        assert (
            self._clk is not None
        ), "sample_dut_edge called before _clock_bind_handles"
        await self._clk.rising_edge
        await ReadOnly()

    async def sample_dut(self, dut: Any) -> T:
        """Return the next observed transaction (or None to skip)."""
        raise NotImplementedError("Implement sample_dut here")
