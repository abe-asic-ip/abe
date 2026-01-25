# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_base.py

"""Base classes for fifo depth calculation modules.

This module provides base classes shared across all fifo depth
calculation protocols (CBFC, XON/XOFF, Replay, Ready/Valid).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, Self, Sequence, Type, cast

import yaml
from pydantic import BaseModel, NonNegativeInt

from abe.uarch.fifo_depth_utils import (
    compile_layered_spec,
    get_args,
)
from abe.utils import PlotLine, red, yellow

if TYPE_CHECKING:
    from ortools.sat.python import cp_model


logger = logging.getLogger(__name__)


class FifoBaseModel(BaseModel):
    """Base model providing JSON serialization and file saving capabilities for FIFO
    configurations.
    """

    margin_type: Literal["percentage", "absolute"] = "absolute"
    margin_val: NonNegativeInt = 0
    rounding: Literal["power2", "none"] = "none"

    def __str__(self) -> str:
        """Return JSON-formatted string representation of the model."""
        return f"{self.__class__.__name__}:\n" + json.dumps(self.model_dump(), indent=2)

    def save(self, outdir: Path, name: str = "") -> None:
        """Save the model to a JSON file in the specified output directory.

        Args:
            outdir: Output directory path where the JSON file will be created
            name: Optional name for the output file (defaults to class name)
        """
        name = name if name else self.__class__.__name__
        (outdir / f"{name}.json").write_text(
            json.dumps(self.model_dump(), indent=2) + "\n"
        )


class FifoModel(FifoBaseModel):
    """FIFO model with core configuration fields common across all protocols
    including horizon, margins, traffic, and latency parameters.
    """

    horizon: NonNegativeInt
    w_max: NonNegativeInt = 1
    r_max: NonNegativeInt = 1
    sum_w_min: NonNegativeInt
    sum_w_max: NonNegativeInt
    sum_r_min: NonNegativeInt
    sum_r_max: NonNegativeInt
    wr_latency: NonNegativeInt = 0
    rd_latency: NonNegativeInt = 0


class FifoBaseParams(ABC):
    """Abstract base class for FIFO parameter objects derived from validated
    models.
    """

    margin_type: Literal["percentage", "absolute"]
    margin_val: int
    rounding: Literal["power2", "none"]

    def __init__(
        self,
        *,
        margin_type: Literal["percentage", "absolute"] = "absolute",
        margin_val: int = 0,
        rounding: Literal["power2", "none"] = "none",
    ) -> None:
        self.margin_type = margin_type
        self.margin_val = margin_val
        self.rounding = rounding

    @classmethod
    @abstractmethod
    def from_model(cls, model: FifoBaseModel) -> Self:
        """Create parameter object from a validated model instance."""

    def __str__(self) -> str:
        """Return JSON-formatted string representation of the parameters."""
        return f"{self.__class__.__name__}:\n" + json.dumps(vars(self), indent=2)

    def check(self) -> None:
        """Validate all parameter constraints."""
        if self.margin_type not in ("percentage", "absolute"):
            raise ValueError(f"{self.margin_type=}")
        if self.margin_val < 0:
            raise ValueError(f"{self.margin_val=}")
        if self.rounding not in ("power2", "none"):
            raise ValueError(f"{self.rounding=}")

    def save(self, outdir: Path, name: str = "") -> None:
        """Save the parameters to a JSON file in the specified output directory.

        Args:
            outdir: Output directory path where the JSON file will be created
            name: Optional name for the output file (defaults to class name)
        """
        name = name if name else self.__class__.__name__
        (outdir / f"{name}.json").write_text(json.dumps(vars(self), indent=2) + "\n")


class FifoParams(
    FifoBaseParams
):  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """FIFO parameters with validation for traffic profiles, latencies, and margin
    configuration.
    """

    horizon: int
    w_max: int
    r_max: int
    sum_w_min: int
    sum_w_max: int
    sum_r_min: int
    sum_r_max: int
    wr_latency: int
    rd_latency: int

    def __init__(  # pylint: disable=too-many-arguments
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
    ) -> None:
        super().__init__(
            margin_type=margin_type, margin_val=margin_val, rounding=rounding
        )
        self.horizon = horizon
        self.w_max = w_max
        self.r_max = r_max
        self.sum_w_min = sum_w_min
        self.sum_w_max = sum_w_max
        self.sum_r_min = sum_r_min
        self.sum_r_max = sum_r_max
        self.wr_latency = wr_latency
        self.rd_latency = rd_latency

    def check(self) -> None:  # pylint: disable=too-many-branches
        """Validate all parameter constraints including ranges, traffic profile
        consistency, and horizon sufficiency.
        """
        super().check()
        if self.horizon <= 0:
            raise ValueError(f"{self.horizon=}")
        if self.w_max < 0:
            raise ValueError(f"{self.w_max=}")
        if self.r_max < 0:
            raise ValueError(f"{self.r_max=}")
        if not 0 <= self.sum_w_min <= self.sum_w_max:
            raise ValueError(f"{self.sum_w_min=}, {self.sum_w_max=}")
        if not 0 <= self.sum_r_min <= self.sum_r_max:
            raise ValueError(f"{self.sum_r_min=}, {self.sum_r_max=}")
        if self.sum_w_max > self.horizon * self.w_max:
            raise SystemExit(f"{self.sum_w_max=}, {self.horizon=}, {self.w_max=}")
        if self.sum_r_max > self.horizon * self.r_max:
            raise SystemExit(f"{self.sum_r_max=}, {self.horizon=}, {self.r_max=}")
        if self.wr_latency < 0:
            raise ValueError(f"{self.wr_latency=}")
        if self.rd_latency < 0:
            raise ValueError(f"{self.rd_latency=}")

        self.summarize_profiles()
        self.check_horizon_sufficiency()

    def check_horizon_sufficiency(self) -> None:
        """Warn if horizon is too short to observe maximum occupancy.

        For accurate FIFO depth calculation, the horizon must be long enough to:
        1. Write the maximum amount of data (sum_w_max / w_max cycles)
        2. Read the maximum amount of data (sum_r_max / r_max cycles)

        This ensures the solver can find write/read patterns that achieve the
        true peak occupancy while satisfying all traffic constraints.

        Note: This check is most critical for protocols without flow control
        (e.g., ready_valid) where occupancy can reach sum_w_max. Protocols with
        flow control (xon_xoff, cbfc) typically have lower occupancy limits.
        """
        # Calculate minimum horizon needed to observe max writes and max reads
        # Using sum_r_max (not sum_r_min) for a conservative check
        min_write_cycles = self.sum_w_max / self.w_max
        min_read_cycles = self.sum_r_max / self.r_max
        min_horizon = min_write_cycles + min_read_cycles

        if self.horizon < min_horizon:
            s = f"Horizon ({self.horizon}) may be too short to observe maximum "
            s += f"occupancy. Recommended minimum: {min_horizon:.0f} "
            s += f"({min_write_cycles:.0f} cycles to write sum_w_max + "
            s += f"{min_read_cycles:.0f} cycles to read sum_r_max)"
            logger.warning(yellow(s))
            raise Warning(s)

    def is_balanced(self, eps: float = 1e-6) -> bool:
        """Return True if minimum read density meets or exceeds maximum write
        density (balanced traffic).
        """
        max_write_density = self.sum_w_max / self.horizon
        min_read_density = self.sum_r_min / self.horizon
        return (min_read_density + eps) >= max_write_density

    def summarize_profiles(self) -> None:
        """Log write/read traffic profile summary including densities and horizon
        coverage.
        """
        max_write_density = self.sum_w_max / self.horizon * 100
        min_read_density = self.sum_r_min / self.horizon * 100
        s = "Profile Summary:\n"
        s += f"  Horizon:                     {self.horizon}\n"
        s += f"  Max write data (sum_w_max):  {self.sum_w_max}\n"
        s += f"  Min read data (sum_r_min):   {self.sum_r_min}\n"
        s += f"  Max write density:           {max_write_density:.1f}%\n"
        s += f"  Min read density:            {min_read_density:.1f}%"
        logger.info(s)


class FifoBaseResults:
    """Container for FIFO depth calculation results with validation status
    tracking.
    """

    def __init__(
        self,
        *,
        basic_checks_pass: bool = False,
        msg: str = "",
    ) -> None:
        self.basic_checks_pass = basic_checks_pass
        self.msg = msg

    def __str__(self) -> str:
        """Return JSON-formatted string representation of all results."""
        return json.dumps(vars(self), indent=2)

    def scalars_to_dict(self) -> dict[str, int | float | str | bool]:
        """Extract scalar attributes (int, str, bool) to dictionary, excluding
        private and sequence attributes.
        """
        result: dict[str, int | float | str | bool] = {}
        for key, value in vars(self).items():
            if key.startswith("_"):
                continue
            if isinstance(value, (int, float, str, bool)):
                result[key] = value
        return result

    def scalars_to_str(self) -> str:
        """Return JSON-formatted string of scalar results only."""
        return json.dumps(self.scalars_to_dict(), indent=2)

    def save_scalars(self, outdir: Path, name: str) -> None:
        """Save scalar results to a JSON file."""
        (outdir / f"{name}_scalars.json").write_text(
            json.dumps(self.scalars_to_dict(), indent=2) + "\n"
        )

    def save(self, outdir: Path, name: str) -> None:
        """Save all results data to the output directory."""
        self.save_scalars(outdir, name)


class FifoResults(
    FifoBaseResults
):  # pylint: disable=too-few-public-methods, too-many-instance-attributes
    """Results container storing FIFO depth, peak occupancy, and time-series
    witness for write/read/occupancy.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        depth: int,
        occ_peak: int,
        w_seq: List[int],
        r_seq: List[int],
        occ_seq: List[int],
    ) -> None:
        super().__init__()
        self.depth = depth
        self.occ_peak = occ_peak
        self.w_seq = w_seq
        self.r_seq = r_seq
        self.occ_seq = occ_seq
        self.witness_to_save = [w_seq, r_seq, occ_seq]
        self.witness_labels = ["cycle", "w_seq", "r_seq", "occ_seq"]
        self._plot_title = "Fifo Occupancy"

    def check(self, occ_max: int) -> None:
        """Validate that peak occupancy matches sequence maximum and does not
        exceed specified limit.
        """
        self.basic_checks_pass = True

        if max(self.occ_seq[1:]) > occ_max:
            self.basic_checks_pass = False
            logger.error(red("Internal error: max occ_seq > occ_max"))

        if self.occ_peak != max(self.occ_seq[1:]):
            self.basic_checks_pass = False
            logger.error(red("Internal error: occ_seq max != occ_peak"))

    def save_witness(self, outdir: Path, name: str) -> None:
        """Save time-series witness (write, read, occupancy) to a CSV file."""
        with (outdir / f"{name}_witness.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            wr = csv.writer(f)
            wr.writerow(self.witness_labels)
            for t in range(len(self.occ_seq) - 1):
                row: list[int | str] = [t]
                for seq in self.witness_to_save:
                    val: int | str = seq[t] if t < len(seq) else ""
                    row.append(val)
                wr.writerow(row)

    def save_plot(self, outdir: Path, name: str) -> None:
        """Generate and save a line plot of FIFO occupancy over time."""
        xs = list(range(len(self.occ_seq)))
        p = PlotLine(outdir)
        p.add_line(xs, self.occ_seq, label=self._plot_title, color="blue")
        p.set_labels("Cycle", self._plot_title, self._plot_title)
        p.format()
        p.save(f"{name}_plot")

    def save(self, outdir: Path, name: str) -> None:
        """Save all results including scalars, witness, and plot to the output
        directory.
        """
        super().save(outdir, name)
        self.save_witness(outdir, name)
        self.save_plot(outdir, name)


class FifoSolver(  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    ABC
):
    """Abstract base class orchestrating the FIFO depth calculation workflow from
    spec loading through result validation.

    Subclasses should set unique_keys to specify required spec keys.
    Subclasses must set model_class to their specific Model class.
    """

    model_class: Type[FifoBaseModel]
    params_class: Type[FifoBaseParams]
    results_class: Type[FifoBaseResults]

    def __init__(self) -> None:
        self.args: argparse.Namespace | None = None
        self.outdir: Path | None = None
        self.cdc_ctx: Dict[str, int] = {}
        self.spec: dict = {}
        self.unique_keys: List[str] = []
        self.flat_spec: Dict[str, int | str] = {}
        self.overall_period: int = 0
        self.write_valid: List[int] = []
        self.read_valid: List[int] = []
        self.model: FifoBaseModel | None = None
        self.params: FifoBaseParams | None = None
        self.results: FifoBaseResults | None = None
        self.results_check_args: dict = {}  # Store arguments for results.check()
        self.results_name: str | None = None

    @property
    def rd_sync_cycles_in_wr(self) -> int:
        """Read-domain synchronizer cycles to be added to effective rd_latency."""
        return int(self.cdc_ctx.get("rd_sync_cycles_in_wr", 0))

    @property
    def base_sync_fifo_depth(self) -> int:
        """Long-term rate/ppm budget to be absorbed by the big synchronous FIFO."""
        return int(self.cdc_ctx.get("base_sync_fifo_depth", 0))

    def run(self, argv: Sequence[str] | None = None) -> None:
        """Execute the complete FIFO depth calculation workflow from CLI parsing
        through result validation and saving.
        """
        self.get_cli(argv)
        self.get_spec()
        self.get_unique_keys()
        self.get_flat_spec()
        self.get_model()
        self.log_model()
        self.check_model()
        self.get_params()
        self.log_params()
        self.check_params()
        self.get_valids()
        self.check_valids()
        self.get_results()
        self.check_results()
        self.log_results()
        self.save_results()
        self.handle_results()

    def get_cli(self, argv: Sequence[str] | None = None) -> None:
        """Parse command line arguments and initialize output directory path."""
        self.args = get_args(argv)
        self.outdir = Path(self.args.outdir)

    def get_spec(self) -> None:
        """Load YAML specification file from the path provided in CLI arguments."""
        assert self.args is not None, "Must call get_cli() first"
        with open(self.args.spec, encoding="utf-8") as f:
            self.spec = yaml.safe_load(f)
        self._get_cdc_ctx()

    def get_unique_keys(self) -> None:
        """Extract protocol-specific configuration keys from the spec (implemented
        by subclasses).
        """

    def get_flat_spec(self) -> None:
        """Flatten layered traffic profiles into a single spec dictionary, or use
        spec as-is if not layered.
        """
        assert self.spec, "Must call get_spec() first"
        if self._is_layered_spec():
            result = compile_layered_spec(self.spec)
            self.flat_spec, self.overall_period, self.write_valid, self.read_valid = (
                result
            )
            self.flat_spec.update({k: self.spec[k] for k in self.unique_keys})
        else:
            self.flat_spec = self.spec
            self.overall_period = int(self.spec.get("horizon", 0))

    def get_model(self) -> None:
        """Validate the flattened specification against the Pydantic model schema."""
        assert self.flat_spec, "Must call get_flat_spec() first"
        self.model = self.model_class.model_validate(self.flat_spec)

    def log_model(self) -> None:
        """Log the validated model to the logger."""
        assert self.flat_spec, "Must call get_flat_spec() first"
        logger.info(self.model)

    def check_model(self) -> None:
        """Perform additional model validation beyond schema checks (overridden by
        subclasses as needed).
        """
        assert self.model is not None, "Must call get_model() first"
        # Subclasses may implement additional checks here

    def get_params(self) -> None:
        """Convert validated model into parameter object for solver use."""
        assert self.model is not None, "Must call get_model() first"
        self.params = self.params_class.from_model(self.model)

    def log_params(self) -> None:
        """Log parameter summary to the logger."""
        assert self.params is not None, "Must call get_params() first"
        logger.info(self.params)

    def check_params(self) -> None:
        """Validate parameter constraints and log profile summaries."""
        assert self.params is not None, "Must call get_params() first"
        self.params.check()

    def get_valids(self) -> None:
        """Get valid profiles for layered specs (not used by CDC)."""
        assert self.params is not None, "Must call get_params() first"
        if not hasattr(self.params, "horizon"):
            return  # CDC doesn't use this
        horizon = getattr(self.params, "horizon")
        self.write_valid = self.write_valid or [1] * horizon
        self.read_valid = self.read_valid or [1] * horizon

    def check_valids(self) -> None:
        """Validate that valid profiles match horizon length and contain only
        binary values.
        """
        assert self.params is not None, "Must call get_params() first"
        params = cast(FifoParams, self.params)
        horizon = params.horizon
        if len(self.write_valid) != horizon:
            raise ValueError(f"{len(self.write_valid)=} {horizon=}")
        if len(self.read_valid) != horizon:
            raise ValueError(f"{len(self.read_valid)=} {horizon=}")
        if any(b not in (0, 1) for b in self.write_valid):
            raise ValueError("write_valid profile must be 0/1 per step")
        if any(b not in (0, 1) for b in self.read_valid):
            raise ValueError("read_valid profile must be 0/1 per step")

    def get_results(self) -> None:
        """Compute FIFO depth and occupancy witness (must be implemented by
        subclasses).
        """
        raise NotImplementedError("Subclasses must implement solve()")

    def log_results(self) -> None:
        """Log scalar results summary to the logger."""
        assert self.results is not None, "Must call get_results() first"
        logger.info("%s:\n%s", self._get_results_name(), self.results.scalars_to_str())

    def check_results(self) -> None:
        """Validate computed results against expected constraints using
        protocol-specific check arguments.
        """
        assert self.results is not None, "Must call get_results() first"
        check_method = getattr(self.results, "check", None)
        if callable(check_method):
            check_method(**self.results_check_args)  # pylint: disable=not-callable

    def save_results(self) -> None:
        """Write all results data to files in the output directory."""
        assert self.results is not None, "Must call solve() first"
        assert self.outdir is not None, "Must call get_cli() first"
        self.results.save(self.outdir, self._get_results_name())

    def handle_results(self) -> None:
        """Raise ValueError if result validation checks did not pass."""
        assert self.results is not None, "Must call get_results() first"
        if not self.results.basic_checks_pass:
            raise ValueError("Result validation failed")

    def add_earliest_peak_tiebreak(
        self,
        model: "cp_model.CpModel",
        peak: "cp_model.IntVar",
        occ_vars: List["cp_model.IntVar"],
        start_index: int = 1,
    ) -> tuple[List["cp_model.IntVar"], "cp_model.IntVar"]:
        """
        Add a one-hot selector y[t] so that exactly one index where occ[t] == peak is
        chosen, and return (y, t_star) where t_star == sum(t * y[t]) can be minimized.

        IMPORTANT: This does not set the objective. It only adds constraints:
          - sum(y) == 1
          - y[t] => occ[t] == peak
          - t_star == sum(t * y[t])

        Args:
            model: The CP-SAT model
            peak: The peak occupancy variable
            occ_vars: List of occupancy variables
            start_index: Index to start from (1 to exclude t=0, 0 to include)

        Returns:
            Tuple of (y, t_star) where y is the one-hot selector and t_star is the time
        """
        horizon_plus_1 = len(occ_vars)
        idx_range = range(start_index, horizon_plus_1)

        y = [model.new_bool_var(f"y_{t}") for t in idx_range]

        # Exactly one chosen
        model.add(sum(y) == 1)

        # If y[t] is chosen, that time's occupancy must equal peak
        for b, t in zip(y, idx_range):
            model.add(occ_vars[t] == peak).only_enforce_if(b)

        # Encode t_star as a small IntVar (0..horizon)
        t_star = model.new_int_var(start_index, horizon_plus_1 - 1, "t_star")
        model.add(t_star == sum(t * y_i for t, y_i in zip(idx_range, y)))

        return y, t_star

    def get_one_unique_key(self, k: str, required: bool) -> None:
        """Add a protocol-specific key to the unique keys list if present in spec,
        or raise error if required but missing.
        """
        if k in self.unique_keys:
            return
        if k in self.spec:
            self.unique_keys.append(k)
        elif required:
            raise ValueError(f"Missing required key: {k}")

    def _get_cdc_ctx(self) -> None:
        """If cdc_results_scalars.json exists in outdir, cache key values."""
        self.cdc_ctx = {}
        try:
            p = (self.outdir or Path(".")) / "cdc_results_scalars.json"
            if not p.exists():
                return
            s = p.read_text()
            data = json.loads(s)
            logger.info("Loaded CDC context from %s:\n%s", p, s)
            # Normalize/defend: ints with defaults
            self.cdc_ctx["base_sync_fifo_depth"] = int(
                data.get("base_sync_fifo_depth", 0)
            )
            self.cdc_ctx["rd_sync_cycles_in_wr"] = int(
                data.get("rd_sync_cycles_in_wr", 0)
            )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            # Corrupt/partial file? Fall back to empty (no CDC effect)
            self.cdc_ctx = {}

    def _get_results_name(self) -> str:
        """Return a name for the results based on protocol and spec details."""
        if self.results_name is not None:
            return self.results_name
        assert self.args is not None, "Must call get_cli() first"
        if self.args.results_name:
            return str(self.args.results_name)
        return self.results.__class__.__name__

    def _is_layered_spec(self) -> bool:
        """Return True if spec uses layered traffic profiles with write_profile and
        read_profile sections.
        """
        return "write_profile" in self.spec and "read_profile" in self.spec
