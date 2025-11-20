# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_coverage.py


"""Coverage."""

from __future__ import annotations

import pyuvm

from abe.rad.shared.dv import BaseCoverage

from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem


class RadAsyncFifoCoverage(BaseCoverage):
    """Track write/read operations and FIFO states.

    Receives both write items (winc, wdata, wfull) and read items (rinc, rdata, rempty)
    from separate monitors in different clock domains.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.total: int = 0
        self.writes: int = 0
        self.reads: int = 0
        self.full_hits: int = 0
        self.empty_hits: int = 0

    def sample(self, tt: RadAsyncFifoWriteItem | RadAsyncFifoReadItem) -> None:
        """Update counters for write/read activity and FIFO state.

        Handles both write items and read items from separate clock domains.
        """
        self.total += 1

        # Check if this is a write item
        if isinstance(tt, RadAsyncFifoWriteItem):
            if tt.winc:
                self.writes += 1
            # Track full (write domain)
            if tt.wfull == 1:
                self.full_hits += 1
        else:
            # This is a read item
            if tt.rinc:
                self.reads += 1
            # Track empty (read domain)
            if tt.rempty == 1:
                self.empty_hits += 1

    def report_phase(self) -> None:
        """Print coverage summary."""
        self.logger.debug("report_phase begin")
        super().report_phase()
        self.logger.info(
            "RadAsyncFifoCoverage summary:"
            " total=%d writes=%d reads=%d full=%d empty=%d",
            self.total,
            self.writes,
            self.reads,
            self.full_hits,
            self.empty_hits,
        )
        self.logger.debug("report_phase end")
