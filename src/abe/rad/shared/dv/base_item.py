# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/base_item.py

"""Base sequence item with a class-level handle to the bench configuration."""

from __future__ import annotations

import copy
import json
from typing import Iterable, Self

import pyuvm


class BaseItem(pyuvm.uvm_sequence_item):
    """Base transaction item with field management and comparison utilities.

    This class provides a comprehensive framework for transaction items with
    clear separation between input fields (randomized/constrained) and output
    fields (observed from DUT). It includes utilities for cloning, copying,
    comparison, and serialization.

    Subclasses must implement:
        _in_fields(): Return tuple of input field names
        _out_fields(): Return tuple of output field names

    The class provides:
    - Deep cloning for safe transaction copies
    - Field-wise copying between items of the same type
    - Separate comparison of input and output fields
    - JSON serialization for logging and debugging
    - Type-safe operations with runtime type checking

    Example:
        >>> class MyItem(BaseItem):
        ...     def __init__(self, name="my_item"):
        ...         super().__init__(name)
        ...         self.addr = 0
        ...         self.data = 0
        ...         self.response = 0
        ...
        ...     def _in_fields(self):
        ...         return ("addr", "data")
        ...
        ...     def _out_fields(self):
        ...         return ("response",)
    """

    def _in_fields(self) -> Iterable[str]:
        """Fields considered *inputs* (randomized / constrained)."""
        return ()

    def _out_fields(self) -> Iterable[str]:
        """Fields considered *outputs* (observed from DUT)."""
        return ()

    def _all_fields(self) -> tuple[str, ...]:
        # Preserve declared order while removing duplicates if any overlap
        seen: set[str] = set()
        ordered: list[str] = []
        for f in list(self._in_fields()) + list(self._out_fields()):
            if f not in seen:
                seen.add(f)
                ordered.append(f)
        return tuple(ordered)

    def clone(self) -> Self:
        """Deep copy so the clone can diverge safely."""
        return copy.deepcopy(self)

    def copy_from(self, other: Self) -> None:
        """Field-wise copy from another item of the same concrete type (in+out)."""
        if type(self) is not type(other):
            raise TypeError(
                f"copy_from: {type(other).__name__} -> {type(self).__name__}"
            )
        for f in self._all_fields():
            setattr(self, f, getattr(other, f))

    def to_dict(self) -> dict[str, object]:
        """Structured view for logging/JSON (in+out)."""
        return {f: getattr(self, f) for f in self._all_fields()}

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def inputs_str(self) -> str:
        """Return JSON string of input fields only."""
        return json.dumps(
            {f: getattr(self, f) for f in self._in_fields()}, sort_keys=True
        )

    def outputs_str(self) -> str:
        """Return JSON string of output fields only."""
        return json.dumps(
            {f: getattr(self, f) for f in self._out_fields()}, sort_keys=True
        )

    def compare_in(self, other: Self, *, fields: Iterable[str] | None = None) -> bool:
        """Compare only input fields."""
        if type(self) is not type(other):
            return False
        flist = list(fields) if fields is not None else list(self._in_fields())
        return all(getattr(self, f) == getattr(other, f) for f in flist)

    def compare_out(self, other: Self, *, fields: Iterable[str] | None = None) -> bool:
        """Compare only output fields."""
        if type(self) is not type(other):
            return False
        flist = list(fields) if fields is not None else list(self._out_fields())
        return all(getattr(self, f) == getattr(other, f) for f in flist)
