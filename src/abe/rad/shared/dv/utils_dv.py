# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/utils_dv.py

"""Design verification utilities for pyuvm and cocotb interaction.

This module provides type-safe, lint-friendly wrappers around pyuvm's config_db
and utilities for working with cocotb signal handles. It addresses common pain
points with dynamic attribute access and provides clear error messages.

Key Features:
    - Type-safe config_db access with optional/required variants
    - Signal handle resolution with clear error messages
    - Value extraction from Logic/LogicArray with X/Z handling
    - Logger configuration for components and non-components
    - Centralized log level management

Functions:
    Config DB:
        uvm_config_db(): Return cached config DB instance
        uvm_config_db_get_try(): Get config value or None if missing
        uvm_config_db_get(): Get config value or raise ConfigKeyError
        uvm_config_db_set(): Set config value

    Signal Access:
        get_signal(): Get signal handle from DUT with validation
        get_signal_value_int(): Extract integer from Logic/LogicArray (or None if X/Z)

    Logging:
        desired_log_level(): Get log level from COCOTB_LOG_LEVEL env var
        configure_component_logger(): Configure logger for UVM component
        configure_non_component_logger(): Configure logger for non-component

Error Handling:
    ConfigKeyError: Raised when required config_db key is missing
    RuntimeError: Raised when signal not found on DUT
    TypeError: Raised when signal has no .value property

Example:
    >>> # In component's end_of_elaboration_phase
    >>> dut = uvm_config_db_get(self, "dut")
    >>> clk = get_signal(dut, "clk")
    >>> period_ps = uvm_config_db_get_try(self, "clock_period_ps")
    >>> if period_ps is None:
    ...     period_ps = 1000  # default
    >>>
    >>> # Extract signal value safely
    >>> val = get_signal_value_int(dut.data.value)
    >>> if val is not None:
    ...     # Value is resolvable (no X/Z)
    ...     process(val)
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Protocol, TypeVar, Union, cast

import pyuvm
from cocotb.handle import SimHandleBase
from cocotb.types import Logic, LogicArray
from pyuvm import error_classes

T = TypeVar("T")
TT = TypeVar("TT", bound=pyuvm.uvm_test)


class ConfigKeyError(KeyError):
    """Raised when a required key is missing from pyuvm's config_db."""


class HasValue(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for signals with values."""

    @property
    def value(self) -> Any:
        """The value."""


def desired_log_level(default: int = logging.INFO) -> int:
    """Return desired log level from env vars or default."""
    name = (os.getenv("COCOTB_LOG_LEVEL") or "INFO").upper()
    return getattr(logging, name, default)


def configure_component_logger(comp: pyuvm.uvm_component) -> None:
    """Configure logger for a component."""
    comp.set_logging_level(desired_log_level())


def configure_non_component_logger(logger: logging.Logger) -> None:
    """Configure logger for a non-component"""
    logger.setLevel(desired_log_level())
    # Make sure it bubbles up to the root/cocotb handlers (don't add new handlers)
    logger.propagate = True


@lru_cache(maxsize=1)
def uvm_config_db() -> Any:
    """Return pyuvm's config DB object (cached) without tripping static checkers."""
    if hasattr(pyuvm, "ConfigDB") and callable(getattr(pyuvm, "ConfigDB")):
        return getattr(pyuvm, "ConfigDB")()
    return getattr(pyuvm, "uvm_config_db")()


def uvm_config_db_get_try(
    comp: pyuvm.uvm_component, key: str, inst: str = ""
) -> Any | None:
    """Return value or None if missing (no logging/raise).
    Note: pyuvm allows wildcards only for set(), not get()."""
    if inst == "*":
        inst = ""
    try:
        return cast(Any, uvm_config_db().get(comp, inst, key))
    except error_classes.UVMConfigItemNotFound:
        return None


def uvm_config_db_get(comp: pyuvm.uvm_component, key: str) -> object:
    """Like uvm_config_db_get_try but raises if key is missing."""
    val = uvm_config_db_get_try(comp, key)
    if val is not None:
        return val
    raise ConfigKeyError(
        f"config_db[{key!r}] missing for component '{comp.get_full_name()}'. "
        "Did you forget to set it in build/start_of_sim?"
    )


def uvm_config_db_set(
    ctx: pyuvm.uvm_component | None, inst_name: str, key: str, value: Any
) -> None:
    """Set a key in the config DB (inst_name like '' or '*' etc.)."""
    uvm_config_db().set(ctx, inst_name, key, value)


def get_signal(dut: Any, signal_name: str) -> SimHandleBase:
    """Return dut.<signal_name> or raise a clear error.

    Returns a SimHandleBase (cocotb signal handle) that has .value property.
    Raises RuntimeError if signal not found, TypeError if signal has no .value.
    """
    signal = getattr(dut, signal_name, None)
    if signal is None:
        raise RuntimeError(f"Signal '{signal_name}' not found on DUT")
    if not hasattr(signal, "value"):
        raise TypeError(f"Signal '{signal_name}' has no .value property")
    return cast(SimHandleBase, signal)


def get_signal_value_int(sig: Union[Logic, LogicArray]) -> int | None:
    """Return integer value if resolvable (no X/Z), else None."""
    if isinstance(sig, Logic):
        # cocotb.Logic supports int() conversion at runtime
        return (
            int(sig) if sig.is_resolvable else None
        )  # pyright: ignore[reportArgumentType]
    # LogicArray
    return sig.to_unsigned() if sig.is_resolvable else None
