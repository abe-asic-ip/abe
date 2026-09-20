# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: scripts/test_py_outdated.py

"""Unit tests for scripts/py_outdated.py.

PyPI is never contacted: lookups are injected and installed packages are faked.

Run with: pytest scripts/test_py_outdated.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version


def _load() -> Any:
    """Import scripts/py_outdated.py, which is not on the package path."""
    path = Path(__file__).resolve().parent / "py_outdated.py"
    spec = importlib.util.spec_from_file_location("py_outdated", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["py_outdated"] = module
    spec.loader.exec_module(module)
    return module


po = _load()
V = Version
PY = V("3.14.7")


def _file(requires_python: str | None = ">=3.9", yanked: bool = False) -> dict:
    """Fake a PyPI release file entry."""
    return {"requires_python": requires_python, "yanked": yanked}


def _rows(
    installed: dict,
    latest: dict,
    parents: dict | None = None,
    declared: dict | None = None,
) -> dict:
    """Run analyze() on simple {name: version} inputs; return rows by name."""
    lookups = {n: (po.Latest(V(v), rp), None) for n, (v, rp) in latest.items()}
    rows = po.analyze(
        {n: V(v) for n, v in installed.items()},
        lookups,
        parents or {},
        declared or {},
        PY,
    )
    return {r.name: r for r in rows}


def test_norm_matches_pypi_rules() -> None:
    """Names are normalized the way PyPI does it."""
    assert po.norm("Foo_Bar.baz") == "foo-bar-baz"
    assert po.norm("PyYAML") == "pyyaml"


def test_latest_stable_skips_prereleases_dev_yanked_and_junk() -> None:
    """Only real, unyanked stable releases count."""
    releases = {
        "1.0": [_file()],
        "1.1": [_file()],
        "2.0rc1": [_file()],  # pre-release
        "2.0.dev3": [_file()],  # dev release
        "1.2": [_file(yanked=True)],  # yanked
        "not-a-version": [_file()],
        "1.3": [],  # no files
    }
    latest = po.latest_stable(releases)
    assert latest is not None
    assert latest.version == V("1.1")


def test_latest_stable_keeps_requires_python() -> None:
    """The latest release's Python requirement is kept."""
    latest = po.latest_stable({"3.0": [_file(">=3.15")]})
    assert latest is not None and latest.requires_python == ">=3.15"


def test_latest_stable_none_when_nothing_stable() -> None:
    """No stable release means no answer."""
    assert po.latest_stable({"1.0rc1": [_file()], "0.9": [_file(yanked=True)]}) is None


def test_declared_ranges_merges_extras_and_normalizes_names() -> None:
    """Ranges from every extra are collected under normalized names."""
    project = {
        "dependencies": ["PyYAML>=6.0.3,<7"],
        "optional-dependencies": {
            "dev": ["black>=26.5,<27"],
            "uarch": ["Pint>=0.26,<0.27"],
        },
    }
    ranges = po.declared_ranges(project)
    assert set(ranges) == {"pyyaml", "black", "pint"}
    assert ranges["pint"].contains(V("0.26.1"))
    assert not ranges["pint"].contains(V("0.27"))


def test_read_constraints_ignores_comments_and_blanks() -> None:
    """constraints.txt parsing skips comments and blank lines."""
    text = "# header\n\nabsl-py==2.5.0\nFoo_Bar==1.0  # trailing\n"
    assert po.read_constraints(text) == {"absl-py": V("2.5.0"), "foo-bar": V("1.0")}


def test_up_to_date() -> None:
    """A package at the latest version is fine."""
    rows = _rows({"a": "1.0"}, {"a": ("1.0", None)})
    assert rows["a"].status == po.OK


def test_installed_newer_than_latest_stable_is_ok() -> None:
    """A newer installed version (e.g. a pre-release) is not flagged."""
    rows = _rows({"a": "2.0"}, {"a": ("1.0", None)})
    assert rows["a"].status == po.OK


def test_upgrade_candidate_when_nothing_blocks() -> None:
    """A newer release that nothing blocks is an upgrade candidate."""
    rows = _rows({"a": "1.0"}, {"a": ("1.1", ">=3.9")})
    assert rows["a"].status == po.CANDIDATE
    assert rows["a"].latest == V("1.1")


def test_held_back_by_python_version() -> None:
    """A release that needs a newer Python is held back."""
    rows = _rows({"a": "1.0"}, {"a": ("2.0", ">=3.15")})
    assert rows["a"].status == po.HELD
    assert "needs Python >=3.15" in rows["a"].why


def test_held_back_by_another_package() -> None:
    """Another installed package's requirement can hold a package back."""
    parents = {"astroid": [("pylint", SpecifierSet("<=4.1.dev0,>=4.0.2"))]}
    rows = _rows({"astroid": "4.0.4"}, {"astroid": ("4.3.1", None)}, parents=parents)
    assert rows["astroid"].status == po.HELD
    assert "pylint requires astroid" in rows["astroid"].why


