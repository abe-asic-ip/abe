// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_mcp/rtl/rad_cdc_mcp_bmcp_recv.sv

// Multi-bit CDC multi-cycle pulse (MCP) block
// Based on "Clock Domain Crossing (CDC) Design & Verification Techniques
// Using SystemVerilog" by Clifford E. Cummings, 2008"

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// rad_cdc_mcp_bmcp_recv: destination-side MCP receive logic (bclk domain)
//------------------------------------------------------------------------------
//
// - adata is the multi-bit bus sampled in the aclk domain and held stable.
// - bq2_en is the synchronized control toggle from aclk => bclk (via sync2).
// - b_en is a 1-cycle pulse whenever bq2_en toggles.
// - When bvalid && bload, capture adata into bdata and toggle b_ack.
//
module rad_cdc_mcp_bmcp_recv #(
    parameter int unsigned WIDTH = 8
) (
    output logic [WIDTH-1:0] bdata,
    output logic             bvalid,  // bdata valid
    output logic             b_ack,   // acknowledge toggle back to aclk domain

    input logic [WIDTH-1:0] adata,   // unsynchronized data bus from aclk domain
    input logic             bload,   // load request from receiving logic
    input logic             bq2_en,  // synchronized control toggle (from a_en)
    input logic             bclk,
    input logic             brst_n
);

  logic b_en;  // 1-cycle pulse generated from bq2_en toggle
  logic load_data;  // internal load qualifier

  // Generate a 1-cycle pulse on any toggle of bq2_en
  rad_pulse_gen u_plsgen (
      .pulse(b_en),
      // verilator lint_off PINCONNECTEMPTY
      .q    (),        // not needed here
      // verilator lint_on PINCONNECTEMPTY
      .d    (bq2_en),
      .clk  (bclk),
      .rst_n(brst_n)
  );

  // Data ready / acknowledge FSM
  rad_cdc_mcp_back_fsm u_back_fsm (
      .bvalid(bvalid),
      .bload (bload),
      .b_en  (b_en),
      .bclk  (bclk),
      .brst_n(brst_n)
  );

  assign load_data = bvalid && bload;

  // Toggle acknowledge when data is consumed
  always_ff @(posedge bclk or negedge brst_n) begin
    if (!brst_n) begin
      b_ack <= 1'b0;
    end else if (load_data) begin
      b_ack <= ~b_ack;
    end
  end

  // Capture data when load_data asserted; adata must be held stable in aclk
  always_ff @(posedge bclk or negedge brst_n) begin
    if (!brst_n) begin
      bdata <= '0;
    end else if (load_data) begin
      bdata <= adata;
    end
  end

endmodule

`default_nettype wire
