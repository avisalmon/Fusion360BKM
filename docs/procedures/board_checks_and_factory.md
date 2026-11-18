# Checking a board, and making its factory files

How a board designed from the chat is proven ready for a factory, and how its factory files are made and
checked. Everything here was run on board 10 (`examples/10_led_switch_board`) on 2026-11-17, Fusion 2706.1.17.
The skill that uses this page is [fusion-electronics](../../.claude/skills/fusion-electronics/SKILL.md).

## Four layers of checking, each catching what the others cannot

| Layer | What runs | Where | What it is good for |
|---|---|---|---|
| 1. Fusion's ERC | `sch_erc()` (Fusion's *ERC* command) | in Fusion | the schematic's own sense: parts without values, pins and nets Fusion finds odd |
| 2. Fusion's board check | `brd_errors()` (*Check Design Rules*) | in Fusion | what is left after Fusion's live checking: unrouted airwires, overlaps. Fusion also refuses rule-breaking edits as you make them (gotcha 29) |
| 3. Our board check | `scripts/pcb_check.py` | outside Fusion, on the EAGLE export | the netlist against the design intent, schematic against board, routing, and every rule of **the fab's** limits, not Fusion's defaults |
| 4. The factory simulation | `scripts/factory_check.py` | outside Fusion, on the Gerber and drill files | what the factory will actually receive: layers, outline, holes, the bare-board electrical test, mask, silkscreen; then the BOM, pick-and-place, previews and the zip to upload |

Layers 3 and 4 are this repo's own code (standard library only), so they also run in CI on the committed files,
and tests break copies of board 10 on purpose to prove each check catches its fault
(`tests/test_pcb_check.py`, `tests/test_factory_check.py`).

## The commands

```powershell
# in Fusion, after the schematic and board scripts (example 10 has these three steps)
python scripts\fusion.py run examples\10_led_switch_board\factory.py 300
#   -> sch_erc(), brd_errors(), ecad_save(), ecad_export(<example>\fusion, "board"), cam_export(<example>\factory)

# outside Fusion, any time
python scripts\pcb_check.py examples\10_led_switch_board\fusion\board.brd
python scripts\factory_check.py examples\10_led_switch_board\factory

# last: conclude the board with its summary page, generated from the files above (never typed)
python scripts\board_summary.py examples\10_led_switch_board            # writes examples\...\index.html
python scripts\board_summary.py examples\10_led_switch_board --check    # stale? (tests run this)
```

Each prints a report by section, one line per finding: `ERROR` (must fix), `WARN` (decide), `APPROVED` (decided,
with the reason), `INFO`, `OK`. Exit code 1 on any ERROR. A board is ready when both say **0 errors, 0 warnings**.

## Design intent and decisions: `checks.json`

Each board keeps a `checks.json` next to its scripts (example: `examples/10_led_switch_board/checks.json`):

* `nets`: the intended netlist, written by hand from the README (pins or pads: `"SW1.P"` or `"SW1.2"`). The
  schematic must match it exactly: this catches a wire drawn to the wrong pin that every other check would accept.
