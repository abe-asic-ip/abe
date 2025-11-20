# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/dv_regress_all.py

"""Find and run all dv_regress.yaml files in the repository.

This module provides a convenient way to run all regression suites defined
across the entire repository. It recursively searches for dv_regress.yaml files
and executes each one using the dv-regress command.

Features:
- Recursive search from specified root directories
- Filters out common non-test directories (.git, .venv, etc.)
- All regressions share the same output directory
- Colored summary report of overall pass/fail status

Usage:
    dv-regress-all [--roots DIR1 DIR2 ...] [--outdir=out_dv]

Example:
    dv-regress-all                     # Search from current directory
    dv-regress-all --roots src/abe/rad # Search only in specific directory
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Sequence

from abe import utils

DEFAULT_OUT_DIR = "out_dv"

_IGNORE_DIRS = {
    ".git",
    ".venv",
    "site",
    "__pycache__",
    "out_synth",
    "formal",
    "out_dv",
    "waves",
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for running all regressions.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Parsed argument namespace with root directories and output directory.
    """
    ap = argparse.ArgumentParser(
        description="Run all regressions in the repo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "--roots",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="roots to scan (default: .)",
    )
    ap.add_argument("--outdir", default=DEFAULT_OUT_DIR, help="output directory")
    return ap.parse_args(argv)


def _walk_find(root: Path, filename: str) -> Iterator[Path]:
    """Recursively search for files with the given name.

    Walks the directory tree, pruning common non-test directories to
    improve search performance.

    Args:
        root: Root directory to start the search.
        filename: Filename to search for.

    Yields:
        Paths to matching files.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # prune in-place
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        if filename in filenames:
            yield Path(dirpath, filename)


def _find_yamls(roots: list[Path]) -> list[Path]:
    """Find all dv_regress.yaml files under the given root directories.

    Args:
        roots: List of root directories to search.

    Returns:
        Sorted list of unique absolute paths to dv_regress.yaml files.

    Raises:
        SystemExit: If a root directory doesn't exist or isn't a directory.
    """
    seen: set[Path] = set()
    for root in roots:
        if not root.exists() or not root.is_dir():
            print(
                f"[dv_regress_all] Error: root {root} does not exist"
                f" or is not a directory.",
                file=sys.stderr,
            )
            sys.exit(2)
        for p in _walk_find(root, "dv_regress.yaml"):
            if p.is_file():
                seen.add(p.resolve())
    return sorted(seen)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point for running all repository regressions.

    Searches for dv_regress.yaml files, executes each regression, and reports
    overall pass/fail status.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        0 if all regressions pass, non-zero if any fail.
    """
    args = parse_args(argv)
    yamls = _find_yamls([r.resolve() for r in args.roots])

    if not yamls:
        print(
            "[dv_regress_all] No dv_regress.yaml files found under:",
            *[str(r) for r in args.roots],
            file=sys.stderr,
        )
        return 2
    print(
        f"[dv_regress_all] Running {len(yamls)}"
        f" regressions with outdir={args.outdir}:\n"
    )
    for y in yamls:
        print(f"{str(y)}")

    overall_rc = 0
    for y in yamls:
        print(f"\n[dv_regress_all] Starting regression {y}")
        cmd = [
            "dv-regress",
            "--file",
            str(y),
            "--outdir",
            args.outdir,
        ]
        rc = subprocess.run(cmd, check=False).returncode
        if rc != 0:
            overall_rc = 1

    print(f"\n[dv_regress_all] Completed regressions: {len(yamls)}")
    rep = f"dv-report --outdir={args.outdir}"
    print(
        f"\n[dv_regress_all] To see a detailed report of all tests: {utils.yellow(rep)}"
    )

    if overall_rc:
        print(f"\n[dv_regress_all] SUMMARY: {utils.red('FAIL')}")
        return 1
    print(f"\n[dv_regress_all] SUMMARY: {utils.green('PASS')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
