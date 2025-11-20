# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/utils.py

"""Utility functions for dv.py and other scripts."""

from __future__ import annotations

import logging
import random
import re
import time
from os import PathLike
from pathlib import Path
from typing import Sequence, Union

import matplotlib.pyplot as plt

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


class NoColorFormatter(logging.Formatter):
    """Formatter that strips ANSI color codes from log messages."""

    # Regex to match ANSI escape sequences
    ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")

    def format(self, record: logging.LogRecord) -> str:
        """Format the record and strip ANSI codes."""
        formatted = super().format(record)
        return self.ANSI_ESCAPE.sub("", formatted)


class PlotLine:
    """Reusable wrapper for simple matplotlib line plots."""

    def __init__(
        self,
        outdir: Union[str, Path] = "output",
        figsize: tuple[int, int] = (10, 6),
    ):
        """Initialize with output directory and figure size."""
        self.outdir = ensure_dir(outdir, True)
        self.figsize = figsize
        self.title: str | None = None
        self.xlabel: str = ""
        self.ylabel: str = ""
        self._initialized = False

    def _init_plot(self) -> None:
        """Create figure once, if not already done."""
        if not self._initialized:
            plt.figure(figsize=self.figsize)
            self._initialized = True

    # pylint: disable=too-many-positional-arguments
    def add_line(  # pylint: disable=too-many-arguments
        self,
        xs: Sequence[float],
        ys: Sequence[float],
        label: str,
        color: str = "blue",
        linestyle: str = "-",
        marker: str = "",
        linewidth: float = 2.0,
    ) -> None:
        """Add a labeled line to the plot."""
        self._init_plot()
        plt.plot(
            xs,
            ys,
            label=label,
            color=color,
            linestyle=linestyle,
            marker=marker,
            linewidth=linewidth,
        )

    def set_labels(self, xlabel: str, ylabel: str, title: str = "") -> None:
        """Set plot title and axis labels."""
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title

    def format(self) -> None:
        """Apply grid, layout, labels, and legend."""
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        if self.title:
            plt.title(self.title)
        plt.grid(True)
        plt.tight_layout()

    def save(self, filename: str, fmt: str = "png") -> None:
        """Save the plot to disk."""
        path = self.outdir / f"{filename}.{fmt}"
        plt.savefig(path)
        logging.debug("Saved plot: %s", path)

    def show(self, block: bool = True) -> None:
        """Display the plot window."""
        plt.show(block=block)


def absolutize_srclist(infile: Path, repo_root: Path, out_dir: Path) -> Path:
    """
    Write an absolute-path copy of infile into out_dir and return its path.
    Recursively expands -f references and converts all paths to absolute.
    """
    out = out_dir / "srclist.abs.f"

    def process_file(filepath: Path, lines_out: list[str]) -> None:
        """Recursively process a srclist file and its -f references."""
        for raw in filepath.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("+incdir+"):
                rel = line[len("+incdir+") :]
                abs_inc = (repo_root / rel).resolve()
                lines_out.append(f"+incdir+{abs_inc}")
            elif line.startswith("-f "):
                # Recursively inline the -f referenced file
                rel = line[3:].strip()  # Remove "-f " prefix
                nested_file = (repo_root / rel).resolve()
                if nested_file.exists():
                    process_file(nested_file, lines_out)
                else:
                    # If file doesn't exist, pass through the line for error reporting
                    lines_out.append(line)
            elif line.startswith(("-", "+")):
                # pass through things like +define+, -y, etc.
                lines_out.append(line)
            else:
                # treat as a source file path
                abs_src = (repo_root / line).resolve()
                lines_out.append(str(abs_src))

    lines_out: list[str] = []
    process_file(infile, lines_out)
    out.write_text("\n".join(lines_out) + "\n")
    return out


def configure_logger(
    verbosity: str = "info", log_file: Path | None = None
) -> logging.Logger:
    """Configure and return a logger with console and optional file handlers.

    Args:
        verbosity: Log level (critical, error, warning, info, debug, notset)
        log_file: Optional path to log file. If provided, logs to both console and file.

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(verbosity.upper())

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    no_color_formatter = NoColorFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stdout) - keeps colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(verbosity.upper())
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file provided) - strips colors
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setLevel(verbosity.upper())
        file_handler.setFormatter(no_color_formatter)
        logger.addHandler(file_handler)

    return logging.getLogger(__name__)


def ensure_dir(
    d: Union[str, Path, PathLike[str]], make_if_not_exists: bool = False
) -> Path:
    """Return absolute path if directory exists, optionally create it."""
    path = Path(d)
    if not path.exists():
        if make_if_not_exists:
            path.mkdir(parents=True, exist_ok=True)
            logging.info("Created directory: %s", path)
        else:
            raise FileNotFoundError(f"Directory does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    return path.resolve()


def get_repo_root() -> Path:
    """Return the root of the repo (where pyproject.toml lives)."""
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "pyproject.toml").exists():
            return p
    # Fallback: parent of 'src' if present, else filesystem root’s parent
    for p in here.parents:
        if p.name == "src":
            return p.parent
    return here.parents[-1]


def green(s: str) -> str:
    """Wrap text in green ANSI escape codes."""
    return f"{GREEN}{s}{RESET}"


def iso_utc() -> str:
    """Return current time in ISO8601 Z format (UTC)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def normalize_seed(rng: random.Random, s: str) -> int:
    """
    Normalize a seed string to a decimal string.
    Supports 'rand'/'random'/'auto' and 0x... hex.
    Raises SystemExit on invalid input (to match existing CLI behavior).
    """
    low = s.lower()
    if low in {"rand", "random", "auto"}:
        return rng.getrandbits(32)
    try:
        return int(s, 0) & 0xFFFF_FFFF
    except ValueError as exc:
        raise SystemExit(
            f"[dv] Invalid seed '{s}'. Use decimal, 0x..., or 'random'."
        ) from exc


def red(s: str) -> str:
    """Wrap text in red ANSI escape codes."""
    return f"{RED}{s}{RESET}"


def round_value(value: int, rounding: str) -> int:
    """Round a value according to the specified method."""
    if rounding == "none":
        return value
    if rounding == "power2":
        if value <= 1:
            return 1
        p = 1
        while p < value:
            p <<= 1
        return p
    raise ValueError(f"Unknown rounding: {rounding}")


def to_snake_case(name: str) -> str:
    """Convert module name to snake_case.

    Examples:
        rad_async_fifo -> rad_async_fifo
        RadAsyncFifo -> rad_async_fifo
    """
    # Handle both snake_case and CamelCase inputs
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def to_pascal_case(name: str) -> str:
    """Convert module name to PascalCase.

    Examples:
        rad_async_fifo -> RadAsyncFifo
        RadAsyncFifo -> RadAsyncFifo
    """
    # Split on underscores and capitalize each part
    parts = name.split("_")
    return "".join(part.capitalize() for part in parts)


def yellow(s: str) -> str:
    """Wrap text in yellow ANSI escape codes."""
    return f"{YELLOW}{s}{RESET}"
