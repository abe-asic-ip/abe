# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_utils.py

"""Utilities for FIFO depth calculation modules.

This module provides common functionality shared across all FIFO depth
calculation protocols (CBFC, XON/XOFF, Replay, Ready/Valid).
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from functools import reduce
from math import ceil, gcd
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Sequence,
)

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from abe.uarch.fifo_depth_base import FifoParams

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _LayerSpec:
    """Validated and canonicalized parameters for one layered traffic profile.

    Stores transaction, burst, and stream-level timing parameters.
    """

    t_valid: int
    t_gap: int
    b_cnt: int
    b_gap: int
    s_cnt: int  # defaults to 1 when stream omitted
    s_gap: int  # defaults to 0 when stream omitted


def _auto_horizon_sync(
    overall_period: int, blind_window: int, kmin_blocks: int = 4
) -> int:
    """Compute automatic horizon for synchronous mode traffic profiles.

    Calculates horizon as multiple of overall_period, ensuring at least
    4*blind_window cycles or kmin_blocks complete periods.
    """
    overall_period = _require_int_ge("overall_period", overall_period, 1)
    blind_window = _require_int_ge("blind_window", blind_window, 0)
    kmin_blocks = _require_int_ge("kmin_blocks", kmin_blocks, 1)
    horizon_0 = max(4 * blind_window, kmin_blocks * overall_period)
    return int(ceil(horizon_0 / overall_period) * overall_period)


def _lcm(a: int, b: int) -> int:
    """Calculate least common multiple of two integers."""
    return a // gcd(a, b) * b


def _lcmm(nums: List[int]) -> int:
    """Calculate least common multiple of a list of integers."""
    return reduce(_lcm, nums)


def _make_one_period_profile(
    p: Dict, mode: Literal["write_congestion", "read_congestion"] = "write_congestion"
) -> List[int]:
    """Build binary (0/1) valid pattern for one complete period of a layered
    traffic profile with worst-case congestion packing.

    Args:
        p: Profile dictionary (write_profile or read_profile)
        mode: Congestion mode - "write_congestion" for worst-case writes,
              "read_congestion" for worst-case reads
    """
    return _profile_from_spec(_parse_layer_spec(p), mode=mode)


def _parse_layer_spec(p: Dict) -> _LayerSpec:
    """Parse and validate layered traffic profile dictionary into structured
    specification.

    Extracts transaction, burst, and stream-level timing parameters.
    """
    t_valid = get_int_from_nested_dict(p, "transaction.valid_cycles", lb=0)
    t_gap = get_int_from_nested_dict(p, "transaction.gap_cycles", lb=0)
    per_txn = t_valid + t_gap
    if per_txn <= 0:
        raise ValueError(f"{per_txn=}")

    b_cnt = get_int_from_nested_dict(p, "burst.transactions_per_burst", lb=1)
    b_gap = get_int_from_nested_dict(p, "burst.gap_cycles", lb=0)
    per_burst = b_cnt * per_txn + b_gap
    if per_burst <= 0:
        raise ValueError(f"{per_burst=}")

    s = p.get("stream", {})
    s_cnt = int(s.get("bursts_per_stream", 1))
    if s_cnt < 1:
        raise ValueError(f"{s_cnt=}")
    s_gap = int(s.get("gap_cycles", 0))
    if s_gap < 0:
        raise ValueError(f"{s_gap=}")

    per_stream = s_cnt * per_burst + s_gap
    if per_stream <= 0:
        raise ValueError(f"{per_stream=}")

    return _LayerSpec(
        t_valid=t_valid, t_gap=t_gap, b_cnt=b_cnt, b_gap=b_gap, s_cnt=s_cnt, s_gap=s_gap
    )


def _period_from_layers(p: Dict) -> int:
    """Calculate total period length in write cycles for a layered traffic
    profile.
    """
    return _period_from_spec(_parse_layer_spec(p))


def _period_from_spec(spec: _LayerSpec) -> int:
    """Calculate total period length in write cycles from a parsed layer
    specification.
    """
    per_txn = spec.t_valid + spec.t_gap
    per_burst = spec.b_cnt * per_txn + spec.b_gap
    return spec.s_cnt * per_burst + spec.s_gap


def _profile_from_spec(  # pylint: disable=too-many-branches
    spec: _LayerSpec,
    mode: Literal["write_congestion", "read_congestion"] = "write_congestion",
) -> List[int]:
    """Build binary (0/1) valid pattern for one complete period from a parsed
    layer specification with worst-case congestion.

    Args:
        spec: Parsed layer specification
        mode: Traffic congestion mode:
            - "write_congestion": Alternates burst phases to maximize data clustering.
              Creates double-wide valid windows at burst boundaries.
            - "read_congestion": Alternates burst phases to maximize idle clustering.
              Creates double-wide idle windows at burst boundaries.

    Implements worst-case pattern from FIFO depth calculation literature:
    alternating phases at each hierarchical level to create maximum congestion.

    Example with t_valid=4, t_gap=4, b_cnt=2 (transaction level only):
      write_congestion: [0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0, ...]
                         [  gap  ][ valid ][ valid ][  gap  ]
                         txn0: gap-first   txn1: valid-first
                         Creates 8-cycle valid window at boundary

      read_congestion:  [1,1,1,1,0,0,0,0,0,0,0,0,1,1,1,1, ...]
                         [ valid ][  gap  ][  gap  ][ valid ]
                         txn0: valid-first txn1: gap-first
                         Creates 8-cycle idle window at boundary
    """
    if mode == "read_congestion":
        # Read worst-case: maximize idle clustering.
        # Strategy: burst gap at START (delays reads), and alternate txn phases
        # within the burst so gaps meet at txn boundaries.
        bursts = []
        for burst_idx in range(spec.s_cnt):
            txns = []
            # Single burst: use uniform gap-first pattern for maximum delay
            if spec.s_cnt == 1:
                for txn_idx in range(spec.b_cnt):
                    txn = [0] * spec.t_gap + [1] * spec.t_valid  # gap-first
                    txns.extend(txn)
            else:
                # Multiple bursts: alternate txn phases to cluster idle at boundaries
                for txn_idx in range(spec.b_cnt):
                    if (burst_idx + txn_idx) % 2 == 0:
                        # valid-first then gap → boundary with next gap-first
                        # forms larger idle
                        txn = [1] * spec.t_valid + [0] * spec.t_gap
                    else:
                        # gap-first then valid
                        txn = [0] * spec.t_gap + [1] * spec.t_valid
                    txns.extend(txn)
            burst = [0] * spec.b_gap + txns  # put burst gap at start
            bursts.extend(burst)

        return [0] * spec.s_gap + bursts

    # Write worst-case: alternate burst gap placement to create maximum valid
    # clustering. Pattern creates Case-4 worst-case: ...write|write... at burst
    # boundaries. Strategy: bursts alternate gap placement, transactions
    # alternate within burst to ensure both start-with-valid and end-with-valid
    # at burst txn sections.
    bursts = []
    for burst_idx in range(spec.s_cnt):
        txns = []

        # Special case: single burst (s_cnt=1)
        # No boundaries to optimize, so use uniform pattern for maximum clustering
        if spec.s_cnt == 1:
            # Uniform valid-first pattern maximizes clustering within burst
            for txn_idx in range(spec.b_cnt):
                txn = [1] * spec.t_valid + [0] * spec.t_gap  # valid-first
                txns.extend(txn)
        else:
            # Multiple bursts: optimize for Case-4 at boundaries
            # We want boundaries (odd -> next even) to be "...valid | valid..."
            # That means: the ODD burst should end with VALID.
            need_last_valid = burst_idx % 2 == 1
            # If b_cnt is odd, a plain "valid-first, gap-first, valid-first, ..."
            # ends with VALID when we start with GAP-FIRST; when b_cnt is even,
            # starting with VALID-FIRST ends with VALID.
            if spec.b_cnt % 2 == 1:
                start_with_gap_first = need_last_valid  # True => last ends valid
            else:
                start_with_gap_first = False  # even b_cnt: start valid-first

            for txn_idx in range(spec.b_cnt):
                use_gap_first = (txn_idx % 2 == 0) and start_with_gap_first
                use_gap_first = use_gap_first or (
                    (txn_idx % 2 == 1) and (not start_with_gap_first)
                )
                if use_gap_first:
                    txn = [0] * spec.t_gap + [1] * spec.t_valid
                else:
                    txn = [1] * spec.t_valid + [0] * spec.t_gap
                txns.extend(txn)

        # Alternate burst gap position to achieve worst-case data clustering.
        # For 1 burst: (D,I) - data then idle
        # For 2+ bursts: first is (I,D), last is (D,I) - idles at start/end
        # concentrate data in the middle
        if spec.s_cnt == 1:
            # Single burst: data then idle (D,I)
            burst = txns + [0] * spec.b_gap
        elif burst_idx == 0:
            # First burst when 2+: idle then data (I,D)
            burst = [0] * spec.b_gap + txns
        elif burst_idx == spec.s_cnt - 1:
            # Last burst when 2+: data then idle (D,I)
            burst = txns + [0] * spec.b_gap
        else:
            # Middle bursts: alternate to maximize clustering
            # Odd indices: (D,I) to create data|data boundary with next burst
            # Even indices: (I,D) to create data|data boundary with previous burst
            if burst_idx % 2 == 1:
                burst = txns + [0] * spec.b_gap  # (D,I)
            else:
                burst = [0] * spec.b_gap + txns  # (I,D)
        bursts.extend(burst)

    return bursts + [0] * spec.s_gap


def _require_int_ge(name: str, val: int, lb: int) -> int:
    """Validate that an integer value meets a lower bound constraint."""
    if val < lb:
        raise ValueError(f"{name} must be >= {lb}, got {val}")
    return val


def _tile_profile(base: List[int], horizon: int) -> List[int]:
    """Repeat a base period profile to cover the specified horizon length."""
    if not base:
        return [0] * horizon
    return (base * (horizon // len(base) + 1))[:horizon]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class LayeredCompileOut(NamedTuple):
    """Output container for compiled layered traffic specification.

    Contains flattened specification dictionary, overall period, and binary
    valid profiles for write and read interfaces.
    """

    flat_spec: Dict[str, int | str]
    overall_period: int
    write_valid: List[int]
    read_valid: List[int]


def adjust_rd_latency_for_cdc(params: FifoParams, rd_sync_cycles_in_wr: int) -> None:
    """Adjust read latency in parameter object for CDC synchronizer cycles."""
    if rd_sync_cycles_in_wr > 0:
        params.rd_latency += rd_sync_cycles_in_wr
        logger.info(
            "Incremented %s.rd_latency by %d for CDC.",
            params.__class__.__name__,
            rd_sync_cycles_in_wr,
        )


def apply_margin(
    val: int,
    margin_type: Literal["percentage", "absolute"],
    margin_val: int,
) -> int:
    """Apply margin to a value."""
    if margin_type == "percentage":
        return int(ceil(val * (100 + margin_val) / 100))
    return val + margin_val


def compile_layered_spec(  # pylint: disable=too-many-locals
    raw: Dict,
) -> LayeredCompileOut:
    """Compile a layered traffic specification (YAML or dict) into flattened
    format.

    Processes write/read profiles with transaction/burst/stream structure,
    computes LCM period, generates binary valid patterns, and produces flat
    specification with sum constraints.
    """

    # Get fields from raw spec
    margin_type = str(raw.get("margin_type", "absolute"))
    margin_val = int(raw.get("margin_val", 0))
    rounding = str(raw.get("rounding", "none"))
    horizon_raw = raw.get("horizon", "auto")
    wr_latency = int(raw.get("wr_latency", 0))
    rd_latency = int(raw.get("rd_latency", 0))
    kmin_blocks = int(raw.get("kmin_blocks", 4))
    blind_window = int(raw.get("blind_window_cycles", 0))
    wp = raw["write_profile"]
    rp = raw["read_profile"]

    # Per-cycle caps
    w_max = get_int_from_nested_dict(wp, "cycle.max_items_per_cycle", lb=1, default=1)
    r_max = get_int_from_nested_dict(rp, "cycle.max_items_per_cycle", lb=1, default=1)

    # Periods (in write-domain cycles)
    write_period = _period_from_layers(wp)
    read_period = _period_from_layers(rp)
    overall_period = _lcmm([write_period, read_period])

    # Choose horizon
    if str(horizon_raw) == "auto":
        horizon = _auto_horizon_sync(overall_period, blind_window, kmin_blocks)
        logger.info("User specified horizon 'auto' resolved to %d cycles.", horizon)
    else:
        horizon_raw = int(horizon_raw)
        # round up to multiple of overall_period
        horizon = (
            (horizon_raw + (overall_period - 1)) // overall_period * overall_period
        )
        logger.info(
            "User specified horizon %d rounded up to %d cycles.", horizon_raw, horizon
        )

    # Profiles
    # Worst-case congestion packing: alternating phases to cluster data
    base_w = _make_one_period_profile(wp, mode="write_congestion")
    base_r = _make_one_period_profile(rp, mode="read_congestion")

    # --- causality guard (ensure no read before data can exist) ---
    def _first_one(mask: List[int]) -> int:
        try:
            return mask.index(1)
        except ValueError:
            return len(mask)

    def _rotate_right(mask: List[int], k: int) -> List[int]:
        n = len(mask)
        if n == 0:
            return mask
        k %= n
        if k == 0:
            return mask
        return mask[-k:] + mask[:-k]

    first_w = _first_one(base_w)
    if first_w < len(base_w):
        warmup = wr_latency + first_w
        base_r = _rotate_right(base_r, warmup)
        logger.debug(
            "read mask rotated by warmup=%d (wr_latency=%d, first_w=%d)",
            warmup,
            wr_latency,
            first_w,
        )
    # --------------------------------------------------------------

    write_valid = _tile_profile(base_w, horizon)
    read_valid = _tile_profile(base_r, horizon)

    # Totals (for flat spec fields)
    sum_w = sum(write_valid) * w_max
    sum_r = sum(read_valid) * r_max

    flat_spec: Dict[str, int | str] = {
        "horizon": horizon,
        "margin_type": margin_type,
        "margin_val": margin_val,
        "rounding": rounding,
        "w_max": w_max,
        "r_max": r_max,
        "sum_w_min": sum_w,
        "sum_w_max": sum_w,
        "sum_r_min": sum_r,
        "sum_r_max": sum_r,
        "wr_latency": wr_latency,
        "rd_latency": rd_latency,
    }

    meta = {
        "write_period": write_period,
        "read_period": read_period,
        "overall_period": overall_period,
        "horizon": horizon,
        "blind_window": blind_window,
    }
    logger.info("meta:\n%s", json.dumps(meta, indent=2))

    return LayeredCompileOut(flat_spec, overall_period, write_valid, read_valid)


def extract_witness(
    s: cp_model.CpSolver,
    peak: cp_model.IntVar,
    w_vars: Iterable[cp_model.IntVar],
    r_vars: Iterable[cp_model.IntVar],
    occ_vars: Iterable[cp_model.IntVar],
) -> tuple[int, List[int], List[int], List[int]]:
    """Extract solution witness from CP-SAT solver after solving.

    Returns peak value, write sequence, read sequence, and occupancy sequence.
    """
    peak_v = int(s.Value(peak))
    w_seq = [int(s.Value(x)) for x in w_vars]
    r_seq = [int(s.Value(x)) for x in r_vars]
    occ_seq = [int(s.Value(x)) for x in occ_vars]
    return peak_v, w_seq, r_seq, occ_seq


def get_args(
    argv: Sequence[str] | None = None, description: str = ""
) -> argparse.Namespace:
    """Parse command line arguments for FIFO depth calculation tools.

    Provides standard arguments for spec file path, output directory, and
    logging verbosity.
    """
    ap = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("spec", nargs="+", help="YAML/JSON spec file path(s)")
    ap.add_argument("--outdir", help="output directory")
    ap.add_argument("--results-name", default="results", help="results name prefix")
    ap.add_argument(
        "--verbosity",
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="logging level",
    )
    args = ap.parse_args(argv)

    # Convert single-element list to string for backward compatibility with solvers
    if len(args.spec) == 1:
        args.spec = args.spec[0]

    return args


def get_int_from_nested_dict(
    p: Dict, path: str, lb: int | None = None, default: int | None = None
) -> int:
    """Extract integer from nested dictionary using dot-notation path.

    Validates that the value exists, is an integer, and optionally meets a
    lower bound constraint. If a default is provided and any key in the path
    is missing, returns the default value.
    """
    parts = path.split(".")
    val: Any
    try:
        cur = p
        for key in parts:
            cur = cur[key]
        val = cur
    except KeyError:
        if default is not None:
            val = default
        else:
            # Reconstruct which part of the path was missing for error message
            temp = p
            for i, k in enumerate(parts):
                if k not in temp:
                    raise KeyError(f"Missing key: {'.'.join(parts[:i+1])}") from None
                temp = temp[k]
            raise  # Should never reach here, but satisfies type checker
    if not isinstance(val, int):
        raise ValueError(f"{path} must be int, got {type(val).__name__}")
    if lb is not None and val < lb:
        raise ValueError(f"{path} must be >= {lb}, got {val}")
    return val


def make_solver(
    max_time_s: float = 10.0, workers: int = 8, seed: int | None = None
) -> cp_model.CpSolver:
    """Create and configure a CP-SAT solver with time limit, parallelism, and
    optional random seed.
    """
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_s
    solver.parameters.num_search_workers = workers
    if seed is not None:
        solver.parameters.random_seed = seed
    return solver


def max_wait_to_next_valid_slot(mask: List[int]) -> int:
    """Calculate maximum wait time to next valid slot across all positions in a
    binary mask.

    Returns the worst-case number of cycles until mask[t+delta] == 1 for any
    starting position t.
    """
    n = len(mask)
    next_one = [n] * n
    nxt = n
    for i in range(n - 1, -1, -1):
        if mask[i] == 1:
            nxt = i
        next_one[i] = nxt
    max_wait = 0
    for t in range(n):
        if next_one[t] == n:
            wait = n - t  # no more slots; cap at remaining horizon
        else:
            wait = max(0, next_one[t] - t)
        max_wait = max(max_wait, wait)
    return max_wait


def max_window_sum(mask: List[int], l: int) -> int:
    """Calculate maximum sum over any sliding window of length l in a binary
    mask.

    Uses efficient sliding window algorithm. Handles edge cases where l <= 0
    or l > len(mask).
    """
    if l <= 0:
        return 0
    n = len(mask)
    l = min(l, n)
    s = sum(mask[:l])
    best = s
    for i in range(l, n):
        s += mask[i] - mask[i - l]
        best = max(best, s)
    return best
