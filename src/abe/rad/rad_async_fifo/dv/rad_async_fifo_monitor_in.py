# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_monitor_in.py


"""Monitors for async FIFO input signals in write and read domains."""

from __future__ import annotations

from typing import Any

from abe.rad.shared.dv import BaseMonitorIn

from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem


class RadAsyncFifoWriteMonitorIn(
    BaseMonitorIn[RadAsyncFifoWriteItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT write-side inputs on wclk."""

    async def sample_dut(self, dut: Any) -> RadAsyncFifoWriteItem:
        # create the transaction
        item = RadAsyncFifoWriteItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.winc = self._get_val(dut.winc.value)
        item.wdata = self._get_val(dut.wdata.value)
        self.logger.debug(
            "Write input monitor sampled item %d: winc=%d, wdata=%d",
            self.item_count,
            item.winc,
            item.wdata,
        )
        # account and return
        self.item_count += 1
        return item


class RadAsyncFifoReadMonitorIn(
    BaseMonitorIn[RadAsyncFifoReadItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT read-side inputs on rclk."""

    async def sample_dut(self, dut: Any) -> RadAsyncFifoReadItem:
        # create the transaction
        item = RadAsyncFifoReadItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.rinc = self._get_val(dut.rinc.value)
        self.logger.debug(
            "Read input monitor sampled item %d: rinc=%d", self.item_count, item.rinc
        )
        # account and return
        self.item_count += 1
        return item
