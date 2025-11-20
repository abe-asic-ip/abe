# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/test_rad_async_fifo.py


"""Tests for rad_async_fifo verification."""

from __future__ import annotations

import cocotb
import pyuvm

from abe.rad.rad_async_fifo.dv.rad_async_fifo_sb import RadAsyncFifoSbPredictor
from abe.rad.shared.dv import (
    BaseClockDriver,
    BaseCoverage,
    BaseEnv,
    BaseRefModel,
    BaseResetDriver,
    BaseResetSink,
    BaseSb,
    BaseSbPredictor,
    BaseSequence,
    BaseTest,
    utils_cli,
    utils_dv,
)
from abe.rad.shared.dv.base_driver import BaseDriver
from abe.rad.shared.dv.base_item import BaseItem
from abe.rad.shared.dv.base_monitor_in import BaseMonitorIn
from abe.rad.shared.dv.base_monitor_out import BaseMonitorOut

from .rad_async_fifo_coverage import RadAsyncFifoCoverage
from .rad_async_fifo_driver import (
    RadAsyncFifoReadDriver,
    RadAsyncFifoWriteDriver,
)
from .rad_async_fifo_env import RadAsyncFifoEnv
from .rad_async_fifo_item import (
    RadAsyncFifoReadItem,
    RadAsyncFifoWriteItem,
)
from .rad_async_fifo_monitor_in import (
    RadAsyncFifoReadMonitorIn,
    RadAsyncFifoWriteMonitorIn,
)
from .rad_async_fifo_monitor_out import (
    RadAsyncFifoReadMonitorOut,
    RadAsyncFifoWriteMonitorOut,
)
from .rad_async_fifo_ref_model import RadAsyncFifoRefModel
from .rad_async_fifo_reset_sink import RadAsyncFifoResetSink
from .rad_async_fifo_sb import RadAsyncFifoSb
from .rad_async_fifo_sequence import (
    RadAsyncFifoReadSequence,
    RadAsyncFifoWriteSequence,
)


