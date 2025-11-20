# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_clock_mixin.py

"""Shared helpers for reading clk config, binding handles, and waiting edges."""

from __future__ import annotations

from typing import Any, cast

import pyuvm
from cocotb.handle import SimHandleBase
from cocotb.triggers import Timer

from . import utils_dv


class BaseClockMixin:
    """Mixin providing clock configuration and timing utilities.

    This mixin is used by drivers and monitors to standardize clock-related
    configuration and timing operations. It provides:

    - Configuration management for clock parameters
    - Signal handle binding for DUT and clock
    - Drive edge alignment with configurable skew

    Configuration:
        clock_name (str): Name of clock signal
        clock_period_ps (int): Clock period in picoseconds
        drive_falling_edge (bool): Drive on falling edge (default: True)
        drive_frac_after (float): Fraction of period after rising edge to drive
                                 (default: 0.20, i.e., 20% into clock period)
                                 Only used when drive_falling_edge=False

    Timing Strategies:
        1. Falling Edge: Drive on falling edge of clock (simple, common)
        2. Post-Edge Skew: Drive after rising edge with fractional delay
           (matches UVM best practices for setup/hold timing)

    The mixin is designed to be mixed into UVM components, requiring them to
    have logger and config_db access.

    Reference:
        C.E. Cummings, "Applying Stimulus & Sampling Outputs - UVM Verification
        Testing Techniques," SNUG 2016 (Austin)

    Example:
        >>> class MyDriver(BaseClockMixin, pyuvm.uvm_driver):
        ...     def __init__(self, name, parent):
        ...         super().__init__(name, parent)
        ...         self._clock_init_defaults(
        ...             name="clk", period_ps=2000, falling=False, frac_after=0.15
        ...         )
    """

    def _clock_init_defaults(
        self,
        *,
        name: str = "clk",
        period_ps: int = 1_000,
        falling: bool = True,
        frac_after: float = 0.20,
    ) -> None:
        """Det defaults in __init__ of the consumer."""
        self.clock_name: str = name
        self.clock_period_ps: int = period_ps
        self.drive_falling_edge: bool = falling
        self.drive_frac_after: float = frac_after
        self._dut: Any | None = None
        self._clk: SimHandleBase | None = None
        self._postedge_delay_ps: int = 0

    def _as_comp(self) -> pyuvm.uvm_component:
        """
        Type-narrow self for config_db utils.
        Safe: mixin is only used on components).
        """
        return cast(pyuvm.uvm_component, self)

    def _clock_pull_config(self) -> None:
        """Read per-instance config once (EoE)."""
        comp = self._as_comp()
        comp.logger.debug("_clock_pull_config begin")
        v = utils_dv.uvm_config_db_get_try(comp, "clock_name")
        if isinstance(v, str) and v:
            self.clock_name = v
        v = utils_dv.uvm_config_db_get_try(comp, "clock_period_ps")
        if isinstance(v, int):
            self.clock_period_ps = v
        if not self.drive_falling_edge and self.drive_frac_after > 0.0:
            if self.clock_period_ps <= 0:
                raise ValueError(
                    "clock_period_ps must be > 0 when using post-edge skew"
                )
        comp.logger.debug("_clock_pull_config end")

    def _clock_bind_handles(self) -> None:
        """Bind dut/signal once (EoE)."""
        comp = self._as_comp()
        comp.logger.debug("_clock_bind_handles begin")
        self._dut = utils_dv.uvm_config_db_get(comp, "dut")
        self._clk = utils_dv.get_signal(self._dut, self.clock_name)
        comp.logger.debug("_clock_bind_handles end")

    # Reference: C.E. Cummings, "Applying Stimulus & Sampling Outputs - UVM
    # Verification Testing Techniques," SNUG 2016 (Austin). We support driving
    # DUT inputs after the rising edge of the clock (default skew is 20% of
    # clock period. We also support driving DUT inputs on the falling edge
    # of the clock.

    def clock_compute_skew(self) -> None:
        """Compute skew once (EoE)."""
        comp = self._as_comp()
        comp.logger.debug("clock_compute_skew begin")
        if not self.drive_falling_edge:
            if not 0.0 <= self.drive_frac_after <= 1.0:
                raise ValueError(
                    f"drive_frac_after must be in [0.0, 1.0],"
                    f"got {self.drive_frac_after}"
                )
            self._postedge_delay_ps = int(self.clock_period_ps * self.drive_frac_after)
        comp.logger.debug("clock_compute_skew end")

    async def clock_drive_edge(self) -> None:
        """Align to the driving edge (runtime)."""
        assert (
            self._clk is not None
        ), "clock_drive_edge called before _clock_bind_handles"
        if self.drive_falling_edge:
            await self._clk.falling_edge
        else:
            await self._clk.rising_edge
            if self._postedge_delay_ps > 0:
                await Timer(self._postedge_delay_ps, unit="ps")
