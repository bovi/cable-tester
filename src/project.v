/*
 * SPDX-FileCopyrightText: (c) 2026 Daniel Bovensiepen
 * SPDX-License-Identifier: Apache-2.0
 *
 * TinyTapeout Ethernet cable continuity tester.
 *
 * The 8 bidirectional uio pins connect, one per wire, to an RJ45 jack on the
 * test board. On the far end of the cable under test, all 8 wires are tied
 * together at a single common node (a soldered-together RJ45 plug).
 *
 * The FSM drives each wire high in turn, holds it long enough for the cable
 * RC to settle, samples all 8 wires, and ORs the non-self bits into an
 * accumulator. After eight drive steps, uo_out[k] is asserted iff wire k was
 * pulled high by at least one other intact wire's drive cycle - which proves
 * wire k is electrically continuous to the far-end common node.
 *
 *   uo_out[k] = 1  ->  wire k is good
 *   uo_out[k] = 0  ->  wire k is open (or no cable / no shorting plug)
 *
 * Limitation: if only one wire in the entire cable is intact, it has no
 * partner to confirm against, so it will also show as bad. Cables with seven
 * or more open wires are unrecoverable anyway.
 */

`default_nettype none

module tt_um_cable_tester (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

`ifdef SIM_FAST
    localparam integer SETTLE_BITS = 3;
`else
    localparam integer SETTLE_BITS = 13;
`endif

    reg [2:0]              idx;
    reg [SETTLE_BITS-1:0]  settle;
    reg [7:0]              acc;
    reg [7:0]              result;

    wire        settle_done = &settle;
    wire [7:0]  drive_mask  = 8'b1 << idx;
    wire [7:0]  sample      = uio_in & ~drive_mask;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            idx    <= 3'd0;
            settle <= {SETTLE_BITS{1'b0}};
            acc    <= 8'd0;
            result <= 8'd0;
        end else begin
            if (!settle_done) begin
                settle <= settle + 1'b1;
            end else begin
                settle <= {SETTLE_BITS{1'b0}};
                if (idx == 3'd7) begin
                    result <= acc | sample;
                    acc    <= 8'd0;
                    idx    <= 3'd0;
                end else begin
                    acc <= acc | sample;
                    idx <= idx + 1'b1;
                end
            end
        end
    end

    assign uio_oe  = rst_n ? drive_mask : 8'h00;
    assign uio_out = rst_n ? drive_mask : 8'h00;
    assign uo_out  = result;

    wire _unused = &{ena, ui_in, 1'b0};

endmodule
