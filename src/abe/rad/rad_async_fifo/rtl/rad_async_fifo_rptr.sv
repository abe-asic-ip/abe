// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0
//
// This file: src/abe/rad/rad_async_fifo/rtl/rad_async_fifo_rptr.sv
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
// Read pointer & empty generation (rclk domain)
//------------------------------------------------------------------------------
module rad_async_fifo_rptr #(
    parameter int ADDRSIZE = 3
) (
    output logic                rempty,
    output logic [ADDRSIZE-1:0] raddr,
    output logic [  ADDRSIZE:0] rptr_gray,
    input  logic [  ADDRSIZE:0] rq2_wptr,
    input  logic                rinc,
    input  logic                rclk,
    input  logic                rrst_n
);

  // Binary pointer used for addressing; Gray pointer crosses clock domains.
  logic [ADDRSIZE:0] rbin;
  logic [ADDRSIZE:0] rbin_next;
  logic [ADDRSIZE:0] rgray_next;
  logic              rempty_val;

  // Binary & Gray pointer update (Gray counter "style #2")
  always_ff @(posedge rclk or negedge rrst_n) begin
    if (!rrst_n) begin
      rbin <= '0;
      rptr_gray <= '0;
    end else begin
      rbin <= rbin_next;
      rptr_gray <= rgray_next;
    end
  end

  // Address into memory uses binary pointer (safe in local clock domain).
  assign raddr = rbin[ADDRSIZE-1:0];

  // Increment binary pointer only when there is a read and FIFO is not empty.
  assign rbin_next = rbin + ((rinc && !rempty) ? 1 : 0);
  // Binary-to-Gray conversion.
  assign rgray_next = (rbin_next >> 1) ^ rbin_next;

  // Empty when *next* Gray pointer equals synchronized write pointer.
  assign rempty_val = (rgray_next == rq2_wptr);

  always_ff @(posedge rclk or negedge rrst_n) begin
    if (!rrst_n) begin
      rempty <= 1'b1;
    end else begin
      rempty <= rempty_val;
    end
  end

endmodule

`default_nettype wire
