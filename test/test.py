# SPDX-FileCopyrightText: (c) 2026 Daniel Bovensiepen
# SPDX-License-Identifier: Apache-2.0
#
# Cocotb tests for tt_um_cable_tester. The behavioral cable model lives in
# tb.v; we inject opens by writing dut.cable_wire_good and then wait long
# enough for the FSM to complete two full result-update passes.

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


CLOCK_PERIOD_NS = 100  # 10 MHz simulated clock

# Keep this in sync with test/Makefile. RTL simulation sets this to 3 with
# -DSIM_FAST; gate-level simulation uses the fabricated 13-bit settle counter.
SETTLE_BITS = int(os.environ.get("COCOTB_SETTLE_BITS", "3"))
SETTLE_CYCLES_PER_PIN = 1 << SETTLE_BITS
FULL_PASS_CYCLES = 8 * SETTLE_CYCLES_PER_PIN
WAIT_CYCLES = 2 * FULL_PASS_CYCLES + 8


def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start())


async def reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1


@cocotb.test()
async def test_all_wires_good(dut):
    """A fully intact cable with shorting plug lights all 8 status LEDs."""
    start_clock(dut)
    dut.cable_wire_good.value = 0xFF
    await reset(dut)
    await ClockCycles(dut.clk, WAIT_CYCLES)
    actual = int(dut.uo_out.value)
    assert actual == 0xFF, f"expected 0xFF, got {actual:#04x}"


@cocotb.test()
async def test_single_wire_broken(dut):
    """For each k, opening only wire k clears exactly bit k in uo_out."""
    start_clock(dut)
    for broken in range(8):
        dut.cable_wire_good.value = 0xFF & ~(1 << broken)
        await reset(dut)
        await ClockCycles(dut.clk, WAIT_CYCLES)
        expected = 0xFF & ~(1 << broken)
        actual = int(dut.uo_out.value)
        assert actual == expected, (
            f"wire {broken} broken: expected {expected:#04x}, got {actual:#04x}"
        )


@cocotb.test()
async def test_two_wires_broken(dut):
    """Two opens clear exactly two bits; the other six remain set."""
    start_clock(dut)
    # wires 0 and 7 broken -> 0b0111_1110
    dut.cable_wire_good.value = 0x7E
    await reset(dut)
    await ClockCycles(dut.clk, WAIT_CYCLES)
    actual = int(dut.uo_out.value)
    assert actual == 0x7E, f"expected 0x7E, got {actual:#04x}"


@cocotb.test()
async def test_no_cable(dut):
    """No cable / no shorting plug -> all wires open -> all LEDs off."""
    start_clock(dut)
    dut.cable_wire_good.value = 0x00
    await reset(dut)
    await ClockCycles(dut.clk, WAIT_CYCLES)
    actual = int(dut.uo_out.value)
    assert actual == 0x00, f"expected 0x00, got {actual:#04x}"


@cocotb.test()
async def test_only_one_wire_good_is_indistinguishable(dut):
    """Documented limitation: a lone intact wire has no partner so it
    cannot confirm itself, and the tester reports it as bad."""
    start_clock(dut)
    for only in range(8):
        dut.cable_wire_good.value = (1 << only)
        await reset(dut)
        await ClockCycles(dut.clk, WAIT_CYCLES)
        actual = int(dut.uo_out.value)
        assert actual == 0x00, (
            f"only wire {only} good: expected 0x00 (limitation), got {actual:#04x}"
        )


@cocotb.test()
async def test_drive_is_one_hot(dut):
    """Invariant: during normal operation exactly one uio_oe bit is high,
    and uio_out matches it (drives that wire to logic 1)."""
    start_clock(dut)
    dut.cable_wire_good.value = 0xFF
    await reset(dut)
    for _ in range(FULL_PASS_CYCLES + 8):
        await ClockCycles(dut.clk, 1)
        oe = int(dut.uio_oe.value)
        out = int(dut.uio_out.value)
        assert bin(oe).count("1") == 1, f"uio_oe must be one-hot, got {oe:#04x}"
        assert out == oe, f"uio_out {out:#04x} should match uio_oe {oe:#04x}"


@cocotb.test()
async def test_fault_clears(dut):
    """After a fault is cleared, uo_out returns to all-good within two passes."""
    start_clock(dut)
    # Start with wires 0,1,4,5 broken -> 0xCC = 0b1100_1100
    dut.cable_wire_good.value = 0xCC
    await reset(dut)
    await ClockCycles(dut.clk, WAIT_CYCLES)
    assert int(dut.uo_out.value) == 0xCC, (
        f"expected 0xCC, got {int(dut.uo_out.value):#04x}"
    )

    dut.cable_wire_good.value = 0xFF
    await ClockCycles(dut.clk, WAIT_CYCLES)
    assert int(dut.uo_out.value) == 0xFF, (
        f"after clear: expected 0xFF, got {int(dut.uo_out.value):#04x}"
    )


@cocotb.test()
async def test_pin_iteration_order(dut):
    """Driver cycles through pins 0..7 in order, one settle-window per pin.

    Collected by watching uio_oe transitions, starting at the first time the
    driver returns to pin 0. That makes the check robust to where in the
    settle window we happen to start sampling after reset.
    """
    start_clock(dut)
    dut.cable_wire_good.value = 0xFF
    await reset(dut)

    transitions = []
    prev = int(dut.uio_oe.value)
    deadline = 4 * FULL_PASS_CYCLES
    while deadline > 0 and len(transitions) < 9:
        await ClockCycles(dut.clk, 1)
        deadline -= 1
        cur = int(dut.uio_oe.value)
        if cur != prev:
            transitions.append(cur)
            prev = cur

    # Find the index where uio_oe becomes 0x01 (start of a fresh pass)
    # and take the next 8 transitions from there.
    try:
        start = transitions.index(0x01)
    except ValueError:
        assert False, f"never saw a transition into 0x01; transitions={transitions}"

    window = transitions[start:start + 8]
    expected = [1 << i for i in range(8)]
    assert window == expected, f"pin order: expected {expected}, got {window}"
