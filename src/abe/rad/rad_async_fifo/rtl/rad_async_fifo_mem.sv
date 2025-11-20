// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0
//
// This file: src/abe/rad/rad_async_fifo/rtl/rad_async_fifo_mem.sv
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
// Dual-port memory (write-clocked, flop-based for small depths)
//------------------------------------------------------------------------------
module rad_async_fifo_mem #(
    parameter int DSIZE    = 8,
    parameter int ADDRSIZE = 3
) (
    output logic [   DSIZE-1:0] rdata,
    input  logic [   DSIZE-1:0] wdata,
    input  logic [ADDRSIZE-1:0] waddr,
    input  logic [ADDRSIZE-1:0] raddr,
    input  logic                wclken,
    input  logic                wfull,
    input  logic                wclk
);

  localparam int DEPTH = 1 << ADDRSIZE;

  // For small DEPTH, this will infer flops in most flows.
  logic [DSIZE-1:0] mem[DEPTH];

  // Simple combinational read in rclk domain.
  // rdata is captured by read-domain logic using rclk.
  assign rdata = mem[raddr];

  // Synchronous write in wclk domain; block writes when full.
  always_ff @(posedge wclk) begin
    if (wclken && !wfull) begin
      mem[waddr] <= wdata;
    end
  end

endmodule

`default_nettype wire
