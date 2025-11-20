# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/dv_regress.py

"""RAD DV: YAML-driven regression runner.

This module implements a strict YAML-based regression system where all test
parameters are defined in a YAML configuration file. No parameters are accepted
from the command line except the YAML file path and output directory.

Features:
- Global default arguments applied to all jobs
- Per-job argument overrides (job args take precedence)
- Seed handling delegated to dv.py (supports --nseeds or --seeds)
- Colored pass/fail report with copy-pasteable replay commands

YAML Schema:
    defaults:
      args: ["--sim=verilator", "--waves=0"]  # Optional global defaults

    jobs:
      - name: <job_name>
        args: ["--design=...", "--test=...", "--nseeds=2", ...]
      - name: <job_name2>
        args: "--design=... --test=..."  # Can also be a single string

Usage:
    dv-regress --file=path/to/dv_regress.yaml [--outdir=out_dv]

After running all jobs, prints a report:
  PASS: <cmd>
  FAIL: <cmd>
where <cmd> is a copy-pasteable command to rerun that job.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

from abe import utils

DEFAULT_OUT_DIR = "out_dv"


@dataclass(frozen=True)
class Job:
    """A single regression job."""

    name: str
    args: list[str]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for regression runner.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Parsed argument namespace containing file path and output directory.
    """
    ap = argparse.ArgumentParser(
        description="RAD DV YAML regression (strict, YAML-only)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--file", type=Path, help="Path to dv_regress.yaml")
    ap.add_argument("--outdir", default=DEFAULT_OUT_DIR, help="output directory")
    return ap.parse_args(argv)


def _as_str_list(x: Any) -> list[str]:
    """Convert YAML value to a list of strings.

    Handles both string arguments (with shell-style splitting) and
    list arguments, converting None to an empty list.

    Args:
        x: YAML value (None, str, or list).

    Returns:
        List of string arguments.
    """
    if x is None:
        return []
    if isinstance(x, str):
        # allow a single string with spaces or a YAML list
        return shlex.split(x)
    return [str(t) for t in list(x)]


def _load_config(path: Path) -> tuple[list[str], list[Job]]:
    """Load and parse the YAML regression configuration file.

    Args:
        path: Path to the dv_regress.yaml file.

    Returns:
        Tuple of (default_args, jobs) where default_args are applied to all
        jobs and jobs is the list of Job objects to execute.

    Raises:
        ValueError: If YAML structure is invalid or jobs list is empty.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("dv_regress.yaml must be a mapping")

    defaults = data.get("defaults") or {}
    default_args = _as_str_list(defaults.get("args"))

    jobs_raw = data.get("jobs")
    if not isinstance(jobs_raw, list) or not jobs_raw:
        raise ValueError("'jobs' must be a non-empty list")

    jobs: list[Job] = []
    for idx, j in enumerate(jobs_raw):
        if not isinstance(j, dict):
            raise ValueError(f"jobs[{idx}] must be a mapping")
        name = str(j.get("name") or f"job{idx}")
        args = _as_str_list(j.get("args"))
        jobs.append(Job(name=name, args=args))

    return default_args, jobs


def _pretty_cmd(cmd: Sequence[str]) -> str:
    """Format command as a properly-quoted shell string.

    Args:
        cmd: Command and arguments.

    Returns:
        Shell-quoted command string suitable for copy-paste execution.
    """
    return " ".join(shlex.quote(x) for x in cmd)


def run_regress(args: argparse.Namespace) -> int:
    """Execute all regression jobs defined in the YAML file.

    Loads the configuration, runs each job sequentially, and prints a summary
    report with pass/fail status and replay commands.

    Args:
        args: Parsed command-line arguments containing file path and output dir.

    Returns:
        0 if all jobs pass, 1 if any job fails or if config is invalid.
    """
    yaml_path = args.file.resolve()
    if not yaml_path.is_file():
        print(f"\n[dv_regress] No file found at {yaml_path}", file=sys.stderr)
        return 1
    print(f"\n[dv_regress] spec: {yaml_path}")

    default_args, jobs = _load_config(yaml_path)
    if not jobs:
        print("[dv_regress] No jobs found in YAML.", file=sys.stderr)
        return 1

    passes: list[str] = []
    fails: list[str] = []

    for job in jobs:
        cmd = [
            "dv",
            *default_args,
            *job.args,
            f"--outdir={args.outdir}",
        ]
        cmd_str = _pretty_cmd(cmd)
        print(f"\n[dv_regress] job: {job.name}")
        print(f"[dv_regress] cmd: {cmd_str}\n")
        job_rc = subprocess.run(cmd, check=False).returncode
        if job_rc == 0:
            passes.append(cmd_str)
        else:
            fails.append(cmd_str)

    print("\n[dv_regress] JOBS REPORT\n")
    for c in passes:
        print(f"{utils.green('PASS')}: {c}")
    for c in fails:
        print(f"{utils.red('FAIL')}: {c}")

    rep = f"dv-report --outdir={args.outdir}"
    print(f"\n[dv_regress] To see a detailed report of all tests: {utils.yellow(rep)}")

    if fails:
        print(f"\n[dv_regress] SUMMARY: {utils.red('FAIL')}")
        return 1
    print(f"\n[dv_regress] SUMMARY: {utils.green('PASS')}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point for regression runner.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        0 if regression passes, non-zero otherwise.
    """
    args = parse_args(argv)
    return run_regress(args)


if __name__ == "__main__":
    raise SystemExit(main())
