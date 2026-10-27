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
| Hand-drawn sketch examples (photo in `media/brief.jpg`, read back, built) | DONE once (2026-10-27, `06_sketched_box`); more briefs welcome |

## Your designs

_(Filled in with the assistant when you describe what you want to build: Phase 2 of the
[checklist](journey_checklist.md). One row per thing you can hold or see.)_
