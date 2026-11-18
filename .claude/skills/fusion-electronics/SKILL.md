---
name: fusion-electronics
description: >
  Design a circuit board in Fusion's Electronics workspace from the chat, and prove it ready for a factory:
  parts looked up in Fusion's libraries, a readable schematic, a placed and routed board, Fusion's ERC and board
  check, our own netlist and rule check against the fab's limits (JLCPCB), Gerber and drill files from a CAM job,
  and a simulated factory that reads them back (electrical test, BOM, pick-and-place, upload zip). Verified on
  Fusion 2706.1.17 with examples/10_led_switch_board; the 3D board and its case are the next step, not yet done.
  TRIGGER: "schematic", "circuit", "pcb", "board layout", "footprint", "electronics workspace", "eagle", "erc",
  "drc", "design rules", "netlist", "route", "gerber", "drill file", "factory files", "manufacture", "jlcpcb",
  "order the board", "bom", "pick and place", "component library", "3d pcb", "put the board in the box".
---

# Fusion electronics: from a circuit in words to files a factory can make

The owner's goal: a circuit created from the chat, parts understood and eventually from **our own library**,
everything set for **reliable production**, then a **3D case** around the board. The road below is verified
from the chat on Fusion 2706.1.17 (example `examples/10_led_switch_board`, 2026-11-16/17), except where it says
"not yet". Facts with sources: [fusion_reference.md](../../../docs/fusion_reference.md) (Electronics section);
traps: [gotchas.md](../../../docs/procedures/gotchas.md) 17-33; the checks in full:
[board_checks_and_factory.md](../../../docs/procedures/board_checks_and_factory.md).

## How it works (one paragraph to tell the owner)

Fusion's electronics Python API (`adsk.electron`) only **reads**. We **write** by sending EAGLE commands
(`ADD`, `NET`, `MOVE`, `WIRE`, `HOLE`...) through `app.executeTextCommand("Electron.run ...")`, which answers
nothing whether it worked or not, so **every write is read back** (the helpers do it). The design is then exported
as EAGLE XML, and our own scripts check it and the factory files outside Fusion, so the proof does not depend on
Fusion staying quiet (it silently refuses rule-breaking edits, gotcha 29).

## The road, step by step (each step is a script in the board's example folder)

1. **The circuit in words, then the parts.** Agree what it does and the nets in plain words (`J1.1 -> SW1 -> R1 ->
   D1 -> J1.2`). Look every part up, never guess a name:
   `python scripts\fusion_parts.py search led 5mm --tht` then `show "LED5MM@SparkFun-LED"` (ADD name, footprint,
   pads, 3D model, MPN, status). Skip parts flagged "crashes ADD" (gotcha 22) and parts not ACTIVE. Prefer parts
   with a 3D model (the case needs it) and an MPN (the BOM needs it).
2. **Schematic** (`circuit.py`): `ecad_new()`, `sch_place(add_name, ref, x, y, value, angle)` with a value for
   every part, `sch_wire(net, ('J1','1'), ('SW1','P'), via=[corners])`, then `sch_netlist()` must equal the intent.
   Draw it **for the person reading it**: one visible loop, signal left to right, corners picked from
   `sch_pin()` read-backs, never across another pin (labels alone looked like "just components spread around").
