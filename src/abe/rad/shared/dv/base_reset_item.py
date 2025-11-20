# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_reset_item.py

"""Base reset item."""

from __future__ import annotations

from .base_item import BaseItem


class BaseResetItem(BaseItem):
    """Transaction item representing a reset signal observation.

    This item captures both the raw signal level and the polarity-resolved
    assertion state, making testbenches polarity-neutral.

    Attributes:
        value (int | None): Raw resolved signal level (0 or 1)
        active (bool | None): Polarity-resolved state:
                             True = reset is asserted (DUT in reset)
                             False = reset is deasserted (DUT operational)

    The 'active' field abstracts away the reset polarity (active-high vs active-low),
    allowing downstream components to use a consistent semantic interpretation.

    Example:
        >>> item = BaseResetItem()
        >>> item.value = 0
        >>> item.active = True  # For active-low reset, 0 means asserted
    """

    def __init__(self, name: str = "reset_tr") -> None:
        super().__init__(name)
        self.value: int | None = None
        self.active: bool | None = None

    def _in_fields(self) -> tuple[str, ...]:
        return ("value", "active")
