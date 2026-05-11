![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# Cable Tester (TinyTapeout)

A 1-tile TinyTapeout submission that tests an 8-conductor cable (e.g. Cat5/Cat6
Ethernet) for per-wire DC continuity.

- [Detailed datasheet](docs/info.md)

## The idea in one paragraph

The chip drives each of the 8 wires high in turn while sampling all 8. On the
*other* end of the cable, a passive RJ45 plug ties all 8 contacts together at a
single node. After eight drive steps the chip knows, per wire, whether that
wire conducted to the far-end common node, and it lights one of 8 status LEDs
accordingly. **All 8 LEDs on = good cable. Any LED off = that specific wire is
broken.**

## Repository layout

| Path | What it is |
|---|---|
| `src/project.v` | The synthesizable design — `tt_um_cable_tester` |
| `test/tb.v` | Verilog testbench + behavioral cable/fault model |
| `test/test.py` | Cocotb tests (continuity, fault injection, invariants) |
| `info.yaml` | TinyTapeout project metadata + pinout |
| `docs/info.md` | Datasheet: how it works, how to test, external hardware |

## Running the tests

```
cd test && make
```

This requires `iverilog` and `cocotb==2.0.1`. The included devcontainer
(`.devcontainer/Dockerfile`) provides both. The RTL compile path defines
`SIM_FAST` to shrink the settle-time counter so a full test pass takes 64
cycles instead of 65536 — see `src/project.v`.

## Resources

- [TinyTapeout](https://tinytapeout.com) — what this is, FAQ, shuttles
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)
