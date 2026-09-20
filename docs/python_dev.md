<!--
SPDX-FileCopyrightText: 2026 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/python_dev.md -->

# ABE Python Development

## Overview

ABE uses Python for microarchitecture tools (see
[FIFO Depth Tool](fifo_depth.md) and
[Packet Quantization Calculator](pkt_quantize.md)) and [RAD DV](dv.md). This
document describes the static analysis tools that help maintain code quality.

**Audience**: ABE contributors

**Tools**:

- [isort](#organize-imports-with-isort) - Organize imports
- [black](#format-with-black) - Format code
- [pylint](#lint-with-pylint) - Lint for errors and style
- [mypy](#type-check-with-mypy) - Type check
- [pyright](#type-check-with-pyright) - Type check (the engine behind Pylance)

---

## Getting Started

### Set Up and Install the Environment

```bash
make py-venv-all
source .venv/bin/activate
make py-install-all
```

### Package Versions

ABE fixes Python package versions in two places:

- `pyproject.toml` declares **ranges**. Each starts at the version verified with
  ABE's tests and stops before the next major release, so an unverified major
  release is never picked up by accident.
- `constraints.txt` lists the **exact** version of every package (direct and
  indirect) that was verified. `make py-install-*` installs with it, so a fresh
  clone gets the verified environment.

Two make targets keep them current. `make py-outdated` compares the installed
packages with PyPI's latest stable releases and explains why any are not
installed. `make py-lock` rewrites `constraints.txt` from the current `.venv`
after you have verified an upgrade.

To install the newest versions the ranges allow instead, skip the file:

```bash
make py-install-all PY_CONSTRAINTS=
```

### Run Example

```bash
make PY_SRCS=ALL py-static-fix
```

See [FAQ](#faq) for more usage examples.

### Run Unit Tests

```bash
make py-test
```

These cover the DV tools (`dv` and its helpers) and the helper scripts behind
`make py-outdated` and `make check-header-years`. The cocotb benches under
`src/abe/rad/*/dv` are not unit tests; they run through `dv-regress`.

`make test` runs the unit tests (`py-test`), the RTL lint of every design
(`rtl-test`), the synthesis of every design (`synth-test`), every formal proof
and cover (`formal-test`), and every DV regression (`dv-test`). The other areas
do not have tests yet.

To run a subset or change the pytest options:

```bash
make py-test PY_TEST_PATHS=scripts/test_py_outdated.py
make py-test PY_TEST_OPTS="-v -x"
```

### Examine Outputs

Outputs appear at the console.

### Explore Relevant Directory Layout

```text
.
├── mk
│   ├── 00-vars.mk
│   ├── 20-python.mk
├── scripts
│   ├── check_header_years.py
│   ├── generate_readme.py
│   ├── py_lock.sh
│   ├── py_outdated.py
│   ├── test_check_header_years.py
│   ├── test_py_outdated.py
│   └── tool_versions.sh
├── src
│   └── abe
│       └── rad
│           └── tools
│               ├── conftest.py
│               ├── test_dv_build_fingerprint.py
│               ├── test_dv_lz4.py
│               └── test_dv_toolchain.py
├── .isort.cfg
├── constraints.txt
├── mypy.ini
└── pyproject.toml
```

---

## Makefiles

Makefiles are in directory `mk`. See [Makefiles](#makefiles) section for details.

- Common flags come from `00-vars.mk`.
- Python commands are in `20-python.mk`.

Common commands:

```bash
make py-help
make py-test
make py-outdated
make py-lock
```

---

## Organize Imports with [isort](https://pycqa.github.io/isort)

[isort](https://pycqa.github.io/isort) automatically sorts and organizes Python
import statements. It groups imports into sections (standard library,
third-party, local) and sorts them alphabetically for consistency.

### [isort](https://pycqa.github.io/isort) Commands

Check import organization without modifying files:

```bash
make PY_SRCS=<files> py-isort-check
```

Fix import organization:

```bash
make PY_SRCS=<files> py-isort-fix
```

The format commands also include [isort](https://pycqa.github.io/isort):

```bash
make PY_SRCS=<files> py-format-check  # includes isort check
make PY_SRCS=<files> py-format-fix    # includes isort fix
```

### [isort](https://pycqa.github.io/isort) Configuration

Configured in `.isort.cfg` and `pyproject.toml` under `[tool.isort]`.

---

## Format with [black](https://github.com/psf/black)

[black](https://github.com/psf/black) is a Python code formatter that
automatically formats code to a consistent style. It applies the same
formatting rules everywhere, making code easier to read and review.

### [black](https://github.com/psf/black) Commands

Check code formatting without modifying files:

```bash
make PY_SRCS=<files> py-format-check
```

Fix code formatting:

```bash
make PY_SRCS=<files> py-format-fix
```

### [black](https://github.com/psf/black) Configuration

Configured in `pyproject.toml` under `[tool.black]`.

---

## Lint with [pylint](https://pylint.org)

[pylint](https://pylint.org) analyzes Python code for errors and style issues.
It finds bugs and potential problems before you run the code.

### Commands

Run [pylint](https://pylint.org) on specified files:

```bash
make PY_SRCS=<files> py-lint
```

### Configuration

Configured in `pyproject.toml` under `[tool.pylint]` and via command-line flags
in `mk/00-vars.mk`.

---

## Type Check with [mypy](https://mypy-lang.org)

[mypy](https://mypy-lang.org) is a static type checker for Python. It checks
type annotations without running the code and finds type-related bugs early.

### [mypy](https://mypy-lang.org) Commands

Run [mypy](https://mypy-lang.org) type checking on specified files:

```bash
make PY_SRCS=<files> py-mypy
```

### [mypy](https://mypy-lang.org) Configuration

- Configured in `mypy.ini`.
- The `typings` directory contains necessary type stubs for imports.

---

## Type Check with [pyright](https://github.com/microsoft/pyright)

[pyright](https://github.com/microsoft/pyright) is a second static type checker.
It is the engine behind Pylance in VS Code, so `make py-pyright` reproduces what
the editor's Problems tab reports. It and mypy disagree in places, and each
catches things the other misses. For example, Pyright rejects
`__doc__.split(...)` because a module docstring can be `None`, and mypy accepts
it. ABE runs both.

### [pyright](https://github.com/microsoft/pyright) Commands

Run [pyright](https://github.com/microsoft/pyright) type checking on specified
files:

```bash
make PY_SRCS=<files> py-pyright
```

### [pyright](https://github.com/microsoft/pyright) Configuration

- Configured in `pyproject.toml` under `[tool.pyright]`. It mirrors `mypy.ini`:
  the same Python version and import paths, and every parameter must be
  annotated.
- The `typings` directory contains necessary type stubs for imports.
- Pyright is installed as the `pyright[nodejs]` package, which includes the
  Pyright engine and its Node.js runtime. Nothing is downloaded when it first
  runs, it works offline, and both are pinned in `constraints.txt` like every
  other package.

---

## FAQ

### Which Python version does ABE use?

ABE requires Python 3.14 or newer (`requires-python` in `pyproject.toml`) and
targets the latest stable Python once its dependencies support it. Black's
`target-version` is `py314`, so some syntax, such as `except A, B:` without
parentheses, does not run on older versions.

---

### Why are versions in both `pyproject.toml` and `constraints.txt`?

`pyproject.toml` says which versions ABE supports. It can only name the direct
dependencies, and exact pins there would still leave the indirect ones (for
example `protobuf` or `numpy`) free to change. `constraints.txt` pins all of
them, so an install reproduces the environment that was verified.

---

### How do I upgrade a package?

1. See what is behind, and why: `make py-outdated`. It lists upgrade
   candidates, packages held back by another package or by the Python
   version, and packages your own range excludes.
2. If the new version is outside the range in `pyproject.toml`, widen the range.
3. Install it: `.venv/bin/pip install -U <package>`.
4. Verify: run the DV regression, formal, static checks and the uarch tools.
5. Record the result with `make py-lock`, and commit `pyproject.toml` and
   `constraints.txt` together.

---

### What does `PY_SRCS=ALL` mean?

`ALL` runs tools on all Python files in the workspace tracked by git. New files
are not included until you `git add` them. To check them earlier, name them:
`make PY_SRCS="path/a.py path/b.py" py-static-check`.

---

### How do I run all static checks at once?

```bash
make PY_SRCS=ALL py-static-check  # check only
make PY_SRCS=ALL py-static-fix    # check and fix
```

Both run isort, black, pylint, mypy and pyright.

---

### Can I run tools on specific files?

Yes, set `PY_SRCS` to specific file patterns:

```bash
make PY_SRCS="src/abe/uarch/*.py" py-lint
make PY_SRCS="src/abe/rad/tools/dv.py" py-mypy
make PY_SRCS="src/abe/rad/tools/dv.py" py-pyright
```

---

## References

- [isort](https://pycqa.github.io/isort)
- [black](https://github.com/psf/black)
- [pylint](https://pylint.org)
- [mypy](https://mypy-lang.org)
- [pyright](https://github.com/microsoft/pyright)

---

## Licensing

See the `LICENSES` directory at the repository root.
