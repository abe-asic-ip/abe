<!--
SPDX-FileCopyrightText: 2026 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: CONTRIBUTING.md -->

# Contributing to ABE

Thank you for your interest in contributing!

ABE is a lightweight, open-source environment for ASIC IP development.
Contributions are welcome across microarchitecture tools, RAD blocks, DV
infrastructure, documentation, and developer tooling.

---

## 📦 Contributing New RAD Designs

Please see:

- [Creating a New RAD Design](docs/rad_new_design.md)

This document provides the full workflow for proposing, designing, verifying,
and documenting a new RAD block using the ABE flows (RTL, synthesis, formal,
DV, reference model, and documentation).

---

## 🧪 Running Tests and Checks

To run the Python-based DV environment for any RAD design, see:

- [RAD DV](docs/dv.md)
- The [`dv`](docs/dv.md#1-dv--main-front-end-runs-a-single-test) command

Set up the environment first (see
[Python setup](docs/python_dev.md#set-up-and-install-the-environment)), then,
with `.venv` active, run these before you submit a change:

| Check | Command |
| ------- | --------- |
| Unit tests for the DV tools and helper scripts | `make py-test` |
| Everything: unit tests, RTL lint, synthesis, formal, all DV regressions | `make test` |
| Python static checks (isort, black, pylint, mypy, pyright) | `make PY_SRCS=ALL py-static-check` |
| Makefile lint | `make checkmake` |
| License headers | `reuse lint` |
| Header years of changed files | `make check-header-years` |

`PY_SRCS=ALL` covers the Python files that git tracks, so `git add` new files
first, or name them: `make PY_SRCS="path/a.py path/b.py" py-static-check`.

Python packages are pinned in `constraints.txt`. To upgrade one, see
[How do I upgrade a package?](docs/python_dev.md#how-do-i-upgrade-a-package)

---

## 📄 Licensing

- All contributions land under the license of the file/directory they modify.
- Python code uses **MIT**.
- SystemVerilog RTL uses **Apache-2.0**.
- Please include or preserve the correct **SPDX header** in every file.
- Set the copyright year in the SPDX header of every file you change to the
  current year. `make check-header-years` lists the changed files that need it
  and `make fix-header-years` updates them.

License texts are in the `LICENSES/` directory.

---

## 🙏 Community

If you would like to discuss ideas, propose improvements, or get help with a
contribution, please open an issue or pull request on GitHub.

Thank you for helping improve ABE!
