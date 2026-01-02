// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_sync/rtl/rad_cdc_sync.sv

// Single-bit CDC synchronizer with optional metastability modeling

`include "rad_timescale.svh"
`default_nettype none

module rad_cdc_sync #(
    parameter int unsigned STAGES                   = 2,
`ifdef SIMULATE_METASTABILITY
    parameter bit          RESET                    = 1'b0,
    parameter bit          PRINT_INJECTION_MESSAGES = 1'b0
`else
    parameter bit          RESET                    = 1'b0
`endif
) (
    input  logic clk,
    input  logic rst_n,
    input  logic async_i,
    output logic sync_o
);
  // Compile-time check: STAGES must be >= 2
  localparam int RadCdcStagesOk = (STAGES >= 2) ? 1 : -1;
  typedef logic [RadCdcStagesOk-1:0] rad_cdc_stages_must_be_ge_2;

`ifdef SIMULATE_METASTABILITY

  // verilator lint_off MULTIDRIVEN
  (* ASYNC_REG = "true" *)logic        [STAGES-1:0] shreg;
  // verilator lint_on MULTIDRIVEN

  int unsigned              tmp_u;
  int unsigned              rand_seed_q = rad_cdc_meta_cfg_pkg::CDC_RAND_SEED;
  realtime                  last_async_change_tu;  // tu = time units
  realtime                  last_clk_edge_tu;
  bit                       hold_window_open;

  localparam realtime TsetupTu = real'(rad_cdc_meta_cfg_pkg::CDC_T_SETUP) / 1ns;
  localparam realtime TholdTu = real'(rad_cdc_meta_cfg_pkg::CDC_T_HOLD) / 1ns;

  initial begin
    $display("%m: SIMULATE_METASTABILITY: STAGES=%0d, RESET=%b", STAGES, RESET);
    if ($value$plusargs("RAD_CDC_RAND_SEED=%d", tmp_u)) rand_seed_q = tmp_u;
    void'($urandom(rand_seed_q));
    last_async_change_tu = 0;
    last_clk_edge_tu = 0;
    hold_window_open = 1'b0;
  end

  always @(async_i) begin
    last_async_change_tu = $realtime;
    // Check if we're in the hold window after a clock edge
    if (hold_window_open && (($realtime - last_clk_edge_tu) < TholdTu)) begin
      #0 shreg[0] <= logic'($urandom_range(0, 1));
      if (PRINT_INJECTION_MESSAGES)
        $display(
            "    %0.2fns DEBUG    %m: async_i changed during hold time after clock edge, injected metastability",
            $realtime / 1ns
        );
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      shreg <= {STAGES{RESET}};
      hold_window_open <= 1'b0;
      last_clk_edge_tu <= 0;
    end else begin
      last_clk_edge_tu <= $realtime;
      hold_window_open <= 1'b1;

      // Check for setup violation
      if (($realtime - last_async_change_tu) < TsetupTu) begin
        shreg[0] <= logic'($urandom_range(0, 1));
        if (PRINT_INJECTION_MESSAGES)
          $display(
              "    %0.2fns DEBUG    %m: async_i changed during setup time before clock edge, injected metastability",
              $realtime / 1ns
          );
      end else begin
        shreg[0] <= async_i;
      end

      for (int unsigned i = 1; i < STAGES; i++) shreg[i] <= shreg[i-1];
    end
  end

`else  // ! SIMULATE_METASTABILITY

  (* ASYNC_REG = "true" *) logic [STAGES-1:0] shreg;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) shreg <= {STAGES{RESET}};
    else begin
      shreg[0] <= async_i;
      for (int unsigned i = 1; i < STAGES; i++) shreg[i] <= shreg[i-1];
    end
  end

`endif  // SIMULATE_METASTABILITY

  assign sync_o = shreg[STAGES-1];
endmodule

`default_nettype wire