@pyuvm.test()
class RadAsyncFifoBaseTest(BaseTest):
    """Basic async FIFO test with independent clock domains and resets.

    Creates dual clock drivers (wclk, rclk) and dual reset drivers (wrst_n, rrst_n).
    Runs concurrent write and read sequences in their respective domains.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        # Declare additional clock/reset drivers for dual-clock design
        self.wclk_driver: BaseClockDriver
        self.rclk_driver: BaseClockDriver
        self.wrst_driver: BaseResetDriver
        self.rrst_driver: BaseResetDriver

    def build_config(self) -> None:
        """Configure scoreboard to handle async FIFO initial state."""
        super().build_config()
        # Skip first several comparisons after reset to allow CDC synchronization
        # The DUT may have undefined state during CDC synchronization after reset
        utils_dv.uvm_config_db_set(
            self, "env.sb.comparator", "sb_initial_flush_num", 10
        )

    def build_clocks(self) -> None:
        """Build write and read clock drivers for dual-clock FIFO."""
        # Write clock configuration
        wclk_enable = utils_cli.get_bool_setting("WCLK_ENABLE", True)
        wclk_period_ps = utils_cli.get_int_setting("WCLK_PERIOD_PS", 1_000)
        wclk_start_high = utils_cli.get_bool_setting("WCLK_START_HIGH", False)
        wclk_init_delay_ps = utils_cli.get_int_setting("WCLK_INIT_DELAY_PS", 0)

        # Read clock configuration
        rclk_enable = utils_cli.get_bool_setting("RCLK_ENABLE", True)
        rclk_period_ps = utils_cli.get_int_setting("RCLK_PERIOD_PS", 1_200)
        rclk_start_high = utils_cli.get_bool_setting("RCLK_START_HIGH", False)
        rclk_init_delay_ps = utils_cli.get_int_setting("RCLK_INIT_DELAY_PS", 0)

        # Create write clock driver
        self.wclk_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseClockDriver,
            parent_inst_path=self.get_full_name(),
            name="wclk_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "wclk_driver", "clock_enable", wclk_enable)
        utils_dv.uvm_config_db_set(self, "wclk_driver", "clock_name", "wclk")
        utils_dv.uvm_config_db_set(
            self, "wclk_driver", "clock_period_ps", wclk_period_ps
        )
        utils_dv.uvm_config_db_set(
            self, "wclk_driver", "clock_start_high", wclk_start_high
        )
        utils_dv.uvm_config_db_set(
            self, "wclk_driver", "clock_init_delay_ps", wclk_init_delay_ps
        )

        # Create read clock driver
        self.rclk_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseClockDriver,
            parent_inst_path=self.get_full_name(),
            name="rclk_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "rclk_driver", "clock_enable", rclk_enable)
        utils_dv.uvm_config_db_set(self, "rclk_driver", "clock_name", "rclk")
        utils_dv.uvm_config_db_set(
            self, "rclk_driver", "clock_period_ps", rclk_period_ps
        )
        utils_dv.uvm_config_db_set(
            self, "rclk_driver", "clock_start_high", rclk_start_high
        )
        utils_dv.uvm_config_db_set(
            self, "rclk_driver", "clock_init_delay_ps", rclk_init_delay_ps
        )

        # Set agent0 (write agent) configurations to use write clock
        utils_dv.uvm_config_db_set(self, "env.agent0.drv", "clock_name", "wclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent0.drv", "clock_period_ps", wclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_in", "clock_name", "wclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent0.mon_in", "clock_period_ps", wclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_out", "clock_name", "wclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent0.mon_out", "clock_period_ps", wclk_period_ps
        )

        # Set agent1 (read agent) configurations to use read clock
        utils_dv.uvm_config_db_set(self, "env.agent1.drv", "clock_name", "rclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent1.drv", "clock_period_ps", rclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_in", "clock_name", "rclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent1.mon_in", "clock_period_ps", rclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_out", "clock_name", "rclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent1.mon_out", "clock_period_ps", rclk_period_ps
        )

        # Keep base reference for backward compatibility (points to write clock)
        self.clock_driver = self.wclk_driver

    def build_resets(self) -> None:
        """Build write and read reset drivers for dual-clock FIFO."""
        # Write reset configuration
        wrst_enable = utils_cli.get_bool_setting("WRST_ENABLE", True)
        wrst_active_low = utils_cli.get_bool_setting("WRST_ACTIVE_LOW", True)
        wrst_cycles = utils_cli.get_int_setting("WRST_CYCLES", 10)
        wrst_settle_cycles = utils_cli.get_int_setting("WRST_SETTLE_CYCLES", 10)

        # Read reset configuration
        rrst_enable = utils_cli.get_bool_setting("RRST_ENABLE", True)
        rrst_active_low = utils_cli.get_bool_setting("RRST_ACTIVE_LOW", True)
        rrst_cycles = utils_cli.get_int_setting("RRST_CYCLES", 10)
        rrst_settle_cycles = utils_cli.get_int_setting("RRST_SETTLE_CYCLES", 10)

        # Create write reset driver
        self.wrst_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseResetDriver,
            parent_inst_path=self.get_full_name(),
            name="wrst_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "wrst_driver", "reset_enable", wrst_enable)
        utils_dv.uvm_config_db_set(self, "wrst_driver", "reset_name", "wrst_n")
        utils_dv.uvm_config_db_set(
            self, "wrst_driver", "reset_active_low", wrst_active_low
        )
        utils_dv.uvm_config_db_set(self, "wrst_driver", "reset_cycles", wrst_cycles)
        utils_dv.uvm_config_db_set(
            self, "wrst_driver", "reset_settle_cycles", wrst_settle_cycles
        )
        utils_dv.uvm_config_db_set(self, "wrst_driver", "clock_name", "wclk")

        # Create read reset driver
        self.rrst_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseResetDriver,
            parent_inst_path=self.get_full_name(),
            name="rrst_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "rrst_driver", "reset_enable", rrst_enable)
        utils_dv.uvm_config_db_set(self, "rrst_driver", "reset_name", "rrst_n")
        utils_dv.uvm_config_db_set(
            self, "rrst_driver", "reset_active_low", rrst_active_low
        )
        utils_dv.uvm_config_db_set(self, "rrst_driver", "reset_cycles", rrst_cycles)
        utils_dv.uvm_config_db_set(
            self, "rrst_driver", "reset_settle_cycles", rrst_settle_cycles
        )
        utils_dv.uvm_config_db_set(self, "rrst_driver", "clock_name", "rclk")

        # Set agent0 (write agent) to use write reset
        utils_dv.uvm_config_db_set(self, "env.agent0.drv", "reset_name", "wrst_n")
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_in", "reset_name", "wrst_n")
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_out", "reset_name", "wrst_n")

        # Set agent1 (read agent) to use read reset
        utils_dv.uvm_config_db_set(self, "env.agent1.drv", "reset_name", "rrst_n")
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_in", "reset_name", "rrst_n")
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_out", "reset_name", "rrst_n")

        # Configure write reset monitor (in RadAsyncFifoEnv)
        utils_dv.uvm_config_db_set(self, "env.mon_wrst", "reset_name", "wrst_n")
        utils_dv.uvm_config_db_set(self, "env.mon_wrst", "reset_active_low", True)
        # clock_name is set directly in RadAsyncFifoEnv.build_phase()

        # Configure read reset monitor (in RadAsyncFifoEnv)
        utils_dv.uvm_config_db_set(self, "env.mon_rrst", "reset_name", "rrst_n")
        utils_dv.uvm_config_db_set(self, "env.mon_rrst", "reset_active_low", True)
        # clock_name is set directly in RadAsyncFifoEnv.build_phase()

        # Keep base reference for backward compatibility (points to write reset)
        self.reset_driver = self.wrst_driver

    def set_factory_overrides(self) -> None:
        override_type_type = pyuvm.uvm_factory().set_type_override_by_type
        override_inst_type = pyuvm.uvm_factory().set_inst_override_by_type

        override_type_type(BaseCoverage, RadAsyncFifoCoverage)
        override_type_type(BaseEnv, RadAsyncFifoEnv)
        override_type_type(BaseRefModel, RadAsyncFifoRefModel)
        override_type_type(BaseResetSink, RadAsyncFifoResetSink)
        override_type_type(BaseSb, RadAsyncFifoSb)

        override_type_type(BaseSbPredictor, RadAsyncFifoSbPredictor)

        # Write domain (agent0): monitors on wclk, write items
        override_inst_type(
            BaseDriver, RadAsyncFifoWriteDriver, "uvm_test_top.env.agent0.drv"
        )
        override_inst_type(BaseItem, RadAsyncFifoWriteItem, "uvm_test_top.env.agent0.*")
        override_inst_type(
            BaseSequence, RadAsyncFifoWriteSequence, "uvm_test_top.env.agent0.*"
        )
        override_inst_type(
            BaseMonitorIn, RadAsyncFifoWriteMonitorIn, "uvm_test_top.env.agent0.mon_in"
        )
        override_inst_type(
            BaseMonitorOut,
            RadAsyncFifoWriteMonitorOut,
            "uvm_test_top.env.agent0.mon_out",
        )

        # Read domain (agent1): monitors on rclk, read items
        override_inst_type(
            BaseDriver, RadAsyncFifoReadDriver, "uvm_test_top.env.agent1.drv"
        )
        override_inst_type(BaseItem, RadAsyncFifoReadItem, "uvm_test_top.env.agent1.*")
        override_inst_type(
            BaseSequence, RadAsyncFifoReadSequence, "uvm_test_top.env.agent1.*"
        )
        override_inst_type(
            BaseMonitorIn, RadAsyncFifoReadMonitorIn, "uvm_test_top.env.agent1.mon_in"
        )
        override_inst_type(
            BaseMonitorOut,
            RadAsyncFifoReadMonitorOut,
            "uvm_test_top.env.agent1.mon_out",
        )

    async def run_phase(self) -> None:
        """Run write and read sequences concurrently on separate agents."""
        self.logger.debug("run_phase begin")
        self.raise_objection()

        # Create write sequence for agent0 (write domain)
        write_seq = pyuvm.uvm_factory().create_object_by_type(
            RadAsyncFifoWriteSequence, name="write_seq"
        )
        # Create read sequence for agent1 (read domain)
        read_seq = pyuvm.uvm_factory().create_object_by_type(
            RadAsyncFifoReadSequence, name="read_seq"
        )

        # Run both sequences concurrently using cocotb.start_soon
        # Note: cocotb doesn't support asyncio.gather, use start_soon instead

        write_task = cocotb.start_soon(write_seq.start(self.env.agents[0].sqr))
        read_task = cocotb.start_soon(read_seq.start(self.env.agents[1].sqr))

        # Wait for both tasks to complete
        await write_task
        await read_task

        await self.drain()
        self.drop_objection()
        self.logger.debug("run_phase end")
