# Procedure: files, imports, exports, screenshots

Owner: the `fusion-files` skill. Verified on Fusion 2706.1.14, Windows 11 (2026-10-27) unless tagged.

## Export a finished design

```powershell
python scripts\fusion.py export <name>
```

From the design currently open in Fusion, writes to `exports/`: `<name>.stl` (the whole design; plus one STL per body,
`<name>_<Body>.stl`, when there are several: a base and a lid print separately), `<name>.step` and `<name>.f3d`. The
same from a script: `export_stl(path, body=None, refinement='high')`, `export_step(path)`, `export_f3d(path)`;
absolute paths, folders created.

* **STL** goes to the slicer. Say which body and which face down.
* **STEP** is the exchange format for other CAD tools (exact geometry, no parameters).
* **F3D** is Fusion's archive: the full design with its timeline and parameters; the one to keep and to commit for an
  example (`examples/NN_name/<name>.f3d`; everywhere else exports are git-ignored).

## Open and import

```python
# .f3d (timeline intact):
opts = app.importManager.createFusionArchiveImportOptions(r"C:\...\thing.f3d")
doc = app.importManager.importToNewDocument(opts)
# STEP:
opts = app.importManager.createSTEPImportOptions(r"C:\...\thing.step")
doc = app.importManager.importToNewDocument(opts)
# STL into the current design, as a mesh body (mm):
root().meshBodies.add(r"C:\...\thing.stl", adsk.fusion.MeshUnits.MillimeterMeshUnit)
```

All three `[verified]`. A mesh body is not a solid: it can be placed and measured, not filleted or shelled
(converting a mesh to a solid is `[unverified]` here). IGES, SAT, DXF, SVG, OBJ, 3MF: `[unverified]`.

## Saving and the cloud

Saving to the Autodesk cloud from the API did not work in this setup (the cause is not established); the method is
`export_f3d` to disk. The owner can save by hand in Fusion (Ctrl+S) if they want the design in their cloud; a
**save dialog is modal** and blocks the bridge until answered (gotcha 1).

Tabs: `new_design()` opens a new tab every time; `close_all_untitled()` closes the unsaved ones;
`close_doc(save=False)` closes the active one without asking.

## Screenshots

```powershell
python scripts\fusion.py shot exports\<name>.png
```

Saves the viewport (1280 x 800 by default, after `fit()`) and the chat reads the image. From a script:
`screenshot(path, width=1280, height=800, do_fit=True)`.

Camera recipe (`[verified]`), for a top view before a shot:

```python
cam = app.activeViewport.camera
cam.viewOrientation = adsk.core.ViewOrientations.TopViewOrientation
app.activeViewport.camera = cam
fit()
```

Other `ViewOrientations` (`FrontViewOrientation`, `IsoTopRightViewOrientation`, ...) follow the same pattern; only
Top was used here. A section view through the API: `[unverified]`.

## Where things are

| | |
|---|---|
| Exports | `exports/` (git-ignored) |
| Example archives | `examples/NN_name/<name>.f3d` (committed) |
| Screenshots for a design's README | next to the README (`my_designs/<name>/` or `examples/NN_name/media/`) |
| The bridge's live port | `bridge/port.txt` (git-ignored) |
