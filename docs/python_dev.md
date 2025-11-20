<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/python_dev.md -->

# ABE Python Development

## Overview

ABE uses Python for microarchitecture tools (see [FIFO Depth Tool](fifo_depth.md) and [Packet Quantization Calculator](pkt_quantize.md)) and [RAD DV](dv.md). This document describes the static analysis tools that help maintain code quality.

**Audience**: ABE contributors

**Tools**:

- [isort](#organize-imports-with-isort) - Organize imports
- [black](#format-with-black) - Format code
- [pylint](#lint-with-pylint) - Lint for errors and style
- [mypy](#type-check-with-mypy) - Type check

---

## Getting Started

### Set Up and Install the Environment

```bash
make py-venv-all
source .venv/bin/activate
make py-install-all
```

### Run Example

```bash
make PY_SRCS=ALL py-static-fix
```

See [FAQ](#faq) for more usage examples.

### Outputs

Outputs appear at the console.

### Examine the Relevant Directory Layout

```text
.
├── mk
│   ├── 00-vars.mk
│   ├── 20-python.mk
├── isort.cfg
├── mypy.ini
├── pyproject.toml
```

---

## Makefiles

Makefiles are in directory `mk`. See [Makefiles](#makefiles) section for details.

- Common flags come from `00-vars.mk`.
- Python commands are in `20-python.mk`.

Common commands:

```bash
make py-help
```

---

## Organize Imports with [isort](https://pycqa.github.io/isort)

[isort](https://pycqa.github.io/isort) automatically sorts and organizes Python import statements. It groups imports into sections (standard library, third-party, local) and sorts them alphabetically for consistency.

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

[black](https://github.com/psf/black) is a Python code formatter that automatically formats code to a consistent style. It applies the same formatting rules everywhere, making code easier to read and review.

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

[pylint](https://pylint.org) analyzes Python code for errors and style issues. It finds bugs and potential problems before you run the code.

### Commands

Run [pylint](https://pylint.org) on specified files:

```bash
make PY_SRCS=<files> py-lint
```

### Configuration

Configured in `pyproject.toml` under `[tool.pylint]` and via command-line flags in `mk/00-vars.mk`.

---

## Type Check with [mypy](https://mypy-lang.org)

[mypy](https://mypy-lang.org) is a static type checker for Python. It checks type annotations without running the code and finds type-related bugs early.

### [mypy](https://mypy-lang.org) Commands

Run [mypy](https://mypy-lang.org) type checking on specified files:

```bash
make PY_SRCS=<files> py-typecheck
```

### [mypy](https://mypy-lang.org) Configuration

- Configured in `mypy.ini`.
- The `typings` directory contains necessary type stubs for imports.

---

## FAQ

### Why doesn't ABE use the latest Python version?

ABE targets the latest Python version when dependencies support it.

---

### What does `PY_SRCS=ALL` mean?

`ALL` runs tools on all Python files in the workspace tracked by git.

---

### How do I run all static checks at once?

```bash
make PY_SRCS=ALL py-static-check  # check only
make PY_SRCS=ALL py-static-fix    # check and fix
```

---

### Can I run tools on specific files?

Yes, set `PY_SRCS` to specific file patterns:

```bash
make PY_SRCS="src/abe/uarch/*.py" py-lint
make PY_SRCS="src/abe/rad/tools/dv.py" py-typecheck
```

---

## References

- [isort](https://pycqa.github.io/isort)
- [black](https://github.com/psf/black)
- [pylint](https://pylint.org)
- [mypy](https://mypy-lang.org)

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
