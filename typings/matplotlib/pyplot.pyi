# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/matplotlib/pyplot.pyi

# pylint: disable=unused-argument

"""Type stubs for matplotlib.pyplot."""

from typing import Any

from matplotlib.figure import Figure

def figure(*args: Any, **kwargs: Any) -> Figure:
    """figure"""

def plot(*args: Any, **kwargs: Any) -> list[Any]:
    """plot"""

def xlabel(*args: Any, **kwargs: Any) -> Any:
    """xlabel"""

def ylabel(*args: Any, **kwargs: Any) -> Any:
    """ylabel"""

def title(*args: Any, **kwargs: Any) -> Any:
    """title"""

def grid(*args: Any, **kwargs: Any) -> Any:
    """grid"""

def legend(*args: Any, **kwargs: Any) -> Any:
    """legend"""

def tight_layout(*args: Any, **kwargs: Any) -> Any:
    """tight_layout"""

def savefig(*args: Any, **kwargs: Any) -> Any:
    """savefig"""

def show(*args: Any, **kwargs: Any) -> Any:
    """show"""

def close(*args: Any, **kwargs: Any) -> Any:
    """close"""
