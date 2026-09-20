# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: scripts/check_header_years.py

"""Check (and optionally fix) the copyright year in the SPDX header of changed files.

ABE keeps the year in the SPDX copyright header (the `SPDX-FileCopyrightText`
line) current for every file that is changed. By default this checks the files
that differ from the branch's upstream (committed but not pushed, staged and
unstaged changes) plus new untracked files. `--all` checks every tracked file
instead.

Files with no SPDX-FileCopyrightText line in their first lines (binary files,
symlinks, files licensed through REUSE.toml) are skipped.

Usage: .venv/bin/python scripts/check_header_years.py [--fix] [--all]
       [--year YEAR] [--base REF]   (or: make check-header-years)
  --fix        rewrite the year in place instead of only reporting
  --all        check every tracked file, not just the changed ones
  --year YEAR  the year expected (default: the current year)
  --base REF   compare against REF instead of the branch's upstream

Exit status: 1 if any file is out of date and --fix was not given, else 0.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DESCRIPTION = (__doc__ or "").split("\n", maxsplit=1)[0]
HEADER_LINES = 15
# The pattern quotes the header tag as data, so keep it out of reuse's scan.
# REUSE-IgnoreStart
_YEAR = re.compile(r"(SPDX-FileCopyrightText:\s*)(\d{4})(?:(\s*[-–]\s*)(\d{4}))?")
# REUSE-IgnoreEnd

OK = "ok"
STALE = "stale"
NO_HEADER = "no header"


@dataclass(frozen=True)
class Result:
    """The outcome of checking one file."""

    path: str
    status: str
    found: int | None = None


def header_year(text: str) -> int | None:
    """Return the latest year in the SPDX copyright line, or None if absent."""
    for line in text.split("\n")[:HEADER_LINES]:
        match = _YEAR.search(line)
        if match:
            return int(match.group(4) or match.group(2))
    return None


def fix_year(text: str, year: int) -> str | None:
    """Return text with the header year set to year, or None if no change is needed.

    A single year becomes the new year. A range keeps its first year and gets a
    new last year. Only the header line changes; line endings are preserved.
    """
    lines = text.split("\n")
    for index, line in enumerate(lines[:HEADER_LINES]):
        match = _YEAR.search(line)
        if not match:
            continue
        if int(match.group(4) or match.group(2)) >= year:
            return None
        if match.group(4):
            new = f"{match.group(1)}{match.group(2)}{match.group(3)}{year}"
        else:
            new = f"{match.group(1)}{year}"
        lines[index] = line[: match.start()] + new + line[match.end() :]
        return "\n".join(lines)
    return None


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _upstream(repo: Path) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "@{upstream}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def changed_files(repo: Path, base: str | None = None) -> list[str]:
    """Files that differ from base (default: the upstream, else HEAD), plus new ones."""
    ref = base or _upstream(repo) or "HEAD"
    tracked = _git(repo, "diff", "--name-only", "-z", "--diff-filter=ACMRT", ref)
    untracked = _git(repo, "ls-files", "-z", "--others", "--exclude-standard")
    return sorted({f for f in (tracked + untracked).split("\0") if f})


def tracked_files(repo: Path) -> list[str]:
    """Every file tracked by git."""
    return sorted(f for f in _git(repo, "ls-files", "-z").split("\0") if f)


def _read(path: Path) -> str | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        return path.read_bytes().decode("utf-8")
    except OSError, UnicodeDecodeError:
        return None


def check_files(repo: Path, files: list[str], year: int) -> list[Result]:
    """Compare each file's header year with the expected year."""
    results: list[Result] = []
    for name in files:
        text = _read(repo / name)
        found = header_year(text) if text is not None else None
        if found is None:
            results.append(Result(name, NO_HEADER))
        elif found < year:
            results.append(Result(name, STALE, found))
        else:
            results.append(Result(name, OK, found))
    return results


def fix_files(repo: Path, results: list[Result], year: int) -> list[str]:
    """Rewrite the header year of every stale file; return the files changed."""
    fixed: list[str] = []
    for result in results:
        if result.status != STALE:
            continue
        path = repo / result.path
        text = _read(path)
        new = fix_year(text, year) if text is not None else None
        if new is not None:
            path.write_bytes(new.encode("utf-8"))
            fixed.append(result.path)
    return fixed


def format_report(results: list[Result], year: int, scope: str) -> str:
    """Render the check result as text."""
    stale = [r for r in results if r.status == STALE]
    skipped = sum(1 for r in results if r.status == NO_HEADER)
    checked = len(results) - skipped
    lines = [
        f"Header year check for {year}: {checked} {scope} file(s) checked"
        + (f", {skipped} without an SPDX header skipped." if skipped else ".")
    ]
    if not results:
        lines[0] = f"Header year check for {year}: no {scope} files."
    elif not stale:
        lines.append(f"All {checked} have {year} in their header.")
    else:
        lines.append(f"{len(stale)} out of date (year in header -> expected):")
        width = max(len(r.path) for r in stale)
        lines += [f"  {r.path.ljust(width)}  {r.found} -> {year}" for r in stale]
        lines.append("Run `make fix-header-years` to update them.")
    return "\n".join(lines)


def main(argv: list[str] | None = None, repo: Path = REPO) -> int:
    """Check (or fix) header years; return the exit status."""
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--fix", action="store_true", help="update the years in place")
    ap.add_argument("--all", action="store_true", help="check every tracked file")
    ap.add_argument("--year", type=int, default=datetime.date.today().year)
    ap.add_argument("--base", help="compare against this ref instead of the upstream")
    args = ap.parse_args(argv)

    try:
        files = tracked_files(repo) if args.all else changed_files(repo, args.base)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: could not list files with git: {exc}", file=sys.stderr)
        return 2
    scope = "tracked" if args.all else "changed"
    results = check_files(repo, files, args.year)
    print(format_report(results, args.year, scope))

    if args.fix:
        fixed = fix_files(repo, results, args.year)
        if fixed:
            print(f"Updated {len(fixed)} file(s) to {args.year}.")
        return 0
    return 1 if any(r.status == STALE for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
