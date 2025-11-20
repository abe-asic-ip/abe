# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_clock_driver.py

"""Base clock driver (per-instance, config_db-driven)."""

from __future__ import annotations

from typing import cast

import cocotb
import pyuvm
from cocotb.clock import Clock
from cocotb.handle import LogicObject
from cocotb.task import Task
from cocotb.triggers import Timer

from . import utils_dv
from .base_clock_mixin import BaseClockMixin


class BaseClockDriver(BaseClockMixin, pyuvm.uvm_component):
    """Clock generation component using cocotb's Clock class.

    This driver creates and manages a clock signal for the DUT. It provides
    flexible configuration including clock period, initial phase, and startup
    delay. The driver can be disabled to allow HDL-driven clocks.

    Configuration (via config_db):
        clock_enable (bool): Enable clock driver (default: True)
                            If False, assumes clock driven in HDL
        clock_name (str): Name of clock signal (default: "clk")
        clock_period_ps (int): Clock period in picoseconds (default: 1000)
        clock_start_high (bool): Start with high phase (default: False)
        clock_init_delay_ps (int): Delay before starting clock (default: 0)

    The driver starts the clock in start_of_simulation_phase, either immediately
    or after clock_init_delay_ps if configured.

    Reference:
        https://github.com/advanced-uvm/second_edition/blob/master/recipes/2.clk_drv.sv

    Example:
        >>> # In test build_phase
        >>> uvm_config_db_set(self, "*", "clock_period_ps", 2000)
        >>> uvm_config_db_set(self, "*", "clock_start_high", True)
        >>> clock_driver = factory.create_component_by_type(
        ...     BaseClockDriver, parent_inst_path=path,
        ...     name="clock_driver", parent=self
        ... )
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self._clock_init_defaults()
        self.clock_enable: bool = True
        self.clock_start_high: bool = False
        self.clock_init_delay_ps: int = 0
        self._starter: Task | None = None
        self._task: Task | None = None

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        self._clock_pull_config()
        self._clock_driver_pull_config()
        self._clock_bind_handles()
        self.logger.debug("end_of_elaboration_phase end")

    def start_of_simulation_phase(self) -> None:
        self.logger.debug("start_of_simulation_phase begin")
        super().start_of_simulation_phase()
        if not self.clock_enable:
            self.logger.debug(
                "Clock '%s' disabled (assumed driven in HDL).", self.clock_name
            )
            return
        if self.clock_init_delay_ps > 0:
            self._starter = cocotb.start_soon(self._delayed_start())
        else:
            self._start_clock()
        self.logger.debug("start_of_simulation_phase end")

    def final_phase(self) -> None:
        self.logger.debug("final_phase begin")
        if self._starter is not None:
            self._starter.cancel()
            self._starter = None
        if self._task is not None:
            self._task.cancel()
            self._task = None
        super().final_phase()
        self.logger.debug("final_phase end")

    def _clock_driver_pull_config(self) -> None:
        """Read per-instance config from uvm_config_db (once) with defaults."""
        self.logger.debug("_clock_driver_pull_config begin")

        v = utils_dv.uvm_config_db_get_try(self, "clock_enable")
        if isinstance(v, bool):
            self.clock_enable = v

        v = utils_dv.uvm_config_db_get_try(self, "clock_start_high")
        if isinstance(v, bool):
            self.clock_start_high = v

        v = utils_dv.uvm_config_db_get_try(self, "clock_init_delay_ps")
        if isinstance(v, int):
            self.clock_init_delay_ps = v

        if self.clock_enable and self.clock_period_ps <= 0:
            raise ValueError(f"clock_period_ps must be > 0, got {self.clock_period_ps}")

        self.logger.debug("_clock_driver_pull_config end")

    async def _delayed_start(self) -> None:
        self.logger.debug("_delayed_start begin")
        try:
            await Timer(self.clock_init_delay_ps, unit="ps")
            if self.clock_enable and self._task is None:
                self._start_clock()
        finally:
            self._starter = None
        self.logger.debug("_delayed_start end")

    def _start_clock(self) -> None:
        self.logger.debug("_start_clock begin")
        assert self._clk is not None, "_start_clock before _clock_bind_handles"
        # Cast to LogicObject - clock signals are LogicObject subtype
        clk = cast(LogicObject, self._clk)
        self._task = cocotb.start_soon(
            Clock(clk, self.clock_period_ps, unit="ps").start(
                start_high=self.clock_start_high
            )
        )
        self.logger.debug(
            "Started clock: dut.%s period=%d ps clock_start_high=%s",
            self.clock_name,
            self.clock_period_ps,
            self.clock_start_high,
        )
        self.logger.debug("_start_clock end")
