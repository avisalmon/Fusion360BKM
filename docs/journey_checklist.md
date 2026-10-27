# The journey, as a checklist

The chat (the `design-with-fusion` skill) orients from this file at every session and ticks boxes as things get done.
**Assistant** = the chat does it; **You** = only a human can. Stage 1 (install Fusion, VS Code, Git, the chat, clone)
is in [get_started.md](get_started.md); stage 2 (the Babook course) is optional and outside this repo.

## Phase 0: the tools and the bridge

- [ ] **Assistant**: `python scripts/check_updates.py` ran (or `git fetch --all` + `git pull --ff-only` before Python)
- [ ] **Assistant**: `env/` created and `requirements-dev.txt` installed
- [ ] **Assistant**: `python scripts/fusion.py doctor` run and the table shown to the owner
- [ ] **You**: Fusion installed and signed in (`doctor` row "Fusion installed" OK)
- [ ] **Assistant**: `python scripts/fusion.py install` linked `CopilotBridge/` into Fusion's AddIns folder
- [ ] **You**: Fusion restarted once after the link (the add-in loads at start-up)
- [ ] **Assistant**: `doctor` ends with `Everything needed is in place.` and `fusion.py ping` prints Fusion's version

## Phase 1: the template built and seen

- [ ] **Assistant**: `fusion.py run templates\parametric_box\design.py`: `result` shows `Base` 80 x 50 x 25 mm, `Lid`, eight parameters
- [ ] **Assistant**: `fusion.py shot` taken and described to the owner; the owner agrees it looks like a box with a lid
- [ ] **Assistant**: `design.py` explained in five lines (parameters, centred rectangle, extrude, vertical fillets, shell; the lid beside the base)
- [ ] **Assistant**: `set_param('length', '120 mm')` shown with a new screenshot, then put back to `'80 mm'`
- [ ] **Assistant**: the examples catalogue shown ([../examples/README.md](../examples/README.md)); the Babook course mentioned for anyone new to Fusion

## Phase 2: the owner's first design

- [ ] **You**: said what the part is for and what it must fit (real measurements when possible)
- [ ] **Assistant**: a numbered spec in mm written (parameters named, up-direction stated, guesses marked) and the owner said OK
- [ ] **Assistant**: `fusion.py new <name>` created `my_designs/<name>/`; "What it does" written in the owner's words
- [ ] **Assistant**: main body built and checked (`result` vs spec, screenshot read)
- [ ] **Assistant**: every feature added, each run checked
- [ ] **Assistant**: reviewed with the `fusion-mentor` checklist (at most three ranked suggestions)
- [ ] **You**: explained in your own words what the part must fit and how

## Phase 3: export, print, measure

- [ ] **Assistant**: `fusion.py export <name>` wrote `exports/<name>.stl` (per body when several), `.step`, `.f3d`
- [ ] **Assistant**: told the owner which STL goes to the slicer and which face goes down
- [ ] **You**: printed it (optional) and measured the critical dimensions
- [ ] **Assistant**: the README status table filled with the evidence (built / numbers / eye / exported / printed)
- [ ] **Assistant**: real clearances that worked recorded in the README, the roadmap and the lessons log
- [ ] **Assistant**: committed

## Phase 4: the owner's own GitHub repository (optional)

- [ ] **Assistant**: `gh auth status` shows the right account with the `repo` and `workflow` scopes
- [ ] **Assistant**: commit email is the account's noreply address
- [ ] **Assistant**: the pre-push check is clean (no `env/`, `exports/`, `bridge/`, private designs, secrets)
- [ ] **You**: chose private or public
- [ ] **Assistant**: `origin` renamed `blueprint`; the owner's repository created as `origin`; pushed on the owner's word
- [ ] **Assistant**: first CI run watched to green

## Phase 5: what next (one at a time)

- [ ] A design from a hand-drawn sketch or photo (`sketch-to-design`)
- [ ] A second part that must fit the first (assemblies: components and joints; helpers to write)
- [ ] Text and emboss (the coin example)
- [ ] Loft and sweep (the nozzle and mug examples)
- [ ] Threads
- [ ] The Electronics workspace (`fusion-electronics`: research first)
- [ ] An object worth keeping promoted to `examples/` (`build-example`)

## Graduation

- [ ] The owner's design builds from its script in one run; numbers match the spec; the screenshot looks right; exported
- [ ] (Ideally) printed and it fits
- [ ] The owner can explain, in their own words: what a parameter is, why the script starts from `new_design`, what the clearance in their design is for
- [ ] Offered: make the repository theirs (own README, licence decision, keep the `blueprint` remote)
