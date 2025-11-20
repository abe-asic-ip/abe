# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/dv_report.py

"""Scan test output directories and generate copy-pasteable test reports.

This module scans test run directories for manifest.json files created by dv.py
and generates a comprehensive report of test results. The report categorizes
results into expected passes, expected failures, unexpected passes, and
unexpected failures.

Each manifest.json contains:
- "status": Test result ("PASS" or "FAIL")
- "expect": Expected result ("PASS" or "FAIL")
- "replay_cmd": Copy-pasteable command to rerun the test

The report helps identify:
- Tests that passed as expected (green)
- Tests that failed as expected (green, for negative tests)
- Tests that unexpectedly passed (red, possible test issues)
- Tests that unexpectedly failed (red, regressions)

Usage:
    dv-report                    # Scan default output directory
    dv-report --outdir=<outdir>  # Scan custom output directory

Example output:
    PASS (EXPECTED): dv --design=foo --test=bar --seeds 42
    FAIL (UNEXPECTED): dv --design=foo --test=baz --seeds 100
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from abe import utils

DEFAULT_OUT_DIR = "out_dv"
DEFAULT_TESTS_SUBDIR = "tests"


@dataclass(frozen=True)
class TestRun:
    """A single test run with its result."""

    path: Path
    status: str  # PASS | FAIL
    expect: str  # PASS | FAIL
    replay_cmd: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for report generator.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Parsed argument namespace with output directory setting.
    """
    ap = argparse.ArgumentParser(
        description="RAD DV report generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--outdir", default=DEFAULT_OUT_DIR, help="output directory")
    return ap.parse_args(argv)


def collect(tests_root: Path) -> list[TestRun]:
    """Collect all test run information from manifest files.

    Recursively searches for manifest.json files in the test directory tree
    and parses them into TestRun objects.

    Args:
        tests_root: Root directory containing test subdirectories.

    Returns:
        List of TestRun objects sorted by path for deterministic ordering.
    """
    if not tests_root.is_dir():
        print(
            f"\n[dv_report] No directory found at {tests_root}",
            file=sys.stderr,
        )
        return []
    print(f"\n[dv_report] Scanning for test manifests in {tests_root}")
    runs: list[TestRun] = []
    for d in _find_manifest_dirs(tests_root):
        tr = _load_run(d)
        if tr is not None:
            runs.append(tr)
    # Sort by path for determinism
    runs.sort(key=lambda r: str(r.path))
    return runs


def _find_manifest_dirs(tests_root: Path) -> list[Path]:
    """Find all directories containing manifest.json files.

    Args:
        tests_root: Root directory to search.

    Returns:
        List of unique directory paths containing manifest.json files.
    """
    dirs: list[Path] = []
    out: list[Path] = []
    seen: set[Path] = set()
    for p in sorted(tests_root.glob("**/manifest.json")):
        dirs.append(p.parent)
    for d in dirs:
        if d not in seen:
            out.append(d)
            seen.add(d)
    return out


def _load_run(run_dir: Path) -> TestRun | None:
    """Load test run information from a manifest.json file.

    Args:
        run_dir: Directory containing the manifest.json file.

    Returns:
        TestRun object if manifest is valid, None if invalid or missing.
    """
    mpath = run_dir / "manifest.json"
    try:
        data = json.loads(mpath.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    status = str(data.get("status", "")).strip().upper()
    expect = str(data.get("expect", "PASS")).strip().upper()
    replay_cmd = str(data.get("replay_cmd", "")).strip()
    if (
        status not in {"PASS", "FAIL"}
        or expect not in {"PASS", "FAIL"}
        or not replay_cmd
    ):
        return None
    return TestRun(path=run_dir, status=status, expect=expect, replay_cmd=replay_cmd)


def print_report(tests_root: Path, runs: Sequence[TestRun]) -> int:
    """Print a formatted report of test results.

    Categorizes test runs by expected/unexpected passes/failures and displays
    them with color coding. Provides summary statistics and overall pass/fail
    status.

    Args:
        tests_root: Root directory that was scanned.
        runs: Sequence of TestRun objects to report on.

    Returns:
        0 if no unexpected outcomes, 1 if there are unexpected passes or failures.
    """
    if not runs:
        print(f"[dv_report] No test manifests found in {tests_root}", file=sys.stderr)
        return 1
    print(f"[dv_report] Results from test manifests in {tests_root}\n")

    xpasses = [r for r in runs if r.status == "PASS" and r.expect == "PASS"]
    xfails = [r for r in runs if r.status == "FAIL" and r.expect == "FAIL"]
    upasses = [r for r in runs if r.status == "PASS" and r.expect == "FAIL"]
    ufails = [r for r in runs if r.status == "FAIL" and r.expect == "PASS"]

    rc = 0 if not (upasses or ufails) else 1

    for r in xpasses:
        print(f"{utils.green('PASS (EXPECTED)')}: {r.replay_cmd}")
    for r in xfails:
        print(f"{utils.green('FAIL (EXPECTED)')}: {r.replay_cmd}")
    for r in upasses:
        print(f"{utils.red('PASS (UNEXPECTED)')}: {r.replay_cmd}")
    for r in ufails:
        print(f"{utils.red('FAIL (UNEXPECTED)')}: {r.replay_cmd}")

    print(f"\n[dv_report] TOTALS: {len(runs)}\n")
    if len(xpasses):
        print(f"{utils.green('PASS (EXPECTED)')}: {len(xpasses)}")
    if len(xfails):
        print(f"{utils.green('FAIL (EXPECTED)')}: {len(xfails)}")
    if len(upasses):
        print(f"{utils.red('PASS (UNEXPECTED)')}: {len(upasses)}")
    if len(ufails):
        print(f"{utils.red('FAIL (UNEXPECTED)')}: {len(ufails)}")

    if rc != 0:
        print(f"\n[dv_report] SUMMARY: {utils.red('FAIL (unexpected outcomes)')}")
    else:
        print(f"\n[dv_report] SUMMARY: {utils.green('PASS (no unexpected outcomes)')}")

    return rc


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point for test report generation.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        0 if all tests have expected outcomes, non-zero otherwise.
    """
    args = parse_args(argv)
    tests_root = Path(f"{args.outdir}/{DEFAULT_TESTS_SUBDIR}").resolve()
    runs = collect(tests_root)
    return print_report(tests_root, runs)


if __name__ == "__main__":
    raise SystemExit(main())
