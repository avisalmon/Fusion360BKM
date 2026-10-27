# Blueprint roadmap and known limits

For whoever maintains the blueprint itself (not for owners who cloned it to design their own parts). Rule 8 of
[CLAUDE.md](../CLAUDE.md) applies here first: a box is ticked only when the thing was done and seen, and the line says
how.

## Verified here

* **The bridge end to end** (Windows 11, Fusion 2706.1.14, bridge 0.1.1, 26-27 October 2026): `fusion.py doctor`
  green; `ping` answers with the Fusion version and the open document; the template
  ([parametric_box](../templates/parametric_box/design.py)) builds a base and a lid with eight parameters;
  `result` reports their bounding boxes and volumes; `shot` saves a PNG that was read and described.
* **Opening and importing**: an `.f3d` to a new document, a STEP to a new document, an STL as a mesh body in mm.
* **Exporting**: STL (whole and per body), STEP, F3D, to disk.
* **Editing an opened design's timeline** (an extrude distance changed by expression) and re-reading its bodies.
* **Camera**: top view through `ViewOrientations`, then `fit()`, then a screenshot.
* **The add-in installed as a junction** into Fusion's AddIns folder and re-pointed after the repo folder moved; the
  double-load that the junction causes is handled by a singleton guard.
* **Modal dialogs**: `ping` reports `blocked`; `fusion_dialog.ps1` read and clicked the update prompt and the
  *Active Sessions Exceeded* dialog.
* **Fusion restarted after the folder move** (27 October 2026): `close_all_untitled()` through the bridge, a
  graceful window close, then `fusion.py launch`; the bridge answered after 35 s and `sys.modules` showed the add-in
  loaded from `C:/Projects/Fusion360BKM/CopilotBridge/CopilotBridge.py` (and once more through the junction path,
  as gotcha 5 says). `doctor` green afterwards.
* **The repo's own checks on this computer** (27 October 2026, Python 3.12.8): `ruff check` clean,
  `ruff format --check` clean (60 files), `pytest -q` 125 passed / 5 skipped (the skips need `.git`),
  `sync_skills.py --check` in sync. The tests earned their keep on the first run: `.gitattributes` lacked
  `*.obj binary`, a gotcha row had a literal pipe that broke the table, and `ruff format` had turned the template's
  quotes double so that `fusion.py new` would have silently stopped renaming.
* **Published and green** (27 October 2026): `gh repo create avisalmon/Fusion360BKM --public --push`; the first CI
  run on Ubuntu / Python 3.12 passed all four steps (gitleaks "no leaks found", `ruff check` + `format --check`,
  `pytest` 126 passed / 4 skipped, `sync_skills.py --check` in sync). GitHub Pages enabled from `main` / root;
  `https://avisalmon.github.io/Fusion360BKM/` answered HTTP 200 with the Hebrew title, and `examples/` too.
* **A hand-drawn sketch, read back and built** (27 October 2026, [examples/06_sketched_box](../examples/06_sketched_box/README.md)):
  the owner's phone photo of a paper drawing (100 × 80 × 27 mm, "2mm thick", "4 holes 6 mm") was rotated upright,
  read back in order, its gaps asked as three one-at-a-time questions, and built in one run; bounding box, volume
  (33.3738 cm³) and face count matched the spec, Fusion's isometric showed the drawing's one visible and three
  hidden holes, and the `.f3d` re-opened with the same body and parameters.
* **Every fact in [fusion_reference.md](fusion_reference.md)** carries `[verified]`, `[community]` or
  `[unverified]`, and the helper signatures were read from the code.

## NOT yet verified

Written from the code's own logic, Autodesk's documents, or the sister blueprints, but not yet run for real. The
first person to do each should record the evidence here and in the relevant README, and fix what was wrong:

- [ ] **A fresh clone on another Windows computer**: `doctor` → `install` → restart Fusion → `ping`, as
      [install_bridge.md](procedures/install_bridge.md) describes
- [ ] **The journey in a fresh clone**: "Tell me what to do" triggers the `design-with-fusion` skill in Claude Code
      and in GitHub Copilot (through `.github/skills/`)
- [ ] **The start page in a browser**: the language switch and whether the choice is remembered (only the served
      HTML and its Hebrew default were checked, with `Invoke-WebRequest`)
- [ ] **A printed part**: an export of this blueprint sliced, printed and measured against its spec
- [ ] **The Babook course links** (`/lesson/1/` … `/lesson/7/`): the course page was read; the lesson pages were not
      opened one by one
- [ ] **`pre-commit install`** and the local `no-secrets` hook on a newcomer's computer
- [ ] **The bridge's fallback port** (8796 when 8787 is busy) and `bridge/port.txt` being read by `fusion.py`
- [ ] **Importing IGES, SAT, DXF, SVG, OBJ, 3MF**; converting a mesh body to a solid
- [ ] **Section views, other `ViewOrientations`**, named views, through the API

## Not covered yet

* **Examples**: the catalogue has five slots mirroring the Babook course and none is built; the first built example
  is the owner's paper note (`06_sketched_box`)
  ([backlog.md](backlog.md) Epic 1). Each needs at least one new helper (text/emboss, loft, sweep).
* **Helpers**: loft, sweep, text and emboss, threads, angled construction planes, joints, sections
  ([backlog.md](backlog.md) Epic 2). Until then a script that needs them calls `adsk` directly through `exec`, and
  the first working call becomes a helper.
* **Electronics** (the user's Stage 3 goal: schematics, boards, fitting a board into an enclosure): the
  `fusion-electronics` skill is research-first; nothing in Fusion Electronics has been driven from the bridge yet.
* **Assemblies**: components exist (`new_component`), joints and motion do not.
* **macOS**: `install` would make a symlink and `launch` would need the macOS path; `fusion_dialog.ps1` is Windows
  only.
* **An MCP server**: the bridge is HTTP on loopback; a wrapper that exposes `run`, `exec`, `shot`, `export` as MCP
  tools is an idea, not code.

## Known limits

* **Fusion must be running** (minimised is fine), signed in, with no modal dialog open. The bridge lives inside it.
* **One Fusion per account**: the same Autodesk account open on two computers triggers *Active Sessions Exceeded*.
* **No authentication on the bridge**: loopback only; never forward the port.
* **Scripts run with Fusion's embedded Python** (3.14 in 2706), not the repo's `env/`; no third-party packages there.
* **The cloud**: saving from the API did not work here; designs live on disk as `.f3d` until the owner saves by hand.
* **A modal dialog freezes everything** until a human (or `fusion.py dialog`) answers it; calls time out after 30 s.
* **Hebrew course, English blueprint**: the Babook lessons are in Hebrew; the start page is bilingual, the rest of
  the repo is English.
