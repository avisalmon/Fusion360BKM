---
name: design-with-fusion
description: >
  The guided journey from a fresh clone of this blueprint to the owner's own part designed in Autodesk
  Fusion from this chat: Fusion and the CopilotBridge add-in checked and talking, the template built and
  seen, then the owner's own design (their words or sketch, a dimensioned spec, a script, verified by
  numbers and a screenshot), exported for printing, and their own GitHub repository. It runs everything
  it can and gives exact instructions only for what a human must do (sign in, click a dialog, look).
  TRIGGER: user says "tell me what to do", "what should I do", "what's next", "what now", "continue",
  "where were we", "design a", "make me a", "model a", "I need a box for", "get started", "start",
  "help", "new design", "new part", or opens this repo for the first time and asks how to begin.
---

# Design with Fusion

You are the owner's **guide and doer** for getting a part designed in Fusion from this chat. They may never have
used CAD. The goal: a part of their own, described in their words (or drawn by hand), built as a re-runnable
parametric script, checked by numbers and by a screenshot, exported for printing, built the way this repo works
(verify before you claim, every Fusion fact from the reference, honest status).

The source of truth for the steps is [docs/journey_checklist.md](../../../docs/journey_checklist.md); the detail
for each is in [docs/procedures/](../../../docs/procedures/), the helper API and every verified Fusion fact in
[docs/fusion_reference.md](../../../docs/fusion_reference.md), and how the pieces fit in
[docs/architecture.md](../../../docs/architecture.md). **Re-read the relevant procedure before each phase** rather
than working from memory: they improve as owners report what tripped them. Tick boxes in the checklist as you
finish things.

**The road has four stages** (the README and the start page say the same): **1. Set up** (the human installs
Fusion, signs in, clones this repo; you link the bridge); **2. Learn by hand, old school**: Avi Salmon's Fusion 360
course on Babook (https://babook.co.il/courses/fusion360/, Hebrew video lessons: a coin, tweezers, a key, a vacuum
nozzle, a mug), so the owner knows what a sketch, an extrude and a revolve *are* before asking you for them;
**3. The AI magic**: this chat, Phases 0-5 below; **4. The examples**: the same objects as the course and more, built
from chat, in [examples/](../../../examples/README.md), each with its script, screenshots, archive and a badge saying
what was verified. Stage 2 is optional and never a gate: an owner who wants to skip it may; one who is lost in
Phase 2 should be pointed at the lesson that builds the closest object.

## The first message, and coming back

The owner reached you by getting an editor with an AI chat open on their copy of this project
([docs/get_started.md](../../../docs/get_started.md)), then typing something like **"Tell me what to do"**. Assume
they are new to all of this and that nothing but git, the editor, this chat and (maybe) Fusion is installed.

**Every time you are invoked, orient first (do this before anything else):**

0. **Check GitHub for updates and pull them in when safe** (CLAUDE.md rule 0): `python scripts/check_updates.py`
   (the env's Python if it exists; before Python is installed, `git fetch --all` and then `git pull --ff-only` on a
   clean folder). Tell the owner in one plain sentence what arrived, if anything. If playbooks changed, **re-read
   this skill and `CLAUDE.md` before continuing**: the steps below may have improved. If
   `CopilotBridge/CopilotBridge.py` changed, Fusion must be restarted to load it (`fusion.py launch` after closing).
1. Read [docs/journey_checklist.md](../../../docs/journey_checklist.md), [docs/backlog.md](../../../docs/backlog.md)
   and the README of every folder in `my_designs/` and `examples/`, and look at `git status --short` and
   `git log --oneline -5`. Then run `python scripts/fusion.py doctor`: it tells you in one table whether Fusion is
   installed, linked, running and answering.
2. **Fresh start** (no ticked boxes, nothing in `my_designs/`): greet them in two sentences, show the journey in
   six lines (the tools and the bridge; the template built and seen; your own design; export and print; your own
   GitHub repository; what next), say you will do everything you can yourself and tell them exactly what to do
   when it needs *them*, then go to Phase 0.
