# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_cbfc.py

"""Calculate Credit-Based Flow Control (CBFC) fifo depth."""

from __future__ import annotations

import logging
from math import ceil
from typing import List, Literal, cast

from ortools.sat.python import cp_model
from pydantic import NonNegativeInt

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
)
from abe.utils import round_value

logger = logging.getLogger(__name__)

Auto = Literal["auto"]


class CbfcModel(FifoModel):
    """Credit-Based Flow Control (CBFC) FIFO model with credit parameters for
    YAML validation.
    """

    cred_max: NonNegativeInt | Auto = "auto"
    cred_init: NonNegativeInt | Auto = "auto"
    cred_gran: NonNegativeInt = 1
    cred_ret_latency: NonNegativeInt = 0
    cred_auto_optimize: bool = True
    cred_headroom: NonNegativeInt = 2
    cred_margin_type: Literal["percentage", "absolute"] = "absolute"
    cred_margin_val: int = 0
    cred_rounding: Literal["power2", "none"] = "none"


class CbfcParams(FifoParams):  # pylint: disable=too-many-instance-attributes
    """CBFC FIFO parameters including credit pool configuration, latencies, and
    margin settings.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        *,
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
        cred_max: int,
        cred_init: int,
        cred_gran: int = 1,
        cred_ret_latency: int = 0,
        cred_auto_optimize: bool = True,
        cred_headroom: int = 2,
        cred_margin_type: Literal["percentage", "absolute"] = "absolute",
        cred_margin_val: int = 0,
        cred_rounding: Literal["power2", "none"] = "none",
    ) -> None:
        # pylint: disable=duplicate-code
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
        # pylint: enable=duplicate-code
        self.cred_max = cred_max
        self.cred_init = cred_init
        self.cred_gran = cred_gran
        self.cred_ret_latency = cred_ret_latency
        self.cred_auto_optimize = cred_auto_optimize
        self.cred_headroom = cred_headroom
        self.cred_margin_type = cred_margin_type
        self.cred_margin_val = cred_margin_val
        self.cred_rounding = cred_rounding

    @classmethod
    def from_model(cls, model: FifoBaseModel) -> "CbfcParams":
        """Create CbfcParams from a validated CbfcModel instance."""
        if not isinstance(model, CbfcModel):
            raise TypeError(f"Expected CbfcModel, got {type(model).__name__}")

        def _to_int(x: NonNegativeInt | Auto) -> int:
            return -1 if x == "auto" else int(x)

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
            # CBFC specific parameters
            cred_max=_to_int(model.cred_max),
            cred_init=_to_int(model.cred_init),
            cred_gran=int(model.cred_gran),
            cred_ret_latency=int(model.cred_ret_latency),
            cred_auto_optimize=bool(model.cred_auto_optimize),
            cred_headroom=int(model.cred_headroom),
            cred_margin_type=model.cred_margin_type,
            cred_margin_val=int(model.cred_margin_val),
            cred_rounding=model.cred_rounding,
        )

    def check(self) -> None:
        """Validate CBFC-specific parameter constraints including credit bounds
        and granularity.
        """
        super().check()
        if self.cred_max != -1 and self.cred_init != -1:
            if self.cred_max < 0 or self.cred_init < 0:
                raise ValueError(f"{self.cred_max=}, {self.cred_init=}")
            if self.cred_init > self.cred_max:
                raise ValueError(f"{self.cred_init=}, {self.cred_max=}")
        if self.cred_gran <= 0:
            raise ValueError(f"{self.cred_gran=}")
        if self.cred_ret_latency < 0:
            raise ValueError(f"{self.cred_ret_latency=}")
        if self.cred_margin_val < 0:
            raise ValueError(f"{self.cred_margin_val=}")


class CbfcResults(FifoResults):  # pylint: disable=too-many-instance-attributes
    """Results container for CBFC solver including computed credit pool
    parameters and FIFO witness.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        depth: int,
        occ_peak: int,
        w_seq: List[int],
        r_seq: List[int],
        occ_seq: List[int],
        cred_max: int,
        cred_init: int,
        throughput: float,
    ) -> None:
        super().__init__(depth, occ_peak, w_seq, r_seq, occ_seq)
        self.cred_max = cred_max
        self.cred_init = cred_init
        # Initial throughput placeholder (normalized to write capacity).
        # The solver will overwrite this in adjust_results() once w_seq is known.
        self.throughput = throughput

    @classmethod
    def make(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        solver: cp_model.CpSolver,
        peak: cp_model.IntVar,
        w: List[cp_model.IntVar],
        r: List[cp_model.IntVar],
        occ: List[cp_model.IntVar],
        cred_max: int,
        cred_init: int,
        throughput: float,
    ) -> "CbfcResults":
        """Create CbfcResults from solver solution, extracting witness and
        computing final depth.
        """
        occ_peak, w_seq, r_seq, occ_seq = extract_witness(solver, peak, w, r, occ)
        depth = occ_peak
        return cls(
            depth, occ_peak, w_seq, r_seq, occ_seq, cred_max, cred_init, throughput
        )

    def check(self, occ_max: int) -> None:
        """Validate results and provide implementation guidance for minimal
        occupancy cases.
        """
        super().check(occ_max)
        if self.occ_peak <= 1 and (self.cred_max or self.cred_init):
            needed_credits = max(self.cred_max, self.cred_init)
            self.msg = (
                "In hardware, implement at least a minimal skid/bypass FIFO "
                f"(1-2 entries) plus a {needed_credits} credit counter or pool."
            )


