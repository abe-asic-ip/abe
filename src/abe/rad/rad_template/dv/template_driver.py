# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_driver.py

# pylint: disable=duplicate-code
# pylint: disable=fixme

"""Testbench: agent, driver, monitors, scoreboard, and environment."""

from __future__ import annotations

from typing import Any

import pyuvm

from abe.rad.shared.dv import BaseDriver

from .template_item import TemplateItem

# from cocotb.triggers import Timer # FIXME: remove comment; place under "import pyuvm"


class TemplateDriver(BaseDriver[TemplateItem]):  # pylint: disable=too-many-ancestors
    """FIXME"""  # FIXME: document

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        raise NotImplementedError("implement __init__")
        # self.initial_dut_input_values = {"async_i": 0}

    async def drive_item(self, dut: Any, tr: TemplateItem) -> None:
        await self.clock_drive_edge()
        raise NotImplementedError("implement drive_item")
        # await Timer(tr.delay_ps, unit="ps")
        # dut.async_i.value = tr.async_i
