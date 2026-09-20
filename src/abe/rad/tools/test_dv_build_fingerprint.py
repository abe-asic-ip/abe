# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/test_dv_build_fingerprint.py

"""Unit tests for dv's build fingerprint (the hash in the build directory name).

A build refers to cocotb's libraries and the simulator's runtime files by
absolute path, so a new virtual environment or a Python, cocotb or simulator
upgrade must get a fresh build directory instead of reusing a stale one.
The toolchain lookup is monkeypatched, so these tests do not depend on which
simulator is installed.

Run with: pytest src/abe/rad/tools/test_dv_build_fingerprint.py
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from abe.rad.tools import dv

TOOLCHAIN = {
    "python": "3.14.7",
    "cocotb": "2.1.0",
    "cocotb_dir": "/venv/lib/python3.14/site-packages/cocotb",
    "simulator": "Verilator 5.052 2026-09-05",
}


def _with_toolchain(monkeypatch: pytest.MonkeyPatch, **changes: str) -> None:
    fake = {**TOOLCHAIN, **changes}
    monkeypatch.setattr(dv, "toolchain_fingerprint", lambda _sim: dict(fake))


def _leaf(ctx: dict) -> str:
    return dv._build_dir_for_ctx(ctx).name  # pylint: disable=protected-access


def test_same_inputs_give_same_build_dir(
    monkeypatch: pytest.MonkeyPatch, build_ctx: Callable[..., dict]
) -> None:
    """The hash is stable, so an unchanged setup reuses its build."""
    _with_toolchain(monkeypatch)
    assert _leaf(build_ctx()) == _leaf(build_ctx())


@pytest.mark.parametrize(
    ("key", "new_value"),
    [
        ("python", "3.15.0"),
        ("cocotb", "2.2.0"),
        ("cocotb_dir", "/other-venv/lib/python3.14/site-packages/cocotb"),
        ("simulator", "Verilator 5.054 2026-12-01"),
    ],
)
def test_toolchain_change_gives_new_build_dir(
    monkeypatch: pytest.MonkeyPatch,
    build_ctx: Callable[..., dict],
    key: str,
    new_value: str,
) -> None:
    """A new venv or a Python/cocotb/simulator upgrade must not reuse a build."""
    _with_toolchain(monkeypatch)
    before = _leaf(build_ctx())
    _with_toolchain(monkeypatch, **{key: new_value})
    after = _leaf(build_ctx())
    assert before != after
    assert before.startswith("rad_async_fifo.")
    assert after.startswith("rad_async_fifo.")


@pytest.mark.parametrize(
    "change",
    [
        {"waves": False},
        {"waves_fmt": "vcd"},
        {"user_build_args": ["-DSIMULATE_METASTABILITY"]},
        {"sim": "icarus"},
    ],
)
def test_original_build_knobs_still_matter(
    monkeypatch: pytest.MonkeyPatch, build_ctx: Callable[..., dict], change: dict
) -> None:
    """The fingerprint still distinguishes the settings it always did."""
    _with_toolchain(monkeypatch)
    assert _leaf(build_ctx()) != _leaf(build_ctx(**change))


def test_test_only_settings_do_not_change_build_dir(
    monkeypatch: pytest.MonkeyPatch, build_ctx: Callable[..., dict]
) -> None:
    """Seeds and test names affect the test run, not the compiled build."""
    _with_toolchain(monkeypatch)
    assert _leaf(build_ctx()) == _leaf(
        build_ctx(seed=7, test="test_rad_async_fifo", expect="FAIL")
    )


def test_build_dir_asks_for_the_toolchain_of_its_simulator(
    monkeypatch: pytest.MonkeyPatch, build_ctx: Callable[..., dict]
) -> None:
    """The toolchain is looked up for the simulator the build uses."""
    asked: list[str] = []

    def fake(sim: str) -> dict[str, str]:
        asked.append(sim)
        return dict(TOOLCHAIN)

    monkeypatch.setattr(dv, "toolchain_fingerprint", fake)
    _leaf(build_ctx(sim="icarus"))
    assert asked == ["icarus"]


def test_manifest_records_toolchain(
    monkeypatch: pytest.MonkeyPatch, build_ctx: Callable[..., dict]
) -> None:
    """manifest.json says which toolchain a build was made with."""
    _with_toolchain(monkeypatch)
    cfg = dv._make_build_cfg(build_ctx())  # pylint: disable=protected-access

    dv._write_build_manifest(cfg, status="built")  # pylint: disable=protected-access

    manifest = json.loads((cfg.build_dir / "manifest.json").read_text())
    assert manifest["toolchain"] == TOOLCHAIN
    assert manifest["fingerprint"] == cfg.build_dir.name
