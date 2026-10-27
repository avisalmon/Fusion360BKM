---
name: fusion-modeling
description: >
  Build and change 3D geometry in the running Fusion from a script: the mm-based helper API in
  bridge_helpers.py (new_design, add_param, sketch_on, prect, circle, mrect, extrude, revolve, fillet_all,
  chamfer_all, shell, top_face, hole_at, combine, patterns, mirror, set_param, body_info), parametric
  expressions, model-space sketching on side planes, re-runnable scripts, editing an existing design
  through parameters and the timeline, and the verify-by-numbers-then-screenshot loop after every run.
  TRIGGER: "extrude", "revolve", "fillet", "chamfer", "shell", "hole", "pattern", "mirror", "sketch",
  "make it taller", "make it 5 mm wider", "change the wall", "add a cutout", "add standoffs", "round the
  corners", "hollow it", "parameter", "change parameters", "edit the design", "timeline", "the script
  failed", "wrong axis", "it extruded the wrong way", "param name is not valid", "body_info".
---

# Fusion modeling from a script

Scripts are plain Python run **inside Fusion** by the bridge (`python scripts/fusion.py run <file>`), with the
helpers from [CopilotBridge/bridge_helpers.py](../../../CopilotBridge/bridge_helpers.py) already in scope, plus
`adsk`, `app`, `ui` for the raw API. The whole helper list with signatures and every verified fact is in
[docs/fusion_reference.md](../../../docs/fusion_reference.md); the method is
[docs/procedures/design_flow.md](../../../docs/procedures/design_flow.md). Part of the journey
([design-with-fusion](../design-with-fusion/SKILL.md), Phases 1-2).

## Rules

1. **mm in, mm out.** Fusion's API is in cm; the helpers convert. Touch the raw API only with `P(x, y, z)`,
   `V(...)`, `mm(x)` or `* MM` (0.1). Volumes in `body_info()` are cm3; bounding boxes are mm.
2. **Numbers are one-off, strings are parametric.** `extrude(sk, 12)` is 12 mm forever; `extrude(sk, 'height')` or
   `'wall + 1 mm'` follows the user parameters. Anything the owner may want to change later: `add_param` first,
   then strings. `prect(sk, 'length', 'width', cy='width + lid_gap')` keeps even the layout parametric.
3. **Parameter names are words**, never a unit symbol: `W`, `H`, `A`, `V`, `F`, `m`, `s` ... raise
   `param name is not valid` [verified]. Use `width`, `height`, `wall`.
4. **Re-runnable.** Every design script starts with `d, r = new_design('Name')` (a fresh document each run) or
   `clear_design()` and never assumes what is on screen. `close_all_untitled()` cleans up after failed runs.
