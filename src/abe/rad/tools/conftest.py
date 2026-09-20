# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/conftest.py

"""Shared pytest fixtures for the dv tool tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def build_ctx(tmp_path: Path) -> Callable[..., dict]:
    """Return a factory for a minimal dv build context.

    The output directory is under tmp_path, so nothing is written to the repo.
    Keyword arguments override or extend the defaults.
    """

    def make(**overrides: object) -> dict:
        ctx: dict = {
            "sim": "verilator",
            "outdir": str(tmp_path),
            "waves": True,
            "waves_fmt": "fst",
            "design": "rad_async_fifo",
            "user_build_args": [],
        }
        ctx.update(overrides)
        return ctx

    return make
