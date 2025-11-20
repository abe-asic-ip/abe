# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/cocotb/types.pyi

"""Type stubs for cocotb.types module."""

from typing import Any

class Logic:
    """Type stub for cocotb Logic."""

    @property
    def is_resolvable(self) -> bool:
        """Check if array is resolvable (no X/Z)."""

    def to_unsigned(self) -> int:
        """Convert to unsigned integer."""

    def __int__(self) -> int:
        """Convert to integer."""

    def __index__(self) -> int:
        """Convert to integer index."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize."""

class LogicArray:
    """Type stub for cocotb LogicArray."""

    @property
    def is_resolvable(self) -> bool:
        """Check if array is resolvable (no X/Z)."""

    def to_unsigned(self) -> int:
        """Convert to unsigned integer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize."""
