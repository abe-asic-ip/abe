# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_sb.py

"""Scoreboard for rad_async_fifo using base class architecture."""

from __future__ import annotations

from abe.rad.shared.dv import BaseSb, BaseSbPredictor

from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem


class RadAsyncFifoSbPredictor(BaseSbPredictor["RadAsyncFifoReadItem"]):
    """Predictor for async FIFO that processes both write and read items.

    Receives both RadAsyncFifoWriteItem (from write agent) and RadAsyncFifoReadItem
    (from read agent). Processes both through the reference model to maintain FIFO
    state, but only forwards read items to the comparator since write outputs (wfull)
    are not checked.
    """

    def write(self, tt: RadAsyncFifoReadItem | RadAsyncFifoWriteItem) -> None:
        """Process items through ref model, but only forward 'real read' items.

        Both write and read items update the ref model's FIFO state, but only
        read items that represent 'real reads' (rinc && !rempty) are forwarded
        to the comparator for output checking.

        The ref model sets exp.rdata to None for non-real-reads, which we use
        as the signal to skip forwarding to the comparator.
        """

        # Clone and compute expected (this updates ref model state)
        exp = tt.clone()
        # Type ignore: ref model actually handles both item types
        exp = self.ref_model.calc_exp(exp)  # type: ignore[arg-type]

        if isinstance(exp, RadAsyncFifoReadItem):
            # Only forward to comparator if this is a 'real read'
            # The ref model sets exp.rdata to None when rinc && !rempty is false
            if exp.rdata is not None:
                # Attach a snapshot of the ref-model's internal state for debug.
                # This attribute is consumed by RadAsyncFifoReadItem.compare_out()
                # on mismatch.
                if hasattr(self.ref_model, "snapshot_state"):
                    # pylint: disable=line-too-long
                    exp.debug_state = self.ref_model.snapshot_state()  # type: ignore[attr-defined]
                    # pylint: enable=line-too-long

                self.logger.debug(
                    "Forwarding REAL READ item to comparator: rinc=%d, rdata=%d",
                    exp.rinc,
                    exp.rdata,
                )
                self.results_ap.write(exp)
            else:
                # Read input sampled but not a real read (rinc=0 or rempty=1)
                self.logger.debug(
                    "Skipping non-real-read item: rinc=%d, rdata=None", exp.rinc
                )
        else:
            # Write items update FIFO state but outputs (wfull) are not checked
            self.logger.debug("Skipping write item (not forwarded to comparator)")


class RadAsyncFifoSb(BaseSb["RadAsyncFifoReadItem"]):
    """Scoreboard for async FIFO that checks read-side outputs.

    Uses the base scoreboard architecture from BaseSb with predictor,
    reference model, and comparator.

    Only read-side outputs (rdata, rempty) are compared against expected values.
    Write-side outputs (wfull) are not checked by this scoreboard.

    The dual reset handling (wrst, rrst) is managed by RadAsyncFifoResetSink
    which directly calls methods on the reference model.

    Note: Uses RadAsyncFifoSbPredictor (set via factory override) which filters
    out write items so only read outputs are checked.
    """
