# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_reset_monitor.py

"""Base reset monitor."""


from __future__ import annotations

from typing import Any

import pyuvm
from cocotb.handle import SimHandleBase
from cocotb.triggers import ReadOnly

from . import utils_dv
from .base_monitor_in import BaseMonitorIn
from .base_reset_item import BaseResetItem


class BaseResetMonitor(
    BaseMonitorIn[BaseResetItem]
):  # pylint: disable=too-many-ancestors disable=duplicate-code
    """Monitor for observing reset signal changes and publishing reset events.

    This monitor watches a reset signal and publishes a transaction whenever the
    reset value changes. It samples the reset at time 0 and then on every value
    change, using ReadOnly() to ensure all drivers have settled.

    The monitor translates raw signal levels into polarity-neutral semantic events
    (asserted/deasserted) based on the reset_active_low configuration.

    Behavior:
        1. At t=0: Sample initial reset state and publish transaction
        2. Runtime: Wake on reset value changes, sample in ReadOnly, publish if changed

    Configuration (via config_db):
        reset_name (str): Name of reset signal (default: "rst_n")
        reset_active_low (bool): True for active-low reset (default: True)

    Published Transactions:
        Each BaseResetItem contains:
        - value: Raw signal level (0 or 1)
        - active: Semantic state (True=asserted, False=deasserted)

    The polarity-neutral design allows downstream components (drivers, reference
    models, predictors) to respond to reset using the 'active' field regardless
    of the actual reset polarity.

    Reference:
        UVM reset handling best practices - publish semantic reset events rather
        than raw levels

    Example:
        >>> # Monitor will publish reset transactions to connected components
        >>> mon_rst = factory.create_component_by_type(
        ...     BaseResetMonitor, parent_inst_path=path,
        ...     name="mon_rst", parent=self
        ... )
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.reset_name: str = "rst_n"
        self.reset_active_low: bool = True
        self._dut: Any | None = None
        self._rst: SimHandleBase | None = None
        self._last_val: int | None = None

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        self._reset_pull_config()
        self._reset_bind_handles()
        self.logger.debug("end_of_elaboration_phase end")

    def _reset_pull_config(self) -> None:
        """Read per-instance config from uvm_config_db (once) with defaults."""
        self.logger.debug("_reset_pull_config begin")
        v = utils_dv.uvm_config_db_get_try(self, "reset_name")
        if isinstance(v, str) and v:
            self.reset_name = v
        v = utils_dv.uvm_config_db_get_try(self, "reset_active_low")
        if isinstance(v, bool):
            self.reset_active_low = v
        self.logger.debug("_reset_pull_config end")

    def _reset_bind_handles(self) -> None:
        """Bind dut once (EoE)."""
        self.logger.debug("_reset_bind_handles begin")
        self._dut = utils_dv.uvm_config_db_get(self, "dut")
        self._rst = utils_dv.get_signal(self._dut, self.reset_name)
        self.logger.debug("_reset_bind_handles end")

    async def run_phase(self) -> None:
        self.logger.debug("run_phase begin")

        assert self._rst is not None, "run_phase called before _reset_bind_handles"
        reset_signal = getattr(self._dut, self.reset_name)

        # t=0
        await ReadOnly()
        val = utils_dv.get_signal_value_int(reset_signal.value)
        if val is not None:
            tr = pyuvm.uvm_factory().create_object_by_type(BaseResetItem, name="tr")
            tr.value = val
            tr.active = self.calc_active(val)
            self.ap.write(tr)
            self.logger.debug(f"run_phase reset tr: {tr}")
            self._last_val = val

        # Reference: General UVM reset handling best practices—publish semantic reset
        # events (assert/deassert) rather than raw levels; downstream models use the
        # active boolean, making the bench polarity-neutral.
        while True:
            await self._rst.value_change  # wake up only on reset change
            await ReadOnly()  # sample after all drivers settle
            val = utils_dv.get_signal_value_int(reset_signal.value)
            if val is not None and val != self._last_val:
                tr = pyuvm.uvm_factory().create_object_by_type(BaseResetItem, name="tr")
                tr.value = val
                tr.active = self.calc_active(val)
                self.ap.write(tr)
                self.logger.debug(f"run_phase reset tr: {tr}")
                self._last_val = val

    def calc_active(self, level: int) -> bool:
        """Level: 0/1; active_low chooses polarity."""
        return (level == 0) if self.reset_active_low else (level != 0)

    async def sample_dut(self, dut: Any) -> BaseResetItem:
        """Return the next observed transaction (or None to skip)."""
        raise NotImplementedError(
            "BaseResetMonitor uses run_phase(), not sample_dut()."
        )
