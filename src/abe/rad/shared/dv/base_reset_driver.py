# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_reset_driver.py

"""Base reset driver."""

from __future__ import annotations

import pyuvm
from cocotb.triggers import NextTimeStep, ReadWrite

from . import utils_dv
from .base_clock_mixin import BaseClockMixin


# pylint: disable=duplicate-code
class BaseResetDriver(BaseClockMixin, pyuvm.uvm_component):
    # pylint: disable=line-too-long
    """Reset generation component with configurable pulse timing.

    This driver generates a synchronous reset pulse aligned to the clock's drive
    edge. It provides comprehensive configuration for reset behavior including
    polarity, duration, and settling time.

    Reset Sequence:
        1. Assert reset at time 0 using non-blocking write (avoids race conditions)
        2. Hold reset for reset_cycles clock edges
        3. Deassert reset synchronously on a clock edge
        4. Wait reset_settle_cycles for DUT to stabilize

    Configuration (via config_db):
        reset_enable (bool): Enable reset driver (default: True)
                            If False, assumes reset driven in HDL
        reset_name (str): Name of reset signal (default: "rst_n")
        reset_active_low (bool): True for active-low reset (default: True)
        reset_cycles (int): Number of clock cycles to hold reset (default: 10)
        reset_settle_cycles (int): Clock cycles after deassertion to settle (default: 10)

    The driver uses clock_drive_edge() from BaseClockMixin to ensure reset
    assertions align with the configured drive edge (falling edge or post-rising
    edge with skew).

    Reference:
        https://github.com/advanced-uvm/second_edition/blob/master/recipes/3.rst_drv.sv
        C.E. Cummings, "Applying Stimulus & Sampling Outputs," SNUG 2016

    Example:
        >>> # In test build_phase
        >>> uvm_config_db_set(self, "*", "reset_cycles", 20)
        >>> uvm_config_db_set(self, "*", "reset_active_low", False)
        >>> reset_driver = factory.create_component_by_type(
        ...     BaseResetDriver, parent_inst_path=path,
        ...     name="reset_driver", parent=self
        ... )
    """
    # pylint: enable=line-too-long

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self._clock_init_defaults()
        self.reset_enable: bool = True
        self.reset_name: str = "rst_n"
        self.reset_active_low: bool = True
        self.reset_cycles: int = 10
        self.reset_settle_cycles: int = 10

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        self._clock_pull_config()
        self._clock_bind_handles()
        self.clock_compute_skew()
        self._reset_pull_config()
        self.logger.debug("end_of_elaboration_phase end")

    def start_of_simulation_phase(self) -> None:
        self.logger.debug("start_of_simulation_phase begin")
        super().start_of_simulation_phase()
        if not self.reset_enable:
            self.logger.debug(
                "Reset '%s' disabled (assumed driven in HDL).", self.reset_name
            )
        self.logger.debug("start_of_simulation_phase end")

    def _reset_pull_config(self) -> None:
        """Read per-instance config from uvm_config_db (once) with defaults."""
        self.logger.debug("_reset_pull_config begin")

        v = utils_dv.uvm_config_db_get_try(self, "reset_enable")
        if isinstance(v, bool):
            self.reset_enable = v

        v = utils_dv.uvm_config_db_get_try(self, "reset_name")
        if isinstance(v, str) and v:
            self.reset_name = v

        v = utils_dv.uvm_config_db_get_try(self, "reset_active_low")
        if isinstance(v, bool):
            self.reset_active_low = v

        v = utils_dv.uvm_config_db_get_try(self, "reset_cycles")
        if isinstance(v, int):
            self.reset_cycles = v

        v = utils_dv.uvm_config_db_get_try(self, "reset_settle_cycles")
        if isinstance(v, int):
            self.reset_settle_cycles = v

        if self.reset_enable:
            if self.reset_cycles < 0:
                raise ValueError("reset_cycles must be >= 0")
            if self.reset_settle_cycles < 0:
                raise ValueError("reset_settle_cycles must be >= 0")

        self.logger.debug("_reset_pull_config end")

    async def run_phase(self) -> None:
        self.logger.debug("run_phase begin")
        if not self.reset_enable:
            return
        await self.pulse_reset()
        self.logger.debug("run_phase end")

    async def pulse_reset(self) -> None:
        """Assert/deassert reset on the same drive edge as stimuli."""

        self.logger.debug("pulse_reset begin")

        rst = getattr(self._dut, self.reset_name)
        active = 0 if self.reset_active_low else 1
        inactive = 1 - active

        # Reference: SNUG 2016 "Applying Stimulus & Sampling Outputs." Assert reset at
        # time 0 using a non-blocking-style write and advance one delta cycle to avoid
        # races.
        rst.value = active
        await ReadWrite()  # like an NBA at t=0
        await NextTimeStep()  # advance one delta to be extra-safe

        # Hold reset for exactly N drive edges (synchronous semantics)
        for _ in range(max(0, self.reset_cycles)):
            await self.clock_drive_edge()

        # Deassert reset at the drive edges (synchronous semantics)
        rst.value = inactive

        # Allow M settle cycles, again in drive cadence
        for _ in range(max(0, self.reset_settle_cycles)):
            await self.clock_drive_edge()

        self.logger.debug("pulse_reset end")
