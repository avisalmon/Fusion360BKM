---
name: build-example
description: >
  (Maintainer) Build the next example of this blueprint in examples/NN_name/: agree the object with Avi
  first (the Babook course's objects come first: coin, tweezers, key, vacuum nozzle, mug; then the owner's
  ideas), write the spec, the design.py built through the bridge and verified by numbers and screenshots,
  the README and the HTML page, the media, the .f3d archive, the badge that says exactly what was verified,
  the catalogue card, and then the part that matters most: what the example taught the skills, the
  reference, the gotchas and the helpers. One example at a time; nothing claimed that was not seen.
  TRIGGER: "build example", "next example", "new example", "add an example", "example 2", "the coin",
  "the tweezers", "the key", "the mug", "the nozzle", "practice series", "let's practice", "add it to the
  catalogue", "make this an example", "promote to examples".
---

# Build an example (maintainer)

The examples are stage 4 of this blueprint and the way it learns: every example is an object built **from the chat**
through the bridge, verified, and written up so a reader can rebuild it, open it, and see exactly what was
checked. The first ones mirror Avi Salmon's Babook course (https://babook.co.il/courses/fusion360/): lesson 2 the
coin, 3 the tweezers, 4 the key, 5 the vacuum nozzle, 6 the mug, so a learner who watched the by-hand lesson sees
the same object as a script. After those, the owner's own ideas (an enclosure for a real board, a phone stand, a part
from a hand-drawn sketch). Coaching an owner through *their* design is `design-with-fusion`; this skill is for the
blueprint's own catalogue.

## Agree it first (one example at a time)

Before writing anything: say which object, what its spec will be (dimensions in mm, which are parameters), which
helpers it needs and **which of those do not exist yet** (`loft`, `sweep`, text and emboss, threads, joints are not
wrapped: see [docs/fusion_reference.md](../../../docs/fusion_reference.md)), and what the example is meant to teach.
Avi says go. A missing helper is part of the example's work: write it in `bridge_helpers.py` with its test, probe
the API in the running Fusion first (CLAUDE.md rule 3), record the facts.

## The files (tests/test_examples.py checks them)

```text
examples/NN_slug/
  design.py        starts with new_design('<Name>'), mm everywhere, add_param with word names, ends with
                   result = {...} (bodies, bounding boxes, volumes, parameters) so a run proves itself
  README.md        title; the Babook lesson it mirrors (if any); what it teaches; parameters table; how to run;
                   status table (built / numbers / eye / exported / printed, each with its evidence and date)
  index.html       the page (same shape as the DE10-Lite examples): crumbs, lead, badges, download of the .f3d,
                   "What you will see" with the screenshot(s), the script explained step by step, the parameters,
                   "What was verified", "What it taught this blueprint" (the lessons, gotchas, helpers it added)
  media/           screenshots from `fusion.py shot` (PNG; one straight-on, one from the top or a section when
                   it helps); brief.jpg when the object started from a sketch or photo
  <slug>.f3d       the archive exported from the finished design (`export_f3d`), committed: the .gitignore allows
                   .f3d inside examples/ only. STL/STEP are not committed (fusion.py export rebuilds them).
```

The catalogue: a row in [examples/README.md](../../../examples/README.md) and a card in
[examples/index.html](../../../examples/index.html) with the badge text. The start page ([index.html](../../../index.html))
lists the examples under stage 4.

Numbering: two digits, in build order; the slug is lowercase letters, digits and `_`, same as `fusion.py new`.

## The build (every step through the chat; that is the point)

1. **Spec** (`sketch-to-design` method): a numbered list of dimensions in mm, parameters named, up-direction stated.
   For a course object, read the lesson's description and keep the object recognisably the same; dimensions may be
   our own, say so.
2. **Script** in steps (`fusion-modeling`): main body, `fusion.py run`, compare `result` with the spec, `shot`, look;
   then each feature. Keep the script readable: a comment line per feature saying what and why; it is teaching
   material.
3. **Verify and record**: the final `result` and the screenshots go into README and page. Every claim on the page has
   its evidence: a number from `result`, a screenshot, a date and the Fusion version from `fusion.py ping`.
4. **Archive**: `export_f3d(r'<abs path>\examples\NN_slug\<slug>.f3d')` from the finished design; re-open it once
   (`fusion-files`) to prove the archive is good, then close it.
5. **Page and card**: build `index.html` from the previous example's page (keep its head, crumbs, footer and
   `../example.css`); replace every string; no leftover previous-example text (grep for it). Badge text is literal
   about what was checked: `Built in Fusion 2706 2026-10-27, checked by numbers and by eye` or adds `printed in PLA`
   only when true.
6. **What it taught**: the real deliverable. Write into the example page *and* into the repo: a new helper (with
   test), a reference fact with its tag, a gotcha row (never renumber), a skill update (`fusion-modeling` recipe,
   `fusion-mentor` concept), a line in [docs/lessons_log.md](../../../docs/lessons_log.md), a roadmap line moved
   from "not yet" to "verified here". An example that taught nothing was probably too close to the last one.
7. **Checks**: `pytest -q`, `ruff check .`, `python scripts/sync_skills.py --check`; `fusion.py run` of the committed
   `design.py` one last time from a clean `new_design`. Commit (push on Avi's word).

## Rules

* Nothing in a page that was not seen: no "prints well" without a print, no "fits" without a measurement.
* The screenshot must show the object the way a reader would recognise it (a `fit()` and a sensible camera;
  `fusion-files` has the camera recipe).
* Keep the examples independent: each `design.py` runs alone from `new_design`; shared code goes into
  `bridge_helpers.py`, never into one example importing another.
* The Babook course is the by-hand path; link the lesson, do not re-teach it. Our page explains the *script*.

## Hand-off checklist

- [ ] object, spec, missing helpers and purpose agreed with Avi before building
- [ ] `design.py` runs from `new_design` and `result` matches the spec; screenshots read and described
- [ ] README status table, page badges and catalogue card say exactly what was verified, with dates
- [ ] `.f3d` archive committed and re-opened once
- [ ] what it taught landed in a helper/test, the reference, the gotchas, a skill and the lessons log
- [ ] pytest, ruff and sync check green; committed
