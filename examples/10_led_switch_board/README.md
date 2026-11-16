# 10 LED switch board: the first board from the chat

A battery connector, a slide switch, a resistor and an LED on a small two-layer board, then a printed case
around it. The smallest real board that walks the whole road once: parts from the library, schematic, electrical
check, board, design-rule check, factory files, the board in 3D, a case that fits. Not from a Babook lesson: it
opens the electronics stage (the 3D course is on Babook, https://babook.co.il/courses/fusion360/).

Status: in progress (schematic and routed board done; design-rule check next).

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
python scripts\fusion.py run examples\10_led_switch_board\circuit.py 120   # schematic
python scripts\fusion.py run examples\10_led_switch_board\board.py 120     # board, on the same design
```

## Status

| Step | Done |
|---|---|
| Parts found in Fusion's libraries, each with a 3D model | 2026-11-16, Fusion 2706.1.17 |
| Schematic from the chat: 4 parts, 4 nets drawn as one visible loop, read back equal to the spec, looked at ([media/schematic.png](media/schematic.png)) | 2026-11-16 |
| Electrical rules check (ERC) clean | not yet |
| Board: 30 x 20 mm outline, parts placed, two M3 holes, routed; 0 airwires read back and in Fusion's inspector, looked at ([media/board.png](media/board.png)) | 2026-11-16 |
| Design rules check (DRC) against a fab's rules | not yet: `Electron::Errors` returned without checking (`board.checked` stayed false); the next experiment |
| Factory files (Gerber, drill, BOM, placement) checked outside Fusion | not yet |
| 3D PCB, and a case around it | not yet |
| Ordered, soldered, lit; case printed and fitted | not yet (human steps) |

## What it taught this repo so far

* Electronics writes are EAGLE commands, checked by reading back (gotcha 17); a wrong library name places nothing.
* `VALUE` on a part with a fixed value opens a modal question that blocks the bridge (gotcha 21); the helper
  checks `deviceset.userValue` first.
* A part whose technology is `_` crashes Fusion's ADD (gotcha 22); `fusion_parts.py` flags them.
* The board editor starts on a mil grid: "MOVE (100 0)" meant 2.54 mm and dragged the wrong outline corner
  (gotcha 24); `ecad_open` now sets GRID MM.
* Deleting the default outline through the API (`deleteEntities`) set off a loop of "unexpected condition"
  dialogs and Fusion had to be killed (gotcha 25); `brd_outline` drags the corners instead.
* Fusion's router reshapes tracks to obey its rules: a corner 1.2 mm from the edge became two 45-degree bends
  (gotcha 26). The read-back is the truth, not the points that were sent.
* A schematic is for people: the first version joined the parts only by matching net labels, and the owner saw "just components spread around". Small circuits are drawn as visible wires, with corners chosen from the pins' read-back positions so no wire passes another pin; the netlist check catches a wrong join.
