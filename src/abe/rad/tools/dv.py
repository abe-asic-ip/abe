# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/dv.py

"""Run UVM testbenches via cocotb, pyuvm, and pytest.

This module provides a framework for building and testing HDL designs using:
- cocotb for HDL/Python co-simulation
- pyuvm for UVM-style verification infrastructure
- pytest for test orchestration and reporting

Supports multiple simulators (Verilator, Icarus) and configurable waveform
generation (FST, VCD). Handles multi-seed regression testing with automatic
test manifest generation for result tracking.

Command-line interface:
    dv --design=<design> --test=<test> [OPTIONS]

Typical usage:
    # Build and run a single test
    dv --design=rad_async_fifo --test=rad_async_fifo_env

    # Run with specific seeds
    dv --design=rad_async_fifo --test=rad_async_fifo_env --seeds 42 100 200

    # Generate N random seeds
    dv --design=rad_async_fifo --test=rad_async_fifo_env --nseeds=10
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import shlex
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Sequence

import pytest
from cocotb_tools.runner import get_runner

# If executed as a script (path mode), __package__ is empty/None and __spec__ is None.
if (__package__ in (None, "")) and (__spec__ is None):
    print("[dv] ERROR: Please run as 'dv'", file=sys.stderr)
    raise SystemExit(2)

from abe import utils  # isort:skip pylint: disable=wrong-import-position

PROJ_DIR: Final[Path] = utils.get_repo_root()
RAD_ROOT: Final[Path] = PROJ_DIR / "src" / "abe" / "rad"
DEFAULT_OUT_DIR = "out_dv"
DEFAULT_BUILDS_SUBDIR = "builds"
DEFAULT_TESTS_SUBDIR = "tests"
DEFAULT_FRAMEWORK = f"{Path(__file__).resolve()}::test_framework"
DEFAULT_PYTEST_OPTS: tuple[str, ...] = ("-vv", "-s", "-ra", "-x")
DEFAULT_DESIGN = ""
DEFAULT_TEST = ""


@dataclass
class _ContextBox:
    value: dict[str, Any] | None = None


@dataclass(frozen=True)
class BuildCfg:  # pylint: disable=too-many-instance-attributes
    """Build configuration."""

    sim: str
    waves: bool
    waves_fmt: str
    design: str
    build_dir: Path
    build_args: list[str]
    build_log_file: Path
    build_force: bool


@dataclass(frozen=True)
class TestCfg:  # pylint: disable=too-many-instance-attributes
    """Test configuration."""

    sim: str
    waves: bool
    waves_fmt: str
    design: str
    build_dir: Path
    test: str
    test_module: str
    seed: int
    test_dir: Path
    test_log_file: Path
    wave_file: Path
    test_args: list[str]
    extra_plusargs: list[str]
    extra_env: dict[str, str]
    results_xml: Path | None


# === CLI ===


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for DV test execution.

    Args:
        argv: Command-line arguments to parse. If None, uses sys.argv[1:].

    Returns:
        Parsed argument namespace with all configuration parameters.
    """

    ap = argparse.ArgumentParser(
        description="Run UVM testbenches via cocotb, pyuvm, and pytest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Global
    ap.add_argument(
        "--cmd",
        choices=["build", "test", "both"],
        default=os.getenv("CMD", "both"),
        help="run only build, only test, or both",
    )
    ap.add_argument(
        "--sim",
        choices=["verilator", "icarus"],
        default=os.getenv("SIM", "verilator"),
        help="simulator (verilator, icarus)",
    )
    ap.add_argument("--outdir", default=DEFAULT_OUT_DIR, help="output directory")
    ap.add_argument(
        "--verbosity",
        choices=["critical", "error", "warning", "info", "debug", "notset"],
        default=os.getenv("VERBOSITY", "info"),
        help="logging level for Python/pyuvm/cocotb",
    )
    ap.add_argument(
        "--waves",
        choices=["0", "1"],
        default=os.getenv("WAVES", "0"),
        help="enable waveforms",
    )
    ap.add_argument(
        "--waves_fmt",
        choices=["fst", "vcd"],
        default=os.getenv("WAVES_FMT", "fst"),
        help="waveform format",
    )

    # Build
    ap.add_argument("--design", default=DEFAULT_DESIGN, help="design to build")
    ap.add_argument("--build-force", action="store_true", help="force a build")
    ap.add_argument(
        "--build-arg",
        dest="build_args",
        action="append",
        default=[],
        help="extra build arg passed verbatim to the simulator (repeatable), "
        "e.g. --build-arg=-DSIMULATE_METASTABILITY",
    )

    # Test
    ap.add_argument(
        "--test",
        default=DEFAULT_TEST,
        help="abe.rad.<design>.dv.<test_module>",
    )
    ap.add_argument(
        "--expect",
        choices=["PASS", "FAIL"],
        default="PASS",
        help="expected result for this test (used in reports)",
    )
    ap.add_argument(
        "--seeds",
        nargs="+",
        metavar="SEED",
        help="Explicit seed list (decimal or 0x...). Overrides --nseeds.",
    )
    ap.add_argument(
        "--nseeds", type=int, default=0, help="Generate N seeds if --seeds not given."
    )
    ap.add_argument(
        "--seed-base",
        type=int,
        default=1999,
        help="Base seed for generating additional seeds.",
    )
    ap.add_argument(
        "--seed-out",
        type=Path,
        default=None,
        help="Write the final seed list to a file (one per line).",
    )
    ap.add_argument(
        "--check-en",
        choices=["0", "1"],
        default=os.getenv("CHECK_EN", "1"),
        help="enable checkers",
    )
    ap.add_argument(
        "--coverage-en",
        choices=["0", "1"],
        default=os.getenv("COVERAGE_EN", "1"),
        help="enable coverage collection",
    )

    return ap.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    """Validate required arguments and fail fast if invalid.

    Args:
        args: Parsed command-line arguments.

    Raises:
        SystemExit: If required arguments are missing or invalid.
    """
    if not args.design:
        raise SystemExit("[dv]: error: argument --design required")
    if args.cmd in {"both", "test"} and not args.test:
        raise SystemExit(f"[dv]: error: argument --test required for {args.cmd=}")


def _strip_seed_args(argv: list[str]) -> list[str]:
    """Remove seed-related arguments from command-line argument list.

    Removes --nseeds and --seeds arguments (both '--opt val' and '--opt=val' forms)
    to enable replay commands with explicit seed values.

    Args:
        argv: List of command-line arguments.

    Returns:
        New list with seed arguments removed.
    """
    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--nseeds":
            i += 2  # skip flag + value
            continue
        if tok.startswith("--nseeds="):
            i += 1
            continue
        if tok == "--seeds":
            i += 1
            # skip seed values until next flag or end
            while i < len(argv) and not argv[i].startswith("-"):
                i += 1
            continue
        if tok.startswith("--seeds="):
            i += 1
            continue
        out.append(tok)
        i += 1
    return out


def _pretty(argv: list[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)


# === Context & Logging ===

_CTX = _ContextBox()


def _ctx() -> dict[str, Any]:
    """Access the in-process context provided by the orchestrator.

    Returns:
        Dictionary containing the current test context (seed, paths, configs).

    Raises:
        RuntimeError: If context has not been initialized.
    """
    if _CTX.value is None:
        raise RuntimeError("[dv] internal context not set")
    return _CTX.value


def _configure_logging(verbosity: str) -> None:
    """Configure global logging format and level for Python, pyuvm, and cocotb.

    Sets up logging with appropriate format (reduced or full) and verbosity level.
    Respects COCOTB_REDUCED_LOG_FMT environment variable for format selection.

    Args:
        verbosity: Logging level name (critical, error, warning, info, debug, notset).
    """
    lvl_name = (verbosity or "info").strip().lower()
    name_to_level = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "notset": logging.NOTSET,
    }
    lvl = name_to_level.get(lvl_name, logging.INFO)

    reduced = os.getenv("COCOTB_REDUCED_LOG_FMT") == "1"
    if reduced:
        fmt = "%(levelname).1s %(name)s: %(message)s"
        datefmt = None
    else:
        fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        datefmt = "%H:%M:%S"

    if not logging.getLogger().handlers:
        logging.basicConfig(level=lvl, format=fmt, datefmt=datefmt)
    logging.getLogger().setLevel(lvl)


# === Seeds ===


def _derive_seeds(args: argparse.Namespace) -> list[int]:
    print(
        f"\n[dv] deriving seeds from {args.seed_base=}, {args.seeds=}, {args.nseeds=}"
    )
    rng = random.Random(args.seed_base & 0xFFFF_FFFF)
    if args.seeds:
        seeds = [utils.normalize_seed(rng, s) for s in args.seeds]
    elif args.nseeds > 0:
        seeds = [utils.normalize_seed(rng, "random") for _ in range(args.nseeds)]
    else:
        seeds = [42]
    print(f"[dv] using seeds: {seeds}")
    return seeds


# === Pytest Args ===


def _pytest_args(selector: str) -> list[str]:
    """Single source of truth for pytest invocation args."""
    return [*DEFAULT_PYTEST_OPTS, selector]


def _pytest_cmd_str(selector: str) -> str:
    """Pretty command string for logs/manifest derived from _pytest_args."""
    return "python -m pytest " + " ".join(_pytest_args(selector))


# === Build/Test Config ===


def _build_dir_for_ctx(ctx: dict) -> Path:
    """Generate build directory path with fingerprint hash.

    Creates a unique build directory path based on build-affecting parameters.
    The path format is: <outdir>/builds/<design>.<hash10>
    The hash is computed from simulator, waves settings, and build arguments.

    Args:
        ctx: Context dictionary containing build configuration.

    Returns:
        Absolute path to the build directory.
    """
    sim = str(ctx.get("sim", "verilator"))
    outdir = str(ctx.get("outdir", DEFAULT_OUT_DIR))
    waves = bool(ctx.get("waves", True))
    waves_fmt = str(ctx.get("waves_fmt", "fst")).lower()
    waves_fmt = waves_fmt if waves_fmt in {"fst", "vcd"} else "fst"
    design = str(ctx.get("design", DEFAULT_DESIGN))
    user_build_args = [str(x) for x in ctx.get("user_build_args", [])]

    # Only include knobs that affect the compiled artifact.
    fp_obj = {
        "sim": sim,
        "waves": waves,
        "waves_fmt": waves_fmt if waves else "",
        "user_build_args": user_build_args,
    }
    raw = json.dumps(fp_obj, sort_keys=True, separators=(",", ":")).encode()
    build_hash = hashlib.sha1(raw).hexdigest()[:10]
    leaf = f"{design}.{build_hash}"

    return (PROJ_DIR / outdir / DEFAULT_BUILDS_SUBDIR / leaf).resolve()


def _write_build_manifest(cfg: "BuildCfg", *, status: str) -> None:
    """Write or update build manifest.json with current build status.

    The manifest tracks build configuration, status, and fingerprint for
    reproducibility and caching.

    Args:
        cfg: Build configuration object.
        status: Build status ("started", "built", or "failed").
    """
    manifest = {
        "status": status,  # "started" | "built" | "failed"
        "updated_at": utils.iso_utc(),
        "sim": cfg.sim,
        "waves": cfg.waves,
        "waves_fmt": cfg.waves_fmt,
        "design": cfg.design,
        "build_force": cfg.build_force,
        "build_dir": str(cfg.build_dir),
        "fingerprint": cfg.build_dir.name,  # last path element (hash)
        "build_args": cfg.build_args,  # final, ordered, verbatim
    }
    cfg.build_dir.mkdir(parents=True, exist_ok=True)
    (cfg.build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _verilator_build_switches(waves: bool, waves_fmt: str) -> list[str]:
    """Generate Verilator-specific build switches.

    Args:
        waves: Whether to enable waveform tracing.
        waves_fmt: Waveform format ("fst" or "vcd").

    Returns:
        List of Verilator command-line arguments.
    """
    args: list[str] = ["--timing", "--autoflush"]
    if waves:
        args.append("--trace-fst" if waves_fmt == "fst" else "--trace")
    return args


def _verilator_test_switches(waves: bool, wave_file: Path) -> list[str]:
    """Generate Verilator-specific test runtime switches.

    Args:
        waves: Whether to enable waveform tracing.
        wave_file: Path where waveform file should be written.

    Returns:
        List of Verilator test arguments.
    """
    if not waves:
        return []
    return ["--trace-file", str(wave_file.resolve())]


def _icarus_wave_plusarg(waves: bool, wave_file: Path) -> list[str]:
    """Return the dumpfile_path plusarg for Icarus waveform output.

    This must be a plusarg (not test_args) so it appears after the .vvp file.
    """
    if not waves:
        return []
    # Icarus docs: "To redirect the wave file to a different location,
    # use the plusarg dumpfile_path when running the test."
    return [f"+dumpfile_path={wave_file.resolve()}"]


def _make_build_cfg(ctx: dict) -> BuildCfg:
    sim = str(ctx.get("sim", "verilator"))
    waves = bool(ctx.get("waves", True))
    waves_fmt = str(ctx.get("waves_fmt", "fst")).lower()
    waves_fmt = waves_fmt if waves_fmt in {"fst", "vcd"} else "fst"

    # Icarus runner only supports FST traces; normalize to fst
    if sim == "icarus" and waves and waves_fmt != "fst":
        logging.getLogger(__name__).warning(
            "Icarus only supports FST waveforms with the cocotb runner; "
            "overriding waves_fmt=%s -> fst",
            waves_fmt,
        )
        waves_fmt = "fst"

    design = str(ctx.get("design", DEFAULT_DESIGN))
    build_force = bool(ctx.get("build_force", False))

    build_dir = _build_dir_for_ctx(ctx)
    build_dir.mkdir(parents=True, exist_ok=True)

    build_args: list[str] = []
    if sim == "verilator":
        build_args += _verilator_build_switches(waves, waves_fmt)

    if design:
        srclist_file = PROJ_DIR / "src" / "abe" / "rad" / design / "rtl" / "srclist.f"
        abs_srclist = utils.absolutize_srclist(srclist_file, PROJ_DIR, build_dir)
        build_args += ["-f", str(abs_srclist)]

    # User-supplied build args go last so they can override defaults.
    user_build_args = [str(x) for x in ctx.get("user_build_args", [])]
    build_args += user_build_args

    return BuildCfg(
        sim=sim,
        waves=waves,
        waves_fmt=waves_fmt,
        design=design,
        build_dir=build_dir,
        build_args=build_args,
        build_log_file=build_dir / "build.log",
        build_force=build_force,
    )


def _make_test_cfg(ctx: dict) -> TestCfg:  # pylint: disable=too-many-locals
    sim = str(ctx.get("sim", "verilator"))
    outdir = str(ctx.get("outdir", DEFAULT_OUT_DIR))
    waves = bool(ctx.get("waves", True))
    waves_fmt = str(ctx.get("waves_fmt", "fst")).lower()
    waves_fmt = waves_fmt if waves_fmt in {"fst", "vcd"} else "fst"

    # Icarus runner only supports FST traces; normalize to fst
    if sim == "icarus" and waves and waves_fmt != "fst":
        logging.getLogger(__name__).warning(
            "Icarus only supports FST waveforms with the cocotb runner; "
            "overriding waves_fmt=%s -> fst",
            waves_fmt,
        )
        waves_fmt = "fst"

    design = str(ctx.get("design", DEFAULT_DESIGN))

    test = str(ctx.get("test", DEFAULT_TEST))
    test_module = f"abe.rad.{design}.dv.{test}"

    build_dir = _build_dir_for_ctx(ctx)
    build_dir.mkdir(parents=True, exist_ok=True)
    build_dir_name = build_dir.name

    seed = int(ctx.get("seed", 12345))

    tests_root = Path(
        ctx.get("tests_root", f"{outdir}/{DEFAULT_TESTS_SUBDIR}")
    ).resolve()
    default_tag = f"{build_dir_name}.{test}.{seed}"
    test_tag = ctx.get("test_tag") or default_tag
    test_dir = (tests_root / test_tag).resolve()
    test_dir.mkdir(parents=True, exist_ok=True)

    wave_file = test_dir / f"waves.{waves_fmt}"

    if sim == "verilator":
        test_args = _verilator_test_switches(waves, wave_file)
    else:
        test_args = []

    # Bench knobs -> plusargs
    extra_plusargs: list[str] = []
    if "check_en" in ctx:
        extra_plusargs.append(f"+CHECK_EN={int(bool(ctx['check_en']))}")
    if "coverage_en" in ctx:
        extra_plusargs.append(f"+COVERAGE_EN={int(bool(ctx['coverage_en']))}")

    # For Icarus, add the dumpfile_path plusarg
    if sim == "icarus":
        extra_plusargs.extend(_icarus_wave_plusarg(waves, wave_file))

    # Simulator-side env (no global env writes)
    verbosity = str(ctx.get("verbosity", "info")).upper()
    extra_env: dict[str, str] = {
        "RANDOM_SEED": str(seed),
        "COCOTB_RANDOM_SEED": str(seed),
        "COCOTB_SEED": str(seed),
        "COCOTB_LOG_LEVEL": verbosity,
    }
    if extra_plusargs:
        extra_env["COCOTB_PLUSARGS"] = " ".join(extra_plusargs)

    results_xml: Path | None = None
    if os.getenv("PYTEST_CURRENT_TEST") is None:
        results_xml = test_dir / "results.xml"

    return TestCfg(
        sim=sim,
        waves=waves,
        waves_fmt=waves_fmt,
        design=design,
        build_dir=build_dir,
        test=test,
        test_module=test_module,
        seed=seed,
        test_dir=test_dir,
        test_log_file=test_dir / "test.log",
        wave_file=wave_file,
        test_args=test_args,
        extra_plusargs=extra_plusargs,
        extra_env=extra_env,
        results_xml=results_xml,
    )


# === Actions ===


def run_build(cfg: BuildCfg) -> None:
    """Execute the HDL build step using cocotb runner.

    Invokes the simulator-specific build process and updates the build
    manifest with status information.

    Args:
        cfg: Build configuration containing all necessary build parameters.
    """
    print("\n[dv] running build...\n")
    runner = get_runner(cfg.sim)
    _write_build_manifest(cfg, status="started")
    runner.build(
        hdl_toplevel=cfg.design,
        timescale=("1ns", "1ps"),
        waves=cfg.waves,
        build_dir=cfg.build_dir,
        build_args=cfg.build_args,
        log_file=str(cfg.build_log_file),
        always=cfg.build_force,
    )
    _write_build_manifest(cfg, status="built")


def run_test(cfg: TestCfg) -> None:
    """Execute a single test run using cocotb runner.

    Runs the test module with the specified configuration, including
    seed, waveform settings, and test-specific arguments.

    Args:
        cfg: Test configuration containing all necessary test parameters.
    """
    print("\n[dv] running test...\n")
    runner = get_runner(cfg.sim)
    runner.test(
        hdl_toplevel_lang="verilog",
        hdl_toplevel=cfg.design,
        waves=cfg.waves,
        build_dir=str(cfg.build_dir),
        test_module=cfg.test_module,
        log_file=str(cfg.test_log_file),
        test_args=cfg.test_args,
        plusargs=cfg.extra_plusargs,
        extra_env=cfg.extra_env,
        results_xml=str(cfg.results_xml) if cfg.results_xml else None,
    )


# === Pytest Entrypoint ===


def test_framework() -> None:
    """Pytest framework entrypoint for cocotb test execution.

    This function is called by pytest and orchestrates the build and/or test
    execution based on the in-process context. It handles logging configuration,
    build directory creation, and conditional execution of build and test phases.

    The function uses the _CTX global to access configuration rather than
    command-line arguments, allowing pytest to manage the test lifecycle.
    """
    ctx = _ctx()  # raises if not set

    cmd = str(ctx.get("cmd", "both")).lower()
    do_build = cmd in {"both", "build"}
    do_test = cmd in {"both", "test"} and bool(ctx.get("test", DEFAULT_TEST))

    bcfg = _make_build_cfg(ctx)
    tcfg = _make_test_cfg(ctx)

    print(
        f"\n\n[dv] sim={bcfg.sim} cmd={cmd} design={bcfg.design} "
        f"test={tcfg.test} seed={tcfg.seed}"
    )

    if do_build:
        run_build(bcfg)
        print(f"\n[dv] result: build: {bcfg.build_dir}")
    else:
        print("[dv] cmd=test → skipping build")
        if not bcfg.build_dir.exists():
            raise RuntimeError(
                f"[dv] build dir missing: {bcfg.build_dir}. Run with --cmd build first."
            )

    if not do_test:
        print("[dv] skipping test (no TEST or cmd=build)")
        return

    run_test(tcfg)


# === Multi-seed Orchestration ===


def _run_one_pytest(seed: int, test_dir: Path, ctx_base: dict) -> int:
    """Execute a single pytest test run with the specified seed.

    Creates test-specific context, invokes pytest framework, generates test
    manifest with results and replay command, and returns appropriate exit code.

    Args:
        seed: Random seed for this test run.
        test_dir: Directory where test outputs will be written.
        ctx_base: Base context dictionary to be extended with test-specific values.

    Returns:
        0 if test result matches expectation, 1 otherwise.
    """

    test_dir.mkdir(parents=True, exist_ok=True)

    ctx = dict(ctx_base)
    ctx["seed"] = seed
    ctx["tests_root"] = str(test_dir.parent)
    ctx["test_tag"] = test_dir.name

    _CTX.value = ctx

    sys.modules.setdefault("abe.rad.tools.dv", sys.modules[__name__])

    print(f"\n[dv] running {DEFAULT_FRAMEWORK} seed={seed} -> {test_dir}\n")

    t0 = time.time()
    framework_rc = pytest.main(_pytest_args(DEFAULT_FRAMEWORK))
    t1 = time.time()
    status = "PASS" if framework_rc == 0 else "FAIL"
    expect = str(ctx.get("expect", "PASS")).strip().upper()
    rc = 0 if status == expect else 1

    base_argv = list(_ctx().get("orig_argv", []))
    replay_argv = _strip_seed_args(base_argv) + ["--seeds", str(seed)]
    replay_cmd = ["python", "-m", "abe.rad.tools.dv", *replay_argv]
    replay_cmd_str = _pretty(replay_cmd)

    manifest = {
        "status": status,
        "expect": expect,
        "duration_s": round(t1 - t0, 3),
        "cmd": _pytest_cmd_str(DEFAULT_FRAMEWORK),
        "replay_cmd": replay_cmd_str,
        "build_dir": str(_build_dir_for_ctx(ctx)),
        "test_dir": str(test_dir),
        "ctx": dict(ctx.items()),
    }

    (test_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"\n[dv] result: test_dir: {test_dir}")
    print(f"[dv] result: duration: " f"{t1 - t0:.2f}s")
    print(f"[dv] result: expect: {expect}")
    print(f"[dv] result: status: {status} (rc={framework_rc})\n")

    if status == "PASS" and expect == "PASS":
        print(f"{utils.green('PASS (EXPECTED)')}: {replay_cmd_str}")
    elif status == "FAIL" and expect == "FAIL":
        print(f"{utils.green('FAIL (EXPECTED)')}: {replay_cmd_str}")
    elif status == "PASS" and expect == "FAIL":
        print(f"{utils.red('PASS (UNEXPECTED)')}: {replay_cmd_str}")
    elif status == "FAIL" and expect == "PASS":
        print(f"{utils.red('FAIL (UNEXPECTED)')}: {replay_cmd_str}")

    return rc


# === Main ===


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for DV test orchestration.

    Parses command-line arguments, configures logging, and orchestrates
    build/test execution for all specified seeds. Handles both single-seed
    and multi-seed test runs.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        0 if all tests pass as expected, non-zero otherwise.
    """
    orig_argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(argv)
    validate_args(args)
    _configure_logging(str(args.verbosity))

    tests_root = Path(f"{args.outdir}/{DEFAULT_TESTS_SUBDIR}").resolve()

    # Shared context for all seeds (no env; carried in-process)
    ctx_base: dict = {
        "orig_argv": orig_argv,
        "cmd": args.cmd,
        "sim": args.sim,
        "outdir": args.outdir,
        "verbosity": args.verbosity,
        "waves": (args.waves == "1"),
        "waves_fmt": args.waves_fmt,
        "design": args.design,
        "build_force": bool(args.build_force),
        "user_build_args": list(args.build_args or []),
        "test": args.test,
        "expect": args.expect,
        "check_en": (args.check_en == "1"),
        "coverage_en": (args.coverage_en == "1"),
    }

    build_dir_name = _build_dir_for_ctx(ctx_base).name

    # Even for cmd=build we go through pytest once (framework will skip test)
    rc = 0
    if args.cmd == "build":
        tag = f"{build_dir_name}.build_only"
        rc = _run_one_pytest(0, tests_root / tag, ctx_base)
    else:
        seeds: list[int] = _derive_seeds(args)
        for idx, seed in enumerate(seeds):
            tag = f"{build_dir_name}.{args.test}.{seed}"
            per_ctx = dict(ctx_base)
            # Build once (first seed) when cmd=both; subsequent seeds run tests only.
            if ctx_base["cmd"] == "both" and idx > 0:
                per_ctx["cmd"] = "test"
            rc |= _run_one_pytest(seed, tests_root / tag, per_ctx)
        if args.seed_out:
            with Path(args.seed_out).open("w", encoding="utf-8", newline="\n") as f:
                for s in seeds:
                    f.write(f"{s}\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
