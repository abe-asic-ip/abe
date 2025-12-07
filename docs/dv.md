<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/dv.md -->

# Reusable ASIC Designs (RAD) – Design Verification (DV)

## Overview

The **Reusable ASIC Designs (RAD)** DV environment provides a complete,
reusable, and open‑source verification framework for all RAD designs. It
combines **[cocotb](https://www.cocotb.org)**,
**[pyuvm](https://github.com/pyuvm/pyuvm)**, and a robust set of **shared base
classes**, enabling UVM‑style verification using modern Python tooling.

RAD DV follows the ABE philosophy:

- **Consistency**: All RAD designs use the same structure and DV
  architecture
- **Reusability**: Shared base classes for agents, drivers, monitors,
  sequences, scoreboards, and coverage
- **Automation**: Make targets, regression scripts, auto‑generated benches
- **Portability**: 100% open‑source toolchain
  ([cocotb](https://www.cocotb.org), [Verilator](https://verilator.org),
  [pyuvm](https://github.com/pyuvm/pyuvm),
  [pytest](https://docs.pytest.org/en/stable))

**[RAD Design](design.md)** ensures RTL quality,
**[RAD Formal](formal.md)** ensures logical correctness, and
**[RAD DV](dv.md)** ensures *functional correctness under realistic
stimulus*.

### Audience

- DV engineers building verification environments for new RAD designs
- RTL designers writing tests or debugging failures
- Contributors adding new modules to the RAD library

### Purpose

- Establish consistent DV architecture across all RAD designs
- Explain the shared DV infrastructure, tools, and base classes
- Show how to create a new RAD DV bench
- Document how to run, debug, and extend RAD testbenches

### Key Features

- UVM‑style architecture built on [cocotb](https://www.cocotb.org) + [pyuvm](https://github.com/pyuvm/pyuvm)
- Reusable base class library (agent/driver/monitor/env/sb/coverage)
- Automated regression tools
- Built‑in support for multi‑clock, multi‑agent designs
- Bench template generator (`dv-make-bench`)
- YAML‑driven regressions (`dv-regress`)
- Unified Makefile integration (`make dv`, `make dv-regress`)

---

## Getting Started

### Set Up and Install the Environment

See [ABE Python Development](python_dev.md) for Python environment setup details.

```bash
make py-venv-all
source .venv/bin/activate
make py-install-all
```

### Install Required Tools

Install [Verilator](https://verilator.org) and a waveform viewer such as
[Surfer](https://surfer-project.org) or [GTKWave](https://gtkwave.sourceforge.net).

### Run Examples

A single test:

```bash
dv --design=rad_async_fifo --test=test_rad_async_fifo --waves 1
```

A regression:

```bash
make DESIGN=rad_cdc_sync dv-regress-design
```

All regressions in the repo:

```bash
make dv-regress-all-and-report
```

### Examine Outputs

```text
out_dv/builds/<rad_design>.<hash>/
out_dv/tests/<rad_design>.<hash>.<test>.<seed>
```

### Explore Relevant Directory Layout

```text
.
├── mk
│   ├── 00-vars.mk
│   ├── 10-helpers.mk
│   ├── 20-python.mk
│   ├── 60-dv.mk
├── src
│   └── abe
│       ├── rad
│       │   ├── rad_async_fifo
│       │   │   ├── dv
│       │   │   │   ├── __init__.py
│       │   │   │   ├── dv_regress.yaml
│       │   │   │   ├── rad_async_fifo_coverage.py
│       │   │   │   ├── rad_async_fifo_driver.py
│       │   │   │   ├── rad_async_fifo_env.py
│       │   │   │   ├── rad_async_fifo_item.py
│       │   │   │   ├── rad_async_fifo_monitor_in.py
│       │   │   │   ├── rad_async_fifo_monitor_out.py
│       │   │   │   ├── rad_async_fifo_ref_model.py
│       │   │   │   ├── rad_async_fifo_reset_sink.py
│       │   │   │   ├── rad_async_fifo_sb.py
│       │   │   │   ├── rad_async_fifo_sequence.py
│       │   │   │   ├── README.md
│       │   │   │   └── test_rad_async_fifo.py
│       │   │   └── __init__.py
│       │   ├── rad_template
│       │   │   └── dv
│       │   │       ├── __init__.py
│       │   │       ├── README.md
│       │   │       ├── template_coverage.py
│       │   │       ├── template_driver.py
│       │   │       ├── template_item.py
│       │   │       ├── template_monitor_in.py
│       │   │       ├── template_monitor_out.py
│       │   │       ├── template_ref_model.py
│       │   │       ├── template_sequence.py
│       │   │       └── test_template.py
│       │   ├── shared
│       │   │   ├── dv
│       │   │   │   ├── __init__.py
│       │   │   │   ├── base_agent.py
│       │   │   │   ├── base_clock_driver.py
│       │   │   │   ├── base_clock_mixin.py
│       │   │   │   ├── base_coverage.py
│       │   │   │   ├── base_driver.py
│       │   │   │   ├── base_env.py
│       │   │   │   ├── base_item.py
│       │   │   │   ├── base_monitor_in.py
│       │   │   │   ├── base_monitor_out.py
│       │   │   │   ├── base_monitor.py
│       │   │   │   ├── base_ref_model.py
│       │   │   │   ├── base_reset_driver.py
│       │   │   │   ├── base_reset_item.py
│       │   │   │   ├── base_reset_monitor.py
│       │   │   │   ├── base_reset_sink.py
│       │   │   │   ├── base_sb_comparator.py
│       │   │   │   ├── base_sb_predictor.py
│       │   │   │   ├── base_sb.py
│       │   │   │   ├── base_sequence.py
│       │   │   │   ├── base_sequencer.py
│       │   │   │   ├── base_test.py
│       │   │   │   ├── utils_cli.py
│       │   │   │   └── utils_dv.py
│       │   │   └── __init__.py
│       │   ├── tools
│       │   │   ├── __init__.py
│       │   │   ├── dv_make_bench.py
│       │   │   ├── dv_regress_all.py
│       │   │   ├── dv_regress.py
│       │   │   ├── dv_report.py
│       │   │   ├── dv.py
│       │   │   └── flatten_srclist.sh
│       │   └── __init__.py
├── Makefile
```

---

## Methodology

### Choices

#### Methodology: UVM for Block-Level Verification

UVM provides a proven, standardized methodology that is good for
block-level verification. Cliff Cummings' uvmtb_template paper (see
[Literature](#literature) section) shows how UVM works well for
block-level testbenches.

#### Technology: cocotb/pyuvm over Verilator/SystemVerilog UVM

ABE's open-source mission uses an open-source simulator. When the project
began, [Verilator](https://verilator.org) did not support UVM for
SystemVerilog (it does now). This made
[cocotb](https://www.cocotb.org)/[pyuvm](https://github.com/pyuvm/pyuvm) a
natural choice for combining UVM methodology with open-source simulation.

#### Discipline: UVM Standard Patterns over Python Idioms

Python enables design patterns not possible in SystemVerilog. Standard UVM
does not support these patterns. However, RAD DV uses fewer Python-specific
patterns. This keeps UVM portable and easier to read for engineers who know
SystemVerilog UVM. Exception: small mixins for clock/reset infrastructure
reduce repetitive code without hiding the UVM structure.

### Benefits

#### Python Reference Models

Traditional UVM testbenches implement reference models in SystemVerilog or
C++ (via DPI-C). Using Python with SystemVerilog simulators is very
difficult. This creates several challenges:

- **The translation gap**: ASIC architects often develop specifications and
  models in Python. Verification engineers must rewrite them in
  SystemVerilog or C++ for use in UVM scoreboards
- **Maintenance creates errors**: Keeping reference models synchronized with
  changing Python specifications causes translation errors and extra
  maintenance work
- **Missed reuse opportunities**: Python's powerful features and extensive
  libraries (NumPy, SciPy, etc.) cannot be used for behavioral modeling in
  traditional UVM

RAD DV solves these problems by allowing reference models to be written
directly in Python with the testbench:

- Architects' Python specifications can often be used directly as reference
  models with small changes
- Model mismatches are greatly reduced because there is no translation
  layer
- Debug time can decrease—the Wilson Research Group Functional Verification
  Study reports that debugging is a significant portion of verification
  effort

#### Rich Python Ecosystem

Open-source simulators like [Verilator](https://verilator.org) and
[Icarus Verilog](https://steveicarus.github.io/iverilog) provide basic
simulation capabilities. They do not have the integrated test management,
analysis, and debugging tools found in commercial products. Python's
ecosystem fills this gap and gives open-source developers access to similar
capabilities:

- **Test management**: [pytest](https://docs.pytest.org/en/stable) for test
  discovery, parametrization, fixtures, and regression orchestration
- **Data analysis**: NumPy, pandas for processing results, analyzing
  coverage trends, and generating metrics
- **Visualization**: Matplotlib, seaborn for plotting coverage data,
  regression trends, and performance metrics
- **Debugging and introspection**: Interactive debugging and comprehensive
  logging for development and debug workflows
- **Automation and CI/CD**: Direct integration with git, reporting tools,
  and continuous integration pipelines

### Known Limitations

- **Simulator support**: Only [Verilator](https://verilator.org) and
  [Icarus Verilog](https://steveicarus.github.io/iverilog) are currently
  supported. While [cocotb](https://www.cocotb.org) supports many
  commercial simulators (VCS, Questa, Xcelium, etc.), integration into RAD
  DV requires access to licenses for testing and validation.
- **Sequential test execution**: Regression tests run one at a time instead
  of in parallel. This makes large test suites run slower
- **Third-party VIP integration**: Does not integrate with commercial VIP
  or third-party AIP

### Future Enhancements

- **Additional simulator support**: Expand beyond
  [Verilator](https://verilator.org) and
  [Icarus Verilog](https://steveicarus.github.io/iverilog)
- **Parallel test execution**: Enable concurrent test runs for faster
  regression completion
- **Multi-agent single-clock example**: Example bench demonstrating single
  clock/reset domain with multiple agents (multiple interfaces)
- **Code coverage integration**: Example using
  [Verilator](https://verilator.org)'s coverage capabilities
- **Constrained randomization**: Example using
  [cocotb-coverage](https://github.com/mciepluc/cocotb-coverage) for
  constraint-based stimulus generation
- **Functional coverage workflows**: Examples demonstrating coverage
  database merging, cross-coverage, and coverage-driven verification
- **Standard protocol libraries**: Pre-built reusable agents for common bus
  protocols (AXI, APB, AHB, etc.)

---

## Makefiles

Makefiles are in directory `mk`

- Common flags come from `00-vars.mk`.
- Python commands are in `20-python.mk`.
- DV commands are in `mk/60-dv.mk`.

Common commands:

```bash
make py-help
make dv-help
```

---

## RAD DV Architecture

Located under:

```text
src/abe/rad/shared/dv/
```

RAD DV environments use classic UVM patterns implemented in Python via
[pyuvm](https://github.com/pyuvm/pyuvm) and [cocotb](https://www.cocotb.org).
All testbenches inherit from reusable base classes that provide standard
verification infrastructure.

The following table summarizes the shared base classes. See the module
docstrings for detailed usage.

| File | Description |
|------|-------------|
| `base_agent.py` | UVM agent connecting sequencer, driver, and separate input/output monitors |
| `base_clock_driver.py` | Clock generation component with configurable period, phase, and startup delay |
| `base_clock_mixin.py` | Shared clock configuration, signal binding, and drive edge alignment utilities |
| `base_coverage.py` | Functional coverage subscriber integrating [cocotb-coverage](https://github.com/mciepluc/cocotb-coverage) with [pyuvm](https://github.com/pyuvm/pyuvm) |
| `base_driver.py` | UVM driver with clock synchronization, reset handling, and BFM hooks |
| `base_env.py` | Top-level environment creating agents, coverage, scoreboard, and reset infrastructure |
| `base_item.py` | Transaction item with input/output field separation, cloning, and comparison |
| `base_monitor.py` | Base monitor with clock synchronization and analysis port infrastructure |
| `base_monitor_in.py` | Design input monitor sampling at rising edge using ReadOnly trigger |
| `base_monitor_out.py` | Design output monitor sampling in read-only phase before next active edge |
| `base_ref_model.py` | Reference model computing expected design behavior from input transactions |
| `base_reset_driver.py` | Reset generation with configurable polarity, duration, and settling time |
| `base_reset_item.py` | Reset transaction capturing raw signal level and polarity-resolved state |
| `base_reset_monitor.py` | Reset monitor publishing transactions on reset signal changes |
| `base_reset_sink.py` | Subscriber forwarding reset events to driver and predictor components |
| `base_sb.py` | Top-level scoreboard managing predictor and comparator components |
| `base_sb_comparator.py` | Dual-FIFO comparator for expected vs actual transaction checking |
| `base_sb_predictor.py` | Predictor generating expected transactions using reference model |
| `base_sequence.py` | Item-generating sequence with factory support and customization hooks |
| `base_sequencer.py` | Standard UVM sequencer managing sequence scheduling and driver connection |
| `base_test.py` | Base test with configuration management, factory overrides, and phase execution |
| `utils_cli.py` | CLI utilities for reading environment variables, plusargs, and factory overrides |
| `utils_dv.py` | Type-safe config_db wrappers, signal handle utilities, and logger configuration |

---

## Structure of a RAD DV Bench

Core files required in every bench:

```text
rad_<design>/dv/
├── __init__.py
├── dv_regress.yaml
├── rad_<design>_coverage.py
├── rad_<design>_driver.py
├── rad_<design>_item.py
├── rad_<design>_monitor_in.py
├── rad_<design>_monitor_out.py
├── rad_<design>_ref_model.py
├── rad_<design>_sequence.py
├── README.md
└── test_rad_<design>.py
```

Additional files for complex designs:

```text
rad_<design>/dv/
├── rad_<design>_env.py          # Custom environment (multi-agent, etc.)
├── rad_<design>_reset_sink.py   # Custom reset routing
└── rad_<design>_sb.py           # Custom scoreboard logic
```

**Note:** The test file should have the prefix `test_` for pytest discovery.

---

## DV Tools

The RAD DV environment includes five main tools under:

```text
src/abe/rad/tools/
```

The following sections describe the tools at a high level. See the module
docstrings for more detail.

### 1. `dv` — Main Front-End (Runs a Single Test)

#### `dv` Purpose

- Verify RTL designs using [cocotb](https://www.cocotb.org) +
  [pyuvm](https://github.com/pyuvm/pyuvm) +
  [pytest](https://docs.pytest.org/en/stable) framework
- Support multiple simulators ([Verilator](https://verilator.org),
  [Icarus Verilog](https://steveicarus.github.io/iverilog)) with configurable
  waveform generation (FST, VCD)
- Execute single or multi-seed regression testing with automatic result
  tracking
- Generate test manifests for build/test reproducibility and caching
- Provide flexible build/test orchestration via `--cmd` (build-only,
  test-only, or both)

#### `dv` Typical Usage

```bash
dv --design=rad_async_fifo --test=test_rad_async_fifo --seed=1999
make DESIGN=rad_async_fifo TEST=test_rad_async_fifo DV_OPTS='-seed=123' dv
```

#### `dv` Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--cmd` | choice | No | `both` | Run only build, only test, or both (choices: build, test, both) |
| `--sim` | choice | No | `verilator` | Simulator to use (choices: verilator, icarus) |
| `--outdir` | string | No | `out_dv` | Output directory for build and test artifacts |
| `--verbosity` | choice | No | `info` | Logging level for Python/pyuvm/cocotb (choices: critical, error, warning, info, debug, notset) |
| `--waves` | choice | No | `0` | Enable waveform generation (choices: 0, 1) |
| `--waves_fmt` | choice | No | `fst` | Waveform format (choices: fst, vcd) |
| `--design` | string | Yes | - | Design to build (e.g., rad_async_fifo) |
| `--build-force` | flag | No | `False` | Force a rebuild even if build directory exists |
| `--build-arg` | string | No | - | Extra build argument passed verbatim to the simulator (repeatable, e.g., --build-arg=-DSIMULATE_METASTABILITY) |
| `--test` | string | Yes* | - | Test module name in format abe.rad.\<rad_design\>.dv.\<test_module\> (required for test/both commands) |
| `--expect` | choice | No | `PASS` | Expected test result for reporting (choices: PASS, FAIL) |
| `--seeds` | list | No | - | Explicit seed list (decimal or 0x...). Overrides --nseeds |
| `--nseeds` | int | No | `0` | Generate N random seeds if --seeds not given |
| `--seed-base` | int | No | `1999` | Base seed for generating additional seeds |
| `--seed-out` | path | No | - | Write the final seed list to a file (one per line) |
| `--check-en` | choice | No | `1` | Enable checkers (choices: 0, 1) |
| `--coverage-en` | choice | No | `1` | Enable coverage collection (choices: 0, 1) |

#### `dv`  Build Outputs

Output directory:

```text
<outdir>/builds/<rad_design>.<hash>
```

The hash is a 10-character SHA-1 fingerprint computed from build-affecting
parameters: simulator type, waveform settings (enabled/format), and user build
arguments. This ensures identical build configurations reuse the same directory
while different configurations get separate builds.

Key files:

| File | Description |
|------|-------------|
| `build.log` | Complete build log from the simulator (Verilator/Icarus) |
| `manifest.json` | Build metadata including status (started/built/failed), timestamp, simulator config, waveform settings, build arguments, and fingerprint for reproducibility |
| `srclist.abs.f` | Absolutized source file list with include paths, generated from the design's rtl/srclist.f |

#### `dv`  Test Outputs

Output directory:

```text
<outdir>/tests/<build-dir-name>.<test>.<seed>
```

Key files:

| File | Description |
|------|-------------|
| `test.log` | Complete test execution log including cocotb/pyuvm output |
| `manifest.json` | Test result metadata including status (PASS/FAIL), expected result, duration, replay command, build/test directories, and full context snapshot |
| `waves.fst` or `waves.vcd` | Waveform file (if `--waves=1`) in the specified format |

---

### 2. `dv-regress` — YAML‑Driven Regression Runner

#### `dv-regress` Purpose

- Execute YAML-defined regression test suites with strict configuration management
- Apply global default arguments to all jobs with per-job override capability
- Run multiple test jobs one at a time with automatic pass/fail tracking
- Generate colored summary reports with copy-pasteable replay commands for
failed tests
- Let `dv` handle seeds for consistent multi-seed support

#### `dv-regress` Typical Usage

```bash
dv-regress --file=src/abe/rad/rad_cdc_sync/dv/dv_regress.yaml
make DESIGN=rad_cdc_sync dv-regress-design
```

#### `dv-regress` Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--file` | path | Yes | - | Path to dv_regress.yaml configuration file |
| `--outdir` | string | No | `out_dv` | Output directory for build and test artifacts |

---

### 3. `dv-regress-all` — Run All RAD Regressions

#### `dv-regress-all` Purpose

Searches all directories for `dv_regress.yaml` files in the repository and runs
each regression using `dv-regress`. All regressions share the same output
directory for unified result tracking.

#### `dv-regress-all` Typical Usage

```bash
dv-regress-all
make dv-regress-all
```

#### `dv-regress-all` Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--roots` | list | No | `[.]` | Root directories to scan for dv_regress.yaml files (can specify multiple) |
| `--outdir` | string | No | `out_dv` | Output directory for build and test artifacts |

---

### 4. `dv-report` — Summaries & Reporting

#### `dv-report` Purpose

Scans test output directories for manifest files and generates an organized
report of expected/unexpected passes and failures with copy-pasteable replay commands.

#### `dv-report` Typical Usage

```bash
dv-report
make dv-report
```

#### `dv-report` Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--outdir` | string | No | `out_dv` | Output directory to scan for test results |

---

### 5. `dv-make-bench` — Auto‑Generate a New DV Bench

Creates a new bench from the template in `src/abe/rad/rad_template/dv`.

#### `dv-make-bench` Purpose

- Generate complete testbench directory structure from template for new designs
- Use consistent naming across snake_case, PascalCase, and UPPER_CASE contexts
- Insert copyright headers with specified author and year
- Clean up template-specific directives for production-ready code
- Run static analysis tools on generated files to find remaining FIXME items

#### `dv-make-bench` Typical Usage

```bash
dv-make-bench <rad_design> 'George Nakashima'
```

#### `dv-make-bench` Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `module_name` | string | Yes | - | Module name (e.g., 'rad_async_fifo' or 'RadAsyncFifo') - converted to appropriate case as needed |
| `author` | string | Yes | - | Author name for copyright headers |
| `--year` | int | No | Current year | Year for copyright headers |
| `--force` | flag | No | `False` | Overwrite existing directory if it exists |

---

## Regression Guidelines

The `dv_regress.yaml` file defines regression test jobs using YAML. Each bench
includes this file to enable `dv-regress` execution.

### Schema

```yaml
# Optional: Global defaults applied to all jobs
defaults:
  args: ["--sim=verilator", "--waves=0"]

# Required: List of test jobs
jobs:
  - name: <job_name>
    args: ["--design=...", "--test=...", "--nseeds=N", ...]
  - name: <job_name2>
    args: "--design=... --test=..."  # Single string also supported
```

### Job Arguments

Each job's `args` can be:

- **List of strings**: `["--design=rad_foo", "--test=test_rad_foo"]`
- **Single string**: `"--design=rad_foo --test=test_rad_foo"`

Arguments are passed directly to `dv`, supporting all `dv` command-line options
(see [`dv` Arguments](#dv-arguments) table).

### Common Patterns

**Basic regression with multiple seeds:**

```yaml
jobs:
  - name: base
    args:
      - --design=rad_async_fifo
      - --test=test_rad_async_fifo
      - --nseeds=10
      - --seed-base=1999
```

**Multiple configurations:**

```yaml
jobs:
  - name: normal
    args:
      - --design=rad_cdc_sync
      - --test=test_rad_cdc_sync
      - --nseeds=2
      - --seed-base=1999

  - name: metastability_simulation
    args:
      - --design=rad_cdc_sync
      - --test=test_rad_cdc_sync
      - --build-arg=-DSIMULATE_METASTABILITY
      - --nseeds=2
      - --seed-base=12345
      - --check-en=0
```

**Expected failures (negative testing):**

```yaml
jobs:
  - name: expect_fail
    args:
      - --design=rad_cdc_sync
      - --test=test_rad_cdc_sync
      - --build-arg=-DSIMULATE_METASTABILITY
      - --nseeds=2
      - --seed-base=67890
      - --expect=FAIL
```

**Using global defaults:**

```yaml
defaults:
  args:
    - --sim=verilator
    - --waves=0
    - --nseeds=5

jobs:
  - name: job1
    args: ["--design=rad_foo", "--test=test_rad_foo"]
  - name: job2
    args: ["--design=rad_bar", "--test=test_rad_bar", "--nseeds=10"]  # Overrides default
```

### Guidelines

1. **Job names**: Use descriptive names for easy identification in reports
2. **Required args**: Each job needs to specify `--design` and `--test`
3. **Seeds**: Use `--nseeds` for random seeds or `--seeds` for explicit values
4. **Build variants**: Use `--build-arg` for RTL compilation flags
5. **Defaults**: Use global defaults to reduce repetition across jobs
6. **Job args override defaults**: Per-job arguments take precedence over
global defaults

#### Example Files

See existing regression files for reference:

- `src/abe/rad/rad_async_fifo/dv/dv_regress.yaml` - Simple single-job regression
- `src/abe/rad/rad_cdc_sync/dv/dv_regress.yaml` - Multiple configurations
including negative tests
- `src/abe/rad/rad_cdc_mcp/dv/dv_regress.yaml` - Basic pattern

---

## Verifying a New RAD Design

### 1. Create a Bench from a Suitable Template

Choose a starting point based on your design's characteristics:

| Template | Clocks | Agents | Best For |
|----------|--------|--------|----------|
| `dv-make-bench` | 1 | 1 | Common single-clock designs with registered outputs |
| `rad_cdc_sync` | 1 | 1 | Single-clock pipelines |
| `rad_cdc_mcp` | 2 | 2 | Dual-clock handshake protocols (both domains registered) |
| `rad_async_fifo` | 2 | 2 | Dual-clock designs with combinational outputs |

#### Single-Clock Designs

For designs with a single clock/reset domain and a single agent:

1. Run `dv-make-bench <module_name> '<Author Name>'` to generate the template
2. Replace all `NotImplementedError` and `FIXME` markers with design-specific logic
3. Reference `rad_cdc_sync` bench for implementation examples

#### Multi-Clock / Multi-Agent Designs

For designs with multiple independent clock domains or requiring separate
agents per domain:

1. Copy the bench most similar to your design (`rad_cdc_mcp` or `rad_async_fifo`)
2. Rename all files and classes to match your design
3. Customize the agent count, clock configurations, and reset routing in the
environment and test classes.
4. See the README.md files in these benches for dual-agent architecture patterns

#### Output Timing Considerations

How you implement monitors depends on output timing and protocol complexity:

- **Simple registered outputs**: Use `BaseMonitorOut` directly
    - Example: `rad_cdc_sync` - output updates same cycle, sampled at standard timing

- **Pipelined registered outputs**: Extend `BaseMonitorOut` with cycle tracking
    - Example: `rad_cdc_mcp` - `bdata` updates one cycle after `bload && bvalid`
    - Monitor uses `_prev_load_pending` to track when valid data is available
    - Only emits transactions when actual data transfer completes

- **Conditional sampling**: Override `run_phase()` to filter transactions
    - Examples: Both `rad_async_fifo` and `rad_cdc_mcp`
    - Only send transactions to analysis port when transfer conditions are met
    - Prevents scoreboard from checking invalid/idle cycles

Most simple designs have registered outputs and can use `BaseMonitorOut`
unchanged. For pipelined protocols or conditional sampling, reference the
existing benches for patterns.

### 2. Implement Core Components

Customize these design-specific files:

- **Item** (`rad_<design>_item.py`): Define input and output fields
    - Implement `_in_fields()` and `_out_fields()` methods
    - Add any design-specific constraints or configuration parameters

- **Driver** (`rad_<design>_driver.py`): Drive design inputs with proper timing
    - Set `initial_dut_input_values` for reset state
    - Implement `drive_item()` to apply transactions on drive edges
    - Handle backpressure or protocol requirements

- **Monitors** (`rad_<design>_monitor_in.py`, `rad_<design>_monitor_out.py`):
Observe design signals
    - Input monitor: Sample inputs for reference model
    - Output monitor: Sample outputs for scoreboard comparison
    - Implement `sample_dut()` to capture signal values

- **Reference Model** (`rad_<design>_ref_model.py`): Compute expected behavior
    - Implement `calc_exp()` to predict design outputs from inputs
    - Maintain internal state matching design behavior
    - Handle `reset_change()` for proper state initialization

- **Sequence** (`rad_<design>_sequence.py`): Generate stimulus patterns
    - Implement `set_item_inputs()` to randomize or set input field values
    - Configure sequence length via `RAD_<DESIGN>_SEQ_LEN` environment variable

- **Coverage** (`rad_<design>_coverage.py`): Define functional coverage
    - Use `@CoverPoint` decorators from [cocotb-coverage](https://github.com/mciepluc/cocotb-coverage)
    - Implement `write()` method to sample coverage from transactions

### 3. Develop Tests

All tests need to:

1. Inherit from `BaseTest`
2. Implement `set_factory_overrides()` to register design-specific components
3. Use `@pyuvm.test()` decorator

**Single-clock example:**

```python
@pyuvm.test()
class RadCdcSyncBaseTest(BaseTest):
    """Execute basic RadCdcSync test."""

    def set_factory_overrides(self) -> None:
        override = pyuvm.uvm_factory().set_type_override_by_type
        override(BaseCoverage, RadCdcSyncCoverage)
        ...
```

**Multi-clock example:**

For designs with multiple clocks/resets, create clock and reset drivers in the
test. Reference `rad_cdc_mcp` and `rad_async_fifo`.

### 4. Create Regression Configuration

Add `dv_regress.yaml` to define test jobs (see [Regression Guidelines](#regression-guidelines)).

### 5. Run & Debug

**Run single test:**

```bash
dv --design=rad_<design> --test=test_rad_<design> --waves=1
```

**View waveforms:**

```bash
surfer out_dv/tests/rad_<design>.*/waves.fst
```

**Run regression:**

```bash
make DESIGN=rad_<design> dv-regress-design
```

**Evaluate coverage:**

Current RAD examples use simple counters logged during `report_phase()`. Check
test logs for coverage summaries:

```bash
grep -A5 "Coverage summary" out_dv/tests/*/test.log
```

**Note:** The `BaseCoverage` class supports
[cocotb-coverage](https://github.com/mciepluc/cocotb-coverage) with
`@CoverPoint` decorators for database-driven coverage collection and merging.
To use this feature:

1. Import decorators: `from cocotb_coverage.coverage import CoverPoint, CoverCross`
2. Decorate the `sample()` method with coverpoints
3. Set `COV_YAML=path/to/output.yaml` to export coverage database
4. Use `coverage_db` API for merging and reporting across multiple test runs

**Debug tips:**

- Enable verbose logging: `--verbosity=debug`
- Check test log: `out_dv/tests/<test_dir>/test.log`
- Review manifest: `out_dv/tests/<test_dir>/manifest.json`
- Use `self.logger.debug()` in components for detailed tracing

### 6. Document

Complete the bench documentation:

- **Module docstrings**: Explain purpose and usage of each component
- **README.md**: Architecture, design rationale, protocol details, examples
- **dv_regress.yaml**: Add descriptive job names and comments for complex configurations

---

## FAQ

### Can I use RAD DV with commercial simulators?

Yes, with caveats:

- [cocotb](https://www.cocotb.org) supports VCS, Questa, Xcelium, and others
- RAD DV tools (`dv`, `dv-regress`) currently only configure
[Verilator](https://verilator.org) and [Icarus Verilog](https://steveicarus.github.io/iverilog)
- Extending to commercial simulators requires license access for testing

The testbench code itself is simulator-agnostic.

---

### Why do regression tests run sequentially instead of in parallel?

Parallel execution is a [future enhancement](#future-enhancements). For faster
regressions, consider:

- Running multiple `dv-regress` instances on different machines
- Reducing `--nseeds` for smoke testing
- Using `--cmd=test` to skip redundant rebuilds

---

### Why use UVM methodology with Python instead of pure cocotb?

UVM provides:

- **Proven patterns** for testbench architecture
- **Standardized components** (agents, scoreboards, coverage)
- **Familiar structure** for verification engineers
- **Reusability** across designs through base classes

Pure [cocotb](https://www.cocotb.org) is excellent for simple testbenches. For
complex block-level verification, RAD DV benefits from UVM's structural framework.

---

### Can I use SystemVerilog assertions with RAD DV?

Yes. SVA assertions in RTL are fully supported by
[Verilator](https://verilator.org) and
[Icarus Verilog](https://steveicarus.github.io/iverilog). They complement the
Python testbench by checking protocol compliance and design constraints at the
RTL level. See also [RAD Formal](formal.md) for property-based verification.

---

### Why separate monitors for inputs and outputs?

This mirrors UVM best practices:

- **Input monitors** capture stimulus for the reference model
- **Output monitors** capture design responses for checking
- **Clean separation** enables independent sampling and timing
- **Reusability** across different verification strategies

See Cliff Cummings' "Applying stimulus and sampling outputs" paper
([Literature](#literature) section).

---

### How do I debug a failing test?

1. **Check the test log**: `out_dv/tests/<test_dir>/test.log`
2. **Enable verbose logging**: `dv --design=<design> --test=<test> --verbosity=debug`
3. **View waveforms**: `dv --design=<design> --test=<test> --waves=1`, then
`surfer out_dv/tests/*/waves.fst`
4. **Add debug logging**: Use `self.logger.debug()` in components
5. **Check manifest**: Review `out_dv/tests/<test_dir>/manifest.json` for test configuration

---

### When should I use multiple agents?

Use multiple agents when:

- **Independent clock domains** (e.g., `rad_async_fifo`, `rad_cdc_mcp`)
- **Separate interfaces** with independent protocols
- **Different timing domains** require isolated control

Single agent is sufficient for:

- **Single clock domain** designs
- **Simple pipelines** (e.g., `rad_cdc_sync`)

---

### Why doesn't my reference model match the design?

Common issues:

- **Reset initialization**: Ensure reference model resets in `reset_change()`
- **Timing**: Check that monitors sample at correct clock edges
- **Pipeline delays**: Account for design latency in reference model
- **Edge cases**: Verify reference model handles corner cases (empty, full, etc.)

Add debug logging to both reference model and monitors to trace mismatches.

---

### How do I add a new test to an existing bench?

1. **Add test function** to `test_<design>.py` with `@pyuvm.test()` decorator
2. **Inherit from BaseTest** or existing test class
3. **Override `set_factory_overrides()`** if using custom components
4. **Add to regression**: Update `dv_regress.yaml` with new job

---

## References

- [Universal Verification Methodology (UVM) 1.2 User’s Guide](https://www.accellera.org/images/downloads/standards/uvm/uvm_users_guide_1.2.pdf)
- [UVM Class Reference Manual, Version 1.2](https://www.accellera.org/images/downloads/standards/uvm/UVM_Class_Reference_Manual_1.2.pdf)
- [cocotb](https://www.cocotb.org)
- [pyuvm](https://github.com/pyuvm/pyuvm)
- [pytest](https://docs.pytest.org/en/stable)
- [Verilator](https://verilator.org)
- [Icarus Verilog](https://steveicarus.github.io/iverilog)
- [Surfer](https://surfer-project.org)
- [GTKWave](https://gtkwave.sourceforge.net)
- [cocotb-coverage](https://github.com/mciepluc/cocotb-coverage)

---

## Literature

[1] R. Salemi, *Python for RTL Verification: A Complete Course in Python,
cocotb, and pyuvm*. Boston, MA: Boston Light Press, 2022.

[2] B. Hunter, *Advanced UVM*. North Charleston, SC: CreateSpace
Independent Publishing Platform, 2016.

[3] C. E. Cummings, "uvmtb_template files—An efficient and rapid way to
create UVM testbenches," in *Proc. Synopsys Users Group (SNUG)*, Silicon
Valley, CA, 2025.

[4] C. E. Cummings, "Applying stimulus and sampling outputs—UVM
verification testing techniques," in *Proc. Synopsys Users Group (SNUG)*,
Austin, TX, 2016.

[5] C. E. Cummings, "OVM/UVM scoreboards—Fundamental architectures," in
*Proc. Synopsys Users Group (SNUG)*, Silicon Valley, CA, 2013.

[6] C. E. Cummings, "The OVM/UVM factory and factory overrides—How they
work and why they are important," in *Proc. Synopsys Users Group (SNUG)*,
San Jose, CA, 2012.

[7] C. E. Cummings and T. Fitzpatrick, "OVM and UVM techniques for
terminating tests," in *Proc. Design and Verification Conf. (DVCon)*, San
Jose, CA, 2011.

---

## Licensing

See the `LICENSES` directory at the repository root.
