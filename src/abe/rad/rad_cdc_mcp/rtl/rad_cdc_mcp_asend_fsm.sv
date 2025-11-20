// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_mcp/rtl/rad_cdc_mcp_asend_fsm.sv

// Multi-bit CDC Multi-Cycle Path (MCP) block
// Based on "Clock Domain Crossing (CDC) Design & Verification Techniques
// Using SystemVerilog" by Clifford E. Cummings, 2008"

`include "rad_timescale.svh"
`default_nettype none

//------------------------------------------------------------------------------
// rad_cdc_mcp_asend_fsm: source-side ready/busy FSM (aclk domain)
//------------------------------------------------------------------------------
//
// aready = 1 => source may send next word (drive adatain, assert asend).
// When asend && aready, FSM goes BUSY until aack (ack pulse) is seen.
//
module rad_cdc_mcp_asend_fsm (
    output logic aready,  // ready to send next data
    input  logic asend,   // send request (adatain valid)
    input  logic aack,    // acknowledge pulse (aclk domain)
    input  logic aclk,
    input  logic arst_n
);

  typedef enum logic [0:0] {
    READY = 1'b1,
    BUSY  = 1'b0
  } state_e;

  state_e state, next_state;

  always_ff @(posedge aclk or negedge arst_n) begin
    if (!arst_n) begin
      state <= READY;
    end else begin
      state <= next_state;
    end
  end

  always_comb begin
    next_state = state;
    unique case (state)
      READY:   if (asend) next_state = BUSY;
      BUSY:    if (aack) next_state = READY;
      default: next_state = READY;
    endcase
  end

  assign aready = (state == READY);

endmodule

`default_nettype wire
