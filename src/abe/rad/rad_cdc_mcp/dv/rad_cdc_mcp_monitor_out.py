# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_monitor_out.py


"""Monitors for CDC MCP output signals in write and read domains."""

from __future__ import annotations

from typing import Any

import pyuvm

from abe.rad.shared.dv import BaseMonitorOut

from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem


class RadCdcMcpWriteMonitorOut(
    BaseMonitorOut[RadCdcMcpWriteItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT a-domain outputs on aclk."""

    async def sample_dut(self, dut: Any) -> RadCdcMcpWriteItem:
        # create the transaction
        item = RadCdcMcpWriteItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.aready = self._get_val(dut.aready.value)
        self.logger.debug(
            "Write output monitor sampled item %d: aready=%d",
            self.item_count,
            item.aready,
        )
        # account and return
        self.item_count += 1
        return item


class RadCdcMcpReadMonitorOut(
    BaseMonitorOut[RadCdcMcpReadItem]
):  # pylint: disable=too-many-ancestors
    # pylint: disable=duplicate-code
    """Sample DUT b-domain outputs on bclk.

    Only emits items to the analysis port for 'real loads' where bload && bvalid.
    This ensures the scoreboard only compares actual load operations, not every cycle.

    Note: bdata is registered and updates one cycle after bload && bvalid.
    We track the previous cycle's load condition to know when to capture valid bdata.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self._prev_load_pending = False

    async def run_phase(self) -> None:
        """
        Override to conditionally write to analysis port based on real load
        condition.
        """
        self.logger.debug("run_phase begin")
        while True:
            tr = await self.sample_dut(self._dut)
            # Only write to analysis port if this was a real load
            if tr is not None:
                self.ap.write(tr)

    # pylint: enable=duplicate-code
    # pylint: disable=line-too-long
    async def sample_dut(self, dut: Any) -> RadCdcMcpReadItem | None:  # type: ignore[override]
        # pylint: enable=line-too-long
        # create the transaction
        item = RadCdcMcpReadItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.bload = self._get_val(dut.bload.value)
        item.bvalid = self._get_val(dut.bvalid.value)
        item.bdata = self._get_val(dut.bdata.value)

        # Check if there was a load in the PREVIOUS cycle
        # If so, the bdata we just sampled is the newly loaded value
        if self._prev_load_pending:
            self._prev_load_pending = False
            self.logger.debug(
                "Read output monitor sampled REAL LOAD "
                "item %d: bdata=%d (from previous cycle's load)",
                self.item_count,
                item.bdata,
            )
            # account and return
            self.item_count += 1
            return item

        # Check if there's a load THIS cycle
        # If so, we'll capture bdata on the NEXT cycle
        is_real_load = bool(item.bload and item.bvalid)
        if is_real_load:
            self._prev_load_pending = True
            self.logger.debug(
                "Read output monitor detected load: bload=%d, bvalid=%d "
                "(will capture bdata next cycle)",
                item.bload,
                item.bvalid,
            )

        # Not emitting this cycle
        return None
