<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/fifo_depth.md -->

# FIFO Depth Tool (`fifo-depth`)

## Overview

The **ABE Uarch FIFO Depth Tool** computes the *optimal* FIFO depth and flow-control thresholds for ASIC micro-architectures. It uses **Constraint Programming - Satisfiability (CP-SAT)** optimization to find minimal-area solutions that satisfy latency and congestion requirements.

**Note:** Throughout this document, "CP-SAT" is used consistently to refer to the constraint programming satisfiability solver.

### Audience

- **ASIC designers** who need to size FIFOs precisely under complex traffic profiles.
- **ASIC DV engineers** who want to create stress scenarios or validate margin in performance simulations.

### Purpose

- Determine the **smallest FIFO depth** and **thresholds** that prevent underflow or overflow.
- Generate **witness sequences** (read/write patterns) that show the limiting case.
- For multi-clock FIFOs, find an **optimal partition** between asynchronous and synchronous storage.

### Key Features

- Unified solver supporting major flow-control protocols:
  - Ready / Valid
  - XON/XOFF
  - Credit-Based Flow Control (CBFC)
- Layered traffic profile input (cycle, transaction, burst, or stream).
- Uses a deterministic algorithm to construct the worst-case write and read profiles.
- Uses a mathematical solver (CP-SAT) to find the worst peak occupancy.
- Proposes optimal Clock Domain Crossing (CDC) solution for multi-clock FIFOs.
- Replay buffer baseline solver for future expansion.

#### Flat vs. Layered Specifications

| Spec Type | Description | Use Case |
|----------|-------------|----------|
| Flat     | Direct FIFO parameters, explicit bounds on total read/write data over a fixed window. | Simple, well-understood traffic or spreadsheet migration |
| Layered  | Hierarchical profiles (cycle, transaction, burst, stream), tool derives worst-case from structure. | Complex, protocol-specific, or bursty traffic |

#### When to Use Flat vs Layered

| Traffic Type | Recommended Spec Type|
|--------------|----------------------|
| Simple burst with known bounds | Flat |
| Protocol-modeled behavior | Layered |
| Unknown or exploratory behavior | Layered |
| Arbitrary bounds without structure | Flat |

### Known Limitations

- Cannot yet model interface/storage quantum mismatches
- Layered replay not supported
- Threshold optimization for XON/XOFF may have long runtimes for large horizons
- CBFC headroom auto-selection depends on read-valid gapiness
- CDC solver assumes Gray-coded pointers and synchronizers (not handshake-based async FIFOs)

---

## Getting Started

### Set Up and Install

See [ABE Python Development](python_dev.md) for Python environment setup details.

```bash
make py-venv-all
source .venv/bin/activate
make py-install-all
```

### Run Examples

```bash
fifo-depth src/abe/uarch/fifo_depth_examples/rv_layered.yaml
fifo-depth src/abe/uarch/fifo_depth_examples/cbfc_cdc.yaml
```

### Look at the Outputs

```bash
ls out_uarch_fd*
cat out_uarch_fd_rv_layered/results_scalars.json
```

### Examine the Relevant Directory Layout

```bash
.
├── src
│   └── abe
│       ├── uarch
│       │   ├── fifo_depth_examples
│       │   │   ├── cbfc_balanced.yaml
│       │   │   ├── cbfc_cdc.yaml
│       │   │   ├── cbfc_flat.yaml
│       │   │   ├── cbfc_layered.yaml
│       │   │   ├── replay_cdc.yaml
│       │   │   ├── replay.yaml
│       │   │   ├── rv_balanced.yaml
│       │   │   ├── rv_cdc.yaml
│       │   │   ├── rv_flat.yaml
│       │   │   ├── rv_layered.yaml
│       │   │   ├── xon_xoff_balanced.yaml
│       │   │   ├── xon_xoff_cdc.yaml
│       │   │   ├── xon_xoff_flat.yaml
│       │   │   └── xon_xoff_layered.yaml
│       │   ├── __init__.py
│       │   ├── fifo_depth_base.py
│       │   ├── fifo_depth_cbfc.py
│       │   ├── fifo_depth_cdc.py
│       │   ├── fifo_depth_ready_valid.py
│       │   ├── fifo_depth_replay.py
│       │   ├── fifo_depth_utils.py
│       │   ├── fifo_depth_xon_xoff.py
│       │   ├── fifo_depth.py
│       │   └── pkt_quantize.py
```

## Conceptual Background

### Scope

This tool models **short-term congestion** in data paths. The YAML specifications describe finite-duration traffic bursts where writes exceed reads. Over longer timescales, system-level flow control ensures balance; that equilibrium is beyond this tool’s scope.

A “balanced” spec (equal write/read densities) requires only minimal buffering for arbitration or phase alignment. The tool automatically detects balanced cases and switches from CP-SAT to a closed-form analytic solver. Such cases may be detected and handled analytically. The main use case is the **imbalanced** case — temporary write oversubscription requiring real buffering.

### Motivation

Traditional sizing methods rely on closed-form equations or spreadsheet estimation. Those approaches may be less accurate when traffic is bursty, multi-layered, or latency-constrained. This tool computes FIFO depth using a hybrid deterministic + solver-based approach. The key idea is to combine (a) domain-specific knowledge of worst-case congestion patterns with (b) an exact optimization stage using CP-SAT. This combination provides a practical and mathematically accurate solution.

