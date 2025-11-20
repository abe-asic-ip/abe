# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_monitor_out.py


"""Monitors for async FIFO output signals in write and read domains."""

from __future__ import annotations

from typing import Any

from abe.rad.shared.dv import BaseMonitorOut

from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem


class RadAsyncFifoWriteMonitorOut(
    BaseMonitorOut[RadAsyncFifoWriteItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT write-side outputs on wclk."""

    async def sample_dut(self, dut: Any) -> RadAsyncFifoWriteItem:
        # create the transaction
        item = RadAsyncFifoWriteItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.wfull = self._get_val(dut.wfull.value)
        self.logger.debug(
            "Write output monitor sampled item %d: wfull=%d",
            self.item_count,
            item.wfull,
        )
        # account and return
        self.item_count += 1
        return item


class RadAsyncFifoReadMonitorOut(
    BaseMonitorOut[RadAsyncFifoReadItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT read-side outputs on rclk.

    Only emits items to the analysis port for 'real reads' where rinc && !rempty.
    This ensures the scoreboard only compares actual read operations, not every cycle.
    """

    async def run_phase(self) -> None:
        """
        Override to conditionally write to analysis port based on real read
        condition.
        """
        self.logger.debug("run_phase begin")
        while True:
            tr = await self.sample_dut(self._dut)
            # Only write to analysis port if this was a real read
            if tr is not None:
                self.ap.write(tr)

    # pylint: disable=line-too-long
    async def sample_dut(self, dut: Any) -> RadAsyncFifoReadItem | None:  # type: ignore[override]
        # pylint: enable=line-too-long
        # create the transaction
        item = RadAsyncFifoReadItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.rinc = self._get_val(dut.rinc.value)
        item.rdata = self._get_val(dut.rdata.value)
        item.rempty = self._get_val(dut.rempty.value)

        # Only emit items for 'real reads': rinc && !rempty
        # This matches the condition in the reference model
        # for when rdata should be checked
        is_real_read = bool(item.rinc and not item.rempty)

        if is_real_read:
            self.logger.debug(
                "Read output monitor sampled REAL READ "
                "item %d: rinc=%d, rdata=%d, rempty=%d",
                self.item_count,
                item.rinc,
                item.rdata,
                item.rempty,
            )
            # account and return
            self.item_count += 1
            return item

        # Not a real read - don't emit to analysis port
        self.logger.debug(
            "Read output monitor skipping non-real-read: rinc=%d, rempty=%d",
            item.rinc,
            item.rempty,
        )
        return None
