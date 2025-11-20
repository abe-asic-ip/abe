# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_sb_predictor.py

"""Reusable predictor."""

from __future__ import annotations

from typing import Generic, TypeVar

import pyuvm

from . import utils_dv
from .base_item import BaseItem
from .base_ref_model import BaseRefModel

T = TypeVar("T", bound=BaseItem)


class BaseSbPredictor(pyuvm.uvm_subscriber, Generic[T]):
    """Predictor that generates expected transactions using a reference model.

    This component receives input transactions from the DUT input monitor,
    clones them to maintain immutability, passes them to a reference model
    to compute expected outputs, and publishes the expected transactions.

    Flow:
        Input Transaction → Clone → Reference Model → Expected Transaction
                                                    ↓
                                              results_ap (to comparator)

    Components:
        ref_model (BaseRefModel): The reference model that computes expected
                                 DUT behavior

    Analysis Port:
        results_ap: Publishes expected transactions to comparator's exp_fifo

    Transaction Cloning:
        Input transactions are cloned before processing to maintain 0-time
        discipline - published transactions remain immutable and cannot be
        modified by downstream components.

    Reset Handling:
        Forwards reset events to the reference model via reset_change(),
        allowing the model to reset its internal state.

    Reference:
        C.E. Cummings, "OVM/UVM Scoreboards - Fundamental Architectures,"
        SNUG 2013 (Silicon Valley)

    Example:
        >>> # Typically used within BaseSb
        >>> # Override reference model type if needed
        >>> factory.set_type_override_by_type(
        ...     BaseRefModel, MyCustomRefModel
        ... )
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)

        self.results_ap: pyuvm.uvm_analysis_port[T] = pyuvm.uvm_analysis_port(
            f"{name}.results_ap", self
        )
        self.ref_model: BaseRefModel[T] = pyuvm.uvm_factory().create_object_by_type(
            BaseRefModel, name=f"{name}.ref_model"
        )

    def reset_change(self, value: int, active: bool) -> None:
        """Apply reset to reference model."""
        self.logger.debug("reset_change begin")
        self.ref_model.reset_change(value, active)
        self.logger.debug(f"reset_change end: value={value} active={active}")

    def write(self, tt: T) -> None:
        """
        - Receives sampled transactions (type T)
        - Makes a clone to keep broadcast transactions immutable (0-time discipline)
        - Uses a DUT-specific BaseRefModel[T] to compute expected
        - Publishes expected on results_ap
        """
        exp = tt.clone()
        exp = self.ref_model.calc_exp(exp)
        self.results_ap.write(exp)
