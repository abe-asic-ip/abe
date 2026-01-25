# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_xon_xoff.py

# pylint: disable=too-many-lines

"""Calculate XON/XOFF FIFO depth."""

from __future__ import annotations

import copy
import logging
import math
from typing import List, Literal, cast

from ortools.sat.python import cp_model
from pydantic import NonNegativeInt, model_validator

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
    max_wait_to_next_valid_slot,
    max_window_sum,
)
from abe.utils import round_value, yellow

logger = logging.getLogger(__name__)

EPS = 1e-9  # Small epsilon for floating-point comparisons
Auto = Literal["auto"]


class XonXoffModel(FifoModel):
    """XON/XOFF FIFO model with threshold configuration (manual or auto) for
    YAML validation.

    Supports manual threshold specification or automatic threshold optimization
    with configurable hysteresis and throughput targets.
    """

    # XON/XOFF specific parameters
    atomic_tail: NonNegativeInt = 0
    react_latency: NonNegativeInt = 0
    resume_latency: NonNegativeInt = 0
    w_throttle_max: NonNegativeInt = 0  # 0: hard stop when paused
    thresholds: Literal["manual", "auto"] = "auto"

    # Manual mode: required xon, xoff
    xon: NonNegativeInt | None = None
    xoff: NonNegativeInt | None = None

    # Auto mode: required parameters
    throughput_target: float | Auto | None = "auto"
    xon_min: NonNegativeInt | Auto | None = "auto"
    xoff_range: List[int] | Literal["auto"] | None = "auto"
    hysteresis: List[float | int] | None = [1.0, 1.5]
    prefer_small_band: bool | None = False
    prefer_low_xoff: bool | None = False

    @model_validator(mode="after")
    def check_threshold_requirements(self) -> "XonXoffModel":
        """Validate that required fields are present based on threshold mode
        (manual or auto).
        """
        if self.thresholds == "manual":
            # Manual mode requires xon and xoff
            if self.xon is None:
                raise ValueError("xon is required when thresholds='manual'")
            if self.xoff is None:
                raise ValueError("xoff is required when thresholds='manual'")
        elif self.thresholds == "auto":
            assert self.hysteresis is not None  # for type checker
            if self.hysteresis is None:
                raise ValueError(
                    "hysteresis [min,max] is required when thresholds='auto'"
                )
            if len(self.hysteresis) != 2:
                raise ValueError("hysteresis must be a 2-element list [min, max]")
            # Type narrowing: hysteresis is confirmed to be a 2-element list here
            hyst = self.hysteresis
            hmin, hmax = hyst[0], hyst[1]  # pylint: disable=unsubscriptable-object
            # Both must be >= 0, and min <= max (allow mix of int/float)
            if (float(hmin) < 0) or (float(hmax) < 0) or (float(hmin) > float(hmax)):
                raise ValueError("invalid hysteresis: require 0 ≤ min ≤ max")
        return self


