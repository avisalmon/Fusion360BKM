# Fusion reference: every fact this repo relies on

Rule 3 of `CLAUDE.md`: **never invent a Fusion fact.** Each statement here carries a tag and a source:

* `[verified]` seen working in this repo, with the Fusion version and date;
* `[community]` from Autodesk's documentation or forums, not yet checked here;
* `[unverified]` our plan or assumption; check in the running Fusion before relying on it.

A fact that is not here: probe the running Fusion (`python scripts\fusion.py exec "result = dir(root())"`), or find
it in Autodesk's API reference (https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-A92A4B10-3781-4925-94C6-47DA85A4F65A),
add it here with its tag, then use it.

## Versions and paths (Windows; verified 2026-10-27 on this computer unless stated)

| Fact | Tag |
|---|---|
| Fusion **2706.1.14** is the version everything below was verified on (`fusion.py ping` -> `"fusion": "2706.1.14"`) | [verified] |
| Fusion's embedded Python is **3.14.7**; your design scripts run in it, not in `env/` | [verified] probe `sys.version` through the bridge |
| Bridge version **0.1.1** (`CopilotBridge.py`); HTTP on `127.0.0.1:8787`, fallback 8788-8796; the port in use is written to `bridge\port.txt` | [verified] |
| Add-ins folder: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`; this repo's `CopilotBridge\` is linked there as a directory junction by `fusion.py install` (`mklink /J`) | [verified] |
| Add-in manifest `CopilotBridge.manifest` has `runOnStartup: true`: the add-in starts with Fusion | [verified] |
| Launcher: `%LOCALAPPDATA%\Autodesk\webdeploy\production\<hash>\FusionLauncher.exe`, the target of the Start-Menu shortcut `Autodesk Fusion.lnk`; it runs the updater first. The `Fusion360.exe` inside a build folder starts that build directly, skipping the updater | [verified] |
| Updater: `%LOCALAPPDATA%\Autodesk\webdeploy\meta\streamer\<ver>\streamer.exe -p update -a 73e72ada57b7480280f7a6f4a289729f -s production`; a full update took about 12 minutes here | [verified] 2026-10 |
| Fusion signs one account into one session at a time; a second one shows the *Active Sessions Exceeded* dialog (`fusion_dialog.ps1 -Select 'Suspend*' -Click Continue`, then `-Click Continue`) | [verified] |
| macOS paths, a clean install on a fresh computer, and Linux: Fusion has **no Linux version**; the rest is not verified here | [unverified] |

## Units, orientation and parameters

| Fact | Tag |
|---|---|
| Fusion's API works in **centimetres** internally for lengths; the helpers take and report **millimetres** (`MM = 0.1`) | [verified] |
| The bridge sets the default modelling orientation to **Z-up** at start-up (`app.preferences.generalPreferences.defaultModelingOrientation`); the orientation is baked into each document when it is created | [verified] |
| Sketch planes: on the **YZ** plane, sketch X = model **-Z** and sketch Y = model **+Y** (with Z-up). Do not guess sketch axes: use `mpt` / `mrect` / `mcircle`, which take **model** coordinates, and `extrude(..., toward=)` | [verified] the hard way, see gotcha 7 |
| User-parameter names must be words: `W`, `H`, `A`, `V`, `F`, `m`, `s` ... are unit symbols and Fusion answers `param name is not valid` | [verified] |
| A **number** passed to a helper is a one-off dimension in mm; a **string** is a Fusion expression (`'length/2 + 1 mm'`) that stays linked to user parameters | [verified] |
| `design.timeline.item(i).entity.extentOne.distance.expression = '12 mm'` edits an existing extrude's distance and the timeline replays | [verified] |
| `body_info()` reports volume in **cm3** and bounding boxes in **mm** | [verified] |

## Documents, files, camera

| Fact | Tag |
|---|---|
| `new_design()` opens a **new tab**; `close_all_untitled()` closes the unsaved ones | [verified] |
| Saving to the Autodesk cloud from the API was not available in this setup; use `export_f3d` for an archive on disk | [verified] (that it did not work here); the cause is [unverified] |
| Import `.f3d`: `app.importManager.createFusionArchiveImportOptions(path)` then `importManager.importToNewDocument(opts)`; the timeline is intact | [verified] |
| Import STEP: `createSTEPImportOptions(path)` | [verified] |
| Import a mesh (STL): `root().meshBodies.add(path, adsk.fusion.MeshUnits.MillimeterMeshUnit)` | [verified] |
| IGES, SAT, DXF, SVG, OBJ, 3MF import | [unverified] |
| Camera: `app.activeViewport.camera` with `viewOrientation = adsk.core.ViewOrientations.TopViewOrientation`, assign the camera back, then `fit()` | [verified] |
| Screenshots: `app.activeViewport.saveAsImageFile(path, width, height)` through `screenshot()` / `fusion.py shot` | [verified] |

## Modal dialogs and the main thread

| Fact | Tag |
|---|---|
| All API work runs on Fusion's main thread via a `CustomEvent`; a **modal dialog** (update prompt, *Active Sessions Exceeded*, save question) blocks every bridge call until dismissed; `ping` reports `blocked` or a call times out: `Timed out after 30s waiting for Fusion main thread (is a modal dialog open in Fusion?)` | [verified] |
| Fusion sees the add-in **twice** through a junction (two entries in the Add-Ins dialog); the singleton guard and `allow_reuse_address = False` keep one server | [verified] gotcha 5 |
| `fusion_dialog.ps1 -All` lists the texts of open Fusion dialogs; `-Click <button>` clicks one; `-Select '<pattern>'` picks a list item first | [verified] on Windows |

## Electronics workspace

| Fact | Tag |
|---|---|
| Fusion has an Electronics workspace (schematic, 2D PCB, 3D PCB document) | [community] not opened here yet |
| The Python API for electronics documents is thinner than for designs | [community] forum consensus; re-check on 2706 |
| EAGLE `.sch` / `.brd` / `.scr` import | [unverified] |

Everything about electronics is research first: the `fusion-electronics` skill lists the probes to run.

## 3D printing rules of thumb

None verified by a print made from this repo yet (the template's 0.2 mm lid clearance and 2.5 mm M3 pilots are
unprinted). The `fusion-mentor` skill lists the `[community]` rules; the first measured print moves them here.

## The helper API (`CopilotBridge/bridge_helpers.py`, reloaded on every call; all lengths in mm) `[verified]`

Scripts run with `adsk.core`, `adsk.fusion`, `app`, `ui` and every helper below already in the namespace; assign
`result = ...` to get data back. Signatures as in the file (`tests/test_helpers_api.py` checks that every name in
`__all__` is defined):

```text
MM = 0.1; mm(x); P(x, y, z); V(x, y, z); deg(a); items(collection)
design(); root(); active_doc_name(); close_doc(save=False, doc=None); close_all_untitled()
new_design(name=None, parametric=True); clear_design(); new_component(name, parent=None)
sketch_on(plane='xy', comp=None, name=None, offset_mm=0.0)        plane: 'xy' | 'xz' | 'yz' | a face | a construction plane
rect(sk, x0, y0, x1, y1); prect(sk, width, height, cx=0.0, cy=0.0)  prect: dimensioned + constrained; width/height may be expressions
eval_mm(x); circle(sk, cx, cy, d); polygon(sk, cx, cy, sides, circumradius_mm, rotation_deg=0.0)   circle/polygon/hole_at/pattern_rect are numeric: eval_mm('length/2 - inset') turns an expression into the number
text(sk, string, height_mm, cx=0.0, cy=0.0, width_mm=None, font=None, bold=False)   returns a SketchText; extrude() takes it directly (text has no profiles)
mpt(sk, x, y, z); mrect(sk, p0, p1); mcircle(sk, center, d)         model-coordinate sketching (no axis guessing)
sketch_normal(sk)
extrude(sk_or_profiles, distance_mm, op='new', comp=None, symmetric=False, taper_deg=0.0, toward=None)   op: 'new' | 'join' | 'cut' | 'intersect'
revolve(sk_or_profiles, axis, angle_deg=360.0, op='new', comp=None)
fillet_all(body, radius_mm, predicate=None, comp=None); chamfer_all(body, distance_mm, predicate=None, comp=None)
shell(body, open_faces, thickness_mm, comp=None); top_face(body, axis='z')
hole_at(face, x_mm, y_mm, diameter_mm, depth_mm=None, comp=None)
combine(target, tools, op='join', keep_tools=False, comp=None); move_body(body, dx=0.0, dy=0.0, dz=0.0, comp=None)
pattern_circular(features_or_bodies, axis, count, angle_deg=360.0, comp=None)
pattern_rect(features_or_bodies, count_x, spacing_x_mm, count_y=1, spacing_y_mm=0.0, comp=None)
mirror_body(body, plane='yz', comp=None)
add_param(name, expression, unit='mm', comment=''); set_param(name, expression); params()
bodies(comp=None); body_info(comp=None)
export_step(path); export_stl(path, body=None, refinement='high'); export_f3d(path)
fit(); screenshot(path, width=1280, height=800, do_fit=True); set_appearance_color(body, r, g, b, name=None)
ValueInput, Point3D, Vector3D (adsk.core classes re-exported)
```

Not wrapped yet (write the helper when an example needs it, probe first, test it): **loft, sweep, threads,
construction planes at an angle, components with joints, sections**. The backlog lists which example brings each
one. `text` was the first to arrive this way (27 October 2026, probed for `01_coin`: `sketchTexts.createInput2` +
`setAsMultiLine`, Arial by default, `font=` and `bold=` verified with Consolas; text adds no profile to the sketch,
and a sketch on a face already holds the face's outline as a profile, so extrude the `SketchText`, never the
sketch; the extrude joined 63 faces of "BKM" onto a Ø30 disc).
