# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_env.py

"""Environment for rad_cdc_mcp with dual reset domains."""

from __future__ import annotations

import pyuvm

from abe.rad.shared.dv import BaseEnv, BaseResetMonitor

from .rad_cdc_mcp_reset_sink import RadCdcMcpResetSink


class RadCdcMcpEnv(BaseEnv):
    """Environment for CDC MCP with dual clock domains and independent resets.

    Creates:
    - agent0: a-domain (aclk, arst_n) - drives asend/adatain, monitors aready
    - agent1: b-domain (bclk, brst_n) - drives bload, monitors bdata/bvalid
    - mon_arst/arst_sink: a-domain reset monitoring path
    - mon_brst/brst_sink: b-domain reset monitoring path
    """

    # Override to create 2 agents: agent0 for a-domain, agent1 for b-domain
    num_agents: int = 2

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        # Additional reset monitors/sinks for dual-clock design
        self.mon_arst: BaseResetMonitor
        self.mon_brst: BaseResetMonitor
        self.arst_sink: RadCdcMcpResetSink
        self.brst_sink: RadCdcMcpResetSink

    def build_phase(self) -> None:
        self.logger.debug("build_phase begin")
        super().build_phase()

        create = pyuvm.uvm_factory().create_component_by_type
        parent_inst_path = self.get_full_name()

        # Configure base class mon_rst to prevent bind errors (not used for monitoring)
        # Actual reset monitoring uses mon_arst and mon_brst with domain-specific sinks
        self.mon_rst.clock_name = "aclk"
        self.mon_rst.reset_name = "arst_n"

        # Create a-domain reset monitor and sink
        self.mon_arst = create(
            BaseResetMonitor,
            parent_inst_path=parent_inst_path,
            name="mon_arst",
            parent=self,
        )
        # Configure a-domain reset monitor to use aclk and arst_n
        self.mon_arst.clock_name = "aclk"
        self.mon_arst.reset_name = "arst_n"
        self.arst_sink = RadCdcMcpResetSink(
            name="arst_sink", parent=self, reset_method_name="arst_change"
        )

        # Create b-domain reset monitor and sink
        self.mon_brst = create(
            BaseResetMonitor,
            parent_inst_path=parent_inst_path,
            name="mon_brst",
            parent=self,
        )
        # Configure b-domain reset monitor to use bclk and brst_n
        self.mon_brst.clock_name = "bclk"
        self.mon_brst.reset_name = "brst_n"
        self.brst_sink = RadCdcMcpResetSink(
            name="brst_sink", parent=self, reset_method_name="brst_change"
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

        # Connect ONLY b-domain agent (agent1) outputs to comparator
        # a-domain agent outputs (aready) are not currently checked by scoreboard
        if self.sb is not None and len(self.agents) > 1:
            self.agents[1].ap_out.connect(self.sb.cmp.out_fifo.analysis_export)

        # Connect a-domain reset path to a-domain agent (agent0)
        self.mon_arst.ap.connect(self.arst_sink.analysis_export)
        if len(self.agents) > 0:
            self.arst_sink.drv = self.agents[0].drv  # a-domain agent
        if self.sb is not None:
            self.arst_sink.sb_prd = self.sb.prd

        # Connect b-domain reset path to b-domain agent (agent1)
        self.mon_brst.ap.connect(self.brst_sink.analysis_export)
        if len(self.agents) > 1:
            self.brst_sink.drv = self.agents[1].drv  # b-domain agent
        if self.sb is not None:
            self.brst_sink.sb_prd = self.sb.prd

        self.logger.debug("connect_phase end")
