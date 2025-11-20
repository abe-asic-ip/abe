# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/shared/dv/utils_cli.py

"""Command-line interface utilities for testbench configuration.

This module provides utilities for reading configuration from environment
variables and plusargs, following the standard UVM command-line processor
pattern. It supports automatic factory override application from CLI.

Configuration Precedence:
    1. Environment variables (NAME or RAD_NAME)
    2. Plusargs (+NAME or +NAME=value)
    3. Default values

Functions:
    get_bool_setting: Resolve boolean configuration
    get_str_setting: Resolve string configuration
    get_int_setting: Resolve integer configuration (supports hex with 0x)
    apply_factory_overrides_from_plusargs: Apply UVM factory overrides from CLI
    iter_plusargs: Iterate over all plusargs

Plusargs Format:
    Boolean flags: +NAME (treated as True) or +NAME=1/0/true/false/yes/no
    String values: +NAME=value
    Integer values: +NAME=123 or +NAME=0x7B (hex supported)
    Factory overrides: +uvm_set_type_override=req,over[,replace]
                      +uvm_set_inst_override=req,over,path

Environment Variables:
    PLUSARGS, COCOTB_PLUSARGS, or RAD_PLUSARGS: Space-separated plusargs
    Individual settings: NAME or RAD_NAME (e.g., CLOCK_PERIOD_PS=2000)

Reference:
    UVM Class Reference Manual - uvm_cmdline_processor
    https://www.accellera.org/images/downloads/standards/uvm/UVM_Class_Reference_Manual_1.2.pdf

Example:
    >>> # In test or component
    >>> period = get_int_setting("CLOCK_PERIOD_PS", 1000)
    >>> enable = get_bool_setting("COVERAGE_EN", True)
    >>>
    >>> # Apply factory overrides from command line
    >>> apply_factory_overrides_from_plusargs(logger)
"""

from __future__ import annotations

import logging
import os
from typing import Iterable, Tuple

import pyuvm

_TRUE_SET = {"1", "true", "yes", "y", "on"}
_FALSE_SET = {"0", "false", "no", "n", "off"}

# pyuvm typically throws lookup/value/type errors on bad overrides
_FACTORY_EXC: Tuple[type[BaseException], ...] = (KeyError, ValueError, TypeError)


def _parse_bool(s: str) -> bool | None:
    """Convert str to bool."""
    v = s.strip().lower()
    if v in _TRUE_SET:
        return True
    if v in _FALSE_SET:
        return False
    return None


def _get_plusarg(name: str) -> str | None:
    """Return the value of +NAME or +NAME=val if present; else None.
    - If found as '+NAME=val', returns 'val'
    - If found as bare '+NAME', returns '1' (treat like a true/enable flag)
    """
    plusargs = (
        os.environ.get("PLUSARGS", "")
        or os.environ.get("COCOTB_PLUSARGS", "")
        or os.environ.get("RAD_PLUSARGS", "")
    )
    if not plusargs:
        return None
    prefix = f"+{name}="
    for tok in plusargs.split():
        if tok.startswith(prefix):
            return tok[len(prefix) :]
        if tok == f"+{name}":
            # Interpret a bare flag as enabled/true
            return "1"
    return None


def iter_plusargs() -> Iterable[str]:
    """Yield +args from common env vars (same precedence you used in BaseTest)."""
    s = (
        os.environ.get("PLUSARGS", "")
        or os.environ.get("COCOTB_PLUSARGS", "")
        or os.environ.get("RAD_PLUSARGS", "")
    )
    return s.split()


def get_bool_setting(name: str, default: bool) -> bool:
    """
    Resolve a boolean setting with precedence: env > plusarg > default.
    bare +NAME is treated as True
    """
    for key in (name, f"RAD_{name}"):
        v = os.environ.get(key)
        if v is not None:
            parsed = _parse_bool(v)
            if parsed is not None:
                return parsed
    v = _get_plusarg(name)
    if v is not None:
        parsed = _parse_bool(v)
        if parsed is not None:
            return parsed
    return default


def get_str_setting(name: str, default: str) -> str:
    """Resolve a string setting: env > plusarg > default (always returns str)."""
    for key in (name, f"RAD_{name}"):
        v = os.environ.get(key)
        if v is not None:
            return v
    v = _get_plusarg(name)
    return v if v is not None else default


def get_int_setting(name: str, default: int) -> int:
    """Resolve an int setting: env > plusarg > default (always returns int)."""
    for key in (name, f"RAD_{name}"):
        v = os.environ.get(key)
        if v is not None:
            try:
                return int(v, 0)  # supports 10/16 prefixes (e.g., "0x10")
            except ValueError:
                continue  # try the RAD_ variant, then fall through to plusarg/default
    v = _get_plusarg(name)
    if v is not None:
        try:
            return int(v, 0)
        except ValueError:
            pass
    return default


def apply_factory_overrides_from_plusargs(logger: logging.Logger | None = None) -> None:
    """
    Reference: uvm_cmdline_processor in the UVM Class Reference Manual
    https://www.accellera.org/images/downloads/standards/uvm/UVM_Class_Reference_Manual_1.2.pdf
    Parse +uvm_set_type_override / +uvm_set_inst_override from PLUSARGS and apply
    via pyuvm's factory. Safe to call multiple times.
    """
    log = logger or logging.getLogger("rad.utils_cli.factory")
    f = pyuvm.uvm_factory()

    for tok in iter_plusargs():
        if tok.startswith("+uvm_set_type_override="):
            body = tok.split("=", 1)[1]
            parts = [p.strip() for p in body.split(",")]
            if len(parts) not in (2, 3):
                log.warning("Bad +uvm_set_type_override: %s", tok)
                continue
            req, over = parts[0], parts[1]
            replace = True if len(parts) == 2 else (parts[2] != "0")
            try:
                f.set_type_override_by_name(req, over, replace=replace)
                log.debug(
                    "Factory: type override %s -> %s (replace=%s)", req, over, replace
                )
            except _FACTORY_EXC as e:  # pragma: no cover
                log.warning("Override failed (%s): %s", tok, e)

        elif tok.startswith("+uvm_set_inst_override="):
            body = tok.split("=", 1)[1]
            parts = [p.strip() for p in body.split(",")]
            if len(parts) != 3:
                log.warning("Bad +uvm_set_inst_override: %s", tok)
                continue
            req, over, path = parts
            try:
                f.set_inst_override_by_name(req, over, path)
                log.debug("Factory: inst override %s @ %s -> %s", req, path, over)
            except _FACTORY_EXC as e:  # pragma: no cover
                log.warning("Override failed (%s): %s", tok, e)
