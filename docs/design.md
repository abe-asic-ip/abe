<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/design.md -->

# Reusable ASIC Designs (RAD) – Design

## Overview

The **Reusable ASIC Designs (RAD)** environment provides a consistent, high‑quality foundation for building reusable SystemVerilog IP within the **ABE** project. **RAD focuses on RTL quality**. RAD helps designs achieve:

- **Consistency** across modules
- **Clean structure** for simulation, lint, formal, and synthesis
- **Compatibility** with open‑source tools
- **Readiness** for verification

This document describes the **design workflow**. It covers what happens *after writing RTL* and *before [formal verification](formal.md) and [DV](dv.md)*.

### Audience

- **ASIC architects and RTL designers** producing reusable IP

### Purpose

- Establish consistent design conventions
- Ensure RTL correctness before formal verification or DV
- Provide standard flows for formatting, linting, and synthesis
- Speed up adding new designs to the RAD library

### Key Features

- Unified Make targets for [RTL formatting](#rtl-formatting-with-verible), [linting](#rtl-linting-with-verible), and [synthesis](#synthesis-flow)
- [Verible](https://github.com/chipsalliance/verible)‑based SystemVerilog formatting and linting
- [Verilator](https://verilator.org)‑based SystemVerilog linting
- [Yosys](https://github.com/YosysHQ/yosys)‑based synthesis flow (via [sv2v](https://github.com/zachjs/sv2v))
- Standardized [directory structure](#directory-structure) and naming
- Reusable [shared components](#timescale-and-shared-headers) under `rad/shared`

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

Run:

```bash
make deps-design
```

This prints any missing host‑side tools. Installation is platform‑specific and outside the scope of this document.

### Run Examples

```bash
make DESIGN=rad_async_fifo rtl-format
make DESIGN=rad_async_fifo rtl-lint-verible
make DESIGN=rad_async_fifo rtl-lint-verilator
make DESIGN=rad_async_fifo synth
make DESIGN=rad_async_fifo synth-report
```

### Examine Outputs

- `rtl-*` targets print to the console
- `synth` writes results to `out_synth/<design>/`

### Explore Relevant Directory Layout

```text
.
├── mk
│   ├── 00-vars.mk
│   ├── 10-helpers.mk
│   ├── 20-python.mk
│   ├── 30-rtl.mk
│   ├── 40-synth.mk
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
│       │   ├── shared
│       │   │   ├── rtl
│       │   │   │   ├── rad_pulse_gen.sv
│       │   │   │   └── rad_timescale.svh
├── Makefile
```

---

## Makefiles

Makefiles are in directory `mk`

- Common flags come from `00-vars.mk`.
- RTL commands are in `30-rtl.mk`.
- [Synthesis](#synthesis-flow) commands are in `40-synth.mk`.

Common commands:

```bash
make rtl-help
make synth-help
```

---

## Guidelines for Creating New RAD RTL Designs

These guidelines help maintain consistency and tooling compatibility across the RAD library:

### Directory Structure

Create designs under:

```text
src/abe/rad/rad_<design>/rtl/
```

Example:

```text
src/abe/rad/rad_async_fifo/rtl/
```

### File Naming

RTL filenames should begin with:

```text
rad_<design>*
```

This naming pattern helps tools find files automatically and keeps designs organized.

### Source List File

Each design includes:

```text
src/abe/rad/rad_<design>/rtl/srclist.f
```

This file lists:

- SystemVerilog source files
- Include directories
- Compile-time defines

Every tool ([Verilator](https://verilator.org), [Verible](https://github.com/chipsalliance/verible), [sv2v](https://github.com/zachjs/sv2v), [Yosys](https://github.com/YosysHQ/yosys), DV) uses the same `srclist.f`.

### Timescale And Shared Headers

RTL should include the shared timescale:

```systemverilog
`include "rad_timescale.svh"
```

Consider using reusable components from:

```text
src/abe/rad/shared/rtl
```

This avoids reimplementing utilities such as:

- Pulse generators
- Synchronizers
- Common CDC helpers

### Clock and Reset Naming

For designs with a single clock and reset:

- Name the clock `clk`
- Use an active-low reset named `rst_n`

The DV base classes assume these names, minimizing verification effort. This convention also maintains consistency across all RAD IP.

### Reference Design

`rad_async_fifo` is a complete example. It shows the recommended [directory structure](#directory-structure), conventions, and Make integration.

---

## Static RTL Tools

### RTL Formatting With Verible

Formatting makes code uniform and easy to read.

- Uses **[Verible](https://github.com/chipsalliance/verible)**
- Configured in `.verible-format`

Run:

```bash
make DESIGN=<design> rtl-format
```

### RTL Linting With Verible

[Verible](https://github.com/chipsalliance/verible) catches:

- Style and naming issues
- Structural problems
- Common SystemVerilog pitfalls

Run:

```bash
make DESIGN=<design> rtl-lint-verible
```

### RTL Linting With Verilator

[Verilator](https://verilator.org) checks for deeper issues:

- Type mismatches
- Unsupported constructs
- Missing signals
- Simulation readiness

Run:

```bash
make DESIGN=<design> rtl-lint-verilator
```

[Verilator](https://verilator.org) linting is important because RAD DV uses [Verilator](https://verilator.org) as the default simulator.

---

## Synthesis Flow

[Yosys](https://github.com/YosysHQ/yosys) synthesis checks that designs can be synthesized and provides statistics.

### End‑to‑End Flow

1. **[sv2v](https://github.com/zachjs/sv2v)** converts SystemVerilog → Verilog
2. **[Yosys](https://github.com/YosysHQ/yosys)** synthesizes the Verilog
3. Reports are written to:

```text
out_synth/<design>/
```

### Invoke Synthesis

```bash
make DESIGN=<design> synth
```

### Examine Synthesis Outputs

| File | Description |
|------|-------------|
| `<design>.v` | sv2v converted Verilog |
| `<design>_net.v` | Gate-level netlist |
| `<design>_net.json` | Structural JSON netlist |
| `stat_width.txt` | Wire/port/cell counts |
| `yosys.log` | Full synthesis log |

### View Statistics

```bash
make DESIGN=<design> synth-report
```

### Graph Visualization

```bash
make DESIGN=<design> synth-dot
```

Creates:

```text
out_synth/<design>/<design>.dot
```

This graph helps you understand how modules connect.

---

## FAQ

### Should I run [Verible](https://github.com/chipsalliance/verible) before checking in RTL?

**Yes.** RAD uses consistent formatting across all designs. Run:

```bash
make DESIGN=<design> rtl-format
```

See [RTL Formatting](#rtl-formatting-with-verible) for details.

---

### Why does [Verilator](https://verilator.org) catch errors that [Verible](https://github.com/chipsalliance/verible) misses?

[Verilator](https://verilator.org) checks **meaning** (like a compiler).
[Verible](https://github.com/chipsalliance/verible) checks **structure and style**.
They work together to find different types of errors.

See [RTL Linting – Verible](#rtl-linting-with-verible) and [RTL Linting – Verilator](#rtl-linting-with-verilator) for details.

---

### Should every RAD design go through synthesis?

Yes. Running synthesis early has several benefits:

- Verifies the design can be synthesized
- Catches issues linters may miss
- Helps avoid problems later in [formal verification](formal.md) or [DV](dv.md)

See [Synthesis Flow](#synthesis-flow) for details.

---

### Why does synthesis use [sv2v](https://github.com/zachjs/sv2v)?

[Yosys](https://github.com/YosysHQ/yosys) provides excellent Verilog support. `sv2v` enables consistent conversion from SystemVerilog to Verilog, allowing us to use [Yosys](https://github.com/YosysHQ/yosys) effectively.

See [End‑to‑End Flow](#endtoend-flow) for details.

---

### What if my module needs vendor-specific cells?

Wrap vendor cells in SystemVerilog wrappers.
This keeps the RAD synthesis flow open‑source and portable.

---

### Can I add custom lint rules?

Yes. Edit:

- `.rules.verible_lint` for [Verible](https://github.com/chipsalliance/verible)
- `00-vars.mk` for [Verilator](https://verilator.org) flags

---

### Why separate design, formal, and DV directories?

Separate directories provide:

- Independent Make flows
- Reproducible builds
- Clean organization

See [RAD Formal](formal.md) and [RAD DV](dv.md) for details on those flows.

---

## References

- [Verible](https://github.com/chipsalliance/verible)
- [Verilator](https://verilator.org)
- [Yosys](https://github.com/YosysHQ/yosys)
- [sv2v](https://github.com/zachjs/sv2v)

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
