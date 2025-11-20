# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/rad_cdc_sync_item.py

"""Sequence items and sequences for cdc_sync verification."""

from __future__ import annotations

from abe.rad.shared.dv import BaseItem


class RadCdcSyncItem(BaseItem):
    """One async toggle with a bit value and a pre-toggle delay in ps."""

    def __init__(self, name: str = "cdc_item") -> None:
        super().__init__(name)
        self.async_i: int | None = 0
        self.delay_ps: int = 0
        self.sync_o: int | None = 0

    def _in_fields(self) -> tuple[str, ...]:
        return ("async_i", "delay_ps")

    def _out_fields(self) -> tuple[str, ...]:
        return ("sync_o",)
