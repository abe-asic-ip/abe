# SPDX-FileCopyrightText: Year Author Name
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_template/dv/template_coverage.py

# pylint: disable=duplicate-code
# pylint: disable=fixme

"""Coverage."""

import pyuvm

from abe.rad.shared.dv import BaseCoverage

from .template_item import TemplateItem


class TemplateCoverage(BaseCoverage[TemplateItem]):
    """FIXME"""  # FIXME: document

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        raise NotImplementedError("implement __init__")
        # self.total: int = 0
        # self.zeros: int = 0
        # self.ones: int = 0

    def sample(self, tt: TemplateItem) -> None:
        """FIXME"""  # FIXME: document
        raise NotImplementedError("implement sample")
        # self.total += 1
        # if tt.async_i == 0:
        #     self.zeros += 1
        # elif tt.async_i == 1:
        #     self.ones += 1

    def report_phase(self) -> None:
        """FIXME"""  # FIXME: document
        self.logger.debug("report_phase begin")
        super().report_phase()
        raise NotImplementedError("implement report_phase")
        # self.logger.info(
        #     "TemplateCoverage summary: total=%d zeros=%d ones=%d",
        #     self.total,
        #     self.zeros,
        #     self.ones,
        # )
        # self.logger.debug("report_phase end")
