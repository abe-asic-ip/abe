# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_replay.py

"""Calculate Replay FIFO depth."""

from __future__ import annotations

import logging
from typing import List, Literal, cast

from ortools.sat.python import cp_model
from pydantic import NonNegativeInt

from abe.uarch.fifo_depth_base import (
    FifoBaseModel,
    FifoBaseParams,
    FifoResults,
    FifoSolver,
)
from abe.uarch.fifo_depth_utils import (
    apply_margin,
    extract_witness,
    make_solver,
)
from abe.utils import round_value

logger = logging.getLogger(__name__)


class ReplayModel(FifoBaseModel):
    """Replay FIFO model with round-trip time (RTT) and atomic tail
    configuration for YAML validation.
    """

    horizon: NonNegativeInt
    w_max: NonNegativeInt = 1
    atomic_tail: NonNegativeInt = 0
    rtt: NonNegativeInt


class ReplayParams(FifoBaseParams):  # pylint: disable=too-many-instance-attributes
    """Replay FIFO parameters including horizon, write capacity, round-trip time,
    atomic tail, and margin configuration.
    """

    horizon: int
    w_max: int
    atomic_tail: int
    rtt: int

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        margin_type: Literal["percentage", "absolute"] = "absolute",
        margin_val: int = 0,
        rounding: Literal["power2", "none"] = "none",
        horizon: int,
        w_max: int = 1,
        atomic_tail: int = 0,
        rtt: int,
    ) -> None:
        super().__init__(
            margin_type=margin_type, margin_val=margin_val, rounding=rounding
        )
        self.horizon = horizon
        self.w_max = w_max
        self.atomic_tail = atomic_tail
        self.rtt = rtt

    @classmethod
    def from_model(cls, model: FifoBaseModel) -> "ReplayParams":
        """Create ReplayParams from a validated ReplayModel instance."""
        if not isinstance(model, ReplayModel):
            raise TypeError(f"Expected ReplayModel, got {type(model).__name__}")
        # pylint: disable=duplicate-code
        return cls(
            margin_type=model.margin_type,
            margin_val=int(model.margin_val),
            rounding=model.rounding,
            horizon=int(model.horizon),
            w_max=int(model.w_max),
            atomic_tail=int(model.atomic_tail),
            rtt=int(model.rtt),
        )
        # pylint: enable=duplicate-code

    def check(self) -> None:
        """Validate Replay-specific parameter constraints including RTT bounds
        relative to horizon.
        """
        # pylint: disable=duplicate-code
        super().check()
        if self.horizon <= 0:
            raise ValueError(f"{self.horizon=}")
        if self.w_max < 0:
            raise ValueError(f"{self.w_max=}")
        # pylint: enable=duplicate-code
        if self.atomic_tail < 0:
            raise ValueError(f"{self.atomic_tail=}")
        if self.rtt <= 0:
            raise ValueError(f"{self.rtt=}")
        if self.rtt > self.horizon:
            raise ValueError(f"{self.rtt=} {self.horizon=}")


