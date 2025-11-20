<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: src/abe/rad/rad_cdc_mcp/dv/README.md -->

# `rad_cdc_mcp` — DV Guide

## Overview

This verification environment implements a **dual-agent architecture** to properly model the independent source and destination clock domains of the rad_cdc_mcp dual-clock Multi-Cycle Path (MCP) synchronizer.

## Design Rationale

The rad_cdc_mcp RTL has:

- **a-domain (source)**: Operates on `aclk`, uses `arst_n`, controls `asend` and `adatain`, observes `aready`
- **b-domain (destination)**: Operates on `bclk`, uses `brst_n`, controls `bload`, observes `bdata` and `bvalid`

These domains are **independent** - in a real system, they would be controlled by separate blocks that only see their respective interface signals. This fundamental architectural constraint led to the dual-agent design.

---

## Dual-Agent Architecture

### Agent 0: a-domain (Source)

- **Clock**: `aclk` (default 1000ps period)
- **Reset**: `arst_n`
- **Driver**: `RadCdcMcpWriteDriver` - Drives `asend`, `adatain` on `aclk` edges
- **Monitors**:
  - `RadCdcMcpWriteMonitorIn` - Samples `asend`, `adatain` on `aclk`
  - `RadCdcMcpWriteMonitorOut` - Samples `aready` on `aclk`
- **Item**: `RadCdcMcpWriteItem`
  - Inputs: `asend`, `adatain`
  - Outputs: `aready` (feedback from DUT)
- **Sequence**: `RadCdcMcpWriteSequence`
  - Generates random send transactions with configurable probability (default 0.7)
  - Protocol enforcement handled by driver, not sequence
  - Generates random `adatain` values within configured data width

### Agent 1: b-domain (Destination)

- **Clock**: `bclk` (default 1200ps period)
- **Reset**: `brst_n`
- **Driver**: `RadCdcMcpReadDriver` - Drives `bload` on `bclk` edges
- **Monitors**:
  - `RadCdcMcpReadMonitorIn` - Samples `bload` on `bclk`
  - `RadCdcMcpReadMonitorOut` - Samples `bdata`, `bvalid` on `bclk`
- **Item**: `RadCdcMcpReadItem`
  - Inputs: `bload`
  - Outputs: `bdata`, `bvalid` (feedback from DUT)
- **Sequence**: `RadCdcMcpReadSequence`
  - Generates random load transactions with configurable probability (default 0.7)
  - Protocol enforcement not required (driver does not implement backpressure)

---

## Component Structure

```text
RadCdcMcpEnv (num_agents=2)
├── agent0 (a-domain / source)
│   ├── drv: RadCdcMcpWriteDriver
│   ├── sqr: BaseSequencer[RadCdcMcpWriteItem]
│   ├── mon_in: RadCdcMcpWriteMonitorIn
│   └── mon_out: RadCdcMcpWriteMonitorOut
├── agent1 (b-domain / destination)
│   ├── drv: RadCdcMcpReadDriver
│   ├── sqr: BaseSequencer[RadCdcMcpReadItem]
│   ├── mon_in: RadCdcMcpReadMonitorIn
│   └── mon_out: RadCdcMcpReadMonitorOut
├── mon_rst: BaseResetMonitor (arst_n, configured but not used)
├── reset_sink: BaseResetSink (configured but not used)
├── mon_arst: BaseResetMonitor (arst_n) → arst_sink
├── mon_brst: BaseResetMonitor (brst_n) → brst_sink
├── arst_sink: RadCdcMcpResetSink → routes to ref_model.arst_change()
├── brst_sink: RadCdcMcpResetSink → routes to ref_model.brst_change()
├── sb: RadCdcMcpSb
│   ├── prd: RadCdcMcpSbPredictor[RadCdcMcpRefModel]
│   └── cmp: BaseSbComparator
└── cov: RadCdcMcpCoverage
```

---

## Test Execution Flow

1. **Clock Setup**: Test creates independent `aclk_driver` and `bclk_driver`
2. **Reset Setup**: Test creates independent `arst_driver` and `brst_driver`
3. **Factory Overrides**: Instance-specific overrides for each agent
   - `*.agent0.*` → a-domain (source) components
   - `*.agent1.*` → b-domain (destination) components
4. **Run Phase**: Sequences run **concurrently** using `cocotb.start_soon()`

   ```python
   write_task = cocotb.start_soon(write_seq.start(self.env.agents[0].sqr))
   read_task = cocotb.start_soon(read_seq.start(self.env.agents[1].sqr))

   await write_task
   await read_task
   ```

---

## Protocol Enforcement (Backpressure)

Backpressure is handled in the **drivers**, not the sequences. This separation allows:

- Sequences to focus on stimulus generation (probabilities, patterns)
- Drivers to enforce protocol correctness (respecting ready/valid flags)

### a-domain Driver (Write) Backpressure

The a-domain driver samples `aready` at each drive edge and stalls if necessary:

```python
while True:
    await self.clock_drive_edge()  # Advance to negedge of aclk

    aready_now = utils_dv.get_signal_value_int(dut.aready.value)

    if tr.asend and not aready_now:
        # Backpressure: MCP is not ready, stall this send
        dut.asend.value = 0
        # Loop to next cycle and re-check aready
    else:
        # Either no send requested, or MCP is ready
        dut.asend.value = tr.asend
        dut.adatain.value = tr.adatain
        break  # Exit after successful drive
```

### b-domain Driver (Read) - No Backpressure

The b-domain driver does not implement backpressure logic:

```python
await self.clock_drive_edge()  # Advance to negedge of bclk

dut.bload.value = tr.bload
# Can always drive bload regardless of bvalid state
```

