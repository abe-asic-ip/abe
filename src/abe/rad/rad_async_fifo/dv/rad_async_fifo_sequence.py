# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_sequence.py


"""Write-side sequence for rad_async_fifo verification."""

from __future__ import annotations

import random

from abe.rad.shared.dv import BaseSequence, utils_cli, utils_dv

from .rad_async_fifo_item import RadAsyncFifoReadItem, RadAsyncFifoWriteItem

# ---------------------------------------------------------------------
# Write-side sequence
# ---------------------------------------------------------------------


class RadAsyncFifoWriteSequence(BaseSequence[RadAsyncFifoWriteItem]):
    """Generate random write transactions for the write domain.

    Randomly asserts winc with configurable probability and generates
    random wdata within the configured data width.
    """

    def __init__(
        self, name: str = "rad_async_fifo_write_seq", seq_len: int = 100
    ) -> None:
        super().__init__(name, seq_len)
        self._me = self.__class__.__name__
        self.seq_len = utils_cli.get_int_setting(
            "RAD_ASYNC_FIFO_WRITE_SEQ_LEN", self.seq_len
        )
        self.dsize: int = 8
        self.write_prob: float = 0.7  # Probability of write when not full

    async def body_pre(self) -> None:
        """Get configuration from uvm_config_db."""
        self.logger.debug("%s body_pre begin", self._me)
        await super().body_pre()
        v = utils_dv.uvm_config_db_get_try(self.sequencer, "dsize")
        if isinstance(v, int):
            self.dsize = v
        if self.dsize <= 0:
            raise ValueError("dsize must be > 0")
        self.logger.debug("%s body_pre end", self._me)

    async def set_item_inputs(self, item: RadAsyncFifoWriteItem, index: int) -> None:
        item.winc = 1 if random.random() < self.write_prob else 0
        if item.winc:
            # Generate random data within data width
            item.wdata = random.randint(0, (1 << self.dsize) - 1)
        else:
            item.wdata = 0


# ---------------------------------------------------------------------
# Read-side sequence
# ---------------------------------------------------------------------


class RadAsyncFifoReadSequence(BaseSequence[RadAsyncFifoReadItem]):
    """Generate random read transactions for the read domain.

    Randomly asserts rinc with configurable probability.
    """

    def __init__(
        self, name: str = "rad_async_fifo_read_seq", seq_len: int = 100
    ) -> None:
        super().__init__(name, seq_len)
        self._me = self.__class__.__name__
        self.seq_len = utils_cli.get_int_setting(
            "RAD_ASYNC_FIFO_READ_SEQ_LEN", self.seq_len
        )
        self.read_prob: float = 0.7  # Probability of read when not empty

    async def set_item_inputs(self, item: RadAsyncFifoReadItem, index: int) -> None:
        item.rinc = 1 if random.random() < self.read_prob else 0
