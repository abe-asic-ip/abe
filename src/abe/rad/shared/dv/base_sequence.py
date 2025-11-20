# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_sequence.py

"""Unified base for item-generating sequences (UVM-style)."""

from __future__ import annotations

import logging
from typing import Generic, Type, TypeVar, cast

import pyuvm

from . import utils_dv
from .base_item import BaseItem
from .base_sequencer import BaseSequencer

T = TypeVar("T", bound=BaseItem)


class BaseSequence(pyuvm.uvm_sequence, Generic[T]):
    """Base class for item-generating sequences with factory support.

    This sequence implements the standard UVM pattern for generating transaction
    items with efficient factory-based object creation. It provides hooks for
    customization before and after the main sequence body.

    Execution Flow:
        1. body_pre() - Optional pre-sequence hook
        2. For each item (seq_len times):
           a. make_item(index) - Create transaction
           b. start_item(item) - Acquire sequencer grant
           c. set_item_inputs(item, index) - Randomize/configure (must implement)
           d. finish_item(item) - Send to driver and release grant
        3. body_post() - Optional post-sequence hook

    Subclasses must implement:
        set_item_inputs(item, index): Randomize or configure transaction fields

    Optional hooks:
        body_pre(): Called before generating items
        body_post(): Called after all items generated

    Attributes:
        seq_len (int): Number of items to generate (default: 100)
        sequencer (BaseSequencer): Target sequencer (set by pyuvm at runtime)
        logger: Logger for debug output

    Factory Optimization:
        The sequence determines the concrete item type from factory overrides
        once during body() and caches the constructor for efficient item creation
        in the hot path.

    Note:
        pyuvm attaches methods dynamically. This class provides type hints and
        forwarders for static analysis tools (pylint/mypy/Pylance).

    Example:
        >>> class MySequence(BaseSequence[MyItem]):
        ...     async def set_item_inputs(self, item, index):
        ...         item.addr = index % 256
        ...         item.data = random.randint(0, 255)
        ...
        >>> seq = factory.create_object_by_type(
        ...     BaseSequence, name="seq"
        ... )
        >>> await seq.start(sequencer)
    """

    def __init__(self, name: str = "seq", seq_len: int = 100) -> None:
        super().__init__(name)
        self.logger: logging.Logger = logging.getLogger(f"uvm.{name}")
        utils_dv.configure_non_component_logger(self.logger)
        self.sequencer: BaseSequencer  # pyuvm sets this at runtime on start()
        self._item_class_constructor: Type[T] | None = None
        self.seq_len: int = max(1, int(seq_len))
        # Subclasses can override seq_len here with CLI if desired.

    async def body(self) -> None:
        """UVM flow: start_item -> set_item_inputs -> finish_item, in a fixed loop."""
        self.logger.debug("BaseSequence body begin: length = %d", self.seq_len)
        # Hook for subclasses
        await self.body_pre()
        # Ask the factory what BaseItem ultimately resolves to (after overrides).
        probe = pyuvm.uvm_factory().create_object_by_type(
            BaseItem, name="probe_for_type"
        )
        # Cache the concrete constructor for the hot path.
        self._item_class_constructor = cast(Type[T], type(probe))
        # Store handles for hot path
        make = self.make_item
        set_inputs = self.set_item_inputs
        # Send the items
        for i in range(self.seq_len):
            item = make(i)
            await self.start_item(item)
            await set_inputs(item, i)
            await self.finish_item(item)
        # Hook for subclasses
        await self.body_post()
        self.logger.debug("BaseSequence body end")

    async def body_pre(self) -> None:
        """Placeholder."""
        self.logger.debug("BaseSequence body_pre begin")
        self.logger.debug("BaseSequence body_pre end")

    def make_item(self, index: int) -> T:
        """Create one transaction item efficiently (honors type overrides)."""
        if self._item_class_constructor is None:
            # Should not happen; keep a safe fallback.
            create = pyuvm.uvm_factory().create_object_by_type
            return cast(T, create(BaseItem, name=f"tr{index}"))
        return self._item_class_constructor(f"tr{index}")

    async def set_item_inputs(self, item: T, index: int) -> None:
        """Must be implemented in subclasses: randomize/tweak before finish_item."""
        raise NotImplementedError

    async def body_post(self) -> None:
        """Placeholder."""
        self.logger.debug("BaseSequence body_post begin")
        self.logger.debug("BaseSequence body_post end")
