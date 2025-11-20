# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_sync/dv/test_rad_cdc_sync.py

"""Tests for cdc_sync verification."""

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

from .rad_cdc_sync_coverage import RadCdcSyncCoverage
from .rad_cdc_sync_driver import RadCdcSyncDriver
from .rad_cdc_sync_item import RadCdcSyncItem
from .rad_cdc_sync_monitor_in import RadCdcSyncMonitorIn
from .rad_cdc_sync_monitor_out import RadCdcSyncMonitorOut
from .rad_cdc_sync_ref_model import RadCdcSyncRefModel
from .rad_cdc_sync_sequence import RadCdcSyncSequence


@pyuvm.test()
class RadCdcSyncBaseTest(BaseTest):
    """Execute basic RadCdcSync test."""

    def set_factory_overrides(self) -> None:
        override = pyuvm.uvm_factory().set_type_override_by_type
        override(BaseCoverage, RadCdcSyncCoverage)
        override(BaseDriver, RadCdcSyncDriver)
        override(BaseItem, RadCdcSyncItem)
        override(BaseMonitorIn, RadCdcSyncMonitorIn)
        override(BaseMonitorOut, RadCdcSyncMonitorOut)
        override(BaseRefModel, RadCdcSyncRefModel)
        override(BaseSequence, RadCdcSyncSequence)
