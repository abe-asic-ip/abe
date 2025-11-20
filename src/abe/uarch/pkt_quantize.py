# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/pkt_quantize.py

"""
Tool to calculate bandwidth and packet rate of packet quantization,
assuming two packets cannot share a beat of the bus (e.g. AXI-Stream).
"""

import argparse
import csv
import logging
import math
from dataclasses import dataclass
from typing import Sequence

import matplotlib.pyplot as plt
from tabulate import tabulate

try:
    # when imported as a package
    from abe.utils import (
        PlotLine,
        ensure_dir,
    )
except (ImportError, ModuleNotFoundError):
    # when run as a standalone script
    from abe.utils import (
        PlotLine,
        ensure_dir,
    )

logger = logging.getLogger(__name__)


@dataclass
class PktStats:
    """Holds performance metrics for a specific packet size."""

    size: int
    cycles: int
    time: float
    pps: float  # packets per second
    bw: float  # bits per second


class PktQuantize:
    """Computes performance metrics for a packet quantization."""

    # pylint: disable=too-many-positional-arguments
    def __init__(  # pylint: disable=too-many-arguments
        self,
        bus_width: int = 128,  # bytes
        clk_freq: float = 1.1e9,  # Hz
        min_cycles: int = 1,
        min_size: int = 64,  # bytes
        max_size: int = 1518,  # bytes
    ):
        """Initialize the quantization configuration and packet range."""
        self.bus_width = bus_width
        self.clk_freq = clk_freq
        self.min_cycles = min_cycles
        self.min_size = min_size
        self.max_size = max_size
        self.pkt: dict[int, PktStats] = {}

    def name(self) -> str:
        """Return a name string based on configuration."""
        part1 = f"{self.bus_width}_{int(self.clk_freq / 1e6)}_{self.min_cycles}"
        part2 = f"_{self.min_size}_{self.max_size}"
        return part1 + part2

    def calc_cycles(self, p: int) -> int:
        """Calculate clock cycles to process a packet of size p."""
        return max(math.ceil(p / self.bus_width), self.min_cycles)

    def calc(self) -> None:
        """Compute and store metrics for all packet sizes."""
        for p in range(self.min_size, self.max_size + 1):
            cycles = self.calc_cycles(p)
            time = cycles / self.clk_freq
            pps = 1 / time
            bw = 8 * p * pps
            self.pkt[p] = PktStats(size=p, cycles=cycles, time=time, pps=pps, bw=bw)

    def print_table(
        self,
        outdir: str = "out_uarch_pkt_quantize",
        abbrev: bool = True,
        echo: bool = True,
    ) -> None:
        """Print and save a table of results (abbreviated or full)."""
        rows: list[list[object]] = []
        for size in sorted(self.pkt):
            s = self.pkt[size]
            if (
                abbrev
                and s.size != self.min_size
                and s.size != self.max_size
                and s.size % self.bus_width > 1
            ):
                continue
            rows.append(
                [
                    s.size,
                    s.cycles,
                    f"{s.time * 1e9:.3f}",
                    f"{s.pps / 1e6:.3f}",
                    f"{s.bw / 1e9:.3f}",
                ]
            )
        headers = ["Size", "Cycles", "Time (ns)", "PPS (M)", "BW (Gbps)"]
        if echo:
            print(tabulate(rows, headers=headers, tablefmt="github"))
        filename = f"table_{self.name()}_{'abbrev' if abbrev else 'full'}.txt"
        path = ensure_dir(outdir, True) / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            print(tabulate(rows, headers=headers, tablefmt="github"), file=f)
        logger.info("Saved table: %s", path)

    def print_csv(self, outdir: str = "out_uarch_pkt_quantize") -> None:
        """Write results to CSV with full packet range."""
        path = ensure_dir(outdir, True) / f"table_{self.name()}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Size", "Cycles", "Time (ns)", "PPS (M)", "BW (Gbps)"])
            for size in sorted(self.pkt):
                p = self.pkt[size]
                writer.writerow(
                    [
                        p.size,
                        p.cycles,
                        round(p.time * 1e9, 3),
                        round(p.pps / 1e6, 3),
                        round(p.bw / 1e9, 3),
                    ]
                )
        logger.info("Saved CSV: %s", path)

    def plot_all(
        self,
        show: bool = True,
        save: bool = True,
        outdir: str = "out_uarch_pkt_quantize",
    ) -> None:
        """Generate and display/save PPS and bandwidth plots."""
        sizes = sorted(self.pkt.keys())
        ppss = [self.pkt[s].pps / 1e6 for s in sizes]  # Mpps
        bws = [self.pkt[s].bw / 1e9 for s in sizes]  # Gbps

        # PPS Plot
        p1 = PlotLine(outdir)
        p1.add_line(sizes, ppss, label="Packets per Second", color="red")
        p1.set_labels(
            "Packet Size (Bytes)",
            "Packets per Second (Mpps)",
            "Packets per Second vs. Packet Size",
        )
        p1.format()
        if save:
            p1.save(f"plot_pps_{self.name()}")
        if show:
            p1.show(block=False)

        # Bandwidth Plot
        p2 = PlotLine(outdir)
        p2.add_line(sizes, bws, label="Bandwidth", color="blue")
        p2.set_labels(
            "Packet Size (Bytes)", "Bandwidth (Gbps)", "Bandwidth vs. Packet Size"
        )
        p2.format()
        if save:
            p2.save(f"plot_bw_{self.name()}")
        if show:
            p2.show(block=False)

    def run(self, args: argparse.Namespace) -> None:
        """Convenience method to run all calculations and outputs."""
        self.calc()
        self.print_table(args.outdir)
        self.print_table(args.outdir, False, False)
        self.print_csv(args.outdir)
        self.plot_all(
            show=not args.no_plot_show,
            save=not args.no_plot_save,
            outdir=args.outdir,
        )
        if not args.no_plot_show:
            plt.show()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments (kept with minimal changes)."""

    ap = argparse.ArgumentParser(
        description="Packet Quantization Calculator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("--bus-width", type=int, default=128, help="Bus width in bytes")
    ap.add_argument(
        "--clk-freq", type=float, default=1.1e9, help="Clock frequency in Hz"
    )
    ap.add_argument(
        "--min-cycles", type=int, default=1, help="Minimum number of cycles"
    )
    ap.add_argument(
        "--min-size", type=int, default=64, help="Minimum packet size in bytes"
    )
    ap.add_argument(
        "--max-size", type=int, default=1518, help="Maximum packet size in bytes"
    )
    ap.add_argument(
        "--outdir", type=str, default="out_uarch_pkt_quantize", help="Output directory"
    )
    ap.add_argument("--no-plot-save", action="store_true", help="Skip saving the plot")
    ap.add_argument("--no-plot-show", action="store_true", help="Skip showing the plot")
    ap.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Set logging level",
    )
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool using a parsed argparse Namespace. Returns process status."""

    args = parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    pp = PktQuantize(
        bus_width=args.bus_width,
        clk_freq=args.clk_freq,
        min_cycles=args.min_cycles,
        min_size=args.min_size,
        max_size=args.max_size,
    )

    pp.run(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
