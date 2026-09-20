#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: scripts/tool_versions.sh

# Print the version of every tool that abe uses.
#
# Sections: platform, external (non-Python) tools, and Python packages. The
# Python package list is read from pyproject.toml so it cannot go stale.
# Output is deterministic (no timestamps), so it can be saved and diffed:
#
#   make tool-versions > versions.before.txt
#   ... update tools ...
#   make tool-versions > versions.after.txt
#   diff versions.before.txt versions.after.txt
#
# Usage: [MAKE_BIN=<make>] tool_versions.sh [python]
#   python:   interpreter of the abe virtual environment (default: .venv/bin/python)
#   MAKE_BIN: the make that is running (default: make on PATH). The Makefile sets
#             this, because "make" can resolve differently in a script than in
#             the user's shell (e.g. macOS /usr/bin/make 3.81 vs. Homebrew gmake).
#
# Tools that are missing print "not installed". Tools that are present but fail
# to run (e.g. a broken shared library) print "ERROR (exit N): <first line>".

set -u

cd "$(dirname "$0")/.." || exit 1
PYTHON=${1:-.venv/bin/python}

# Print a section heading.
# Args:
#   $1: Heading text
section() {
    printf '\n%s\n' "$1"
}

# Print one "label  version" line, using the first line of the command's output.
# Args:
#   $1: Label to print
#   $2...: Command (and arguments) that prints the tool's version
ver() {
    local label=$1
    shift
    if ! command -v "$1" >/dev/null 2>&1; then
        printf '  %-24s%s\n' "$label" "not installed"
        return
    fi
    local out rc
    out=$("$@" 2>&1)
    rc=$?
    out=$(printf '%s\n' "$out" | head -n 1 | tr '\t' ' ')
    if [ "$rc" -ne 0 ]; then
        # Drop process IDs (e.g. "dyld[1234]") so saved output stays diffable.
        out=$(printf '%s\n' "$out" | sed -E 's/\[[0-9]+\]//')
        printf '  %-24sERROR (exit %s): %s\n' "$label" "$rc" "$out"
    else
        printf '  %-24s%s\n' "$label" "$out"
    fi
}

# Print the installed version of each Python package abe declares, plus pip.
python_packages() {
    "$PYTHON" - <<'EOF'
import importlib.metadata as md
import re
import tomllib

with open("pyproject.toml", "rb") as f:
    project = tomllib.load(f)["project"]

reqs = list(project.get("dependencies", []))
for extra in project.get("optional-dependencies", {}).values():
    reqs += extra

norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
names = sorted({norm(re.split(r"[<>=!~\[;\s]", r, maxsplit=1)[0]) for r in reqs})
installed = {norm(d.metadata["Name"]): d.version for d in md.distributions()}

for name in ["pip", *names]:
    print("  %-24s%s" % (name, installed.get(name, "not installed")))
EOF
}

read -r -a CXX_CMD <<<"${CXX:-c++}"

section "Platform"
ver "OS" uname -sm
ver "make" "${MAKE_BIN:-make}" --version
ver "C++ compiler" "${CXX_CMD[@]}" --version
ver "git" git --version

section "RTL, synthesis and formal"
ver "verilator" verilator --version
ver "verible-verilog-format" verible-verilog-format --version
ver "verible-verilog-lint" verible-verilog-lint --version
ver "sv2v" sv2v --numeric-version
ver "yosys" yosys -V
ver "sby" sby --version
ver "z3" z3 --version
ver "dot (Graphviz)" dot -V

section "DV support"
ver "iverilog" iverilog -V
ver "lz4 (cli)" lz4 --version
ver "surfer" surfer --version

section "Repo checks"
ver "checkmake" checkmake --version
ver "reuse" reuse --version

section "Python"
if command -v "$PYTHON" >/dev/null 2>&1; then
    ver "python" "$PYTHON" --version
    python_packages
else
    printf '  %s\n' "$PYTHON not found. Run: make py-venv-all"
fi
