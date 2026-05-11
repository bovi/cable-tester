`default_nettype none
`timescale 1ns / 1ps

/* Testbench for tt_um_cable_tester.
 *
 * Includes a behavioral model of the cable + far-end shorting plug. The
 * cable model lets cocotb inject per-wire opens by writing the
 * cable_wire_good register: bit k = 1 means wire k is electrically
 * continuous from the near-end RJ45 pin to the far-end common node.
 *
 *   wire k good + any good wire being driven high  =>  uio_in[k] = 1
 *   wire k open, or no driver active              =>  uio_in[k] = 0  (PCB pulldown)
 *   wire k currently driving                       =>  uio_in[k] = uio_out[k] (self-read)
 */
module tb ();

  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  reg        clk;
  reg        rst_n;
  reg        ena;
  reg  [7:0] ui_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;
  wire [7:0] uio_in;

  // Cable fault model. Default to a fully intact cable + shorting plug.
  reg  [7:0] cable_wire_good;
  initial    cable_wire_good = 8'hFF;

  // Far-end "blob": pulls high if any intact wire is driven high.
  wire any_far_high = |(uio_oe & uio_out & cable_wire_good);

  genvar k;
  generate
    for (k = 0; k < 8; k = k + 1) begin : g_cable
      assign uio_in[k] = uio_oe[k]
                       ? uio_out[k]
                       : (cable_wire_good[k] & any_far_high);
    end
  endgenerate

`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  tt_um_cable_tester user_project (
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

endmodule
