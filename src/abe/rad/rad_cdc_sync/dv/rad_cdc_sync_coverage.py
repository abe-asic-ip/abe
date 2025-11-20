# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/rad_cdc_sync_coverage.py

"""Coverage."""

import pyuvm

from abe.rad.shared.dv import BaseCoverage

from .rad_cdc_sync_item import RadCdcSyncItem


class RadCdcSyncCoverage(BaseCoverage[RadCdcSyncItem]):
    """Super-light coverage: count input samples (0/1) for basic checking."""

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        self.total: int = 0
        self.zeros: int = 0
        self.ones: int = 0

    def sample(self, tt: RadCdcSyncItem) -> None:
        """Update simple hit counters."""
        self.total += 1
        if tt.async_i == 0:
            self.zeros += 1
        elif tt.async_i == 1:
            self.ones += 1

    def report_phase(self) -> None:
        """Print simple counters (and let BaseCoverage handle YAML/export)."""
        self.logger.debug("report_phase begin")
        super().report_phase()
        self.logger.info(
            "CdcSyncCoverage summary: total=%d zeros=%d ones=%d",
            self.total,
            self.zeros,
            self.ones,
        )
        self.logger.debug("report_phase end")
