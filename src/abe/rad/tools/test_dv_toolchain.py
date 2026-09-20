# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/test_dv_toolchain.py

"""Unit tests for dv_toolchain (Python, cocotb and simulator identification).

The tool lookups are monkeypatched where needed, so these tests do not depend
on which simulator is installed.

Run with: pytest src/abe/rad/tools/test_dv_toolchain.py
"""

from __future__ import annotations

import platform
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest

from abe.rad.tools import dv_toolchain


@pytest.fixture(autouse=True)
def _fresh_cache() -> Iterator[None]:
    """The fingerprint is cached per process; keep tests independent."""
    dv_toolchain.toolchain_fingerprint.cache_clear()
    yield
    dv_toolchain.toolchain_fingerprint.cache_clear()


def test_fingerprint_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collects Python, cocotb (version and directory) and the simulator line."""
    monkeypatch.setattr(dv_toolchain.platform, "python_version", lambda: "9.9.9")
    monkeypatch.setattr(
        dv_toolchain.importlib.metadata, "version", lambda _name: "1.2.3"
    )
    monkeypatch.setattr(
        dv_toolchain.importlib.util,
        "find_spec",
        lambda _name: Mock(origin="/x/site-packages/cocotb/__init__.py"),
    )
    monkeypatch.setattr(dv_toolchain, "first_line", lambda cmd: f"ran {' '.join(cmd)}")

    fp = dv_toolchain.toolchain_fingerprint("verilator")

    assert fp == {
        "python": "9.9.9",
        "cocotb": "1.2.3",
        "cocotb_dir": str(Path("/x/site-packages/cocotb").resolve()),
        "simulator": "ran verilator --version",
    }


def test_icarus_uses_its_own_version_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each simulator is asked for its version the way it understands."""
    monkeypatch.setattr(dv_toolchain, "first_line", " ".join)
    fp = dv_toolchain.toolchain_fingerprint("icarus")
    assert fp["simulator"] == "iverilog -V"


def test_unknown_simulator_runs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrecognised simulator is reported as unavailable, without running it."""

    def boom(_cmd: object) -> str:
        raise AssertionError("should not run a tool for an unknown simulator")

    monkeypatch.setattr(dv_toolchain, "first_line", boom)
    fp = dv_toolchain.toolchain_fingerprint("questa")
    assert fp["simulator"] == "unavailable"


def test_real_environment_is_described() -> None:
    """Without any patching, the Python and cocotb parts are found."""
    fp = dv_toolchain.toolchain_fingerprint("verilator")
    assert fp["python"] == platform.python_version()
    assert fp["cocotb"] != "unavailable"
    assert fp["cocotb_dir"] != "unavailable"
    assert Path(fp["cocotb_dir"]).name == "cocotb"


def test_fingerprint_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """The simulator is queried once per process, not on every call."""
    calls: list[object] = []

    def fake(cmd: object) -> str:
        calls.append(cmd)
        return "Fake 1.0"

    monkeypatch.setattr(dv_toolchain, "first_line", fake)
    dv_toolchain.toolchain_fingerprint("verilator")
    dv_toolchain.toolchain_fingerprint("verilator")
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("stdout", "stderr", "expected"),
    [
        ("Line one\nLine two\n", "", "Line one"),
        ("", "Version on stderr\nmore\n", "Version on stderr"),
        ("  padded  \n", "", "padded"),
        ("", "", "unavailable"),
    ],
)
def test_first_line(
    monkeypatch: pytest.MonkeyPatch, stdout: str, stderr: str, expected: str
) -> None:
    """Uses the first line of stdout, falling back to stderr."""
    proc = Mock(stdout=stdout, stderr=stderr)
    monkeypatch.setattr(dv_toolchain.subprocess, "run", lambda *_a, **_k: proc)
    assert dv_toolchain.first_line(["tool", "--version"]) == expected


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(),
        dv_toolchain.subprocess.TimeoutExpired("tool", 1),
    ],
    ids=["missing tool", "hung tool"],
)
def test_first_line_when_tool_cannot_run(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """A missing or hung tool must not crash dv; it is reported as unavailable."""

    def fail(*_a: object, **_k: object) -> None:
        raise error

    monkeypatch.setattr(dv_toolchain.subprocess, "run", fail)
    assert dv_toolchain.first_line(["nope"]) == "unavailable"
