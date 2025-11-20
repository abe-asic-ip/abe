// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0
//
// This file: src/abe/rad/rad_async_fifo/rtl/rad_async_fifo_wptr.sv
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
// Write pointer & full generation (wclk domain)
//------------------------------------------------------------------------------
module rad_async_fifo_wptr #(
    parameter int ADDRSIZE = 3
) (
    output logic                wfull,
    output logic [ADDRSIZE-1:0] waddr,
    output logic [  ADDRSIZE:0] wptr_gray,
    input  logic [  ADDRSIZE:0] wq2_rptr,
    input  logic                winc,
    input  logic                wclk,
    input  logic                wrst_n
);

  logic [ADDRSIZE:0] wbin;
  logic [ADDRSIZE:0] wbin_next;
  logic [ADDRSIZE:0] wgray_next;
  logic              wfull_val;

  // Binary & Gray pointer update
  always_ff @(posedge wclk or negedge wrst_n) begin
    if (!wrst_n) begin
      wbin <= '0;
      wptr_gray <= '0;
    end else begin
      wbin <= wbin_next;
      wptr_gray <= wgray_next;
    end
  end

  // Address into memory uses binary pointer.
  assign waddr = wbin[ADDRSIZE-1:0];

  // Increment binary pointer only when there is a write and FIFO is not full.
  assign wbin_next = wbin + ((winc && !wfull) ? 1 : 0);
  // Binary-to-Gray conversion.
  assign wgray_next = (wbin_next >> 1) ^ wbin_next;

  // Full when next Gray write pointer equals synchronized, MSB-twiddled read
  // pointer (classic extra-MSB full detection).
  assign wfull_val = (wgray_next == {~wq2_rptr[ADDRSIZE:ADDRSIZE-1], wq2_rptr[ADDRSIZE-2:0]});

  always_ff @(posedge wclk or negedge wrst_n) begin
    if (!wrst_n) begin
      wfull <= 1'b0;
    end else begin
      wfull <= wfull_val;
    end
  end

endmodule

`default_nettype wire
