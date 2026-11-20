# Backlog

> Status words: `IDEA`, `TODO`, `WIP`, `DONE`, `DROPPED`. Update a status in the same commit that acts on the
> decision, so the next session can trust this page. Rows for the blueprint itself first; an owner's own designs go
> under their own epic at the bottom.

## Epic 0 - The bridge works (see [journey_checklist.md](journey_checklist.md))

| Item | Status |
|---|---|
| `fusion.py doctor` says "Everything needed is in place." on this computer | DONE (2026-10-27, Fusion 2706.1.14) |
| The template builds through the bridge and the screenshot is read | DONE (2026-10-26) |
| Fusion restarted after the folder move; the add-in loads from `Fusion360BKM` | DONE (2026-10-27, bridge up in 35 s) |
| The repo checks itself (`pytest -q`, `ruff`, `sync_skills.py --check`) | DONE (2026-10-27, 125 passed) |
| Published to GitHub as `avisalmon/Fusion360BKM`, CI green | DONE (2026-10-27, first run green) |
| GitHub Pages serves `index.html` (the start page) | DONE (2026-10-27, HTTP 200) |

## Epic 1 - Examples that mirror the Babook course

| Item | Needs | Status |
|---|---|---|
| `01_coin` (lesson 2): disc, rim, raised text | `text` helper (done) | TODO |
| `02_tweezers` (lesson 3): two arms joined, a living hinge | thin extrude, fillet, mirror | TODO |
| `03_key` (lesson 4): bow, shaft, bitting | cuts from a side plane, pattern | TODO |
| `04_vacuum_nozzle` (lesson 5): round to rectangular | a `loft` helper | TODO |
| `05_mug` (lesson 6): body, handle | `revolve`, a `sweep` helper | TODO |
| `06_sketched_box`: the owner's paper sketch, 100 x 80 x 27 mm, 2 mm walls, 4 holes 6 mm ([examples/06_sketched_box](../examples/06_sketched_box/README.md)) | `shell`, circles cut from the underside; the first real run of `sketch-to-design` | DONE (2026-10-27: built first run, numbers and eye matched the drawing, archive re-opened; not printed) |
| Then: a board enclosure, a phone stand, more paper notes | | IDEA |

## Epic 2 - Helpers the examples will need

| Item | Status |
|---|---|
| `loft(profiles)` | TODO |
| `sweep(profile, path)` | TODO |
| `text(sk, string, height_mm, ...)` + emboss/engrave | DONE (2026-10-27, probed for `01_coin`) |
| A parametric `pcircle(sk, d, cx, cy)` (dimensioned + constrained like `prect`), so holes follow the parameters after the build; `06_sketched_box` computes them with `eval_mm` instead | TODO |
| Threads (`threadFeatures`) | IDEA |
| Angled and offset construction planes | IDEA |
| Joints between components | IDEA |
| Section view / section analysis for screenshots | IDEA |
| Convert mesh (STL) to solid | IDEA |

## Epic 3 - Electronics: a circuit from the chat, our own parts library, reliable production, a case around it

The owner's goal (2026-11-16), in this order. Each row is done only when it is seen working in Fusion, with the
evidence written in [fusion_reference.md](fusion_reference.md) and the `fusion-electronics` skill.

| Item | Done when | Status |
|---|---|---|
| E3.1 Probe Fusion Electronics from the bridge: product types, API objects, text commands, EAGLE-style scripts | every finding is a tagged row in the reference, with the Fusion version | DONE (2026-11-16, 2706.1.17) |
| E3.2 Choose the route (API, EAGLE script/ULP run inside Fusion, or generated EAGLE file imported) | the roadmap names the route and the reason | DONE (2026-11-16: write with `Electron.run` EAGLE commands, read back with `adsk.electron`) |
| E3.3 A first circuit from the chat: battery header, switch, resistor, LED; schematic, then board | ERC and DRC clean; schematic and board screenshots match the request | DONE (2026-11-17: `examples/10_led_switch_board`; Fusion's ERC and board check clean, `pcb_check.py` 0 errors 0 warnings) |
| E3.4 Library parts understood: where Fusion's parts come from, how a part is symbol + footprint + 3D package + manufacturer number | a short lesson in the skill and the reference | TODO |
| E3.5 Our own library: known-good parts (each with footprint checked against the datasheet, 3D model, MPN and supplier number), versioned in the repo | the first circuit is rebuilt from our library only | DONE 2026-11-20 for 4 parts (board 12 uses only them; MPN and supplier numbers still open) |
| E3.6 Reliable production: fab design rules (JLCPCB first), Gerbers + drill + BOM + pick-and-place from a saved CAM job, checked by an independent reader | files open cleanly outside Fusion; a checklist the doctor can run | WIP (2026-11-17: JLCPCB profile, CAM job, `cam_export`, `pcb_check.py` + `factory_check.py` with tests, board 10 clean. Not yet: an order placed, so JLCPCB's own review and a real electrical test are unverified) |
| E3.7 The board in 3D and a case around it: board outline, holes and connector positions feed `templates/parametric_box` | the board sits on the standoffs in the design; screenshot and clearances checked | DONE 2026-11-20 (board 12: `board3d.py`, `case.py`, fit proven by intersection, production package); not printed |
| E3.8 Example `07_led_board_in_case`: all of the above, end to end, with evidence | example README with what was verified | TODO |
| E3.9 Conclude every board with a summary page: `scripts/board_summary.py` writes `examples/NN/index.html` (verdict, four layers of checks, schematic and board drawn with nets that light up, factory view, netlist traced intent -> copper, parts, approvals, every check line, every file linked, rebuild, status) | the owner approves the page; then it becomes the skill's last step and a section in the procedure page | DONE (2026-11-18: the owner approved the page; it is step 8 of `fusion-electronics` and in `docs/procedures/board_checks_and_factory.md`; board 11 gets one next) |
| Order a real board and print the case; measure the fit | human-only steps; record the result | IDEA |
| E3.10 A parts store ("מחסן רכיבים"): the owner's real stock, built later from photos and lists the owner hands over (searched 2026-11-18: no earlier inventory found on the PC, Drive or Gmail). Boards are then designed from parts on the shelf, and it seeds our own library (E3.5). **Decided 2026-11-20 (the owner): public.** Avi's library is published as the example of what a library looks like, with his deal "take one, give back two"; every user keeps their own. The page: `library/index.html` (`scripts/library_page.py`) | the owner decides public or private; the first board built only from parts in the store | DONE for 4 parts (board 12 is built only from them); grows as parts are added |

## Epic 5 - Software: the product's code (the owner, 2026-11-20: later)

| Item | Done when | Status |
|---|---|---|
| E5.1 The firmware that runs on a board becomes part of the product: written from the chat, built and flashed, checked on the real board, and added to the production package and the summary page (Tiny Arcade first: the Single Button kit's programs on six buttons) | a board's page shows its firmware, how it was built, and what was checked on hardware | IDEA (later) |

## Epic 4 - Infrastructure

| Item | Status |
|---|---|
| A thin MCP wrapper over the HTTP bridge (same calls, no new Fusion code) | IDEA |
| macOS: `install` as a symlink, `launch`, `dialog` | IDEA |
| A first print of an example, measured, recorded in its README | IDEA |
| Hand-drawn sketch examples (photo in `media/brief.jpg`, read back, built) | DONE once (2026-10-27, `06_sketched_box`); more briefs welcome |

## Your designs

_(Filled in with the assistant when you describe what you want to build: Phase 2 of the
[checklist](journey_checklist.md). One row per thing you can hold or see.)_
