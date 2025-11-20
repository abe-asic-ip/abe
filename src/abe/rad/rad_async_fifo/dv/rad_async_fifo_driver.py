# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_driver.py


"""Write-side driver for rad_async_fifo."""

from __future__ import annotations

from typing import Any

import pyuvm
from cocotb.triggers import ReadOnly

from abe.rad.shared.dv import BaseDriver, utils_dv

from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem


class RadAsyncFifoWriteDriver(
    BaseDriver[RadAsyncFifoWriteItem]
):  # pylint: disable=too-many-ancestors
    """Drives write-side inputs (winc, wdata) with protocol-aware backpressure.

    Samples wfull at the drive edge (negedge of wclk) before driving inputs.
    If winc=1 is requested but wfull=1, stalls (drives winc=0) and retries
    on the next clock edge, ensuring writes only occur when FIFO has space.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.initial_dut_input_values = {"winc": 0, "wdata": 0}

    async def drive_item(self, dut: Any, tr: RadAsyncFifoWriteItem) -> None:
        """Drive a write transaction, stalling while the FIFO is full.

        If tr.winc == 1 and wfull is 1 at the drive edge, we do *not*
        issue the write yet. Instead we drive an idle cycle (winc=0),
        and try again on the next clock edge. We do not return until
        we've actually issued the requested write once.
        """
        while True:
            # 1. Advance to the write clock drive edge (negedge of wclk).
            await self.clock_drive_edge()

            # 2. Sample current wfull. Because wfull is registered, this
            #    reflects the most recent posedge (e.g., 41.5ns).
            wfull_now = utils_dv.get_signal_value_int(dut.wfull.value)
            tr.wfull = wfull_now

            # 3. Decide what to drive this cycle.
            if tr.winc and wfull_now:
                # Backpressure: FIFO is full, stall this item.
                dut.winc.value = 0
                dut.wdata.value = 0
                self.logger.debug(
                    "Write driver stalling item: requested winc=1 but "
                    "wfull=1 at drive edge; wdata=%d",
                    tr.wdata,
                )
                # Loop to the next cycle and re-check wfull.
            else:
                # Either no write requested, or FIFO is not full.
                dut.winc.value = tr.winc
                dut.wdata.value = tr.wdata
                self.logger.debug(
                    "Write input driver drove: winc=%d, wdata=%d (wfull=%d)",
                    tr.winc,
                    tr.wdata,
                    wfull_now,
                )

            # 4. Let combinational logic settle (not strictly required for
            #    write-side here, but keeps phase behavior consistent).
            await ReadOnly()

            # 5. Exit conditions.
            if tr.winc == 0:
                # No write requested; we've done our one-cycle drive.
                break

            if tr.winc and not wfull_now:
                # We actually issued the requested write this cycle.
                break

            # Otherwise: tr.winc == 1 and wfull_now == 1. We stalled
            # (drove winc=0) and need to loop to try again.


class RadAsyncFifoReadDriver(
    BaseDriver[RadAsyncFifoReadItem]
):  # pylint: disable=too-many-ancestors
    """Drives read-side inputs (rinc) with protocol-aware backpressure.

    Samples rempty at the drive edge (negedge of rclk) before driving inputs.
    If rinc=1 is requested but rempty=1, stalls (drives rinc=0) and retries
    on the next clock edge, ensuring reads only occur when FIFO has data.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.initial_dut_input_values = {"rinc": 0}

    async def drive_item(self, dut: Any, tr: RadAsyncFifoReadItem) -> None:
        """
        Drive a rinc transaction. Don't depend on rempty.
        """
        await self.clock_drive_edge()

        rempty_now = utils_dv.get_signal_value_int(dut.rempty.value)

        dut.rinc.value = tr.rinc
        self.logger.debug(
            "Read input driver drove: rinc=%d (rempty=%d)",
            tr.rinc,
            rempty_now,
        )

        await ReadOnly()
        tr.rdata = utils_dv.get_signal_value_int(dut.rdata.value)
        tr.rempty = utils_dv.get_signal_value_int(dut.rempty.value)
