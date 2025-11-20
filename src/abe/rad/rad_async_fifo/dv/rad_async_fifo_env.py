# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_env.py

"""Environment for rad_async_fifo with dual reset domains."""

from __future__ import annotations

import pyuvm

from abe.rad.shared.dv import BaseEnv, BaseResetMonitor

from .rad_async_fifo_reset_sink import RadAsyncFifoResetSink


class RadAsyncFifoEnv(BaseEnv):
    """Environment for async FIFO with dual clock domains and independent resets.

    Creates:
    - agent0: Write domain (wclk, wrst_n) - drives winc/wdata, monitors wfull
    - agent1: Read domain (rclk, rrst_n) - drives rinc, monitors rdata/rempty
    - mon_wrst/wrst_sink: Write reset monitoring path
    - mon_rrst/rrst_sink: Read reset monitoring path
    """

    # Override to create 2 agents: agent0 for write, agent1 for read
    num_agents: int = 2

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        # Additional reset monitors/sinks for dual-clock design
        self.mon_wrst: BaseResetMonitor
        self.mon_rrst: BaseResetMonitor
        self.wrst_sink: RadAsyncFifoResetSink
        self.rrst_sink: RadAsyncFifoResetSink

    def build_phase(self) -> None:
        self.logger.debug("build_phase begin")
        super().build_phase()

        create = pyuvm.uvm_factory().create_component_by_type
        parent_inst_path = self.get_full_name()

        # Configure base class mon_rst to prevent bind errors (not used for monitoring)
        # Actual reset monitoring uses mon_wrst and mon_rrst with domain-specific sinks
        self.mon_rst.clock_name = "wclk"
        self.mon_rst.reset_name = "wrst_n"

        # Create write reset monitor and sink
        self.mon_wrst = create(
            BaseResetMonitor,
            parent_inst_path=parent_inst_path,
            name="mon_wrst",
            parent=self,
        )
        # Configure write reset monitor to use wclk and wrst_n
        self.mon_wrst.clock_name = "wclk"
        self.mon_wrst.reset_name = "wrst_n"
        self.wrst_sink = RadAsyncFifoResetSink(
            name="wrst_sink", parent=self, reset_method_name="wrst_change"
        )

        # Create read reset monitor and sink
        self.mon_rrst = create(
            BaseResetMonitor,
            parent_inst_path=parent_inst_path,
            name="mon_rrst",
            parent=self,
        )
        # Configure read reset monitor to use rclk and rrst_n
        self.mon_rrst.clock_name = "rclk"
        self.mon_rrst.reset_name = "rrst_n"
        self.rrst_sink = RadAsyncFifoResetSink(
            name="rrst_sink", parent=self, reset_method_name="rrst_change"
        )

        self.logger.debug("build_phase end")

    def connect_phase(self) -> None:
        self.logger.debug("connect_phase begin")

        # Override base class connect_phase for dual-domain architecture
        # - Both agents' inputs connect to coverage and predictor
        # - Only read agent outputs connect to comparator (write outputs not checked)
        # - Independent reset paths for each domain

        # Connect agents to coverage and predictor (inputs)
        # pylint: disable=duplicate-code
        for agent in self.agents:
            if self.cov is not None:
                agent.ap_in.connect(self.cov.analysis_export)
            if self.sb is not None:
                agent.ap_in.connect(self.sb.prd.analysis_export)
        # pylint: enable=duplicate-code

        # Connect ONLY read agent (agent1) outputs to comparator
        # Write agent outputs (wfull) are not currently checked by scoreboard
        if self.sb is not None and len(self.agents) > 1:
            self.agents[1].ap_out.connect(self.sb.cmp.out_fifo.analysis_export)

        # Connect write reset path to write agent (agent0)
        self.mon_wrst.ap.connect(self.wrst_sink.analysis_export)
        if len(self.agents) > 0:
            self.wrst_sink.drv = self.agents[0].drv  # Write agent
        if self.sb is not None:
            self.wrst_sink.sb_prd = self.sb.prd

        # Connect read reset path to read agent (agent1)
        self.mon_rrst.ap.connect(self.rrst_sink.analysis_export)
        if len(self.agents) > 1:
            self.rrst_sink.drv = self.agents[1].drv  # Read agent
        if self.sb is not None:
            self.rrst_sink.sb_prd = self.sb.prd

        self.logger.debug("connect_phase end")
