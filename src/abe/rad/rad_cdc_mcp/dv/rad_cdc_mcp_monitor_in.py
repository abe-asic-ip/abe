# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_monitor_in.py


"""Monitors for CDC MCP input signals in write and read domains."""

from __future__ import annotations

from typing import Any

from abe.rad.shared.dv import BaseMonitorIn

from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem


class RadCdcMcpWriteMonitorIn(
    BaseMonitorIn[RadCdcMcpWriteItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT a-domain inputs on aclk."""

    async def sample_dut(self, dut: Any) -> RadCdcMcpWriteItem:
        # create the transaction
        item = RadCdcMcpWriteItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.asend = self._get_val(dut.asend.value)
        item.adatain = self._get_val(dut.adatain.value)
        self.logger.debug(
            "Write input monitor sampled item %d: asend=%d, adatain=%d",
            self.item_count,
            item.asend,
            item.adatain,
        )
        # account and return
        self.item_count += 1
        return item


class RadCdcMcpReadMonitorIn(
    BaseMonitorIn[RadCdcMcpReadItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT b-domain inputs on bclk."""

    async def sample_dut(self, dut: Any) -> RadCdcMcpReadItem:
        # create the transaction
        item = RadCdcMcpReadItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.bload = self._get_val(dut.bload.value)
        self.logger.debug(
            "Read input monitor sampled item %d: bload=%d", self.item_count, item.bload
        )
        # account and return
        self.item_count += 1
        return item
