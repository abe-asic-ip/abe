# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_ref_model.py

"""rad_cdc_mcp reference model (single-word CDC transfer).

This model implements the expected behavior of a multi-cycle pulse (MCP) CDC:

* Sends (a-domain):
  - When asend == 1 and the MCP is ready (aready == 1), capture adatain
    and mark the MCP as busy until acknowledged from b-domain.
  - aready/bvalid from the DUT are not modeled or checked here.

* Loads (b-domain):
  - When bload == 1 and data is valid (bvalid == 1), the b-domain consumes
    the data and sends an acknowledgment back to a-domain.
  - If no "real load" occurs, exp.bdata is set to None so the comparator
    can treat it as "don't care".

This keeps the reference model focused on **data integrity** and
protocol correctness, while the **drivers** enforce protocol timing with respect
to aready/bvalid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from abe.rad.shared.dv import BaseRefModel, utils_cli

if TYPE_CHECKING:
    from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem
else:
    # Import at runtime for isinstance checks
    from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem


class RadCdcMcpRefModel(BaseRefModel):  # pylint: disable=too-many-instance-attributes
    """Generic CDC MCP reference model based on single-word transfer."""

    # ------------------------------------------------------------------
    # Construction / configuration
    # ------------------------------------------------------------------

    def __init__(self, name: str = "rad_cdc_mcp_ref_model") -> None:
        super().__init__(name)

        # Configuration defaults (can be overridden via CLI env vars)
        self.dsize: int = 8

        self.dsize = int(utils_cli.get_int_setting("RAD_CDC_MCP_DSIZE", self.dsize))

        # Clamp to reasonable minimums
        self.dsize = max(1, self.dsize)

        # Derived constants
        self.data_mask: int = (1 << self.dsize) - 1

        # Internal MCP state: single data word and busy flag
        self._data_in_flight: int | None = None

        # Track whether each domain is currently in reset
        self._arst_active: bool = False
        self._brst_active: bool = False

        # Simple counters for debug/statistics
        self._sends_accepted: int = 0
        self._sends_dropped: int = 0  # should be 0 under protocol-correct drivers
        self._loads_accepted: int = 0
        self._loads_blocked: int = 0

    # ------------------------------------------------------------------
    # Reset handling
    # ------------------------------------------------------------------

    def _clear_state(self) -> None:
        """Clear shared MCP state and counters."""
        self._data_in_flight = None
        self._sends_accepted = 0
        self._sends_dropped = 0
        self._loads_accepted = 0
        self._loads_blocked = 0

    def _clear_a_domain(self) -> None:
        """Reset a-domain state.

        For this simplified model, a-domain and b-domain share the
        same logical transfer state, so we conservatively clear shared state when
        either side asserts reset.
        """
        self._clear_state()

    def _clear_b_domain(self) -> None:
        """Reset b-domain state (see _clear_a_domain)."""
        self._clear_state()

    def arst_change(self, value: int, active: bool) -> None:
        """Handle a-domain reset change."""
        self.logger.debug("arst_change: value=%d active=%s", value, active)
        self._arst_active = active
        if active:
            self._clear_a_domain()

    def brst_change(self, value: int, active: bool) -> None:
        """Handle b-domain reset change."""
        self.logger.debug("brst_change: value=%d active=%s", value, active)
        self._brst_active = active
        if active:
            self._clear_b_domain()

    # Legacy wrst_change/rrst_change for compatibility
    def wrst_change(self, value: int, active: bool) -> None:
        """Handle write-domain reset change (legacy compatibility)."""
        self.arst_change(value, active)

    def rrst_change(self, value: int, active: bool) -> None:
        """Handle read-domain reset change (legacy compatibility)."""
        self.brst_change(value, active)

    def reset_change(self, value: int, active: bool) -> None:
        """Legacy single reset - apply to both domains for compatibility."""
        self.logger.debug("reset_change begin value=%d active=%s", value, active)
        super().reset_change(value, active)
        self._arst_active = active
        self._brst_active = active
        self._clear_state()
        self.logger.debug("reset_change end")

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def snapshot_state(self) -> dict:
        """Return a snapshot of logical MCP state for debug.

        Used by the scoreboard on mismatches to give context.
        """
        return {
            "data_in_flight": self._data_in_flight,
            "sends_accepted": self._sends_accepted,
            "sends_dropped": self._sends_dropped,
            "loads_accepted": self._loads_accepted,
            "loads_blocked": self._loads_blocked,
        }

    # ------------------------------------------------------------------
    # Main calc_exp entry point
    # ------------------------------------------------------------------

    def calc_exp(
        self, tr: RadCdcMcpWriteItem | RadCdcMcpReadItem
    ) -> RadCdcMcpWriteItem | RadCdcMcpReadItem:
        """Compute expected behavior for a send or load transaction.

        Sends:
          - Update the internal logical MCP state only.
        Loads:
          - Update the logical MCP state and drive exp.bdata for comparison.
        """
        if isinstance(tr, RadCdcMcpWriteItem):
            return self._calc_send_exp(tr)

        return self._calc_load_exp(tr)

    # ------------------------------------------------------------------
    # a-domain behavior (aclk domain)
    # ------------------------------------------------------------------

    def _calc_send_exp(self, tr: RadCdcMcpWriteItem) -> RadCdcMcpWriteItem:
        """Process a-domain transaction (asend, adatain)."""

        if self._arst_active:
            # During a-domain reset we don't update state, and we don't care
            # about aready predictions in this simplified model.
            tr.aready = None
            return tr

        # Inputs, with None treated as 0
        asend = tr.asend if tr.asend is not None else 0
        adatain = tr.adatain if tr.adatain is not None else 0
        adatain &= self.data_mask

        if asend:
            if self._data_in_flight is None:
                # MCP is ready, accept the send
                self._data_in_flight = adatain
                self._sends_accepted += 1
                self.logger.debug(
                    "REF SEND: adatain=%d, data_in_flight=%d",
                    adatain,
                    self._data_in_flight,
                )
            else:
                # Under protocol-correct drivers, this should not happen.
                self._sends_dropped += 1
                self.logger.warning(
                    "Ref-model MCP busy: data_in_flight=%d, dropping adatain=%d",
                    self._data_in_flight,
                    adatain,
                )

        # We don't model expected aready closely; leave it as None so any
        # comparator that looks at it can treat it as don't-care.
        tr.aready = None
        return tr

    # ------------------------------------------------------------------
    # b-domain behavior (bclk domain)
    # ------------------------------------------------------------------

    def _calc_load_exp(self, tr: RadCdcMcpReadItem) -> RadCdcMcpReadItem:
        """Process b-domain transaction (bload, bdata).

        We consider a "real load" to occur whenever:
            bload == 1 and data is in flight (bvalid == 1).

        For real loads:
            - Consume the data in flight.
            - Drive exp.bdata to that value.

        For non-real loads:
            - Set exp.bdata = None so the comparator can ignore it.

        We do not attempt to model bvalid timing; exp.bvalid is always None.
        """

        if self._brst_active:
            tr.bdata = None
            tr.bvalid = None
            return tr

        bload = tr.bload if tr.bload is not None else 0

        # Determine whether this is a "real load" in the logical model.
        has_data = self._data_in_flight is not None
        load_en = bool(bload and has_data)

        if load_en:
            expected = self._data_in_flight
            self._data_in_flight = None  # Clear the data in flight
            self._loads_accepted += 1
            tr.bdata = expected
            self.logger.debug(
                "REF LOAD: expected_bdata=%d, data_in_flight=%s",
                expected,
                self._data_in_flight,
            )
        else:
            # No data consumed this cycle; don't-check bdata.
            tr.bdata = None
            if bload and not has_data:
                # bload asserted but no data in flight in model – under the current
                # protocol-aware driver this should not occur.
                self._loads_blocked += 1
                self.logger.debug(
                    "Ref-model: bload=1 but no data in flight; blocked load."
                )

        # Expected bvalid is not checked in this environment.
        tr.bvalid = None

        return tr
