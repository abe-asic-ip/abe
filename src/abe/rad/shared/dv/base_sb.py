# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_sb.py

"""Top level scoreboard."""

from __future__ import annotations

from typing import Generic, TypeVar

import pyuvm

from . import utils_dv
from .base_item import BaseItem
from .base_sb_comparator import BaseSbComparator
from .base_sb_predictor import BaseSbPredictor

T = TypeVar("T", bound=BaseItem)


class BaseSb(pyuvm.uvm_scoreboard, Generic[T]):
    """Top-level scoreboard coordinating prediction and comparison.

    The scoreboard implements the classic UVM scoreboard architecture with
    separate predictor and comparator components. It is completely generic
    and requires no DUT-specific customization.

    Architecture:
        Input Transactions → Predictor → Expected Transactions → Comparator
        Output Transactions ────────────────────────────────────→ Comparator

    Components:
        prd (BaseSbPredictor): Predictor that uses reference model to compute
                              expected outputs from input transactions
        cmp (BaseSbComparator): Comparator that checks expected vs actual
                               outputs using dual analysis FIFOs

    Connection:
        The scoreboard automatically connects the predictor's results_ap to
        the comparator's exp_fifo during connect_phase.

    Usage:
        The BaseEnv creates and connects a BaseSb when check_en=True. The
        environment connects:
        - Agent input monitor → predictor (for expected values)
        - Agent output monitor → comparator (for actual values)

    Reference:
        C.E. Cummings, "OVM/UVM Scoreboards - Fundamental Architectures,"
        SNUG 2013 (Silicon Valley)

    Example:
        >>> # Typically created by BaseEnv, not instantiated directly
        >>> sb = factory.create_component_by_type(
        ...     BaseSb, parent_inst_path=path, name="sb", parent=self
        ... )
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        create = pyuvm.uvm_factory().create_component_by_type
        parent_inst_path = self.get_full_name()
        self.prd: BaseSbPredictor[T] = create(
            BaseSbPredictor, parent_inst_path=parent_inst_path, name="prd", parent=self
        )
        self.cmp: BaseSbComparator[T] = create(
            BaseSbComparator,
            parent_inst_path=parent_inst_path,
            name="comparator",
            parent=self,
        )

    def connect_phase(self) -> None:
        self.logger.debug("connect_phase begin")
        self.prd.results_ap.connect(self.cmp.exp_fifo.analysis_export)
        self.logger.debug("connect_phase end")
