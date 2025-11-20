# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_coverage.py


"""Coverage."""

from __future__ import annotations

import pyuvm

from abe.rad.shared.dv import BaseCoverage

from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem


class RadCdcMcpCoverage(BaseCoverage):
    """Track send/load operations and MCP states.

    Receives both send items (asend, adatain, aready) and load items
    (bload, bdata, bvalid) from separate monitors in different clock domains.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.total: int = 0
        self.sends: int = 0
        self.loads: int = 0
        self.not_ready_hits: int = 0
        self.not_valid_hits: int = 0

    def sample(self, tt: RadCdcMcpWriteItem | RadCdcMcpReadItem) -> None:
        """Update counters for send/load activity and MCP state.

        Handles both send items and load items from separate clock domains.
        """
        self.total += 1

        # Check if this is a send item
        if isinstance(tt, RadCdcMcpWriteItem):
            if tt.asend:
                self.sends += 1
            # Track not ready (a-domain)
            if tt.aready == 0:
                self.not_ready_hits += 1
        else:
            # This is a load item
            if tt.bload:
                self.loads += 1
            # Track not valid (b-domain)
            if tt.bvalid == 0:
                self.not_valid_hits += 1

    def report_phase(self) -> None:
        """Print coverage summary."""
        self.logger.debug("report_phase begin")
        super().report_phase()
        self.logger.info(
            "RadCdcMcpCoverage summary:"
            " total=%d sends=%d loads=%d not_ready=%d not_valid=%d",
            self.total,
            self.sends,
            self.loads,
            self.not_ready_hits,
            self.not_valid_hits,
        )
        self.logger.debug("report_phase end")