class ReplayResults(FifoResults):
    """Results container for Replay solver with acknowledgement and inflight
    data witness.

    Provides replay-specific naming aliases (inflight instead of occupancy,
    acknowledgements instead of reads).
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        depth: int,
        infl_peak: int,
        w_seq: List[int],
        a_seq: List[int],
        infl_seq: List[int],
    ) -> None:
        super().__init__(depth, infl_peak, w_seq, a_seq, infl_seq)
        self.witness_labels = ["cycle", "w_seq", "a_seq", "infl_seq"]
        self._plot_title = "Inflight Data"

    # Properties to provide replay-specific naming
    @property
    def infl_peak(self) -> int:
        """Peak inflight data (alias for occ_peak)."""
        return self.occ_peak

    @property
    def a_seq(self) -> List[int]:
        """Acknowledgement sequence over time (alias for r_seq)."""
        return self.r_seq

    @property
    def infl_seq(self) -> List[int]:
        """Inflight data sequence over time (alias for occ_seq)."""
        return self.occ_seq

    def scalars_to_dict(self) -> dict[str, int | float | str | bool]:
        """Extract scalar attributes with replay-specific naming (infl_peak
        instead of occ_peak).
        """
        # pylint: disable=duplicate-code
        result: dict[str, int | float | str | bool] = {}
        for key, value in vars(self).items():
            if key.startswith("_"):
                continue
            if isinstance(value, (int, float, str, bool)):
                # Use replay-specific naming
                if key == "occ_peak":
                    result["infl_peak"] = value
                else:
                    result[key] = value
        return result
        # pylint: enable=duplicate-code

    @classmethod
    def make(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        solver: cp_model.CpSolver,
        peak: cp_model.IntVar,
        w: List[cp_model.IntVar],
        a: List[cp_model.IntVar],
        infl: List[cp_model.IntVar],
    ) -> "ReplayResults":
        """Create ReplayResults from CP-SAT solver solution, extracting witness
        sequences and setting initial depth.
        """
        infl_peak, w_seq, a_seq, infl_seq = extract_witness(solver, peak, w, a, infl)
        depth = infl_peak
        return cls(depth, infl_peak, w_seq, a_seq, infl_seq)


class ReplaySolver(FifoSolver):
    """Replay FIFO depth solver using constraint programming to find worst-case
    inflight data considering round-trip time constraints.

    Models transmit/acknowledgement sequences with RTT-delayed acknowledgements
    and computes required depth for replay buffer.
    """

    def __init__(self) -> None:
        super().__init__()
        self.model_class = ReplayModel
        self.params_class = ReplayParams
        self.results_class = ReplayResults

    def get_spec(self) -> None:
        """Load specification and verify it is not layered (layered profiles not
        supported for Replay).
        """
        super().get_spec()
        assert self.spec, "Must call get_spec() first"
        if "write_profile" in self.spec and "read_profile" in self.spec:
            raise ValueError("Layered specs not supported in Replay fifo.")

    def get_valids(self) -> None:
        """Not used by Replay FIFO (no valid profiles needed)."""

    def check_valids(self) -> None:
        """Not used by Replay FIFO (no valid profiles needed)."""

    def get_results(self) -> None:
        """Calculate Replay FIFO depth using constraint programming to maximize
        inflight data under RTT and horizon constraints.
        """
        # pylint: disable=too-many-locals
        # pylint: disable=duplicate-code

        assert self.params is not None, "Must call get_params() first"
        params = cast(ReplayParams, self.params)

        # Local variables for convenience
        horizon = params.horizon
        w_max = params.w_max
        rtt = params.rtt

        # --- CDC: add synchronizer delay (in write cycles) to RTT ---
        rd_sync_delay = (
            int(self.rd_sync_cycles_in_wr) if self.rd_sync_cycles_in_wr > 0 else 0
        )
        rtt_eff = rtt + rd_sync_delay

        # Param check enforces this; keep as assert to catch refactors.
        assert horizon >= rtt_eff, (
            f"internal: horizon={horizon} < rtt_eff={rtt_eff} "
            f"(rtt={rtt}, rd_sync_delay={rd_sync_delay})"
        )

        peak_analytic = min(rtt_eff, horizon - rtt_eff) * w_max
        if horizon < 2 * rtt_eff:
            logger.warning(
                "horizon (%d) < 2*rtt (%d): peak will be limited to "
                "(horizon - rtt) * w_max = %d",
                horizon,
                2 * rtt_eff,
                peak_analytic,
            )
        if horizon == rtt_eff:
            logger.info("horizon == rtt → no sends allowed by construction; peak=0.")
        logger.info(
            "Replay (BDP-equivalent): rtt=%d, rd_sync_delay=%d, rtt_eff=%d, "
            "horizon=%d, w_max=%d -> peak_analytic=%d; atomic_tail=%d, "
            "margin=(%s,%d)",
            rtt,
            rd_sync_delay,
            rtt_eff,
            horizon,
            w_max,
            peak_analytic,
            params.atomic_tail,
            params.margin_type,
            params.margin_val,
        )

        # Define the maximum possible inflight
        infl_max = peak_analytic

        # Create CP-SAT model
        cp_sat_model = cp_model.CpModel()

        # Setup variables
        w = [cp_sat_model.new_int_var(0, w_max, f"tx_{t}") for t in range(horizon)]
        a = [cp_sat_model.new_int_var(0, w_max, f"ack_{t}") for t in range(horizon)]
        infl = [
            cp_sat_model.new_int_var(0, infl_max, f"infl_{t}")
            for t in range(horizon + 1)
        ]
        peak = cp_sat_model.new_int_var(0, infl_max, "peak")

        # Add constraints

        cp_sat_model.add(infl[0] == 0)

        for t in range(horizon):
            if t >= rtt_eff:
                cp_sat_model.add(a[t] == w[t - rtt_eff])
            else:
                cp_sat_model.add(a[t] == 0)

        for t in range(horizon):
            cp_sat_model.add(infl[t + 1] == infl[t] + w[t] - a[t])

        # Forbid new sends in the last rtt_eff cycles
        # (so inflight drains to 0 by horizon)
        for t in range(max(0, horizon - rtt_eff), horizon):
            cp_sat_model.add(w[t] == 0)

        # No inflight at end
        cp_sat_model.add(infl[horizon] == 0)

        cp_sat_model.add_max_equality(peak, infl[1:])

        # Small symmetry/branching hint: push w early and high.
        cp_sat_model.add_decision_strategy(
            w,
            cp_model.CHOOSE_FIRST,
            cp_model.SELECT_MAX_VALUE,
        )

        # Create a solver
        solver = make_solver(max_time_s=15.0, workers=8)

        # Solve to maximize peak
        cp_sat_model.maximize(peak)
        status = solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = solver.StatusName(status)
            raise RuntimeError(
                f"Solve max peak failed with status={status} ({status_name})"
            )
        peak_star = int(solver.Value(peak))

        # Guardrail against regressions
        if peak_star != peak_analytic:
            logger.warning(
                "CP peak (%d) != analytic peak (%d). Investigate constraints/inputs.",
                peak_star,
                peak_analytic,
            )

        # Solve to find the earliest time of the peak
        cp_sat_model.add(peak == peak_star)
        _, t_star = self.add_earliest_peak_tiebreak(
            cp_sat_model, peak, infl, start_index=1
        )
        cp_sat_model.minimize(t_star)
        status = solver.Solve(cp_sat_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_name = solver.StatusName(status)
            raise RuntimeError(
                f"Solve earliest peak time failed with status={status} ({status_name})"
            )

        # Extract results
        self.results = ReplayResults.make(solver, peak, w, a, infl)
        self._adjust_results()

        # Store check arguments for later validation (after save)
        self.results_check_args = {"occ_max": infl_max}

        # pylint: enable=duplicate-code

    def _adjust_results(self) -> None:
        """Adjust results for CDC, margin, rounding."""
        # pylint: disable=duplicate-code
        assert self.params is not None, "Must call get_params() first"
        params = cast(ReplayParams, self.params)

        assert self.results is not None, "Must call get_results() first"
        results = cast(ReplayResults, self.results)

        # Adjust depth
        results.depth += params.atomic_tail
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
        # pylint: enable=duplicate-code
