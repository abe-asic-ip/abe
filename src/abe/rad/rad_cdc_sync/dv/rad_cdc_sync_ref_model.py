# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/rad_cdc_sync_ref_model.py

"""cdc_sync reference model."""

from __future__ import annotations

from collections import deque

from abe.rad.shared.dv import BaseRefModel, utils_cli

from .rad_cdc_sync_item import RadCdcSyncItem


class RadCdcSyncRefModel(BaseRefModel[RadCdcSyncItem]):
    """Implement reset and calc_exp_out."""

    def __init__(self, name: str = "cdc_sync_ref_model") -> None:
        super().__init__(name)
        # Configuration default
        self.stages: int = 2
        self.val_on_reset: int = 0
        # Configuration CLI override
        self.stages = int(utils_cli.get_int_setting("RAD_CDC_STAGES", self.stages))
        self.val_on_reset = int(
            bool(utils_cli.get_int_setting("RAD_CDC_VAL_ON_RESET", self.val_on_reset))
        )
        # Configuration validation
        self.stages = max(2, self.stages)
        self.val_on_reset = 1 if self.val_on_reset else 0
        # Internal state
        self._shreg: deque[int] = deque([0, 0], maxlen=2)

    def reset_change(self, value: int, active: bool) -> None:
        self.logger.debug("reset_change begin")
        super().reset_change(value, active)
        self._shreg = deque([self.val_on_reset] * self.stages, maxlen=self.stages)
        self.logger.debug("reset_change end")

    def calc_exp(self, tr: RadCdcSyncItem) -> RadCdcSyncItem:
        if self._reset_active:
            tr.sync_o = self.val_on_reset
            return tr
        async_i = int(tr.async_i or 0)
        self._shreg.appendleft(async_i)
        tr.sync_o = self._shreg[-1]
        return tr