5. **Side planes: think in model space.** On the XZ and YZ planes the sketch axes are not what you'd guess (YZ:
   sketch X = model -Z, sketch Y = model +Y, observed with Z-up [verified]). Don't guess: use `mrect(sk, (x,y,z),
   (x,y,z))`, `mcircle(sk, (x,y,z), d)`, `mpt(sk, x, y, z)` with real model coordinates, and
   `extrude(sk, dist, 'cut', toward=(1, 0, 0))` to say which way it must go.
6. **Verify by numbers, then by eye** (CLAUDE.md rule 4). End every script with
   `result = {'bodies': body_info(), 'params': params()}`; after the run compare bounding boxes and body count with
   the spec, then `python scripts/fusion.py shot exports/<name>.png` and read the image. Say what you see.
7. **Build in steps.** Main body first, run, check; then one feature at a time. When a step fails, the traceback
   names the line; fix that line, re-run the whole script (rule 4 makes that cheap).
8. **Separate bodies stay separate.** `'join'` fuses into whatever it touches; build a lid or a second part offset
   from the first (the template uses `cy='width + lid_gap'`) and name bodies (`body.name = 'Lid'`).

## The shape of a script

```python
d, r = new_design("Bracket")  # (design, rootComponent)
add_param("width", "40 mm", "mm", "overall width")
add_param("thick", "5 mm")
sk = sketch_on(
    "xy", name="outline"
)  # 'xy' | 'xz' | 'yz' | a BRepFace | a ConstructionPlane, offset_mm=...
prect(sk, "width", "20 mm")  # centred, fully constrained, parametric
circle(sk, 0, 0, 6)  # centre (mm), diameter (mm); inner profile -> a hole after extrude
body = extrude(sk, "thick", "new").bodies.item(
    0
)  # 'new' | 'join' | 'cut' | 'intersect' | 'component'
body.name = "Bracket"
fillet_all(
    body,
    1.5,
    lambda e: (
        abs(e.geometry.startPoint.z - e.geometry.endPoint.z) > 1e-6
        if e.geometry.objectType == adsk.core.Line3D.classType()
        else False
    ),
)  # vertical edges only
sk2 = sketch_on("yz", name="side slot")
mrect(sk2, (0, -5, 1), (0, 5, 4))  # model-space corners
extrude(sk2, "width/2 + 1 mm", "cut", toward=(1, 0, 0))
fit()
result = {"doc": active_doc_name(), "bodies": body_info(), "params": params()}
```

`extrude(sk)` uses **all** profiles of the sketch; pass one profile (`items(sk.profiles)[0]`) or a list to choose
(sort by `p.areaProperties().area` to pick the ring between two rectangles, as the template's lip does).

## Recipes (all verified on Fusion 2706 unless tagged)

| Want | Do |
|---|---|
| Rounded box, hollow from the top | `prect` -> `extrude 'new'` -> `fillet_all(body, 'corner_r', vertical-edge predicate)` -> `shell(body, top_face(body), 'wall')` |
| Standoffs on the floor | `sketch_on('xy', offset_mm='wall')`, `circle` x4, `extrude(sk, h, 'join')`; pilot holes: another sketch at `offset_mm=f'wall + {h} mm'`, `extrude(sk, -(h - 0.8), 'cut')` |
| Slot or port in a side wall | `sketch_on('yz')` / `'xz'`, `mrect` with model coords, `extrude(..., 'cut', toward=(±1,0,0))` with a distance past the wall (`'length/2 + 1 mm'`) |
| Knob, cap, bushing | profile on `'xz'` with `rect`, `revolve(sk, 'z', 360)`; axis = `'x'|'y'|'z'`, a SketchLine or a ConstructionAxis |
| Hole on a face | `hole_at(face, x, y, d, depth=None)` (depth None = through all; x,y in that face's sketch space) |
| Regular pattern | `pattern_rect(feature_or_body, nx, dx_mm, ny, dy_mm)`, `pattern_circular(..., 'z', count)` |
| Mirror half a part | `mirror_body(body, 'yz')` |
| Boolean | `combine(target, tools, 'join'|'cut'|'intersect', keep_tools=False)` |
| Move a body | `move_body(body, dx, dy, dz)` (mm) |
| Colour bodies apart in screenshots | `set_appearance_color(body, r, g, b)` |
| Change a dimension on the existing design | `set_param('length', '120 mm')` (no re-run needed), then `fit(); body_info()` |
| Edit a feature in the timeline | `tl = design().timeline; f = tl.item(i).entity; f.extentOne.distance.expression = '12 mm'`; `f.isSuppressed = True`; `f.deleteMe()` |
| Evaluate an expression | `eval_mm('width - 2*wall')` -> float mm |
| Components (assemblies) | `new_component('Lid')` then pass `comp=` to `sketch_on`/`extrude`; joints: raw API only, no helper yet [unverified] |
| Threads, text/emboss, sweeps, lofts, drawings | raw `adsk.fusion` API; not tried here yet [unverified]: probe, then add a helper and a reference row |

## When it goes wrong

* **`param name is not valid`**: a unit-symbol name (rule 3).
* **Extrude went the wrong way / cut nothing**: side-plane axes (rule 5). Add `toward=`; check with `sketch_normal(sk)`.
* **Shell failed**: the opening face was not found (`top_face` picks the planar face with the highest centroid on
  that axis; use `'-z'` or `'x'`), or the wall is thicker than a feature.
* **Fillet failed**: radius too large for a neighbouring edge, or the predicate matched a non-line edge. Fillet
  before shell (bigger radii work) or filter edges.
* **`join` swallowed my second body**: it touched the first (rule 8).
* **Nothing came back, `Timed out ... main thread`**: a dialog, not your script: `setup-fusion-bridge`.
* **`_helpers_error` in the result**: `bridge_helpers.py` has a syntax error (it is reloaded on every call); fix
  it and re-run, no restart needed. Changes to `CopilotBridge.py` **do** need a Fusion restart.

## Hand-off checklist (before you say "done")

- [ ] the script re-runs clean from `new_design`
- [ ] `result` body count and bounding boxes match the spec, in mm
- [ ] the screenshot was taken and read; what it shows is described, including anything off
- [ ] dimensions the owner may change are user parameters with word names
- [ ] a new fact or recipe learned went into the reference / this skill
