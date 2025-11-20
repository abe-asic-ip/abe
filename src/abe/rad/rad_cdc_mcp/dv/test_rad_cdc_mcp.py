# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/test_rad_cdc_mcp.py


"""Tests for rad_cdc_mcp verification."""

from __future__ import annotations

import cocotb
import pyuvm

from abe.rad.rad_cdc_mcp.dv.rad_cdc_mcp_sb import RadCdcMcpSbPredictor
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

from .rad_cdc_mcp_coverage import RadCdcMcpCoverage
from .rad_cdc_mcp_driver import (
    RadCdcMcpReadDriver,
    RadCdcMcpWriteDriver,
)
from .rad_cdc_mcp_env import RadCdcMcpEnv
from .rad_cdc_mcp_item import (
    RadCdcMcpReadItem,
    RadCdcMcpWriteItem,
)
from .rad_cdc_mcp_monitor_in import (
    RadCdcMcpReadMonitorIn,
    RadCdcMcpWriteMonitorIn,
)
from .rad_cdc_mcp_monitor_out import (
    RadCdcMcpReadMonitorOut,
    RadCdcMcpWriteMonitorOut,
)
from .rad_cdc_mcp_ref_model import RadCdcMcpRefModel
from .rad_cdc_mcp_reset_sink import RadCdcMcpResetSink
from .rad_cdc_mcp_sb import RadCdcMcpSb
from .rad_cdc_mcp_sequence import (
    RadCdcMcpReadSequence,
    RadCdcMcpWriteSequence,
)


