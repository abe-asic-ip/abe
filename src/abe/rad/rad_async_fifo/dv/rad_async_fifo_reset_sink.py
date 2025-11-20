# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/rad_async_fifo/dv/rad_async_fifo_reset_sink.py

"""Reset sink that routes to specific reset method on reference model."""

from __future__ import annotations

import pyuvm

from abe.rad.shared.dv import BaseResetItem, BaseResetSink


class RadAsyncFifoResetSink(BaseResetSink[BaseResetItem]):
    """Routes reset events to domain-specific methods on the reference model.

    For dual-reset async FIFOs, this allows separate handling of write-domain
    (wrst_change) and read-domain (rrst_change) reset events while reusing the
    base reset monitoring infrastructure.
    """

    def __init__(
        self,
        name: str,
        parent: pyuvm.uvm_component | None,
        reset_method_name: str = "reset_change",
    ) -> None:
        super().__init__(name, parent)
        self.reset_method_name = reset_method_name

    def write(self, tt: BaseResetItem) -> None:
        # pylint: disable=duplicate-code
        self.logger.debug("write begin: method=%s", self.reset_method_name)
        if tt.value is None or tt.active is None:
            return

        # Forward to driver (if present)
        if self.drv is not None:
            self.drv.reset_change(tt.value, tt.active)

        # Forward to predictor's ref model using specific reset method
        if self.sb_prd is not None:
            ref_model = self.sb_prd.ref_model
            if hasattr(ref_model, self.reset_method_name):
                reset_method = getattr(ref_model, self.reset_method_name)
                reset_method(tt.value, tt.active)
            else:
                self.logger.warning(
                    "ref_model does not have method '%s'", self.reset_method_name
                )

        self.logger.debug("write end")
        # pylint: enable=duplicate-code
