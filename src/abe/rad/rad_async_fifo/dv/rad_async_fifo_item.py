# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_item.py


"""Sequence items for rad_async_fifo verification."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from abe.rad.shared.dv import BaseItem

logger = logging.getLogger(__name__)


class RadAsyncFifoWriteItem(BaseItem):
    """Transaction for async FIFO write domain (wclk).

    Inputs: winc, wdata
    Outputs: wfull (not checked by scoreboard)
    """

    def __init__(self, name: str = "rad_async_fifo_write_item") -> None:
        super().__init__(name)
        # Write side inputs
        self.winc: int | None = 0
        self.wdata: int | None = 0
        # Write side output
        self.wfull: int | None = None

    def _in_fields(self) -> tuple[str, ...]:
        return ("winc", "wdata")

    def _out_fields(self) -> tuple[str, ...]:
        return ("wfull",)


class RadAsyncFifoReadItem(BaseItem):
    """Transaction for async FIFO read domain (rclk).

    Inputs: rinc
    Outputs: rdata (checked), rempty (not checked due to CDC)
    """

    def __init__(self, name: str = "rad_async_fifo_read_item") -> None:
        super().__init__(name)
        # Read side input
        self.rinc: int | None = 0
        # Read side outputs
        self.rdata: int | None = None
        self.rempty: int | None = None

    def _in_fields(self) -> tuple[str, ...]:
        return ("rinc",)

    def _out_fields(self) -> tuple[str, ...]:
        return ("rdata", "rempty")

    def compare_out(
        self, other: BaseItem, *, fields: Iterable[str] | None = None
    ) -> bool:
        """Override comparison for async FIFO read outputs.

        Due to CDC synchronization delays in async FIFOs, we use a relaxed
        comparison strategy that focuses on data integrity rather than
        cycle-accurate timing:

        - self  is ACTUAL (DUT output, from RadAsyncFifoReadMonitorOut)
        - other is EXPECTED (reference model output, from RadAsyncFifoRefModel)

        Rules:
        - If expected rdata is None, skip comparison (CDC tolerance).
        - Only compare rdata when the ref model expects a valid read.
        - rempty is not checked due to CDC synchronization delays.
        """

        # Type narrowing: we know other is RadAsyncFifoReadItem after type check
        assert isinstance(other, RadAsyncFifoReadItem)

        # Only compare rdata.
        if self.rdata != other.rdata:
            # Basic mismatch log
            logger.error(
                "READ MISMATCH: exp.rdata=%s act.rdata=%s",
                other.rdata,
                self.rdata,
            )

            # If the expected item carries a debug_state snapshot from the
            # reference model, dump it as well so we can see pointers/FIFO.
            debug_state = getattr(other, "debug_state", None)
            if debug_state is not None:
                logger.error("REF_MODEL_STATE: %s", debug_state)

            return False

        return True