class XonXoffParams(FifoParams):  # pylint: disable=too-many-instance-attributes
    """XON/XOFF FIFO parameters including flow control thresholds, latencies,
    and throttle configuration for manual or automatic threshold selection.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        *,
        # Base parameters
        margin_type: Literal["percentage", "absolute"] = "absolute",
        margin_val: int = 0,
        rounding: Literal["power2", "none"] = "none",
        horizon: int,
        w_max: int = 1,
        r_max: int = 1,
        sum_w_min: int,
        sum_w_max: int,
        sum_r_min: int,
        sum_r_max: int,
        wr_latency: int = 0,
        rd_latency: int = 0,
        # XON/XOFF specific parameters
        atomic_tail: int = 0,
        react_latency: int = 0,
        resume_latency: int = 0,
        w_throttle_max: int = 0,
        thresholds: Literal["manual", "auto"] = "auto",
        xon: int | None = None,
        xoff: int | None = None,
        throughput_target: float | Auto | None = "auto",
        xon_min: int | Auto | None = "auto",
        xoff_range: List[int] | Literal["auto"] | None = "auto",
        hysteresis: List[float | int] | None = None,
        prefer_small_band: bool | None = False,
        prefer_low_xoff: bool | None = False,
    ) -> None:
        super().__init__(
            margin_type=margin_type,
            margin_val=margin_val,
            rounding=rounding,
            horizon=horizon,
            w_max=w_max,
            r_max=r_max,
            sum_w_min=sum_w_min,
            sum_w_max=sum_w_max,
            sum_r_min=sum_r_min,
            sum_r_max=sum_r_max,
            wr_latency=wr_latency,
            rd_latency=rd_latency,
        )
        self.atomic_tail = atomic_tail
        self.react_latency = react_latency
        self.resume_latency = resume_latency
        self.w_throttle_max = w_throttle_max
        self.thresholds = thresholds
        self.xon = xon
        self.xoff = xoff
        self.throughput_target = throughput_target
        self.xon_min = xon_min
        self.xoff_range = xoff_range
        self.hysteresis = hysteresis if hysteresis is not None else [1.0, 1.5]
        self.prefer_small_band = prefer_small_band
        self.prefer_low_xoff = prefer_low_xoff

    @classmethod
    def from_model(cls, model: FifoBaseModel) -> "XonXoffParams":
        """Create XonXoffParams from a validated XonXoffModel instance."""
        if not isinstance(model, XonXoffModel):
            raise TypeError(f"Expected XonXoffModel, got {type(model).__name__}")
        return cls(
            # Base parameters
            # pylint: disable=duplicate-code
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
            # pylint: enable=duplicate-code
            # XON/XOFF specific parameters
            atomic_tail=int(model.atomic_tail),
            react_latency=int(model.react_latency),
            resume_latency=int(model.resume_latency),
            w_throttle_max=int(model.w_throttle_max),
            thresholds=model.thresholds,
            xon=int(model.xon) if model.xon is not None else None,
            xoff=int(model.xoff) if model.xoff is not None else None,
            throughput_target=model.throughput_target,
            xon_min=model.xon_min if model.xon_min is not None else None,
            xoff_range=model.xoff_range if model.xoff_range is not None else None,
            hysteresis=(
                list(model.hysteresis) if model.hysteresis is not None else None
            ),
            prefer_small_band=model.prefer_small_band,
            prefer_low_xoff=model.prefer_low_xoff,
        )

    def check(self) -> None:
        """Validate XON/XOFF parameter constraints including threshold ordering,
        throttle limits, and hysteresis bounds.
        """
        super().check()

        if self.atomic_tail < 0:
            raise ValueError(f"{self.atomic_tail=}")
        if self.react_latency < 0:
            raise ValueError(f"{self.react_latency=}")
        if self.resume_latency < 0:
            raise ValueError(f"{self.resume_latency=}")
        if self.w_throttle_max < 0:
            raise ValueError(f"{self.w_throttle_max=}")
        if self.w_throttle_max > self.w_max:
            raise ValueError(
                f"w_throttle_max ({self.w_throttle_max}) > w_max ({self.w_max})"
            )

        if self.xon is not None and self.xoff is not None:
            if not 0 <= self.xon < self.xoff:
                raise ValueError(f"{self.xon=} {self.xoff=}")
            if self.xoff > self.sum_w_max:
                s = f"xoff ({self.xoff}) > sum_w_max ({self.sum_w_max}):"
                s += " XOFF may never engage in this run"
                logger.warning(yellow(s))


class XonXoffResults(FifoResults):  # pylint: disable=too-many-instance-attributes
    """Results container for XON/XOFF solver including computed thresholds and
    FIFO witness.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        depth: int,
        occ_peak: int,
        w_seq: List[int],
        r_seq: List[int],
        occ_seq: List[int],
        xon: int,
        xoff: int,
        throughput: float,
        t_star: int,
    ) -> None:
        super().__init__(depth, occ_peak, w_seq, r_seq, occ_seq)
        self.xon = xon
        self.xoff = xoff
        self.throughput = throughput
        self.t_star = t_star

    @classmethod
    def make(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        solver: cp_model.CpSolver,
        peak: cp_model.IntVar,
        w: List[cp_model.IntVar],
        r: List[cp_model.IntVar],
        occ: List[cp_model.IntVar],
        xon: int,
        xoff: int,
        throughput: float,
        t_star: int,
    ) -> "XonXoffResults":
        """Create XonXoffResults from CP-SAT solver solution, extracting
        witness sequences and setting initial depth.
        """
        occ_peak, w_seq, r_seq, occ_seq = extract_witness(solver, peak, w, r, occ)
        depth = occ_peak
        return cls(
            depth, occ_peak, w_seq, r_seq, occ_seq, xon, xoff, throughput, t_star
        )

    def check(self, occ_max: int, throughput_target: float | None = None) -> None:
        """Run base occupancy checks and, if a throughput target was provided,
        verify that the achieved throughput meets the target.
        """
        # Run the common FIFO consistency checks first
        super().check(occ_max)

        # No throughput target provided (or thresholds='auto' with target 'auto'):
        # nothing else to do.
        if throughput_target is None:
            return

        # Clamp the target into [0.0, 1.0] for robustness
        target = max(0.0, min(1.0, float(throughput_target)))

        # If we already failed basic checks (e.g. internal occupancy mismatch),
        # don't override that reason, but we can still update msg.
        if self.throughput + EPS < target:
            self.basic_checks_pass = False
            self.msg = (
                "Throughput target not met: "
                f"target={target:.6f}, achieved={self.throughput:.6f} "
                "(ratio of max write capacity per cycle)."
            )


