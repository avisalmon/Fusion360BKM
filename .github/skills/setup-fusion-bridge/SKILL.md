---
name: setup-fusion-bridge
description: >
  Get Fusion talking to this chat: run fusion.py doctor, create env/ and the dev tools, guide the Fusion
  install and Autodesk sign-in (the owner's part), link the CopilotBridge add-in into Fusion's AddIns
  folder as a junction, start Fusion and wait for the bridge, and fix the things that stop it: a modal
  dialog blocking Fusion's main thread (update prompt, Active Sessions Exceeded, save question), a
  forced Fusion update, two add-in entries, a wrong port, "unreachable" and "blocked" pings.
  TRIGGER: "set up fusion", "install the add-in", "install the bridge", "fusion not found", "bridge
  unreachable", "ping fails", "blocked", "timed out", "fusion doesn't answer", "nothing happens in
  fusion", "active sessions exceeded", "update fusion", "looks like you need to update", "doctor says
  MISS", "scripts and add-ins", "add-in not loaded", "two CopilotBridge entries", "port 8787", "restart
  fusion", "launch fusion", "venv", "pip install fails".
---

# Set up the Fusion bridge

The owner has an editor with an AI chat open on this project, and git; nothing else is guaranteed. Your job: find out
what is installed, **do what you can yourself**, guide the owner through the parts only they can do (installing
Fusion, signing in, some dialogs), and say in plain words what you did. The step-by-step reference is
[docs/procedures/install_bridge.md](../../../docs/procedures/install_bridge.md); how the pieces fit is
[docs/architecture.md](../../../docs/architecture.md); every fact below with its source and tag is in
[docs/fusion_reference.md](../../../docs/fusion_reference.md). The journey continues in
[design-with-fusion](../design-with-fusion/SKILL.md).

## What is needed, and who installs it

| Piece | What for | Who |
|---|---|---|
| Python 3.10+ (3.12 is CI's; 3.15 works here) | `scripts/fusion.py` (stdlib only), the tests | You (per-user install, no admin) |
| `env/` with `requirements-dev.txt` | tests, lint, the commit hook; **not** the design scripts | You |
| **Autodesk Fusion** (Windows or macOS; no Linux) | the CAD itself; it must be **running and signed in** | **The owner**: Autodesk's site, an Autodesk account, a licence (free for personal use at the time of writing; do not promise terms) |
| `CopilotBridge` linked into Fusion's AddIns folder | the HTTP server inside Fusion that runs your scripts | You: `fusion.py install` |
| GitHub CLI `gh` (optional) | publishing, later | `publish-to-github` |

## Principles

1. **Look before you install.** `python scripts/fusion.py doctor` first; show the owner the table; fix only what is
   not `OK`, top to bottom (each row depends on the ones above).
2. **Fusion is a GUI program that must be running.** Nothing here works with Fusion closed; it may be minimised.
   This is not an MCP server and does not start Fusion on its own except through `fusion.py launch`.
3. **One Fusion per account.** Fusion signs one account into one session at a time; a Fusion left open on another
   computer makes this one show *Active Sessions Exceeded* and block.
4. **A dialog is not a bug.** The bridge answers HTTP from its own thread, but your code runs on Fusion's main
   thread; any modal dialog stops it. `ping` says *blocked* or times out after ~30 s: look at the dialog first.
5. Say plainly before anything that may show a Windows "allow changes?" prompt; it can hide behind the editor.

## 1. Python and `env/`

```powershell
python --version                                # 3.10+; missing on Windows: winget install --id Python.Python.3.12 -e
python -m venv env
.\env\Scripts\python.exe -m pip install -r requirements-dev.txt
.\env\Scripts\python.exe -m pytest -q           # the repo checks itself; all green before going on
```
macOS: `python3 -m venv env`, `env/bin/python`. `fusion.py` itself needs no packages: any Python runs it.

## 2. Fusion installed and signed in (the owner)

`doctor` row *Autodesk Fusion installed* looks for the Start-Menu launcher
(`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Autodesk\Autodesk Fusion.lnk`) and falls back to
`%LOCALAPPDATA%\Autodesk\webdeploy\production\<hash>\FusionLauncher.exe` [verified on one computer]. On macOS it
looks for `/Applications/Autodesk Fusion.app` [unverified]. Missing: the owner downloads Fusion from Autodesk
(https://www.autodesk.com/products/fusion-360/) and installs it; on first start Fusion asks them to **sign in**
with their Autodesk account. Give those as 3-4 numbered lines, then wait. You cannot sign in for them.

## 3. Link the add-in (once per computer)

```powershell
python scripts\fusion.py install
```
It creates a **directory junction** `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\CopilotBridge ->
<repo>\CopilotBridge` (macOS: a symlink under `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`,
unverified). A junction, not a copy, so editing the repo edits the add-in. The manifest has `runOnStartup: true`:
Fusion starts it at every launch. If Fusion was already running: either restart it (close Fusion, then
`fusion.py launch`) or, in Fusion, *Utilities > Add-Ins > Scripts and Add-Ins*, tab *Add-Ins*, select CopilotBridge,
*Run* (and tick *Run on Startup*).

**Two "CopilotBridge" entries** in that dialog (real path and junction path) are harmless: the add-in has a
process-wide guard and the server refuses to share a port, so one server runs [verified; gotcha #5].

## 4. Start Fusion and wait for the bridge

```powershell
python scripts\fusion.py launch        # starts the Start-Menu launcher (it runs the updater), polls ping for up to 4 min
python scripts\fusion.py ping          # {"fusion": "2706.1.14", "bridge": "0.1.1", "doc": "...", "product": "DesignProductType"}
```
The add-in writes the port it got into `bridge/port.txt` (8787, or the next free one up to 8796); `fusion.py` reads
it. Fusion's start-up takes 30-90 s here; longer after an update.

## 5. When it does not answer

| `ping` says | Meaning | Do |
|---|---|---|
| `bridge unreachable` and `doctor` says Fusion not running | Fusion is closed | `fusion.py launch` |
| `bridge unreachable` but Fusion **is** running | the add-in did not start (not linked, not enabled, crashed) | `doctor` row 3; *Scripts and Add-Ins* > Run; look for an error dialog in Fusion; restart Fusion |
| *blocked* / `Timed out ... waiting for Fusion main thread` | a **modal dialog** | `python scripts\fusion.py dialog` (below) |
| answers, but `doc` is `null` | no document open | fine; `new_design` opens one |
| a different port than 8787 | another program holds 8787 | nothing to do: `port.txt` has the real one |

### Dialogs (Windows: `scripts/fusion_dialog.ps1`, wrapped by `fusion.py dialog`)

```powershell
python scripts\fusion.py dialog                              # list Fusion's windows and dump the modal dialog's controls
python scripts\fusion.py dialog -Click Continue              # click a button by (wildcard) name
python scripts\fusion.py dialog -Select 'Suspend*' -Click Continue
```
It uses Windows UI Automation on the `Fusion360` process: lists top-level windows, finds the enabled Qt dialog that is
not the main window, prints its controls (text, radio buttons, buttons), and can select a row and click a button.
Known dialogs [verified]:

* **Active Sessions Exceeded** (Fusion open on another computer): `-Select 'Suspend*' -Click Continue`, then once
  more `-Click Continue`. The other computer's Fusion is suspended, not closed.
* **"Looks like you need to update Fusion"**: Fusion will not work until updated. Either let the owner click
  through, or run the updater directly:
  `%LOCALAPPDATA%\Autodesk\webdeploy\meta\streamer\<ver>\streamer.exe -p update -a 73e72ada57b7480280f7a6f4a289729f -s production`
  (about 12 minutes here; the trailing "uninstall after live update" step can spin for a long time while Fusion
  can already be started). Always launch via the Start-Menu launcher, which runs the updater; the
  `FusionLauncher.exe` inside the build folder skips it.
* A **save prompt** when a document is closed with changes: `close_doc(save=False)` in the helpers avoids it;
  from the dialog, click the "don't save" button (check the exact button text in the dump first).
* macOS: the script does not apply; ask the owner what the dialog says.

### Verified environment (for comparison; the reference has the sources)
Fusion 2706.1.14, embedded Python 3.14.7, bridge 0.1.1 on 127.0.0.1:8787, Windows 11, add-in loaded from the
junction. On a fresh computer none of this has been run end-to-end yet: when you do, record what happened in
[docs/blueprint_roadmap.md](../../../docs/blueprint_roadmap.md) and [docs/lessons_log.md](../../../docs/lessons_log.md).

## Hand-off checklist

- [ ] `fusion.py doctor`: every row `OK`, ending with `Everything needed is in place.`
- [ ] `fusion.py ping` prints Fusion's version and the bridge version
- [ ] `env/` exists and `pytest -q` is green
- [ ] the owner knows: Fusion must be running (minimised is fine), one Fusion per account, a dialog blocks the chat
- [ ] anything new learned (another dialog, a path, a version) is in the reference and the gotchas
