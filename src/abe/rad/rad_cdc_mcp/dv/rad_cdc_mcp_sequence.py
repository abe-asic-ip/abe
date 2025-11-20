# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_cdc_mcp/dv/rad_cdc_mcp_sequence.py


"""a-domain sequence for rad_cdc_mcp verification."""

from __future__ import annotations

import random

from abe.rad.shared.dv import BaseSequence, utils_cli, utils_dv

from .rad_cdc_mcp_item import RadCdcMcpReadItem, RadCdcMcpWriteItem

# ---------------------------------------------------------------------
# a-domain sequence
# ---------------------------------------------------------------------


class RadCdcMcpWriteSequence(BaseSequence[RadCdcMcpWriteItem]):
    """Generate random send transactions for the a-domain.

    Randomly asserts asend with configurable probability and generates
    random adatain within the configured data width.
    """

    def __init__(self, name: str = "rad_cdc_mcp_write_seq", seq_len: int = 100) -> None:
        super().__init__(name, seq_len)
        self._me = self.__class__.__name__
        self.seq_len = utils_cli.get_int_setting(
            "RAD_CDC_MCP_WRITE_SEQ_LEN", self.seq_len
        )
        self.dsize: int = 8
        self.send_prob: float = 0.7  # Probability of send when ready

    async def body_pre(self) -> None:
        """Get configuration from uvm_config_db."""
        # pylint: disable=duplicate-code
        self.logger.debug("%s body_pre begin", self._me)
        await super().body_pre()
        v = utils_dv.uvm_config_db_get_try(self.sequencer, "dsize")
        if isinstance(v, int):
            self.dsize = v
        if self.dsize <= 0:
            raise ValueError("dsize must be > 0")
        self.logger.debug("%s body_pre end", self._me)
        # pylint: enable=duplicate-code

    async def set_item_inputs(self, item: RadCdcMcpWriteItem, index: int) -> None:
        item.asend = 1 if random.random() < self.send_prob else 0
        if item.asend:
            # Generate random data within data width
            item.adatain = random.randint(0, (1 << self.dsize) - 1)
        else:
            item.adatain = 0


# ---------------------------------------------------------------------
# b-domain sequence
# ---------------------------------------------------------------------


class RadCdcMcpReadSequence(BaseSequence[RadCdcMcpReadItem]):
    """Generate random load transactions for the b-domain.

    Randomly asserts bload with configurable probability.
    """

    def __init__(self, name: str = "rad_cdc_mcp_read_seq", seq_len: int = 100) -> None:
        super().__init__(name, seq_len)
        self._me = self.__class__.__name__
        self.seq_len = utils_cli.get_int_setting(
            "RAD_CDC_MCP_READ_SEQ_LEN", self.seq_len
        )
        self.load_prob: float = 0.7  # Probability of load when valid

    async def set_item_inputs(self, item: RadCdcMcpReadItem, index: int) -> None:
        item.bload = 1 if random.random() < self.load_prob else 0