class XonXoffSolver(FifoSolver):  # pylint: disable=too-many-instance-attributes
    """XON/XOFF FIFO depth solver using constraint programming with automatic
    threshold optimization or manual threshold specification.

    In auto mode, sweeps XON/XOFF threshold combinations to find optimal
    configuration balancing depth, hysteresis band, and throughput targets.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model_class = XonXoffModel
        self.params_class = XonXoffParams
        self.results_class = XonXoffResults
        self._run_tiebreak = False
        self._best_peak: int | None = None
        self._peak_ub: int | None = None
        self._w_hint: List[int] | None = None
        self._r_hint: List[int] | None = None
        self._occ_hint: List[int] | None = None
        self.t_star_val: int | None = None
        self._throughput_abs_req: int | None = None

    def get_unique_keys(self) -> None:
        """Extract XON/XOFF-specific configuration keys from specification based
        on threshold mode (manual or auto).
        """
        super().get_unique_keys()
        assert self.spec, "Must call get_spec() first"

        self.get_one_unique_key("atomic_tail", required=False)
        self.get_one_unique_key("react_latency", required=False)
        self.get_one_unique_key("resume_latency", required=False)
        self.get_one_unique_key("w_throttle_max", required=False)
        self.get_one_unique_key("thresholds", required=False)

        thresholds = self.spec.get("thresholds", "auto")  # default to auto

        if thresholds == "manual":
            self.get_one_unique_key("xon", required=False)
            self.get_one_unique_key("xoff", required=False)
        elif thresholds == "auto":
            self.get_one_unique_key("throughput_target", required=False)
            self.get_one_unique_key("xon_min", required=False)
            self.get_one_unique_key("xoff_range", required=False)
            self.get_one_unique_key("hysteresis", required=False)
            self.get_one_unique_key("prefer_small_band", required=False)
            self.get_one_unique_key("prefer_low_xoff", required=False)
        else:
            raise ValueError(f"Invalid thresholds value: {thresholds}")

    def get_params(self) -> None:
        """Convert validated model into parameter object and adjust rd_latency for
        CDC synchronizer cycles if applicable.
        """
        super().get_params()
        params = cast(XonXoffParams, self.params)
        adjust_rd_latency_for_cdc(params, self.rd_sync_cycles_in_wr)

    def get_results(  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
        self,
    ) -> None:
        """Calculate FIFO depth using manual thresholds or automatic threshold
        optimization.

        In auto mode, sweeps XON/XOFF combinations within configured range,
        evaluating each against throughput targets and selecting optimal
        configuration based on depth, band size, and user preferences.
        """

        assert self.params is not None, "Must call get_params() first"
        params = cast(XonXoffParams, self.params)

        if params.thresholds == "manual":
            self._run_tiebreak = True
            self._get_results_one()
            return

        # Auto mode: ensure required parameters are set
        assert params.xoff_range is not None, "xoff_range required for auto mode"
        assert (
            params.prefer_small_band is not None
        ), "prefer_small_band required for auto mode"
        assert (
            params.prefer_low_xoff is not None
        ), "prefer_low_xoff required for auto mode"

        # Helper local variables
        horizon = params.horizon
        throughput_target = params.throughput_target
        # For pruning when min hysteresis is a ratio:
        min_ratio = self._min_ratio_if_any(params)
        prefer_small_band = params.prefer_small_band
        prefer_low_xoff = params.prefer_low_xoff

        # Cheap global caps ignoring pause/throttle (true upper bounds).
        # These let us skip impossible (xon,xoff) combos without calling the solver.
        write_slots = sum(int(v) for v in self.write_valid[: params.horizon])
        ub_w = min(params.sum_w_max, params.w_max * write_slots)

        # Initialize before trials
        cnt = 0
        solved = 0
        best_key = None
        best_result: XonXoffResults | None = None
        best_depth = None
        best_xon = 0
        best_xoff = 0
        best_abs_req = 0
        self._run_tiebreak = False
        self._throughput_abs_req = None  # avoid carrying a stale value between runs

        xon_min_eff, xoff_lo_eff, xoff_hi_eff = self._get_effective_thresholds(params)
        logger.info(
            "Sweep window: xon_min_eff=%d, xoff∈[%d,%d], band∈[%d,%d] at xon_min_eff",
            xon_min_eff,
            xoff_lo_eff,
            xoff_hi_eff,
            self._hys_min_for_xon(params, xon_min_eff),
            self._hys_max_for_xon(params, xon_min_eff),
        )

        for xoff in range(xoff_lo_eff, xoff_hi_eff + 1):
            if xoff > params.sum_w_max:
                continue
            if xon_min_eff >= xoff:
                continue

            # Tight upper & lower bounds for xon given this xoff
            min_ratio = self._min_ratio_if_any(params)  # already have this
            max_ratio = self._max_ratio_if_any(params)  # new

            # Upper bound from min hysteresis
            if min_ratio is not None:
                # xon ≤ floor( xoff / (1 + r_min) )
                xon_hi_bound = min(xoff - 1, int(math.floor(xoff / (1.0 + min_ratio))))
            else:
                # absolute min: band ≥ hmin_abs ⇒ xon ≤ xoff - hmin_abs
                # Use a conservative probe near the floor just for the bound:
                hmin_abs = self._hys_min_for_xon(params, max(1, xon_min_eff))
                xon_hi_bound = min(xoff - 1, xoff - hmin_abs)

            # Lower bound from max hysteresis
            if max_ratio is not None:
                # xon ≥ ceil( (xoff - 1) / (1 + r_max) )
                xon_lo_bound = int(math.ceil((xoff - 1) / (1.0 + max_ratio)))
            else:
                # absolute max: band ≤ hmax_abs ⇒ xon ≥ xoff - hmax_abs
                hmax_abs = self._hys_max_for_xon(params, max(1, xon_min_eff))
                xon_lo_bound = xoff - hmax_abs

            # Always respect xon_min_eff
            xon_lo_bound = max(xon_lo_bound, xon_min_eff)

            # If the interval is empty, skip this xoff
            if xon_lo_bound > xon_hi_bound:
                continue

            # Now iterate only the feasible xon range
            # (still descending to prefer small band)
            for xon in range(xon_hi_bound, xon_lo_bound - 1, -1):

                cnt += 1
                runstr = f"auto run {cnt} with (xon, xoff) = ({xon}, {xoff})"

                band = xoff - xon
                # Enforce per-trial min/max (ratio/abs mixed allowed)
                min_band_trial = self._hys_min_for_xon(params, xon)
                max_band_trial = self._hys_max_for_xon(params, xon)
                if band < min_band_trial or band > max_band_trial:
                    logger.info(
                        "%s skipped: band=%d outside [%d,%d]",
                        runstr,
                        band,
                        min_band_trial,
                        max_band_trial,
                    )
                    continue

                band = xoff - xon
                ub_rate = self._get_throughput_upper_bound(params, band)

                # Resolve effective throughput target for this trial
                if throughput_target == "auto" or throughput_target is None:
                    throughput_target_eff = ub_rate
                else:
                    tt = float(throughput_target)
                    # clamp to [0, ub_rate] to keep the solver feasible
                    throughput_target_eff = min(max(tt, 0.0), ub_rate)

                # Set absolute requirement for this trial (used in get_results_one).
                # Use FLOOR (not CEIL) and a small safety cushion (−1) so we don't
                # force the model to hit an optimistic upper bound exactly.
                raw_target_w = int(math.floor(throughput_target_eff * horizon + EPS))
                safety = 1
                target_w = max(0, raw_target_w - safety)

                # Respect the global write budget ub_w and sum_w_min.
                # Note: ub_w already accounts for write-valid mask; target_w may still
                # be slightly optimistic vs. discrete windows, hence the safety above.
                capped_target = min(ub_w - safety if ub_w > 0 else 0, target_w)

                # IMPORTANT:
                # In AUTO mode with XON/XOFF, sum_w_min may be computed without
                # considering throttle/pause and can be unattainable.
                # Do NOT promote the lower bound with sum_w_min here.
                # We deliberately relax to the pause-aware target only.
                self._throughput_abs_req = capped_target

                if params.sum_w_min > self._throughput_abs_req:
                    logger.info(
                        "Relaxing write lower bound for AUTO+XON/XOFF: "
                        "sum_w_min=%d > abs_req=%d (pause-aware).",
                        params.sum_w_min,
                        self._throughput_abs_req,
                    )

                logger.info(
                    (
                        "%s throughput target: raw=%s, ub_rate=%.6f, eff=%.6f, "
                        "raw_target_w=%d, ub_w=%d, abs_req=%d"
                    ),
                    runstr,
                    str(throughput_target),
                    ub_rate,
                    throughput_target_eff,
                    raw_target_w,
                    ub_w,
                    self._throughput_abs_req,
                )

                # Clone current params
                trial = copy.deepcopy(params)
                trial.xon = xon
                trial.xoff = xoff
                if self._best_peak is not None:
                    self._peak_ub = self._best_peak
                self.params = trial  # temporarily swap in

                try:
                    self._get_results_one()
                    solved += 1
                except RuntimeError as e:
                    logger.warning(
                        yellow("%s infeasible: %s (ub_w=%d, target=%s, band=%d)"),
                        runstr,
                        str(e),
                        ub_w,
                        str(self._throughput_abs_req),
                        xoff - xon,
                    )
                    continue  # infeasible

                logger.info("%s completed _get_results_one()", runstr)

                assert (
                    self.results is not None
                ), "Results should be set after _get_results_one()"
                # results has t_star attached in get_results_one()
                r = cast(XonXoffResults, self.results)

                if best_depth is None or r.depth < best_depth:
                    best_depth = r.depth

                # Prefer: smaller depth → smaller band (if configured)
                # → lower xoff (if configured)
                # → smaller raw peak → earliest peak time (t_star).
                key = (
                    r.depth,
                    band if prefer_small_band else math.inf,
                    xoff if prefer_low_xoff else math.inf,
                    r.occ_peak,
                    getattr(r, "t_star", 0),
                )

                if best_key is None or key < best_key:
                    best_key = key
                    best_result = copy.deepcopy(r)
                    best_xon = xon
                    best_xoff = xoff
                    best_abs_req = self._throughput_abs_req
                    self._best_peak = r.occ_peak
                    self._w_hint = r.w_seq[:]
                    self._r_hint = r.r_seq[:]
                    self._occ_hint = r.occ_seq[:]
                    msg = (
                        "NEW BEST depth=%d xon=%d xoff=%d peak=%d "
                        "t_star=%s band=%d sum_w=%d"
                    )
                    logger.info(
                        msg,
                        r.depth,
                        xon,
                        xoff,
                        r.occ_peak,
                        getattr(r, "t_star", 0),
                        band,
                        sum(r.w_seq),
                    )

        if best_result is None:
            raise RuntimeError(
                "No (xon,xoff) combination met throughput and drop criteria"
            )

        self.params = cast(XonXoffParams, self.params)
        self.params.xon = best_xon
        self.params.xoff = best_xoff
        self._run_tiebreak = True
        self._throughput_abs_req = best_abs_req
        self._get_results_one()
        logger.info(
            "Tried %d pairs, solved %d (%.1f%%)",
            cnt,
            solved,
            100.0 * solved / max(1, cnt),
        )

    def _get_results_one(  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        self,
    ) -> None:
        """Calculate FIFO depth for a single XON/XOFF threshold configuration
        using constraint programming.

        Models flow control behavior with hysteresis, reaction latency, resume
        latency, and throttle constraints to find worst-case peak occupancy.
        """
        # pylint: disable=duplicate-code

        # ensure we don't carry a stale t_star across solves
        self.t_star_val = None

        assert self.params is not None, "Must call get_params() first"
        params = cast(XonXoffParams, self.params)

        # For manual mode, xon and xoff must be set
        # (enforced by model validator when thresholds='manual')
        assert params.xon is not None, "xon must be set for manual mode"
        assert params.xoff is not None, "xoff must be set for manual mode"

        # Local variables for convenience
        horizon = params.horizon
        w_max = params.w_max
        r_max = params.r_max
        occ_max = params.sum_w_max
        wr_latency = params.wr_latency
        rd_latency = params.rd_latency
        react_latency = params.react_latency
        w_throttle_max = params.w_throttle_max
        xon = params.xon
        xoff = params.xoff

        # Create CP-SAT model
        cp_sat_model = cp_model.CpModel()

        # Setup base variables
        w = [cp_sat_model.new_int_var(0, w_max, f"w_{t}") for t in range(horizon)]
        r = [cp_sat_model.new_int_var(0, r_max, f"r_{t}") for t in range(horizon)]
        occ = [
            cp_sat_model.new_int_var(0, occ_max, f"occ_{t}") for t in range(horizon + 1)
        ]
        peak = cp_sat_model.new_int_var(0, occ_max, "peak")

        # Add hints if available
        if self._w_hint is not None:
            for v, val in zip(w, self._w_hint):
                cp_sat_model.add_hint(v, val)
        if self._r_hint is not None:
            for v, val in zip(r, self._r_hint):
                cp_sat_model.add_hint(v, val)
        if self._occ_hint is not None:
            for v, val in zip(occ[1:], self._occ_hint):
                cp_sat_model.add_hint(v, val)

        # XON/XOFF specific variables
        in_pause = [
            cp_sat_model.new_bool_var(f"in_pause_{t}") for t in range(horizon + 1)
        ]

        # Initial occupancy
        cp_sat_model.add(occ[0] == 0)

        # Gate activity by profiles (also enforces per-step caps)
        for t in range(horizon):
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
        cp_sat_model.add(sum(r) <= params.sum_r_max)
        cp_sat_model.add(sum(r) >= params.sum_r_min)
        cp_sat_model.add(sum(w) <= params.sum_w_max)

        # If auto mode provided throughput target, enforce it here
        if self._throughput_abs_req is not None:
            cp_sat_model.add(sum(w) >= self._throughput_abs_req)

        # Peak tracking
        cp_sat_model.add_max_equality(peak, occ[1:])

        # XON/XOFF specific constraints

        cp_sat_model.add(in_pause[0] == 0)

        def geq_bool(var: cp_model.IntVar, thr: int, name: str) -> cp_model.IntVar:
            """Return a boolean variable that is true if var >= thr."""
            b = cp_sat_model.new_bool_var(name)
            cp_sat_model.add(var >= thr).only_enforce_if(b)
            cp_sat_model.add(var < thr).only_enforce_if(b.Not())
            return b

        # Create throttle_active variables (in_pause delayed by react_latency)
        throttle_active = [
            cp_sat_model.new_bool_var(f"throttle_active[{t}]") for t in range(horizon)
        ]

        # Engage after react_latency; hold for resume_latency after pause clears.
        # Implementation: throttle_active[t] ==
        # OR(in_pause[idx - k] for k=0..resume_latency),
        # where idx = t - react_latency (if idx-k < 0, that term is treated as 0).
        for t in range(horizon):
            sources = []
            if react_latency == 0:
                base_idx = t
            else:
                base_idx = t - react_latency
            # collect window over the shifted source
            for k in range(0, max(0, int(params.resume_latency)) + 1):
                j = base_idx - k
                if j >= 0:
                    sources.append(in_pause[j])

            if not sources:
                # No valid sources in window yet (pre-react window at the beginning)
                cp_sat_model.add(throttle_active[t] == 0)
            else:
                # Encode throttle_active[t] <=> OR(sources)
                # (1) OR(sources) => throttle_active[t]
                for s in sources:
                    cp_sat_model.add_implication(s, throttle_active[t])
                # (2) throttle_active[t] => OR(sources)
                cp_sat_model.add_bool_or([throttle_active[t].Not(), *sources])

        for t in range(horizon):
            # Hysteresis gates based on occ[t]
            enter_b = geq_bool(occ[t], xoff, f"enter_{t}")  # True if occ >= xoff
            # True if occ <= xon
            exit_b = cp_sat_model.new_bool_var(f"exit_{t}")
            # occ <= xon  <=>  NOT(occ >= xon+1)
            cp_sat_model.add(occ[t] <= xon).only_enforce_if(exit_b)
            cp_sat_model.add(occ[t] >= xon + 1).only_enforce_if(exit_b.Not())
            # exit_b = True when occupancy drops at or below xon
            # enter_b = True when occupancy rises at or above xoff
            # (maintaining proper hysteresis band)

            # Base mask is always active;
            # throttle only reduces allowance within valid slots
            cp_sat_model.add(w[t] <= params.w_max * self.write_valid[t])
            cp_sat_model.add(w[t] <= w_throttle_max).only_enforce_if(throttle_active[t])

            # Pause state update (true hysteresis):
            # in_pause[t+1] = (in_pause[t] AND NOT exit_b) OR enter_b
            # Linearization (bounds are sufficient and non-conflicting):
            cp_sat_model.add(in_pause[t + 1] >= enter_b)
            cp_sat_model.add(in_pause[t + 1] >= in_pause[t] - exit_b)
            cp_sat_model.add(in_pause[t + 1] <= in_pause[t] + enter_b)
            cp_sat_model.add(in_pause[t + 1] <= 1 - exit_b + enter_b)

            # assert in_pause rises same-cycle on enter when RL=0
            if react_latency == 0:
                cp_sat_model.add(in_pause[t] >= enter_b)

        # Create a solver
        solver = make_solver(max_time_s=15.0, workers=8)

        if self._peak_ub is not None:
            cp_sat_model.add(peak <= self._peak_ub)

        # Solve to maximize peak
        cp_sat_model.maximize(peak)
        status = solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = solver.StatusName(status)
            raise RuntimeError(
                f"Solve max peak failed with status={status} ({status_name})"
            )
        peak_star = int(solver.Value(peak))

        # Solve to find the earliest time of the peak
        # (always do this so auto-mode key uses t_star)
        cp_sat_model.add(peak == peak_star)
        _, t_star = self.add_earliest_peak_tiebreak(
            cp_sat_model, peak, occ, start_index=1
        )
        cp_sat_model.minimize(t_star)
        status = solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = solver.StatusName(status)
            raise RuntimeError(
                f"Solve earliest peak time failed with {status=} ({status_name})"
            )
        self.t_star_val = int(solver.Value(t_star))

        # Extract results
        self.results = XonXoffResults.make(
            solver=solver,
            peak=peak,
            w=w,
            r=r,
            occ=occ,
            xon=xon,
            xoff=xoff,
            throughput=0.0,  # updated in adjust_results()
            t_star=self.t_star_val if self.t_star_val is not None else 0,
        )
        self._adjust_results()

        # Extract witness as integers
        in_pause_seq = [solver.Value(in_pause[t]) for t in range(horizon)]
        throttle_active_seq = [solver.Value(throttle_active[t]) for t in range(horizon)]

        # Define witness to save to CSV
        self.results.witness_to_save = [
            self.results.w_seq,
            self.results.r_seq,
            in_pause_seq,
            throttle_active_seq,
            self.results.occ_seq,
        ]
        self.results.witness_labels = [
            "cycle",
            "w_seq",
            "r_seq",
            "in_pause",
            "throttle_active",
            "occ_seq",
        ]

        # Store check arguments for later validation (after save)
        # Pass occ_max for base checks and the *raw* throughput_target (if any)
        # so XonXoffResults.check() can compare target vs achieved throughput.
        target = params.throughput_target
        target_float: float | None
        if isinstance(target, (int, float)):
            target_float = float(target)
        else:
            # 'auto' or None → no explicit user target to enforce
            target_float = None

        self.results_check_args = {"occ_max": params.sum_w_max}
        if target_float is not None:
            self.results_check_args["throughput_target"] = target_float

        # pylint: enable=duplicate-code

    def _adjust_results(self) -> None:
        """Adjust results for CDC, margin, rounding."""
        # pylint: disable=duplicate-code
        assert self.params is not None, "Must call get_params() first"
        params = cast(XonXoffParams, self.params)

        assert self.results is not None, "Must call get_results() first"
        results = cast(XonXoffResults, self.results)

        # Adjust depth & thresholds with CDC semantics
        #
        # 1) Thresholds (xon/xoff) live in the big synchronous FIFO domain.
        #    They must be translated by the portion of capacity that we moved
        #    out of the CDC slice into the base sync FIFO, i.e. base_sync_fifo_depth.
        #    Do NOT scale thresholds by margins/rounding/atomic_tail.
        #
        # 2) Depth:
        #    - Add atomic_tail (implementation detail of storage)
        #    - Add base_sync_fifo_depth (CDC split)
        #    - Then apply margin and rounding to DEPTH ONLY.

        # (1) Translate thresholds by base_sync_fifo_depth
        if self.base_sync_fifo_depth > 0:
            results.xon += self.base_sync_fifo_depth
            results.xoff += self.base_sync_fifo_depth

        # (2) Build final depth
        depth = results.depth
        depth += params.atomic_tail
        if self.base_sync_fifo_depth > 0:
            depth += self.base_sync_fifo_depth
            logger.info(
                "Incremented %s.depth by %d for CDC.",
                results.__class__.__name__,
                self.base_sync_fifo_depth,
            )
        depth = apply_margin(depth, params.margin_type, params.margin_val)
        depth = round_value(depth, params.rounding)
        results.depth = depth

        # Optional safety clamp: keep thresholds within [0, results.depth]
        # (No-op if already valid; preserves hysteresis ordering.)
        results.xon = max(results.xon, 0)
        results.xoff = max(results.xoff, 0)
        results.xon = min(results.xon, results.depth)
        results.xoff = min(results.xoff, results.depth)

        # Compute achieved throughput as a ratio in [0.0, 1.0], normalized to
        # the maximum possible write volume (horizon * w_max).
        #
        # Note: w_seq length equals params.horizon. Guard against w_max == 0
        # (degenerate configs) by clamping the denominator to at least 1.
        total_w = sum(results.w_seq)
        denom = params.horizon * max(params.w_max, 1)
        raw_thr = total_w / float(denom) if denom > 0 else 0.0
        # Clamp to [0.0, 1.0] for numerical robustness.
        results.throughput = max(0.0, min(1.0, raw_thr))
        # pylint: enable=duplicate-code

    def _get_effective_thresholds(self, params: XonXoffParams) -> tuple[int, int, int]:
        """Return (xon_min_eff, xoff_lo_eff, xoff_hi_eff).

        Computes conservative lower bounds based on latencies and read capacity
        to ensure safe flow control operation.
        """

        delta_mask = max_wait_to_next_valid_slot(self.write_valid)
        l_total = (
            params.rd_latency
            + params.wr_latency
            + getattr(params, "resume_latency", 0)
            + delta_mask
        )
        max_reads = params.r_max * max_window_sum(self.read_valid, l_total)
        xon_min_auto = max_reads

        # Effective lower bound
        if params.xon_min is None or params.xon_min == "auto":
            xon_min_eff = 0
        else:
            xon_min_eff = int(params.xon_min)
        if xon_min_auto > xon_min_eff:
            msg = (
                "Auto-raising xon_min: user=%s -> auto=%d "
                "(rd_lat=%d, wr_lat=%d, resume_lat=%d, delta_mask=%d, L_total=%d)"
            )
            logger.info(
                msg,
                str(params.xon_min),
                xon_min_auto,
                params.rd_latency,
                params.wr_latency,
                getattr(params, "resume_latency", 0),
                delta_mask,
                l_total,
            )
            xon_min_eff = xon_min_auto

        # Tighten lower bound by min hysteresis at xon_min (ratio or absolute)
        mh_min = self._hys_min_for_xon(params, xon_min_eff)

        if isinstance(params.xoff_range, list):
            xoff_lo, xoff_hi = params.xoff_range
            xoff_lo_eff = max(xoff_lo, xon_min_eff + mh_min)
            # Cap the upper bound using max hysteresis evaluated
            # at xon_min (conservative)
            hmax_cap = self._hys_max_for_xon(params, max(1, xon_min_eff))
            xoff_hi_eff = min(xoff_hi, xoff_lo_eff + hmax_cap, params.sum_w_max)
        else:
            # Auto range: start at the hysteresis-tight lower bound,
            # cap width by band_max_ratio * xon_min, and by sum_w_max.
            xoff_lo_eff = xon_min_eff + mh_min
            hmax_cap = self._hys_max_for_xon(params, max(1, xon_min_eff))
            xoff_hi_eff = min(params.sum_w_max, xoff_lo_eff + hmax_cap)

        # Guard: if tightened range is empty, we can fail fast
        if xoff_lo_eff > xoff_hi_eff:
            raise RuntimeError(
                f"No feasible xoff after bounds tightening: "
                f"xoff_lo'={xoff_lo_eff} > xoff_hi={xoff_hi_eff}"
            )

        return xon_min_eff, xoff_lo_eff, xoff_hi_eff

    def _get_throughput_upper_bound(self, params: XonXoffParams, band: int) -> float:
        """Calculate throughput upper bound for a given hysteresis band.

        Models duty cycle considering write/read densities, reaction latency,
        and pause/resume behavior to estimate achievable throughput.
        """
        w_den = sum(int(v) for v in self.write_valid[: params.horizon]) / params.horizon
        r_den = sum(int(v) for v in self.read_valid[: params.horizon]) / params.horizon
        # simple hard-stop model with react_latency
        net = max(w_den - r_den, 0.0)
        if net == 0.0 or r_den == 0.0:
            return w_den  # degenerate bound
        t_active = band / net
        t_active_prime = t_active + params.react_latency
        t_pause = band / r_den
        duty = t_active_prime / (t_active_prime + t_pause)
        return w_den * duty

    def _hys_max_for_xon(self, p: "XonXoffParams", xon_val: int) -> int:
        """Return maximum hysteresis band for a given xon.
        If value is int -> absolute; if float -> ceil(ratio * xon)."""
        assert p.hysteresis is not None
        hmax = p.hysteresis[1]
        if isinstance(hmax, float):
            return int(math.ceil(hmax * xon_val))
        return int(hmax)

    def _hys_min_for_xon(self, p: "XonXoffParams", xon_val: int) -> int:
        """Return minimum hysteresis band for a given xon.
        If value is int -> absolute; if float -> ceil(ratio * xon)."""
        assert p.hysteresis is not None
        hmin = p.hysteresis[0]
        if isinstance(hmin, float):
            return int(math.ceil(hmin * xon_val))
        return int(hmin)

    def _max_ratio_if_any(self, p: "XonXoffParams") -> float | None:
        assert p.hysteresis is not None
        hmax = p.hysteresis[1]
        return float(hmax) if isinstance(hmax, float) else None

    def _min_ratio_if_any(self, p: "XonXoffParams") -> float | None:
        """If hysteresis min is a ratio, return it; else None."""
        assert p.hysteresis is not None
        return float(p.hysteresis[0]) if isinstance(p.hysteresis[0], float) else None
