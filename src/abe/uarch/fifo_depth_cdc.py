# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/uarch/fifo_depth_cdc.py

"""Clock Domain Crossing (CDC) FIFO depth calculation.

This solver computes the required depth for an asynchronous FIFO that bridges
two clock domains with potentially different frequencies and PPM tolerances.

The CDC buffering problem is decomposed into four independent components:

  - credit_loop_depth: Steady-state round-trip latency buffering required to
    sustain write-rate. Accounts for write pointer synchronization into
    the read domain, read-side reaction time, read pointer synchronization back
    to the write domain, and write-side full-flag update. This uses the approach
    described in the book "Crack the Hardware Interview - from RTL Designers'
    Perspective: Architecture and Micro-architecture."

  - phase_margin_depth: Additional depth for unknown relative phase alignment
    between the two clocks at reset or during free-running operation.

  - ppm_drift_depth: Worst-case frequency drift over the analysis window,
    considering PPM tolerances on both clocks.

  - base_sync_fifo_depth: Long-term rate mismatch accumulation over the analysis
    window when write frequency exceeds read frequency. This component is
    intentionally excluded from the CDC FIFO depth and is returned separately
    for downstream synchronous FIFO sizing.

The final CDC FIFO depth is: credit_loop + phase_margin + ppm_drift.
"""

from __future__ import annotations

import json
import logging
from math import ceil
from typing import Annotated, Any, Literal, Sequence, cast

import yaml
from pint import UnitRegistry
from pydantic import BeforeValidator, NonNegativeInt, field_validator

from abe.uarch.fifo_depth_base import (
    FifoBaseModel,
    FifoBaseParams,
    FifoBaseResults,
    FifoSolver,
)
from abe.uarch.fifo_depth_utils import (
    apply_margin,
    compile_layered_spec,
    get_int_from_nested_dict,
)
from abe.utils import round_value

logger = logging.getLogger(__name__)


def _parse_frequency(value: str | int | float) -> int:
    """Parse frequency from string with units (e.g., '1.1 GHz'), integer Hz
    value, or float Hz value.

    Returns frequency in Hz as integer.
    """
    if isinstance(value, (int, float)):
        return int(value)
    # Parse with pint and convert to Hz
    ureg: Any = UnitRegistry()
    quantity: Any = ureg.Quantity(value)
    return int(quantity.to("Hz").magnitude)


# Type alias for clock frequency fields. Accepts string with units (e.g., '1.1 GHz'),
# integer Hz, or float Hz during parsing, but validates to int Hz after conversion.
FrequencyHz = Annotated[int, BeforeValidator(_parse_frequency)]


class CdcModel(FifoBaseModel):
    """CDC FIFO configuration model for YAML specification validation.

    Attributes:
        wr_clk_freq: Write clock frequency in Hz (accepts unit strings like '1 GHz').
        rd_clk_freq: Read clock frequency in Hz (accepts unit strings like '1 GHz').
        big_fifo_domain: Which clock domain hosts the main synchronous FIFO
            ('write' or 'read'). Determines how the analysis window is interpreted.
        wr_clk_ppm: Write clock PPM tolerance for frequency drift calculation.
        rd_clk_ppm: Read clock PPM tolerance for frequency drift calculation.
        wptr_inc_cycles: Write-domain cycles to increment write pointer after write.
        wptr_sync_slip_cycles: Read-domain cycles for wptr synchronization slips.
        wptr_sync_stages: Number of synchronizer flip-flop stages for wptr CDC.
        rd_react_cycles: Read-domain cycles for read logic to react to new data.
        rptr_inc_cycles: Read-domain cycles to increment read pointer after read.
        rptr_sync_slip_cycles: Write-domain cycles for rptr synchronization slips.
        rptr_sync_stages: Number of synchronizer flip-flop stages for rptr CDC.
        wr_full_update_cycles: Write-domain cycles to update full flag after rptr sync.
        window_cycles: Analysis window in cycles ('auto' or explicit count).
    """

    wr_clk_freq: FrequencyHz
    rd_clk_freq: FrequencyHz
    big_fifo_domain: Literal["write", "read"] = "write"

    @field_validator("wr_clk_freq", "rd_clk_freq")
    @classmethod
    def _check_positive_frequency(cls, v: int) -> int:
        """Ensure clock frequencies are positive to prevent division by zero."""
        if v <= 0:
            raise ValueError(f"Clock frequency must be positive, got {v}")
        return v

    wr_clk_ppm: NonNegativeInt = 0
    rd_clk_ppm: NonNegativeInt = 0
    wptr_inc_cycles: NonNegativeInt = 0
    wptr_sync_slip_cycles: NonNegativeInt = 1
    wptr_sync_stages: NonNegativeInt = 2
    rd_react_cycles: NonNegativeInt = 1
    rptr_inc_cycles: NonNegativeInt = 1
    rptr_sync_slip_cycles: NonNegativeInt = 1
    rptr_sync_stages: NonNegativeInt = 2
    wr_full_update_cycles: NonNegativeInt = 1
    window_cycles: Literal["auto"] | NonNegativeInt = "auto"


