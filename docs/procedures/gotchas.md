# Gotchas: what went wrong, and the fix

Numbered once, never renumbered (skills and lessons point at the numbers). Add new rows at the bottom. "How we know"
says whether it was seen here or read somewhere.

| # | Gotcha | Fix | How we know |
|---|---|---|---|
| 1 | A modal dialog in Fusion (update prompt, *Active Sessions Exceeded*, a save question) blocks the main thread; every bridge call waits and then fails with `Timed out after 30s waiting for Fusion main thread (is a modal dialog open in Fusion?)`; `ping` says `blocked` | `python scripts\fusion.py dialog` (reads and clicks with `fusion_dialog.ps1`), or the human clicks it; then retry | seen here, 2026-10 |
| 2 | *Active Sessions Exceeded*: the same Autodesk account has Fusion open on another computer | `fusion_dialog.ps1 -Select 'Suspend*' -Click Continue`, then `-Click Continue`; or close Fusion on the other computer | seen here, 2026-10 |
| 3 | Starting Fusion through `FusionLauncher.exe` runs Autodesk's updater first; a pending update takes about 12 minutes and looks like a hang | wait for the main window; `launch` tells you; the build folder's `Fusion360.exe` skips the updater (but then you run an old build) | seen here, 2026-10 |
| 4 | Fusion's API is in centimetres; a dimension typed in mm comes out ten times too small | never call `adsk` lengths directly from a script; the helpers take mm (`MM = 0.1`) | Autodesk API docs; the helpers were built around it and verified by `body_info()` |
| 5 | The add-in appears **twice** in Fusion's Add-Ins dialog because Fusion sees the junction and the folder; two servers fought for the port | singleton guard in `CopilotBridge.py` plus `allow_reuse_address = False`; the second instance exits quietly. Two entries in the dialog are normal | seen here, 2026-10 |
| 6 | A user parameter named `W`, `H`, `A`, `V`, `F`, `m` or `s` fails with `param name is not valid`: they are unit symbols | word names: `width`, `height`, `wall` | seen here |
| 7 | On the YZ plane, sketch X is model **-Z** and sketch Y is model **+Y** (Z-up); a cutout drawn by guessing the axes landed in the wrong place | sketch in model coordinates (`mpt`, `mrect`, `mcircle`) and `extrude(..., toward=)`; the reference records the mapping | seen here |
| 8 | `new_design()` opens a new tab on every run; after ten runs Fusion has ten Untitled documents | `close_all_untitled()` at the top of a run; `close_doc(save=False)` for one | seen here |
| 9 | Saving to the Autodesk cloud from the API did not work in this setup | `export_f3d` to disk; save by hand if the cloud copy matters (the save dialog is modal: gotcha 1) | seen here; cause not established |
| 10 | Editing `CopilotBridge.py` does nothing until Fusion restarts; editing `bridge_helpers.py` takes effect on the next call | restart Fusion after a server change (`fusion.py launch` after closing); helpers never need it | by design, seen here |
| 11 | A fillet on the bottom edges, or a shell before the outside fillets, makes a part that prints badly or has sharp inside corners | fillet the vertical edges only (a `predicate` on the edge direction), then shell from the top; the mentor checklist asks | [community] FDM guidance; the template does it this way (unprinted) |
| 12 | The modelling orientation (Z-up or Y-up) is baked into a document when it is created; a document made before the bridge set the preference may have its "top" on another axis | the bridge sets Z-up at start-up; check `body_info()` bounding boxes rather than assuming which axis is up in an old document | seen here |
| 13 | A folder with a running process in it cannot be renamed on Windows (`being used by another process`): the app session's shell has the repo as its working directory | copy with `robocopy` to the new name, re-point the AddIns junction (`fusion.py install`), leave a pointer in the old folder, delete it after the session closes | seen here, 2026-10-27 (renaming `Fusuin360` to `Fusion360BKM`) |
| 14 | `Remove-Item` and a `create` of the same file in parallel raced: the create saw the old file and refused | do delete-then-create sequentially | seen here, 2026-10-27 |
| 15 | PowerShell 5.1 has no `&&`; a `gh --jq` expression with `\(` breaks quoting | `;` plus `$LASTEXITCODE`; `gh --json ...` piped to `ConvertFrom-Json` | seen here |
