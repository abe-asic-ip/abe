# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/cocotb/task.pyi

"""Type stubs for cocotb.task."""

from typing import Any, Generator

class Task:  # pylint: disable=too-few-public-methods
    """Task"""

    def cancel(self) -> None:
        """cancel"""

    def __await__(self) -> Generator[Any, None, Any]:
        """Make Task awaitable."""
