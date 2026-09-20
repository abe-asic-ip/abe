# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: scripts/test_check_header_years.py

# These tests quote SPDX header text as data, so keep it out of reuse's scan.
# REUSE-IgnoreStart

"""Unit tests for scripts/check_header_years.py.

The git-related tests use a real temporary repository, so which files count as
"changed" is tested against actual git behavior.

Run with: pytest scripts/test_check_header_years.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _load() -> Any:
    """Import scripts/check_header_years.py, which is not on the package path."""
    path = Path(__file__).resolve().parent / "check_header_years.py"
    spec = importlib.util.spec_from_file_location("check_header_years", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_header_years"] = module
    spec.loader.exec_module(module)
    return module


chy = _load()

OLD = (
    "# SPDX-FileCopyrightText: 2025 Hugh Walsh\n"
    "#\n"
    "# SPDX-License-Identifier: MIT\n"
    "\n"
    "body 2025\n"
)
NEW = OLD.replace("2025 Hugh", "2026 Hugh")


def _git(repo: Path, *args: str) -> str:
    """Run git in the temporary repository."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout


@pytest.fixture(name="repo")
def _repo(tmp_path: Path) -> Path:
    """A git repository with two committed files (one old header, one new)."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.py").write_text(OLD)
    (tmp_path / "b.py").write_text(OLD)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# SPDX-FileCopyrightText: 2025 Hugh Walsh\n", 2025),
        ("<!--\nSPDX-FileCopyrightText: 2026 Hugh Walsh\n-->\n", 2026),
        ("# SPDX-FileCopyrightText: 2024-2026 Hugh Walsh\n", 2026),
        ("# SPDX-FileCopyrightText: 2024 – 2025 Hugh\n", 2025),
        ("no header here\n", None),
        ("\n" * 20 + "# SPDX-FileCopyrightText: 2025 Hugh\n", None),  # too far down
        ("", None),
    ],
)
def test_header_year(text: str, expected: int | None) -> None:
    """The latest year in the first header lines is found."""
    assert chy.header_year(text) == expected


def test_fix_year_changes_only_the_header_line() -> None:
    """A single year is replaced; body text mentioning the year is untouched."""
    fixed = chy.fix_year(OLD, 2026)
    assert fixed == NEW
    assert "body 2025" in fixed


def test_fix_year_extends_a_range() -> None:
    """A range keeps its first year and gets a new last year."""
    text = "# SPDX-FileCopyrightText: 2024-2025 Hugh\n"
    assert chy.fix_year(text, 2026) == "# SPDX-FileCopyrightText: 2024-2026 Hugh\n"


@pytest.mark.parametrize(
    "text", [NEW, "# SPDX-FileCopyrightText: 2027 Hugh\n", "plain\n"]
)
def test_fix_year_leaves_current_future_and_headerless_alone(text: str) -> None:
    """Nothing to do if the year is current or later, or there is no header."""
    assert chy.fix_year(text, 2026) is None


def test_fix_year_preserves_crlf_line_endings() -> None:
    """Windows line endings survive the rewrite."""
    text = "# SPDX-FileCopyrightText: 2025 Hugh\r\n# x\r\n"
    assert chy.fix_year(text, 2026) == "# SPDX-FileCopyrightText: 2026 Hugh\r\n# x\r\n"


def test_check_files_statuses(tmp_path: Path) -> None:
    """Old, current, future, headerless, binary and symlinked files."""
    (tmp_path / "old.txt").write_text(OLD)
    (tmp_path / "new.txt").write_text(NEW)
    (tmp_path / "future.txt").write_text(OLD.replace("2025", "2027"))
    (tmp_path / "none.txt").write_text("nothing\n")
    (tmp_path / "bin.dat").write_bytes(b"\xff\xfe\x00\x01")
    (tmp_path / "link.txt").symlink_to("old.txt")
    names = ["old.txt", "new.txt", "future.txt", "none.txt", "bin.dat", "link.txt"]

    got = {r.path: r.status for r in chy.check_files(tmp_path, names, 2026)}

    assert got == {
        "old.txt": chy.STALE,
        "new.txt": chy.OK,
        "future.txt": chy.OK,
        "none.txt": chy.NO_HEADER,
        "bin.dat": chy.NO_HEADER,
        "link.txt": chy.NO_HEADER,
    }


def test_changed_files_without_upstream_uses_head(repo: Path) -> None:
    """Modified, staged and untracked files count; untouched ones do not."""
    (repo / "a.py").write_text(OLD + "edit\n")  # unstaged change
    (repo / "c.py").write_text(OLD)  # untracked
    (repo / "d.py").write_text(OLD)  # staged new file
    _git(repo, "add", "d.py")

    assert chy.changed_files(repo) == ["a.py", "c.py", "d.py"]


def test_changed_files_against_a_base_includes_commits_since(repo: Path) -> None:
    """Committed-but-not-pushed work counts when compared with the base."""
    _git(repo, "tag", "base")
    (repo / "b.py").write_text(OLD + "edit\n")
    _git(repo, "commit", "-q", "-am", "change b")

    assert chy.changed_files(repo, "base") == ["b.py"]
    assert chy.changed_files(repo) == []  # nothing differs from HEAD


def test_changed_files_uses_the_upstream_when_there_is_one(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """With an upstream, unpushed commits are included."""
    remote = tmp_path_factory.mktemp("remote")
    _git(remote, "init", "-q", "--bare", "-b", "main")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    (repo / "b.py").write_text(OLD + "edit\n")
    _git(repo, "commit", "-q", "-am", "unpushed change")

    assert chy.changed_files(repo) == ["b.py"]


def test_tracked_files(repo: Path) -> None:
    """--all looks at every tracked file, and only tracked ones."""
    (repo / "untracked.py").write_text(OLD)
    assert chy.tracked_files(repo) == ["a.py", "b.py"]


def test_main_reports_and_fails_on_stale_files(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit status 1 and a list of what to fix."""
    (repo / "a.py").write_text(OLD + "edit\n")

    code = chy.main(["--year", "2026"], repo=repo)

    out = capsys.readouterr().out
    assert code == 1
    assert "a.py" in out and "2025 -> 2026" in out
    assert "make fix-header-years" in out


