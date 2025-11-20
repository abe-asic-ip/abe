# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_sequencer.py

"""Base sequencer, extendable."""

from __future__ import annotations

import pyuvm

from . import utils_dv


class BaseSequencer(pyuvm.uvm_sequencer):
    """Base sequencer for managing sequence execution.

    This sequencer provides the standard UVM sequencer functionality with
    proper logger configuration. It serves as a TLM connection point between
    sequences (transaction generators) and drivers (transaction executors).

    The sequencer:
    - Manages sequence arbitration when multiple sequences target it
    - Provides seq_item_export for driver connection
    - Handles sequence execution via the start() method
    - Configures logging based on environment settings

    Usage:
        The sequencer is typically created by BaseAgent when is_active=UVM_ACTIVE.
        Sequences call start(sequencer) to begin execution, and the driver pulls
        items via seq_item_port.get_next_item().

    This is an empty subclass that enables future expansion with custom
    functionality while maintaining compatibility with existing code.

    Example:
        >>> # Created by BaseAgent
        >>> sqr = factory.create_component_by_type(
        ...     BaseSequencer, parent_inst_path=path,
        ...     name="sqr", parent=self
        ... )
        >>> # Used by sequences
        >>> await my_sequence.start(sqr)
    """

    def __init__(self, name: str, parent: pyuvm.uvm_component | None) -> None:
        super().__init__(name, parent)
        utils_dv.configure_component_logger(self)