class CdcParams(FifoBaseParams):  # pylint: disable=too-many-instance-attributes
    """Runtime parameters for CDC FIFO depth calculation.

    Created from a validated CdcModel instance. Provides computed properties
    for total CDC latencies and validation of parameter constraints.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        *,
        margin_type: Literal["percentage", "absolute"] = "absolute",
        margin_val: int = 0,
        rounding: Literal["power2", "none"] = "none",
        wr_clk_freq: int,
        rd_clk_freq: int,
        big_fifo_domain: Literal["write", "read"] = "write",
        wr_clk_ppm: int = 0,
        rd_clk_ppm: int = 0,
        wptr_inc_cycles: int = 0,
        wptr_sync_slip_cycles: int = 1,
        wptr_sync_stages: int = 2,
        rd_react_cycles: int = 1,
        rptr_inc_cycles: int = 1,
        rptr_sync_slip_cycles: int = 1,
        rptr_sync_stages: int = 2,
        wr_full_update_cycles: int = 1,
    ) -> None:
        super().__init__(
            margin_type=margin_type, margin_val=margin_val, rounding=rounding
        )
        self.wr_clk_freq = wr_clk_freq
        self.rd_clk_freq = rd_clk_freq
        self.big_fifo_domain = big_fifo_domain
        self.wr_clk_ppm = wr_clk_ppm
        self.rd_clk_ppm = rd_clk_ppm
        self.wptr_inc_cycles = wptr_inc_cycles
        self.wptr_sync_slip_cycles = wptr_sync_slip_cycles
        self.wptr_sync_stages = wptr_sync_stages
        self.rd_react_cycles = rd_react_cycles
        self.rptr_inc_cycles = rptr_inc_cycles
        self.rptr_sync_slip_cycles = rptr_sync_slip_cycles
        self.rptr_sync_stages = rptr_sync_stages
        self.wr_full_update_cycles = wr_full_update_cycles

    @classmethod
    def from_model(cls, model: FifoBaseModel) -> "CdcParams":
        """Create CdcParams from a validated CdcModel instance."""
        if not isinstance(model, CdcModel):
            raise TypeError(f"Expected CdcModel, got {type(model).__name__}")
        return cls(
            margin_type=model.margin_type,
            margin_val=model.margin_val,
            rounding=model.rounding,
            wr_clk_freq=int(model.wr_clk_freq),
            rd_clk_freq=int(model.rd_clk_freq),
            big_fifo_domain=model.big_fifo_domain,
            wr_clk_ppm=int(model.wr_clk_ppm),
            rd_clk_ppm=int(model.rd_clk_ppm),
            wptr_inc_cycles=int(model.wptr_inc_cycles),
            wptr_sync_slip_cycles=int(model.wptr_sync_slip_cycles),
            wptr_sync_stages=int(model.wptr_sync_stages),
            rd_react_cycles=int(model.rd_react_cycles),
            rptr_inc_cycles=int(model.rptr_inc_cycles),
            rptr_sync_slip_cycles=int(model.rptr_sync_slip_cycles),
            rptr_sync_stages=int(model.rptr_sync_stages),
            wr_full_update_cycles=int(model.wr_full_update_cycles),
        )

    @property
    def wptr_cdc_cycles_in_rd(self) -> int:
        """Total read-domain cycles for write pointer to become visible to reader.

        Sum of metastability settling time and synchronizer pipeline stages.
        This is the latency before the read side can "see" a new write.
        """
        return self.wptr_sync_slip_cycles + self.wptr_sync_stages

    @property
    def rptr_cdc_cycles_in_wr(self) -> int:
        """Total write-domain cycles for read pointer to become visible to writer.

        Sum of metastability settling time and synchronizer pipeline stages.
        This is the latency before the write side can "see" freed FIFO slots.
        """
        return self.rptr_sync_slip_cycles + self.rptr_sync_stages

    def check(self) -> None:
        """Validate CDC-specific parameter constraints."""
        if self.wr_clk_freq <= 0:
            raise ValueError(f"{self.wr_clk_freq=}")
        if self.rd_clk_freq <= 0:
            raise ValueError(f"{self.rd_clk_freq=}")
        if self.big_fifo_domain not in ("write", "read"):
            raise ValueError(f"{self.big_fifo_domain=}")
        if self.wptr_inc_cycles < 0:
            raise ValueError(f"{self.wptr_inc_cycles=}")
        if self.wptr_sync_slip_cycles < 0:
            raise ValueError(f"{self.wptr_sync_slip_cycles=}")
        if self.wptr_sync_stages < 0:
            raise ValueError(f"{self.wptr_sync_stages=}")
        if self.rd_react_cycles < 0:
            raise ValueError(f"{self.rd_react_cycles=}")
        if self.rptr_inc_cycles < 0:
            raise ValueError(f"{self.rptr_inc_cycles=}")
        if self.rptr_sync_slip_cycles < 0:
            raise ValueError(f"{self.rptr_sync_slip_cycles=}")
        if self.rptr_sync_stages < 0:
            raise ValueError(f"{self.rptr_sync_stages=}")
        if self.wr_full_update_cycles < 0:
            raise ValueError(f"{self.wr_full_update_cycles=}")


class CdcResults(FifoBaseResults):  # pylint: disable=too-many-instance-attributes
    """Results from CDC FIFO depth calculation.

    Attributes:
        depth: Required CDC FIFO depth (credit_loop + phase_margin + ppm_drift).
        credit_loop_depth: Depth for round-trip latency to sustain write-rate.
        phase_margin_depth: Depth for unknown clock phase alignment.
        ppm_drift_depth: Depth for worst-case frequency drift over the window.
        base_sync_fifo_depth: Long-term rate mismatch depth (for downstream FIFO).
        wptr_cdc_cycles_in_wr: Write pointer CDC latency in write-domain cycles,
            for use by downstream synchronous FIFO sizing.
    """

    depth: int
    credit_loop_depth: int
    phase_margin_depth: int
    ppm_drift_depth: int
    base_sync_fifo_depth: int
    wptr_cdc_cycles_in_wr: int

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        basic_checks_pass: bool = False,
        msg: str = "",
        depth: int,
        credit_loop_depth: int,
        phase_margin_depth: int,
        ppm_drift_depth: int,
        base_sync_fifo_depth: int,
        wptr_cdc_cycles_in_wr: int,
    ) -> None:
        super().__init__(
            basic_checks_pass=basic_checks_pass,
            msg=msg,
        )
        self.depth = depth
        self.credit_loop_depth = credit_loop_depth
        self.phase_margin_depth = phase_margin_depth
        self.ppm_drift_depth = ppm_drift_depth
        self.base_sync_fifo_depth = base_sync_fifo_depth
        self.wptr_cdc_cycles_in_wr = wptr_cdc_cycles_in_wr


class CdcSolver(FifoSolver):  # pylint: disable=too-many-instance-attributes
    """CDC FIFO depth solver.

    The CDC FIFO depth returned in `results.depth` is the portion that must live
    inside the CDC FIFO itself (credit loop + phase + ppm drift). The long-term
    mismatch term over the analysis window is returned separately as
    `base_sync_fifo_depth` (and is intended to be carried downstream into the
    subsequent synchronous FIFO sizing stages).
    """

    def __init__(self) -> None:
        super().__init__()
        self.model_class = CdcModel
        self.params_class = CdcParams
        self.results_class = CdcResults
        self.full_spec: dict = {}
        self.wr_window_cycles: int = 0
        self.wr_items_per_cycle: int = 0

    def run(self, argv: Sequence[str] | None = None) -> None:
        """Execute CDC FIFO depth calculation workflow."""
        # pylint: disable=duplicate-code
        self.get_cli(argv)
        self.get_spec()
        self.get_unique_keys()
        self.get_flat_spec()
        self.get_model()
        self.log_model()
        self.check_model()
        model = cast(CdcModel, self.model)
        self.get_params()
        self.log_params()
        self.check_params()
        self.wr_window_cycles = self._get_wr_window_cycles(model, self.full_spec)
        self.wr_items_per_cycle = self._get_wr_items_per_cycle(self.full_spec)
        self.get_results()
        self.check_results()
        self.log_results()
        self.save_results()
        self.handle_results()
        # pylint: enable=duplicate-code

    def get_spec(self) -> None:
        """Load YAML specification and extract CDC-specific configuration section."""
        assert self.args is not None, "Must call get_cli() first"
        # Get the full spec
        with open(self.args.spec, encoding="utf-8") as f:
            self.full_spec = yaml.safe_load(f)
        # Extract CDC spec from full spec
        self.spec = self._get_cdc_spec(self.full_spec)
        logger.debug("cdc_spec:\n%s", json.dumps(self.spec, indent=2))

    def get_results(self) -> None:
        """Analytic CDC: compute CDC FIFO depth + base_sync_depth."""
        assert self.params is not None, "Must call get_params() first"
        params = cast(CdcParams, self.params)

        # 1) Long-term rate mismatch (items) over the write-domain window (NO ppm here)
        #    mismatch_per_w_cycle_items = w_items * max(0, 1 - f_rd/f_wr)
        #    Only positive mismatch matters (write faster than read). When
        #    rd_clk_freq > wr_clk_freq, the reader drains faster than the writer
        #    fills, so there is no overflow risk from rate mismatch—hence zero.
        mismatch_per_w_cycle = self.wr_items_per_cycle * max(
            0.0, 1.0 - (params.rd_clk_freq / params.wr_clk_freq)
        )
        base_sync_fifo_depth = int(ceil(self.wr_window_cycles * mismatch_per_w_cycle))

        # 2) Small CDC components that stay in the CDC FIFO
        credit_loop_depth = self._get_credit_loop_depth(params, self.wr_items_per_cycle)
        phase_margin_depth = self._get_phase_margin_depth(
            params, self.wr_items_per_cycle
        )
        ppm_drift_depth = self._get_ppm_drift_depth(
            params, self.wr_window_cycles, self.wr_items_per_cycle
        )

        # 3) CDC FIFO depth excludes the long-term mismatch
        depth = credit_loop_depth + phase_margin_depth + ppm_drift_depth

        depth = apply_margin(depth, params.margin_type, params.margin_val)
        depth = round_value(depth, params.rounding)

        self.results = CdcResults(
            basic_checks_pass=True,
            msg="Analytic results.",
            depth=depth,
            credit_loop_depth=credit_loop_depth,
            phase_margin_depth=phase_margin_depth,
            ppm_drift_depth=ppm_drift_depth,
            base_sync_fifo_depth=base_sync_fifo_depth,
            wptr_cdc_cycles_in_wr=self._get_wptr_cdc_cycles_in_wr(params),
        )

    def _get_cdc_spec(self, full_spec: dict) -> dict:
        """Extract and validate CDC-specific configuration section from full
        specification.
        """
        if "cdc" not in full_spec:
            raise ValueError("Missing 'cdc' field in spec.")
        cdc_spec = full_spec["cdc"]
        if not isinstance(cdc_spec, dict):
            raise ValueError("'cdc' field must be a mapping.")
        return cdc_spec

    def _get_phase_margin_depth(
        self, cdc_params: CdcParams, wr_items_per_cycle: int
    ) -> int:
        """Calculate additional FIFO depth for clock phase uncertainty.

        Accounts for up to one read cycle of uncertainty due to unknown relative
        phase between write and read clocks at reset or during free-running
        operation.
        """
        rd_cycles = 1
        rd_cycles_in_w = int(
            ceil(rd_cycles * cdc_params.wr_clk_freq / cdc_params.rd_clk_freq)
        )
        return rd_cycles_in_w * wr_items_per_cycle

    def _get_ppm_drift_depth(
        self, cdc_params: CdcParams, wr_window_cycles: int, wr_items_per_cycle: int
    ) -> int:
        """Calculate additional FIFO depth to absorb worst-case frequency drift
        (PPM) over the analysis window.

        Computes drift in both write and read domains (converted to write cycles)
        and returns total depth needed to handle combined PPM error.
        """

        wr_ppm = abs(cdc_params.wr_clk_ppm)
        wr_drift_cycles = int(ceil(wr_ppm * wr_window_cycles / 1_000_000))
        wr_drift_depth = wr_drift_cycles * wr_items_per_cycle

        # In the read domain, the window is:
        #     rd_window_cycles = wr_window_cycles * (rd_clk_freq / wr_clk_freq)
        # The drift in read cycles is:
        #     rd_drift_cycles = rd_ppm * rd_window_cycles / 1_000_000
        # Converting to write cycles:
        #     rd_drift_cycles_in_w = rd_drift_cycles * (wr_clk_freq / rd_clk_freq)
        # Combining the above equations simplifies to
        #     rd_drift_cycles_in_w = rd_ppm * wr_window_cycles / 1_000_000
        # Apply ceil() after all substitutions and conversions.

        rd_ppm = abs(cdc_params.rd_clk_ppm)
        rd_drift_cycles_in_w = int(ceil(rd_ppm * wr_window_cycles / 1_000_000))
        rd_drift_depth_in_w = rd_drift_cycles_in_w * wr_items_per_cycle

        return wr_drift_depth + rd_drift_depth_in_w

    def _get_wptr_cdc_cycles_in_wr(self, cdc_params: CdcParams) -> int:
        """Convert write pointer CDC latency from read cycles to write cycles.

        The write pointer takes wptr_cdc_cycles_in_rd read-domain cycles to
        cross the CDC boundary. This method converts that latency to an
        equivalent number of write-domain cycles using the clock frequency
        ratio, rounded up to ensure conservative sizing.

        Used by downstream synchronous FIFO solvers that need the CDC latency
        expressed in write-domain units for their rd_latency adjustments.
        """
        return int(
            ceil(
                cdc_params.wptr_cdc_cycles_in_rd
                * cdc_params.wr_clk_freq
                / cdc_params.rd_clk_freq
            )
        )

    def _get_credit_loop_depth(
        self, cdc_params: CdcParams, wr_items_per_cycle: int
    ) -> int:
        """Compute credit-loop depth for steady-state write-rate.

        This uses the approach described in the book "Crack the Hardware
        Interview - from RTL Designers' Perspective: Architecture and
        Micro-architecture."

        The credit loop represents the round-trip time for a write to be
        acknowledged back to the producer:
          1. wptr_inc_cycles: Update write pointer after write
          2. wptr crosses to read domain (wptr_cdc_cycles_in_rd)
          3. rd_react_cycles: Reader reacts and starts reading
          4. rptr_inc_cycles: Update read pointer after read
          5. rptr crosses to write domain (rptr_cdc_cycles_in_wr)
          6. wr_full_update_cycles: Update full flag

        The FIFO must hold (write_rate * RTT) items to sustain write-rate.
        """
        wr_clk_cycles = (
            cdc_params.wptr_inc_cycles
            + cdc_params.rptr_cdc_cycles_in_wr
            + cdc_params.wr_full_update_cycles
        )
        rd_clk_cycles = (
            cdc_params.wptr_cdc_cycles_in_rd
            + cdc_params.rd_react_cycles
            + cdc_params.rptr_inc_cycles
        )
        # Convert cycles to time (seconds)
        rtt = (wr_clk_cycles / cdc_params.wr_clk_freq) + (
            rd_clk_cycles / cdc_params.rd_clk_freq
        )
        # Producer write rate (items / second)
        write_rate = wr_items_per_cycle * cdc_params.wr_clk_freq
        return int(ceil(write_rate * rtt))

    def _get_wr_items_per_cycle(self, full_spec: dict) -> int:
        """Extract maximum write items per cycle from specification.

        Retrieves from layered write_profile or direct w_max field.
        """

        if not ("write_profile" in full_spec and "read_profile" in full_spec):
            if "w_max" not in full_spec:
                return 1
            if not isinstance(full_spec["w_max"], int):
                raise ValueError(f"{full_spec['w_max']=}")
            return full_spec["w_max"]

        wp = full_spec["write_profile"]
        w_max = get_int_from_nested_dict(
            wp, "cycle.max_items_per_cycle", lb=1, default=1
        )
        return w_max

    def _get_wr_window_cycles(self, cdc_model: CdcModel, full_spec: dict) -> int:
        """Determine write-domain window size in cycles from specification.

        Extracts horizon from layered profiles or direct specification, converting
        to write-domain cycles if big_fifo_domain is 'read'.
        """

        if cdc_model.window_cycles == "auto":
            if "write_profile" in full_spec and "read_profile" in full_spec:
                compiled_spec = compile_layered_spec(full_spec)
                flat_spec, _overall_period, _write_valid, _read_valid = compiled_spec
                window_cycles = flat_spec["horizon"]
            elif "horizon" not in full_spec:
                raise ValueError("Missing 'horizon' field in spec.")
            else:
                window_cycles = full_spec["horizon"]
        else:
            window_cycles = cdc_model.window_cycles

        if not isinstance(window_cycles, int) or window_cycles <= 0:
            raise ValueError(f"{window_cycles=}")

        if cdc_model.big_fifo_domain == "read":
            return int(
                ceil(window_cycles * cdc_model.wr_clk_freq / cdc_model.rd_clk_freq)
            )

        return window_cycles
