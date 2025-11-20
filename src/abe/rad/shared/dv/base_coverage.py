# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_coverage.py

"""Base functional coverage subscriber (cocotb-coverage + pyuvm)."""

from __future__ import annotations

import os
from typing import Generic, TypeVar

import pyuvm
from cocotb_coverage.coverage import coverage_db

from . import utils_dv
from .base_item import BaseItem

T = TypeVar("T", bound=BaseItem)


class BaseCoverage(pyuvm.uvm_subscriber, Generic[T]):
    """Functional coverage subscriber using cocotb-coverage.

    This subscriber receives transactions from monitors via its analysis_export
    and samples them for functional coverage. It integrates with cocotb-coverage's
    decorator-based coverage collection.

    Usage Pattern:
        1. Subclass BaseCoverage
        2. Override sample() method
        3. Decorate sample() with @CoverPoint and @CoverCross decorators
        4. Coverage is automatically collected when write() is called

    Configuration (via config_db):
        coverage_en (bool): Enable coverage collection (default: True)
                           If False, sample() is not called

    Environment Variables:
        COV_YAML: Path to write coverage YAML report (optional)

    The coverage database is automatically reported in report_phase and
    optionally exported to YAML if COV_YAML is set.

    Example:
        >>> from cocotb_coverage.coverage import CoverPoint
        >>>
        >>> class MyCoverage(BaseCoverage[MyItem]):
        ...     @CoverPoint(
        ...         "top.addr_coverage",
        ...         bins=list(range(256))
        ...     )
        ...     def sample(self, tr):
        ...         return tr.addr
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self.yaml_path: str | None = os.getenv("COV_YAML")
        self._coverage_en: bool = True

    def end_of_elaboration_phase(self) -> None:
        """Cache coverage_en."""
        self.logger.debug("end_of_elaboration_phase begin")
        super().end_of_elaboration_phase()
        cvrg = utils_dv.uvm_config_db_get_try(self, "coverage_en")
        if isinstance(cvrg, bool):
            self._coverage_en = cvrg
        self.logger.debug("end_of_elaboration_phase end")

    def write(self, tt: T) -> None:
        """Receive a transaction from a monitor and sample coverage."""
        if not self._coverage_en:
            return
        self.sample(tt)

    def sample(self, tt: T) -> None:  # pragma: no cover - abstract hook
        """Override in subclasses and decorate with CoverPoint/CoverCross."""
        raise NotImplementedError("Override in subclass and decorate with coverpoints")

    def report_phase(self) -> None:
        """Emit coverage report (and optional YAML) at end of sim."""
        self.logger.debug("report_phase begin")
        super().report_phase()
        if not self._coverage_en:
            return
        coverage_db.report_coverage(self.logger.debug)
        if self.yaml_path:
            coverage_db.export_to_yaml(self.yaml_path)
            self.logger.debug("Coverage YAML written to %s", self.yaml_path)
        self.logger.debug("report_phase end")
