# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_ref_model.py

# pylint: disable=duplicate-code

"""template reference model."""

from __future__ import annotations

from abe.rad.shared.dv import BaseRefModel

from .template_item import TemplateItem


class TemplateRefModel(BaseRefModel[TemplateItem]):
    """Implement reset and calc_exp_out."""

    def __init__(self, name: str = "template_ref_model") -> None:
        super().__init__(name)
        raise NotImplementedError("implement __init__")

    def reset_change(self, value: int, active: bool) -> None:
        self.logger.debug("reset_change begin")
        super().reset_change(value, active)
        raise NotImplementedError("implement reset_change")
        # self.logger.debug("reset_change end")

    def calc_exp(self, tr: TemplateItem) -> TemplateItem:
        raise NotImplementedError("implement calc_exp")
        # return tr
