# What we learned, by date

The short version of every lesson in this blueprint, newest first, so you can see what changed since you last looked.
Each line points to where the full rule lives. Most of them came from something going wrong, or from checking an
assumption against a running Fusion and finding it was not quite true.

## 2026-10-27

- **CI was green on the first push because it runs nothing new.** The four commands in `ci.yml` are the same four
  run here before committing (`ruff check`, `ruff format --check`, `pytest -q`, `sync_skills.py --check`), on the
  same Python. The one difference, gitleaks over the whole history, is approximated locally by the staged-secrets
  check.
  [ci.yml](../.github/workflows/ci.yml) · [publish-to-github](../.claude/skills/publish-to-github/SKILL.md)
- **`ruff format` reaches into Markdown.** Ruff 0.17 formats the Python code blocks inside `.md` files too, and it
  turns single quotes into double. That silently changed the template, and `fusion.py new` matched
  `new_design('ParametricBox')` with single quotes only: the rename would have stopped working without an error. The
  renamer and the tests now accept either quote style. Rule: after a formatter runs, re-run the tests, not just the
  linter. [test_templates.py](../tests/test_templates.py) · [fusion.py](../scripts/fusion.py)
- **Closing Fusion from the chat, without a save prompt.** `close_all_untitled()` through the bridge first, then a
  graceful close of the main window by process id, then `fusion.py launch`; the bridge answered 35 s after a cold
  start and the add-in loaded from the new folder. [gotcha 10](procedures/gotchas.md) ·
  [install_bridge.md](procedures/install_bridge.md)
- **The system Python was too new for the tooling.** Python 3.15 could not build `pyyaml` for `pre-commit`; the
  `env/` is made with `py -3.12`, the same version CI uses. [get_started.md](get_started.md)
- **The blueprint has four stages, and the examples mirror a course.** Set up (the human) → learn by hand (Babook's
  Fusion 360 course, in Hebrew, seven video lessons) → the AI magic → examples. The example series follows the course's
  objects (coin, tweezers, key, vacuum nozzle, mug) so a learner can watch an object being made by hand and then read
  the same object as a script. [README.md](../README.md) · [examples/README.md](../examples/README.md) ·
  [build-example](../.claude/skills/build-example/SKILL.md)
- **A folder with a running session in it cannot be renamed.** Windows refused to rename `Fusuin360` to
  `Fusion360BKM` while the app session's shell had it as its working directory. The answer was a `robocopy` copy, a
  re-pointed AddIns junction (`fusion.py install`), and a pointer left in the old folder for the session to finish
  with. [gotcha 13](procedures/gotchas.md)
- **A junction, not a copy, is how the add-in is installed.** Fusion loads from
  `%APPDATA%\...\API\AddIns\CopilotBridge`, which is a `mklink /J` junction into the repo, so an edit to
  `bridge_helpers.py` is live on the next call. The cost: Fusion lists the add-in twice and two servers fought for the
  port until a singleton guard was added. [gotcha 5](procedures/gotchas.md) ·
  [install_bridge.md](procedures/install_bridge.md)
- **Every Fusion fact in the reference is tagged.** `[verified]` (seen on Fusion 2706.1.14 here), `[community]` or
  `[unverified]`; the helpers' signatures were read from `bridge_helpers.py`, not remembered.
  [fusion_reference.md](fusion_reference.md)
- **`doctor` is the setup procedure.** The install page quotes `fusion.py`'s own messages row by row, so what you read
  is what the tool prints; nothing is paraphrased. [install_bridge.md](procedures/install_bridge.md)
- **Verify by numbers, then by eye, after every run.** `result` carries bounding boxes in mm and volumes in cm3 for
  each body; a screenshot is read and described, including what is wrong. "It ran" is not "it is right".
  [design_flow.md](procedures/design_flow.md) · [CLAUDE.md](../CLAUDE.md)

## 2026-10-26

- **Fusion must be running; the bridge is not an MCP.** The add-in runs an HTTP server inside Fusion
  (`127.0.0.1:8787`) and hands each script to Fusion's main thread through a custom event; a modal dialog blocks
  everything until somebody clicks it. A thin MCP wrapper over the same HTTP calls is possible later.
  [architecture.md](architecture.md) · [gotcha 1](procedures/gotchas.md)
- **Fusion's API counts in centimetres.** Every helper takes millimetres and multiplies by `MM = 0.1`; a script never
  calls `adsk` lengths directly. [gotcha 4](procedures/gotchas.md)
- **Sketch axes on a side plane are not what you guess.** On the YZ plane, sketch X is model −Z and sketch Y is
  model +Y (Z-up). Side features are sketched in model coordinates (`mpt`, `mrect`, `mcircle`) and extruded with
  `toward=`. [gotcha 7](procedures/gotchas.md) · [fusion_reference.md](fusion_reference.md)
- **Some parameter names are unit symbols.** `W`, `H`, `A`, `V`, `F`, `m`, `s` fail with `param name is not valid`;
  word names always work. [gotcha 6](procedures/gotchas.md)
- **The launcher runs the updater first.** A Fusion update took about twelve minutes and looked like a hang; the
  *Active Sessions Exceeded* dialog (the same account open elsewhere) is answered with `fusion_dialog.ps1 -Select
  'Suspend*' -Click Continue`. [gotcha 2](procedures/gotchas.md) · [gotcha 3](procedures/gotchas.md)
- **Saving to the cloud from the API did not work here; `export_f3d` does.** The design, timeline and parameters go
  to disk as an `.f3d`; examples commit theirs. [gotcha 9](procedures/gotchas.md) ·
  [files_and_export.md](procedures/files_and_export.md)
- **Open and import work: `.f3d`, STEP, and STL as a mesh body.** Verified with the import manager and
  `meshBodies.add`; IGES, SAT, DXF, SVG, OBJ and 3MF are untried. [files_and_export.md](procedures/files_and_export.md)
- **Editing the timeline from a script works.** A feature's extent can be changed after the fact
  (`timeline.item(i).entity.extentOne.distance.expression`), so an opened design can be adjusted, not only rebuilt.
  [fusion_reference.md](fusion_reference.md)
