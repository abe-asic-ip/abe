# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_agent.py

"""Base agent wiring sequencer, driver, and monitor (factory-friendly)."""

from __future__ import annotations

import pyuvm

from . import utils_dv
from .base_driver import BaseDriver
from .base_monitor_in import BaseMonitorIn
from .base_monitor_out import BaseMonitorOut
from .base_sequencer import BaseSequencer


class BaseAgent(pyuvm.uvm_agent):
    """UVM agent that wires together sequencer, driver, and monitors.

    This agent follows the standard UVM pattern of containing a driver, sequencer,
    and monitors. It uses separate monitors for DUT inputs and outputs to maintain
    clear separation of concerns and enable independent observation of stimulus
    and responses.

    The agent can be configured as either active (with driver/sequencer) or passive
    (monitors only) using the standard UVM is_active configuration.

    Components:
        drv: Driver for applying stimulus to DUT inputs (active mode only)
        sqr: Sequencer for generating transaction sequences (active mode only)
        mon_in: Monitor observing DUT input signals
        mon_out: Monitor observing DUT output signals

    Analysis Ports:
        ap_in: Analysis port connected to input monitor
        ap_out: Analysis port connected to output monitor

    Reference:
        https://github.com/paradigm-works/uvmtb_template/blob/main/tb_agent.svh

    Example:
        >>> # In a testbench environment
        >>> agent = factory.create_component_by_type(
        ...     BaseAgent, parent_inst_path=path, name="agent", parent=self
        ... )
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self.ap_in: pyuvm.uvm_analysis_port
        self.ap_out: pyuvm.uvm_analysis_port
        self.drv: BaseDriver
        self.mon_in: BaseMonitorIn
        self.mon_out: BaseMonitorOut
        self.sqr: BaseSequencer

    def build_phase(self) -> None:
        self.logger.debug("build_phase begin")
        super().build_phase()
        create = pyuvm.uvm_factory().create_component_by_type
        parent_inst_path = self.get_full_name()
        if self.is_active == pyuvm.uvm_active_passive_enum.UVM_ACTIVE:
            self.drv = create(
                BaseDriver, parent_inst_path=parent_inst_path, name="drv", parent=self
            )
            self.sqr = create(
                BaseSequencer,
                parent_inst_path=parent_inst_path,
                name="sqr",
                parent=self,
            )
        self.mon_in = create(
            BaseMonitorIn, parent_inst_path=parent_inst_path, name="mon_in", parent=self
        )
        self.mon_out = create(
            BaseMonitorOut,
            parent_inst_path=parent_inst_path,
            name="mon_out",
            parent=self,
        )
        self.ap_in = pyuvm.uvm_analysis_port("ap_in", self)
        self.ap_out = pyuvm.uvm_analysis_port("ap_out", self)
        self.logger.debug("build_phase end")

    def connect_phase(self) -> None:
        self.logger.debug("connect_phase begin")
        super().connect_phase()
        if self.is_active == pyuvm.uvm_active_passive_enum.UVM_ACTIVE:
            self.drv.seq_item_port.connect(self.sqr.seq_item_export)
        self.mon_in.ap.connect(self.ap_in)
        self.mon_out.ap.connect(self.ap_out)
        self.logger.debug("connect_phase end")
