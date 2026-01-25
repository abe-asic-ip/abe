# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_ready_valid.py

"""Generic producer/consumer FIFO.

Despite the name, this model does *not* simulate the Ready/Valid
handshake. It computes the depth required so the FIFO never
overflows over the horizon, regardless of whether the surrounding
system uses Ready/Valid backpressure or allows drops on overflow.
"""

from __future__ import annotations

import logging
from typing import List, cast

from ortools.sat.python import cp_model

from abe.uarch.fifo_depth_base import (
    FifoBaseModel,
    FifoModel,
    FifoParams,
    FifoResults,
    FifoSolver,
)
from abe.uarch.fifo_depth_utils import (
    adjust_rd_latency_for_cdc,
    apply_margin,
    extract_witness,
    make_solver,
)
from abe.utils import round_value

logger = logging.getLogger(__name__)


class ReadyValidModel(FifoModel):
    """Ready/Valid FIFO model for YAML validation.

    Inherits all configuration fields from FifoModel including horizon, traffic
    parameters, latencies, and margin settings.
    """


class ReadyValidParams(FifoParams):
    """Ready/Valid FIFO parameters for depth calculation."""

    @classmethod
    def from_model(cls, model: FifoBaseModel) -> "ReadyValidParams":
        """Create ReadyValidParams from a validated ReadyValidModel instance."""
        if not isinstance(model, ReadyValidModel):
            raise TypeError(f"Expected ReadyValidModel, got {type(model).__name__}")
        return cls(
            margin_type=model.margin_type,
            margin_val=int(model.margin_val),
            rounding=model.rounding,
            horizon=int(model.horizon),
            w_max=int(model.w_max),
            r_max=int(model.r_max),
            sum_w_min=int(model.sum_w_min),
            sum_w_max=int(model.sum_w_max),
            sum_r_min=int(model.sum_r_min),
            sum_r_max=int(model.sum_r_max),
            wr_latency=int(model.wr_latency),
            rd_latency=int(model.rd_latency),
        )


class ReadyValidResults(FifoResults):
    """Results container for Ready/Valid solver including computed FIFO depth and
    occupancy witness.
    """

    @classmethod
    def make(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        solver: cp_model.CpSolver,
        peak: cp_model.IntVar,
        w: List[cp_model.IntVar],
        r: List[cp_model.IntVar],
        occ: List[cp_model.IntVar],
    ) -> "ReadyValidResults":
        """Create ReadyValidResults from CP-SAT solver solution, extracting
        witness sequences and setting initial depth.
        """
        occ_peak, w_seq, r_seq, occ_seq = extract_witness(solver, peak, w, r, occ)
        depth = occ_peak
        return cls(depth, occ_peak, w_seq, r_seq, occ_seq)