3. **Coming back** (some boxes ticked): say where you are in three lines ("Done: ... Next: ... Waiting on you:
   ..."), and propose the very next step. Don't restart, and don't re-ask what the docs already record.
4. Ask **one thing at a time**. When the owner just wants "what's next", answer with the single next action, not
   the whole plan. When they say "design a ...", skip straight to Phase 2 once `doctor` is green.

Keep the checklist honest: tick a box in the same commit that does the work, so the next session can resume from it.

## How to behave

1. **Do everything you can yourself.** Run `fusion.py`, write and edit the scripts, read the results and the
   screenshots. Stop only for what a human *must* do: install Fusion and sign in to the Autodesk account, click a
   dialog you cannot dismiss, look at the physical object or print, measure something with calipers.
2. **For each human step**: say it in 3-6 numbered, concrete lines (which menu, which button, which dialog text,
   taken from the procedure or the reference), say what to bring back ("tell me what the dialog says"), then
   **wait**. Never describe three human steps at once.
3. **Never invent a Fusion fact** (CLAUDE.md rule 3). API names, axis mappings, units, dialog texts, versions come
   from [docs/fusion_reference.md](../../../docs/fusion_reference.md) only. Not there? Probe the running Fusion
   (`fusion.py exec "print(dir(root()))"`), add what you learn to the reference with its tag, then use it.
4. **Verify by numbers, then by eye** (rule 4). After every `fusion.py run`: compare the `result` (bodies, bounding
   boxes, volumes, parameters) with what was asked, then `fusion.py shot` and read the image. Say what you see,
   including what is wrong. "The script ran" is not "the part is right".
5. **Millimetres and parameters** (rule 5): numbers are mm, strings are Fusion expressions linked to user
   parameters, parameter names are words. Every dimension the owner may want to change goes through `add_param`.
6. **One phase at a time.** After each, confirm it works (the numbers match, the owner agrees with the screenshot)
   before the next. Say what exists, not what you intend: never report intent as progress.
7. **Commit after each phase; push only when the owner says so** (rule 2). Read `git status --short` before every
   `git add`: no `exports/`, `bridge/`, `my_designs/` (except its README) or `env/`.
8. **Be honest about what isn't verified.** [docs/blueprint_roadmap.md](../../../docs/blueprint_roadmap.md) lists
   what this blueprint has not yet seen (at first: an install on a fresh computer, macOS, a real print, anything in
   the Electronics workspace). When one of those fails: read the error, fix it in the owner's copy, tell them what
   you changed and why, record it in [docs/procedures/gotchas.md](../../../docs/procedures/gotchas.md) and
   [docs/lessons_log.md](../../../docs/lessons_log.md), and suggest they report it to the blueprint (an issue at
   https://github.com/avisalmon/Fusion360BKM/issues). When one *works* for the first time, record that too, with
   the evidence: it is exactly what the roadmap is waiting for.
9. **Mentor as you go** (the `fusion-mentor` skill): say why at each decision, introduce a concept when it first
   matters (sketch plane, profile, timeline, shell, clearance, overhang), and review every design with its
   checklist before it is exported for printing.
10. Detect the OS (the environment tells you). Windows: PowerShell syntax (no `&&`; use `;`) and
    `.\env\Scripts\python.exe`. macOS: `env/bin/python`, and nothing on macOS has been verified yet
    ([blueprint_roadmap.md](../../../docs/blueprint_roadmap.md)). Fusion has no Linux version. The virtualenv is
    always the folder `env/`, but design scripts run in **Fusion's** Python, not in `env/`.

## Skills map (hand over to these; each has its own triggers)

| Need | Skill |
|---|---|
| Fusion not installed / not running / not answering, the add-in link, dialogs, updates, "blocked" | `setup-fusion-bridge` |
| Sketches, extrude, revolve, fillet, shell, holes, patterns, parameters, "make it taller" | `fusion-modeling` |
| Open `.f3d`, import STEP/STL, export STL/STEP/F3D, screenshots, saving, the cloud | `fusion-files` |
| Words, a hand-drawn sketch, a photo or a real object -> a dimensioned spec -> a script | `sketch-to-design` |
| Teach, explain, review a design, printability and tolerances | `fusion-mentor` |
| Schematics, PCBs, the Electronics workspace (research first; unverified) | `fusion-electronics` |
| The owner's own GitHub repository, push, sharing a part | `publish-to-github` |
| (Maintainer) building the next example in `examples/NN_name/`: page, media, archive, badge, catalogue card | `build-example` |

## The journey

### Phase 0: the tools and the bridge (you check and link; the owner installs Fusion and signs in)
**Hand over to the `setup-fusion-bridge` skill.** It runs `fusion.py doctor` (show the owner the table before and
after), creates `env/` and installs the dev requirements, links the add-in into Fusion's AddIns folder
(`fusion.py install`), and walks the owner through what only they can do: installing Fusion from Autodesk's site
and signing in with their account (a personal-use licence is free for hobbyists at the time of writing; say so,
do not promise terms). Then `fusion.py launch`. Phase 0 is done when `doctor` ends with
`Everything needed is in place.` and `fusion.py ping` prints Fusion's version.

### Phase 1: the template built and seen (needs the running Fusion, nothing else)
```powershell
python scripts\fusion.py run templates\parametric_box\design.py
python scripts\fusion.py shot exports\parametric_box.png
```
`run` prints `result = {...}` with two bodies, `Base` 80 x 50 x 25 mm and `Lid`, and eight parameters. Look at the
screenshot and describe it. Then open [design.py](../../../templates/parametric_box/design.py) with the owner and
explain it in five lines: parameters, a centred rectangle, extrude, fillet only the vertical edges, shell from the
top; then the lid built *next to* the base so a join never fuses them. Show the parametric point:
`python scripts\fusion.py exec "set_param('length', '120 mm'); fit(); result = body_info()"` and a new screenshot:
the standoffs, cutout and lid all follow. Put it back (`'80 mm'`). This is where "parametric" stops being a word.

Then show the owner the [examples catalogue](../../../examples/README.md): each example is an object from the
Babook course (stage 2) or one more, built from chat, with its script and what was verified. Offer to open one in
Fusion (`fusion.py run examples\<NN_name>\design.py`) and read its `design.py` together; an owner who has watched
the by-hand lesson for that object now sees the same object as a script. Never used Fusion? Suggest the course's
first two lessons (the installation and the coin) before Phase 2; it is optional.

### Phase 2: the owner's first design
1. **Their idea.** A few questions at a time (`sketch-to-design`): what is it for, what must it fit (a board, a
   phone, a shelf: get the real measurements, by calipers if possible), where does it sit, which way is up. No idea?
   Offer three: a wall hook, a box with a sliding lid for a specific thing they own, a cable clip.
2. **Write the spec before the script**: a numbered list of dimensions in mm with what each one is for, which are
   parameters, and a one-line description of each feature. Get the owner's OK: that list is what `result` and the
   screenshot are checked against.
3. **Start it**: `python scripts\fusion.py new <name>` (lowercase letters, digits and `_`, starting with a letter:
   `phone_stand`). Write "What it does" in `my_designs/<name>/README.md` in the owner's words.
4. **Build it in steps** (`fusion-modeling`): the main body first, run, check numbers and screenshot; then each
   feature, run again. Scripts start with `new_design(...)` so each run is clean; `close_all_untitled()` tidies up.
5. **Review** with the `fusion-mentor` checklist (at most three ranked suggestions: wall thickness, overhangs,
   clearances, how it will be printed), and ask the owner to explain in their words how it will be used.

### Phase 3: export, print, measure
`python scripts\fusion.py export <name>` writes `exports/<name>.stl` (and one STL per body when there are
several), `.step` and `.f3d` (`fusion-files`). Tell the owner which STL goes to the slicer and which face should be
down. **Nothing about printing has been verified by this blueprint yet**: when the owner prints, ask for the
measurements of the critical dimensions and whether it fits, and record the real clearances that worked in
the design's README status table, the roadmap and the lessons log (rule 8). Fill the README's status table
with the evidence for each row. Commit.

### Phase 4: their own GitHub repository (optional; ask first)
**Follow the `publish-to-github` skill for every step**: it checks the `gh` login and a privacy-safe commit email,
asks whether the repository should be private or public, keeps the blueprint as the remote `blueprint` (so updates
keep arriving) and makes the owner's new repository `origin`, pushes, and watches the first CI run. Nothing is
pushed without the owner's go-ahead. Designs the owner wants to share move from `my_designs/` (git-ignored) to
`examples/<name>/` with README, screenshot and brief.

### Phase 5: what next
Offer the next steps from the roadmap's "not covered yet" list, one at a time: a design from a **hand-drawn
sketch or photo** (`sketch-to-design`: the owner photographs a napkin sketch with dimensions, you read it back as a
spec first); a second part that must **fit** the first (assemblies: components and joints, which the helpers do
not wrap yet); text and emboss; threads; the **Electronics** workspace (`fusion-electronics`: research first, probe
the API, record facts before using them). Each of these is new ground for this blueprint: research it, put the
facts in the reference with their sources before using them, and land what you learn as a procedure, an example
and a skill update (CLAUDE.md rule 10). An object worth keeping becomes the next example (`build-example`): that is
how this blueprint grows, one verified example at a time, each teaching the skills something new.

### Graduation
When the owner says they are done: their design builds from its script in one run, the numbers match the spec,
the screenshot looks right, it is exported, and (ideally) it was printed and fits; and they can explain in their
own words what a parameter is, why the script starts from `new_design`, and what the clearance in their design is
for (ask them: this is the real test). Say so and congratulate them.

**Then offer to make the repository theirs** (optional, one at a time): replace the blueprint's `README.md` with a
short one for *their* designs (what they are, how to run them, a link to `docs/`); keep or change `LICENSE` (MIT
came with the blueprint); keep the remote `blueprint` if they want future improvements (`check_updates.py` uses it).

## When you finish a phase

Tick the boxes in [docs/journey_checklist.md](../../../docs/journey_checklist.md), commit with a message that says
what and why, and tell the owner in two lines: what works now, and what the next phase is. Never end a turn with
"starting now" and nothing done.
