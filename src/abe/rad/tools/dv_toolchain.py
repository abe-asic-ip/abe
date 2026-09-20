# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/dv_toolchain.py

"""Identify the toolchain (Python, cocotb, simulator) that a DV build depends on.

A build refers to files by absolute path: cocotb's libraries and headers inside
the virtual environment, and the simulator's own runtime files. If any of them
go away, e.g. a new virtual environment or a Python, cocotb or simulator
upgrade, an existing build directory can no longer be reused (make stops with
"No rule to make target" on the missing file). dv therefore includes this
fingerprint in the hash of its build directory name, so such a change gets a
fresh build.
"""

from __future__ import annotations

import functools
import importlib.metadata
import importlib.util
import platform
import subprocess
from pathlib import Path
from typing import Final, Sequence

UNAVAILABLE: Final = "unavailable"
SIM_VERSION_CMDS: Final[dict[str, tuple[str, ...]]] = {
    "verilator": ("verilator", "--version"),
}


def first_line(cmd: Sequence[str]) -> str:
    """Return the first line a tool prints (stdout, else stderr).

    Args:
        cmd: Command and arguments to run.

    Returns:
        The first output line, or "unavailable" if the tool cannot be run or
        prints nothing.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except OSError, subprocess.SubprocessError:
        return UNAVAILABLE
    lines = (proc.stdout.strip() or proc.stderr.strip()).splitlines()
    return lines[0].strip() if lines else UNAVAILABLE


@functools.cache
def toolchain_fingerprint(sim: str) -> dict[str, str]:
    """Identify the toolchain that a build depends on (cached per process).

    Args:
        sim: Simulator name (currently only "verilator").

    Returns:
        Python version, cocotb version and install directory, and the
        simulator's version line. Anything that cannot be determined is
        reported as "unavailable".
    """
    try:
        cocotb_version = importlib.metadata.version("cocotb")
    except importlib.metadata.PackageNotFoundError:
        cocotb_version = UNAVAILABLE
    spec = importlib.util.find_spec("cocotb")
    cocotb_dir = (
        str(Path(spec.origin).resolve().parent) if spec and spec.origin else UNAVAILABLE
    )
    sim_cmd = SIM_VERSION_CMDS.get(sim)
    return {
        "python": platform.python_version(),
        "cocotb": cocotb_version,
        "cocotb_dir": cocotb_dir,
        "simulator": first_line(sim_cmd) if sim_cmd else UNAVAILABLE,
    }
