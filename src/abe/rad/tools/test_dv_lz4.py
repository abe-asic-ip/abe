# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/test_dv_lz4.py

"""Unit tests for dv's lz4 detection (Verilator FST waveform dependency).

The compiler probe is monkeypatched so these tests do not depend on the
machine's compiler or on lz4 being installed.

Run with: pytest src/abe/rad/tools/test_dv_lz4.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest

from abe.rad.tools import dv

BREW_PREFIX = Path("/fake/brew/opt/lz4")
MACPORTS_PREFIX = Path("/opt/local")
DEFAULT_PREFIXES = [
    Path(p) for p in dv._LZ4_FALLBACK_PREFIXES  # pylint: disable=protected-access
]


def _fail_if_probed(*_args: object, **_kwargs: object) -> bool:
    raise AssertionError("compiler probe should not run")


@pytest.fixture(autouse=True)
def _fake_compiler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend a C++ compiler exists so detection proceeds to the probe."""
    monkeypatch.delenv("CXX", raising=False)
    monkeypatch.delenv(dv.LZ4_PREFIX_ENV, raising=False)
    monkeypatch.setattr(dv.shutil, "which", lambda name: f"/usr/bin/{name}")


@pytest.mark.parametrize(
    ("sim", "waves", "waves_fmt"),
    [
        ("icarus", True, "fst"),
        ("verilator", False, "fst"),
        ("verilator", True, "vcd"),
    ],
)
def test_no_lz4_needed(
    monkeypatch: pytest.MonkeyPatch, sim: str, waves: bool, waves_fmt: str
) -> None:
    """lz4 is only required for Verilator with FST waves."""
    monkeypatch.setattr(dv, "_cxx_links_lz4", _fail_if_probed)
    assert not dv.verilator_lz4_build_args(sim, waves, waves_fmt)


def test_default_search_path_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the compiler already finds lz4, add no flags."""
    monkeypatch.setattr(dv, "_cxx_links_lz4", lambda _cxx, prefix=None: prefix is None)
    assert not dv.verilator_lz4_build_args("verilator", True, "fst")


def test_missing_compiler_defers_to_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a compiler, don't claim lz4 is missing; the build will report it."""
    monkeypatch.setattr(dv.shutil, "which", lambda _name: None)
    monkeypatch.setattr(dv, "_cxx_links_lz4", _fail_if_probed)
    assert not dv.verilator_lz4_build_args("verilator", True, "fst")


def test_falls_back_to_first_working_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prefixes are tried in order; the first that links wins."""
    tried: list[Path | None] = []

    def probe(_cxx: object, prefix: Path | None = None) -> bool:
        tried.append(prefix)
        return prefix == MACPORTS_PREFIX

    monkeypatch.setattr(dv, "_cxx_links_lz4", probe)
    monkeypatch.setattr(
        dv,
        "_lz4_candidate_prefixes",
        lambda: [BREW_PREFIX, MACPORTS_PREFIX, Path("/never/reached")],
    )

    args = dv.verilator_lz4_build_args("verilator", True, "fst")

    assert args == [
        "-CFLAGS",
        f"-I{MACPORTS_PREFIX}/include",
        "-LDFLAGS",
        f"-L{MACPORTS_PREFIX}/lib",
    ]
    assert tried == [None, BREW_PREFIX, MACPORTS_PREFIX]


def test_missing_lz4_stops_with_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When nothing works, exit with install hints and the VCD escape hatch."""
    monkeypatch.setattr(dv, "_cxx_links_lz4", lambda _cxx, prefix=None: False)
    monkeypatch.setattr(dv, "_lz4_candidate_prefixes", lambda: [BREW_PREFIX])

    with pytest.raises(SystemExit) as exc:
        dv.verilator_lz4_build_args("verilator", True, "fst")

    msg = str(exc.value)
    assert "lz4" in msg
    assert "brew install lz4" in msg
    assert "liblz4-dev" in msg
    assert dv.LZ4_PREFIX_ENV in msg
    assert "--waves_fmt vcd" in msg
    assert str(BREW_PREFIX) in msg


def test_candidate_prefixes_order_env_then_brew_then_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """$LZ4_PREFIX wins, then `brew --prefix lz4`, then well-known locations."""
    monkeypatch.setenv(dv.LZ4_PREFIX_ENV, "/custom/lz4")

    proc = Mock(returncode=0, stdout=f"{BREW_PREFIX}\n")
    monkeypatch.setattr(dv.subprocess, "run", lambda *_a, **_k: proc)

    prefixes = dv._lz4_candidate_prefixes()  # pylint: disable=protected-access

    assert prefixes[0] == Path("/custom/lz4")
    assert prefixes[1] == BREW_PREFIX
    assert prefixes[2:] == DEFAULT_PREFIXES


def test_candidate_prefixes_without_brew(monkeypatch: pytest.MonkeyPatch) -> None:
    """Systems without Homebrew (e.g. Linux) just get the well-known locations."""
    monkeypatch.setattr(dv.shutil, "which", lambda _name: None)

    prefixes = dv._lz4_candidate_prefixes()  # pylint: disable=protected-access

    assert prefixes == DEFAULT_PREFIXES


def test_detected_args_precede_user_args(build_ctx: Callable[..., dict]) -> None:
    """Detected flags follow the defaults; user --build-arg values stay last."""
    ctx = build_ctx(
        detected_build_args=["-CFLAGS", "-I/x/include"],
        user_build_args=["-DUSER_FLAG"],
    )

    cfg = dv._make_build_cfg(ctx)  # pylint: disable=protected-access

    args = cfg.build_args
    assert args.index("--trace-fst") < args.index("-CFLAGS") < args.index("-f")
    assert args[-1] == "-DUSER_FLAG"
