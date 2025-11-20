# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_sb.py

"""Scoreboard for rad_cdc_mcp using base class architecture."""

from __future__ import annotations

from abe.rad.shared.dv import BaseSb, BaseSbPredictor

from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem


class RadCdcMcpSbPredictor(BaseSbPredictor["RadCdcMcpReadItem"]):
    """Predictor for CDC MCP that processes both send and load items.

    Receives both RadCdcMcpWriteItem (from a-domain agent) and RadCdcMcpReadItem
    (from b-domain agent). Processes both through the reference model to maintain MCP
    state, but only forwards load items to the comparator since send outputs (aready)
    are not checked.
    """

    def write(self, tt: RadCdcMcpReadItem | RadCdcMcpWriteItem) -> None:
        """Process items through ref model, but only forward 'real load' items.

        Both send and load items update the ref model's MCP state, but only
        load items that represent 'real loads' (bload && bvalid) are forwarded
        to the comparator for output checking.

        The ref model sets exp.bdata to None for non-real-loads, which we use
        as the signal to skip forwarding to the comparator.
        """

        # Clone and compute expected (this updates ref model state)
        exp = tt.clone()
        # Type ignore: ref model actually handles both item types
        exp = self.ref_model.calc_exp(exp)  # type: ignore[arg-type]

        if isinstance(exp, RadCdcMcpReadItem):
            # Only forward to comparator if this is a 'real load'
            # The ref model sets exp.bdata to None when bload && bvalid is false
            if exp.bdata is not None:
                # Attach a snapshot of the ref-model's internal state for debug.
                # This attribute is consumed by RadCdcMcpReadItem.compare_out()
                # on mismatch.
                if hasattr(self.ref_model, "snapshot_state"):
                    # pylint: disable=line-too-long
                    exp.debug_state = self.ref_model.snapshot_state()  # type: ignore[attr-defined]
                    # pylint: enable=line-too-long

                self.logger.debug(
                    "Forwarding REAL LOAD item to comparator: bload=%d, bdata=%d",
                    exp.bload,
                    exp.bdata,
                )
                self.results_ap.write(exp)
            else:
                # Load input sampled but not a real load (bload=0 or bvalid=0)
                self.logger.debug(
                    "Skipping non-real-load item: bload=%d, bdata=None", exp.bload
                )
        else:
            # Send items update MCP state but outputs (aready) are not checked
            self.logger.debug("Skipping send item (not forwarded to comparator)")


class RadCdcMcpSb(BaseSb["RadCdcMcpReadItem"]):
    """Scoreboard for CDC MCP that checks b-domain outputs.

    Uses the base scoreboard architecture from BaseSb with predictor,
    reference model, and comparator.

    Only b-domain outputs (bdata, bvalid) are compared against expected values.
    a-domain outputs (aready) are not checked by this scoreboard.

    The dual reset handling (arst, brst) is managed by RadCdcMcpResetSink
    which directly calls methods on the reference model.

    Note: Uses RadCdcMcpSbPredictor (set via factory override) which filters
    out send items so only load outputs are checked.
    """
