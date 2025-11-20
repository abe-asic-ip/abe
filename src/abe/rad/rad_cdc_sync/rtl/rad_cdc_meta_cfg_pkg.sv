// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: Apache-2.0

// This file: src/abe/rad/rad_cdc_sync/rtl/rad_cdc_meta_cfg_pkg.sv

// Metastability configuration package for CDC synchronizer

`include "rad_timescale.svh"

package rad_cdc_meta_cfg_pkg;
  // Allow command-line overrides via +define+RAD_CDC_* (optional)
`ifndef RAD_CDC_T_SETUP
  `define RAD_CDC_T_SETUP 100ps
`endif
`ifndef RAD_CDC_T_HOLD
  `define RAD_CDC_T_HOLD 100ps
`endif
`ifndef RAD_CDC_RAND_SEED
  `define RAD_CDC_RAND_SEED 32'hC0FFEE01
`endif
  // Global defaults (edit here or override with +define)
  parameter realtime CDC_T_SETUP = `RAD_CDC_T_SETUP;
  parameter realtime CDC_T_HOLD = `RAD_CDC_T_HOLD;
  parameter int unsigned CDC_RAND_SEED = `RAD_CDC_RAND_SEED;
endpackage
