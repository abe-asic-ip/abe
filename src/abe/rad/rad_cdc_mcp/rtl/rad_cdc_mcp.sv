// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_mcp/rtl/rad_cdc_mcp.sv

// Multi-bit CDC Multi-Cycle Path (MCP) block
// Based on "Clock Domain Crossing (CDC) Design & Verification Techniques
// Using SystemVerilog" by Clifford E. Cummings, 2008"

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// rad_cdc_mcp: top-level MCP CDC block (closed-loop ready/ack)
//------------------------------------------------------------------------------
//
// This is essentially the "MCP formulation with acknowledge feedback" from the
// paper, factored into a single reusable block.
//
// a-domain (source):
//   - adatain, asend, aclk, arst_n
//   - aready indicates we can launch the next word
//
// b-domain (destination):
//   - bdata, bvalid, bclk, brst_n
//   - when bvalid && bload, bdata is consumed and ack is sent back
//
module rad_cdc_mcp #(
    parameter int unsigned WIDTH = 8
) (
    // a-domain (source)
    output logic             aready,
    input  logic [WIDTH-1:0] adatain,
    input  logic             asend,
    input  logic             aclk,
    input  logic             arst_n,

    // b-domain (destination)
    output logic [WIDTH-1:0] bdata,
    output logic             bvalid,
    input  logic             bload,
    input  logic             bclk,
    input  logic             brst_n
);

  // Internal multi-bit bus & handshake toggles
  logic [WIDTH-1:0] adata;

  logic             a_en;  // toggle from a-domain to b-domain
  logic             bq2_en;  // synchronized version in b-domain

  logic             b_ack;  // toggle from b-domain to a-domain
  logic             aq2_ack;  // synchronized version in a-domain

  // Synchronize toggles between domains
  rad_cdc_sync u_async_to_b (
      .sync_o (bq2_en),
      .async_i(a_en),
      .clk    (bclk),
      .rst_n  (brst_n)
  );

  rad_cdc_sync u_async_to_a (
      .sync_o (aq2_ack),
      .async_i(b_ack),
      .clk    (aclk),
      .rst_n  (arst_n)
  );

  // Source-side logic (aclk)
  rad_cdc_mcp_amcp_send #(
      .WIDTH(WIDTH)
  ) u_amcp_send (
      .adata  (adata),
      .a_en   (a_en),
      .aready (aready),
      .adatain(adatain),
      .asend  (asend),
      .aq2_ack(aq2_ack),
      .aclk   (aclk),
      .arst_n (arst_n)
  );

  // Destination-side logic (bclk)
  rad_cdc_mcp_bmcp_recv #(
      .WIDTH(WIDTH)
  ) u_bmcp_recv (
      .bdata (bdata),
      .bvalid(bvalid),
      .b_ack (b_ack),
      .adata (adata),
      .bload (bload),
      .bq2_en(bq2_en),
      .bclk  (bclk),
      .brst_n(brst_n)
  );

endmodule

`default_nettype wire
