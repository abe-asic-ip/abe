# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_test.py

"""Base test scaffold (factory-friendly config + env creation)."""

from __future__ import annotations

import logging
import os

import cocotb
import pyuvm
from cocotb.triggers import Timer
from pyuvm import ConfigDB

from . import utils_cli, utils_dv
from .base_clock_driver import BaseClockDriver
from .base_env import BaseEnv
from .base_reset_driver import BaseResetDriver
from .base_sequence import BaseSequence


class BaseTest(pyuvm.uvm_test):
    """Base test providing configuration, factory overrides, and environment setup.

    This test implements the standard UVM test structure with comprehensive
    configuration management, factory override support, and phase-based execution.
    It creates and manages clock drivers, reset drivers, and the verification
    environment.

    UVM Phases:
        build_phase: Configure factory, create components
        end_of_elaboration_phase: Set logging levels, print configuration
        start_of_simulation_phase: Log configuration/seed, print factory/config_db
        run_phase: Execute test sequence and drain pipeline

    Components Created:
        clock_driver (BaseClockDriver): Clock generation
        reset_driver (BaseResetDriver): Reset generation
        env (BaseEnv): Verification environment with agents/scoreboard/coverage

    Subclasses must implement:
        set_factory_overrides(): Set UVM factory type/instance overrides

    Optional overrides:
        build_config(): Additional configuration (calls base for drain_time_ps)
        build_clocks(): Custom clock setup (default: single clock from CLI)
        build_resets(): Custom reset setup (default: single reset from CLI)
        build_envs(): Custom environment setup (default: single env from CLI)
        drain(time_ps): Custom drain timing (default: uses config_db)

    Configuration Sources (precedence: env > plusargs > defaults):
        Clock: CLOCK_ENABLE, CLOCK_NAME, CLOCK_PERIOD_PS, CLOCK_START_HIGH,
               CLOCK_INIT_DELAY_PS
        Reset: RESET_ENABLE, RESET_NAME, RESET_ACTIVE_LOW, RESET_CYCLES,
               RESET_SETTLE_CYCLES
        Environment: CHECK_EN, COVERAGE_EN, SB_FAIL_ON_ERROR,
                    SB_ERROR_QUIT_COUNT, SB_INITIAL_FLUSH_NUM
        Test: DRAIN_TIME_PS

    Factory Overrides:
        Supports both code-based (set_factory_overrides) and CLI-based
        (+uvm_set_type_override, +uvm_set_inst_override) factory configuration.

    Reference:
        UVM Class Reference Manual (Accellera)
        C.E. Cummings, "Applying Stimulus & Sampling Outputs," SNUG 2016

    Example:
        >>> class MyTest(BaseTest):
        ...     def set_factory_overrides(self):
        ...         factory.set_type_override_by_type(
        ...             BaseItem, MyItem
        ...         )
        ...         factory.set_type_override_by_type(
        ...             BaseSequence, MySequence
        ...         )
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)

        self.clock_driver: BaseClockDriver
        self.reset_driver: BaseResetDriver
        self.env: BaseEnv

    def build_phase(self) -> None:
        self.logger.debug("build_phase begin")
        self.publish_dut()
        self.set_factory_overrides()  # code-defined overrides
        utils_cli.apply_factory_overrides_from_plusargs(self.logger)
        super().build_phase()
        self.build_config()
        self.build_clocks()
        self.build_resets()
        self.build_envs()
        self.logger.debug("build_phase end")

    def end_of_elaboration_phase(self) -> None:
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        self.set_logging_level_hier(utils_dv.desired_log_level())
        self.logger.debug("end_of_elaboration_phase end")

    def start_of_simulation_phase(self) -> None:
        self.logger.debug("start_of_simulation_phase begin")
        super().start_of_simulation_phase()
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("printing uvm_config_db")
            print(ConfigDB())
            self.logger.debug("printing factory")
            pyuvm.uvm_factory().print(debug_level=1)

        self._log_run_seed()
        self.logger.debug("start_of_simulation_phase end")

    async def run_phase(self) -> None:
        self.logger.debug("run_phase begin")
        self.raise_objection()
        seq = pyuvm.uvm_factory().create_object_by_type(BaseSequence, name="seq")
        await seq.start(self.env.agents[0].sqr)
        await self.drain()
        self.drop_objection()
        self.logger.debug("run_phase begin")

    def publish_dut(self) -> None:
        """Publish DUT via config_db."""
        utils_dv.uvm_config_db_set(self, "*", "dut", cocotb.top)

    def set_factory_overrides(self) -> None:
        """Override in subclasses to set uvm_factory() overrides."""
        raise NotImplementedError("Implement set_factory_overrides here")

    def build_config(self) -> None:
        """Get and set testbench config properties."""
        drain_time_ps = utils_cli.get_int_setting("DRAIN_TIME_PS", 10_000)
        if drain_time_ps > 0:
            utils_dv.uvm_config_db_set(self, "", "drain_time_ps", drain_time_ps)
            utils_dv.uvm_config_db_set(self, "*", "drain_time_ps", drain_time_ps)

    def build_clocks(self) -> None:
        """
        The default is a single clock with the default configuration properties listed
        in Base ClockMixin and BaseClockDriver. If your testbench needs more than one
        clock or needs non-default configuration properties, override this method.
        Bench-level defaults are placed under *. Override as needed.
        """
        clock_enable = utils_cli.get_bool_setting("CLOCK_ENABLE", True)
        clock_name = utils_cli.get_str_setting("CLOCK_NAME", "clk")
        clock_period_ps = utils_cli.get_int_setting("CLOCK_PERIOD_PS", 1_000)
        clock_start_high = utils_cli.get_bool_setting("CLOCK_START_HIGH", False)
        clock_init_delay_ps = utils_cli.get_int_setting("CLOCK_INIT_DELAY_PS", 0)

        utils_dv.uvm_config_db_set(self, "*", "clock_enable", clock_enable)
        utils_dv.uvm_config_db_set(self, "*", "clock_name", clock_name)
        utils_dv.uvm_config_db_set(self, "*", "clock_period_ps", clock_period_ps)
        utils_dv.uvm_config_db_set(self, "*", "clock_start_high", clock_start_high)
        utils_dv.uvm_config_db_set(
            self, "*", "clock_init_delay_ps", clock_init_delay_ps
        )

        self.clock_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseClockDriver,
            parent_inst_path=self.get_full_name(),
            name="clock_driver",
            parent=self,
        )

    def build_resets(self) -> None:
        """
        The default is a single reset with the default configuration properties listed
        in BaseResetDriver. If your testbench needs more than one reset or needs
        non-default configuration properties, override this method. Bench-level defaults
        are placed under *. Override as needed.
        """
        reset_enable = utils_cli.get_bool_setting("RESET_ENABLE", True)
        reset_name = utils_cli.get_str_setting("RESET_NAME", "rst_n")
        reset_active_low = utils_cli.get_bool_setting("RESET_ACTIVE_LOW", True)
        reset_cycles = utils_cli.get_int_setting("RESET_CYCLES", 10)
        reset_settle_cycles = utils_cli.get_int_setting("RESET_SETTLE_CYCLES", 10)

        utils_dv.uvm_config_db_set(self, "*", "reset_enable", reset_enable)
        utils_dv.uvm_config_db_set(self, "*", "reset_name", reset_name)
        utils_dv.uvm_config_db_set(self, "*", "reset_active_low", reset_active_low)
        utils_dv.uvm_config_db_set(self, "*", "reset_cycles", reset_cycles)
        utils_dv.uvm_config_db_set(
            self, "*", "reset_settle_cycles", reset_settle_cycles
        )

        self.reset_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseResetDriver,
            parent_inst_path=self.get_full_name(),
            name="reset_driver",
            parent=self,
        )

    def build_envs(self) -> None:
        """
        The default is a single environment. If your testbench needs more than one
        environment or needs non-default configuration properties, override this
        method. Bench-level defaults are placed under *. Override as needed.
        """
        check_en = utils_cli.get_bool_setting("CHECK_EN", True)
        coverage_en = utils_cli.get_bool_setting("COVERAGE_EN", True)
        sb_fail_on_error = utils_cli.get_bool_setting("SB_FAIL_ON_ERROR", True)
        sb_error_quit_count = utils_cli.get_int_setting("SB_ERROR_QUIT_COUNT", 1)
        sb_initial_flush_num = utils_cli.get_int_setting("SB_INITIAL_FLUSH_NUM", 0)

        utils_dv.uvm_config_db_set(self, "env*", "check_en", check_en)
        utils_dv.uvm_config_db_set(self, "env*", "coverage_en", coverage_en)
        utils_dv.uvm_config_db_set(
            self, "env*", "sb_initial_flush_num", sb_initial_flush_num
        )
        utils_dv.uvm_config_db_set(self, "env*", "sb_fail_on_error", sb_fail_on_error)
        utils_dv.uvm_config_db_set(
            self, "env*", "sb_error_quit_count", sb_error_quit_count
        )

        self.env = pyuvm.uvm_factory().create_component_by_type(
            BaseEnv, parent_inst_path=self.get_full_name(), name="env", parent=self
        )

    def _log_run_seed(self) -> None:
        seed = (
            os.getenv("COCOTB_RANDOM_SEED")  # cocotb 2.x
            or os.getenv("RANDOM_SEED")  # cocotb 1.x
            or os.getenv("COCOTB_SEED")  # legacy/compat
        )
        if seed:
            self.logger.debug("Run seed: %s", seed)
        else:
            self.logger.debug("Run seed: (unset)")

    async def drain(self, time_ps: int | None = None) -> None:
        """
        The UVM Class Reference Manual
        https://www.accellera.org/images/downloads/standards/uvm/UVM_Class_Reference_Manual_1.2.pdf
        describes set_drain_time(). This functionality is not directly available in
        pyuvm, so we implement our own. Wait simulation time instead of clocks to
        have a consistent methodology regardless of the number of clocks.
        """

        self.logger.debug("drain begin")

        dt = utils_dv.uvm_config_db_get_try(self, "drain_time_ps")

        if time_ps is None and isinstance(dt, int) and dt > 0:
            time_ps = dt

        if time_ps is not None:
            n = max(0, int(time_ps))
            self.logger.debug("drain: %s ps begin", format(n, "_d"))
            await Timer(n, unit="ps")
            self.logger.debug("drain: %s ps end", format(n, "_d"))

        self.logger.debug("drain end")