def test_parent_that_allows_the_latest_does_not_hold_it_back() -> None:
    """A parent whose range allows the latest does not block it."""
    parents = {"a": [("b", SpecifierSet(">=1.0"))]}
    rows = _rows({"a": "1.0"}, {"a": ("1.5", None)}, parents=parents)
    assert rows["a"].status == po.CANDIDATE


def test_range_in_pyproject_excludes_latest() -> None:
    """Our own range excluding the latest is a decision, not a blocker."""
    declared = {"pyuvm": SpecifierSet(">=5.0,<6")}
    rows = _rows({"pyuvm": "5.0.0"}, {"pyuvm": ("6.0.0", None)}, declared=declared)
    assert rows["pyuvm"].status == po.RANGE
    assert "pyproject.toml range" in rows["pyuvm"].why


def test_held_back_wins_over_range() -> None:
    """If another package blocks it, widening our range would not help."""
    declared = {"a": SpecifierSet("<2")}
    parents = {"a": [("b", SpecifierSet("<2"))]}
    rows = _rows({"a": "1.0"}, {"a": ("2.0", None)}, parents=parents, declared=declared)
    assert rows["a"].status == po.HELD


def test_direct_versus_indirect() -> None:
    """Packages declared in pyproject.toml are direct, the rest indirect."""
    rows = _rows(
        {"a": "1.0", "b": "1.0"},
        {"a": ("1.0", None), "b": ("1.0", None)},
        declared={"a": SpecifierSet(">=1")},
    )
    assert rows["a"].direct and not rows["b"].direct


def test_lookup_failure_is_reported_not_raised() -> None:
    """A failed lookup becomes an 'unknown' row."""
    rows = po.analyze({"a": V("1.0")}, {"a": (None, "URLError: offline")}, {}, {}, PY)
    assert rows[0].status == po.UNKNOWN
    assert "offline" in rows[0].why


def test_lookup_all_records_failures_and_results() -> None:
    """One failing lookup does not stop the others."""

    def fetch(name: str) -> Any:
        if name == "bad":
            raise OSError("boom")
        if name == "weird":
            raise KeyError("releases")
        return po.Latest(V("1.0"), None)

    result = po.lookup_all(["good", "bad", "weird"], fetch=fetch, jobs=2)
    assert result["good"][1] is None and result["good"][0] is not None
    assert result["bad"] == (None, "OSError: boom")
    assert result["weird"][0] is None and "KeyError" in str(result["weird"][1])


def test_drift_reports_changed_and_missing_but_not_pip() -> None:
    """Differences from constraints.txt are reported, except pip."""
    installed = {"a": V("1.1"), "b": V("2.0"), "c": V("3.0"), "pip": V("26.2")}
    pinned = {"a": V("1.0"), "b": V("2.0")}
    assert po.drift(installed, pinned) == [
        ("a", "1.1", "1.0"),
        ("c", "3.0", "not in file"),
    ]


def test_report_lists_only_problems_by_default_and_orders_them() -> None:
    """By default only problems are listed, most actionable first."""
    rows = _rows(
        {"ok": "1.0", "cand": "1.0", "held": "1.0", "rng": "1.0"},
        {
            "ok": ("1.0", None),
            "cand": ("1.1", None),
            "held": ("2.0", ">=3.15"),
            "rng": ("3.0", None),
        },
        declared={"rng": SpecifierSet("<2")},
    )
    text = po.format_report(list(rows.values()), [])
    assert "ok " not in text.split("Summary")[0].replace("Python packages", "")
    order = [text.index(n) for n in ("rng", "cand", "held")]
    assert order == sorted(order)  # range change, then candidate, then held back
    assert (
        "1 up to date, 1 upgrade candidates, 1 held back, 1 need a range change" in text
    )
    assert "docs/python_dev.md" in text


def test_report_all_includes_up_to_date() -> None:
    """--all also lists packages that are up to date."""
    rows = _rows({"ok": "1.0"}, {"ok": ("1.0", None)})
    shown = po.format_report(list(rows.values()), [], show_all=True)
    hidden = po.format_report(list(rows.values()), [])
    assert "  ok " in shown
    assert "  ok " not in hidden


def test_report_mentions_drift_and_py_lock() -> None:
    """Drift is reported with a pointer to make py-lock."""
    rows = _rows({"a": "1.0"}, {"a": ("1.0", None)})
    text = po.format_report(list(rows.values()), [("a", "1.0", "0.9")])
    assert "Drift: 1 package(s)" in text
    assert "make py-lock" in text


@pytest.mark.parametrize("failing", [True, False])
def test_main_exit_code_when_pypi_unreachable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failing: bool
) -> None:
    """main() exits 2 only if every lookup failed."""
    monkeypatch.setattr(po, "installed_state", lambda: ({"a": V("1.0")}, {}))
    if failing:
        monkeypatch.setattr(
            po, "lookup_all", lambda names, **_k: {"a": (None, "OSError: offline")}
        )
    else:
        monkeypatch.setattr(
            po,
            "lookup_all",
            lambda names, **_k: {"a": (po.Latest(V("1.0"), None), None)},
        )
    code = po.main([])
    out = capsys.readouterr()
    assert code == (2 if failing else 0)
    assert ("Could not reach PyPI" in out.err) == failing
