# Spec: what this repo is

## What it is

A BKM (best known method) for designing with **Autodesk Fusion from a chat**: a small add-in (`CopilotBridge/`) runs
inside Fusion and executes Python on Fusion's main thread; one command (`scripts/fusion.py`) talks to it; the chat
(Claude Code or GitHub Copilot in VS Code, or the Copilot app) writes parametric design scripts, runs them, verifies
the result by numbers and by screenshot, exports for printing, and teaches as it goes. 3D parts first; Fusion's
Electronics workspace (schematic, PCB) next; fitting a board into an enclosure after that.

The road has four stages, like the owner's other BKMs (SingleButtonKitBKM, De10LiteBKM):

1. **Set up** (a human): Fusion installed and signed in, VS Code, Git, an AI chat, this repo cloned.
2. **Learn by hand, old school**: Avi Salmon's Fusion 360 course on Babook (https://babook.co.il/courses/fusion360/,
   Hebrew, 7 video lessons: a coin, tweezers, a key, a vacuum nozzle, a mug). Optional, never a gate.
3. **The AI magic**: "Tell me what to do"; the chat runs everything it can and stops only for what a human must do.
4. **Examples**: the course's objects and more, built from the chat, each with its script, screenshots, `.f3d`
   archive and a badge that says exactly what was verified. The examples are how the repo learns.

## Audience

* Avi (the maintainer), who builds the examples here and grows the skills through them.
* People who took (or are taking) the Babook course and want to see the same objects built by an AI, then design
  their own parts without learning every menu.
* Makers with a 3D printer and no CAD background: they describe or draw a part, the chat designs it.
* Later: people who want a PCB and its enclosure from one conversation.

## Decisions (and why)

* **An add-in with a local HTTP server, not an MCP server.** Fusion's API lives inside Fusion's process and must be
  called on its main thread; the add-in is the only place that code can run. The HTTP server is on `127.0.0.1` only.
  An MCP wrapper over the same HTTP is possible later and would not change the add-in ([architecture.md](architecture.md)).
* **Scripts, not clicks.** Every design is a re-runnable `design.py` (starts from `new_design`), so it is diff-able,
  parametric, and rebuilt in one command. The script is the design's timeline on disk.
* **Millimetres in, millimetres out.** Fusion's API uses cm; the helpers convert, so nobody multiplies by ten.
* **Verify by numbers, then by eye.** `result` (bodies, bounding boxes, volumes, parameters) is compared with the
  spec, then a screenshot is read. "The script ran" is never "the part is right".
* **Never invent a Fusion fact.** [fusion_reference.md](fusion_reference.md) holds every fact with a source and tag;
  unknowns are probed in the running Fusion first.
* **Honest status everywhere.** Status tables with evidence; a roadmap of what is not yet verified; badges that say
  "checked by numbers and by eye", never "works" without a check.
* **Examples before features.** A helper is written when an example needs it, with its test, and the example's page
  says what it taught.
* **Same conventions as the sister BKMs**: `CLAUDE.md` rules, `.claude/skills/` mirrored to `.github/skills/`,
  `env/` virtualenv, `check_updates.py` at session start, CI with secret scan, lessons log stamping the README.
* **Exports are not committed**, except each example's `.f3d` archive (the equivalent of the DE10 BKMs' `.qar`).

## Not in scope

* Teaching Fusion by hand: that is the Babook course (stage 2); this repo links to it.
* Running Fusion in CI (a GUI with a licence and a sign-in): builds happen on the owner's computer, and READMEs say so.
* Autodesk account management, licensing advice, cloud collaboration features.
* Slicing and printer operation: the repo exports STL and records what was measured after printing; the slicer is the
  owner's.
* Linux: Fusion has no Linux version.
