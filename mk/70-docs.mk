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

.PHONE: docs-sync-readme
docs-sync-readme:
	@echo "Syncing docs/index.md to README.md"
	@cp docs/index.md README.md

.PHONY: docs-serve
docs-serve: py-ensure-venv
	$(MKDOCS) serve

.PHONY: docs-build
docs-build: py-ensure-venv
	$(MKDOCS) build

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
