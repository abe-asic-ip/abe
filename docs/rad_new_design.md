<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/rad_new_design.md -->

# Creating a New RAD Design

## Overview

This document describes how to create a new reusable IP design in the **RAD (Reusable ASIC Designs)** environment. It brings together information from these documents:

- [FIFO Depth Tool](fifo_depth.md) & [Packet Quantization Calculator](pkt_quantize.md) — tools for sizing buffers and analyzing throughput
- [ABE Python Development](python_dev.md) — Python coding standards for DV utilities
- [RAD Design](design.md) — RTL structure, linting, formatting, synthesis
- [RAD Formal](formal.md) — formal proof setup and methods
- [RAD DV](dv.md) — UVM-style testbench using cocotb + pyuvm

A RAD design includes **RTL**, **formal verification**, **DV tests**, and **documentation**. All parts follow ABE conventions and use Make-based flows.

This guide provides a step-by-step process for creating a new RAD design.

---

## Goals

A complete RAD design should:

- Use a consistent directory and naming structure
- Pass static checks (formatting, linting, synthesis)
- Include formal proofs of key safety properties
- Include a complete UVM-style DV testbench that runs with open-source simulators
- Include documentation that explains purpose and usage
- Work with ABE's Make-based automation

RAD helps make this process **repeatable, predictable, and high-quality**.

---

## Directory Structure

RAD designs follow a consistent structure:

```text
├── src
│   └── abe
│       ├── rad
│       │   ├── rad_<design>
│       │   │   ├── dv
│       │   │   │   ├── __init__.py
│       │   │   │   ├── dv_regress.yaml
│       │   │   │   ├── rad_<design>*.py
│       │   │   │   ├── README.md
│       │   │   │   └── test_rad_<design>.py
│       │   │   ├── formal
│       │   │   │   ├── rad_<design>_cover.sby
│       │   │   │   ├── rad_<design>_formal_top.sv
│       │   │   │   └── rad_<design>.sby
│       │   │   ├── rtl
│       │   │   │   ├── rad_<design>*.sv
│       │   │   │   └── srclist.f
```

This structure ensures compatibility with all Makeflows, DV tools, and templates in the ABE environment.

---

## Workflow

## 1. Create the Design Directory

Create the top-level directory:

```text
src/abe/rad/rad_<design>/
```

Add these subdirectories:

```text
rtl/
formal/
dv/
```

Add a placeholder `README.md`.

---

## 2. Use Microarchitecture Tools if Needed

If your design needs buffer sizing or throughput analysis, use the `fifo-depth` or `pkt-quantize` tools.

---

## 3. Write RTL Using RAD Conventions

See [RAD Design](design.md) for RTL guidelines. Your RTL should:

- Include shared headers
- Have a `srclist.f` file
- Pass linting and synthesis checks

---

## 4. Add Formal Verification

You can use templates from existing designs as a starting point. Add:

- Safety properties
- Assumptions (on inputs only)

Then run:

```bash
make DESIGN=rad_<design> formal
make DESIGN=rad_<design> formal-cover
```

---

## 5. Create the DV Environment

- Start with a template from an existing design.
- Customize these parts for your design:
  - Driver
  - Monitors
  - Item
  - Reference model
  - Sequence
  - Coverage
  - Tests
- Run tests and regressions to verify your design works correctly.

---

## 6. Document the Design

Create a README.md that explains:

- What the design does
- The design's interface
- How the design behaves
- Any important assumptions

---

## Checklist

✔ RTL is clean
✔ Formal proofs pass
✔ DV regression passes
✔ Documentation is complete
✔ Make commands work

---

## Explore

For more information, see:

- [RAD Design](design.md)
- [RAD Formal](formal.md)
- [RAD DV](dv.md)

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
