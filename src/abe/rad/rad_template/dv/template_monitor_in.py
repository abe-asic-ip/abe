# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_monitor_in.py

# pylint: disable=duplicate-code

"""Monitor for DUT inputs."""

from __future__ import annotations

from typing import Any

from abe.rad.shared.dv import BaseMonitorIn

from .template_item import TemplateItem


class TemplateMonitorIn(
    BaseMonitorIn[TemplateItem]
):  # pylint: disable=too-many-ancestors
    """Sample DUT inputs."""

    async def sample_dut(self, dut: Any) -> TemplateItem:
        raise NotImplementedError("implement sample_dut")
        # create the transaction
        # item = TemplateItem(f"item{self.item_count}")
        # capture transaction from wires
        # await self.sample_dut_edge()
        # item.async_i = self._get_val(dut.async_i.value)
        # account and return
        # self.item_count += 1
        # return item
