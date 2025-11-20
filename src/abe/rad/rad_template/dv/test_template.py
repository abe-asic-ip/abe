# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/test_template.py

# pylint: disable=duplicate-code

"""Tests for template verification."""

from __future__ import annotations

import pyuvm

from abe.rad.shared.dv import (
    BaseCoverage,
    BaseDriver,
    BaseItem,
    BaseMonitorIn,
    BaseMonitorOut,
    BaseRefModel,
    BaseSequence,
    BaseTest,
)

from .template_coverage import TemplateCoverage
from .template_driver import TemplateDriver
from .template_item import TemplateItem
from .template_monitor_in import TemplateMonitorIn
from .template_monitor_out import TemplateMonitorOut
from .template_ref_model import TemplateRefModel
from .template_sequence import TemplateSequence


@pyuvm.test()
class TemplateBaseTest(BaseTest):
    """Execute basic Template test."""

    def set_factory_overrides(self) -> None:
        override = pyuvm.uvm_factory().set_type_override_by_type
        override(BaseCoverage, TemplateCoverage)
        override(BaseDriver, TemplateDriver)
        override(BaseItem, TemplateItem)
        override(BaseMonitorIn, TemplateMonitorIn)
        override(BaseMonitorOut, TemplateMonitorOut)
        override(BaseRefModel, TemplateRefModel)
        override(BaseSequence, TemplateSequence)
