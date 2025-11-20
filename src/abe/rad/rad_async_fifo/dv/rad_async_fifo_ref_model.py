# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_ref_model.py

"""rad_async_fifo reference model (simplified, queue-based).

This model intentionally ignores internal pointer/CDC details and
implements a logical FIFO:

* Writes:
  - When winc == 1 and the FIFO is not logically full, push wdata.
  - wfull/rempty from the DUT are not modeled or checked here.

* Reads:
  - When rinc == 1 and the FIFO is not logically empty, pop the next word
    and set exp.rdata to that value.
  - If no "real read" occurs, exp.rdata is set to None so the comparator
    can treat it as "don't care".

This keeps the reference model focused on **data integrity** and
order, while the **drivers** enforce protocol correctness with respect
to wfull/rempty.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from abe.rad.shared.dv import BaseRefModel, utils_cli

if TYPE_CHECKING:
    from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem
else:
    # Import at runtime for isinstance checks
    from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem


class RadAsyncFifoRefModel(  # pylint: disable=too-many-instance-attributes
    BaseRefModel
):
    """Generic async FIFO reference model based on a logical queue."""

    # ------------------------------------------------------------------
    # Construction / configuration
    # ------------------------------------------------------------------

    def __init__(self, name: str = "rad_async_fifo_ref_model") -> None:
        super().__init__(name)

        # Configuration defaults (can be overridden via CLI env vars)
        self.dsize: int = 8
        self.asize: int = 3  # FIFO depth = 2**asize by default

        self.dsize = int(utils_cli.get_int_setting("RAD_ASYNC_FIFO_DSIZE", self.dsize))
        self.asize = int(utils_cli.get_int_setting("RAD_ASYNC_FIFO_ASIZE", self.asize))

        # Clamp to reasonable minimums
        self.dsize = max(1, self.dsize)
        self.asize = max(1, self.asize)

        # Derived constants
        self.depth: int = 1 << self.asize
        self.data_mask: int = (1 << self.dsize) - 1

        # Internal FIFO state: logical data queue
        self._fifo: deque[int] = deque(maxlen=self.depth)

        # Track whether each domain is currently in reset
        self._wrst_active: bool = False
        self._rrst_active: bool = False

        # Simple counters for debug/statistics
        self._writes_accepted: int = 0
        self._writes_dropped: int = 0  # should be 0 under protocol-correct drivers
        self._reads_accepted: int = 0
        self._reads_blocked: int = 0

    # ------------------------------------------------------------------
    # Reset handling
    # ------------------------------------------------------------------

    def _clear_state(self) -> None:
        """Clear shared FIFO state and counters."""
        self._fifo.clear()
        self._writes_accepted = 0
        self._writes_dropped = 0
        self._reads_accepted = 0
        self._reads_blocked = 0

    def _clear_write_domain(self) -> None:
        """Reset write-domain state.

        For this simplified model, write-domain and read-domain share the
        same logical FIFO, so we conservatively clear shared state when
        either side asserts reset.
        """
        self._clear_state()

    def _clear_read_domain(self) -> None:
        """Reset read-domain state (see _clear_write_domain)."""
        self._clear_state()

    def wrst_change(self, value: int, active: bool) -> None:
        """Handle write-domain reset change."""
        self.logger.debug("wrst_change: value=%d active=%s", value, active)
        self._wrst_active = active
        if active:
            self._clear_write_domain()

    def rrst_change(self, value: int, active: bool) -> None:
        """Handle read-domain reset change."""
        self.logger.debug("rrst_change: value=%d active=%s", value, active)
        self._rrst_active = active
        if active:
            self._clear_read_domain()

    def reset_change(self, value: int, active: bool) -> None:
        """Legacy single reset - apply to both domains for compatibility."""
        self.logger.debug("reset_change begin value=%d active=%s", value, active)
        super().reset_change(value, active)
        self._wrst_active = active
        self._rrst_active = active
        self._clear_state()
        self.logger.debug("reset_change end")

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def snapshot_state(self) -> dict:
        """Return a snapshot of logical FIFO state for debug.

        Used by the scoreboard on mismatches to give context.
        """
        return {
            "fifo_len": len(self._fifo),
            "depth": self.depth,
            "writes_accepted": self._writes_accepted,
            "writes_dropped": self._writes_dropped,
            "reads_accepted": self._reads_accepted,
            "reads_blocked": self._reads_blocked,
        }

    # ------------------------------------------------------------------
    # Main calc_exp entry point
    # ------------------------------------------------------------------

    def calc_exp(
        self, tr: RadAsyncFifoWriteItem | RadAsyncFifoReadItem
    ) -> RadAsyncFifoWriteItem | RadAsyncFifoReadItem:
        """Compute expected behavior for a write or read transaction.

        Writes:
          - Update the internal logical FIFO only.
        Reads:
          - Update the logical FIFO and drive exp.rdata for comparison.
        """
        if isinstance(tr, RadAsyncFifoWriteItem):
            return self._calc_write_exp(tr)

        return self._calc_read_exp(tr)

    # ------------------------------------------------------------------
    # Write-domain behavior (wclk domain)
    # ------------------------------------------------------------------

    def _calc_write_exp(self, tr: RadAsyncFifoWriteItem) -> RadAsyncFifoWriteItem:
        """Process write-domain transaction (winc, wdata)."""

        if self._wrst_active:
            # During write reset we don't update state, and we don't care
            # about wfull/rempty predictions in this simplified model.
            tr.wfull = None
            return tr

        # Inputs, with None treated as 0
        winc = tr.winc if tr.winc is not None else 0
        wdata = tr.wdata if tr.wdata is not None else 0
        wdata &= self.data_mask

        if winc:
            if len(self._fifo) < self.depth:
                self._fifo.append(wdata)
                self._writes_accepted += 1
                self.logger.debug(
                    "REF WRITE: wdata=%d, fifo_len=%d", wdata, len(self._fifo)
                )
            else:
                # Under protocol-correct drivers, this should not happen.
                self._writes_dropped += 1
                self.logger.warning(
                    "Ref-model logical FIFO overflow: depth=%d, len=%d, "
                    "dropping wdata=%d",
                    self.depth,
                    len(self._fifo),
                    wdata,
                )

        # We don't model expected wfull closely; leave it as None so any
        # comparator that looks at it can treat it as don't-care.
        tr.wfull = None
        return tr

    # ------------------------------------------------------------------
    # Read-domain behavior (rclk domain)
    # ------------------------------------------------------------------

    def _calc_read_exp(self, tr: RadAsyncFifoReadItem) -> RadAsyncFifoReadItem:
        """Process read-domain transaction (rinc, rdata).

        We consider a "real read" to occur whenever:
            rinc == 1 and the logical FIFO is non-empty.

        For real reads:
            - Pop the head of the logical FIFO.
            - Drive exp.rdata to that value.

        For non-real reads:
            - Set exp.rdata = None so the comparator can ignore it.

        We do not attempt to model rempty timing; exp.rempty is always None.
        """

        if self._rrst_active:
            tr.rdata = None
            tr.rempty = None
            return tr

        rinc = tr.rinc if tr.rinc is not None else 0

        # Determine whether this is a "real read" in the logical model.
        has_data = len(self._fifo) > 0
        read_en = bool(rinc and has_data)

        if read_en:
            expected = self._fifo.popleft()
            self._reads_accepted += 1
            tr.rdata = expected
            self.logger.debug(
                "REF READ: expected_rdata=%d, fifo_len=%d",
                expected,
                len(self._fifo),
            )
        else:
            # No data consumed this cycle; don't-check rdata.
            tr.rdata = None
            if rinc and not has_data:
                # rinc asserted but FIFO empty in model – under the current
                # protocol-aware driver this should not occur.
                self._reads_blocked += 1
                self.logger.warning(
                    "Ref-model: rinc=1 but logical FIFO empty; blocked read."
                )

        # Expected rempty is not checked in this environment.
        tr.rempty = None

        return tr
