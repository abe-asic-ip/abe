# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_driver.py


"""Write-side driver for rad_cdc_mcp."""

from __future__ import annotations

from typing import Any

import pyuvm
from cocotb.triggers import ReadOnly

from abe.rad.shared.dv import BaseDriver, utils_dv

from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem


class RadCdcMcpWriteDriver(
    BaseDriver[RadCdcMcpWriteItem]
):  # pylint: disable=too-many-ancestors
    """Drives a-domain inputs (asend, adatain) with protocol-aware backpressure.

    Samples aready at the drive edge (negedge of aclk) before driving inputs.
    If asend=1 is requested but aready=0, stalls (drives asend=0) and retries
    on the next clock edge, ensuring sends only occur when MCP is ready.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.initial_dut_input_values = {"asend": 0, "adatain": 0}

    async def drive_item(self, dut: Any, tr: RadCdcMcpWriteItem) -> None:
        """Drive a send transaction, stalling while MCP is not ready.

        If tr.asend == 1 and aready is 0 at the drive edge, we do *not*
        issue the send yet. Instead we drive an idle cycle (asend=0),
        and try again on the next clock edge. We do not return until
        we've actually issued the requested send once.
        """
        while True:
            # 1. Advance to the a-domain clock drive edge (negedge of aclk).
            await self.clock_drive_edge()

            # 2. Sample current aready. Because aready is registered, this
            #    reflects the most recent posedge (e.g., 41.5ns).
            aready_now = utils_dv.get_signal_value_int(dut.aready.value)
            tr.aready = aready_now

            # 3. Decide what to drive this cycle.
            if tr.asend and not aready_now:
                # Backpressure: MCP is not ready, stall this item.
                dut.asend.value = 0
                dut.adatain.value = 0
                self.logger.debug(
                    "Write driver stalling item: requested asend=1 but "
                    "aready=0 at drive edge; adatain=%d",
                    tr.adatain,
                )
                # Loop to the next cycle and re-check aready.
            else:
                # Either no send requested, or MCP is ready.
                dut.asend.value = tr.asend
                dut.adatain.value = tr.adatain
                self.logger.debug(
                    "Write input driver drove: asend=%d, adatain=%d (aready=%d)",
                    tr.asend,
                    tr.adatain,
                    aready_now,
                )

            # 4. Let combinational logic settle (not strictly required for
            #    a-domain here, but keeps phase behavior consistent).
            await ReadOnly()

            # 5. Exit conditions.
            if tr.asend == 0:
                # No send requested; we've done our one-cycle drive.
                break

            if tr.asend and aready_now:
                # We actually issued the requested send this cycle.
                break

            # Otherwise: tr.asend == 1 and aready_now == 0. We stalled
            # (drove asend=0) and need to loop to try again.


class RadCdcMcpReadDriver(
    BaseDriver[RadCdcMcpReadItem]
):  # pylint: disable=too-many-ancestors
    """Drives b-domain inputs (bload) with protocol-aware backpressure.

    Samples bvalid at the drive edge (negedge of bclk) before driving inputs.
    If bload=1 is requested but bvalid=0, stalls (drives bload=0) and retries
    on the next clock edge, ensuring loads only occur when MCP has valid data.
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.initial_dut_input_values = {"bload": 0}

    async def drive_item(self, dut: Any, tr: RadCdcMcpReadItem) -> None:
        """Drive a load transaction on the b-domain.

        Advances to the drive edge (negedge of bclk), drives bload,
        and samples bdata/bvalid outputs. Unlike the write driver,
        this does not implement backpressure logic since the b-domain
        can always assert bload regardless of bvalid state.
        """
        await self.clock_drive_edge()
        bvalid_now = utils_dv.get_signal_value_int(dut.bvalid.value)

        dut.bload.value = tr.bload
        self.logger.debug(
            "Read input driver drove: bload=%d (bvalid=%d)",
            tr.bload,
            bvalid_now,
        )

        await ReadOnly()
        tr.bdata = utils_dv.get_signal_value_int(dut.bdata.value)
        tr.bvalid = utils_dv.get_signal_value_int(dut.bvalid.value)
