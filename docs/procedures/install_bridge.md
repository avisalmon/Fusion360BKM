# Procedure: install the bridge and get Fusion answering

Owner of this procedure: the `setup-fusion-bridge` skill. Everything here was run on Windows 11 with Fusion
2706.1.14 (2026-10-27). macOS is not verified ([blueprint_roadmap.md](../blueprint_roadmap.md)).

## 0. What the human has done already

Fusion installed and signed in, VS Code + Git + a chat, the repo cloned ([get_started.md](../get_started.md)).

## 1. The dev environment (for the repo's own checks; designs do not use it)

```powershell
python -m venv env
.\env\Scripts\python.exe -m pip install -r requirements-dev.txt
```

No Python? Windows: `winget install --id Python.Python.3.12 -e` (then open a new terminal). `scripts/fusion.py`
itself needs only the standard library.

## 2. `doctor`: one table

```powershell
python scripts\fusion.py doctor
```

Rows, in order, and what to do about each one that is not `OK`:

| Row | Not OK means | Do |
|---|---|---|
| `Python 3.x` | never not OK (it is the Python running the script) | |
| `Autodesk Fusion installed` | `not found: install Fusion` | the human installs Fusion ([get_started.md](../get_started.md) section 1) |
| `CopilotBridge add-in not installed` | `run: python scripts\fusion.py install` | step 3 |
| `CopilotBridge linked to another folder` (WARN) | the junction points at an older copy of this repo | `python scripts\fusion.py install` re-points it |
| `Fusion running` | `python scripts\fusion.py launch` | step 4 |
| `bridge port 8787` (WARN `no port file yet; assuming 8787`) | the add-in has not started once since the link | harmless until the next row answers |
| `bridge <ver> answers` | `bridge does not answer` / `main thread is blocked` | step 5 |

Last line when all is well: `Everything needed is in place. Next: python scripts\fusion.py new <name>` (exit code 0).
Otherwise `N thing(s) to fix, in the order above.` (exit code 2).

## 3. `install`: link the add-in

```powershell
python scripts\fusion.py install
```

Creates a **directory junction** `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\CopilotBridge` -> this repo's
`CopilotBridge\` (`mklink /J`; a symlink on macOS). Messages: `already installed: <link> -> <repo>`;
`<link> exists and is a real folder. Move it away, or re-run with --force.` (a hand-copied add-in is in the way);
`mklink failed: ...`. The junction means editing `bridge_helpers.py` in the repo is immediately what Fusion loads
(helpers reload on every call); `CopilotBridge.py` itself loads once at start-up, so a change to it needs a Fusion
restart.

**Fusion must be restarted once after the first install** (the add-in has `runOnStartup`). If Fusion was already
running: close it (File > Exit; answer *Don't save* for an Untitled document if asked), then step 4.

From the chat, when the bridge already answers, the same restart without touching the mouse (done here 27 October
2026; the bridge was back 35 s after the cold start):

```powershell
python scripts\fusion.py exec "result = close_all_untitled()"     # no save prompt later
$p = Get-Process Fusion360; $p.CloseMainWindow(); $p.WaitForExit(90000)   # File > Exit, gracefully
python scripts\fusion.py launch
```

Prefer this over killing the process: Fusion closes its documents and the bridge's port cleanly, so `launch` finds
8787 free again.

## 4. `launch`: start Fusion

```powershell
python scripts\fusion.py launch
```

Starts `FusionLauncher.exe` (the Start-Menu shortcut's target), which runs Autodesk's updater first. A pending
update can take about 12 minutes and shows a progress window; wait for Fusion's main window. If an **update dialog**
asks a question, the human clicks it (or `python scripts\fusion.py dialog`). Fusion then opens an `Untitled` design.

## 5. `ping`: is the bridge answering?

```powershell
python scripts\fusion.py ping
```

* JSON with `fusion`, `bridge`, `doc`, `product` -> done; `doctor` is green.
* `unreachable` (exit 2): Fusion is not running, or the add-in did not start. In Fusion: **Utilities > Add-Ins >
  Scripts and Add-Ins**, tab *Add-Ins*: `CopilotBridge` should be listed (twice, through the junction: gotcha 5) and
  *Running*. Select it, *Run*. Still nothing: close Fusion, `launch` again.
* `blocked` (exit 2) or `Timed out after 30s waiting for Fusion main thread (is a modal dialog open in Fusion?)`:
  a modal dialog is open. `python scripts\fusion.py dialog` lists and dismisses it (`fusion_dialog.ps1 -All` to
  read the texts, `-Click Continue` to click; *Active Sessions Exceeded*: `-Select 'Suspend*' -Click Continue`, then
  `-Click Continue`). Then `ping` again.

## 6. Prove it

```powershell
python scripts\fusion.py run templates\parametric_box\design.py
python scripts\fusion.py shot exports\parametric_box.png
```

`result` lists two bodies (`Base` 80 x 50 x 25 mm, `Lid`) and eight parameters; the PNG shows a box with a lid
beside it. Describe the picture to the owner. Phase 0 and 1 of the [journey](../journey_checklist.md) are done.

## When something moves

* The repo folder moved or was re-cloned: `doctor` says `linked to another folder`; `install` re-points the
  junction; the running Fusion keeps the old path in memory until restarted (it still works through the junction).
* A new Fusion version: `ping` shows it; re-run the template and record the version in the reference if anything
  changed.
* `bridge\port.txt` says a port other than 8787: 8787 was busy when the add-in started; `fusion.py` reads the file,
  nothing to do.
