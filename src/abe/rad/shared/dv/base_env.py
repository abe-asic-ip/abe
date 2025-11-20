# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_env.py

"""Environment scaffold (UVM-style, factory-first)."""

from __future__ import annotations

import pyuvm

from . import utils_dv
from .base_agent import BaseAgent
from .base_coverage import BaseCoverage
from .base_reset_item import BaseResetItem
from .base_reset_monitor import BaseResetMonitor
from .base_reset_sink import BaseResetSink
from .base_sb import BaseSb


class BaseEnv(pyuvm.uvm_env):
    """Top-level UVM environment that builds and connects all verification components.

    The environment is responsible for:
    - Creating the specified number of agents via the UVM factory
    - Conditionally building coverage and scoreboard components
    - Creating reset monitor and reset sink for reset handling
    - Connecting all analysis ports between components

    The environment uses the UVM factory pattern throughout, allowing all
    component types to be overridden via factory configuration.

    Components:
        agents: List of agent instances (length determined by num_agents)
        cov: Coverage collector (optional, controlled by coverage_en config)
        sb: Scoreboard for checking (optional, controlled by check_en config)
        mon_rst: Reset monitor observing reset signal
        reset_sink: Component that forwards reset events to driver and predictor

    Configuration (via config_db):
        coverage_en (bool): Enable coverage collection (default: True)
        check_en (bool): Enable scoreboard checking (default: True)

    Example:
        >>> # In a test's build_phase
        >>> env = factory.create_component_by_type(
        ...     BaseEnv, parent_inst_path=path, name="env", parent=self
        ... )
    """

    num_agents: int = 1

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self.agents: list[BaseAgent] = []
        self.cov: BaseCoverage | None = None
        self.sb: BaseSb | None = None
        self.mon_rst: BaseResetMonitor
        self.reset_sink: BaseResetSink[BaseResetItem]
        self._coverage_en: bool = True
        self._check_en: bool = True

    def build_phase(self) -> None:
        self.logger.debug("build_phase begin")

        super().build_phase()

        create = pyuvm.uvm_factory().create_component_by_type
        parent_inst_path = self.get_full_name()

        for idx in range(self.num_agents):
            agent = create(
                BaseAgent,
                parent_inst_path=parent_inst_path,
                name=f"agent{idx}",
                parent=self,
            )
            self.agents.append(agent)

        cvrg = utils_dv.uvm_config_db_get_try(self, "coverage_en")
        if isinstance(cvrg, bool):
            self._coverage_en = cvrg
        if self._coverage_en:
            self.cov = create(
                BaseCoverage,
                parent_inst_path=parent_inst_path,
                name="coverage",
                parent=self,
            )

        chk = utils_dv.uvm_config_db_get_try(self, "check_en")
        if isinstance(chk, bool):
            self._check_en = chk
        if self._check_en:
            self.sb = create(
                BaseSb, parent_inst_path=parent_inst_path, name="sb", parent=self
            )

        self.mon_rst = create(
            BaseResetMonitor,
            parent_inst_path=parent_inst_path,
            name="mon_rst",
            parent=self,
        )
        self.reset_sink = create(
            BaseResetSink,
            parent_inst_path=parent_inst_path,
            name="reset_sink",
            parent=self,
        )

        self.logger.debug("build_phase begin")

    def connect_phase(self) -> None:
        self.logger.debug("connect_phase begin")
        super().connect_phase()
        for agent in self.agents:
            if self.cov is not None:
                agent.ap_in.connect(self.cov.analysis_export)
            if self.sb is not None:
                agent.ap_in.connect(self.sb.prd.analysis_export)
                agent.ap_out.connect(self.sb.cmp.out_fifo.analysis_export)
            self.reset_sink.drv = agent.drv
        self.mon_rst.ap.connect(self.reset_sink.analysis_export)
        if self.sb is not None:
            self.reset_sink.sb_prd = self.sb.prd
        self.logger.debug("connect_phase end")
