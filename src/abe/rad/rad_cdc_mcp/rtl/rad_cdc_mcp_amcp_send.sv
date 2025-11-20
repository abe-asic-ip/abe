// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_mcp/rtl/rad_cdc_mcp_amcp_send.sv

// Multi-bit CDC multi-cycle pulse (MCP) block
// Based on "Clock Domain Crossing (CDC) Design & Verification Techniques
// Using SystemVerilog" by Clifford E. Cummings, 2008"

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// rad_cdc_mcp_amcp_send: source-side MCP send logic (aclk domain)
//------------------------------------------------------------------------------
//
// - adatain: new word in aclk domain
// - asend:   request to send adatain when aready is 1
// - a_en:    toggle sent to bclk domain via sync2 ⇒ generates enable pulse
// - aready:  indicates MCP is ready to accept next adatain/asend
//
module rad_cdc_mcp_amcp_send #(
    parameter int unsigned WIDTH = 8
) (
    output logic [WIDTH-1:0] adata,  // held stable while transfer in progress
    output logic             a_en,   // toggle control sent to bclk domain
    output logic             aready, // ready to send next data

    input logic [WIDTH-1:0] adatain,  // new data from aclk domain logic
    input logic             asend,    // send request when aready is 1
    input logic             aq2_ack,  // synchronized ack toggle from bclk domain
    input logic             aclk,
    input logic             arst_n
);

  logic aack;  // 1-cycle pulse from synchronized ack toggle
  logic send_now;  // transfer qualifier

  // Pulse generator on the ack toggle (b_ack synchronized back to aclk)
  rad_pulse_gen u_plsgen (
      .pulse(aack),
      // verilator lint_off PINCONNECTEMPTY
      .q    (),         // not used
      // verilator lint_on PINCONNECTEMPTY
      .d    (aq2_ack),
      .clk  (aclk),
      .rst_n(arst_n)
  );

  // Source-side ready/busy FSM
  rad_cdc_mcp_asend_fsm u_asend_fsm (
      .aready(aready),
      .asend (asend),
      .aack  (aack),
      .aclk  (aclk),
      .arst_n(arst_n)
  );

  assign send_now = asend && aready;

  // Toggle a_en each time we launch a new word
  always_ff @(posedge aclk or negedge arst_n) begin
    if (!arst_n) begin
      a_en <= 1'b0;
    end else if (send_now) begin
      a_en <= ~a_en;
    end
  end

  // Latch adatain when we launch the word; hold while handshake completes
  always_ff @(posedge aclk or negedge arst_n) begin
    if (!arst_n) begin
      adata <= '0;
    end else if (send_now) begin
      adata <= adatain;
    end
  end

endmodule

`default_nettype wire
