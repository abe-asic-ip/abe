<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: src/abe/rad/rad_cdc_sync/dv/README.md -->

# `rad_cdc_sync` — DV Guide

## Overview

This verification environment implements a **single-agent architecture** to verify the rad_cdc_sync multi-stage clock domain crossing synchronizer. The DUT is a simple pipeline of flip-flops that synchronizes an asynchronous input signal to the destination clock domain.

## Design Rationale

The rad_cdc_sync RTL has:

- **Synchronous domain**: Operates on `clk`, uses `rst_n`, observes `sync_o`
- **Asynchronous input**: `async_i` can toggle at arbitrary times relative to `clk`
- **Parameterizable stages**: `STAGES` (default 2) determines synchronizer depth
- **Optional metastability simulation**: When `SIMULATE_METASTABILITY` is defined, models metastability injection

The DUT performs a single function: synchronizing an asynchronous signal into the clock domain. This straightforward architecture requires only a single agent to drive the async input and monitor the synchronized output.

## Single-Agent Architecture

### Agent 0: Synchronous Domain

- **Clock**: `clk` (default 1000ps period)
- **Reset**: `rst_n`
- **Driver**: `RadCdcSyncDriver` - Drives `async_i` with timing jitter relative to `clk` edges
- **Monitors**:
    - `RadCdcSyncMonitorIn` - Samples `async_i` on `clk` (for reference model input)
    - `RadCdcSyncMonitorOut` - Samples `sync_o` on `clk` (synchronized output)
- **Item**: `RadCdcSyncItem`
    - Inputs: `async_i`, `delay_ps` (pre-toggle jitter)
    - Outputs: `sync_o` (synchronized output from DUT)
- **Sequence**: `RadCdcSyncSequence`
    - Generates toggling pattern with timing jitter to stress metastability
    - Enforces visible transitions (state alternates 0 → 1 → 0 → 1)
    - Applies random delay in ±20% window around half clock period

---

## Component Structure

```text
RadCdcSyncEnv (num_agents=1)
├── agent0 (synchronous domain)
│   ├── drv: RadCdcSyncDriver
│   ├── sqr: BaseSequencer[RadCdcSyncItem]
│   ├── mon_in: RadCdcSyncMonitorIn
│   └── mon_out: RadCdcSyncMonitorOut
├── mon_rst: BaseResetMonitor (rst_n)
├── reset_sink: BaseResetSink → routes to ref_model.reset_change()
├── sb: RadCdcSyncSb
│   ├── prd: RadCdcSyncSbPredictor[RadCdcSyncRefModel]
│   └── cmp: BaseSbComparator
└── cov: RadCdcSyncCoverage
```

---

## Test Execution Flow

1. **Clock Setup**: Test creates single `clk_driver`
2. **Reset Setup**: Test creates single `rst_driver`
3. **Factory Overrides**: Type-level overrides for all components
4. **Run Phase**: Single sequence runs on agent0.sqr

   ```python
   seq = RadCdcSyncSequence.create()
   await seq.start(self.env.agents[0].sqr)
   ```

---

## Timing and Jitter

The verification strategy focuses on stressing the synchronizer's metastability handling by varying the timing relationship between `async_i` transitions and the `clk` edge.

### Driver Timing Strategy

The driver applies each transaction with configurable jitter:

```python
async def drive_item(self, dut: Any, tr: RadCdcSyncItem) -> None:
    await self.clock_drive_edge()  # Align to clock edge
    await Timer(tr.delay_ps, unit="ps")  # Apply jitter
    dut.async_i.value = tr.async_i  # Toggle the async input
```

### Sequence Jitter Generation

The sequence generates jitter within ±20% of the clock period around the half-period point:

```python
# For 1000ps clock: setup=400ps, hold=600ps
# Jitter range: 400ps to 600ps after drive edge
t = self.clock_period_ps
win = t // 5  # 20% window
setup = (t // 2) - win  # Half period minus window
hold = (t // 2) + win   # Half period plus window
item.delay_ps = random.randrange(setup, hold)
```

