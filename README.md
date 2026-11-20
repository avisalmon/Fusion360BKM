# Fusion360BKM

### Design a whole product with an AI that drives Fusion 360 for you: 3D parts, circuit boards a factory can make, and the case and production files that join them.

<!-- last-updated:start -->
**Last updated 20 November 2026** · 8 new lessons · [See what's new](docs/lessons_log.md)
<!-- last-updated:end -->

**Start page (Hebrew / English): https://avisalmon.github.io/Fusion360BKM/**

---

**Autodesk Fusion 360** is free for personal use and does 3D parts, electronics (schematics and boards) and the
fitting of one into the other. This repo is the best known method for working it **from a chat**: a small add-in
(`CopilotBridge`) runs inside Fusion and takes Python scripts over a local HTTP port; the AI in your editor writes
the script, runs it, reads back every body's measurements and a screenshot, and tells you what it sees. You keep
Fusion open beside the chat and watch the part appear.

Open the repo in VS Code with **Claude Code** or **GitHub Copilot** (Agent mode), type **"Tell me what to do"**
(or **"תגיד לי מה לעשות"**), and the chat:

* checks your computer and links the add-in into Fusion (one Fusion restart, once),
* asks what you want to make, writes a numbered spec in millimetres, and gets your OK,
* builds it in Fusion step by step, **verifying by numbers and by eye** after every run,
* exports STL for the printer, STEP for other CAD tools, F3D to keep,
* teaches as it goes, in Hebrew or English, and resumes where you stopped next time,
* pulls the newest version of this guide at the start of every session.

## Four stages

1. **Set up** (you, by hand): install [Fusion 360](https://www.autodesk.com/products/fusion-360/personal) and sign
   in; install [VS Code](https://code.visualstudio.com), [Git](https://git-scm.com/downloads), and an AI chat
   (Claude Code, or GitHub Copilot in Agent mode); in VS Code **Ctrl+Shift+P** -> **Git: Clone** -> paste
   `https://github.com/avisalmon/Fusion360BKM.git` -> **Open**. Every click: [docs/get_started.md](docs/get_started.md).
2. **Learn by hand, old school**: Avi Salmon's Fusion 360 course at
   [Babook](https://babook.co.il/courses/fusion360/) (Hebrew, seven video lessons: a coin, tweezers, a key, a
   vacuum-cleaner nozzle, a mug). Optional; the chat suggests the lesson that matches what you are about to build.
3. **The AI magic** (this repo): in the chat, type `Tell me what to do` / `תגיד לי מה לעשות`. The whole road is
   [docs/journey_checklist.md](docs/journey_checklist.md).
4. **Examples**: [examples/](examples/README.md), each with its scripts, files, pictures, what was verified, and what it
   taught this guide: [a box from a paper note](examples/06_sketched_box/README.md), three circuit boards, and the demo
   product below.

## Three tracks (and a fourth coming)

* **3D parts**: from words, a hand sketch or a real object, to a spec in mm, a script, checks, and STL to print.
* **Circuit design**: the circuit in words, a schematic, a placement *you* review, routing, then three layers of
  checks (Fusion's, ours against JLCPCB's limits, a simulated factory that reads the Gerbers) and one summary page
  per board with the zip to upload. Boards [10](examples/10_led_switch_board/index.html),
  [11](examples/11_blinker_555/index.html), [12](examples/12_tiny_arcade/index.html).
* **A whole product**: the board in 3D (every part's model comes from the library), a case designed around it and
  proven by intersecting every printed part with every part, screw, battery and cable, and a production package:
  STL, Gerbers, the assembly as STEP and `.f3d`, assembly steps, one bill of materials for everything. The demo:
  **[Tiny Arcade](examples/12_tiny_arcade/index.html)**, an ESP32 game board in a rounded handheld with a power
  bank inside (an example for learning, not for production).
* **Software** (coming later): the code that runs on the board, as part of the product.

## The part library

**[library/](library/index.html)**: real parts from a real shelf, each a full library cell (photos, pins checked on
the part, a footprint and symbol checked in Fusion, a 3D model). Every user keeps their own; Avi's is public, as the
example of what a library should look like. **Take one, give back two:** borrow a part from Avi's shelf today
instead of waiting for AliExpress, and order two that come back to him.

## What's in the box

```
index.html                 The start page (GitHub Pages), Hebrew + English
CLAUDE.md                  The AI's standing rules for this repo
.claude/skills/            9 playbooks: design-with-fusion, setup-fusion-bridge, fusion-modeling, fusion-files,
                           sketch-to-design, fusion-mentor, fusion-electronics, build-example, publish-to-github
.github/skills/            The same playbooks for GitHub Copilot (generated, kept identical by a test)
.github/copilot-instructions.md, AGENTS.md   Generated instructions + an index of every skill
CopilotBridge/             The Fusion add-in: HTTP server + helpers in millimetres (sketch, extrude, revolve,
                           fillet, shell, holes, patterns, parameters, export, screenshot)
scripts/fusion.py          One tool: doctor | install | launch | ping | new | run | exec | info | shot | export | dialog
scripts/fusion_dialog.ps1  Reads and clicks Fusion's modal dialogs when they block the bridge
templates/parametric_box/  A known-good start: a shelled box with a lid, eight parameters, verified
examples/                  Built from the chat, with evidence: 06_sketched_box (from a paper note); boards
                           10, 11 and 12; 12_tiny_arcade is a whole product with its production package
library/                   The part library: one folder per owner, one per part; index.html is its page
                           (scripts/library_page.py)
my_designs/                YOUR work (git-ignored, so updates never touch it)
exports/                   STL / STEP / F3D / PNG output (git-ignored)
docs/                      Setup, the journey, architecture, the Fusion reference, procedures, gotchas, what's new
```

## By hand, without the AI

```powershell
python scripts\fusion.py doctor                             # what is there, what is missing, the next command
python scripts\fusion.py install                            # link the add-in into Fusion (then restart Fusion once)
python scripts\fusion.py launch                             # start Fusion and wait for the bridge
python scripts\fusion.py ping                               # {"fusion": "2706.1.14", "bridge": "0.1.1", "doc": ...}
python scripts\fusion.py run templates\parametric_box\design.py
python scripts\fusion.py shot exports\box.png               # a picture of the viewport
python scripts\fusion.py new my_part                        # my_designs\my_part\design.py from the template
python scripts\fusion.py export my_part                     # STL (per body + whole), STEP, F3D into exports\
```

`scripts/fusion.py` needs only Python's standard library. The repo's own checks (`pytest`, `ruff`) use a virtualenv:
`python -m venv env` then `.\env\Scripts\python.exe -m pip install -r requirements-dev.txt`.

**What the setup is, in one paragraph.** Fusion must be running (minimised is fine) and signed in. The add-in is
linked into Fusion's AddIns folder and starts with Fusion; it listens on `127.0.0.1:8787` only. The chat sends a
Python script, the add-in runs it on Fusion's main thread, and sends back printed output, a `result` value and any
traceback. It is not an MCP server (a thin MCP wrapper over the same calls is possible later). A modal dialog in
Fusion blocks everything until somebody clicks it; `fusion.py dialog` can. Details: [docs/architecture.md](docs/architecture.md).

## Honest status

Tested on Windows 11 with Fusion 2706.1.14: `doctor`, `install` (as a junction), `launch` (a cold start, bridge up
in 35 s), `ping`, the template built through the bridge with its measurements read back and its screenshot
described, exports (STL, STEP, F3D), opening `.f3d` / STEP / STL, editing an opened design's timeline, and clearing
the update and *Active Sessions* dialogs. The first example is real: a hand-drawn paper note became a verified tray
in one run ([examples/06_sketched_box](examples/06_sketched_box/README.md)). The repo checks itself (ruff, tests,
skills in sync) and CI has been green on every push; the start page is served at the Pages URL above. Not yet: the
course's five examples, electronics, a printed part, a fresh clone on another computer, GitHub Copilot end to end,
macOS. See [docs/blueprint_roadmap.md](docs/blueprint_roadmap.md) and [docs/backlog.md](docs/backlog.md).

## License

[MIT](LICENSE). Use it, change it, teach with it.