@pyuvm.test()
class RadCdcMcpBaseTest(BaseTest):
    """Basic CDC MCP test with independent clock domains and resets.

    Creates dual clock drivers (aclk, bclk) and dual reset drivers (arst_n, brst_n).
    Runs concurrent send and load sequences in their respective domains.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        # Declare additional clock/reset drivers for dual-clock design
        self.aclk_driver: BaseClockDriver
        self.bclk_driver: BaseClockDriver
        self.arst_driver: BaseResetDriver
        self.brst_driver: BaseResetDriver

    def build_config(self) -> None:
        """Configure scoreboard to handle CDC MCP initial state."""
        super().build_config()
        # Skip first several comparisons after reset to allow CDC synchronization
        # The DUT may have undefined state during CDC synchronization after reset
        utils_dv.uvm_config_db_set(
            self, "env.sb.comparator", "sb_initial_flush_num", 10
        )

    def build_clocks(self) -> None:
        """Build a-domain and b-domain clock drivers for dual-clock MCP."""
        # a-domain clock configuration
        aclk_enable = utils_cli.get_bool_setting("ACLK_ENABLE", True)
        aclk_period_ps = utils_cli.get_int_setting("ACLK_PERIOD_PS", 1_000)
        aclk_start_high = utils_cli.get_bool_setting("ACLK_START_HIGH", False)
        aclk_init_delay_ps = utils_cli.get_int_setting("ACLK_INIT_DELAY_PS", 0)

        # b-domain clock configuration
        bclk_enable = utils_cli.get_bool_setting("BCLK_ENABLE", True)
        bclk_period_ps = utils_cli.get_int_setting("BCLK_PERIOD_PS", 1_200)
        bclk_start_high = utils_cli.get_bool_setting("BCLK_START_HIGH", False)
        bclk_init_delay_ps = utils_cli.get_int_setting("BCLK_INIT_DELAY_PS", 0)

        # Create a-domain clock driver
        self.aclk_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseClockDriver,
            parent_inst_path=self.get_full_name(),
            name="aclk_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "aclk_driver", "clock_enable", aclk_enable)
        utils_dv.uvm_config_db_set(self, "aclk_driver", "clock_name", "aclk")
        utils_dv.uvm_config_db_set(
            self, "aclk_driver", "clock_period_ps", aclk_period_ps
        )
        utils_dv.uvm_config_db_set(
            self, "aclk_driver", "clock_start_high", aclk_start_high
        )
        utils_dv.uvm_config_db_set(
            self, "aclk_driver", "clock_init_delay_ps", aclk_init_delay_ps
        )

        # Create b-domain clock driver
        self.bclk_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseClockDriver,
            parent_inst_path=self.get_full_name(),
            name="bclk_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "bclk_driver", "clock_enable", bclk_enable)
        utils_dv.uvm_config_db_set(self, "bclk_driver", "clock_name", "bclk")
        utils_dv.uvm_config_db_set(
            self, "bclk_driver", "clock_period_ps", bclk_period_ps
        )
        utils_dv.uvm_config_db_set(
            self, "bclk_driver", "clock_start_high", bclk_start_high
        )
        utils_dv.uvm_config_db_set(
            self, "bclk_driver", "clock_init_delay_ps", bclk_init_delay_ps
        )

        # Set agent0 (a-domain agent) configurations to use a-domain clock
        utils_dv.uvm_config_db_set(self, "env.agent0.drv", "clock_name", "aclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent0.drv", "clock_period_ps", aclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_in", "clock_name", "aclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent0.mon_in", "clock_period_ps", aclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_out", "clock_name", "aclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent0.mon_out", "clock_period_ps", aclk_period_ps
        )

        # Set agent1 (b-domain agent) configurations to use b-domain clock
        utils_dv.uvm_config_db_set(self, "env.agent1.drv", "clock_name", "bclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent1.drv", "clock_period_ps", bclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_in", "clock_name", "bclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent1.mon_in", "clock_period_ps", bclk_period_ps
        )
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_out", "clock_name", "bclk")
        utils_dv.uvm_config_db_set(
            self, "env.agent1.mon_out", "clock_period_ps", bclk_period_ps
        )

        # Keep base reference for backward compatibility (points to a-domain clock)
        self.clock_driver = self.aclk_driver

    def build_resets(self) -> None:
        """Build a-domain and b-domain reset drivers for dual-clock MCP."""
        # a-domain reset configuration
        arst_enable = utils_cli.get_bool_setting("ARST_ENABLE", True)
        arst_active_low = utils_cli.get_bool_setting("ARST_ACTIVE_LOW", True)
        arst_cycles = utils_cli.get_int_setting("ARST_CYCLES", 10)
        arst_settle_cycles = utils_cli.get_int_setting("ARST_SETTLE_CYCLES", 10)

        # b-domain reset configuration
        brst_enable = utils_cli.get_bool_setting("BRST_ENABLE", True)
        brst_active_low = utils_cli.get_bool_setting("BRST_ACTIVE_LOW", True)
        brst_cycles = utils_cli.get_int_setting("BRST_CYCLES", 10)
        brst_settle_cycles = utils_cli.get_int_setting("BRST_SETTLE_CYCLES", 10)

        # Create a-domain reset driver
        self.arst_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseResetDriver,
            parent_inst_path=self.get_full_name(),
            name="arst_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "arst_driver", "reset_enable", arst_enable)
        utils_dv.uvm_config_db_set(self, "arst_driver", "reset_name", "arst_n")
        utils_dv.uvm_config_db_set(
            self, "arst_driver", "reset_active_low", arst_active_low
        )
        utils_dv.uvm_config_db_set(self, "arst_driver", "reset_cycles", arst_cycles)
        utils_dv.uvm_config_db_set(
            self, "arst_driver", "reset_settle_cycles", arst_settle_cycles
        )
        utils_dv.uvm_config_db_set(self, "arst_driver", "clock_name", "aclk")

        # Create b-domain reset driver
        self.brst_driver = pyuvm.uvm_factory().create_component_by_type(
            BaseResetDriver,
            parent_inst_path=self.get_full_name(),
            name="brst_driver",
            parent=self,
        )
        utils_dv.uvm_config_db_set(self, "brst_driver", "reset_enable", brst_enable)
        utils_dv.uvm_config_db_set(self, "brst_driver", "reset_name", "brst_n")
        utils_dv.uvm_config_db_set(
            self, "brst_driver", "reset_active_low", brst_active_low
        )
        utils_dv.uvm_config_db_set(self, "brst_driver", "reset_cycles", brst_cycles)
        utils_dv.uvm_config_db_set(
            self, "brst_driver", "reset_settle_cycles", brst_settle_cycles
        )
        utils_dv.uvm_config_db_set(self, "brst_driver", "clock_name", "bclk")

        # Set agent0 (a-domain agent) to use a-domain reset
        utils_dv.uvm_config_db_set(self, "env.agent0.drv", "reset_name", "arst_n")
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_in", "reset_name", "arst_n")
        utils_dv.uvm_config_db_set(self, "env.agent0.mon_out", "reset_name", "arst_n")

        # Set agent1 (b-domain agent) to use b-domain reset
        utils_dv.uvm_config_db_set(self, "env.agent1.drv", "reset_name", "brst_n")
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_in", "reset_name", "brst_n")
        utils_dv.uvm_config_db_set(self, "env.agent1.mon_out", "reset_name", "brst_n")

        # Configure a-domain reset monitor (in RadCdcMcpEnv)
        utils_dv.uvm_config_db_set(self, "env.mon_arst", "reset_name", "arst_n")
        utils_dv.uvm_config_db_set(self, "env.mon_arst", "reset_active_low", True)
        # clock_name is set directly in RadCdcMcpEnv.build_phase()

        # Configure b-domain reset monitor (in RadCdcMcpEnv)
        utils_dv.uvm_config_db_set(self, "env.mon_brst", "reset_name", "brst_n")
        utils_dv.uvm_config_db_set(self, "env.mon_brst", "reset_active_low", True)
        # clock_name is set directly in RadCdcMcpEnv.build_phase()

        # Keep base reference for backward compatibility (points to a-domain reset)
        self.reset_driver = self.arst_driver

    def set_factory_overrides(self) -> None:
        override_type_type = pyuvm.uvm_factory().set_type_override_by_type
        override_inst_type = pyuvm.uvm_factory().set_inst_override_by_type

        override_type_type(BaseCoverage, RadCdcMcpCoverage)
        override_type_type(BaseEnv, RadCdcMcpEnv)
        override_type_type(BaseRefModel, RadCdcMcpRefModel)
        override_type_type(BaseResetSink, RadCdcMcpResetSink)
        override_type_type(BaseSb, RadCdcMcpSb)

        override_type_type(BaseSbPredictor, RadCdcMcpSbPredictor)

        # a-domain (agent0): monitors on aclk, send items
        override_inst_type(
            BaseDriver, RadCdcMcpWriteDriver, "uvm_test_top.env.agent0.drv"
        )
        override_inst_type(BaseItem, RadCdcMcpWriteItem, "uvm_test_top.env.agent0.*")
        override_inst_type(
            BaseSequence, RadCdcMcpWriteSequence, "uvm_test_top.env.agent0.*"
        )
        override_inst_type(
            BaseMonitorIn, RadCdcMcpWriteMonitorIn, "uvm_test_top.env.agent0.mon_in"
        )
        override_inst_type(
            BaseMonitorOut,
            RadCdcMcpWriteMonitorOut,
            "uvm_test_top.env.agent0.mon_out",
        )

        # b-domain (agent1): monitors on bclk, load items
        override_inst_type(
            BaseDriver, RadCdcMcpReadDriver, "uvm_test_top.env.agent1.drv"
        )
        override_inst_type(BaseItem, RadCdcMcpReadItem, "uvm_test_top.env.agent1.*")
        override_inst_type(
            BaseSequence, RadCdcMcpReadSequence, "uvm_test_top.env.agent1.*"
        )
        override_inst_type(
            BaseMonitorIn, RadCdcMcpReadMonitorIn, "uvm_test_top.env.agent1.mon_in"
        )
        override_inst_type(
            BaseMonitorOut,
            RadCdcMcpReadMonitorOut,
            "uvm_test_top.env.agent1.mon_out",
        )

    async def run_phase(self) -> None:
        """Run send and load sequences concurrently on separate agents."""
        self.logger.debug("run_phase begin")
        self.raise_objection()

        # Create send sequence for agent0 (a-domain)
        write_seq = pyuvm.uvm_factory().create_object_by_type(
            RadCdcMcpWriteSequence, name="write_seq"
        )
        # Create load sequence for agent1 (b-domain)
        read_seq = pyuvm.uvm_factory().create_object_by_type(
            RadCdcMcpReadSequence, name="read_seq"
        )
        # pylint: disable=duplicate-code
        # Run both sequences concurrently using cocotb.start_soon
        # Note: cocotb doesn't support asyncio.gather, use start_soon instead

        write_task = cocotb.start_soon(write_seq.start(self.env.agents[0].sqr))
        read_task = cocotb.start_soon(read_seq.start(self.env.agents[1].sqr))

        # Wait for both tasks to complete
        self.logger.debug("awaiting write_task")
        await write_task
        self.logger.debug("awaiting read_task")
        await read_task
        self.logger.debug("awaiting drain")
        await self.drain()
        self.logger.debug("awaiting drop_objection")
        self.drop_objection()
        self.logger.debug("run_phase end")
