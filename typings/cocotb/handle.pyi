# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/cocotb/handle.pyi

"""Type stubs for cocotb.handle module."""

from typing import Any

from cocotb.triggers import Edge

class SimHandleBase:
    """Base class for simulation object handles."""

    @property
    def value(self) -> Any:
        """Get the value of the handle."""

    @value.setter
    def value(self, val: Any) -> None:
        """Set the value of the handle."""

    @property
    def name(self) -> str:
        """Get the name of the handle."""

    @property
    def rising_edge(self) -> Edge:
        """Create a trigger for rising edge."""

    @property
    def falling_edge(self) -> Edge:
        """Create a trigger for falling edge."""

    @property
    def value_change(self) -> Edge:
        """Create a trigger for any value change."""

class LogicObject(SimHandleBase):
    """Handle to a logic signal in the simulation."""

class ModifiableObject(SimHandleBase):
    """Handle to a modifiable object in the simulation."""
