<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/formal.md -->

# Reusable ASIC Designs (RAD) – Formal

## Overview

The **Reusable ASIC Designs (RAD)** environment includes a formal verification
flow built with open‑source tools. Formal verification works together with RAD's
linting, synthesis, and DV flows. It uses math to prove that key safety
properties are correct in each design.

The [RAD Design](design.md) flow checks **structure and synthesis**. The [RAD
Formal](formal.md) flow checks **logic** for *all possible* input sequences.

The RAD Formal methodology focuses on:

- **Practical properties** that match the implementation
- **Small, focused proof harnesses**
- **Reusable SBY templates**
- **Repeatable Make‑based automation**

This document describes a flow that fits naturally *after initial RTL and
design‑side checks* and *before [DV](dv.md) simulation*.

### Audience

- **ASIC RTL designers** adding formal checks to RAD IP
- **Verification engineers** using formal together with simulation
- **Architects** checking safety and corner‑case behavior

### Purpose

- Check that key safety properties work correctly for all legal inputs
- Find corner‑case bugs earlier than simulation
- Provide automated, repeatable proofs that work with Make
- Use the same structure for formal files across all RAD designs

### Key Features

- [SymbiYosys](https://github.com/YosysHQ/sby)‑based flow (`prove` and `cover`)
- Reusable SBY templates for each design
- Standard formal testbench structure
- Open‑source SMT solvers ([Boolector](https://github.com/Boolector/boolector) recommended)
- Make‑based automation for proofs and coverage
- Same directory structure for each `rad_<design>` design

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

```bash
make deps
```

This shows any missing tools. Installation steps depend on your platform and
are not covered in this document.

### Run Examples

```bash
make DESIGN=rad_async_fifo formal
make DESIGN=rad_async_fifo formal-cover
```

### Examine Outputs

- `out_formal/<design>`
- `out_formal/<design>_cover`

### Explore Relevant Directory Layout

```text
.
├── mk
│   ├── 00-vars.mk
│   ├── 10-helpers.mk
│   ├── 20-python.mk
│   ├── 50-formal.mk
├── src
│   └── abe
│       ├── rad
│       │   ├── rad_async_fifo
│       │   │   ├── rtl
│       │   │   │   ├── rad_async_fifo_mem.sv
│       │   │   │   ├── rad_async_fifo_rptr.sv
│       │   │   │   ├── rad_async_fifo_sync.sv
│       │   │   │   ├── rad_async_fifo_wptr.sv
│       │   │   │   ├── rad_async_fifo.sv
│       │   │   │   └── srclist.f
│       │   │   ├── formal
│       │   │   │   ├── rad_async_fifo_cover.sby
│       │   │   │   ├── rad_async_fifo_formal_top.sv
│       │   │   │   └── rad_async_fifo.sby
│       │   ├── shared
│       │   │   ├── rtl
│       │   │   │   ├── rad_pulse_gen.sv
│       │   │   │   └── rad_timescale.svh
├── Makefile
```

---

## Makefiles

Makefiles are in directory `mk`.

- Common flags come from `00-vars.mk`.
- Formal commands are in `50-formal.mk`.

Common commands:

```bash
make formal-help
```

---

## Initial Steps

1. It's helpful to complete design‑side checks first:
   - `rtl-format`
   - `rtl-lint-verible`
   - `rtl-lint-verilator`
   - `synth`
2. Create: `src/abe/rad/rad_<design>/formal`
3. Templates from proven designs like `rad_async_fifo` can serve as a starting point.
4. Review existing formal collateral for examples.

See also: [Formal Verification Flow](#formal-verification-flow) and [Formal
Coverage Flow](#formal-coverage-flow).

---

## Formal Verification Flow

### Formal Testbench: `<design>_formal_top.sv`

Main parts:

- Clock generation using `$global_clock` and `(* gclk *)` (see [FAQ #6](#why-global_clock)).
- Reset sequence for each domain.
- `(* anyseq *)` for free inputs.
- `assume` for legal input conditions (see [FAQ #7](#how-many-assumptions-are-too-many)).
- `assert` for invariants and safety properties.
- `$past()` protected by `past_valid`.

Reference:

```text
src/abe/rad/rad_async_fifo/formal/rad_async_fifo_formal_top.sv
```

See also: [SymbiYosys Configuration](#symbiyosys-configuration-designsby).

---

### [SymbiYosys](https://github.com/YosysHQ/sby) Configuration: `<design>.sby`

Sections:

| Section | Purpose |
|--------|---------|
| `[options]` | Mode (`prove`), depth, multiclock |
| `[engines]` | Solver selection (see [FAQ #4](#which-solvers-should-i-use)) |
| `[script]` | [Yosys](https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/smtbmc.html) steps |
| `[files]` | RTL + formal top |

Reference:

```text
rad_async_fifo/formal/rad_async_fifo.sby
```

See also: [Running Proofs](#running-proofs) and [Formal Coverage Flow](#formal-coverage-flow).

---

### Running Proofs

```bash
make DESIGN=<design> formal
```

**Examine the Output Directory: `out_formal/<design>`**

| File/Directory | Description |
|----------------|-------------|
| `PASS` | Status marker file containing verification statistics and elapsed time |
| `config.sby` | Copy of the `.sby` configuration file used for this run |
| `engine_0/` | Engine-specific outputs including trace files (`.vcd`, `.yw`) for counterexamples |
| `logfile.txt` | Complete [SymbiYosys](https://github.com/YosysHQ/sby) log showing all steps, solver progress, and results |
| `model/` | Intermediate [Yosys](https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/smtbmc.html) files including the SMT2 model and design elaboration logs |
| `<design>.xml` | JUnit-style XML report of verification results |
| `src/` | Copies of all source files used in verification for reproducibility (see [FAQ #8](#why-does-symbiyosys-copy-source-files)) |
| `status` | Human-readable summary of verification status (basecase/induction results) |
| `status.sqlite` | SQLite database with detailed status information |

See also: [FAQ #2](#what-depth-should-i-use) and [FAQ #3](#why-doesnt-induction-work).

---

## Formal Coverage Flow

**Create the Coverage Configuration: `<design>_cover.sby`**

The coverage `.sby` file is almost the same as the
[verification configuration](#symbiyosys-configuration-designsby). The main
difference is in the `[options]` section: use `mode cover` instead of `mode
prove` (see [FAQ #5](#difference-between-formal-and-formal-cover)). Coverage
mode finds traces that meet the `cover` statements in your formal testbench.
This is useful for:

- Creating traces.
- Checking reachability.
- Finding over‑constrained assumptions.

Run:

```bash
make DESIGN=<design> formal-cover
```

Reference:

```text
src/abe/rad/rad_async_fifo/formal/rad_async_fifo_cover.sby
```

---

## FAQ

### Why use formal if simulation passes?

Formal checks *all* legal input sequences. It works together with [simulation
testing](dv.md). It can help find:

- Underflow/overflow.
- Race conditions.
- Reset bugs.
- Multi‑clock hazards.
- Illegal input patterns.

These issues are hard to find with only simulation.

---

### What depth should I use?

Here are some starting values:

- Small modules: **16–40**
- FIFOs & CDC logic: **40–80**
- Handshakes: **20–50**

Increase the depth if induction does not work at first.

---

### Why doesn't induction work?

Check these common causes:

- Reset not modeled correctly.
- Missing assumptions.
- `$past()` guard missing.
- Real bug in the design.
- Long initialization sequences.

Making assumptions simpler or stronger can often fix induction problems.

---

### Which solvers should I use?

- **[Boolector](https://github.com/Boolector/boolector)** (recommended to start).
- [Yices](https://yices.csl.sri.com/) or [Z3](https://github.com/Z3Prover/z3)
can help if Boolector does not support something.

---

### Difference between `formal` and `formal-cover`?

| Mode | Meaning |
|------|---------|
| **prove** | Property must hold always |
| **cover** | Scenario must be reachable |

---

### Why `$global_clock`?

It enables:

- Correct multi‑clock modeling.
- Correct SMT scheduling.
- No need for manual clock generation.

---

### How many assumptions are too many?

Here is a helpful guide:

> Use assumptions for legal *inputs*, not for internal design behavior.

---

### Why does [SymbiYosys](https://github.com/YosysHQ/sby) copy source files?

To make results repeatable.
Each run includes everything:

- RTL.
- formal tops.
- logs.
- SMT model.

---

## References

- [SymbiYosys](https://github.com/YosysHQ/sby)
- [yosys-smtbmc](https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/smtbmc.html)
- [Boolector](https://github.com/Boolector/boolector)

---

## Licensing

See the `LICENSES` directory at the repository root.
