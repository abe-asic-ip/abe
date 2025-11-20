# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_sequence.py

# pylint: disable=duplicate-code

"""Sequence items and sequences for template verification."""

from __future__ import annotations

from abe.rad.shared.dv import BaseSequence

from .template_item import TemplateItem


class TemplateSequence(BaseSequence[TemplateItem]):
    """Generate a stream of random async toggles with small timing jitter."""

    def __init__(self, name: str = "template_rand_seq", seq_len: int = 100) -> None:
        super().__init__(name, seq_len)
        self._me = self.__class__.__name__  # keep
        raise NotImplementedError("implement __init__")
        # self.seq_len = utils_cli.get_int_setting(
        #     "RAD_TEMPLATE_SEQ_LEN", self.seq_len
        # )

    async def body_pre(self) -> None:
        """Get _clock_period_ps from uvm_config.db."""
        self.logger.debug("%s body_pre begin", self._me)
        await super().body_pre()
        raise NotImplementedError("implement body_pre")
        # self.logger.debug("%s body_pre begin", self._me)

    async def set_item_inputs(self, item: TemplateItem, index: int) -> None:
        raise NotImplementedError("implement set_item_inputs")
