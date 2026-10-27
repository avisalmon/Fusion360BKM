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
| Then: a board enclosure, a phone stand, a hand-sketched part | | IDEA |

## Epic 2 - Helpers the examples will need

| Item | Status |
|---|---|
| `loft(profiles)` | TODO |
| `sweep(profile, path)` | TODO |
| `text(sk, string, height_mm, ...)` + emboss/engrave | DONE (2026-10-27, probed for `01_coin`) |
| Threads (`threadFeatures`) | IDEA |
| Angled and offset construction planes | IDEA |
| Joints between components | IDEA |
| Section view / section analysis for screenshots | IDEA |
| Convert mesh (STL) to solid | IDEA |

## Epic 3 - Electronics (Stage 3, later)

| Item | Status |
|---|---|
| Probe Fusion Electronics from the API: what is exposed in 2706 (schematic, library, board outline) | TODO |
| A board outline from a 3D enclosure, or an enclosure from a board's `.step` | IDEA |
| Push a 3D PCB into the mechanical design and check the fit | IDEA |

## Epic 4 - Infrastructure

| Item | Status |
|---|---|
| A thin MCP wrapper over the HTTP bridge (same calls, no new Fusion code) | IDEA |
| macOS: `install` as a symlink, `launch`, `dialog` | IDEA |
| A first print of an example, measured, recorded in its README | IDEA |
| Hand-drawn sketch examples (photo in `media/brief.jpg`, read back, built) | IDEA |

## Your designs

_(Filled in with the assistant when you describe what you want to build: Phase 2 of the
[checklist](journey_checklist.md). One row per thing you can hold or see.)_