3. **Placement** (`board.py`), **then STOP and hand the board to the owner** (the owner's rule, 2026-11-18):
   `ecad_open('brd')`, `brd_outline(w, h)` (drags the default outline's corners; never delete through the API,
   gotcha 25), `brd_hole(x, y, 3.2)` for M3, `brd_move(ref, x, y, angle)`, `brd_name_size(1.0)`. No tracks yet.
   Capture the window, look at it, and ask the owner to **review the placement in Fusion and move whatever they
   like** (Move tool; Fusion's tracks do not follow cleanly, which is why routing waits), and to agree the **board
   size, shape and holes** (where, how many, which screw). When they say it is agreed, read their placement back
   (`brd_elements()`, `brd_report()['outline']` and `['holes']`), write it into `board.py` (`PLACE`, `W`, `H`,
   `HOLES`), and only then route. Shrinking around an agreed placement: move every part by the same offset, then the
   holes (`MOVE (x y) (x2 y2)` on a hole's centre moves it; read it back, one landed 0.32 mm off once), then
   `brd_outline`. Torn-up tracks from an earlier try: `ecad('RIPUP;')` asks "All segments will be converted to
   unrouted signals" (Yes/No), so answer it with `fusion_dialog.ps1 -Class QMessageBox -Text '*converted to
   unrouted*' -Click Yes`.
3b. **Routing** (`route.py`, after the placement is agreed): pads from `brd_pad(ref, pad)` (read back, never
   assumed), `brd_route(signal, points, layer="top"|"bottom")`, then `brd_report()`: every signal with tracks,
   **0 unrouted** and no `stray` layer.
   Leave room for the rules: Fusion keeps copper 1.02 mm from the edge and bends tracks to do so (gotcha 26).
   Two layers without vias: a track changes layer only at a through-hole pad, and **every route starts and ends on
   a pad** (a net of many pins is a chain; a WIRE ending on another track's corner raised "unexpected condition",
   gotcha 38). The bottom is Fusion's layer 304, not 16 (gotcha 37): the export cannot show the difference, only
   Fusion's airwires can. A DIP chip's diagonal links (555: pins 4-8, 2-6) go under it, one per layer (board 11).
4. **Fusion's checks, save, export, factory files** (`factory.py`): `sch_erc()` and `brd_errors()` must return
   nothing unapproved; `ecad_save(name)` (CAM needs a saved design, gotcha 28); `ecad_export(<example>\fusion,
   'board')`; `cam_export(<example>\factory)` with `production/cam/two_layer.cam`.
5. **Our board check**: `python scripts\pcb_check.py <example>\fusion\board.brd`. Netlist against the intent in
   the board's `checks.json`, schematic against board, part bodies, routing, every limit of the fab profile
   (`production/fab/jlcpcb_2layer.json`, JLCPCB, read 2026-11-17), Fusion's rule set against the fab's.
6. **The simulated factory**: `python scripts\factory_check.py <example>\factory`. Reads the Gerbers and drill
   file as the fab does: outline, holes, the bare-board electrical test (copper alone must give the schematic's
   nets: an OPEN or SHORT here means never order), mask, silkscreen; writes `BOM.csv`, `CPL.csv`, previews, and
   `board_gerbers.zip` to upload.
7. **Ready** = both checks print **0 errors, 0 warnings**, and every APPROVED line has a reason the owner agreed to.
   Show the owner the previews (render the SVGs with headless Edge) next to the Fusion screenshot.
8. **Conclude the board with its summary page**: `python scripts\board_summary.py <example>` writes
   `<example>\index.html` from the board's own files (verdict, the four layers of checks, schematic and board with
   nets that light up, the factory's view, the netlist traced intent -> copper, parts, approvals, every file). Open
   it, read the verdict, and show it to the owner: it is how a board is handed over (approved by the owner
   2026-11-18). `tests/test_board_summary.py` fails when a board with a `fusion/*.brd` has a stale or missing page.
9. **Order** (human): upload the zip to the fab, compare its viewer with the preview. **Not yet done** in this repo:
   say so; the fab's own review and a real electrical test are unverified until the first order.
10. **The board in 3D and the case**: not yet (backlog E3.7). `Switch3dPcbDocCmd` opens the 3D PCB; outline, holes
   and connector positions are to feed `templates/parametric_box`.

## Rules while in this territory

* **The repo is the source of truth; Fusion is the vehicle** (the owner's rule, 2026-11-17). A board is its
  scripts, `checks.json`, the EAGLE export in `fusion/` and the factory files in `factory/`, all in git. The
  Fusion cloud copy exists only because CAM output needs a saved design: `ecad_save` keeps exactly one per
  board and overwrites it on every build, which also spares Fusion Personal's limited documents. Never edit a
  board by hand in Fusion and keep only that: change the script, rebuild. (A rebuild reproduced the export and
  the Gerbers byte for byte, timestamps aside.) The one planned hand edit is the owner's placement review
  (step 3): it is read back into `board.py` before anything else happens.
* **Fusion Personal allows 10 editable documents** (the Data Panel shows "8 of 10"; seen 2026-11-18). A full
  count stops every save: board 11's board tab opened locked and its changes could not be saved. **When a board
  is finished, make its documents read-only** (the owner's rule, 2026-11-18), and make them editable again only
  when we go back to that board. How to switch it in the Data Panel is not yet verified here: the first time,
  ask the owner to do it and tell you what they clicked, then write it into the reference.

* **Read back every write**; a command that says nothing has not necessarily worked (gotcha 17).
* **Approvals are decisions, not silence**: a finding the owner accepts goes into `checks.json` `approved` with
  `code`, `match` and `why`. Never approve an OPEN, SHORT, UNROUTED or NET-EXPECTED.
* **The intent is written by hand** in `checks.json` `nets` from the agreed circuit, not copied from the schematic:
  it is what catches a wire to the wrong pin.
* **Fab numbers come with their source and date**; re-read the fab's page before an order.
* **A modal dialog blocks the bridge**: never send `DRC` (gotcha 27); a part whose library fixes its value (a
  connector) gets `value=None`, because `VALUE` on it asks a question nothing answers from a script (gotcha 21;
  `sch_place` refuses it); `fusion.py dialog` lists what is open.
* Screenshots: `fusion.py shot` does not work in these editors (gotcha 18); capture the Fusion window with Windows
  (PrintWindow) and look at it.
* Every new trap becomes a numbered gotcha, every new fact a tagged row in the reference, every new check a test
  that breaks a copy of a real board on purpose.

## Not done yet (do not claim these)

Our own library (E3.5: parts with checked footprints, 3D models, MPN and supplier numbers), library parts explained
as a lesson (E3.4), an order placed (E3.6), the 3D PCB and the case (E3.7), SMD parts and copper pours (no board has
used them; the checks report pours as not modelled).

## Hand-off checklist

- [ ] the circuit and its nets agreed in words, and written as `checks.json` `nets`
- [ ] every part looked up with `fusion_parts.py`, with a value, ACTIVE, with a 3D model
- [ ] schematic screenshot looked at; `sch_netlist()` equal to the intent
- [ ] placement, board size and holes reviewed in Fusion and agreed by the owner, read back into `board.py`,
      before any routing
- [ ] board: 0 unrouted, screenshot looked at
- [ ] `sch_erc()` and `brd_errors()` clean; design saved; exported; factory files written
- [ ] `pcb_check.py` and `factory_check.py`: 0 errors, 0 warnings; approvals explained to the owner
- [ ] `board_summary.py` page written, opened, its verdict read and shown to the owner
- [ ] the example README's status table says exactly what was verified and when, and what was not
- [ ] the finished board's Fusion documents made read-only (Fusion Personal's 10 editable documents)
