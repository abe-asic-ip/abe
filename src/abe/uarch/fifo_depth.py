# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth.py

"""Fifo depth calculation orchestrator."""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Sequence, cast

import yaml

from abe.uarch.fifo_depth_base import FifoBaseResults, FifoSolver
from abe.uarch.fifo_depth_cbfc import CbfcSolver
from abe.uarch.fifo_depth_cdc import CdcSolver
from abe.uarch.fifo_depth_ready_valid import ReadyValidSolver
from abe.uarch.fifo_depth_replay import ReplaySolver
from abe.uarch.fifo_depth_utils import get_args
from abe.uarch.fifo_depth_xon_xoff import XonXoffSolver
from abe.utils import configure_logger, green, red


def _get_fifo_type(spec: dict) -> str:
    """
    Extract FIFO protocol type from specification.

    Returns fifo_type from spec (cbfc, ready_valid, replay, or xon_xoff).
    """
    if "fifo_type" not in spec:
        raise ValueError("Missing 'fifo_type' field in spec.")
    fifo_type = str(spec["fifo_type"])
    if fifo_type not in ("cbfc", "ready_valid", "replay", "xon_xoff"):
        raise ValueError(f"{fifo_type=}")
    return fifo_type


def _get_logger(outdir: Path, verbosity: str) -> logging.Logger:
    """
    Configure and return logger for FIFO depth calculation.

    Creates log file in outdir and sets level based on verbosity.
    """
    log_file = outdir / "run.log"
    logger = configure_logger(verbosity, log_file)
    logger.info("Logging to console and %s", log_file)
    return logger


def _get_outdir(spec_file: str, user_outdir: str | None) -> Path:
    """
    Determine output directory for calculation results.

    Uses command-line override if provided, otherwise creates directory
    based on spec filename.
    """
    spec_path = Path(spec_file)
    if user_outdir:
        # User specified outdir - use it for all files
        outdir = Path(user_outdir)
    else:
        # Auto-generate outdir based on current spec file
        outdir = Path(f"out_uarch_fd_{spec_path.stem}")
    # Clean output directory: delete contents if it exists, then create it
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    return outdir


def _get_solver_argv(
    spec_file: str, outdir: Path, results: str, verbosity: str
) -> list[str]:
    """
    Build command-line arguments for individual protocol solvers.

    Returns argv list with spec path, output directory, and optional
    verbosity flag for solver invocation.
    """
    solver_argv = [spec_file, "--outdir", str(outdir)]
    if results:
        solver_argv.extend(["--results", results])
    if verbosity:
        solver_argv.extend(["--verbosity", verbosity])
    return solver_argv


def _get_spec(spec_file: str, logger: logging.Logger) -> dict:
    """
    Load and parse YAML specification file.

    Returns validated spec dictionary after logging file path.
    """
    spec_path = Path(spec_file)
    if not spec_path.exists():
        raise SystemExit(f"ERROR: Spec file not found: {spec_file}")
    with open(spec_path, encoding="utf-8") as f:
        s = f.read()
        logger.debug("Input spec:\n%s", s)
        spec = cast(dict, yaml.safe_load(s))
        logger.debug("Loaded spec:\n%s", json.dumps(spec, indent=2))
    return spec


def _get_sync_solver(fifo_type: str) -> FifoSolver:
    """
    Return appropriate synchronous FIFO solver instance for protocol.

    Maps fifo_type string to corresponding solver class (CBFC, RV, etc.).
    """
    if fifo_type == "cbfc":
        return CbfcSolver()
    if fifo_type == "replay":
        return ReplaySolver()
    if fifo_type == "xon_xoff":
        return XonXoffSolver()
    return ReadyValidSolver()


def _handle_results(results: FifoBaseResults, logger: logging.Logger) -> int:
    """
    Process calculation results and log validation errors.

    Returns 1 if validation fails, 0 if validation passes.
    """
    name = results.__class__.__name__
    error = 0
    s = f"{name}: {results.basic_checks_pass=}"
    if results.basic_checks_pass:
        logger.info(green(s))
    else:
        logger.error(red(s))
        error += 1
    return error


def _log_elapsed_time(
    start_time: float, spec_file: str, logger: logging.Logger
) -> None:
    """
    Record processing time for specification file.

    Logs elapsed time in HH:MM:SS format since start_time for
    performance tracking and benchmarking.
    """
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(int(elapsed_time), 3600)
    minutes, seconds = divmod(remainder, 60)
    logger.info("Completed %s in %d:%02d:%02d", spec_file, hours, minutes, seconds)


def _run_cdc(spec: dict, solver_argv: list[str], logger: logging.Logger) -> None:
    """
    Execute CDC stage solver if present in specification. Raises RuntimeError if
    validation checks fail.
    """
    if "cdc" not in spec:
        return
    cdc_solver = CdcSolver()
    cdc_solver.run(solver_argv)
    assert cdc_solver.results is not None, "Results should be set after run()"
    res = _handle_results(cdc_solver.results, logger)
    if res != 0:
        raise RuntimeError(f"Stage 1 failed {res} validation checks")


def _run_sync(  # pylint: disable=too-many-arguments, too-many-positional-arguments
    spec: dict,
    solver_argv: list[str],
    logger: logging.Logger,
) -> None:
    """
    Execute synchronous stage solver and validate results. Raises RuntimeError if
    validation checks fail.
    """
    fifo_type = _get_fifo_type(spec)
    sync_solver = _get_sync_solver(fifo_type)
    sync_solver.run(solver_argv)
    assert sync_solver.results is not None, "Results should be set after run()"
    res = _handle_results(sync_solver.results, logger)
    if res != 0:
        raise RuntimeError(f"Stage 2 failed {res} validation checks")


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """
    Orchestrate multi-stage FIFO depth calculation workflow.

    Processes one or more spec files through CDC and synchronous stages,
    generating results. Returns 0 on success.
    """

    args = get_args(argv, "Fifo depth calculator")

    # Ensure args.spec is always a list for iteration
    spec_files = [args.spec] if isinstance(args.spec, str) else args.spec

    # Process each input spec file
    for spec_file in spec_files:

        start_time = time.time()
        outdir = _get_outdir(spec_file, args.outdir)
        logger = _get_logger(outdir, args.verbosity)
        spec = _get_spec(spec_file, logger)

        # Stage 1: CDC fifo
        solver_argv = _get_solver_argv(spec_file, outdir, "cdc_results", args.verbosity)
        logger.info("command: %s", " ".join(solver_argv))
        _run_cdc(spec, solver_argv, logger)

        # Stage 2: Synchronous fifo
        solver_argv = _get_solver_argv(
            spec_file, outdir, args.results_name, args.verbosity
        )
        logger.info("command: %s", " ".join(solver_argv))
        _run_sync(spec, solver_argv, logger)

        _log_elapsed_time(start_time, spec_file, logger)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