class ReadyValidSolver(FifoSolver):
    """Ready/Valid FIFO depth solver using analytical methods for balanced traffic
    or constraint programming for general cases.

    Automatically selects the appropriate solver based on traffic profile balance.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model_class = ReadyValidModel
        self.params_class = ReadyValidParams
        self.results_class = ReadyValidResults

    def get_params(self) -> None:
        """Convert validated model into parameter object and adjust rd_latency for
        CDC synchronizer cycles if applicable.
        """
        super().get_params()
        params = cast(ReadyValidParams, self.params)
        adjust_rd_latency_for_cdc(params, self.wptr_cdc_cycles_in_wr)

    def get_results(self) -> None:
        """Calculate FIFO depth using analytical solver for balanced traffic or
        CP-SAT solver for unbalanced cases.
        """
        assert self.params is not None, "Must call get_params() first"
        params = cast(ReadyValidParams, self.params)
        if params.is_balanced():
            self._get_results_analysis()
        else:
            self._get_results_cp_sat()

    def _get_results_analysis(  # pylint: disable=too-many-locals, too-many-statements
        self,
    ) -> None:
        """Compute FIFO depth analytically for balanced traffic with layered masks.

        Uses phase-sweep strategy: for each circular shift of the read profile,
        computes maximum occupancy considering write/read latencies. Selects the
        worst-case peak across all phases.
        """
        logger.info("Using analytical balanced-case Ready/Valid solver")
        assert self.params is not None, "Must call get_params() first"
        params = cast(ReadyValidParams, self.params)

        horizon = params.horizon
        w_max, r_max = params.w_max, params.r_max
        wr_lat, rd_lat = params.wr_latency, params.rd_latency

        # Helpers
        def roll(arr: List[int], s: int) -> List[int]:
            s %= len(arr)
            return arr[-s:] + arr[:-s] if s else arr[:]

        def apply_latency(seq: List[int], lat: int) -> List[int]:
            if lat <= 0:
                return seq[:]
            # shift right by 'lat' (events occur later)
            return [0] * lat + seq[: max(0, horizon - lat)]

        def trim_to_sum(seq: List[int], target_sum: int) -> List[int]:
            s = 0
            out = []
            for v in seq:
                if s >= target_sum:
                    out.append(0)
                else:
                    take = min(v, target_sum - s)
                    out.append(take)
                    s += take
            return out

        # Base per-tick attempts (bounded by valid masks & caps)
        w_base = [w_max * v for v in self.write_valid]  # length H

        best_peak = -1
        best_tstar = horizon + 1
        best_r_seq_eff: List[int] = []
        best_w_seq_eff: List[int] = []
        best_occ_seq: List[int] = []
        best_shift = 0

        for s in range(self.overall_period):
            # Shift read mask by s (phase sweep)
            r_mask_shift = roll(self.read_valid, s)
            r_base = [r_max * v for v in r_mask_shift]

            # Apply fixed latencies (same-clock RV: these are deterministic)
            w_eff = apply_latency(w_base, wr_lat)
            r_eff = apply_latency(r_base, rd_lat)

            w_eff = trim_to_sum(w_eff, params.sum_w_max)
            r_eff = trim_to_sum(r_eff, params.sum_r_min)

            # Compute occupancy trajectory (occ[0] = 0), clamp at 0
            occ = 0
            occ_seq = [0]  # include t=0 so downstream checks using occ[1:] still work
            peak_here = 0
            tstar_here = 0

            for t in range(horizon):
                occ = max(0, occ + w_eff[t] - r_eff[t])
                occ_seq.append(occ)
                if occ > peak_here:
                    peak_here = occ
                    tstar_here = t + 1  # match occ index

            # Keep the worst peak, tie-break by earliest time
            if (peak_here > best_peak) or (
                peak_here == best_peak and tstar_here < best_tstar
            ):
                best_peak = peak_here
                best_tstar = tstar_here
                best_r_seq_eff = r_eff
                best_w_seq_eff = w_eff
                best_occ_seq = occ_seq
                best_shift = s

        # Final depth; occ_peak is the analytic worst-case
        depth = best_peak

        self.results = ReadyValidResults(
            depth=depth,
            occ_peak=best_peak,
            w_seq=best_w_seq_eff,
            r_seq=best_r_seq_eff,
            occ_seq=best_occ_seq,
        )
        self._adjust_results()

        self.results_check_args = {"occ_max": params.sum_w_max}
        logger.info(
            "Balanced RV analytic: peak=%d at t*=%d, shift=%d, wr_lat=%d, rd_lat=%d",
            best_peak,
            best_tstar,
            best_shift,
            wr_lat,
            rd_lat,
        )

    def _get_results_cp_sat(  # pylint: disable=too-many-locals, too-many-statements
        self,
    ) -> None:
        """Calculate FIFO depth using constraint programming (CP-SAT) solver.

        Models write/read sequences with valid masks, latencies, and sum constraints
        to find worst-case peak occupancy and earliest peak time.
        """
        # pylint: disable=duplicate-code

        logger.info("Using CP-SAT solver for Ready/Valid protocol")
        assert self.params is not None, "Must call get_params() first"
        params = cast(ReadyValidParams, self.params)

        horizon = params.horizon
        w_max = params.w_max
        r_max = params.r_max
        occ_max = params.sum_w_max
        wr_latency = params.wr_latency
        rd_latency = params.rd_latency

        # Create CP-SAT model
        cp_sat_model = cp_model.CpModel()

        # Setup base variables
        w = [cp_sat_model.new_int_var(0, w_max, f"w_{t}") for t in range(horizon)]
        r = [cp_sat_model.new_int_var(0, r_max, f"r_{t}") for t in range(horizon)]
        occ = [
            cp_sat_model.new_int_var(0, occ_max, f"occ_{t}") for t in range(horizon + 1)
        ]
        peak = cp_sat_model.new_int_var(0, occ_max, "peak")

        # Add common constraints (occupancy evolution, sum constraints, peak tracking)

        # Initial occupancy
        cp_sat_model.add(occ[0] == 0)

        # Gate activity by profiles (also enforces per-step caps)
        for t in range(horizon):
            cp_sat_model.add(w[t] <= params.w_max * self.write_valid[t])
            cp_sat_model.add(r[t] <= params.r_max * self.read_valid[t])

        # Occupancy evolution with latencies
        for t in range(horizon):
            we = w[t - wr_latency] if t >= wr_latency else None
            re = r[t - rd_latency] if t >= rd_latency else None
            if we is None and re is None:
                cp_sat_model.add(occ[t + 1] == occ[t])
            elif we is not None and re is None:
                cp_sat_model.add(occ[t + 1] == occ[t] + we)
            elif re is not None and we is None:
                cp_sat_model.add(occ[t + 1] == occ[t] - re)
            elif we is not None and re is not None:
                cp_sat_model.add(occ[t + 1] == occ[t] + we - re)

        # Sum constraints
        cp_sat_model.add(sum(w) >= params.sum_w_min)
        cp_sat_model.add(sum(w) <= params.sum_w_max)
        cp_sat_model.add(sum(r) >= params.sum_r_min)
        cp_sat_model.add(sum(r) <= params.sum_r_max)

        # Peak tracking
        cp_sat_model.add_max_equality(peak, occ[1:])

        # Create a solver
        cp_sat_solver = make_solver(max_time_s=15.0, workers=8)

        # Solve to maximize peak
        cp_sat_model.maximize(peak)
        status = cp_sat_solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = cp_sat_solver.StatusName(status)
            raise RuntimeError(
                f"Solve max peak failed with status={status} ({status_name})"
            )
        peak_star = int(cp_sat_solver.Value(peak))

        # Solve to find the earliest time of the peak
        cp_sat_model.add(peak == peak_star)
        _, t_star = self.add_earliest_peak_tiebreak(
            cp_sat_model, peak, occ, start_index=1
        )
        cp_sat_model.minimize(t_star)
        status = cp_sat_solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = cp_sat_solver.StatusName(status)
            raise RuntimeError(
                f"Solve earliest peak time failed with status={status} ({status_name})"
            )

        # Extract results
        self.results = ReadyValidResults.make(cp_sat_solver, peak, w, r, occ)
        self._adjust_results()

        # Store check arguments for later validation (after save)
        self.results_check_args = {"occ_max": occ_max}

        # pylint: enable=duplicate-code

    def _adjust_results(self) -> None:
        """Adjust results for CDC, margin, rounding."""

        assert self.params is not None, "Must call get_params() first"
        params = cast(ReadyValidParams, self.params)

        assert self.results is not None, "Must call get_results() first"
        results = cast(ReadyValidResults, self.results)

        if self.base_sync_fifo_depth > 0:
            results.depth += self.base_sync_fifo_depth
            logger.info(
                "Incremented %s.depth by %d for CDC.",
                results.__class__.__name__,
                self.base_sync_fifo_depth,
            )

        results.depth = apply_margin(
            results.depth, params.margin_type, params.margin_val
        )
        results.depth = round_value(results.depth, params.rounding)
