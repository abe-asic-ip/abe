// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_mcp/rtl/rad_cdc_mcp_back_fsm.sv

// Multi-bit CDC Multi-Cycle Path (MCP) block
// Based on "Clock Domain Crossing (CDC) Design & Verification Techniques
// Using SystemVerilog" by Clifford E. Cummings, 2008"

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// rad_cdc_mcp_back_fsm: destination-side valid/ready FSM (bclk domain)
//------------------------------------------------------------------------------
//
// bvalid = 1 => bdata holds a valid word that can be loaded when bload is 1.
// Internally waits for b_en (pulse from plsgen) before declaring new data VALID.
//
module rad_cdc_mcp_back_fsm (
    output logic bvalid,  // data is valid / ready to load
    input  logic bload,   // load request from receiving logic
    input  logic b_en,    // enable pulse from synchronized control
    input  logic bclk,
    input  logic brst_n
);

  typedef enum logic [0:0] {
    READY = 1'b1,  // data valid & waiting for bload
    WAIT  = 1'b0   // waiting for next b_en pulse
  } state_e;

  state_e state, next_state;

  always_ff @(posedge bclk or negedge brst_n) begin
    if (!brst_n) begin
      state <= WAIT;
    end else begin
      state <= next_state;
    end
  end

  always_comb begin
    next_state = state;
    unique case (state)
      // Data is valid; when bload asserted, consume and wait for next enable
      READY: if (bload) next_state = WAIT;

      // Waiting for new enable pulse from synchronized control
      WAIT: if (b_en) next_state = READY;

      default: next_state = WAIT;
    endcase
  end

  assign bvalid = (state == READY);

endmodule

`default_nettype wire
