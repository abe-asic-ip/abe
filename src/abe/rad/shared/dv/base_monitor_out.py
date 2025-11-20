# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_monitor_out.py

"""Base monitor for DUT outputs."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

import pyuvm
from cocotb.triggers import ReadOnly, Timer

from .base_item import BaseItem
from .base_monitor import BaseMonitor

T = TypeVar("T", bound=BaseItem)


class BaseMonitorOut(BaseMonitor[T], Generic[T]):  # pylint: disable=too-many-ancestors
    """Monitor for observing DUT output signals.

    This monitor samples DUT outputs in the read-only phase just before the next
    active edge, consistent with SystemVerilog's #1step timing. This captures
    the stable output values after sequential logic has updated.

    Sampling Strategy:
        1. Wait for rising edge of clock (outputs update)
        2. Delay to just before next rising edge (default: period - 1ps)
        3. Enter ReadOnly region (equivalent to SV #1step)
        4. Sample all output signals in their stable state

    Configuration:
        pre_ps (int): Time in ps before next edge to sample (default: 1)
                     Must be: 0 <= pre_ps < clock_period_ps

    The preedge_delay_ps is automatically computed as: clock_period_ps - pre_ps

    Subclasses must implement:
        sample_dut(dut): Sample DUT output signals and return a transaction

    Reference:
        C.E. Cummings, "Applying Stimulus & Sampling Outputs - UVM Verification
        Testing Techniques," SNUG 2016 (Austin)

    Example:
        >>> class MyOutputMonitor(BaseMonitorOut[MyItem]):
        ...     async def sample_dut(self, dut):
        ...         await self.sample_dut_edge()
        ...         item = MyItem()
        ...         item.result = self._get_val(dut.result.value)
        ...         return item
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.pre_ps: int = 1
        self.preedge_delay_ps: int = 0

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        if self.pre_ps < 0:
            raise ValueError(f"self.pre_ps must be >= 0, got {self.pre_ps}")
        if self.pre_ps >= self.clock_period_ps:
            raise ValueError(
                (
                    f"self.pre_ps={self.pre_ps} must be less than"
                    f"self.clock_period_ps={self.clock_period_ps}"
                )
            )
        self.preedge_delay_ps = self.clock_period_ps - self.pre_ps
        self.logger.debug("end_of_elaboration_phase end")

    async def sample_dut_edge(self) -> None:
        """
        Wait rising edge, then delay to just-before next edge.
        Finalize with ReadOnly to be consistent with SV #1step.
        """
        assert (
            self._clk is not None
        ), "sample_dut_edge called before _clock_bind_handles"
        await self._clk.rising_edge
        if self.preedge_delay_ps > 0:
            await Timer(self.preedge_delay_ps, unit="ps")
        await ReadOnly()

    async def sample_dut(self, dut: Any) -> T:
        """Return the next observed transaction (or None to skip)."""
        raise NotImplementedError("Implement sample_dut here")
