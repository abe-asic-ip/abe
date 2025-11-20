// SPDX-FileCopyrightText: 2025 Hugh Walsh
//
// SPDX-License-Identifier: MIT

// This file: src/abe/rad/rad_cdc_mcp/formal/rad_cdc_mcp_formal_top.sv

module rad_cdc_mcp_formal_top;
  // Parameter for data width
  parameter int WIDTH = 8;
  typedef logic [WIDTH-1:0] data_t;

  //==========================================================================
  // Clock generation - two independent free-running clocks
  //==========================================================================

  (* gclk *)reg aclk = 1'b0;
  (* gclk *)reg bclk = 1'b0;

  always @($global_clock) aclk <= !aclk;
  always @($global_clock) bclk <= !bclk;

  //==========================================================================
  // Reset generation for both domains
  //==========================================================================

  reg [1:0] aboot = 2'b00;
  reg       arst_n = 1'b0;
  always @(posedge aclk) begin
    if (aboot != 2'b11) aboot <= aboot + 2'b01;
    arst_n <= (aboot == 2'b11);
  end

  reg [1:0] bboot = 2'b00;
  reg       brst_n = 1'b0;
  always @(posedge bclk) begin
    if (bboot != 2'b11) bboot <= bboot + 2'b01;
    brst_n <= (bboot == 2'b11);
  end

  //==========================================================================
  // DUT inputs - unconstrained
  //==========================================================================

  (* anyseq *)logic [WIDTH-1:0] adatain;
  (* anyseq *)logic             asend;
  (* anyseq *)logic             bload;

  //==========================================================================
  // DUT outputs
  //==========================================================================

  logic             aready;
  logic [WIDTH-1:0] bdata;
  logic             bvalid;

  //==========================================================================
  // DUT instantiation
  //==========================================================================

  rad_cdc_mcp #(
      .WIDTH(WIDTH)
  ) dut (
      .aready (aready),
      .adatain(adatain),
      .asend  (asend),
      .aclk   (aclk),
      .arst_n (arst_n),
      .bdata  (bdata),
      .bvalid (bvalid),
      .bload  (bload),
      .bclk   (bclk),
      .brst_n (brst_n)
  );

  //==========================================================================
  // Safe $past gating for both clock domains
  //==========================================================================

  reg apast_valid = 1'b0;
  always @(posedge aclk) apast_valid <= 1'b1;
  always @(posedge aclk) if (!apast_valid) assume (!arst_n);

  reg bpast_valid = 1'b0;
  always @(posedge bclk) bpast_valid <= 1'b1;
  always @(posedge bclk) if (!bpast_valid) assume (!brst_n);

  //==========================================================================
  // Assertions
  //==========================================================================

  // Reset behavior: outputs should be in known state when in reset
  always @(posedge aclk) begin
    if (!arst_n) begin
      assert (aready == 1'b1);  // Ready to accept data after reset
    end
  end

  always @(posedge bclk) begin
    if (!brst_n) begin
      assert (bvalid == 1'b0);  // No valid data during reset
    end
  end

  // A-domain: Protocol constraint - don't send when not ready
  always @(posedge aclk) begin
    if (arst_n && !aready) begin
      assume (!asend);  // Only send when ready
    end
  end

  // A-domain: aready should be stable (boolean value)
  always @(posedge aclk) begin
    if (arst_n) begin
      assert (aready == 1'b0 || aready == 1'b1);
    end
  end

  // B-domain: bvalid should be stable (boolean value)
  always @(posedge bclk) begin
    if (brst_n) begin
      assert (bvalid == 1'b0 || bvalid == 1'b1);
    end
  end

  // A-domain: After reset release, should be ready immediately
  always @(posedge aclk) begin
    if (apast_valid && !$past(arst_n) && arst_n) begin
      assert (aready == 1'b1);
    end
  end

  // B-domain: After reset release, should not have valid data
  always @(posedge bclk) begin
    if (bpast_valid && !$past(brst_n) && brst_n) begin
      assert (bvalid == 1'b0);
    end
  end

  // B-domain: bdata should remain stable while bvalid is asserted and not loaded
  always @(posedge bclk) begin
    if (brst_n && bpast_valid && $past(bvalid) && bvalid && !bload) begin
      assert (bdata == $past(bdata));  // Data stable until loaded
    end
  end

  // B-domain: Protocol constraint - only load when valid
  always @(posedge bclk) begin
    if (brst_n && !bvalid) begin
      assume (!bload);  // Only load when data is valid
    end
  end

  //==========================================================================
  // Cover properties
  //==========================================================================

  always @(posedge aclk) begin
    // Cover sending data when ready
    cover (arst_n && asend && aready);

    // Cover transition from ready to busy
    cover (arst_n && apast_valid && $past(aready) && !aready);
  end

  always @(posedge bclk) begin
    // Cover receiving valid data
    cover (brst_n && bvalid);

    // Cover consuming data
    cover (brst_n && bvalid && bload);

    // Cover bvalid transitions
    cover (brst_n && bpast_valid && !$past(bvalid) && bvalid);
    cover (brst_n && bpast_valid && $past(bvalid) && !bvalid);
  end

endmodule