* `unconnected_ok`: pins left free on purpose (SW1's second throw).
* `approved`: findings the owner accepted, each `{"code", "match", "why"}`. The finding stays in the report as
  APPROVED with the reason; `match` must appear in its message, so an approval never covers a new problem.

## The fab profile: `production/fab/jlcpcb_2layer.json`

JLCPCB's standard 2-layer FR-4, 1 oz limits, read from https://jlcpcb.com/capabilities/pcb-capabilities on
2026-11-17 (source and date are in the file). `min` is the fab's limit (below it: ERROR; for silkscreen: WARN),
`recommended` is where yield is comfortable (below it: WARN). Re-read the page before an order; for another fab,
copy the file, fill in its numbers with the source, and pass `--fab`.

| Rule | min | recommended |
|---|---|---|
| track width | 0.10 mm | 0.15 mm |
| copper clearance (track/pad/via) | 0.10 mm | 0.15 mm |
| SMD pad to pad | 0.15 mm | |
| plated hole to track | 0.28 mm | 0.35 mm |
| non-plated hole to copper | 0.20 mm | |
| copper to board edge | 0.20 mm | 0.30 mm |
| drill | 0.15 to 6.30 mm | |
| non-plated hole | 0.50 mm | |
| annular ring | 0.18 mm | 0.25 mm |
| hole to hole (edges) | 0.45 mm | |
| silkscreen line / text height / to pad | 0.15 / 1.0 / 0.15 mm | |
| board size | 3 x 3 to 670 x 600 mm | |

## Every check, what it means, and the usual fix

**pcb_check.py** (reads `board.brd` + `board.sch`, Fusion's EAGLE 9 export):

| Code | Finding | Usual fix |
|---|---|---|
| NET-SINGLE | a net reaches one pad only: a wire to nowhere | connect it, or delete the stub |
| NET-EXPECTED | the schematic differs from `checks.json` nets | the schematic is wrong (or the intent changed: update both, on purpose) |
| PIN-UNCONNECTED | a pin with a pad is in no net | connect it, or list it in `unconnected_ok` |
| PART-SHORTED | all of a part's pads are on one net | a wiring mistake |
| PART-NOVALUE, NET-UNNAMED | empty value (empty BOM line); automatic `N$` net name | `sch_place(..., value=...)`; name the net |
| PART-MISSING / PART-EXTRA / PART-PACKAGE / PART-VALUE | schematic and board disagree on parts | rebuild the board from the schematic |
| NET-DIFFERS / NET-RENAMED | a net has other pads on the board than in the schematic | the board was edited apart from the schematic |
| PART-OVERLAP | two part bodies (outline boxes) overlap on one side | move one; a round body's box is generous |
| PART-3D | no 3D model: the 3D board and the case will miss it | pick a part with a model (`fusion_parts.py` shows it) |
| PART-MPN (info) | no manufacturer part number | our own library (backlog E3.5) adds them |
| UNROUTED | a signal's pads are in separate pieces of copper | route it |
| STRAY-COPPER | a track touching none of its signal's pads | delete it |
| SHORT | copper of two signals touches | move the track |
| CLEARANCE, TRACK-WIDTH, EDGE, OUTSIDE | the fab's copper limits | widen, move, or make room |
| OUTLINE, BOARD-SIZE | outline not closed; size outside the fab's range | fix layer 20 |
| DRILL, RING, HOLE-SPACING, HOLE-COPPER, HOLE-TRACK | the fab's hole limits | bigger pad, other part, move the hole |
| SILK-WIDTH, SILK-TEXT, SILK-PAD | thin or small silkscreen; silkscreen on a pad (the fab trims it) | `brd_name_size(1.0)`; library lines need our own library |
| RULESET | Fusion's own rule is looser than the fab's: Fusion would pass what the fab rejects | load stricter rules in Fusion's Design Rules |

**factory_check.py** (reads the Gerber RS-274X and Excellon files, as the fab does):

| Code | Finding | Usual fix |
|---|---|---|
| MISSING, TRUNCATED, GERBER | a layer missing, cut short, or using a feature not modelled | rerun `cam_export` |
| PROFILE | the cut outline differs from the board | the CAM job's profile layer |
| DRILL-MISSING / DRILL-EXTRA | holes in the file and holes of the board differ | rerun the export; check the drill layers in the CAM job |
| NPTH-PLATED | a mounting hole sits in the plated drill file, so it will be plated (gotcha 33) | fine for screws; otherwise a separate non-plated file |
| HOLE-OFF-COPPER | a plated hole with no pad around it on a side | misregistered files: re-export |
| OPEN / SHORT (etest) | the bare board's copper, joined through plated holes, does not give the schematic's nets | the most serious finding: never order |
| CLEARANCE, TRACK-WIDTH (copper) | measured on the Gerbers: smallest gap between different copper, narrowest track | as above |
| MASK-COVERED / MASK-SMALL | a pad without (enough) solder-mask opening | mask expansion in the rules |
| SILK-WIDTH, SILK-ON-PAD | thin silkscreen; silkscreen in a mask opening (the fab removes it) | as above |
| LCSC | no LCSC part number: JLCPCB cannot assemble the part | add the attribute, or solder by hand |

## Where the board lives: the repo, not Fusion

The board's scripts, `checks.json`, the EAGLE export (`fusion/`) and the factory files (`factory/`) are in git:
that is the board. Fusion's cloud holds one disposable copy per board (Default Project / Fusion360BKM), made
only because CAM output needs a saved design, and `ecad_save` overwrites it on every build (deleting the old
`.fprj`, `.fsch` and `.fbrd`, gotchas 30 and 34). Rebuilding board 10 from its scripts gave the same export
and the same Gerbers byte for byte (only the drill file's creation time differs), which is the proof that the
repo, not Fusion, holds the design.

## The factory files: how Fusion makes them

* The CAM job is `production/cam/two_layer.cam`, made from Fusion's own `example_2_layer.cam` (in Fusion's install,
  `...\Electron\LibEagle\examples\cam\examples\`) with the ODB++ and drawing outputs removed and plain file names:
  copper top/bottom, profile, solder mask, solder paste and silkscreen top/bottom (silkscreen = layers 21 tPlace +
  25 tNames: values are not printed), and one Excellon drill file.
* `cam_export()` runs the hidden text command `Electron.mfgexport <dir> <job>`. It needs a **saved** design
  (gotcha 28) and writes to `<parent of dir>/<job>/<job>.gbr/CAMOutputs/...`; the helper collects the files.
* Fusion's assembly outputs (BOM, pick-and-place) in the job produced nothing; `factory_check.py` writes
  `BOM.csv` and `CPL.csv` in JLCPCB's columns from the board instead. CPL positions are the parts' origins (their
  centres for most library parts): check the placement in JLCPCB's preview before ordering assembly.
* Upload `board_gerbers.zip` (git-ignored: rebuilt by `factory_check.py`). JLCPCB's viewer should look like
  `preview_top.svg` / `preview_bottom.svg`.

## What is not checked yet (say so; do not imply it)

* Copper pours (polygons) and thermal reliefs: reported as POLYGONS, not modelled. Board 10 has none.
* Clearances use the pads' outlines: octagons and long pads exactly, SMD pads as rectangles (rounding ignored,
  so slightly strict); arcs are cut into 10-degree pieces.
* Part bodies are compared as outline boxes, not 3D heights; real clearance to a case comes with the 3D board
  (backlog E3.7).
* No order has been placed yet: the files have not passed JLCPCB's own review or a real electrical test.
