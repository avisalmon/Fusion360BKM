# Instructions for Claude working in this repo

This repo is a **blueprint for designing with Autodesk Fusion from a chat**: 3D parts now, electronics (schematic +
PCB) next, and fitting the two together after that. A small add-in (`CopilotBridge/`) runs inside Fusion and executes
Python on Fusion's main thread; `scripts/fusion.py` is the one command that talks to it. The person you are helping is
the **owner** and may be new to CAD, to the command line, or to both. **Fusion must be running** on the owner's
computer for anything to happen; this is not an MCP server (see [docs/architecture.md](docs/architecture.md)).

The road has four stages, like the owner's other BKMs (SingleButtonKitBKM, De10LiteBKM): **1. Set up** (a human
installs Fusion and signs in, clones this repo; the chat links the bridge: [docs/get_started.md](docs/get_started.md));
**2. Learn by hand, old school**: Avi Salmon's Fusion 360 course on Babook (https://babook.co.il/courses/fusion360/,
Hebrew video lessons: a coin, tweezers, a key, a vacuum nozzle, a mug); **3. The AI magic**: this chat;
**4. The examples**: the course's objects and more, built from chat, in [examples/](examples/README.md), each with its
script, screenshots, `.f3d` archive and a badge saying exactly what was verified. The examples are how this blueprint
grows: every one teaches the skills, the gotchas and the reference something new.

## First thing: which situation are you in?

* The owner says anything like **"Tell me what to do"**, "what's next", "continue", "design a ...", "make me a box
  for ...", "get started" (or this is clearly a fresh clone of the blueprint) -> **invoke the `design-with-fusion`
  skill** and follow it. It orients from [docs/journey_checklist.md](docs/journey_checklist.md) (fresh start, or
  resume where the last session stopped), guides the whole journey, runs everything it can, and gives exact
  instructions only for what a human must do (sign in to Fusion, click a dialog, look at the screen). The human-only
  setup that comes before this chat is in [docs/get_started.md](docs/get_started.md).
* Fusion is not installed, the add-in is not linked, `fusion.py ping` says *unreachable* or *blocked*, a dialog is
  in the way, Fusion wants to update -> `setup-fusion-bridge` skill.
* Building or changing geometry (sketches, extrude, revolve, fillet, shell, holes, parameters, "make it 5 mm
  taller") -> `fusion-modeling` skill. The helper functions are listed in
  [docs/fusion_reference.md](docs/fusion_reference.md).
* Opening a `.f3d`, importing a STEP/STL, exporting for printing, screenshots, saving -> `fusion-files` skill.
* The owner describes a part in words, hands you a **hand-drawn sketch or photo**, or points at a real object ->
  `sketch-to-design` skill (turn it into a dimensioned spec first, then into a script).
* The owner asks to *understand* something (why a fillet before a shell, what tolerance for a snap fit, is this
  printable?), wants design advice, or asks "did I do it right?" -> `fusion-mentor` skill. **Teach as you build**
  (rule 9).
* Anything about schematics, PCBs, footprints, Fusion's Electronics workspace -> `fusion-electronics` skill (research
  first; nothing there is verified yet and the skill says so).
* Creating the GitHub repo, `gh` login, pushing, sharing a part -> `publish-to-github` skill (asks before anything
  irreversible or public).
* (Maintainer) building the next example in `examples/NN_name/` (script, page, media, archive, badge, catalogue card,
  what it taught the skills) -> `build-example` skill.
* The owner has never used Fusion and wants to learn it by hand first -> point at the Babook course (stage 2) and
  the lesson that builds the closest object; the `fusion-mentor` skill explains the concepts as they come up.
* "Add this to the methodology", "remember this" -> add it to [docs/procedures/gotchas.md](docs/procedures/gotchas.md)
  (or the procedure it belongs to) and [docs/lessons_log.md](docs/lessons_log.md), and confirm what you wrote.

The map of all documentation is [docs/README.md](docs/README.md).

## Standing rules (apply to everything)

0. **Start every session by checking GitHub for updates, and pull them in when it is safe.** Before anything else, run
   `python scripts/check_updates.py` (with the env's Python once it exists). It fetches the **blueprint** (the remote
   `origin` right after cloning, `blueprint` once the owner has their own repository) and the owner's **own**
   repository, and pulls only when the folder has no unsaved changes and the update applies cleanly; a conflict is
   undone and reported, never left half-done; it never pushes. Then tell the owner in one or two plain sentences what
   arrived ("the install guide got clearer; nothing you need to do"), and act on what the script says: **re-read
   `CLAUDE.md` and your skills if they changed**, reinstall the dev requirements if they changed, and restart Fusion
   if `CopilotBridge/CopilotBridge.py` changed (helpers reload on every call; the server file does not). Unsaved
   changes? Commit them first (with a clear message), then run it again. Conflicts? Resolve them with the owner: keep
   their designs, take the update's fixes. No Python yet (very first session)? Do the same with git directly:
   `git fetch --all`, then `git pull --ff-only` if `git status` is clean. Offline? Say so and carry on.
1. **The virtualenv is the folder `env/`**, always: not `.env`, not `venv`/`.venv`. Run Python through it: Windows
   `.\env\Scripts\python.exe`; macOS/Linux `env/bin/python`. Shell state does not persist between commands, so call the
   interpreter explicitly in every command. Fusion is a program, not a Python package: the scripts you send run in
   **Fusion's own Python** (3.14 inside Fusion 2706), not in `env/`; `env/` is only for this repo's tests and lint.
