<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: src/abe/rad/rad_async_fifo/dv/README.md -->

# `rad_async_fifo` — DV Guide

## Overview

This verification environment implements a **dual-agent architecture** to properly model the independent write and read clock domains of the rad_async_fifo dual-clock asynchronous FIFO.

---

## Design Rationale

The rad_async_fifo RTL has:

- **Write domain**: Operates on `wclk`, uses `wrst_n`, controls `winc` and `wdata`, observes `wfull`
- **Read domain**: Operates on `rclk`, uses `rrst_n`, controls `rinc`, observes `rdata` and `rempty`

These domains are **independent** - in a real system, they would be controlled by separate blocks that only see their respective interface signals. This fundamental architectural constraint led to the dual-agent design.

## Dual-Agent Architecture

### Agent 0: Write Domain

- **Clock**: `wclk` (default 1000ps period)
- **Reset**: `wrst_n`
- **Driver**: `RadAsyncFifoWriteDriver` - Drives `winc`, `wdata` on `wclk` edges
- **Monitors**:
  - `RadAsyncFifoWriteMonitorIn` - Samples `winc`, `wdata` on `wclk`
  - `RadAsyncFifoWriteMonitorOut` - Samples `wfull` on `wclk`
- **Item**: `RadAsyncFifoWriteItem`
  - Inputs: `winc`, `wdata`
  - Outputs: `wfull` (feedback from DUT)
- **Sequence**: `RadAsyncFifoWriteSequence`
  - Generates random write transactions with configurable probability (default 0.7)
  - Protocol enforcement handled by driver, not sequence
  - Generates random `wdata` values within configured data width

### Agent 1: Read Domain

- **Clock**: `rclk` (default 1200ps period)
- **Reset**: `rrst_n`
- **Driver**: `RadAsyncFifoReadDriver` - Drives `rinc` on `rclk` edges
- **Monitors**:
  - `RadAsyncFifoReadMonitorIn` - Samples `rinc` on `rclk`
  - `RadAsyncFifoReadMonitorOut` - Samples `rdata`, `rempty` on `rclk`
- **Item**: `RadAsyncFifoReadItem`
  - Inputs: `rinc`
  - Outputs: `rdata`, `rempty` (feedback from DUT)
- **Sequence**: `RadAsyncFifoReadSequence`
  - Generates random read transactions with configurable probability (default 0.7)
  - Protocol enforcement handled by driver, not sequence

---

## Component Structure

```text
RadAsyncFifoEnv (num_agents=2)
├── agent0 (write domain)
│   ├── drv: RadAsyncFifoWriteDriver
│   ├── sqr: BaseSequencer[RadAsyncFifoWriteItem]
│   ├── mon_in: RadAsyncFifoWriteMonitorIn
│   └── mon_out: RadAsyncFifoWriteMonitorOut
├── agent1 (read domain)
│   ├── drv: RadAsyncFifoReadDriver
│   ├── sqr: BaseSequencer[RadAsyncFifoReadItem]
│   ├── mon_in: RadAsyncFifoReadMonitorIn
│   └── mon_out: RadAsyncFifoReadMonitorOut
├── mon_rst: BaseResetMonitor (wrst_n, configured but not used)
├── reset_sink: BaseResetSink (configured but not used)
├── mon_wrst: BaseResetMonitor (wrst_n) → wrst_sink
├── mon_rrst: BaseResetMonitor (rrst_n) → rrst_sink
├── wrst_sink: RadAsyncFifoResetSink → routes to ref_model.wrst_change()
├── rrst_sink: RadAsyncFifoResetSink → routes to ref_model.rrst_change()
├── sb: RadAsyncFifoSb
│   ├── prd: RadAsyncFifoSbPredictor[RadAsyncFifoRefModel]
│   └── cmp: BaseSbComparator
└── cov: RadAsyncFifoCoverage
```

---

## Test Execution Flow

1. **Clock Setup**: Test creates independent `wclk_driver` and `rclk_driver`
2. **Reset Setup**: Test creates independent `wrst_driver` and `rrst_driver`
3. **Factory Overrides**: Instance-specific overrides for each agent
   - `*.agent0.*` → Write components
   - `*.agent1.*` → Read components
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
- Drivers to enforce protocol correctness (respecting full/empty flags)

### Write Driver Backpressure

The write driver samples `wfull` at each drive edge and stalls if necessary:

```python
while True:
    await self.clock_drive_edge()  # Advance to negedge of wclk

    wfull_now = utils_dv.get_signal_value_int(dut.wfull.value)

    if tr.winc and wfull_now:
        # Backpressure: FIFO is full, stall this write
        dut.winc.value = 0
        # Loop to next cycle and re-check wfull
    else:
        # Either no write requested, or FIFO is not full
        dut.winc.value = tr.winc
        dut.wdata.value = tr.wdata
        break  # Exit after successful drive
```

### Read Driver Backpressure

The read driver samples `rempty` at each drive edge and stalls if necessary:

```python
while True:
    await self.clock_drive_edge()  # Advance to negedge of rclk

    rempty_now = utils_dv.get_signal_value_int(dut.rempty.value)

    if tr.rinc and rempty_now:
        # Backpressure: FIFO is empty, stall this read
        dut.rinc.value = 0
        # Loop to next cycle and re-check rempty
    else:
        # Either no read requested, or FIFO is not empty
        dut.rinc.value = tr.rinc
        break  # Exit after successful drive
```

### Sequence Generation

