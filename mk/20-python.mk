# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/20-python.mk

.PHONY: py-help
py-help:
	@echo ""
	@echo "Python Setup Steps (in order):"
	@echo ""
	@echo "  make py-venv                             # Make virtual environment"
	@echo "  source .venv/bin/activate                # Activate (Unix/macOS)"
	@echo "  .venv\\Scripts\\activate                 # Activate (Windows)"
	@echo "  make py-install-<usage>                  # Install python tools"
	@echo ""
	@echo "Python Static:"
	@echo ""
	@echo "  make PY_SRCS=<files> py-format-check     # Run isort and formatter on <files> but don't modify"
	@echo "  make PY_SRCS=<files> py-format-fix       # Run isort and formatter on <files> and modify"
	@echo "  make PY_SRCS=<files> py-lint             # Run linter on <files>"
	@echo "  make PY_SRCS=<files> py-typecheck        # Run static type checker on <files>"
	@echo "  make PY_SRCS=<files> py-static-check     # Run isort, formatter, linter, type checker on <files> but don't modify"
	@echo "  make PY_SRCS=<files> py-static-fix       # Run isort, formatter, linter, type checker on <files> and modify"

.PHONY: py-version-same
py-version-same:
	@if [ "$(PYTHON_VER_RAD)" != "$(PYTHON_VER_UARCH)" ]; then \
	  echo "ERROR: Different python versions for rad ($(PYTHON_VER_RAD)) and uarch ($(PYTHON_VER_UARCH))"; \
	  exit 2; \
	fi

.PHONY: py-venv-clean
py-venv-clean:
	rm -rf .venv
	rm -rf src/*.egg-info

.PHONY: py-ensure-venv
py-ensure-venv:
	@test -x "$(BIN)/python" || { echo "ERROR: .venv missing."; exit 2; }

.PHONY: py-venv-rad
py-venv-rad: py-venv-clean
	python$(PYTHON_VER_RAD) -m venv .venv

.PHONY: py-venv-uarch
py-venv-uarch: py-venv-clean
	python$(PYTHON_VER_UARCH) -m venv .venv

.PHONY: py-venv-all
py-venv-all: py-version-same py-venv-rad

.PHONY: py-install-dev
py-install-dev: py-ensure-venv
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

.PHONY: py-install-docs
py-install-docs: py-ensure-venv
	$(PIP) install -e ".[docs]"

.PHONY: py-install-rad
py-install-rad: py-install-dev py-install-docs
	$(PIP) install -e ".[rad]"

.PHONY: py-install-uarch
py-install-uarch: py-install-dev py-install-docs
	$(PIP) install -e ".[uarch]"

.PHONY: py-install-all
py-install-all: py-install-dev py-install-docs
	$(PIP) install -e ".[rad]"
	$(PIP) install -e ".[uarch]"

.PHONY: py-tools
py-tools: py-ensure-venv
	@echo "Python: $$($(PYTHON) --version)"
	@echo "pip:    $$($(PIP) --version)"
	@echo "black:  $$($(PY_FORMAT) --version)"
	@echo "isort:  $$($(PY_ISORT) --version)"
	@echo "pylint: $$($(PY_LINT) --version 2>/dev/null || echo 'via module')"
	@echo "mypy:   $$($(PY_TYPECHECK) --version)"
	@echo "pytest: $$($(PYTEST) --version)"

.PHONY: py-import-check
py-import-check:
	@echo "running $@ ..."
	@$(PYTHON) -c "import importlib.metadata as m; print(m.version('abe'))"
	@$(PYTHON) -c "import abe; print(abe.__version__)"

.PHONY: py-check-srcs
py-check-srcs:
	@if [ -z "$(strip $(PY_SRCS))" ]; then \
	  echo "ERROR: Set PY_SRCS=<files> (or PY_SRCS=ALL)"; exit 2; fi
	@if [ -z "$(strip $(PY_SRCS_RESOLVED))" ]; then \
	  echo "ERROR: No files matched: $(PY_SRCS)"; exit 2; fi

.PHONY: py-isort-check
py-isort-check: py-check-srcs
	@echo "running $@ ..."
	@$(PY_ISORT) --check-only --diff $(PY_ISORT_FLAGS) $(PY_SRCS_RESOLVED)

.PHONY: py-format-check
py-format-check: py-check-srcs py-isort-check
	@echo "running $@ ..."
	@$(PY_FORMAT) --check --diff $(PY_FORMAT_FLAGS) $(PY_SRCS_RESOLVED)

.PHONY: py-isort-fix
py-isort-fix: py-check-srcs
	@echo "running $@ ..."
	@$(PY_ISORT) $(PY_ISORT_FLAGS) $(PY_SRCS_RESOLVED)

.PHONY: py-format-fix
py-format-fix: py-check-srcs py-isort-fix
	@echo "running $@ ..."
	@$(PY_FORMAT) $(PY_FORMAT_FLAGS) $(PY_SRCS_RESOLVED)

.PHONY: py-lint
py-lint: py-check-srcs
	@echo "running $@ ..."
	@$(PY_LINT) $(PY_LINT_FLAGS) $(PY_SRCS_RESOLVED)

.PHONY: py-typecheck
py-typecheck: py-check-srcs
	@echo "running $@ ..."
	@$(PY_TYPECHECK) $(PY_TYPECHECK_FLAGS) $(PY_SRCS_RESOLVED)

.PHONY: py-static-check
py-static-check: py-isort-check py-format-check py-lint py-typecheck

.PHONY: py-static-fix
py-static-fix: py-format-fix py-lint py-typecheck

.PHONY: py-clean
py-clean:
	@echo "Cleaning python outputs"
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +

.PHONY: clean
clean: py-clean

.PHONY: py-test
py-test:
	@echo "Test python - not implemented yet"

.PHONY: test
test: py-test

.PHONY: py-all
py-all:
	@echo "All python - not implemented yet"

.PHONY: all
all: py-all
