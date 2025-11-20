# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/cocotb/__init__.pyi

# pylint: disable=unused-argument

"""Type stubs for cocotb."""

from typing import Any, Awaitable

from cocotb.task import Task

top: Any

def start_soon(coro: Awaitable[Any]) -> Task:
    """start_soon - accepts any awaitable (coroutine, task, etc.)"""