Sequences generate transactions based on probability, independent of FIFO state:

```python
# Write sequence
item.winc = 1 if random.random() < self.write_prob else 0
if item.winc:
    item.wdata = random.randint(0, (1 << self.dsize) - 1)

# Read sequence
item.rinc = 1 if random.random() < self.read_prob else 0
```

This design ensures protocol correctness while allowing flexible stimulus patterns.

---

## Reset Handling

The environment supports **independent reset domains** with domain-specific routing:

- **Write Reset Path**: `mon_wrst` → `wrst_sink` → `ref_model.wrst_change()`
- **Read Reset Path**: `mon_rrst` → `rrst_sink` → `ref_model.rrst_change()`

Each reset sink (`RadAsyncFifoResetSink`) routes reset events to:

1. The corresponding driver (agent0.drv or agent1.drv) via `drv.reset_change()`
2. The reference model's domain-specific method (`wrst_change` or `rrst_change`)

The reference model (`RadAsyncFifoRefModel`) implements:

- `wrst_change(value, active)`: Clears write-domain state when active
- `rrst_change(value, active)`: Clears read-domain state when active
- `reset_change(value, active)`: Legacy single-reset method (clears both domains)

---

## Key Design Decisions

### Why Dual Agents?

Rejected alternatives:

1. ❌ Single sequence controlling both domains - unrealistic, violates clock domain separation
2. ❌ Dual sequences with single agent - complexity in driver/sequencer routing
3. ❌ Single sequence with dual clock driver - doesn't model real system behavior
4. ✅ **Dual agents** - clean separation, matches real system architecture

### Why Backpressure in Drivers?

- **Protocol enforcement** separate from **stimulus generation**
- Sequences focus on test patterns (random, burst, corner cases)
- Drivers ensure protocol correctness (never write when full, never read when empty)
- Allows reuse of driver logic across different sequence types
- Models real hardware behavior: protocol is enforced at interface level

### Why cocotb.start_soon?

- Both sequences must run **concurrently** (not sequentially)
- Write and read operations happen simultaneously in different clock domains
- `cocotb.start_soon()` is the cocotb-native way to launch concurrent tasks
- Unlike `asyncio.gather()`, it works properly with cocotb's scheduler

---

## Files

### Transaction Items

- `rad_async_fifo_item.py` - Contains both transaction classes:
  - `RadAsyncFifoWriteItem` - Write domain (winc, wdata, wfull)
  - `RadAsyncFifoReadItem` - Read domain (rinc, rdata, rempty)

### Drivers

- `rad_async_fifo_driver.py` - Contains both driver classes:
  - `RadAsyncFifoWriteDriver` - Drives write inputs on wclk
  - `RadAsyncFifoReadDriver` - Drives read inputs on rclk

### Sequences

- `rad_async_fifo_sequence.py` - Contains both sequence classes:
  - `RadAsyncFifoWriteSequence` - Generates write transactions
  - `RadAsyncFifoReadSequence` - Generates read transactions

### Monitors

- `rad_async_fifo_monitor_in.py` - Contains both input monitor classes:
  - `RadAsyncFifoWriteMonitorIn` - Samples winc, wdata on wclk
  - `RadAsyncFifoReadMonitorIn` - Samples rinc on rclk
- `rad_async_fifo_monitor_out.py` - Contains both output monitor classes:
  - `RadAsyncFifoWriteMonitorOut` - Samples wfull on wclk
  - `RadAsyncFifoReadMonitorOut` - Samples rdata, rempty on rclk

### Environment & Test

- `rad_async_fifo_env.py` - Environment with `num_agents=2` and dual reset monitors
- `test_rad_async_fifo.py` - Test with dual clocks/resets/sequences

### Shared Components

- `rad_async_fifo_ref_model.py` - Golden model with dual-reset support
- `rad_async_fifo_coverage.py` - Functional coverage for both domains
- `rad_async_fifo_reset_sink.py` - Reset event router with configurable method names

---

## Configuration

### Clock Configuration

```bash
# Write clock (default 1000ps)
WCLK_PERIOD_PS=1000 WCLK_ENABLE=1

# Read clock (default 1200ps, shows async behavior)
RCLK_PERIOD_PS=1200 RCLK_ENABLE=1
```

### Reset Configuration

```bash
# Write reset
WRST_ENABLE=1 WRST_ACTIVE_LOW=1 WRST_CYCLES=10

# Read reset
RRST_ENABLE=1 RRST_ACTIVE_LOW=1 RRST_CYCLES=10
```

### Sequence Configuration

```bash
# Write sequence length (number of transactions)
RAD_ASYNC_FIFO_WRITE_SEQ_LEN=100

# Read sequence length (number of transactions)
RAD_ASYNC_FIFO_READ_SEQ_LEN=100
```

### FIFO Configuration

```bash
# Data width (default 8 bits)
RAD_ASYNC_FIFO_DSIZE=8

# Address width determines depth = 2^ASIZE (default 3 → depth=8)
RAD_ASYNC_FIFO_ASIZE=3
```

---

## Future Enhancements

Potential improvements:

1. **Variable timing sequences**: Add random delays between transactions
2. **Burst sequences**: Write/read bursts until full/empty
3. **Stress sequences**: Maximum rate writes and reads
4. **Corner case sequences**: Single item, wrap-around, simultaneous full/empty
5. **Protocol violations**: Intentionally violate timing constraints
6. **Coverage-driven**: Use coverage feedback to guide sequence generation

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