This creates transitions that occur near the sampling edge of the destination clock, maximizing the likelihood of metastability in RTL simulations with metastability modeling enabled.

### Toggle Enforcement

To ensure observable behavior, the sequence enforces alternating values:

```python
self._state ^= 1  # Toggle internal state
item.async_i = self._state  # Always produces visible transitions
```

This prevents repeated same-value "toggles" that would be invisible to the synchronizer.

---

## Reference Model

The `RadCdcSyncRefModel` implements a shift register matching the RTL's synchronizer chain:

- **Configuration**: Reads `RAD_CDC_STAGES` (default 2) and `RAD_CDC_VAL_ON_RESET` (default 0)
- **Internal state**: `_shreg` - deque of length `STAGES` representing the synchronizer pipeline
- **Operation**:
  1. On each input transaction, shift `async_i` into the front of the deque
  2. The last element of the deque represents the synchronized output
  3. During reset, all stages are initialized to `val_on_reset`

```python
def calc_exp(self, tr: RadCdcSyncItem) -> RadCdcSyncItem:
    if self._reset_active:
        tr.sync_o = self.val_on_reset
        return tr
    async_i = int(tr.async_i or 0)
    self._shreg.appendleft(async_i)  # Shift in new value
    tr.sync_o = self._shreg[-1]      # Output is last stage
    return tr
```

---

## Reset Handling

The environment supports single-domain reset with standard routing:

- **Reset Path**: `mon_rst` → `reset_sink` → `ref_model.reset_change()`

The reset sink routes reset events to:

1. The driver via `drv.reset_change()` to handle drive-edge waiting
2. The reference model to clear internal state

---

## Metastability Simulation

When the RTL is compiled with `SIMULATE_METASTABILITY` defined:

- The DUT can inject metastable values (X) on setup/hold violations
- The injection window is configurable via `rad_cdc_meta_cfg_pkg`
- Random seed control: `+RAD_CDC_RAND_SEED=<value>`
- Injection messages: Controlled by `PRINT_INJECTION_MESSAGES` parameter

The testbench handles metastability:

- Reference model ignores X values (treats as previous stable value)
- Comparator waits for resolution before checking
- Coverage tracks metastability events when enabled

---

## Key Design Decisions

### Why Single Agent?

The rad_cdc_sync DUT has no clock domain crossing in the traditional multi-clock sense:

- Only one clock domain (`clk`) drives the synchronous logic
- The `async_i` input is truly asynchronous (no associated clock)
- No protocol or handshaking between domains
- Simple pipeline structure

Therefore:

- ✅ **Single agent** - matches the single synchronous clock domain
- ❌ Dual agents would be unnecessary complexity for this simple DUT

### Why Timing Jitter?

The critical verification challenge for synchronizers is metastability:

- Transitions near the clock edge can cause metastable states
- Varying the timing relationship stresses the synchronizer
- Jitter creates setup/hold violations when metastability simulation is enabled
- Deterministic timing patterns would miss corner cases

### Why Toggle Enforcement?

Observable verification requires visible signal changes:

- Random values might accidentally repeat (e.g., 1 → 1)
- Repeated values don't propagate through the synchronizer
- Alternating pattern guarantees every transaction creates observable behavior
- Simplifies debug and coverage analysis

---

## Configuration

Configure via environment variables or plusargs:

```bash
# Synchronizer stages (must be >= 2)
+RAD_CDC_STAGES=3

# Reset value for all stages
+RAD_CDC_VAL_ON_RESET=1

# Sequence length
+RAD_CDC_SYNC_SEQ_LEN=200

# Random seed (for metastability injection when enabled)
+RAD_CDC_RAND_SEED=42
```

---

## Licensing

See the `LICENSES` directory at the repository root.
