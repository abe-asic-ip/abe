# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/rad_cdc_sync_monitor_in.py

"""Monitor for DUT inputs."""

from __future__ import annotations

from typing import Any

from abe.rad.shared.dv import BaseMonitorIn

from .rad_cdc_sync_item import RadCdcSyncItem


class RadCdcSyncMonitorIn(
    BaseMonitorIn[RadCdcSyncItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT inputs."""

    async def sample_dut(self, dut: Any) -> RadCdcSyncItem:
        # create the transaction
        item = RadCdcSyncItem(f"item{self.item_count}")
        # capture transaction from wires
        await self.sample_dut_edge()
        item.async_i = self._get_val(dut.async_i.value)
        # account and return
        self.item_count += 1
        return item
