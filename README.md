<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/index.md -->

# ABE: A Better Environment for Open-Source ASIC IP Development

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub](https://img.shields.io/badge/github-abe--asic--ip%2Fabe-blue.svg)](https://github.com/abe-asic-ip/abe)
[![Documentation](https://img.shields.io/badge/docs-github%20pages-blue.svg)](https://abe-asic-ip.github.io/abe/)
[![REUSE Compliance](https://img.shields.io/badge/REUSE-compliant-green.svg)](https://reuse.software/)

ABE ("A Better Environment") is a lightweight, modern environment for
open-source ASIC IP development. It combines microarchitecture tools, reusable
RTL designs, synthesis, formal verification, and Python-based design
verification (DV). ABE runs on free and open-source tools.

The goal is simple: **make block-level ASIC development easier, clearer, and
more productive** for professional engineers, students, researchers, and enthusiasts.

📚 **[Read the full documentation](https://abe-asic-ip.github.io/abe/)**

Welcome to ABE — a better environment for open-source ASIC IP development.

---

## What is ABE?

ABE provides tools and resources for digital design and verification:

- [Microarchitecture tools](#microarchitecture-tools): Including
[fifo-depth](docs/fifo_depth.md), a CP-SAT (Constraint Programming -
Satisfiability)-based tool that computes provably minimal FIFO depths and
flow-control parameters for complex traffic profiles.
- [UVM-based Python verification environment](docs/dv.md): A complete design
verification (DV) methodology using [cocotb](https://www.cocotb.org) and [pyuvm](https://github.com/pyuvm/pyuvm).
- [Developer workflow and tooling](#developer-tooling): Make-based workflows,
synthesis scripts, and code management tools.
- [Reusable ASIC Designs (RAD)](#reusable-asic-designs-rad): A library of RTL
designs validated with ABE's synthesis, formal verification, and DV flows.

These components work together to support the full development cycle from
microarchitecture to verification.

---

## Who is ABE for?

ABE is designed for anyone who wants to build ASIC modules with a modern,
open-source workflow:

- **Professional engineers** who prefer Python for modeling and verification
- **Professional engineers** who want license-free tools
- **Students** learning microarchitecture, design, formal, or verification
- **Researchers** building prototypes and publishing reproducible results
- **Enthusiasts** exploring ASIC IP development with free tools

ABE works well if you want a workflow that is clear, repeatable, and Python-friendly.

---

## Why was ABE created?

ASIC IP development often involves creating microarchitecture tools, scripts,
and testbenches for each new project. ABE's philosophy is practical: provide
solid, reusable infrastructure so designers can focus on building designs
rather than recreating validation frameworks.

ABE was created to address these common challenges:

- **Analytical FIFO sizing.** ABE provides [fifo-depth](docs/fifo_depth.md), a
CP-SAT-based analytical tool that complements simulation and spreadsheet
approaches by computing provably minimal FIFO depths and flow-control
parameters for complex, multi-layered traffic profiles across various
flow-control protocols.
- **Comprehensive DV infrastructure.** Many open-source projects provide RTL.
ABE adds complete Python-based verification environments with agents,
scoreboards, reference models, functional coverage, and randomization.
- **Python modeling and RTL simulation are often separate.** ABE connects them
using [cocotb](https://www.cocotb.org),
[pyuvm](https://github.com/pyuvm/pyuvm), and Python reference models.
- **Workflow and structure around open-source tools.** ABE provides Makefiles,
directory conventions, naming patterns, and tooling to complement powerful
open-source simulators with consistent project organization.

---

## Where does ABE fit in the open-source ecosystem?

ABE sits between lightweight code-writing tools and complete SoC frameworks.
ABE is designed to work together with other open-source projects and complement
existing workflows.

### ABE and EDA playgrounds / AI copilots

These tools are excellent for writing SystemVerilog code and interactive
experimentation. ABE complements them by providing infrastructure for
**complete, reusable ASIC IP** development with synthesis, formal verification,
Python-based DV, and structured workflows.

### ABE and [SVUnit](https://github.com/svunit/svunit) / [VUnit](https://vunit.github.io)

These are excellent testing frameworks for VHDL/SystemVerilog.
[SVUnit](https://github.com/svunit/svunit) focuses on unit testing, while
[VUnit](https://vunit.github.io) provides verification components and
block-level testing in VHDL/SystemVerilog. ABE complements them by providing
**Python-based verification** ([cocotb](https://www.cocotb.org) +
[pyuvm](https://github.com/pyuvm/pyuvm)) with reusable agents, scoreboards,
reference models, and functional coverage.

### ABE and [Verilator](https://verilator.org)'s new UVM support

[Verilator](https://verilator.org) now supports UVM. This is great progress
for open-source SystemVerilog verification. ABE offers a different approach
with **Python-based UVM** ([cocotb](https://www.cocotb.org) +
[pyuvm](https://github.com/pyuvm/pyuvm)). This provides easier integration
with Python reference models, Python workflows, and Python ecosystem tools
(e.g. data analysis).

### ABE and [OpenTitan](https://opentitan.org)

[OpenTitan](https://opentitan.org) is an open-source silicon Root of Trust
project. It provides a complete SoC design, reusable ASIC IP, and
production-grade SystemVerilog UVM verification. ABE has a different scope,
focusing on **general-purpose ASIC blocks** with **microarchitecture tools**
and **Python-based verification** for ASIC IP development.

---

## How Can I Get Started?

1. **Clone the repository**
2. **Set up the Python environment** ([see details](docs/python_dev.md#set-up-and-install-the-environment))
3. **Try [fifo-depth](docs/fifo_depth.md)** on an example YAML spec to see CP-SAT
based FIFO optimization in action
4. **Install free tools**: see [RAD Design](docs/design.md#install-required-tools),
[RAD Formal](docs/formal.md#install-required-tools), and
[RAD DV](docs/dv.md#install-required-tools) for details.
5. **Explore a [RAD](#reusable-asic-designs-rad) design** to experience
[RTL](docs/design.md), [synthesis](docs/design.md), [formal](docs/formal.md),
and [DV](docs/dv.md) flows firsthand
6. **[Run a test](docs/dv.md#run-examples)** with
[`dv`](docs/dv.md#1-dv-main-front-end-runs-a-single-test) and a
([cocotb](https://www.cocotb.org) + [pyuvm](https://github.com/pyuvm/pyuvm)) bench

---

## The ABE Toolkit

ABE provides three main categories of tools and resources:

---

## Microarchitecture Tools

ABE's microarchitecture tools help you make informed decisions before writing RTL.

### [FIFO Depth Tool](docs/fifo_depth.md)

The [fifo-depth](docs/fifo_depth.md) tool is a CP-SAT-based optimization tool that
addresses an important challenge in ASIC microarchitecture: determining the
minimal FIFO depth and flow-control parameters required to prevent underflow or
overflow under complex traffic conditions.

#### Key Features

The [fifo-depth](docs/fifo_depth.md) tool offers several advantages through its
CP-SAT-based approach:

- **Provably minimal:** Uses CP-SAT optimization to find the smallest FIFO
depth that satisfies all constraints, and computes appropriate flow-control
parameters (such as thresholds for XON/XOFF or credits for CBFC) when applicable.
- **Complex traffic profiles:** Handles layered, hierarchical traffic
specifications (cycle, transaction, burst, stream levels) that are difficult to
analyze manually.
- **Multiple flow-control protocols:** Supports Ready/Valid, XON/XOFF,
Credit-Based Flow Control (CBFC), and replay buffers.
- **CDC optimization:** For multi-clock FIFOs, proposes optimal partitioning
between asynchronous and synchronous storage.
- **Witness sequences:** Generates the exact read/write patterns that cause
the worst-case occupancy.

This analytical approach complements spreadsheet and simulation-based methods
and can help identify corner cases and optimize FIFO provisioning in complex scenarios.

### [Packet Quantization Calculator](docs/pkt_quantize.md)

The [pkt-quantize](docs/pkt_quantize.md) tool calculates bandwidth and packet rate
metrics for packet-based interfaces where packets are quantized to bus beats.

---

## Developer Tooling

ABE includes:

- Standard directory layout
- [Python environment setup](docs/python_dev.md)
- [Python static analysis](docs/python_dev.md) with
[isort](https://pycqa.github.io/isort), [black](https://github.com/psf/black),
[pylint](https://pylint.org), and [mypy](https://mypy-lang.org)
- Make targets for RTL development, synthesis, formal, and DV
- Documentation conventions

All designed to help you build ASIC IP quickly and consistently.

---

## Reusable ASIC Designs (RAD)

RAD provides production-quality RTL designs that have been validated using
ABE's synthesis, formal verification, and DV flows.

Each RAD design includes:

- [RTL implementation](docs/design.md)
- [Synthesis](docs/design.md)
- [Formal](docs/formal.md) verification and coverage
- A Python reference model
- A complete [DV environment](docs/dv.md) with agents, scoreboards, functional
coverage, and randomization
- Documentation

Current RAD designs include core CDC building blocks: synchronizers,
Multi-Cycle Path formulations, and asynchronous FIFOs.

---

## Explore ABE

Ready to dive deeper? Here's your map to everything ABE has to offer:

| Document | Description |
| ---------- | ------------- |
| [FIFO Depth Tool](docs/fifo_depth.md) | CP-SAT based tool for computing minimal FIFO depths and flow-control parameters |
| [Packet Quantization Calculator](docs/pkt_quantize.md) | Packet quantization calculator for performance metrics and bus analysis |
| [ABE Python Development](docs/python_dev.md) | Python development environment setup and tooling |
| [RAD Design](docs/design.md) | RAD design support for RTL quality, linting, and synthesis |
| [RAD Formal](docs/formal.md) | RAD formal verification flow and methodology |
| [RAD DV](docs/dv.md) | RAD design verification using [cocotb](https://www.cocotb.org) and [pyuvm](https://github.com/pyuvm/pyuvm) |
| [Creating a New RAD Design](docs/rad_new_design.md) | Guide for creating new RAD designs |

---

## FAQ

### **Is ABE good for beginners?**

Yes. ABE was designed to be clear and easy to learn. It is friendly to people
who are new to ASIC IP development.

---

### **Is ABE an SoC framework?**

ABE focuses on microarchitecture analysis, reusable ASIC IP, and DV patterns
rather than full SoC integration.

---

### **Does ABE replace UVM?**

ABE uses [pyuvm](https://github.com/pyuvm/pyuvm), a Python implementation of
UVM. Some users may prefer Python UVM. Others may prefer SystemVerilog UVM.
Both approaches have advantages and disadvantages.

---

### **Can I use ABE with commercial simulators?**

ABE currently supports [Verilator](https://verilator.org) and
[Icarus Verilog](https://steveicarus.github.io/iverilog). While
[cocotb](https://www.cocotb.org) works with commercial simulators, ABE's test
infrastructure would need updates to support them. Contributors with simulator
access can extend the [`dv`](docs/dv.md#1-dv-main-front-end-runs-a-single-test)
tool and submit changes to the repository.

---

### **Is the [fifo-depth](docs/fifo_depth.md) tool a simulator?**

No. It is an analytical tool that uses deterministic traffic analysis and a
CP‑SAT solver to determine worst‑case depths and flow-control parameters.

---

## Licensing

See the `LICENSES` directory at the repository root.
