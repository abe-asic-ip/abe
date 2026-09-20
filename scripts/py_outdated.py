# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: scripts/py_outdated.py

"""Show which installed Python packages are behind the latest stable release.

For every package installed in the abe virtual environment, look up the latest
stable release on PyPI (pre-releases and yanked releases are ignored). If it is
newer than what is installed, say why it is not installed:

- upgrade candidate: nothing blocks it (try it, verify, then `make py-lock`)
- held back: the Python version, or another installed package's requirement,
  excludes it (nothing to do until that package moves)
- needs a range change: the range in pyproject.toml excludes it (widen the range
  if you want it)

Packages whose installed version differs from constraints.txt are reported as
drift. Run it with the virtual environment's Python (`make py-outdated`).

Usage: .venv/bin/python scripts/py_outdated.py [--all] [--jobs N]
       (or: make py-outdated)
  --all     also list packages that are up to date
  --jobs N  number of parallel PyPI lookups (default: 8)
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import platform
import re
import sys
import tomllib
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

REPO = Path(__file__).resolve().parent.parent
DESCRIPTION = (__doc__ or "").split("\n", maxsplit=1)[0]

OK = "ok"
RANGE = "range"
CANDIDATE = "candidate"
HELD = "held"
UNKNOWN = "unknown"
_ORDER = {RANGE: 0, CANDIDATE: 1, HELD: 2, UNKNOWN: 3, OK: 4}

Parents = dict[str, list[tuple[str, SpecifierSet]]]
Lookups = dict[str, tuple["Latest | None", "str | None"]]


@dataclass(frozen=True)
class Latest:
    """The newest stable release of a package on PyPI."""

    version: Version
    requires_python: str | None


@dataclass(frozen=True)
class Row:  # pylint: disable=too-many-instance-attributes
    """One package's comparison result."""

    name: str
    installed: Version
    latest: Version | None
    direct: bool
    status: str
    why: str


def norm(name: str) -> str:
    """Normalize a package name the way PyPI does."""
    return re.sub(r"[-_.]+", "-", name).lower()


def latest_stable(releases: dict[str, list[dict[str, Any]]]) -> Latest | None:
    """Pick the newest release that is not a pre-release, dev or yanked one."""
    best: Latest | None = None
    for text, files in releases.items():
        try:
            version = Version(text)
        except InvalidVersion:
            continue
        if version.is_prerelease or version.is_devrelease:
            continue
        live = [f for f in files if not f.get("yanked")]
        if not live:
            continue
        if best is None or version > best.version:
            best = Latest(version, live[0].get("requires_python"))
    return best


def declared_ranges(project: dict[str, Any]) -> dict[str, SpecifierSet]:
    """Read the version ranges declared in pyproject.toml (all extras)."""
    texts = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        texts += extra
    ranges: dict[str, SpecifierSet] = {}
    for text in texts:
        req = Requirement(text)
        name = norm(req.name)
        ranges[name] = ranges.get(name, SpecifierSet()) & req.specifier
    return ranges


def read_constraints(text: str) -> dict[str, Version]:
    """Parse constraints.txt lines of the form name==version."""
    pinned: dict[str, Version] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        pinned[norm(name.strip())] = Version(version.strip())
    return pinned


def installed_state() -> tuple[dict[str, Version], Parents]:
    """Installed versions, and who requires which version range of what."""
    versions: dict[str, Version] = {}
    parents: Parents = {}
    for dist in md.distributions():
        name = norm(dist.metadata["Name"])
        try:
            versions[name] = Version(dist.version)
        except InvalidVersion:
            continue
        if name == "abe":
            continue  # abe's own ranges come from pyproject.toml
        for text in dist.requires or []:
            try:
                req = Requirement(text)
            except InvalidRequirement:
                continue
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            if str(req.specifier):
                parents.setdefault(norm(req.name), []).append((name, req.specifier))
    versions.pop("abe", None)
    return versions, parents


def fetch_latest(name: str) -> Latest | None:
    """Look up the latest stable release of a package on PyPI."""
    url = f"https://pypi.org/pypi/{name}/json"
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.load(resp)
    return latest_stable(data["releases"])


def lookup_all(
    names: Iterable[str],
    fetch: Callable[[str], Latest | None] = fetch_latest,
    jobs: int = 8,
) -> Lookups:
    """Look up every package; a failure is recorded, not raised."""

    def one(name: str) -> tuple[Latest | None, str | None]:
        try:
            return fetch(name), None
        except (OSError, ValueError, KeyError) as exc:
            return None, f"{type(exc).__name__}: {exc}"

    ordered = sorted(names)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return dict(zip(ordered, pool.map(one, ordered)))


def _blockers(
    name: str, latest: Latest, parents: Parents, python_version: Version
) -> list[str]:
    """Why the latest release cannot be installed in this environment."""
    reasons: list[str] = []
    if latest.requires_python and not SpecifierSet(latest.requires_python).contains(
        str(python_version)
    ):
        reasons.append(f"latest needs Python {latest.requires_python}")
    for parent, spec in parents.get(name, []):
        if not spec.contains(latest.version):
            reasons.append(f"{parent} requires {name}{spec}")
    return reasons


