# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_sb_comparator.py

"""Reusable comparator using analysis FIFOs (expected & actual)."""

from __future__ import annotations

from typing import Generic, TypeVar

import pyuvm

from . import utils_dv
from .base_item import BaseItem

T = TypeVar("T", bound=BaseItem)


class BaseSbComparator(pyuvm.uvm_component, Generic[T]):
    """Scoreboard comparator using dual analysis FIFOs for expected and actual.

    This component compares expected transactions (from predictor) against
    actual transactions (from DUT output monitor) in strict order. It maintains
    pass/fail statistics and can halt simulation on errors.

    Architecture:
        Expected Transactions → exp_fifo ──┐
                                           ├→ Compare → Pass/Fail
        Actual Transactions → out_fifo ────┘

    FIFOs:
        exp_fifo: Analysis FIFO receiving expected transactions from predictor
        out_fifo: Analysis FIFO receiving actual transactions from monitor

    Statistics:
        vect_cnt: Total number of comparisons performed
        pass_cnt: Number of passing comparisons
        err_cnt: Number of failing comparisons

    Configuration (via config_db):
        sb_fail_on_error (bool): Raise error in final_phase if errors occurred
                                (default: True)
        sb_error_quit_count (int): Stop simulation after this many errors
                                  (default: 1, set to 0 to disable)
        sb_initial_flush_num (int): Number of transactions to flush before
                                   comparing (default: 0, for pipeline bubbles)

    Comparison:
        Uses BaseItem.compare_out() to compare only output fields, ignoring
        input fields that may differ.

    Reference:
        C.E. Cummings, "OVM/UVM Scoreboards - Fundamental Architectures,"
        SNUG 2013 (Silicon Valley) - Dual analysis FIFO pattern

    Example:
        >>> # Configure in test
        >>> uvm_config_db_set(self, "env*", "sb_error_quit_count", 10)
        >>> uvm_config_db_set(self, "env*", "sb_initial_flush_num", 3)
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)

        self.exp_fifo: pyuvm.uvm_tlm_analysis_fifo[T] = pyuvm.uvm_tlm_analysis_fifo(
            f"{name}.exp_fifo", self
        )
        self.out_fifo: pyuvm.uvm_tlm_analysis_fifo[T] = pyuvm.uvm_tlm_analysis_fifo(
            f"{name}.out_fifo", self
        )

        self.vect_cnt: int = 0
        self.pass_cnt: int = 0
        self.err_cnt: int = 0

        f = utils_dv.uvm_config_db_get_try(self, "sb_fail_on_error")
        self.fail_on_error: bool = bool(f) if isinstance(f, bool) else True

        q = utils_dv.uvm_config_db_get_try(self, "sb_error_quit_count")
        self.error_quit_count: int = int(q) if isinstance(q, int) and q >= 0 else 1

    # No connect_phase() needed

    async def run_phase(self) -> None:
        self.logger.debug("run_phase begin")

        # Initial flush to drain pipeline bubbles if requested

        initial_flush_num = 0
        n = utils_dv.uvm_config_db_get_try(self, "sb_initial_flush_num")
        if n is not None and not isinstance(n, int):
            self.logger.warning(
                "sb_initial_flush_num should be int, got %r; using 0", n
            )
        elif isinstance(n, int):
            initial_flush_num = max(0, n)

        for f in range(initial_flush_num):
            exp: T = await self.exp_fifo.get()
            act: T = await self.out_fifo.get()
            self.logger.debug(
                "Initial flush %d: exp=%s act=%s", f, exp.to_dict(), act.to_dict()
            )

        # Compare stream forever

        while True:
            exp = await self.exp_fifo.get()
            act = await self.out_fifo.get()
            self.vect_cnt += 1
            if act.compare_out(exp):
                self.pass_cnt += 1
                self.logger.debug(
                    "PASS exp=%s act=%s vect_cnt=%s",
                    exp.to_dict(),
                    act.to_dict(),
                    self.vect_cnt,
                )
            else:
                self.err_cnt += 1
                self.logger.error(
                    "MISMATCH exp=%s act=%s", exp.to_dict(), act.to_dict()
                )
            if (
                self.fail_on_error
                and self.error_quit_count
                and self.err_cnt >= self.error_quit_count
            ):
                raise AssertionError(
                    f"Scoreboard error_quit_count exceeded "
                    f"(errors={self.err_cnt}, threshold={self.error_quit_count})"
                )

    def report_phase(self) -> None:
        self.logger.debug("report_phase begin")
        if self.vect_cnt and self.err_cnt == 0:
            self.logger.info(
                "*** TEST PASSED - %d ran, %d passed ***", self.vect_cnt, self.pass_cnt
            )
        else:
            self.logger.error(
                "*** TEST FAILED - %d ran, %d passed, %d failed ***",
                self.vect_cnt,
                self.pass_cnt,
                self.err_cnt,
            )
        self.logger.debug("report_phase end")

    def final_phase(self) -> None:
        self.logger.debug("final_phase begin")
        if self.fail_on_error and self.err_cnt > 0:
            raise AssertionError(
                f"Scoreboard saw {self.err_cnt} error(s); sb_fail_on_error is enabled"
            )
        self.logger.debug("final_phase end")
