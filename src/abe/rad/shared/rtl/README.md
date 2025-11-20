# Shared RTL Components

## Purpose

This directory contains reusable RTL components shared across multiple Reusable ASIC Designs (RAD). These components reduce code duplication and ensure consistent techniques throughout the design.

## Files

### rad_timescale.svh

A SystemVerilog header file that defines global simulation time units and precision.

**Configuration:**

- `timeunit 1ns` - Sets the time unit to 1 nanosecond
- `timeprecision 1ps` - Sets the time precision to 1 picosecond

**Conditional Compilation:**

- The timescale directives are excluded when `FORMAL` is defined
- This ensures compatibility with formal verification and Yosys synthesis tools

**Usage:**

Include this file at the top of RTL files to ensure consistent timing across simulations:

```verilog
`include "rad_timescale.svh"
```

---

### rad_pulse_gen.sv

**Module:** `rad_pulse_gen`

A toggle-based pulse generator for clock domain crossing applications. This module generates a single-cycle pulse whenever the input toggle signal changes state.

**Based on:** "Clock Domain Crossing (CDC) Design & Verification Techniques Using SystemVerilog" by Clifford E. Cummings, 2008

**Ports:**

- `output logic pulse` - Single-cycle pulse output (asserted when `d` and `q` differ)
- `output logic q` - Registered version of the input toggle signal
- `input logic d` - Synchronous toggle input signal
- `input logic clk` - Clock signal
- `input logic rst_n` - Active-low asynchronous reset

**Functionality:**

- Registers the input toggle signal `d` on each clock cycle
- Generates a pulse by XORing the current input `d` with the registered version `q`
- Produces a 1-cycle pulse whenever the toggle input changes state
- Commonly used in CDC synchronization chains to detect edge transitions

**Usage:**
This module is typically used in conjunction with synchronizers to safely transfer edge-triggered events across clock domains.
