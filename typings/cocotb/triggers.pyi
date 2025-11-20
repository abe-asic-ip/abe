# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/cocotb/triggers.pyi

# pylint: disable=unused-argument disable=too-few-public-methods

"""Type stubs for cocotb.triggers."""

from typing import Any, Awaitable

class _Trigger(Awaitable[Any]):
    def __await__(self) -> Any: ...

class Edge(_Trigger):
    """Edge trigger"""

class NextTimeStep(_Trigger):
    """NextTimeStep"""

class ReadOnly(_Trigger):
    """ReadOnly"""

class ReadWrite(_Trigger):
    """ReadWrite"""

class Timer(_Trigger):
    """Timer"""

    def __init__(self, time: int | float, unit: str | None = ...) -> None: ...

class Event:
    """Event"""

    def __init__(self, name: str | None = ...) -> None: ...
    def set(self) -> None:
        """set"""

    def clear(self) -> None:
        """clear"""

    def wait(self) -> _Trigger:
        """wait"""
