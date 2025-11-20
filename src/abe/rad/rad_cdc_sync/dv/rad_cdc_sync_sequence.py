# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/rad_cdc_sync_sequence.py

"""Sequence items and sequences for cdc_sync verification."""

from __future__ import annotations

import random

from abe.rad.shared.dv import BaseSequence, utils_cli, utils_dv

from .rad_cdc_sync_item import RadCdcSyncItem


class RadCdcSyncSequence(BaseSequence[RadCdcSyncItem]):
    """Generate a stream of random async toggles with small timing jitter."""

    def __init__(self, name: str = "cdc_rand_seq", seq_len: int = 100) -> None:
        super().__init__(name, seq_len)
        self._me = self.__class__.__name__
        self.seq_len = utils_cli.get_int_setting("RAD_CDC_SYNC_SEQ_LEN", self.seq_len)
        self.clock_period_ps: int = 1_000
        self._state: int = 0  # ensure observable toggling

    async def body_pre(self) -> None:
        """Get _clock_period_ps from uvm_config.db."""
        self.logger.debug("%s body_pre begin", self._me)
        await super().body_pre()
        v = utils_dv.uvm_config_db_get_try(self.sequencer, "clock_period_ps")
        if isinstance(v, int):
            self.clock_period_ps = v
        if self.clock_period_ps <= 0:
            raise ValueError("clock_period_ps must be > 0")
        self.logger.debug("%s body_pre begin", self._me)

    async def set_item_inputs(self, item: RadCdcSyncItem, index: int) -> None:
        # Enforce visible toggling
        self._state ^= 1
        item.async_i = self._state
        # define jitter range as +/- 20% of clock period
        t = self.clock_period_ps
        win = t // 5
        setup = (t // 2) - win
        hold = (t // 2) + win
        item.delay_ps = random.randrange(setup, hold)
        # self.logger.debug(
        #    "set_item_inputs[%d]: async_i=%d delay_ps=%d",
        #    index,
        #    item.async_i,
        #    item.delay_ps,
        # )
