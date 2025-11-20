# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_reset_sink.py

"""Forwards reset events into predictor (and optionally comparator)."""

from __future__ import annotations

from typing import Generic, TypeVar

import pyuvm

from . import utils_dv
from .base_driver import BaseDriver
from .base_reset_item import BaseResetItem
from .base_sb_predictor import BaseSbPredictor

T = TypeVar("T", bound=BaseResetItem)


class BaseResetSink(pyuvm.uvm_subscriber, Generic[T]):
    """Subscriber that forwards reset events to driver and predictor components.

    This component receives reset transactions from the reset monitor and
    forwards them to other components that need to respond to reset events.
    It acts as a distribution point for reset notifications.

    Connected Components:
        drv (BaseDriver | None): Driver to notify of reset changes
        sb_prd (BaseSbPredictor | None): Scoreboard predictor to notify

    The sink calls reset_change(value, active) on connected components,
    allowing them to respond appropriately (e.g., flushing state, resetting
    reference models).

    Configuration:
        flush_after_deassert (int): Number of items to flush after reset
                                    deassertion (currently unused, reserved
                                    for future enhancement)

    Usage Pattern:
        The BaseEnv automatically creates a BaseResetSink and connects it to
        the reset monitor, driver, and scoreboard predictor. Users typically
        don't need to interact with this component directly.

    Example:
        >>> # Typically created and connected by BaseEnv
        >>> reset_sink.drv = agent.drv
        >>> reset_sink.sb_prd = scoreboard.prd
        >>> mon_rst.ap.connect(reset_sink.analysis_export)
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
        self.drv: BaseDriver | None = None
        self.sb_prd: BaseSbPredictor | None = None
        self.flush_after_deassert: int = 0

    def write(self, tt: T) -> None:
        self.logger.debug("write begin")
        if tt.value is None or tt.active is None:
            return
        if self.drv is not None:
            self.drv.reset_change(tt.value, tt.active)
        if self.sb_prd is not None:
            self.sb_prd.reset_change(tt.value, tt.active)
        self.logger.debug("write end")