### Sequence Generation

Sequences generate transactions based on probability, independent of MCP state:

```python
# a-domain send sequence
item.asend = 1 if random.random() < self.send_prob else 0
if item.asend:
    item.adatain = random.randint(0, (1 << self.dsize) - 1)

# b-domain load sequence
item.bload = 1 if random.random() < self.load_prob else 0
```

This design ensures protocol correctness while allowing flexible stimulus patterns.

---

## Reset Handling

The environment supports **independent reset domains** with domain-specific routing:

- **a-domain Reset Path**: `mon_arst` → `arst_sink` → `ref_model.arst_change()`
- **b-domain Reset Path**: `mon_brst` → `brst_sink` → `ref_model.brst_change()`

Each reset sink (`RadCdcMcpResetSink`) routes reset events to:

1. The corresponding driver (agent0.drv or agent1.drv) via `drv.reset_change()`
2. The reference model's domain-specific method (`arst_change` or `brst_change`)

The reference model (`RadCdcMcpRefModel`) implements:

- `arst_change(value, active)`: Clears a-domain state when active
- `brst_change(value, active)`: Clears b-domain state when active
- `reset_change(value, active)`: Legacy single-reset method (clears both domains)

---

## Key Design Decisions

### Why Dual Agents?

Rejected alternatives:

1. ❌ Single sequence controlling both domains - unrealistic, violates clock domain separation
2. ❌ Dual sequences with single agent - complexity in driver/sequencer routing
3. ❌ Single sequence with dual clock driver - doesn't model real system behavior
4. ✅ **Dual agents** - clean separation, matches real system architecture

### Why Backpressure in a-domain Driver Only?

- **Protocol enforcement** separate from **stimulus generation**
- a-domain (source) must respect `aready` to ensure MCP can accept data
- b-domain (destination) can assert `bload` freely; data validity is checked via `bvalid`
- Sequences focus on test patterns (random, burst, corner cases)
- Drivers ensure protocol correctness at the interface level
- Models real hardware behavior: protocol is enforced at interface level

### Why cocotb.start_soon?

- Both sequences must run **concurrently** (not sequentially)
- Send and load operations happen simultaneously in different clock domains
- `cocotb.start_soon()` is the cocotb-native way to launch concurrent tasks
- Unlike `asyncio.gather()`, it works properly with cocotb's scheduler

---

## Files

### Transaction Items

- `rad_cdc_mcp_item.py` - Contains both transaction classes:
  - `RadCdcMcpWriteItem` - a-domain (asend, adatain, aready)
  - `RadCdcMcpReadItem` - b-domain (bload, bdata, bvalid)

### Drivers

- `rad_cdc_mcp_driver.py` - Contains both driver classes:
  - `RadCdcMcpWriteDriver` - Drives a-domain inputs on aclk with backpressure
  - `RadCdcMcpReadDriver` - Drives b-domain inputs on bclk (no backpressure)

### Sequences

- `rad_cdc_mcp_sequence.py` - Contains both sequence classes:
  - `RadCdcMcpWriteSequence` - Generates send transactions
  - `RadCdcMcpReadSequence` - Generates load transactions

### Monitors

- `rad_cdc_mcp_monitor_in.py` - Contains both input monitor classes:
  - `RadCdcMcpWriteMonitorIn` - Samples asend, adatain on aclk
  - `RadCdcMcpReadMonitorIn` - Samples bload on bclk
- `rad_cdc_mcp_monitor_out.py` - Contains both output monitor classes:
  - `RadCdcMcpWriteMonitorOut` - Samples aready on aclk
  - `RadCdcMcpReadMonitorOut` - Samples bdata, bvalid on bclk

### Environment & Test

- `rad_cdc_mcp_env.py` - Environment with `num_agents=2` and dual reset monitors
- `test_rad_cdc_mcp.py` - Test with dual clocks/resets/sequences

### Shared Components

- `rad_cdc_mcp_ref_model.py` - Golden model with dual-reset support
- `rad_cdc_mcp_coverage.py` - Functional coverage for both domains
- `rad_cdc_mcp_reset_sink.py` - Reset event router with configurable method names

---

## Configuration

### Clock Configuration

```bash
# a-domain clock (default 1000ps)
ACLK_PERIOD_PS=1000 ACLK_ENABLE=1

# b-domain clock (default 1200ps, shows async behavior)
BCLK_PERIOD_PS=1200 BCLK_ENABLE=1
```

### Reset Configuration

```bash
# a-domain reset
ARST_ENABLE=1 ARST_ACTIVE_LOW=1 ARST_CYCLES=10

# b-domain reset
BRST_ENABLE=1 BRST_ACTIVE_LOW=1 BRST_CYCLES=10
```

### Sequence Configuration

```bash
# a-domain sequence length (number of send transactions)
RAD_CDC_MCP_WRITE_SEQ_LEN=100

# b-domain sequence length (number of load transactions)
RAD_CDC_MCP_READ_SEQ_LEN=100
```

### MCP Configuration

```bash
# Data width (default 8 bits)
RAD_CDC_MCP_DSIZE=8
```

---

## Future Enhancements

Potential improvements:

1. **Variable timing sequences**: Add random delays between transactions
2. **Burst sequences**: Send/load bursts with configurable patterns
3. **Stress sequences**: Maximum rate sends and loads
4. **Corner case sequences**: Single item, simultaneous send/load edge cases
5. **Protocol violations**: Intentionally violate timing constraints
6. **Coverage-driven**: Use coverage feedback to guide sequence generation
7. **Back-to-back operations**: Test consecutive sends/loads without idle cycles

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
