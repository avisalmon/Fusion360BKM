# 10 LED switch board: the first board from the chat

A battery connector, a slide switch, a resistor and an LED on a small two-layer board, then a printed case
around it. The smallest real board that walks the whole road once: parts from the library, schematic, electrical
check, board, design-rule check, factory files, the board in 3D, a case that fits. Not from a Babook lesson: it
opens the electronics stage (the 3D course is on Babook, https://babook.co.il/courses/fusion360/).

Status: in progress (schematic done).

```text
J1 (battery, JST XH 2-pin) --VBAT-- SW1 (slide, SPDT) --VSW-- R1 100R --LED_A-- D1 (5 mm LED) --GND-- J1
```

## Parts (all from Fusion's own libraries, all with a 3D model; found with `scripts/fusion_parts.py`)

| Ref | Part, as `ADD` names it | Why this one |
|---|---|---|
| J1 | `B2B-XH-A@Connector` | JST XH, top entry, MPN `B2B-XH-A(LF)(SN)`, status ACTIVE; the usual battery-pack plug |
| SW1 | `SWITCH-SPDT-PTH-11.6X4.0MM@SparkFun-Switches` | SparkFun COM-00102 slide switch, through-hole. The TE `1825159-1@Switches` was rejected: "pending discontinuance", and its prefix is U |
| R1 | `RESISTOR_AXIAL-10.16MM-PITCH@Tinkercad` | axial, 10.16 mm pitch. Fusion's own `R-USAXIAL-7.2MM-PITCH_@Resistor` crashes the ADD command (gotcha 22) |
| D1 | `LED5MM@SparkFun-LED` | 5 mm through-hole LED; pins A and C |

R1 = 100 ohm suits two AA cells (3 V) and a red LED: (3.0 - 2.0) V / 100 ohm = 10 mA.

## Build

```powershell
python scripts\fusion.py run examples\10_led_switch_board\circuit.py 120
```

## Status

| Step | Done |
|---|---|
| Parts found in Fusion's libraries, each with a 3D model | 2026-11-16, Fusion 2706.1.17 |
| Schematic from the chat: 4 parts, 4 nets, read back equal to the spec, looked at | 2026-11-16 |
| Electrical rules check (ERC) clean | not yet |
| Board: 30 x 20 mm outline, parts placed, two M3 holes, routed | not yet |
| Design rules check (DRC) against a fab's rules | not yet |
| Factory files (Gerber, drill, BOM, placement) checked outside Fusion | not yet |
| 3D PCB, and a case around it | not yet |
| Ordered, soldered, lit; case printed and fitted | not yet (human steps) |

## What it taught this repo so far

* Electronics writes are EAGLE commands, checked by reading back (gotcha 17); a wrong library name places nothing.
* `VALUE` on a part with a fixed value opens a modal question that blocks the bridge (gotcha 21); the helper
  checks `deviceset.userValue` first.
* A part whose technology is `_` crashes Fusion's ADD (gotcha 22); `fusion_parts.py` flags them.
* Net stubs with labels, never long wires: a wire can't touch a pin it was not meant for.