def analyze(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    installed: dict[str, Version],
    lookups: Lookups,
    parents: Parents,
    declared: dict[str, SpecifierSet],
    python_version: Version,
) -> list[Row]:
    """Classify each installed package against its latest stable release."""
    rows: list[Row] = []
    for name, have in sorted(installed.items()):
        latest, error = lookups.get(name, (None, "not looked up"))
        direct = name in declared
        if error is not None or latest is None:
            why = f"lookup failed: {error}" if error else "no stable release found"
            rows.append(Row(name, have, None, direct, UNKNOWN, why))
            continue
        if latest.version <= have:
            rows.append(Row(name, have, latest.version, direct, OK, ""))
            continue

        reasons = _blockers(name, latest, parents, python_version)
        if reasons:
            rows.append(
                Row(name, have, latest.version, direct, HELD, "; ".join(reasons))
            )
            continue

        rng = declared.get(name)
        if rng is not None and not rng.contains(latest.version):
            why = f"pyproject.toml range {rng} excludes it"
            rows.append(Row(name, have, latest.version, direct, RANGE, why))
        else:
            rows.append(Row(name, have, latest.version, direct, CANDIDATE, ""))
    return rows


def drift(
    installed: dict[str, Version], pinned: dict[str, Version]
) -> list[tuple[str, str, str]]:
    """Packages whose installed version differs from (or is missing in) the lock."""
    out: list[tuple[str, str, str]] = []
    for name, have in sorted(installed.items()):
        if name == "pip":
            continue  # pip is upgraded separately, not pinned
        want = pinned.get(name)
        if want != have:
            out.append((name, str(have), str(want) if want else "not in file"))
    return out


_STATUS_TEXT = {
    OK: "up to date",
    CANDIDATE: "upgrade candidate",
    HELD: "held back",
    RANGE: "needs a range change",
    UNKNOWN: "unknown",
}


def format_report(
    rows: list[Row], drifted: list[tuple[str, str, str]], show_all: bool = False
) -> str:
    """Render the comparison as text."""
    shown = [r for r in rows if show_all or r.status != OK]
    shown.sort(key=lambda r: (_ORDER[r.status], not r.direct, r.name))
    lines = [
        f"Python packages checked against PyPI's latest stable release: {len(rows)}"
    ]
    if shown:
        table = [("Package", "Installed", "Latest", "Kind", "Status")]
        for r in shown:
            status = _STATUS_TEXT[r.status] + (f": {r.why}" if r.why else "")
            table.append(
                (
                    r.name,
                    str(r.installed),
                    str(r.latest) if r.latest else "?",
                    "direct" if r.direct else "indirect",
                    status,
                )
            )
        widths = [max(len(row[i]) for row in table) for i in range(4)]
        lines.append("")
        for row in table:
            cells = [row[i].ljust(widths[i]) for i in range(4)] + [row[4]]
            lines.append("  " + "  ".join(cells))
    counts = {s: sum(1 for r in rows if r.status == s) for s in _STATUS_TEXT}
    lines += [
        "",
        f"Summary: {counts[OK]} up to date, {counts[CANDIDATE]} upgrade candidates, "
        f"{counts[HELD]} held back, {counts[RANGE]} need a range change, "
        f"{counts[UNKNOWN]} unknown.",
    ]
    if counts[CANDIDATE] or counts[RANGE]:
        lines.append(
            "To upgrade: see 'How do I upgrade a package?' in docs/python_dev.md."
        )
    if drifted:
        lines += ["", f"Drift: {len(drifted)} package(s) differ from constraints.txt:"]
        lines += [
            f"  {n}: installed {i}, constraints.txt has {w}" for n, i, w in drifted
        ]
        lines.append("If this environment is verified, run `make py-lock`.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Compare the installed packages with PyPI and print the report."""
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--all", action="store_true", help="also list up-to-date packages")
    ap.add_argument("--jobs", type=int, default=8, help="parallel PyPI lookups")
    args = ap.parse_args(argv)

    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    declared = declared_ranges(project["project"])
    lock = REPO / "constraints.txt"
    pinned = read_constraints(lock.read_text(encoding="utf-8")) if lock.exists() else {}

    installed, parents = installed_state()
    lookups = lookup_all(installed, jobs=args.jobs)
    if all(err for _, err in lookups.values()):
        print(
            "Could not reach PyPI (all lookups failed). Are you online?",
            file=sys.stderr,
        )
        return 2

    rows = analyze(
        installed, lookups, parents, declared, Version(platform.python_version())
    )
    drifted = drift(installed, pinned) if pinned else []
    print(format_report(rows, drifted, show_all=args.all))
    return 0


if __name__ == "__main__":
    sys.exit(main())
