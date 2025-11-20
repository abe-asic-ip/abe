# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_driver.py

"""Base driver with BFM hooks folded in."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

import pyuvm
from cocotb.triggers import Event, NextTimeStep, ReadWrite

from . import utils_dv
from .base_clock_mixin import BaseClockMixin
from .base_item import BaseItem

T = TypeVar("T", bound=BaseItem)


class BaseDriver(BaseClockMixin, pyuvm.uvm_driver, Generic[T]):
    """UVM driver with clock synchronization and reset handling.

    This driver provides a complete framework for driving DUT inputs with proper
    timing alignment and reset awareness. It integrates with the clock infrastructure
    via BaseClockMixin and handles reset events through level-triggered events.

    The driver:
    - Applies initial DUT input values at time 0 with proper delta cycle handling
    - Waits for reset assertion and deassertion before driving transactions
    - Provides timing alignment via clock_drive_edge() from BaseClockMixin
    - Uses level-triggered events to track reset state

    Subclasses must implement:
        drive_item(dut, tr): Drive DUT signals for one transaction

    Attributes:
        initial_dut_input_values: Dict mapping signal names to initial values
        seq_item_port: TLM port for getting transactions from sequencer

    Reset Events:
        _rst_asserted: Event set when reset is active
        _rst_deasserted: Event set when reset is inactive

    Reference:
        C.E. Cummings, "Applying Stimulus & Sampling Outputs," SNUG 2016

    Example:
        >>> class MyDriver(BaseDriver[MyItem]):
        ...     async def drive_item(self, dut, tr):
        ...         await self.clock_drive_edge()
        ...         dut.data.value = tr.data
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self._clock_init_defaults()
        self.initial_dut_input_values: dict[str, int] = {}
        self._reset_active: bool = False
        # Level-triggered events reflect current reset state
        self._rst_asserted: Event = Event()
        self._rst_deasserted: Event = Event()
        self._rst_deasserted.set()  # default: not in reset at t=0

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        self._clock_pull_config()
        self._clock_bind_handles()
        self.clock_compute_skew()
        self.logger.debug("end_of_elaboration_phase begin")

    async def run_phase(self) -> None:
        self.logger.debug("run_phase begin")
        tr: T
        await self.apply_initial_dut_inputs()
        await self.wait_for_reset_active()
        await self.wait_for_reset_inactive()
        while True:
            tr = await self.seq_item_port.get_next_item()
            await self.drive_item(self._dut, tr)
            self.seq_item_port.item_done()

    async def apply_initial_dut_inputs(self) -> None:
        """
        Reference: SNUG 2016 "Applying Stimulus & Sampling Outputs." Apply DUT
        inputs at time 0 using a non-blocking-style write and advance one delta
        cycle to avoid races.
        """
        self.logger.debug("apply_initial_dut_inputs begin")
        for sig_name, val in self.initial_dut_input_values.items():
            getattr(self._dut, sig_name).value = val
        await ReadWrite()  # like an NBA at t=0
        await NextTimeStep()  # advance one delta to be extra-safe
        self.logger.debug("apply_initial_dut_inputs end")

    async def wait_for_reset_active(self) -> None:
        """Block until reset is asserted (polarity-neutral)."""
        self.logger.debug("wait_for_reset_active begin")
        await self._rst_asserted.wait()
        self.logger.debug("wait_for_reset_active end")

    async def wait_for_reset_inactive(self) -> None:
        """Block until reset is deasserted (polarity-neutral)."""
        self.logger.debug("wait_for_reset_inactive begin")
        await self._rst_deasserted.wait()
        self.logger.debug("wait_for_reset_inactive end")

    def reset_change(self, value: int, active: bool) -> None:
        """Called by BaseResetSink on reset level changes."""
        self.logger.debug("reset_change begin")
        self._reset_active = active
        if active:
            self._rst_asserted.set()
            self._rst_deasserted.clear()
        else:
            self._rst_deasserted.set()
            self._rst_asserted.clear()
        self.logger.debug("reset_change end: value=%d active=%s", value, active)

    async def drive_item(self, dut: Any, tr: T) -> None:
        """Drive DUT signals for one transaction."""
        raise NotImplementedError("Implement DUT signal driving here")