2. **`git push` publishes the owner's work** (to everyone, if the repository is public). Commit freely; **push only when
   the owner says** push / publish / share. Never `git add -A` without reading `git status --short` first: `exports/`,
   `bridge/`, `my_designs/` and `env/` must never appear.
3. **Never invent a Fusion fact.** API names, units, which axis a sketch plane maps to, dialog texts, file paths,
   version numbers and electronics capabilities come from [docs/fusion_reference.md](docs/fusion_reference.md), where
   each one has its source and a `[verified]` / `[community]` / `[unverified]` tag. A fact that is not there: **try it
   in the running Fusion** (`fusion.py exec`, `dir(obj)`, a one-line probe) or find it in Autodesk's API docs, add it
   to the reference with its source and tag, then use it. Cannot establish it? Say so; never guess. An invented API
   call fails loudly, but an invented tolerance or axis mapping produces a confident, wrong part.
4. **Verify by numbers, then by eye, before you claim.** A script that ran without an exception has not necessarily
   built the right part. After every build: read `fusion.py run`'s `result` (bodies, bounding boxes in mm, volumes,
   parameters) and compare with what was asked; then `fusion.py shot` and **look at the screenshot** (you can read
   images) and say what you see, including what is wrong. Only then tell the owner it is done.
5. **Millimetres everywhere, parameters where it matters.** Fusion's API works in **cm** internally; the helpers in
   `bridge_helpers.py` take and report **mm**, so never multiply by 10 yourself. A number is a one-off dimension; a
   **string is a Fusion expression** (`'length/2 + 1 mm'`) that stays linked to a user parameter, so dimensions the
   owner will want to change later go through `add_param` and strings. Parameter names must not be unit symbols
   (`W`, `H`, `A`, `V` ... are watt, henry, ampere, volt): use words like `width`, `height`.
6. **One Fusion, one main thread, one dialog blocks everything.** The bridge hands your code to Fusion's main
   thread; a modal dialog (update prompt, *Active Sessions Exceeded*, a save question) stops every call until it is
   dismissed. `ping` answering *blocked* or a 30 s timeout means a dialog, not a bug: run `fusion.py dialog`. Fusion
   signs one account into one session at a time, so a Fusion left open on another computer blocks this one. Design
   scripts must be re-runnable: start with `new_design(...)` or `clear_design()`, never assume what is on screen.
7. **Check before you commit.** The blueprint's own tooling is in `requirements-dev.txt`. Before a commit run
   `pytest -q`, `ruff check .` and `python scripts/sync_skills.py --check`; CI runs the same on every push. CI cannot
   run Fusion: a design counts as working only when it was built on a real computer and the README says so.
8. **Tell the truth about status**: say what exists, not what you intend. Each design's README has a status table
   (built in Fusion, checked by numbers, checked by eye, exported, printed): tick one only when it was done and seen,
   and say how. Say plainly when something is unverified: [docs/blueprint_roadmap.md](docs/blueprint_roadmap.md) lists
   what this blueprint has not yet checked (a fresh-machine install, macOS, a real print, electronics).
9. **Mentor, don't just build.** The owner may be new to CAD. At each decision say *why* in a sentence, introduce a
   concept when it first matters (sketch plane, profile, parametric timeline, shell, clearance, overhang), and review
   each design with the `fusion-mentor` checklist (at most three ranked suggestions). Before a part is printed, ask
   the owner to explain what it must fit and how; that is how both of you know what to measure.
10. **Everything this repo knows how to do is a skill.** Skills live in `.claude/skills/` (Claude Code) and are
    mirrored to `.github/skills/` (GitHub Copilot) by `python scripts/sync_skills.py`; `.github/copilot-instructions.md`
    and `AGENTS.md` are generated too. Edit only `.claude/skills/` and `CLAUDE.md`, then run the sync (CI and a test
    fail if the copies drift). New knowledge becomes a new or updated skill, with the detail in `docs/`. When something
    goes wrong, the owner corrects you, or you find a better way: do a short post-mortem (what happened, why the way we
    work let it, the rule that prevents it) and land it in [docs/procedures/gotchas.md](docs/procedures/gotchas.md), the
    skill that covers it, and [docs/lessons_log.md](docs/lessons_log.md).

## Layout in one glance

`index.html` the start page (GitHub Pages, Hebrew + English: the four stages) ·
`CopilotBridge/` the Fusion add-in (server + `bridge_helpers.py`, the mm-based API your scripts use) ·
`templates/parametric_box/` the known-good starting design (`fusion.py new` copies it) · `examples/` the catalogue
(`README.md`, `index.html`) and one folder per example: `design.py`, `README.md`, `index.html`, `media/`, the `.f3d`
archive · `my_designs/` the owner's designs, one folder each (git-ignored) ·
`exports/` STL/STEP/F3D outputs (git-ignored) · `scripts/` (`fusion.py` the whole flow, `fusion_dialog.ps1`,
`check_updates.py`, `sync_skills.py`, `check_staged_secrets.py`) · `docs/` (the Fusion reference, the journey
checklist, architecture, procedures, lessons) · `tests/` (the repo checks itself) · `.github/workflows/` (CI: lint,
tests, skill sync, secret scan) · `.claude/skills/` (your playbooks).
