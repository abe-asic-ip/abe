// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0
//
// This file: src/abe/rad/rad_async_fifo/rtl/rad_async_fifo.sv
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
// Top-level async FIFO
//------------------------------------------------------------------------------
module rad_async_fifo #(
    parameter int DSIZE = 8,  // data width
    parameter int ASIZE = 3   // address bits → depth = 2**ASIZE
) (
    // Write side (wclk domain)
    input  logic             wclk,
    input  logic             wrst_n,
    input  logic             winc,    // write increment (when !wfull)
    input  logic [DSIZE-1:0] wdata,
    output logic             wfull,

    // Read side (rclk domain)
    input  logic             rclk,
    input  logic             rrst_n,
    input  logic             rinc,    // read increment (when !rempty)
    output logic [DSIZE-1:0] rdata,
    output logic             rempty
);

  // Binary-address portions of pointers
  logic [ASIZE-1:0] waddr, raddr;

  // Gray-coded pointers (ASIZE+1 bits — extra MSB for full/empty detection)
  logic [ASIZE:0] wptr_gray, rptr_gray;
  logic [ASIZE:0] wq2_rptr, rq2_wptr;  // synchronized versions

  // Write-domain: sync read pointer into write clock domain
  rad_async_fifo_sync #(
      .ADDRSIZE(ASIZE)
  ) u_sync_r2w (
      .q2   (wq2_rptr),
      .d    (rptr_gray),
      .clk  (wclk),
      .rst_n(wrst_n)
  );

  // Read-domain: sync write pointer into read clock domain
  rad_async_fifo_sync #(
      .ADDRSIZE(ASIZE)
  ) u_sync_w2r (
      .q2   (rq2_wptr),
      .d    (wptr_gray),
      .clk  (rclk),
      .rst_n(rrst_n)
  );

  // FIFO storage (flop-based for small depths)
  rad_async_fifo_mem #(
      .DSIZE(DSIZE),
      .ADDRSIZE(ASIZE)
  ) u_mem (
      .rdata (rdata),
      .wdata (wdata),
      .waddr (waddr),
      .raddr (raddr),
      .wclken(winc),
      .wfull (wfull),
      .wclk  (wclk)
  );

  // Read pointer + empty flag (rclk domain)
  rad_async_fifo_rptr #(
      .ADDRSIZE(ASIZE)
  ) u_rptr (
      .rempty   (rempty),
      .raddr    (raddr),
      .rptr_gray(rptr_gray),
      .rq2_wptr (rq2_wptr),
      .rinc     (rinc),
      .rclk     (rclk),
      .rrst_n   (rrst_n)
  );

  // Write pointer + full flag (wclk domain)
  rad_async_fifo_wptr #(
      .ADDRSIZE(ASIZE)
  ) u_wptr (
      .wfull    (wfull),
      .waddr    (waddr),
      .wptr_gray(wptr_gray),
      .wq2_rptr (wq2_rptr),
      .winc     (winc),
      .wclk     (wclk),
      .wrst_n   (wrst_n)
  );

endmodule

`default_nettype wire
