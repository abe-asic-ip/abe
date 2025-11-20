<!--
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT
-->

<!--- This file: docs/pkt_quantize.md -->

# Packet Quantization Calculator

This tool calculates packet processing performance metrics—**cycles**, **latency**, **bandwidth**, and **packets per second (PPS)**—for packet quantization given a range of packet sizes, bus width, and clock frequency. It also generates output tables, CSV files, and plots. It assumes two packets cannot share a beat of the bus (e.g. AXI-Stream).

See also: [ABE Python Development](python_dev.md) for development tools.

---

## Project Structure

```bash
abe/
├── src/abe/uarch/pkt_quantize.py   # Main script
├── src/abe/utils.py                # Utilities
└── out_uarch_pkt_quantize/         # Output directory (created automatically)
```

---

## Command-Line Usage

```bash
pkt-quantize [options]
```

---

### Configuration Options

| Option             | Description                                         | Default                   |
|--------------------|-----------------------------------------------------|---------------------------|
| `--bus-width`      | Bus width (bytes)                                   | `128`                     |
| `--clk-freq`       | Clock frequency (Hz)                                | `1.1e9`                   |
| `--min-cycles`     | Minimum clock cycles to process a packet            | `1`                       |
| `--min-size`       | Minimum packet size (bytes)                         | `64`                      |
| `--max-size`       | Maximum packet size (bytes)                         | `1518`                    |
| `--outdir`         | Output directory                                    | `out_uarch_pkt_quantize/` |
| `--no-plot-save`   | Skip saving plots to PNG                            | Off                       |
| `--no-plot-show`   | Skip displaying plots in GUI                        | Off                       |
| `--log-level`      | Logging level (`debug`, `info`, `warning`, `error`) | `info`                    |

---

## Outputs

Files are written to the `--outdir` directory:

- `table_<config>_abbrev.txt` — Abbreviated table of results (Markdown-style)
- `table_<config>_full.txt` — Full table of results (Markdown-style)
- `table_<config>.csv` — CSV-formatted results
- `plot_bw_<config>.png` — Bandwidth vs packet size plot
- `plot_pps_<config>.png` — PPS vs packet size plot

---

## Import as a Library

You can import the `PktQuantize` class into another Python program.

```python
from abe.uarch.pkt_quantize import PktQuantize

# Create instance with custom parameters
pq = PktQuantize(
    bus_width=64,
    clk_freq=1.5e9,
    min_cycles=2,
    min_size=64,
    max_size=512
)

# Run calculations
pq.calc()

# Access results
for size, stats in pq.pkt.items():
    print(f"Size: {size}, BW: {stats.bw / 1e9:.3f} Gbps")
```

---

## Example

```bash
pkt-quantize --bus-width 64 --clk-freq 1.5e9 --min-cycles 2 --min-size 64 --max-size 512
```

---

## Licensing

See the `LICENSES` directory at the repository root.

---

## Author

[Hugh Walsh](https://linkedin.com/in/hughwalsh)
