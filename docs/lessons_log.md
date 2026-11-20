# What we learned, by date

The short version of every lesson in this blueprint, newest first, so you can see what changed since you last looked.
Each line points to where the full rule lives. Most of them came from something going wrong, or from checking an
assumption against a running Fusion and finding it was not quite true.

## 2026-11-20

- **A case is proven by intersecting it with what it holds.** Board 12's case script builds the board, every part
  and the power bank as reference bodies and intersects every printed part with each: all 0 mm3. Two deliberate
  clashes proved the check sees what it should. [fusion_reference](fusion_reference.md)
- **"It switched" needs proof of where it landed.** `ecad_open('3d')` took any design for the 3D board and built the
  parts into the case; a name that Fusion silently refused let a re-run stack a second set of parts. Both were
  caught by looking at the screenshot. [gotchas 49, 50](procedures/gotchas.md)
- **The summary page carries the whole flow.** A board's page now shows the board in 3D and its case, captioned
  with the README's own words.

## 2026-11-19

- **Check what a command added, not only what it was asked to add.** Each ADD from our own library left an extra copy of the
  part on the sheet; `sch_place` now ends the ADD and fails on any part nobody asked for. [gotcha 48](procedures/gotchas.md)
- **Our own library places like Fusion's.** Board 12 (the Tiny Arcade) is the first built only from the owner's parts: a
  pin on two pads (the tact switch) and GND pins that join by name on the board (not in the schematic's nets).
- **Run what CI runs, and read CI after a push.** The push of board 11 failed on `ruff format --check`, a check
  CI had all along and our pre-commit list did not. A test now keeps that list equal to ci.yml.
  [gotcha 45](procedures/gotchas.md)
- **Photos are published data.** Library photos lose their metadata before they are committed, after being
  turned upright. [gotcha 46](procedures/gotchas.md)
- **Read-only is the owner's switch.** `DataFile.isReadOnly` only reads; on a Personal licence a file is
  editable only when the owner designates it so in the Data Panel. [fusion_reference](fusion_reference.md)

## 2026-11-18

- **A human reviews the placement before anything is routed.** The owner moved board 11's parts by hand after it
  was routed; the tracks did not follow and had to be ripped up. The road now stops after placement: the owner
  moves what they like and agrees on size and holes, their placement is read back into `board.py`, and only then
  does `route.py` run. [gotcha 43](procedures/gotchas.md),
  [fusion-electronics step 3](../.claude/skills/fusion-electronics/SKILL.md)
- **Finished boards go read-only.** Fusion Personal allows 10 editable documents ("8 of 10" in the Data Panel); a
  full count stops every save. [gotcha 44](procedures/gotchas.md)
- **A rule written once is not a rule followed.** The here-doc backslash trap (gotcha 41) happened again a few
  hours after it was written down; an `assert` caught it before anything was written. Prose alone was not enough;
  the habit is the Edit tool for any text with a backslash. [gotcha 41](procedures/gotchas.md)

- **A fix checked on a case that never had the problem is not a fix.** Gotcha 21's `SET CONFIRM YES` was
  "verified" on D1, which never asks; on J1 the question still blocked Fusion. Test a fix on the case that
  failed. `sch_place` now reads `deviceset.userValue` and refuses instead of hanging.
  [gotcha 21](procedures/gotchas.md)
- **Power symbols ask for their name in a modal box; a watcher answers only that box.** `sch_place` starts
  `fusion_dialog.ps1 -WaitSec -Class -Expect -Click OK` before placing one. [gotcha 35](procedures/gotchas.md)
- **A schematic with a chip cannot always avoid a crossing.** The 555's fixed pin order forces one; a crossing
  without a dot is not a connection, and the netlist read-back proves it. Power goes through symbols.
  [examples/11_blinker_555](../examples/11_blinker_555/README.md)
- **An independent check is blind to what the export flattens.** Board 11's bottom tracks went onto Fusion's
  inner layer 16 (the bottom is 304); they connected nothing, yet the EAGLE export wrote them as "16 Bottom" and
  `pcb_check.py` passed the file. Fusion's zero-length airwires were the only witness. Why the way we worked let
  it: board 10 used one layer, and the reference took "16 = bottom" from the exported file, not from the live
  board. The rule: a fact about Fusion comes from Fusion (`board.layers`), and both layers of checking count:
  Fusion's airwires and our file check. [gotcha 37](procedures/gotchas.md)
- **A silent no-op needs a read-back.** `ROTATE =R90 R1` did nothing for R1-R3 (the name read as an angle);
  only the routes going astray showed it. `brd_move` now reads the angle back. [gotcha 36](procedures/gotchas.md)
- **Route pad to pad.** Tracks ending on another track's corner made Fusion raise internal-error boxes; chains
  from pad to pad built cleanly, first time. [gotcha 38](procedures/gotchas.md)
- **My own mistakes today, and the rule each one left** (the owner: "learn, improve and document mistakes"):
  committed while 4 tests failed, because the commit was chained after `pytest` in one command (now: run the
  checks, read the result, commit as a separate step: CLAUDE.md rule 7); closed the design being built along
  with probe documents of the same name (gotcha 40); a shell here-doc put a backspace into a skill (gotcha 41,
  and a test now catches control characters); clicked OK on any dialog when a filter did not match (gotcha 42,
  `fusion_dialog.ps1 -Text`); tried to close Fusion without asking: closing the owner's Fusion is the owner's
  decision (CLAUDE.md rule 6). [gotchas 40-42](procedures/gotchas.md)
- **The summary page concludes every board** (the owner approved it): `board_summary.py` is step 8 of
  `fusion-electronics`. [board_checks_and_factory.md](procedures/board_checks_and_factory.md)

## 2026-11-17

- **The repo holds the board; Fusion is only the vehicle.** Scripts, intent, export and factory files live in
  git; the Fusion cloud keeps one copy per board, overwritten on every build (Fusion Personal limits how many
  documents you keep). A rebuild reproduced the Gerbers byte for byte. Deleting the old copy has an order: the
  design file first. [gotchas 30, 34](procedures/gotchas.md)
- **The first board passed every check we have, and its factory files were made and read back like a factory
  would.** Fusion's ERC and board check are clean; our own `scripts/pcb_check.py` checks the netlist against the
  intent in `checks.json`, the schematic against the board, routing, and JLCPCB's limits (read from their site,
  dated); `scripts/factory_check.py` reads the Gerbers and drill file, simulates the bare-board electrical test
  (copper alone gives the schematic's 4 nets: no opens, no shorts), and writes the BOM, pick-and-place and a zip to
  upload. Tests break copies of the board on purpose so each check proves it catches its fault.
  [board_checks_and_factory.md](procedures/board_checks_and_factory.md)
- **Fusion's own checks are not enough on their own.** Its default rules are not the fab's (the router's 1.27 mm
  from the edge was its 1.02 mm Board Outline Clearance), it silently refuses edits that break them, `DRC` only
  opens a rule dialog, and `Board.checked` never turns true. An independent check on the exported files is the
  proof. [gotchas 26-29, 32](procedures/gotchas.md)
- **Factory files need a saved design.** `Electron.mfgexport` failed until the design was saved to the Fusion cloud,
  then wrote to an unexpected folder; saving also allows twins with the same name. [gotchas 28, 30](procedures/gotchas.md)
- **Read the factory files, not only the design.** The Gerber showed what the design did not: Fusion hatches
  thick silkscreen arcs with hairlines, and puts the M3 holes into the plated drill file. [gotchas 31, 33](procedures/gotchas.md)

## 2026-11-16

- **The first board's schematic was drawn from the chat** ([examples/10_led_switch_board](../examples/10_led_switch_board/README.md)),
  with parts looked up in Fusion's own cached libraries (`scripts/fusion_parts.py`) instead of guessed. Two Fusion
  traps found on the way: a value on a fixed-value part opens a blocking question, and parts with the `_`
  technology crash the ADD command. [gotchas 21-23](procedures/gotchas.md)
- **The first board was laid out and routed from the chat**: 30 x 20 mm, two M3 holes, four tracks, zero
  unrouted connections, confirmed by reading back and in Fusion's own inspector. On the way: the board editor
  starts in mil, deleting through the API breaks Fusion, and its router reshapes tracks to fit its rules.
  [gotchas 24-26](procedures/gotchas.md)
- **A schematic is drawn for people, not only for the netlist.** Parts joined by matching labels alone looked like
  "just components spread around" to the owner; small circuits get visible wires (`sch_wire`), labels only on
  dense sheets. [fusion-electronics](../.claude/skills/fusion-electronics/SKILL.md)
- **Fusion's electronics can be driven from the chat.** The official Python API only reads; EAGLE commands sent
  with `Electron.run` write. A new electronics design, a part from a managed library, and a named net between two
  pins were made from the bridge and each confirmed by reading it back. [fusion_reference.md](fusion_reference.md#electronics-workspace-probed-from-the-bridge-2026-11-16-fusion-2706117-python-3147)
- **A command that says nothing is not a command that worked.** Placing a part from a library Fusion does not have
  failed silently; every write is followed by a read. [gotchas 17-20](procedures/gotchas.md)

## 2026-10-27

- **A paper note became an object, and the drawing's dashes were the clue.** The first hand-drawn sketch through
  `sketch-to-design` ([examples/06_sketched_box](../examples/06_sketched_box/README.md)): rotate the phone photo
  upright, read it in order (view, every number with its edge, shapes, gaps), ask each gap as one question with a
  recommended answer, then build. The three dashed circles were hidden lines of floor holes seen through the walls,
  and Fusion's own isometric showed the same one-visible-three-hidden pattern afterwards. Built in one run; volume,
  bounding box and face count matched the spec. [sketch-to-design](../.claude/skills/sketch-to-design/SKILL.md)
- **Numeric helpers next to parametric ones.** `prect`, `extrude`, `shell` take expressions and stay linked;
  `circle`, `hole_at`, `pattern_rect` take numbers. `eval_mm("length/2 - hole_inset")` makes the numbers follow the
  parameters at build time; a parametric `pcircle` is now in the backlog. Cutting holes from the underside
  (`sketch_on("xy")`, `extrude(..., "wall", "cut", toward=(0, 0, 1))`) avoids face-sketch axis surprises, and the face
  count (15, not 19) proved the cut went through. [fusion_reference.md](fusion_reference.md)
- **Scripts run through the bridge see the helpers' public names only.** `_app` raised `NameError`; `app`,
  `design()`, `root()` are the names to use, as every skill recipe writes them (gotcha 16).
  [gotchas.md](procedures/gotchas.md)
- **Prove the archive by re-opening it.** `export_f3d` returned `True`, but the proof was `importManager.
  importToNewDocument(createFusionArchiveImportOptions(path))` and reading back the same volume, 6 parameters and 5
  timeline features, then `close_doc()`. The example page says "re-opened once" because it was.
  [fusion-files](../.claude/skills/fusion-files/SKILL.md)
- **The commit hook contradicted the example contract.** `check_staged_secrets.py` blocked every `.f3d`, while
  `tests/test_examples.py` requires one per example and `.gitignore` un-ignores exactly `examples/**/*.f3d`. The first
  real example found it; the hook now allows `examples/NN_name/<name>.f3d` and nothing else, with a test that says so.
  [check_staged_secrets.py](../scripts/check_staged_secrets.py)
- **Text is not a profile.** `sketchTexts` adds no profile to a sketch, and a sketch on a face already holds the
  face's outline as one, so `extrude(sketch)` would have raised the whole disc. The rule, now in the `text()` helper's
  docstring: extrude the `SketchText` itself. Probed on a Ø30 coin before the helper was written; `font=` and `bold=`
  checked by eye (Consolas's slashed zero). [fusion_reference.md](fusion_reference.md) ·
  [bridge_helpers.py](../CopilotBridge/bridge_helpers.py)
- **Read the helper's signature before calling it.** `circle(sk, cx, cy, d)` takes separate coordinates; a call
  written from memory as `circle(sk, (0, 0), 30)` failed inside Fusion. The reference lists every signature for
  exactly this reason. [fusion_reference.md](fusion_reference.md)
- **A BOM and a cp1252 console can each stop the tool.** PowerShell's `Set-Content -Encoding UTF8` and Notepad
  prefix a BOM that Python inside Fusion rejects; and printing a traceback containing it crashed `fusion.py` on a
  cp1252 console (a Hebrew document name would do the same). `run` now reads scripts as `utf-8-sig`, and output is
  UTF-8 with replacement, never an exception. [test_fusion_tool.py](../tests/test_fusion_tool.py)
- **CI was green on the first push because it runs nothing new.** The four commands in `ci.yml` are the same four
  run here before committing (`ruff check`, `ruff format --check`, `pytest -q`, `sync_skills.py --check`), on the
  same Python. The one difference, gitleaks over the whole history, is approximated locally by the staged-secrets
  check.
  [ci.yml](../.github/workflows/ci.yml) · [publish-to-github](../.claude/skills/publish-to-github/SKILL.md)
- **`ruff format` reaches into Markdown.** Ruff 0.17 formats the Python code blocks inside `.md` files too, and it
  turns single quotes into double. That silently changed the template, and `fusion.py new` matched
  `new_design('ParametricBox')` with single quotes only: the rename would have stopped working without an error. The
  renamer and the tests now accept either quote style. Rule: after a formatter runs, re-run the tests, not just the
  linter. [test_templates.py](../tests/test_templates.py) · [fusion.py](../scripts/fusion.py)
- **Closing Fusion from the chat, without a save prompt.** `close_all_untitled()` through the bridge first, then a
  graceful close of the main window by process id, then `fusion.py launch`; the bridge answered 35 s after a cold
  start and the add-in loaded from the new folder. [gotcha 10](procedures/gotchas.md) ·
  [install_bridge.md](procedures/install_bridge.md)
- **The system Python was too new for the tooling.** Python 3.15 could not build `pyyaml` for `pre-commit`; the
  `env/` is made with `py -3.12`, the same version CI uses. [get_started.md](get_started.md)
- **The blueprint has four stages, and the examples mirror a course.** Set up (the human) → learn by hand (Babook's
  Fusion 360 course, in Hebrew, seven video lessons) → the AI magic → examples. The example series follows the course's
  objects (coin, tweezers, key, vacuum nozzle, mug) so a learner can watch an object being made by hand and then read
  the same object as a script. [README.md](../README.md) · [examples/README.md](../examples/README.md) ·
  [build-example](../.claude/skills/build-example/SKILL.md)
- **A folder with a running session in it cannot be renamed.** Windows refused to rename `Fusuin360` to
  `Fusion360BKM` while the app session's shell had it as its working directory. The answer was a `robocopy` copy, a
  re-pointed AddIns junction (`fusion.py install`), and a pointer left in the old folder for the session to finish
  with. [gotcha 13](procedures/gotchas.md)
- **A junction, not a copy, is how the add-in is installed.** Fusion loads from
  `%APPDATA%\...\API\AddIns\CopilotBridge`, which is a `mklink /J` junction into the repo, so an edit to
  `bridge_helpers.py` is live on the next call. The cost: Fusion lists the add-in twice and two servers fought for the
  port until a singleton guard was added. [gotcha 5](procedures/gotchas.md) ·
  [install_bridge.md](procedures/install_bridge.md)
- **Every Fusion fact in the reference is tagged.** `[verified]` (seen on Fusion 2706.1.14 here), `[community]` or
  `[unverified]`; the helpers' signatures were read from `bridge_helpers.py`, not remembered.
  [fusion_reference.md](fusion_reference.md)
- **`doctor` is the setup procedure.** The install page quotes `fusion.py`'s own messages row by row, so what you read
  is what the tool prints; nothing is paraphrased. [install_bridge.md](procedures/install_bridge.md)
- **Verify by numbers, then by eye, after every run.** `result` carries bounding boxes in mm and volumes in cm3 for
  each body; a screenshot is read and described, including what is wrong. "It ran" is not "it is right".
  [design_flow.md](procedures/design_flow.md) · [CLAUDE.md](../CLAUDE.md)

## 2026-10-26

- **Fusion must be running; the bridge is not an MCP.** The add-in runs an HTTP server inside Fusion
  (`127.0.0.1:8787`) and hands each script to Fusion's main thread through a custom event; a modal dialog blocks
  everything until somebody clicks it. A thin MCP wrapper over the same HTTP calls is possible later.
  [architecture.md](architecture.md) · [gotcha 1](procedures/gotchas.md)
- **Fusion's API counts in centimetres.** Every helper takes millimetres and multiplies by `MM = 0.1`; a script never
  calls `adsk` lengths directly. [gotcha 4](procedures/gotchas.md)
- **Sketch axes on a side plane are not what you guess.** On the YZ plane, sketch X is model −Z and sketch Y is
  model +Y (Z-up). Side features are sketched in model coordinates (`mpt`, `mrect`, `mcircle`) and extruded with
  `toward=`. [gotcha 7](procedures/gotchas.md) · [fusion_reference.md](fusion_reference.md)
- **Some parameter names are unit symbols.** `W`, `H`, `A`, `V`, `F`, `m`, `s` fail with `param name is not valid`;
  word names always work. [gotcha 6](procedures/gotchas.md)
- **The launcher runs the updater first.** A Fusion update took about twelve minutes and looked like a hang; the
  *Active Sessions Exceeded* dialog (the same account open elsewhere) is answered with `fusion_dialog.ps1 -Select
  'Suspend*' -Click Continue`. [gotcha 2](procedures/gotchas.md) · [gotcha 3](procedures/gotchas.md)
- **Saving to the cloud from the API did not work here; `export_f3d` does.** The design, timeline and parameters go
  to disk as an `.f3d`; examples commit theirs. [gotcha 9](procedures/gotchas.md) ·
  [files_and_export.md](procedures/files_and_export.md)
- **Open and import work: `.f3d`, STEP, and STL as a mesh body.** Verified with the import manager and
  `meshBodies.add`; IGES, SAT, DXF, SVG, OBJ and 3MF are untried. [files_and_export.md](procedures/files_and_export.md)
- **Editing the timeline from a script works.** A feature's extent can be changed after the fact
  (`timeline.item(i).entity.extentOne.distance.expression`), so an opened design can be adjusted, not only rebuilt.
  [fusion_reference.md](fusion_reference.md)
