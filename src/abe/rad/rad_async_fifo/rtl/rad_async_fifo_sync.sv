// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0
//
// This file: src/abe/rad/rad_async_fifo/rtl/rad_async_fifo_sync.sv
//
// Asynchronous dual-clock FIFO with Gray-coded pointers.
// Based on:
//   - "Simulation and Synthesis Techniques for Asynchronous FIFO Design"
//     by Clifford E. Cummings, SNUG San Jose 2002, Rev 1.2 (FIFO Style #1).
//   - "Simulation and Synthesis Techniques for Asynchronous FIFO Design
//      with Asynchronous Pointer Comparisons" by Cummings & Alfke, SNUG 2002
//     (Gray counter style #2 ideas).
//
// Implementation is an original SystemVerilog re-write, not verbatim code
// from the papers.

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// Gray-pointer synchronizer wrapper for async FIFO
// Uses rad_cdc_sync for each bit of the (ADDRSIZE+1)-bit Gray pointer.
//------------------------------------------------------------------------------
module rad_async_fifo_sync #(
    parameter int          ADDRSIZE = 3,
    // Expose stages & reset polarity in case you want to tweak later.
    parameter int unsigned STAGES   = 2,
    parameter bit          RESET    = 1'b0
) (
    output logic [ADDRSIZE:0] q2,
    input  logic [ADDRSIZE:0] d,
    input  logic              clk,
    input  logic              rst_n
);

  // Each bit of the Gray pointer gets its own single-bit rad_cdc_sync
  genvar i;
  generate
    for (i = 0; i <= ADDRSIZE; i++) begin : gen_ptr_sync
      rad_cdc_sync #(
          .STAGES(STAGES),
          .RESET (RESET)
      ) u_rad_cdc_sync_bit (
          .clk    (clk),
          .rst_n  (rst_n),
          .async_i(d[i]),
          .sync_o (q2[i])
      );
    end
  endgenerate

endmodule

`default_nettype wire