For details on how layers compose and how worst-case patterns are generated, see [How Layers Compose](#how-layers-compose).

---

## Unique Approach

### Deterministic Construction of Worst-Case Write and Read Profiles

The user’s layered traffic specification (transaction, burst, and stream structure) is first compiled into **binary valid profiles** for the write and read sides. These profiles are not arbitrary: the tool intentionally creates **worst-case congestion patterns** using a set of deterministic rules derived from theory and literature.

#### **Write-side Worst Case (maximizing clustering of data)**

The write profile generator creates patterns that produce the densest possible windows of valid cycles:

- Transactions inside a burst alternate between `valid-first` and `gap-first` to create long, contiguous data regions.
- Bursts with data (D) and idles (I) are arranged using an `(I,D)` / `(D,I)` envelope based on the number of bursts:
  - `s_cnt = 1`: `(D,I)`
  - `s_cnt = 2`: `(I,D) (D,I)`
  - `s_cnt = 3`: `(I,D) (D,I) (D,I)`
  - `s_cnt = 4`: `(I,D) (D,I) (I,D) (D,I)`
- This places idles at the start and end of the stream, while concentrating data in the interior.
- For multi-burst streams, boundaries are constructed to create `...1 | 1...` transitions (“Case-4” behavior), known to maximize FIFO occupancy.

#### **Read-side Worst Case (delaying consumption)**

The read profile generator clusters **idle** cycles to delay consumption:

- Every burst begins with a gap (`I,D`) to ensure reads start as late as possible.
- Transactions alternate so that gap boundaries align and create long idle runs.
- Burst boundaries aggregate idles across the stream.
- A causality guard rotates the read mask so that **no read occurs before data can physically arrive**, incorporating write latency.

The result is a pair of profiles `(write_valid[], read_valid[])` that represent **the worst traffic environment allowed by the user’s layered specification**.

### Constraint-Based Optimization Using CP-SAT

After generating deterministic worst-case masks, the tool invokes a **cycle-accurate CP-SAT optimization** stage.

The solver determines **when** writes and reads actually fire within cycles marked valid, while enforcing:

- **FIFO causality**
  `occ[t+1] = occ[t] + writes[t] - reads[t]`
- **Non-negativity**
  `occ[t] ≥ 0`
- **Throughput constraints**
  - total writes = `sum_w`
  - total reads  = `sum_r`
- **Latency constraints**
  - `wr_latency`, `rd_latency`
  - synchronizer delays (CDC)

The solver’s objective is to **maximize the peak occupancy** under these constraints.

Because the deterministic masks already encode the worst-case timing structure, CP-SAT only needs to explore *cycle-level scheduling* inside those windows — which is computationally tractable while still exact.

### Why Both Stages Are Necessary

Using **only deterministic mask construction** would give plausible worst cases, but could miss problematic write/read alignments that depend on exact cycle timing.

Using **only CP-SAT** would require the solver to reason about transactions, bursts, and streams directly, which is computationally impractical for realistic horizons.

The hybrid method combines the strengths of both:

| Component | Purpose | Strength |
|----------|---------|----------|
| **Deterministic Worst-Case Mask Builder** | Shapes adversarial write/read behavior | Fast, structured, captures known worst-case patterns |
| **CP-SAT Optimization** | Finds the mathematically worst alignment and firing schedule | Exact, global maximum of occupancy |

Together, they compute FIFO depths that are **tight, consistent, and reliable**, yet fast enough for interactive use.

The hybrid deterministic + CP-SAT method provides a true worst-case bound for the reported depth.

---

## Architecture

```text
YAML spec files (flat / layered)
             |
             v
   Pydantic models + validation
             |
   ----------------------------
   |                          |
   v                          v
Traffic compiler        CDC solver
(layered → worst-case   (closed-form
 write/read masks)       CDC depth)
   |                          |
   v                          |
CP-SAT solvers                |
(Ready/Valid, XON/XOFF,       |
 CBFC, Replay)                |
   \                         /
    \                       /
     v                     v
        Core results (occ_peak,
        thresholds, credits…)
                     |
                     v
     Post-processing (atomic_tail +
          CDC + margin + rounding)
                     |
                     v
      JSON / CSV / PNG / log outputs
```

Each solver ([Ready/Valid](#ready-valid-solver), [XON/XOFF](#xon-xoff-solver), [CBFC](#cbfc-solver), [Replay](#replay-solver), [CDC](#cdc-solver)) extends `FifoSolver`. Common data structures are defined in `fifo_depth_base.py`.

### Typical Workflow

1. Start with a layered write/read spec
2. Run fifo-depth → observe occ_peak and witness
3. Apply margin/rounding
4. For CDC: use CDC solver first, then feed into sync FIFO solver
5. Integrate results in RTL

---

### File Overview

| File | Description |
|------|--------------|
| `fifo_depth.py` | Top-level orchestrator, CLI entrypoint |
| `fifo_depth_base.py` | Common models and solver framework |
| `fifo_depth_utils.py` | Shared helper functions |
| `fifo_depth_ready_valid.py` | Ready / Valid flow control solver |
| `fifo_depth_xon_xoff.py` | XON/XOFF flow control solver |
| `fifo_depth_cbfc.py` | Credit-based flow control solver |
| `fifo_depth_replay.py` | Replay buffer solver |
| `fifo_depth_cdc.py` | CDC composition and partitioning |
| `fifo_depth_examples/` | Example YAML configurations |

---

## Command Line Interface

### Arguments

The `fifo-depth` tool accepts the following command-line arguments:

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `spec` | positional | Yes | — | One or more YAML/JSON spec file path(s). You can specify multiple files. |
| `--outdir` | optional | No | See description | Output directory for results files (JSON, CSV, PNG) and log file. If not specified, outputs to "out_uarch_fd_\<spec-stem\>, where \<spec-stem\> is the stem of the spec file. |
| `--results-name` | optional | No | See description | Prefix for results filenames. The default prefix is the name of the solver results class. |
| `--verbosity` | optional | No | `info` | Logging level. Choices: `critical`, `error`, `warning`, `info`, `debug`. |

### Examples

```bash
# Basic usage with single spec file
fifo-depth src/abe/uarch/fifo_depth_examples/ready_valid.yaml

# Multiple spec files
fifo-depth spec1.yaml spec2.yaml

# With custom output directory and results prefix
fifo-depth my_spec.yaml --outdir ./results --results-name run1

# With debug logging
fifo-depth my_spec.yaml --verbosity debug
```

## Input Specifications

### Types of Specs

Two YAML specification forms are supported:

| Type | Description |
|------|--------------|
| **Flat** | Direct FIFO parameters (simple cases). |
| **Layered** | Hierarchical read/write profiles (cycle, transaction, burst, stream). |

**Flat specifications** provide explicit bounds on total read and write data over a fixed horizon. Users directly specify `sum_w_min`, `sum_w_max`, `sum_r_min`, and `sum_r_max` to limit the worst-case traffic pattern. This approach works well when traffic characteristics are well-understood or when migrating from spreadsheet-based analysis. Flat specs require the user to manually calculate aggregate traffic bounds.

**Layered specifications** define traffic patterns hierarchically through independent read and write profiles. Each profile can include multiple layers (e.g., cycle-level behavior, transaction grouping, burst patterns, stream periodicity) that combine to describe complex, realistic traffic. The tool automatically calculates the worst-case aggregate constraints from these layered descriptions. This approach is more intuitive for modeling protocol-specific behavior and allows the solver to explore combinations of layer parameters to find the most stressful scenario.

### Data Quantities

The `fifo-depth` tool:

- Assumes that the interface data quantum matches the FIFO storage data quantum.
- Treats all data quantities as unitless integers.
- Does not automatically scale data values for the CP-SAT solver.

Users must ensure that all write and read data parameters are specified in consistent units (e.g., bytes, words, flits) and at appropriate magnitudes for the solver.

### Horizon Concept

The **horizon** defines the time window (in cycles) over which the solver analyzes traffic patterns and computes FIFO depth requirements. It represents the finite duration of the scenario being modeled — typically a burst or congestion event where write traffic temporarily exceeds read traffic.

Key characteristics:

- **Finite-duration analysis**: The horizon captures a specific traffic scenario, not steady-state equilibrium. The solver finds the worst-case FIFO occupancy within this time window.
- **Flat specs**: Users specify horizon directly as a positive integer. All traffic constraints (`sum_w_min`, `sum_w_max`, `sum_r_min`, `sum_r_max`) apply over this fixed window.
- **Layered specs**: Horizon can be `"auto"` (recommended) or user-specified. Auto mode computes horizon based on the traffic pattern's natural periodicity (`overall_period`), the blind window (`blind_window_cycles`), and minimum repetition count (`kmin_blocks`). This ensures the solver examines sufficient pattern cycles to find worst-case alignment.
- **Longer horizons**: Generally capture more realistic worst-case scenarios but increase solver runtime. For layered specs, the auto-computed horizon balances coverage and efficiency.

The horizon does not model long-term system-level flow control or equilibrium — it focuses on short-term congestion that requires buffering.

**Horizon Sufficiency Check**: The solver checks if the specified horizon may be too short to observe the maximum FIFO occupancy. The check uses this formula:

```text
horizon >= (sum_w_max / w_max) + (sum_r_max / r_max)
```

This check ensures there are enough cycles to write the maximum write traffic (`sum_w_max` at rate `w_max`) and read the maximum read traffic (`sum_r_max` at rate `r_max`). If the horizon is shorter than this threshold, a warning is issued showing that the computed FIFO depth may be underestimated. This check is most important for protocols without flow control (e.g., `ready_valid`) where occupancy can reach `sum_w_max`. Protocols with flow control (e.g., `xon_xoff`, `cbfc`) typically have lower occupancy limits because of their flow control mechanisms.

### Common Parameters {#common-parameters}

All solvers use these YAML parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `fifo_type` | string | Yes | — | FIFO protocol type. Choices: `ready_valid`, `xon_xoff`, `cbfc`, `replay`, `cdc`. |
| `margin_type` | string | No | `"absolute"` | Type of margin to apply. Choices: `percentage`, `absolute`. |
| `margin_val` | int | No | `0` | Margin value (non-negative). Interpreted based on `margin_type`. |
| `rounding` | string | No | `"none"` | Rounding strategy for final depth. Choices: `power2`, `none`. |

### Flat Spec Parameters {#flat-spec-parameters}

The Ready / Valid, XON / XOFF, and CBFC solvers use these YAML parameters for flat specs:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `horizon` | int | Yes | — | Number of cycles to model (positive integer). |
| `wr_latency` | int | No | `0` | Write latency in cycles (non-negative). |
| `rd_latency` | int | No | `0` | Read latency in cycles (non-negative). |
| `w_max` | int | No | `1` | Maximum write data per cycle (non-negative). |
| `r_max` | int | No | `1` | Maximum read data per cycle (non-negative). |
| `sum_w_min` | int | Yes | — | Minimum total write data over horizon (non-negative). |
| `sum_w_max` | int | Yes | — | Maximum total write data over horizon (non-negative, ≥ `sum_w_min`). |
| `sum_r_min` | int | Yes | — | Minimum total read data over horizon (non-negative). |
| `sum_r_max` | int | Yes | — | Maximum total read data over horizon (non-negative, ≥ `sum_r_min`). |

### Layered Spec Parameters {#layered-spec-parameters}

The Ready / Valid, XON / XOFF, and CBFC solvers use these YAML parameters for layered specs:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `horizon` | int or string | No | `"auto"` | Number of cycles to model. Can be `"auto"` (recommended) to automatically compute based on `overall_period`, `blind_window_cycles`, and `kmin_blocks`, or a user-specified positive integer (will be rounded up to multiple of `overall_period`). |
| `wr_latency` | int | No | `0` | Write latency in cycles (non-negative). |
| `rd_latency` | int | No | `0` | Read latency in cycles (non-negative). |
| `kmin_blocks` | int | No | `4` | Minimum number of complete periods to include in auto-computed horizon. Ensures sufficient repetition of layered traffic pattern. Must be ≥ 1. |
| `blind_window_cycles` | int | No | `0` | Number of cycles during which reads cannot observe writes (e.g., round-trip latency). Auto-computed horizon ensures at least `4 × blind_window_cycles` to capture worst-case behavior. Must be ≥ 0. |

#### Layered Profiles

Layered specs specify independent **write** and **read** traffic profiles using a hierarchical structure. Both `write_profile` and `read_profile` use identical YAML parameters organized into four layers that build upon each other to create complex, realistic traffic patterns.

**Layer Structure:**

Each profile is composed of up to 4 layers that define traffic at increasing levels of granularity:

1. **Cycle Layer** (optional): Defines the maximum data items per cycle
2. **Transaction Layer** (required): Defines active and idle periods within a transaction
3. **Burst Layer** (required): Defines how transactions are grouped with inter-burst gaps
4. **Stream Layer** (optional): Defines how bursts are grouped with inter-stream gaps

**Layer Parameters:**

| Layer | Parameter | Type | Required | Default | Description |
|-------|-----------|------|----------|---------|-------------|
| **Cycle** | `cycle.max_items_per_cycle` | int | No | `1` | Maximum data items that can be transferred in a single cycle (≥ 1). |
| **Transaction** | `transaction.valid_cycles` | int | Yes | — | Number of active cycles in a transaction (≥ 0). |
| **Transaction** | `transaction.gap_cycles` | int | Yes | — | Number of idle cycles in a transaction (≥ 0). |
| **Burst** | `burst.transactions_per_burst` | int | Yes | — | Number of transactions in each burst (≥ 1). |
| **Burst** | `burst.gap_cycles` | int | Yes | — | Number of idle cycles between bursts (≥ 0). |
| **Stream** | `stream.bursts_per_stream` | int | No | `1` | Number of bursts in each stream (≥ 1). |
| **Stream** | `stream.gap_cycles` | int | No | `0` | Number of idle cycles between streams (≥ 0). |

The `fifo-depth` tool composes write and read patterns to trigger the worst-case FIFO occupancy. See the [How Layers Compose](#how-layers-compose) section of the Appendix for details.

**Example:**

```yaml
write_profile:
  cycle:
    max_items_per_cycle: 2
  transaction:
    valid_cycles: 4
    gap_cycles: 2
  burst:
    transactions_per_burst: 8
    gap_cycles: 16
  stream:
    bursts_per_stream: 3
    gap_cycles: 32
```

This creates a write pattern where:

- Up to 2 data items can be written per active cycle
- Each transaction has 4 active cycles, then 2 idle cycles (period = 6)
- Each burst has 8 transactions, then 16 idle cycles (period = 8×6 + 16 = 64)
- Each stream has 3 bursts, then 32 idle cycles (period = 3×64 + 32 = 224)

---

## Outputs

| File | Description |
|------|--------------|
| `results_scalars.json` | Key numeric results (depth, thresholds, margins) |
| `results_witness.csv` | Read/write occupancy sequence producing worst-case depth |
| `results_plot.png` | Graphical witness visualization |
| `run.log` | Log of parameters, solver stats, and final results |
| `cdc_results_scalars.json` | Additional results for CDC partitioning |

Example console output:

```bash
2025-11-13 07:34:09 - abe.uarch.fifo_depth_base - INFO - results:
{
  "basic_checks_pass": true,
  "msg": "",
  "depth": 36,
  "occ_peak": 32,
  "xon": 15,
  "xoff": 31,
  "t_star": 227
}
2025-11-13 07:34:10 - abe.utils - INFO - XonXoffResults: results.basic_checks_pass=True
2025-11-13 07:34:10 - abe.utils - INFO - Completed src/abe/uarch/fifo_depth_examples/xon_xoff_layered.yaml in 0:02:17
```

### Common Results {#common-results}

The Ready / Valid, XON/XOFF, and CBFC solvers produce these common results:

| Field | Type | Description |
|-------|------|-------------|
| `basic_checks_pass` | bool | Internal validation flag showing whether the solver's self-consistency checks passed. When `true`, the results are valid. When `false`, an error occurred (e.g., peak occupancy mismatch in witness sequences) and the tool will raise an exception. |
| `msg` | str | Informational message about the solution method. For CP-SAT solvers, typically empty. For CDC solver, contains `"Analytic results."` to indicate closed-form calculation was used instead of constraint programming. |
| `depth` | int | Recommended minimum FIFO depth. Starts with `occ_peak`, then adds: `atomic_tail` (if applicable), CDC synchronizer depth (if applicable), margin (percentage or absolute), and rounding (power-of-2 if specified). This is the final value for FIFO sizing. |
| `occ_peak` | int | Peak occupancy computed by the CP-SAT solver. This is the worst-case number of data items simultaneously stored in the FIFO before any margins or adjustments are applied. |
| `w_seq` | List[int] | Write sequence witness: the number of data items written to the FIFO at each cycle. This time-series demonstrates the worst-case traffic pattern that produces `occ_peak`. |
| `r_seq` | List[int] | Read sequence witness: the number of data items read from the FIFO at each cycle. Combined with `w_seq`, this shows how the FIFO fills and drains over time. |
| `occ_seq` | List[int] | Occupancy sequence witness: the FIFO occupancy (number of stored items) at each cycle boundary. The maximum value in this sequence equals `occ_peak`. Useful for visualizing worst-case behavior and validating the solution. |

---

## Future Enhancements

### Replay Solver Extensions {#replay-solver-extensions}

As noted in the [Replay Solver](#replay-solver) section, the current implementation serves as a reference baseline for more complex future variants including:

- Variable round-trip time (jitter, retry delays)
- Credit windows smaller than bandwidth–delay product
- Multiple senders sharing a replay buffer
- Dynamic flow control and non-uniform transmission rates

### Data Quantum and Units Support

The tool currently has these data-related limitations:

- Assumes interface data quantum matches FIFO storage data quantum
- Treats all data quantities as unitless integers
- Does not automatically scale data values for CP-SAT solver efficiency

**Storage Quantum Mismatch:**

The first limitation can underestimate FIFO depth in certain protocols. For example, consider XON/XOFF flow control for Ethernet where FIFO storage is allocated in 64-byte words. Between when the receiver sends XOFF and the sender receives it, the worst case occurs when the sender bursts 65-byte Ethernet packets (64-byte payload + 1-byte overhead). These 65-byte packets use the most FIFO storage relative to bandwidth, but the tool currently cannot model this interface-to-storage quantum mismatch.

**Units and Autoscaling:**

Supporting units (similar to the `pint`-based approach used for CDC clock frequencies) would improve specification clarity and reduce user errors from unit inconsistencies.

Automatic scaling would simultaneously simplify YAML specifications and optimize CP-SAT solver performance by normalizing large or small data values to efficient integer ranges.

**Implementation Approach:**

The recommended enhancement strategy:

1. Add preprocessing stage to read user YAML, translate units, autoscale values, and generate normalized YAML for existing solvers
2. Keep current solver implementations unchanged
3. Add postprocessing stage to reverse scaling and restore units in results

This approach preserves the existing solver architecture while providing a cleaner user interface.

---

## Ready / Valid Solver {#ready-valid-solver}

### Ready / Valid Purpose

Basic data-valid interface (no explicit feedback).

### Ready / Valid Parameters

None beyond [common parameters](#common-parameters).

### Ready / Valid Results

None beyond [common results](#common-results).

### Ready / Valid Recommendations

**Flat Specifications:**

For flat (non-layered) ready/valid specifications, the FIFO depth will always equal `sum_w_max`. This happens because:

- In a flat spec, write and read valid masks are constant (all 1s), meaning data can be written or read every cycle
- The worst-case scenario happens when the maximum amount of data (`sum_w_max`) is written before any reads can complete
- With no temporal structure to use, the FIFO must hold the entire maximum write burst

For this simple case, a direct calculation would be sufficient. The solver still works correctly but provides no optimization benefit beyond the analytical result.

**Balanced Specifications:**

For balanced specifications (where minimum read density ≥ maximum write density), CP-SAT cannot work effectively because:

- The solver tries to maximize peak occupancy by scheduling writes and reads in the worst way
- In balanced specs, reads can always drain the FIFO faster than writes can fill it
- CP-SAT would explore an infinite solution space trying to delay reads indefinitely
- No meaningful worst-case bound exists in the constraint formulation

The tool automatically detects balanced specifications using the `is_balanced()` method and switches to an analytical solver (`_get_results_analysis()`) instead. This analytical approach:

- Performs a phase-sweep across all possible read/write alignments
- Accounts for write/read latencies in a deterministic way
- Calculates the worst-case occupancy trajectory across all phase shifts
- Returns a meaningful depth based on the temporal interaction of layered traffic patterns

*Note:* Layered specifications with temporal structure enable the solver to perform meaningful optimization. Flat and balanced specs are handled automatically with appropriate methods.

---

## XON / XOFF Solver {#xon-xoff-solver}

### XON / XOFF Purpose

Models XON/XOFF flow control protocols where the receiver uses threshold-based signaling to control the sender's transmission rate. In XON/XOFF:

- The receiver monitors FIFO occupancy and asserts XOFF when occupancy reaches the `xoff` threshold, signaling the sender to pause
- The sender reacts to XOFF after a reaction latency (`react_latency`), then stops or throttles transmission
- When occupancy drains below the `xon` threshold, the receiver de-asserts XOFF (signals XON)
- The sender resumes transmission after a resume latency (`resume_latency`)
- Hysteresis between `xon` and `xoff` prevents rapid toggling (control chatter) when occupancy stays near a single threshold

XON/XOFF is commonly used in UARTs, network switches, and storage interfaces where simple threshold-based flow control provides adequate backpressure without per-transaction handshaking.

### XON / XOFF Overview

The XON/XOFF solver computes three critical values:

1. **`depth`** - The required FIFO buffer depth
2. **`xon`** - The threshold at which flow control is de-asserted (resume transmission)
3. **`xoff`** - The threshold at which flow control is asserted (pause transmission)

Both `xon` and `xoff` are essential hardware parameters. They determine:

- **Hysteresis behavior**: The separation between pause and resume thresholds prevents rapid toggling of flow control
- **Throughput vs. depth trade-off**: Lower thresholds reduce buffering but may cause more frequent pauses, reducing effective bandwidth
- **Reaction margin**: Sufficient headroom above `xoff` to accommodate data written during the writer's reaction latency

**Auto Mode vs. Manual Mode:**

The solver supports two modes:

- **Auto Mode** (`thresholds="auto"`, default): The solver automatically computes optimal threshold values using constraint programming. It finds threshold configurations that satisfy throughput targets while minimizing FIFO depth, then explores the hysteresis range to balance depth, throughput, and control stability.

- **Manual Mode** (`thresholds="manual"`): You specify fixed `xon` and `xoff` values, and the solver validates whether they provide sufficient flow control and computes the resulting FIFO depth.

**How Auto-Optimization Works:**

When `thresholds="auto"` (default):

1. The solver analyzes traffic patterns (write/read caps, latencies, atomic writes, throttle rates)
2. It calculates bounds for thresholds based on reaction/resume latencies and sustained throughput requirements
3. It explores candidate threshold pairs within the specified `hysteresis` range
4. It optimizes based on preferences: minimize depth (default), minimize hysteresis band (`prefer_small_band`), or minimize `xoff` (`prefer_low_xoff`)
5. It validates each candidate against throughput targets and requirements
6. It applies any specified margins and rounding to the final depth

*Note on adaptive optimization:* The solver automatically adjusts threshold search ranges based on traffic burstiness to help ensure adequate margin for reaction latency while avoiding over-provisioning.

### XON / XOFF Parameters

XON / XOFF parameters include all [common parameters](#common-parameters) plus these XON / XOFF-specific parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `atomic_tail` | int | No | `0` | Number of data items in the final atomic write transaction that cannot be interrupted (non-negative). When the writer begins this tail transaction, it must complete even if XOFF is asserted. |
| `react_latency` | int | No | `0` | Latency in cycles for the writer to react to XOFF assertion and stop writing (non-negative). Data continues to be written during this reaction period. |
| `resume_latency` | int | No | `0` | Latency in cycles for the writer to resume writing after XON assertion (non-negative). No data is written during this resume period. |
| `w_throttle_max` | int | No | `0` | Maximum number of data items that can be written per cycle while paused (non-negative). Default `0` means hard stop - no writes occur when paused. |
| `thresholds` | str | No | `"auto"` | Threshold configuration mode: `"manual"` or `"auto"`. In manual mode, `xon` and `xoff` must be specified. In auto mode, the solver optimizes threshold values. |
| `xon` | int or None | Conditional | `None` | XON threshold - occupancy level at which flow control is de-asserted and writer resumes (non-negative). Required when `thresholds="manual"`, ignored in auto mode. |
| `xoff` | int or None | Conditional | `None` | XOFF threshold - occupancy level at which flow control is asserted to pause the writer (non-negative). Required when `thresholds="manual"`, ignored in auto mode. Must be ≥ `xon` to ensure hysteresis. |
| `throughput_target` | float or "auto" | No | `"auto"` | Target throughput ratio (0.0 to 1.0) for auto mode. When `"auto"`, defaults to maximum achievable throughput. Lower values allow smaller FIFO depths at the cost of reduced performance. |
| `xon_min` | int or "auto" | No | `"auto"` | Minimum allowed XON threshold for auto mode (non-negative). When `"auto"`, solver computes the minimum based on resume latency and traffic patterns. Constrains the search space for threshold optimization. |
| `xoff_range` | List[int] or "auto" | No | `"auto"` | Range of XOFF values `[min, max]` to explore in auto mode. When `"auto"`, solver determines the range based on traffic patterns and throughput target. Allows constraining threshold search space. |
| `hysteresis` | List[float or int] | No | `[1.0, 1.5]` | Hysteresis range `[min, max]` as ratio between XOFF and XON thresholds. Used in auto mode to ensure separation between pause and resume levels. Both values must be ≥ 1.0, and `min ≤ max`. Larger hysteresis reduces control chatter but may increase depth. |
| `prefer_small_band` | bool | No | `false` | When `true`, auto mode prioritizes minimizing hysteresis band (XOFF - XON) over other optimization goals. Useful when minimizing control signal transitions is more important than depth. |
| `prefer_low_xoff` | bool | No | `false` | When `true`, auto mode prioritizes lower XOFF values over other optimization goals. Useful when minimizing peak occupancy before flow control engages is important. |

### XON / XOFF Results

XON / XOFF results include all [common results](#common-results) plus these XON / XOFF-specific results:

| Result | Description |
|--------|-------------|
| `xon` | Computed or validated XON threshold - the FIFO occupancy level at which flow control is de-asserted to resume writing |
| `xoff` | Computed or validated XOFF threshold - the FIFO occupancy level at which flow control is asserted to pause writing |
| `throughput` | Achieved write throughput as a ratio in [0.0, 1.0], normalized to (horizon * w_max). It is populated by the solver after witness extraction. |
| `t_star` | Earliest cycle at which peak occupancy occurs. Used as a tiebreaker in auto mode optimization when multiple threshold configurations achieve the same depth. Lower values indicate the peak occurs earlier in the horizon. |

### XON / XOFF Recommendations

**Auto Mode Benefits:**

Auto mode (`thresholds="auto"`) is recommended because:

1. **Optimal Threshold Selection**: The solver finds threshold configurations that minimize FIFO depth while meeting your throughput requirements, avoiding over-provisioning of buffer memory.

2. **Correct Reaction Margins**: The solver automatically accounts for reaction and resume latencies, ensuring sufficient headroom above `xoff` to handle data written during the pause reaction period.

3. **Adaptive to Traffic Patterns**: The solver analyzes your specific write/read profiles, atomic transactions, and throttle behavior to determine appropriate threshold values, rather than requiring manual calculation.

4. **Hysteresis Optimization**: The solver explores the specified hysteresis range to balance control stability (avoiding chatter) against depth minimization.

**When to Use Manual Mode:**

Manual mode is useful when:

- You have pre-existing XON/XOFF protocol specifications that must be validated
- Hardware constraints dictate specific threshold values (e.g., register width limitations)
- You want to verify that a proposed threshold configuration is sufficient for your traffic

**Recommendations:**

- Consider starting with auto mode to understand the optimal thresholds for your traffic pattern
- Use `hysteresis` (default: `[1.0, 1.5]`) to control the minimum and maximum separation between `xon` and `xoff`
- Set `throughput_target` below 1.0 if you're willing to trade some bandwidth for reduced FIFO depth
- Use `prefer_small_band=true` to minimize hysteresis width if reducing control signal transitions is critical
- Use `prefer_low_xoff=true` to minimize peak occupancy if you want flow control to engage earlier
- Apply standard margin and rounding options to add implementation safety margin to the computed depth

---

## CBFC Solver {#cbfc-solver}

### CBFC Purpose

Models Credit-Based Flow Control (CBFC) protocols where the sender's transmission rate is regulated by credits returned asynchronously from the receiver. In CBFC:

- The sender maintains a credit pool that is decremented with each write and incremented when credits are returned from the receiver
- Credits are returned after the receiver consumes data, subject to a return latency (`cred_ret_latency`)
- The sender can only transmit when sufficient credits are available
- This provides backpressure without requiring a synchronous ready/valid handshake

CBFC is commonly used in network protocols and interconnects where asynchronous flow control is preferred over cycle-by-cycle handshaking.

### CBFC Overview

The CBFC solver computes three critical values:

1. **`depth`** - The required FIFO buffer depth
2. **`cred_max`** - The maximum size of the credit pool
3. **`cred_init`** - The initial number of credits at startup

Both `cred_max` and `cred_init` are essential hardware implementation parameters. They determine:

- **Credit pool sizing**: How many credits the sender must track (affects counter width or memory requirements)
- **Startup behavior**: How much data can be transmitted before the first credits return from the receiver
- **Sustained throughput**: Whether the credit return rate can support the desired bandwidth

**Auto Mode vs. Manual Mode:**

The solver supports two modes:

- **Auto Mode** (`cred_max="auto"` and/or `cred_init="auto"`, default): The solver automatically computes optimal credit values using constraint programming. It finds the minimal feasible credit configuration that satisfies the traffic requirements, then adds adaptive headroom based on read-valid gapiness patterns.

- **Manual Mode** (explicit integer values): You specify fixed credit values, and the solver validates whether they provide sufficient flow control and computes the resulting FIFO depth.

**How Auto-Optimization Works:**

When `cred_auto_optimize=true` (default) with auto mode:

1. The solver analyzes traffic patterns (write/read caps, latencies, credit return latency)
2. It computes lower bounds for credits based on startup requirements and sustained throughput
3. It performs lexicographic minimization: first minimizes `cred_init`, then minimizes `cred_max`
4. It adds adaptive headroom derived from the read-valid pattern's maximum gap between valid slots
5. It applies any specified margins and rounding

*Note on adaptive headroom:* The solver automatically adjusts headroom based on read-valid gapiness to help ensure credits are available even when reads arrive in bursts rather than uniformly.

### CBFC Parameters

CBFC parameters include all [common parameters](#common-parameters) plus these CBFC-specific parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cred_max` | int or "auto" | No | `"auto"` | Maximum credit pool size (non-negative). When `"auto"`, solver optimizes this value. |
| `cred_init` | int or "auto" | No | `"auto"` | Initial credit count at start (non-negative). When `"auto"`, solver optimizes this value. Must be ≤ `cred_max`. |
| `cred_gran` | int | No | `1` | Credit granularity - number of data units per credit (non-negative). |
| `cred_ret_latency` | int | No | `0` | Latency in cycles for credit return from receiver to sender (non-negative). |
| `cred_auto_optimize` | bool | No | `true` | Enable automatic optimization of credit parameters when set to `"auto"`. |
| `cred_headroom` | int | No | `2` | Additional headroom credits beyond computed minimum (non-negative). Used when auto-optimizing credits. |
| `cred_margin_type` | str | No | `"absolute"` | Type of margin to apply to credit values: `"percentage"` or `"absolute"`. |
| `cred_margin_val` | int | No | `0` | Margin value to add to credit calculations. |
| `cred_rounding` | str | No | `"none"` | Rounding strategy for credit values: `"power2"` or `"none"`. |

### CBFC Results

CBFC results include all [common results](#common-results) plus these CBFC-specific results:

| Result | Description |
|--------|-------------|
| `cred_max` | Computed or validated maximum credit pool size |
| `cred_init` | Computed or validated initial credit count |
| `throughput` | Achieved write throughput as a ratio in [0.0, 1.0], normalized to (horizon * w_max). It is populated by the solver after witness extraction. |

### CBFC Recommendations

**Auto Mode Benefits:**

Auto mode (`cred_max="auto"` and `cred_init="auto"`) is recommended because:

1. **Optimal Credit Sizing**: The solver finds the minimal credit configuration that satisfies your traffic requirements, avoiding over-provisioning of credit counters or pools.

2. **Correct Startup Credits**: The solver automatically accounts for credit return latency and startup requirements, ensuring sufficient initial credits to achieve desired throughput before the first credits return.

3. **Adaptive to Traffic Patterns**: The solver analyzes your specific write/read profiles and latencies to determine appropriate credit values, rather than requiring manual calculation.

4. **Built-in Headroom**: Adaptive headroom is automatically added based on read-valid gapiness, providing protection against traffic burstiness.

**When to Use Manual Mode:**

Manual mode is useful when:

- You have pre-existing credit protocol specifications that must be validated
- Hardware constraints dictate specific credit pool sizes (e.g., power-of-2 counter widths)
- You want to verify that a proposed credit configuration is sufficient

**Recommendations:**

- Consider starting with auto mode to understand the minimal credit requirements for your traffic pattern
- Use `cred_headroom` (default: 2) to add safety margin beyond the computed minimum
- Apply `cred_rounding="power2"` if your hardware prefers power-of-2 credit pool sizes
- Use `cred_margin_type` and `cred_margin_val` to add implementation margin to credit values

---

## CDC Solver {#cdc-solver}

### CDC Purpose

The CDC solver handles FIFO depth sizing when the write and read interfaces operate in different clock domains. It implements a two-stage approach:

1. **Small CDC FIFO**: Handles clock domain crossing with Gray-coded pointers and synchronizer latency
2. **Large synchronous FIFO**: Buffers traffic patterns in a single clock domain

This separation is preferred over a single asynchronous FIFO because:

- Gray counter logic is simpler for small, power-of-2 depths
- Most buffering depth can use simpler synchronous FIFO logic
- The CDC solver calculates both the small CDC depth and initial conditions for the downstream synchronous solver

### CDC Overview

The CDC solver computes three critical values:

1. **`depth`** - The required small CDC FIFO buffer depth
2. **`base_sync_fifo_depth`** - The minimum depth for the large synchronous FIFO based on long-term rate mismatch
3. **`rd_sync_cycles_in_wr`** - Read-domain synchronization latency converted to write-domain cycles

These values enable a two-stage solution: the small CDC FIFO handles clock domain crossing, while the computed parameters inform stage 2's solution of the large synchronous FIFO.

**Analytic Solution vs. CP-SAT:**

Unlike other solvers (Ready/Valid, XON/XOFF, CBFC, Replay) which use CP-SAT constraint programming, the CDC solver uses closed-form analytical formulas. This works because:

- **Well-defined latencies**: Synchronization stages, Gray code delays, and phase relationships have deterministic bounds
- **Independent components**: Synchronizer depth, phase margin, and PPM drift can be calculated separately and summed
- **No optimization needed**: There are no tunable parameters to optimize (like thresholds or credits) — the physics of clock domain crossing determines the requirements
- **Computational efficiency**: Analytic formulas execute instantly, while CP-SAT would add unnecessary overhead for a problem with a unique deterministic solution

The CDC depth calculation sums three components:

- **Synchronizer depth**: Latency for pointer synchronization across clock domains (`sync_stages + ptr_gray_extra` converted to items)
- **Phase margin depth**: One read-cycle worth of items to account for unknown initial phase relationship between clocks
- **PPM drift depth**: Accumulated frequency drift over the horizon in both write and read domains

### CDC Parameters

CDC parameters include all [common parameters](#common-parameters) plus these CDC-specific parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `wr_clk_freq` | int or str | Yes | - | Write clock frequency. Can be specified as integer Hz (e.g., `1000000000` for 1 GHz) or string with units (e.g., `"1.1 GHz"`, `"100 MHz"`). Must be positive. |
| `rd_clk_freq` | int or str | Yes | - | Read clock frequency. Can be specified as integer Hz or string with units. Must be positive. |
| `big_fifo_domain` | str | No | `"write"` | Clock domain for the large synchronous FIFO in stage 2: `"write"` or `"read"`. Determines which domain's cycles are used for the `horizon` and traffic pattern analysis. |
| `wr_clk_ppm` | int | No | `0` | Write clock frequency tolerance in parts-per-million (non-negative). Used to calculate worst-case drift over the horizon. |
| `rd_clk_ppm` | int | No | `0` | Read clock frequency tolerance in parts-per-million (non-negative). Used to calculate worst-case drift over the horizon. |
| `sync_stages` | int | No | `2` | Number of synchronizer flip-flop stages for pointer crossing (non-negative). Typical values are 2-3 stages for MTBF requirements. Contributes to synchronization latency. |
| `ptr_gray_extra` | int | No | `1` | Extra Gray code pointer stability margin in cycles (non-negative). Accounts for Gray counter transitions and sampling uncertainty. Typical value is 1. |
| `window_cycles` | int or "auto" | No | `"auto"` | Horizon size in cycles for the `big_fifo_domain`. When `"auto"`, extracted from `horizon` field or compiled from layered profiles. Must be positive when specified as integer. |

### CDC Results

The CDC-specific results are:

| Result | Description |
|--------|-------------|
| `depth` | Required small CDC FIFO buffer depth (after margin and rounding). Sum of `synchronizer_depth`, `phase_margin_depth`, and `ppm_drift_depth`. |
| `synchronizer_depth` | Depth component for synchronization latency. Accounts for `sync_stages` and `ptr_gray_extra` cycles converted from read domain to write domain and scaled by items per cycle. |
| `phase_margin_depth` | Depth component for clock phase uncertainty. Accounts for one read cycle of uncertainty due to unknown relative phase between write and read clocks. |
| `ppm_drift_depth` | Depth component for PPM frequency drift. Accumulated worst-case drift over the horizon in both write and read domains (combined). |
| `base_sync_fifo_depth` | Minimum depth for the large synchronous FIFO in stage 2. Based on long-term rate mismatch over the window: `window_cycles × items_per_cycle × max(0, 1 - f_rd/f_wr)`. |
| `rd_sync_cycles_in_wr` | Read-domain synchronization cycles converted to write-domain cycles. Used as initial condition parameter for stage 2 synchronous FIFO solver. |

Results are saved in file `cdc_results_scalars.json` in the output directory.

### CDC Recommendations

**Margin and Rounding Strategy:**

CDC FIFOs should typically be small and power-of-2 sized for efficient Gray counter implementation. However, automatic margin and rounding can lead to excessive sizing:

- If the solver computes a depth of 13 and you specify 25% margin with power-of-2 rounding, the result will be 32 (potentially excessive)
- **Recommended approach**: Set `margin_val=0` and `rounding="none"` initially, review the computed depth, then manually select an appropriate power-of-2 size
- For critical applications, consider adding 1-2 entries of margin, then rounding up to the next power-of-2

**Clock Domain Selection:**

The `big_fifo_domain` parameter determines which clock domain is used for the large synchronous FIFO in stage 2:

- Set `big_fifo_domain="write"` (default) when the write clock is faster or when traffic patterns are naturally specified in write-domain cycles
- Set `big_fifo_domain="read"` when the read clock is faster, as this may reduce the total depth of the large synchronous FIFO
- The CDC FIFO depth is independent of this choice; only the stage 2 synchronous FIFO is affected

**PPM Tolerance Specification:**

- Set `wr_clk_ppm` and `rd_clk_ppm` to match your oscillator specifications (e.g., 100 ppm for typical crystals)
- Omit or set to 0 if clocks are derived from the same source (frequency-locked)
- PPM drift accumulates over the horizon, so larger windows require proportionally more depth
- Higher PPM values add safety margin but increase CDC FIFO size

**Synchronizer Stage Configuration:**

- Default `sync_stages=2` is standard for most applications and provides sufficient MTBF (Mean Time Between Failures)
- Use `sync_stages=3` for very high-speed designs or stringent reliability requirements
- `ptr_gray_extra=1` (default) accounts for Gray code sampling uncertainty; typically no need to change
- Increasing these values improves reliability but increases synchronization latency and CDC depth

**Analysis Window:**

- Use `window_cycles="auto"` (default) to inherit from the main `horizon` or layered profile specification
- Manually specify `window_cycles` only if you need a different horizon than the synchronous FIFO
- The window should cover the longest traffic burst or congestion period you want to handle

---

## Replay Solver {#replay-solver}

### Replay Purpose

Models replay buffers that hold unacknowledged (in-flight) data until acknowledgements (ACKs) arrive after a round-trip time (RTT). This is needed for protocols that require retransmission capability, where data must be kept until confirmed receipt.

### Replay Overview

The replay FIFO model uses a CP-SAT formulation for consistency with other `fifo_depth_*` solvers. For the standard deterministic case (fixed RTT, single sender, continuous transmission at `w_max`), the solution is equivalent to the classic bandwidth–delay product (BDP):

```text
peak_inflight = min(rtt, horizon - rtt) × w_max
```

The solver enforces that:

- Writes transmit data into the replay buffer
- Acknowledgements arrive exactly `rtt` cycles after the corresponding write
- No new writes occur in the final `rtt` cycles (ensuring the buffer drains to zero by the horizon)
- The buffer must accommodate all in-flight (unacknowledged) data

While the current implementation produces the same result as the analytical BDP formula, the CP-SAT solver serves as a reference implementation and extensibility placeholder for more complex future variants such as:

- Variable `rtt[t]` (jitter, retry delays)
- Credit windows smaller than BDP
- Multiple senders sharing a replay buffer
- Discrete protocol phases (pause, resume, retry)
- Dynamic flow control rules (`w[t]` ≤ function of inflight)
- Non-uniform `w_max` (burst shaping)
- Overlapping atomic tail semantics

Future extensions will leverage this solver framework to capture those non-trivial dynamics without requiring new analytical derivations.

### Replay Parameters

The Replay FIFO is fundamentally different from the previously described Ready / Valid, XON/XOFF, and CBFC FIFOs. It **only supports flat specs** (not layered profiles) and models the transmission/acknowledgement pattern directly. Layered replay is not currently supported because replay buffers inherently depend on temporal ACK structure rather than transaction/burst layering.

Replay supports the [common parameters](#common-parameters) `fifo_type`, `margin_type`, `margin_val`, and `rounding` and these replay-specific parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `horizon` | int | Yes | — | Number of cycles to model (positive integer). Must be ≥ `rtt`. |
| `w_max` | int | No | `1` | Maximum write (transmit) data per cycle (non-negative). Represents the maximum bandwidth of the sender. |
| `atomic_tail` | int | No | `0` | Additional buffer space to reserve beyond the computed in-flight peak (non-negative). Useful for protocol-specific padding or alignment requirements. |
| `rtt` | int | Yes | — | Round-trip time in cycles (positive integer). The delay between a data transmission and its corresponding acknowledgement. Must be ≤ `horizon`. |

### Replay Results

The replay solver results are fundamentally the same as the [common FIFO results](#common-results) in principle, but use more precise terminology specific to replay buffers. In a replay buffer context:

- **Occupancy** (occ) → **Inflight** (infl): The amount of data that has been transmitted but not yet acknowledged
- **Read** (r) → **Acknowledgement** (ack/a): The signal indicating data has been received and can be removed from the replay buffer
- **Write** (w) remains **Write** (w): The transmission of new data

The mapping between common FIFO results and replay-specific results is:

| Common Result | Replay Result | Description |
|---------------|--------------|-------------|
| `depth` | `depth` | Required buffer depth |
| `occ_peak` | `infl_peak` | Peak inflight data (maximum unacknowledged transmissions) |
| `w_seq` | `w_seq` | Write (transmit) sequence over time |
| `r_seq` | `a_seq` | Read (acknowledgement) sequence over time |
| `occ_seq` | `infl_seq` | Occupancy (inflight) sequence over time |

**Why CP-SAT Yields the Same Result as the BDP Equation:**

The CP-SAT solver produces the same result as the analytical bandwidth–delay product (BDP) calculation because of the specific constraints in the current Replay model:

1. **Deterministic Acknowledgements:** Every write at cycle `t` generates an acknowledgement at cycle `t + rtt`. This creates a perfectly predictable in-flight pattern.

2. **Maximum Transmission Rate:** The solver maximizes the objective (peak in-flight data) by transmitting at `w_max` continuously during the valid transmission window.

3. **Drain Constraint:** The requirement that no writes occur in the final `rtt` cycles (ensuring `inflight[horizon] == 0`) creates a symmetric ramp-up and ramp-down pattern.

4. **Peak Occurs at Predictable Time:** Under continuous transmission at `w_max`, in-flight data accumulates linearly until either:
   - Time `rtt` (first acknowledgements arrive), or
   - Time `horizon - rtt` (last writes that will be acknowledged before horizon)

   The peak is therefore `min(rtt, horizon - rtt) × w_max`.

5. **No Alternative Strategies:** The CP-SAT solver explores the solution space but finds no transmission pattern that exceeds this peak. Any change from continuous transmission at `w_max` (e.g., pausing or reducing transmission rate) would only reduce the in-flight accumulation.

The CP-SAT formulation serves as a **reference implementation** that validates the analytical formula and provides a foundation for future extensions where analytical solutions may not exist (variable RTT, multiple senders, flow control, etc.).

---

## Advanced Topics {#advanced-topics}

### Performance Considerations

Solver runtime depends on several factors:

- **Horizon Length:** Longer horizons increase the number of variables and constraints, leading to longer solve times. For layered specs, auto-computed horizons that cover many periods can significantly increase runtime. Layered specs generate multiple periodicities whose least common multiple (LCM) determines the horizon, which directly increases solver variables.
- **Layer Complexity:** Each additional layer (cycle, transaction, burst, stream) increases the combinatorial space the solver must explore. Deeply layered profiles with many bursts or streams are more computationally intensive.
- **Spec Type:** Flat specs are typically solved in seconds, as they have fewer variables and a simpler structure. Layered specs, especially with large horizons or many periods, may take from seconds to several minutes.
- **Traffic Burstiness:** Highly bursty or imbalanced profiles can create more challenging optimization problems, increasing runtime.
- **Parameter Choices:** Using `"auto"` for horizon or specifying a large number of periods can unintentionally create very large problem sizes. Manually limiting the horizon or simplifying profiles can improve performance.

**Recommendations for Efficient Solving:**

- Consider starting with flat specs or small horizons to validate basic behavior.
- Use layered specs for detailed analysis, but minimize the number of periods and layers where possible.
- If solve time is excessive, consider reducing the horizon, simplifying the traffic profile, or using fewer bursts/streams.
- Monitor solver logs for warnings about horizon sufficiency or problem size.

In most practical cases, flat and moderately layered specs solve in under a minute. Only highly complex, deeply layered, or very long-horizon cases should require longer runtimes.

### How Layers Compose {#how-layers-compose}

The tool builds a binary valid pattern (0/1 sequence) by composing layers from innermost (transaction) to outermost (stream):

- **Transaction period** = `valid_cycles` + `gap_cycles`
- **Burst** = `transactions_per_burst` transactions + `gap_cycles`
- **Stream** = `bursts_per_stream` bursts + `gap_cycles`
- **Overall period** = LCM of write and read stream periods

**Worst-Case Pattern Generation:**

The tool uses different strategies based on whether the profile has a single burst or multiple bursts, implementing patterns from FIFO depth calculation literature to create maximum congestion:

**For Write Profiles (maximizing FIFO fill):**

*Single Burst (`bursts_per_stream == 1`):*

- **Uniform valid-first pattern**: All transactions use valid cycles followed by gap cycles
- Maximizes clustering of valid cycles within the burst for safe depth estimation
- No burst boundaries exist to optimize

*Multiple Bursts (`bursts_per_stream > 1`):*

- **Transaction-level alternation**: Transactions within each burst alternate between gap-first and valid-first patterns to achieve valid clustering at burst boundaries
  - Pattern choice depends on burst index parity and `transactions_per_burst` parity
  - Odd-indexed bursts are configured to end with valid cycles
  - Even-indexed bursts ≥ 2 are configured to start with valid cycles
- **Burst-level alternation**: Bursts place gaps strategically to concentrate data in the middle of the observation window
  - First burst (index 0): gap followed by transactions (I,D) - places idle at start
  - Last burst: transactions followed by gap (D,I) - places idle at end
  - Middle bursts alternate:
    - Odd-indexed middle bursts: transactions followed by gap (D,I)
    - Even-indexed middle bursts: gap followed by transactions (I,D)
  - Creates worst-case patterns by concentrating data centrally:
    - 2 bursts: (I,D)(D,I)
    - 3 bursts: (I,D)(D,I)(D,I)
    - 4 bursts: (I,D)(D,I)(I,D)(D,I)

**For Read Profiles (maximizing FIFO drain delay):**

*Single Burst (`bursts_per_stream == 1`):*

- **Uniform gap-first pattern**: All transactions use gap cycles followed by valid cycles
- Maximizes delay by front-loading idle cycles within the burst

*Multiple Bursts (`bursts_per_stream > 1`):*

- **Transaction-level alternation**: Transactions alternate to cluster idle cycles at boundaries
  - Alternation pattern based on combined (burst_index + transaction_index) parity
  - Even parity: valid-first then gap (boundary with next gap-first forms larger idle)
  - Odd parity: gap-first then valid
- **Burst-level alternation**: All burst gaps placed at start to maximize read delay

**Causality Preservation:**

- Write patterns never start with gaps (first burst begins with transactions)
- Read patterns include warmup rotation based on write latency to ensure reads occur after writes
- Guarantees cumulative writes ≥ cumulative reads at all times

This hybrid approach (uniform for single burst, alternating for multi-burst) ensures conservative FIFO depth estimates across all configurations.

---

## FAQ {#faq}

If you encounter performance issues, the first four questions may be helpful to review first.

### Why does the solver sometimes take several minutes to run?

Solver runtime is dominated by:

- **Horizon length** — longer windows → more variables → longer solve time
- **Layer complexity** — cycle + transaction + burst + stream generates deeply nested patterns
- **Burstiness / imbalance** — highly adversarial patterns increase the CP-SAT search space
- **XON/XOFF auto-threshold search** — exploring multiple `(xon, xoff)` candidates can multiply solve time

Flat specifications typically solve in seconds. Layered profiles with multiple streams/periods can take minutes. This is normal and expected based on CP-SAT complexity.

---

### Why does `horizon: auto` sometimes produce very large horizons?

Because the tool must ensure it covers *all* worst-case alignments between the write and read patterns. The auto logic includes:

- multiple full pattern periods (`kmin_blocks`)
- blind window coverage (`blind_window_cycles`)
- LCM of read/write stream periods
- safety padding

This produces a horizon long enough to ensure correctness. If runtime is too long, you may manually set a smaller horizon—but note that making it too small may underestimate FIFO depth.

---

### Why does the depth equal `sum_w_max` for flat ready/valid?

Flat ready/valid has:

- constant write-valid = 1
- constant read-valid = 1
- no temporal structure to exploit

The worst case is:

```text
depth = sum_w_max
```

Because all writes can occur before any reads.

---

### Why does the solver switch from CP-SAT to analytic mode for balanced specs?

A spec is *balanced* when:

```text
(min read density) ≥ (max write density)
```

In this case:

- reads can always drain faster than writes can fill
- CP-SAT can delay reads arbitrarily → problem becomes poorly defined

So the solver automatically switches to a deterministic analytic solver that:

- sweeps phase alignment
- includes latencies
- calculates worst-case occupancy deterministically

This produces a stable, meaningful result.

---

### Why does the XON/XOFF solver choose a higher `xoff` than expected?

Usually because:

- `react_latency` > 0
- `atomic_tail` > 0
- the write pattern is very bursty
- throughput target must be met
- hysteresis constraints limit low values
- low `xoff` would not be feasible

The solver must leave *headroom above xoff* to absorb data written during the reaction latency.

So `xoff` increases when mathematically required for correctness.

---

### Why are thresholds or credits ignored when using auto mode?

In auto mode:

```yaml
thresholds: auto
cred_max: auto
cred_init: auto
```

the solver intentionally ignores user-specified values and computes optimal ones.

To force manual values:

```yaml
thresholds: manual
xon: <value>
xoff: <value>
```

or for CBFC:

```yaml
cred_auto_optimize: false
cred_max: <value>
cred_init: <value>
```

---

### Why is peak occupancy lower than expected?

Common reasons:

- burst/gap structure limits congestion
- XON/XOFF throttling reduces peaks
- CBFC credit return naturally controls writes
- CDC FIFO is limited by synchronizer depth

Many spreadsheet estimates are pessimistic; CP-SAT often finds a tighter true bound.

---

### Why is peak occupancy higher than expected?

Often due to:

- adversarial phase alignment
- large blind window
- write/read latency asymmetry
- clustered burst boundaries
- XON/XOFF reaction overshoot
- CBFC credit-return latency

The solver explores worst-case timing that may not be immediately intuitive.

---

### Why does XON/XOFF auto mode take longer than other solvers?

Because auto mode must:

1. Compute feasible `xon_min`
2. Compute feasible `xoff` range
3. Sweep hysteresis space
4. Solve CP-SAT per candidate
5. Choose the lexicographically optimal configuration

Manual threshold mode is much faster.

---

### Why is replay modeled with CP-SAT if the result is just BDP?

Replay currently follows deterministically from:

```text
peak_inflight = min(rtt, horizon - rtt) × w_max
```

But CP-SAT is used for:

- consistency with other solvers
- reuse of infrastructure
- future support of jitter, retries, multi-sender cases

BDP is just the simplest member of a larger family of replay behaviors.

---

### Why does CDC always use closed-form math instead of CP-SAT?

CDC behavior is governed by:

- synchronizer latency
- Gray code pointer stability
- phase uncertainty
- PPM drift

These have strict analytic bounds and no adversarial scheduling. Closed-form computation is exact and instantaneous.

---

### Why does rounding sometimes jump depth by a large factor?

Two features cause this:

1. **Margin** (percentage or absolute)
2. **Rounding** (`power2`)

Example:

```text
depth_raw = 13
25% margin → 16.25 → 17
round to power of 2 → 32
```

The tool prioritizes safety and hardware alignment.

To avoid over-sizing:

- disable rounding
- or apply zero margin
- inspect raw depth first
- then manually choose rounding

---

### Why does the tool warn that the horizon may be too small?

Because true peak occupancy might occur beyond the examined window.

The heuristic check:

```text
horizon >= (sum_w_max / w_max) + (sum_r_max / r_max)
```

warns when the user-specified horizon may miss the true worst case.

---

### Why are witness traces sometimes non-intuitive?

Because the solver:

1. Builds deterministic worst-case valid masks
2. Then schedules writes/reads adversarially within those masks
3. Maximizes occupancy

This leads to witness patterns that are mathematically valid but may not always follow expected patterns. The witness ensures correctness for the computed FIFO depth.

---

## Appendix {#appendix}

### Key Classes

| Class | Defined In | Role |
|-------|-------------|------|
| `FifoSolver` | `fifo_depth_base.py` | Abstract base class for all solvers |
| `FifoParams` | `fifo_depth_base.py` | Parameter model validated from YAML |
| `FifoResults` | `fifo_depth_base.py` | Container for solver results |
| `CdcSolver` | `fifo_depth_cdc.py` | CDC partition computation |
| `CbfcSolver` | `fifo_depth_cbfc.py` | Credit-based FIFO solver |

---

## References

- W. Dally and B. Towles, [Principles and Practices of Interconnection Networks](https://www.amazon.com/Principles-Practices-Interconnection-Networks-Architecture/dp/0122007514). San Francisco, CA, USA. Morgan Kaufmann Publishers, 2004.
- A. DeJans Jr,  [The MILP Optimization Handbook: An Introduction to Linear and Integer Programming for Practitioners](https://www.amazon.com/dp/B0FPDHVN7T?ref=ppx_yo2ov_dt_b_fed_digi_asin_title_351). Bit Bros LLC, 2025.
- [Google OR-Tools CP-SAT Solver](https://developers.google.com/optimization/cp/cp_solver)
- [Calculation of FIFO Depth - Made Easy](https://hardwaregeeksblog.wordpress.com/wp-content/uploads/2016/12/fifodepthcalculationmadeeasy2.pdf)

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
