# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/70-docs.mk

.PHONY: docs-help
docs-help:
	@echo ""
	@echo "Docs:"
	@echo ""
	@echo "  make docs-serve                          # mkdocs live preview"
	@echo "  make docs-build                          # mkdocs build to ./site"
	@echo "  make docs-deploy                         # Publish to GitHub Pages"

# docs/index.md is the golden source for README.md
.PHONY: docs-generate-readme
docs-generate-readme:
	@scripts/generate_readme.py

# Create at http://127.0.0.1:8000/abe/
.PHONY: docs-serve
docs-serve: py-ensure-venv
	$(MKDOCS) serve

# Build to ./site
.PHONY: docs-build
docs-build: py-ensure-venv
	$(MKDOCS) build

# Deploy to GitHub Pages
.PHONY: docs-deploy
docs-deploy: py-ensure-venv
	$(MKDOCS) gh-deploy --force

.PHONY: docs-clean
docs-clean:
	@echo "Cleaning docs outputs"
	@rm -rf site

.PHONY: clean
clean: docs-clean

.PHONY: docs-test
docs-test:
	@echo "Test docs - not implemented yet"

.PHONY: test
test: docs-test

.PHONY: docs-all
docs-all:
	@echo "All docs - not implemented yet"

.PHONY: all
all: docs-all
