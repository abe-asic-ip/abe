# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: mk/00-vars.mk

# ---------- General ----------
DESIGN ?= undefined
TEST ?= undefined

# ---------- Layout ----------
RAD_ROOT ?= src/abe/rad
DESIGN_DIR := $(RAD_ROOT)/$(DESIGN)
RTL_DIR    ?= $(DESIGN_DIR)/rtl
FORMAL_DIR ?= $(DESIGN_DIR)/formal

# Sources (default single file; overridden by srclist.f when present)
SV_SRCS     ?= $(RTL_DIR)/$(DESIGN).sv
SV_SRCLIST  ?= $(RTL_DIR)/srclist.f

# ---------- Python ----------
PYTHON_VER_RAD ?= 3.13
PYTHON_VER_UARCH ?= 3.13
VENV := .venv
BIN := $(VENV)/bin
PYTHON ?= $(BIN)/python
PIP ?= $(PYTHON) -m pip
PY_ISORT ?= $(BIN)/isort
PY_FORMAT ?= $(BIN)/black
PY_LINT ?= $(PYTHON) -m pylint
PY_TYPECHECK ?= $(BIN)/mypy
PYTEST ?= $(BIN)/pytest

PY_SRCS ?=

PY_ISORT_FLAGS ?= --profile black --line-length 88
PY_FORMAT_FLAGS ?= --line-length 88
PY_LINT_FLAGS ?= --max-line-length=88
PY_TYPECHECK_FLAGS ?= --config-file mypy.ini

# ---------- uarch ----------
UARCH_DIR := src/abe/uarch

# ---------- RTL (format / lint) ----------
VERIBLE_FORMAT_FLAGS ?= --inplace --flagfile .verible-format
VERIBLE_LINT_FLAGS   ?= --ruleset=default --rules_config .rules.verible_lint
VERILATOR_LINT_FLAGS ?= --lint-only --default-language 1800-2017 --Wall \
                        -Wno-UNOPTFLAT -Wno-WIDTH -Wno-LITENDIAN --timing
SV2V_FLAGS           ?=
STATIC_OPTS          ?=

# ---------- Synthesis ----------
SYNTH_OUT_DIR ?= out_synth/$(DESIGN)
SYNTH_NET_V    := $(SYNTH_OUT_DIR)/$(DESIGN)_net.v
SYNTH_NET_JSON := $(SYNTH_OUT_DIR)/$(DESIGN)_net.json
SYNTH_STAT_TXT := $(SYNTH_OUT_DIR)/stat_width.txt

# ---------- Formal ----------
FORMAL_OUT_DIR ?= out_formal/$(DESIGN)

# ---------- DV ----------
DV ?= dv
DV_REGRESS ?= dv-regress
DV_REGRESS_ALL ?= dv-regress-all
DV_REPORT ?= dv-report
DV_OUTDIR ?= out_dv
DV_OPTS ?=
DV_REGRESS_OPTS ?=
DV_REGRESS_ALL_OPTS ?=
DV_REPORT_OPTS ?=

# ---------- Docs ----------
MKDOCS ?= $(BIN)/mkdocs

# Expand into an actual file list that tools will consume
# - If PY_SRCS=ALL, use git ls-files (fallback to find)
# - Otherwise expand each space-separated pattern with $(wildcard)
#   (supports: "*.py tests/*.py foo.py")
ifeq ($(strip $(PY_SRCS)),ALL)
  # Detect if we are inside a git repo
  IN_GIT := $(shell git rev-parse --is-inside-work-tree 2>/dev/null || echo no)
  ifeq ($(IN_GIT),true)
    PY_SRCS_RESOLVED := $(shell git ls-files '*.py' '*.pyi')
  else
    # Cross-platform find (BSD/GNU), prune venv
    PY_SRCS_RESOLVED := $(shell find . -type f \( -name '*.py' -o -name '*.pyi' \) ! -path './.venv/*')
  endif
else
  PY_SRCS_RESOLVED := $(strip $(foreach p,$(PY_SRCS),$(wildcard $(p))))
endif

# ---------- Parse srclist.f (files, incdirs, defines) ----------
# Supported in srclist.f (one item per line; relative paths OK):
#   # or // comments
#   +incdir+path        or  -I path
#   +define+NAME=VAL    or  -D NAME=VAL
#   <file>.sv (and other SV headers)
#
# We canonicalize to:
#   SV_FILES      := space-separated file list
#   INC_DIRS      := space-separated include dirs
#   DEFINES_LIST  := space-separated NAME[=VAL] tokens

ifeq ($(wildcard $(SV_SRCLIST)),)
  SV_FILES      := $(SV_SRCS)
  INC_DIRS      :=
  DEFINES_LIST  :=
else
  SV_FILES := $(shell awk '\
    {gsub(/\r/,"")} \
    /^[ \t]*($$|#|\/\/)/{next} \
    /^[ \t]*\+incdir\+/{next} \
    /^[ \t]*-I[ \t]*/{next} \
    /^[ \t]*\+define\+/{next} \
    /^[ \t]*-D[ \t]*/{next} \
    {print $$0}' $(SV_SRCLIST))
  INC_DIRS := $(shell awk '\
    {gsub(/\r/,"")} \
    /^[ \t]*($$|#|\/\/)/{next} \
    /^[ \t]*\+incdir\+/{sub(/^[ \t]*\+incdir\+/,""); gsub(/^[ \t]+|[ \t]+$$/,""); print $$0; next} \
    /^[ \t]*-I[ \t]*/  {sub(/^[ \t]*-I[ \t]*/,"");   gsub(/^[ \t]+|[ \t]+$$/,""); print $$0; next}' $(SV_SRCLIST))
  DEFINES_LIST := $(shell awk '\
    {gsub(/\r/,"")} \
    /^[ \t]*($$|#|\/\/)/{next} \
    /^[ \t]*\+define\+/{sub(/^[ \t]*\+define\+/,""); gsub(/^[ \t]+|[ \t]+$$/,""); print $$0; next} \
    /^[ \t]*-D[ \t]*/  {sub(/^[ \t]*-D[ \t]*/,"");   gsub(/^[ \t]+|[ \t]+$$/,""); print $$0; next}' $(SV_SRCLIST))
endif

# Map canonical lists to per-tool flag styles
INCFLAGS_CC   := $(foreach d,$(INC_DIRS),-I$(d))
DEFFLAGS_CC   := $(foreach d,$(DEFINES_LIST),-D$(d))
INCFLAGS_SV2V := $(foreach d,$(INC_DIRS),--incdir=$(d))
DEFFLAGS_SV2V := $(foreach d,$(DEFINES_LIST),--define=$(d))

.PHONY: vars-clean
vars-clean:
	@echo "Cleaning vars outputs"

.PHONY: clean
clean: vars-clean

.PHONY: vars-test
vars-test:
	@echo "Test vars - not implemented yet"

.PHONY: test
test: vars-test

.PHONY: vars-all
vars-all:
	@echo "All vars - not implemented yet"

.PHONY: all
all: vars-all
