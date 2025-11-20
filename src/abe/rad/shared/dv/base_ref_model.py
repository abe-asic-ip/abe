# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_ref_model.py

"""Reference model of DUT."""

import logging
from typing import Generic, TypeVar

import pyuvm

from .base_item import BaseItem

T = TypeVar("T", bound=BaseItem)


class BaseRefModel(pyuvm.uvm_object, Generic[T]):
    """Reference model for computing expected DUT behavior.

    This model provides the golden reference for DUT outputs. It maintains
    internal state as needed and processes input transactions to predict
    expected output transactions.

    The reference model:
    - Maintains DUT-specific internal state (queues, counters, etc.)
    - Responds to reset events to initialize/clear state
    - Computes expected outputs from input transactions

    Subclasses must implement:
        calc_exp(tr): Calculate expected output fields for a transaction

    Reset Handling:
        The reset_change(value, active) method is called when reset state
        changes. Subclasses should override to reset internal state when
        active=True.

    Design Pattern:
        This follows the UVM predictor/refmodel separation pattern where:
        - The predictor (BaseSbPredictor) receives input transactions
        - The reference model computes expected outputs
        - The comparator (BaseSbComparator) checks expected vs actual

    Reference:
        R. Salemi, "Python for RTL Verification"
        C.E. Cummings, "OVM/UVM Scoreboards – Fundamental Architectures,"
        SNUG 2013

    Example:
        >>> class FifoRefModel(BaseRefModel[FifoItem]):
        ...     def __init__(self, name="fifo_ref"):
        ...         super().__init__(name)
        ...         self.queue = []
        ...
        ...     def reset_change(self, value, active):
        ...         super().reset_change(value, active)
        ...         if active:
        ...             self.queue.clear()
        ...
        ...     def calc_exp(self, tr):
        ...         if tr.write:
        ...             self.queue.append(tr.data)
        ...         elif tr.read and self.queue:
        ...             tr.data_out = self.queue.pop(0)
        ...         return tr
    """

    def __init__(self, name: str = "ref_model") -> None:
        super().__init__(name)
        self._logger: logging.Logger = logging.getLogger(f"uvm.obj.{name}")
        self._reset_active: bool = False

    @property
    def logger(self) -> logging.Logger:
        """Logger with a familiar .info/.debug/.warning interface."""
        return self._logger

    def reset_change(self, value: int, active: bool) -> None:
        """Handle a change in reset."""
        self.logger.debug("reset_change begin")
        self._reset_active = active
        self.logger.debug("reset_change end: value = %d: active = %s", value, active)

    def calc_exp(self, tr: T) -> T:
        """Calculate expected output."""
        raise NotImplementedError