def test_main_passes_when_changed_files_are_current(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit status 0 when every changed file has the current year."""
    (repo / "a.py").write_text(NEW)

    assert chy.main(["--year", "2026"], repo=repo) == 0
    assert "All 1 have 2026" in capsys.readouterr().out


def test_main_with_nothing_changed(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clean tree is fine."""
    assert chy.main(["--year", "2026"], repo=repo) == 0
    assert "no changed files" in capsys.readouterr().out


def test_main_fix_updates_only_changed_files(repo: Path) -> None:
    """--fix rewrites the header of changed files and leaves the rest alone."""
    (repo / "a.py").write_text(OLD + "edit\n")

    assert chy.main(["--fix", "--year", "2026"], repo=repo) == 0

    assert "2026 Hugh" in (repo / "a.py").read_text()
    assert "body 2025" in (repo / "a.py").read_text()
    assert (repo / "b.py").read_text() == OLD  # unchanged file not touched
    assert chy.main(["--year", "2026"], repo=repo) == 0  # and now it passes


def test_main_all_checks_every_tracked_file(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--all includes files that were not changed."""
    code = chy.main(["--all", "--year", "2026"], repo=repo)
    out = capsys.readouterr().out
    assert code == 1
    assert "2 out of date" in out


def test_main_outside_a_git_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clear error, exit status 2."""
    assert chy.main([], repo=tmp_path) == 2
    assert "could not list files with git" in capsys.readouterr().err


# REUSE-IgnoreEnd
