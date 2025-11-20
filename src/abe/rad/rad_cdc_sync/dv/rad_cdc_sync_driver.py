# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/rad_cdc_sync_driver.py

"""Testbench: agent, driver, monitors, scoreboard, and environment."""

from __future__ import annotations

from typing import Any

import pyuvm
from cocotb.triggers import Timer

from abe.rad.shared.dv import BaseDriver

from .rad_cdc_sync_item import RadCdcSyncItem


class RadCdcSyncDriver(
    BaseDriver[RadCdcSyncItem]
):  # pylint: disable=too-many-ancestors
    """Drives async_i; applies items on the falling edge with jitter."""

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.initial_dut_input_values = {"async_i": 0}

    async def drive_item(self, dut: Any, tr: RadCdcSyncItem) -> None:
        await self.clock_drive_edge()
        await Timer(tr.delay_ps, unit="ps")
        dut.async_i.value = tr.async_i
