# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_item.py


"""Sequence items for rad_cdc_mcp verification."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from abe.rad.shared.dv import BaseItem

logger = logging.getLogger(__name__)


class RadCdcMcpWriteItem(BaseItem):
    """Transaction for CDC MCP a-domain (source/send).

    Inputs: asend, adatain
    Outputs: aready (not checked by scoreboard)
    """

    def __init__(self, name: str = "rad_cdc_mcp_write_item") -> None:
        super().__init__(name)
        # a-domain inputs
        self.asend: int | None = 0
        self.adatain: int | None = 0
        # a-domain output
        self.aready: int | None = None

    def _in_fields(self) -> tuple[str, ...]:
        return ("asend", "adatain")

    def _out_fields(self) -> tuple[str, ...]:
        return ("aready",)


class RadCdcMcpReadItem(BaseItem):
    """Transaction for CDC MCP b-domain (destination/receive).

    Inputs: bload
    Outputs: bdata (checked), bvalid (not checked due to CDC)
    """

    def __init__(self, name: str = "rad_cdc_mcp_read_item") -> None:
        super().__init__(name)
        # b-domain input
        self.bload: int | None = 0
        # b-domain outputs
        self.bdata: int | None = None
        self.bvalid: int | None = None

    def _in_fields(self) -> tuple[str, ...]:
        return ("bload",)

    def _out_fields(self) -> tuple[str, ...]:
        return ("bdata", "bvalid")

    def compare_out(
        self, other: BaseItem, *, fields: Iterable[str] | None = None
    ) -> bool:
        """Override comparison for CDC MCP read outputs.

        Due to CDC synchronization delays in CDC MCPs, we use a relaxed
        comparison strategy that focuses on data integrity rather than
        cycle-accurate timing:

        - self  is ACTUAL (DUT output, from RadCdcMcpReadMonitorOut)
        - other is EXPECTED (reference model output, from RadCdcMcpRefModel)

        Rules:
        - If expected bdata is None, skip comparison (CDC tolerance).
        - Only compare bdata when the ref model expects a valid read.
        - bvalid is not checked due to CDC synchronization delays.
        """

        # Type narrowing: we know other is RadCdcMcpReadItem after type check
        assert isinstance(other, RadCdcMcpReadItem)

        # Only compare bdata.
        if self.bdata != other.bdata:
            # Basic mismatch log
            logger.error(
                "READ MISMATCH: exp.bdata=%s act.bdata=%s",
                other.bdata,
                self.bdata,
            )
            # pylint: disable=duplicate-code
            # If the expected item carries a debug_state snapshot from the
            # reference model, dump it as well so we can see pointers/FIFO.
            debug_state = getattr(other, "debug_state", None)
            if debug_state is not None:
                logger.error("REF_MODEL_STATE: %s", debug_state)

            return False
            # pylint: enable=duplicate-code
        return True
