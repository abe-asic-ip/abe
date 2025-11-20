# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_monitor_out.py

# pylint: disable=duplicate-code

"""Monitor for DUT outputs."""

from __future__ import annotations

from typing import Any

from abe.rad.shared.dv import BaseMonitorOut

from .template_item import TemplateItem


class TemplateMonitorOut(
    BaseMonitorOut[TemplateItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT outputs."""

    async def sample_dut(self, dut: Any) -> TemplateItem:
        raise NotImplementedError("implement sample_dut")
        # create the transaction
        # item = TemplateItem(f"item{self.item_count}")
        # capture transaction from wires
        # await self.sample_dut_edge()
        # item.sync_o = self._get_val(dut.sync_o.value)
        # account and return
        # self.item_count += 1
        # return item
