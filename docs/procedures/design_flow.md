# Procedure: from words (or a sketch) to a verified part

Owners: the `sketch-to-design` and `fusion-modeling` skills. The template this follows:
[templates/parametric_box/design.py](../../templates/parametric_box/design.py).

## 1. Listen, then write the spec

Ask a few questions at a time: what is it for, what must it fit (real measurements), where it sits, which way is up,
how it is printed, what should stay adjustable. A hand-drawn sketch or photo: read it back (views, every number and
its unit, shapes and relations, what is missing) before anything else.

Write the spec, in mm, numbered, in `my_designs/<name>/README.md`:

```text
Spec: <name> (v1)
Fits: <the real thing, measured>
1. <dim> = <value> mm (param | fixed)  <what it is for>   [GUESS when not given]
...
Up: <which face is down, which way it faces>
Not in v1: <what is left out on purpose>
```

Get an explicit OK. The spec is what `result` and the screenshot are checked against.

## 2. Start the design

```powershell
python scripts\fusion.py new <name>          # lowercase letters, digits, _ ; starts with a letter
```

Copies the template to `my_designs/<name>/design.py` (with `new_design('<Name>')` renamed) and writes a README with
a status table. Replace the template's body with the spec's, step by step.

## 3. Build in steps; verify after each

A script's shape:

```python
# 1. parameters (word names; what the owner will change)
add_param("width", "80 mm", comment="outer width")
# 2. the main body: a dimensioned sketch and an extrude
sk = sketch_on("xy", name="base")
prect(sk, "width", "depth")  # strings = expressions linked to parameters
base = extrude(sk, "height", op="new")
# 3. features, one at a time
fillet_all(base, 3, predicate=lambda e: ...)  # numbers = one-off mm
...
# 4. what a run proves
fit()
result = body_info()
```

After every `python scripts\fusion.py run my_designs\<name>\design.py`:

1. **Numbers**: `result` lists each body with its bounding box (mm) and volume (cm3), and the parameters. Compare
   with the spec line by line. A box 80 x 50 x 25 that reports 80 x 50 x 24.8 is wrong, not "close".
2. **Eye**: `python scripts\fusion.py shot exports\<name>.png`, read the image, say what you see, including what is
   wrong (a cut that went the wrong way, a feature missing, a fillet on the wrong edges). Same view as the sketch
   when there was one (camera recipe in [files_and_export.md](files_and_export.md)).
3. Only then say it is done, and move to the next feature.

Rules while building:

* Scripts start from `new_design(...)` (or `clear_design()`): re-runnable, never dependent on what is on screen.
  `close_all_untitled()` at the top of a run tidies previous tabs.
* Side-wall features: sketch in **model coordinates** (`mpt`, `mrect`, `mcircle`) and extrude with `toward=`;
  never guess a sketch plane's axes (gotcha 7).
* Fillet before shell when the inside should follow the outside; fillet only the vertical edges of a part that
  will print flat (a `predicate` on the edge's direction).
* Two bodies that must stay separate: build the second beside the first (the template's lid), or `op='new'`.
* A parameter name that fails with `param name is not valid` is a unit symbol: use a word.
* One failing feature at a time: comment the rest out, run, read the traceback (the bridge returns it), fix, uncomment.

## 4. Review, then export

`fusion-mentor` checklist (at most three ranked suggestions): does it do the job; walls and features vs the printer;
clearances as parameters; printability (flat base, overhangs, horizontal holes); parameters named; re-runnable and
honest. Then [files_and_export.md](files_and_export.md): `python scripts\fusion.py export <name>`.

## 5. Record

The design's README status table, with how each row was checked:

| Step | Done | How |
|---|---|---|
| Built in Fusion by `design.py` | x | `fusion.py run`, 2026-10-27, Fusion 2706.1.14 |
| Checked by numbers | x | `result`: Base 80 x 50 x 25 mm, 8 parameters |
| Checked by eye | x | `exports/<name>.png` read: ... |
| Exported | x | `exports/<name>.stl` / `.step` / `.f3d` |
| Printed and measured | | not yet |

Tick only what was done and seen. Then commit (push on the owner's word).