class CbfcSolver(FifoSolver):
    """CBFC FIFO depth solver using constraint programming to find worst-case
    occupancy under credit-based flow control with automatic or manual credit
    configuration.

    Credits are validated for feasibility; occupancy sizing follows ready/valid
    style against layered traffic profile caps.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model_class = CbfcModel
        self.params_class = CbfcParams
        self.results_class = CbfcResults
        self._cred_bounds: dict[str, int] = {}

    def get_unique_keys(self) -> None:
        super().get_unique_keys()
        assert self.spec, "Must call get_spec() first"
        self.get_one_unique_key("cred_max", required=False)
        self.get_one_unique_key("cred_init", required=False)
        self.get_one_unique_key("cred_gran", required=False)
        self.get_one_unique_key("cred_ret_latency", required=False)
        self.get_one_unique_key("cred_auto_optimize", required=False)
        self.get_one_unique_key("cred_headroom", required=False)
        self.get_one_unique_key("cred_margin_type", required=False)
        self.get_one_unique_key("cred_margin_val", required=False)
        self.get_one_unique_key("cred_rounding", required=False)

    def get_params(self) -> None:
        """Convert validated model into parameter object and adjust rd_latency for
        CDC synchronizer cycles if applicable.
        """
        super().get_params()
        params = cast(CbfcParams, self.params)
        adjust_rd_latency_for_cdc(params, self.rd_sync_cycles_in_wr)

    def get_results(
        self,
    ) -> (
        None
    ):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        # pylint: disable=duplicate-code

        assert self.params is not None, "Must call get_params() first"
        params = cast(CbfcParams, self.params)

        # Local variables for convenience
        horizon = params.horizon
        w_max = params.w_max
        r_max = params.r_max
        sum_w_min = params.sum_w_min
        sum_w_max = params.sum_w_max
        sum_r_min = params.sum_r_min
        sum_r_max = params.sum_r_max
        wr_latency = params.wr_latency
        rd_latency = params.rd_latency
        cred_max = params.cred_max
        cred_init = params.cred_init
        cred_gran = params.cred_gran
        cred_ret_latency = params.cred_ret_latency

        if cred_init == -1 or cred_max == -1:  # auto values
            mode = "AUTO"
            cred_init, cred_max = self._resolve_auto_credits(params)
        else:  # user-provided values
            mode = "USER"
            self._check_user_credits()

        logger.info(
            "Effective credits: mode=%s, cred_init=%d, cred_max=%d",
            mode,
            cred_init,
            cred_max,
        )
        logger.info(
            "CBFC credit pipeline: rd_latency=%d, cred_ret_latency=%d, total=%d",
            rd_latency,
            cred_ret_latency,
            rd_latency + cred_ret_latency,
        )

        ub_asymp, ub_startup, limiter = self._get_throughput_upper_bound(
            params, cred_init
        )
        r_req = sum_r_min / horizon

        s = "Rate Summary:\n"
        s += f"  Required read rate: {r_req:.6f} items/cycle\n"
        s += f"  Asymptotic UB:      {ub_asymp:.6f}\n"
        s += f"  Startup UB:         {ub_startup:.6f} (limiter: {limiter})\n"
        s += f"  Write cap density:  {sum_w_max / horizon:.6f}"
        logger.info(s)

        if min(ub_asymp, ub_startup, sum_w_max / horizon) < r_req:
            raise SystemExit(
                "CBFC cannot guarantee the requested read throughput. "
                "Increase credits (cred_init and/or cred_max), "
                "reduce latencies, or relax profiles."
            )

        # Define the maximum possible occupancy
        max_deficit = self._cred_bounds.get("max_deficit", 0)
        occ_max = min(sum_w_max, cred_init + max_deficit)
        logger.info(
            "Occupancy pruning: occ_max=%d "
            "(min(sum_w_max=%d, cred_init=%d + max_deficit=%d))",
            occ_max,
            sum_w_max,
            cred_init,
            max_deficit,
        )

        # Create CP-SAT model
        cp_sat_model = cp_model.CpModel()

        # Setup base variables
        w = [cp_sat_model.NewIntVar(0, w_max, f"w_{t}") for t in range(horizon)]
        r = [cp_sat_model.NewIntVar(0, r_max, f"r_{t}") for t in range(horizon)]
        occ = [
            cp_sat_model.NewIntVar(0, occ_max, f"occ_{t}") for t in range(horizon + 1)
        ]
        peak = cp_sat_model.NewIntVar(0, occ_max, "peak")

        # CBFC-specific variables
        cred = [
            cp_sat_model.NewIntVar(0, cred_max, f"cred_{t}") for t in range(horizon + 1)
        ]
        ret = [
            cp_sat_model.NewIntVar(0, r_max * cred_gran, f"ret_{t}")
            for t in range(horizon)
        ]

        # Add constraints

        cp_sat_model.Add(occ[0] == 0)
        cp_sat_model.Add(cred[0] == cred_init)

        for t in range(horizon):
            cp_sat_model.Add(w[t] <= params.w_max * self.write_valid[t])
            cp_sat_model.Add(r[t] <= params.r_max * self.read_valid[t])

        w_eff: List[cp_model.IntVar | None] = [None] * horizon
        r_eff: List[cp_model.IntVar | None] = [None] * horizon
        for t in range(horizon):
            w_eff[t] = w[t - wr_latency] if t >= wr_latency else None
            r_eff[t] = r[t - rd_latency] if t >= rd_latency else None
            if w_eff[t] is None and r_eff[t] is None:
                cp_sat_model.Add(occ[t + 1] == occ[t])
            elif w_eff[t] is not None and r_eff[t] is None:
                w_val = w_eff[t]
                assert w_val is not None
                cp_sat_model.Add(occ[t + 1] == occ[t] + w_val)
            elif r_eff[t] is not None and w_eff[t] is None:
                r_val = r_eff[t]
                assert r_val is not None
                cp_sat_model.Add(occ[t + 1] == occ[t] - r_val)
            elif w_eff[t] is not None and r_eff[t] is not None:
                w_val = w_eff[t]
                r_val = r_eff[t]
                assert w_val is not None and r_val is not None
                cp_sat_model.Add(occ[t + 1] == occ[t] + w_val - r_val)

        for t in range(horizon):
            src_idx = t - cred_ret_latency
            if src_idx >= 0 and r_eff[src_idx] is not None:
                r_val = r_eff[src_idx]
                assert r_val is not None
                cp_sat_model.Add(ret[t] == cred_gran * r_val)
            else:
                cp_sat_model.Add(ret[t] == 0)

        for t in range(horizon):
            cp_sat_model.Add(cred[t + 1] == cred[t] - w[t] + ret[t])

        for t in range(horizon):
            cp_sat_model.Add(w[t] <= cred[t])

        cp_sat_model.Add(sum(w) >= sum_w_min)
        cp_sat_model.Add(sum(w) <= sum_w_max)
        cp_sat_model.Add(sum(r) >= sum_r_min)
        cp_sat_model.Add(sum(r) <= sum_r_max)

        cp_sat_model.AddMaxEquality(peak, occ[1:])

        # Create a solver
        solver = make_solver(max_time_s=15.0, workers=8)

        # Solve to maximize peak
        cp_sat_model.Maximize(peak)
        status = solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):  # type: ignore
            status_name = solver.StatusName(status)
            raise RuntimeError(
                f"Solve max peak failed with status={status} ({status_name})"
            )
        peak_star = int(solver.Value(peak))

        # Solve to find the earliest time of the peak
        cp_sat_model.Add(peak == peak_star)
        _, t_star = self.add_earliest_peak_tiebreak(
            cp_sat_model, peak, occ, start_index=1
        )
        cp_sat_model.Minimize(t_star)
        status = solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):  # type: ignore
            status_name = solver.StatusName(status)
            raise RuntimeError(
                f"Solve earliest peak time failed with status={status} ({status_name})"
            )

        # Extract results
        self.results = CbfcResults.make(
            solver=solver,
            peak=peak,
            w=w,
            r=r,
            occ=occ,
            cred_max=cred_max,
            cred_init=cred_init,
            throughput=0.0,  # Placeholder, overwritten in adjust_results()
        )
        self.adjust_results()

        # Define witness to save to CSV
        cred_seq = [solver.Value(cred[t]) for t in range(horizon)]
        ret_seq = [solver.Value(ret[t]) for t in range(horizon)]
        self.results.witness_to_save = [
            self.results.w_seq,
            self.results.r_seq,
            cred_seq,
            ret_seq,
            self.results.occ_seq,
        ]
        self.results.witness_labels = [
            "cycle",
            "w_seq",
            "r_seq",
            "cred_seq",
            "ret_seq",
            "occ_seq",
        ]

        # Store check arguments for later validation (after save)
        self.results_check_args = {"occ_max": occ_max}

        # pylint: enable=duplicate-code

    def _adaptive_headroom(self, p: CbfcParams) -> int:
        """Choose headroom from read-valid mask 'gapiness'.
        Uses the longest wait to next valid slot as a deterministic cushion."""
        gap = max_wait_to_next_valid_slot(self.read_valid)
        # Clamp to a sensible band: [1, 2*gap] but never exceed sum_w_max
        raw = max(1, gap)
        return min(2 * raw, max(1, p.sum_w_max // 16))

    def adjust_results(self) -> None:
        """Adjust results for CDC, margin, rounding."""
        # pylint: disable=duplicate-code
        assert self.params is not None, "Must call get_params() first"
        params = cast(CbfcParams, self.params)

        assert self.results is not None, "Must call get_results() first"
        results = cast(CbfcResults, self.results)

        # Adjust depth & credits with CDC semantics
        #
        # 1) Credits (cred_init/cred_max) live in the big synchronous FIFO domain.
        #    They must be translated by the portion of capacity that we moved
        #    out of the CDC slice into the base sync FIFO, i.e. base_sync_fifo_depth.
        #    Do NOT scale credits by margins/rounding.
        #
        # 2) Depth:
        #    - Add base_sync_fifo_depth (CDC split)
        #    - Then apply margin and rounding to DEPTH ONLY.

        # (1) Translate credits by base_sync_fifo_depth
        if self.base_sync_fifo_depth > 0:
            results.cred_init += self.base_sync_fifo_depth
            results.cred_max += self.base_sync_fifo_depth

        # (2) Build final depth
        depth = results.depth
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

        # Optional safety clamp: keep credits within [0, results.depth]
        # (No-op if already valid.)
        results.cred_init = max(results.cred_init, 0)
        results.cred_max = max(results.cred_max, 0)
        results.cred_init = min(results.cred_init, results.depth)
        results.cred_max = min(results.cred_max, results.depth)

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

        # ------------------------------------------------------------------
        # Basic throughput sanity check (same spirit as XON/XOFF):
        #
        # Required read rate in items/cycle:
        #     r_req = sum_r_min / horizon
        #
        # Our throughput metric is normalized to the max write capacity
        # (w_max items/cycle), so the corresponding target fraction is:
        #     target_thr = r_req / w_max, clamped to [0, 1].
        #
        # If achieved throughput falls below this target, mark basic checks
        # as failed and attach a human-readable message.
        # ------------------------------------------------------------------
        r_req = params.sum_r_min / params.horizon
        max_w = max(params.w_max, 1)
        target_thr = max(0.0, min(1.0, r_req / max_w))

        if results.throughput + 1e-9 < target_thr:
            # Attach / overwrite basic_checks_pass and msg, similar to XON/XOFF.
            results.basic_checks_pass = False
            msg = (
                "CBFC achieved throughput below target: "
                f"target={target_thr:.6f}, "
                f"actual={results.throughput:.6f} "
                "(normalized to write capacity)."
            )
            # If there is already a message, append; otherwise set.
            if getattr(results, "msg", ""):
                results.msg = f"{results.msg}  {msg}"
            else:
                results.msg = msg
        # pylint: enable=duplicate-code

    def _check_user_credits(self) -> None:  # pylint: disable=too-many-locals
        """Validate that user-provided credit parameters are sufficient for the
        configured traffic profiles and latencies.

        Computes minimum required credits and raises SystemExit if user values
        are insufficient.
        """

        assert self.params is not None, "Must call get_params() first"
        params = cast(CbfcParams, self.params)

        if params.cred_init == -1 or params.cred_max == -1:
            logger.info(
                "Auto credit mode detected in check_user_credits(); "
                "skipping strict bound enforcement."
            )
            return

        horizon = params.horizon
        w_max = params.w_max
        r_max = params.r_max
        rd_latency = params.rd_latency
        cred_gran = params.cred_gran
        cred_ret_latency = params.cred_ret_latency

        w_cap = [w_max * b for b in self.write_valid]
        r_cap = [r_max * b for b in self.read_valid]

        r_lat = [0] * horizon
        for t in range(horizon):
            u = t - rd_latency
            r_lat[t] = r_cap[u] if u >= 0 else 0

        ret = [0] * horizon
        for t in range(horizon):
            v = t - cred_ret_latency
            ret[t] = cred_gran * (r_lat[v] if v >= 0 else 0)

        cw = 0
        cr = 0
        max_deficit = 0
        max_surplus = 0
        for t in range(horizon):
            cw += w_cap[t]
            cr += ret[t]
            max_deficit = max(max_deficit, cw - cr)  # writes outrun returns
            max_surplus = max(max_surplus, cr - cw)  # returns outrun writes

        cred_init_lb = max(0, max_deficit)
        cred_max_lb = cred_init_lb + max_surplus

        s = "CBFC Credit Check Summary:\n"
        s += f"  Calculated minimum initial credits: {cred_init_lb}\n"
        s += f"  Calculated minimum maximum credits: {cred_max_lb}\n"
        s += f"  User initial credits: {params.cred_init}\n"
        s += f"  User maximum credits: {params.cred_max}"
        logger.info(s)

        if params.cred_init < cred_init_lb or params.cred_max < cred_max_lb:
            raise SystemExit(
                "CBFC credits too small for the latencies / layered profiles.\n"
                f"Required:\n"
                f"    cred_init ≥ {cred_init_lb}, cred_max ≥ {cred_max_lb}\n"
                f"Provided:\n"
                f"    cred_init = {params.cred_init}, cred_max = {params.cred_max}\n"
                "Either increase credits or relax profiles/sums."
            )

        self._cred_bounds = {
            "cred_init_lb": cred_init_lb,
            "cred_max_lb": cred_max_lb,
            "max_deficit": max_deficit,
            "max_surplus": max_surplus,
        }

    def _compute_credit_bounds_from_caps(
        self, p: CbfcParams
    ) -> tuple[int, int, int, int]:
        """Compute minimum required credit bounds from write/read capacity
        profiles.

        Returns tuple of (cred_init_lb, cred_max_lb, max_deficit, max_surplus)
        based on worst-case write/read imbalances considering all latencies.
        """
        h = p.horizon
        w_cap = [p.w_max * b for b in self.write_valid]
        r_cap = [p.r_max * b for b in self.read_valid]

        # latency-affected read enable vis-à-vis credits
        r_lat = [
            (r_cap[t - p.rd_latency] if t - p.rd_latency >= 0 else 0) for t in range(h)
        ]
        ret = [
            p.cred_gran
            * (r_lat[t - p.cred_ret_latency] if t - p.cred_ret_latency >= 0 else 0)
            for t in range(h)
        ]

        cw = cr = 0
        max_deficit = max_surplus = 0
        for t in range(h):
            cw += w_cap[t]
            cr += ret[t]
            max_deficit = max(max_deficit, cw - cr)
            max_surplus = max(max_surplus, cr - cw)

        cred_init_lb = max(0, max_deficit)
        cred_max_lb = cred_init_lb + max_surplus
        return cred_init_lb, cred_max_lb, max_deficit, max_surplus

    def _feasible_with_credits(  # pylint: disable=too-many-locals
        self, p: CbfcParams, ci: int, cm: int
    ) -> bool:
        """Return True if there exists a (w,r) schedule that meets sums/caps
        with the credit pool recurrence under (ci, cm)."""
        h = p.horizon
        m = cp_model.CpModel()
        w = [m.NewIntVar(0, p.w_max, f"w_{t}") for t in range(h)]
        r = [m.NewIntVar(0, p.r_max, f"r_{t}") for t in range(h)]
        cred = [m.NewIntVar(0, cm, f"cred_{t}") for t in range(h + 1)]
        ret = [m.NewIntVar(0, p.r_max * p.cred_gran, f"ret_{t}") for t in range(h)]

        # caps
        for t in range(h):
            m.Add(w[t] <= p.w_max * self.write_valid[t])
            m.Add(r[t] <= p.r_max * self.read_valid[t])

        # returns (respect rd_latency and cred_ret_latency)
        r_eff: List[cp_model.IntVar | None] = [None] * h
        for t in range(h):
            u = t - p.rd_latency
            r_eff[t] = r[u] if u >= 0 else None
        for t in range(h):
            v = t - p.cred_ret_latency
            if v >= 0 and r_eff[v] is not None:
                m.Add(ret[t] == p.cred_gran * r_eff[v])  # type: ignore
            else:
                m.Add(ret[t] == 0)

        # credit pool
        m.Add(cred[0] == ci)
        for t in range(h):
            m.Add(cred[t + 1] == cred[t] - w[t] + ret[t])
            m.Add(w[t] <= cred[t])  # cannot write more than current credits

        # sums
        m.Add(sum(w) >= p.sum_w_min)
        m.Add(sum(w) <= p.sum_w_max)
        m.Add(sum(r) >= p.sum_r_min)
        m.Add(sum(r) <= p.sum_r_max)

        # We only need feasibility.
        s = make_solver(max_time_s=5.0, workers=8)
        status = s.Solve(m)
        return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)  # type: ignore

    def _get_throughput_upper_bound(  # pylint: disable=too-many-locals
        self, p: CbfcParams, cred_init_eff: int
    ) -> tuple[float, float, Literal["credits_startup", "write_caps", "read_caps"]]:
        """Calculate throughput upper bounds for CBFC configuration.

        Returns (ub_asymptotic, ub_startup_min, limiting_factor) where:
        - ub_asymptotic: Long-run throughput bound from min(write, read) density
        - ub_startup_min: Credit-limited bound during startup before returns
        - limiting_factor: Which constraint is tightest (credits, write, or read)

        All throughput values are in items/cycle.
        """

        h = p.horizon
        w_density_max = p.sum_w_max / h
        r_density_max = p.sum_r_max / h
        r_req = p.sum_r_min / h

        # Asymptotic (cred_gran >= 1 never reduces the long-run bound for this model)
        ub_asymptotic = min(w_density_max, r_density_max)

        # Startup credit-limited bound over short windows:
        # Over any [0..T), total writes ≤ cred_init_eff + sum_{t<T} ret[t].
        # We conservatively assume reads arrive no faster than a uniform schedule
        # meeting r_req once writes make data available;
        # returns appear after rd_latency + cred_ret_latency.
        lat = p.rd_latency + p.cred_ret_latency

        # Simple conservative lower return model (uniform r_req once T>L):
        # ret_sum(T) ≈ cred_gran * r_req * max(0, T - L)
        # => credit-limited avg write rate
        # UB over window T: (cred_init_eff + ret_sum(T)) / T
        ub_startup_min = float("inf")
        t_max = min(
            h, max(32, 8 * (lat + 1))
        )  # scan a reasonable prefix of the horizon
        for t in range(1, t_max + 1):
            ret_sum = p.cred_gran * r_req * max(0, t - lat)
            ub_t = (cred_init_eff + ret_sum) / t
            ub_startup_min = min(ub_startup_min, ub_t)

        # Final "guaranteed read" bound is limited by:
        #   credits during startup, write caps, and read caps
        limiting_triplet = {
            "credits_startup": ub_startup_min,
            "write_caps": w_density_max,
            "read_caps": r_density_max,
        }
        limiting_factor = cast(
            Literal["credits_startup", "write_caps", "read_caps"],
            min(limiting_triplet, key=lambda k: limiting_triplet[k]),
        )
        return ub_asymptotic, ub_startup_min, limiting_factor

    def _minimize_auto_credits(self, p: CbfcParams) -> tuple[int, int]:
        """Lexicographic minimization:
        1) minimize cred_init, 2) given cred_init, minimize cred_max.
        Uses bounds from compute_credit_bounds_from_caps() and binary search."""
        ci_lb, cm_lb, _, _ = self._compute_credit_bounds_from_caps(p)
        # Upper bounds: never need more than sum_w_max, and cred_max >= cred_init
        ub = max(p.sum_w_max, cm_lb)
        # First, find minimal cred_init
        lo, hi = ci_lb, ub
        best_ci = None
        while lo <= hi:
            mid = (lo + hi) // 2
            # cred_max must be at least cm_lb and >= mid; try the smallest first
            trial_cm = max(cm_lb, mid)
            if self._feasible_with_credits(p, mid, trial_cm):
                best_ci = mid
                hi = mid - 1
            else:
                lo = mid + 1
        if best_ci is None:
            # Not feasible even at large UB -> let caller handle with its checks
            return p.cred_gran, p.sum_w_max

        # Next, minimize cred_max given best_ci
        lo, hi = max(cm_lb, best_ci), ub
        best_cm = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._feasible_with_credits(p, best_ci, mid):
                best_cm = mid
                hi = mid - 1
            else:
                lo = mid + 1
        assert best_cm is not None
        return best_ci, best_cm

    def _quick_cap_auto_credits(self, p: CbfcParams) -> tuple[int, int]:
        """Compute automatic credit values using bandwidth-delay product style
        estimation.

        Calculates credits needed for phase/latency cushion and horizon backlog,
        then clamps and quantizes to credit granularity.

        Returns (cred_init_auto, cred_max_auto) as the same value.
        """
        # phase cushion from read-valid mask
        cushion = max_wait_to_next_valid_slot(self.read_valid)
        phase_lat_cushion = p.r_max * (p.rd_latency + p.cred_ret_latency) + cushion

        # backlog required by whole-horizon balance: total_w ≥ sum_w_min and
        # returns over the horizon are ≤ cred_gran * (sum_r_min - tail_loss),
        # where up to L = rd_latency + cred_ret_latency reads at the end of the
        # horizon haven't returned yet. Worst-case tail_loss ≤ r_max * L.
        lat = p.rd_latency + p.cred_ret_latency
        tail_loss = p.r_max * lat
        needed_backlog = max(
            0, p.sum_w_min - p.cred_gran * p.sum_r_min + p.cred_gran * tail_loss
        )

        # choose the larger of the two; this avoids infeasible “not enough credits”
        base = max(phase_lat_cushion, needed_backlog)

        # clamp to sane range
        base = max(p.cred_gran, min(base, p.sum_w_max))
        # quantize up to multiple of cred_gran
        q = ((base + p.cred_gran - 1) // p.cred_gran) * p.cred_gran
        return q, q

    def _resolve_auto_credits(  # pylint: disable=too-many-locals
        self, p: CbfcParams
    ) -> tuple[int, int]:
        """Resolve automatic credit values to concrete integers, preserving any
        user-specified values.

        Computes credit bounds from traffic profiles, applies margins and
        rounding, and adds headroom for auto mode.

        Returns (cred_init, cred_max) with all 'auto' values resolved.
        """
        # Quick path: if either is auto, derive starting window; optionally minimize.
        if p.cred_init == -1 or p.cred_max == -1:
            # seed
            qi, qm = self._quick_cap_auto_credits(p)
            if p.cred_auto_optimize:
                # Find minimal feasible pair; prefer lexicographic minimum
                mi, mm = self._minimize_auto_credits(p)
                qi, qm = mi, mm
            cred_init = qi if p.cred_init == -1 else p.cred_init
            cred_max = qm if p.cred_max == -1 else max(p.cred_max, cred_init)
            # Always compute informative bounds from caps for pruning/logging
            ci_lb, cm_lb, max_deficit, max_surplus = (
                self._compute_credit_bounds_from_caps(p)
            )
            self._cred_bounds = {
                "cred_init_lb": ci_lb,
                "cred_max_lb": cm_lb,
                "max_deficit": max_deficit,
                "max_surplus": max_surplus,
            }
            r_req = p.sum_r_min / p.horizon
            lat = p.rd_latency + p.cred_ret_latency
            cred_init_startup = ceil(r_req * lat)
        else:
            # USER path (no autos): compute informative bounds for logging/cuts
            cred_init_lb, cred_max_lb, max_deficit, max_surplus = (
                self._compute_credit_bounds_from_caps(p)
            )
            r_req = p.sum_r_min / p.horizon
            lat = p.rd_latency + p.cred_ret_latency
            cred_init_startup = ceil(r_req * lat)
            cred_init = p.cred_init
            cred_max = p.cred_max
            self._cred_bounds = {
                "cred_init_lb": cred_init_lb,
                "cred_max_lb": cred_max_lb,
                "max_deficit": max_deficit,
                "max_surplus": max_surplus,
            }

        # apply optional margin/rounding to both; ensure ordering
        mtype = cast(  # type: ignore[redundant-cast]
            Literal["percentage", "absolute"], p.cred_margin_type
        )
        rounding = cast(  # type: ignore[redundant-cast]
            Literal["power2", "none"], p.cred_rounding
        )
        cred_init = apply_margin(cred_init, mtype, p.cred_margin_val)
        cred_init = round_value(cred_init, rounding)

        cred_max = apply_margin(cred_max, mtype, p.cred_margin_val)
        cred_max = round_value(cred_max, rounding)

        cred_max = max(cred_max, cred_init)  # keep sane early

        # deterministic headroom: adaptive if autos are used, else keep user’s
        if p.cred_init == -1 or p.cred_max == -1:
            hr = self._adaptive_headroom(p)
            logger.info(
                "CBFC adaptive headroom: gap=%d → hr=%d",
                max_wait_to_next_valid_slot(self.read_valid),
                hr,
            )
        else:
            hr = p.cred_headroom
        if p.cred_init == -1:
            cred_init += hr
        if p.cred_max == -1:
            cred_max += hr

        logger.info(
            "CBFC Auto Credits:\n"
            "  startup L=%d, r_req=%.6f → cred_init_startup≥%d\n"
            "  bounds:  cred_init_lb=%d, cred_max_lb=%d\n"
            "  chosen:  cred_init=%d, cred_max=%d (+headroom=%d)",
            lat,
            r_req,
            cred_init_startup,
            self._cred_bounds.get("cred_init_lb", -1),
            self._cred_bounds.get("cred_max_lb", -1),
            cred_init,
            cred_max,
            hr,
        )

        return cred_init, cred_max
