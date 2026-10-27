---
name: fusion-files
description: >
  Move designs in and out of the running Fusion from the chat: open a .f3d with its timeline, import
  STEP, IGES, SAT, DXF/SVG sketches and STL/OBJ meshes, export STL (per body or whole, for the slicer),
  STEP (for other CAD) and F3D (full Fusion archive), take screenshots from chosen views, close
  documents without prompts, and what saving means when the cloud Data Panel is not available to the
  API.
  TRIGGER: "open the f3d", "open this file", "import step", "import stl", "load the mesh", "export stl",
  "export step", "export f3d", "save the design", "save as", "where is the file", "screenshot", "take a
  picture", "show me", "top view", "close the document", "untitled", "cloud save", "data panel".
---

# Files: open, import, export, screenshots

All of it runs inside Fusion through the bridge (`fusion.py run` / `exec`); the paths you pass are paths on the
owner's computer, so use **absolute paths** inside scripts (`fusion.py export` and `fusion.py shot` resolve
relative paths for you). Detail and sources:
[docs/procedures/files_and_export.md](../../../docs/procedures/files_and_export.md),
[docs/fusion_reference.md](../../../docs/fusion_reference.md). Part of the journey
([design-with-fusion](../design-with-fusion/SKILL.md), Phase 3).

## Export (the finished part leaves Fusion)

```powershell
python scripts\fusion.py export my_bracket                 # exports\my_bracket.stl (+ one STL per body if several), .step, .f3d
python scripts\fusion.py export my_bracket --stl           # only what is asked for
```
From a script: `export_stl(path, body=None, refinement='high')`, `export_step(path)`, `export_f3d(path)` [verified].
`exports/` is git-ignored: exports are build outputs, `design.py` is the source. Share a finished part as a GitHub
Release (`publish-to-github`).

* **STL** is what slicers eat: one file per body for a multi-part print (base and lid print separately, each flat
  face down). The first time with a new slicer, compare the bounding box it shows with `body_info()` (mm): a
  unit mix-up shows up as a part ten times too small or too big [community].
* **STEP** keeps exact geometry for other CAD programs and for people who want to edit the part without Fusion.
* **F3D** is Fusion's own archive with the full timeline and parameters: the local "save" of this flow.
* OBJ / 3MF: the export manager has options for them in the API docs [unverified here]: try, then record.

## Screenshots (how you see the part)

```powershell
python scripts\fusion.py shot exports\view.png 1600 1000    # fits the view, saves PNG, prints {"saved": true, "path": ...}
```
From a script: `screenshot(path, width=1280, height=800, do_fit=True)`. Choose a view first with the raw camera
when it matters:
```python
cam = app.activeViewport.camera
cam.viewOrientation = (
    adsk.core.ViewOrientations.TopViewOrientation
)  # Iso*, Front, Back, Left, Right, Top, Bottom
cam.isFitView = True
app.activeViewport.camera = cam
```
[verified: `templates/parametric_box/parametric_box_top.png` was taken this way]. **Read the image back** and
describe it: this is how the owner knows you looked (CLAUDE.md rule 4). Colour bodies apart with
`set_appearance_color` so they are distinguishable.

## Open and import (something comes into Fusion)

```python
im = app.importManager
doc = im.importToNewDocument(
    im.createFusionArchiveImportOptions(r"C:\...\part.f3d")
)  # .f3d: full timeline [verified]
doc = im.importToNewDocument(im.createSTEPImportOptions(r"C:\...\part.step"))  # STEP [verified]
mesh = root().meshBodies.add(
    r"C:\...\part.stl", adsk.fusion.MeshUnits.MillimeterMeshUnit
)  # STL/OBJ as a mesh body [verified]
```
IGES (`createIGESImportOptions`), SAT (`createSATImportOptions`), DXF (`createDXF2DImportOptions(path, plane)`),
SVG (`createSVGImportOptions`) exist in the API docs but were not tried here [unverified]: try, then tag.
After an import the new document is active: `active_doc_name()`, `body_info()`, `params()` tell you what you got;
a `.f3d`'s features are in `design().timeline` and can be edited (`fusion-modeling`). A mesh body is not a solid:
measuring works, booleans need a mesh-to-solid conversion (not wrapped; raw API or by hand in Fusion).

## Save, close, the cloud

* **Saving to Fusion's cloud (the Data Panel) is not done by this flow** [verified: `doc.saveAs` needs a cloud
  data folder, which was not available to the API here]. The local equivalent is `export_f3d(path)`: everything,
  timeline included, in one file you can re-open with the import above.
* `close_doc(save=False)` closes the active document without the save prompt; `close_all_untitled()` closes every
  `Untitled*` left by failed runs [verified]. A save prompt that appears anyway blocks the bridge:
  `setup-fusion-bridge` (dialog recipe).
* The **source of truth is `design.py`**: a design that can be rebuilt by one command does not need its `.f3d`
  committed. Commit the script and a screenshot; exports are git-ignored.

## Hand-off checklist

- [ ] the exported files exist, with sizes, and the owner was told which one goes where
- [ ] a screenshot was taken and read back
- [ ] imports: the document is active and `body_info()` shows what arrived
- [ ] anything tried for the first time (OBJ, IGES, a view) is recorded in the reference with its tag
