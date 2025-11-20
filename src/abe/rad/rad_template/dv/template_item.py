# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_item.py

# pylint: disable=duplicate-code
# pylint: disable=fixme

"""Sequence items and sequences for template verification."""

from __future__ import annotations

from abe.rad.shared.dv import BaseItem


class TemplateItem(BaseItem):
    """FIXME"""  # FIXME: document

    def __init__(self, name: str = "template_item") -> None:
        super().__init__(name)
        raise NotImplementedError("implement __init__")
        # self.async_i: int | None = 0
        # self.delay_ps: int = 0
        # self.sync_o: int | None = 0

    def _in_fields(self) -> tuple[str, ...]:
        raise NotImplementedError("implement _in_fields")
        # return ("async_i", "delay_ps")

    def _out_fields(self) -> tuple[str, ...]:
        raise NotImplementedError("implement _out_fields")
        # return ("sync_o",)
