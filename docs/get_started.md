# Get started: the setup a human does (stage 1)

Once per computer, about an hour including Fusion's download. Nothing here needs the command line. When it is done
you open the folder in VS Code and type **"Tell me what to do"**; from there the chat drives.

## 1. Autodesk Fusion

1. Go to https://www.autodesk.com/products/fusion-360/ and choose the download for your system (Windows 10/11 or
   macOS; there is no Linux version). A **personal-use** licence is free for hobbyists at the time of writing; read
   the terms on Autodesk's page, this repo does not promise them.
2. Create or sign in to an Autodesk account when the installer asks. Fusion needs the sign-in; it stores your
   designs in Autodesk's cloud by default (this repo keeps the *scripts* in git and exports files to your disk, so
   nothing depends on the cloud).
3. Start Fusion once and let it finish any update it wants (it may take ten minutes and restart itself). Leave it
   signed in. You can close it afterwards; the chat knows how to start it.

Facts about where Fusion installs itself and how it updates are in [fusion_reference.md](fusion_reference.md).

## 2. VS Code, Git, and an AI chat

1. Install [VS Code](https://code.visualstudio.com) (defaults are fine).
2. Install [Git](https://git-scm.com/downloads) (defaults are fine; on Windows accept "Git from the command line").
3. In VS Code, install one AI chat with an agent mode: **GitHub Copilot** (Extensions, search "GitHub Copilot",
   sign in with your GitHub account, switch the chat to **Agent**) or **Claude Code**. The GitHub Copilot *app*
   works too: open the folder in it.
4. Python: the chat installs it if missing (it is needed for `scripts/fusion.py`; Fusion has its own Python inside,
   which is what runs your designs).

## 3. Clone this repo

1. In VS Code: **Ctrl+Shift+P** (macOS **Cmd+Shift+P**) -> type **Git: Clone** -> Enter.
2. Paste `https://github.com/avisalmon/Fusion360BKM.git` -> Enter -> pick a folder (for example `C:\Projects`) ->
   **Open** when asked.
3. Open the chat panel.

## 4. Say the words

Type **"Tell me what to do"** (or **"תגיד לי מה לעשות"**). The chat then:

* checks GitHub for a newer version of this guide and pulls it in when safe;
* runs `scripts/fusion.py doctor` and shows you a table: Fusion installed? linked? running? answering?
* links the `CopilotBridge` add-in into Fusion's AddIns folder and asks you to **restart Fusion once** (the add-in
  loads at start-up; after that it is always on);
* builds the template (a parametric box with a lid) and shows you a screenshot;
* asks what you want to design.

While you work, **Fusion must be open** (minimised is fine). The chat talks to the add-in inside Fusion on your own
computer; nothing leaves it. A dialog left open in Fusion (an update prompt, a save question) stops everything until
it is closed; the chat will tell you when that happens and what to click.

## Optional, between 1 and 4: learn Fusion by hand (stage 2)

Avi Salmon's course on Babook (Hebrew, 7 video lessons): https://babook.co.il/courses/fusion360/. Lesson 2
installs Fusion and makes a coin; then tweezers, a key, a vacuum nozzle and a mug. Someone who did it understands
what the chat is doing and can check it. Not a gate: skip it if you like, the chat explains each concept when it
first matters.

## If you want a terminal anyway

In VS Code: **Terminal -> New Terminal**. The repo's own tooling (tests, lint) runs in a virtualenv that is always
the folder `env/`:

```powershell
py -3.12 -m venv env
.\env\Scripts\python.exe -m pip install -r requirements-dev.txt
python scripts\fusion.py doctor
python scripts\fusion.py run templates\parametric_box\design.py
python scripts\fusion.py shot exports\parametric_box.png
```

Python 3.12 is what CI uses and what was verified here; a newer system Python (3.15) could not build `pyyaml` for
`pre-commit`. `fusion.py` itself needs only the standard library, 3.10 or later.

(macOS: `python3.12 -m venv env`, then `env/bin/python`; nothing on macOS has been verified yet, see
[blueprint_roadmap.md](blueprint_roadmap.md).)

What each command does and every message it can print: [procedures/install_bridge.md](procedures/install_bridge.md).
