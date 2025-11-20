// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/shared/rtl/rad_pulse_gen.sv

// Based on "Clock Domain Crossing (CDC) Design & Verification Techniques
// Using SystemVerilog" by Clifford E. Cummings, 2008"

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// plsgen: toggle-based pulse generator
//------------------------------------------------------------------------------
//
// d is a synchronous toggle input; q is the registered version.
// pulse is a 1-cycle pulse whenever d and q differ.
//
module rad_pulse_gen (
    output logic pulse,
    output logic q,
    input  logic d,
    input  logic clk,
    input  logic rst_n
);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      q <= 1'b0;
    end else begin
      q <= d;
    end
  end

  assign pulse = q ^ d;

endmodule

`default_nettype wire
