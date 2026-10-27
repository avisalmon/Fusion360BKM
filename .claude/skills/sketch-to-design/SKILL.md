---
name: sketch-to-design
description: >
  Turn what the owner has in their head into a part Fusion can build: a verbal description, a
  hand-drawn sketch or napkin drawing photographed and attached to the chat, a photo of a real object
  with a ruler, or measurements read out loud. The method is spec-first: read the input back as a
  numbered list of dimensions in mm with purpose and parameters, resolve every ambiguity with one
  question at a time, get the owner's OK, then write the script and verify against that list. Honest
  about what is guessed.
  TRIGGER: "here is a sketch", "I drew this", "from this drawing", "from this photo", "look at this
  picture", "I'll describe it", "something like", "it should look like", "measure", "the real thing
  is", "convert this to a design", "napkin", "hand drawn", "whiteboard", "turn this into a part".
---

# Sketch to design: words, drawings and photos into a spec, then a script

The owner's input is never the script's input. Between them sits a **spec**: a short numbered list of dimensions and
features that both of you agree on. The spec is what `result` and the screenshot are checked against afterwards
(CLAUDE.md rule 4), and it is what goes into the design's README. Part of the journey
([design-with-fusion](../design-with-fusion/SKILL.md), Phase 2 and Phase 5); the method is written up in
[docs/procedures/design_flow.md](../../../docs/procedures/design_flow.md).

**Status (be honest with the owner):** the words-to-spec-to-script path has been used for the template; reading a
**hand-drawn sketch or photo** has not been practised in this blueprint yet. It is the next item in the practice
series ([docs/backlog.md](../../../docs/backlog.md)). Do it, then record what worked and what did not here.

## 1. Read the input

**Words.** Listen for: what it is for, what it must fit (the thing that drives the dimensions), where it sits and
which way is up, how it is held or mounted, what it is made of (3D print? which printer?), and what must be
adjustable later. Repeat the object back in one sentence before anything else.

**A hand-drawn sketch or photo (attached image).** You can read images. Say what you see, in order:
1. the views (one? top and side? a 3D-ish drawing?) and which way is up;
2. every number written on it, with the unit you assume (`mm` unless written otherwise; check inches!), and which
   edge each number belongs to;
3. the shapes (rectangle, circle, slot, rounded corner) and how they relate (centred? flush? offset by...);
4. what is **not** on it: a missing thickness, an unspecified radius, a hole with no size.
Never silently fill a gap: every value you did not read is a **guess** marked as such in the spec.

**A photo of a real object.** Ask for a ruler or a known object in the frame; otherwise only proportions are
readable. Ask for the key measurements with calipers (one at a time: "the outer width, please"). Perspective
distorts everything away from the centre of the photo.

## 2. Write the spec (before any code)

```
Spec: phone_stand (v1)
Fits: a phone 72 x 150 x 8 mm (measured by the owner), with a 1.5 mm case
1. base_w   = 80 mm   (param)  width of the base; 8 mm wider than the phone
2. base_d   = 70 mm   (param)  depth of the base; stability on a desk
3. slot_w   = 11 mm   (param)  phone 8 + case 2x1.5 = 11; no extra clearance yet
4. angle    = 65 deg  (param)  lean back; GUESS, owner to confirm
5. wall     = 3 mm    (param)  printed in PLA, 0.4 nozzle
6. cable notch 12 mm wide in the slot floor, centred   (fixed)
7. all vertical edges rounded r = 3 mm                 (fixed)
Up: the base lies on XY, the phone leans toward -Y
Not in v1: a second phone, cable routing out the back
```

Rules for the spec:
* **mm everywhere**; a dimension is a number plus a purpose. "GUESS" is written on anything not given.
* Say which dimensions become **user parameters** (word names, rule 5) and which are fixed details.
* Say which face is down and which direction the part faces: it decides sketch planes and printing.
* Ask **one question at a time** for the unknowns that change the geometry; defaults are fine for cosmetic ones.
* Get an explicit OK ("spec v1 OK?") before writing code; store the spec in `my_designs/<name>/README.md`
  (and the sketch/photo next to it as `brief.jpg` if the owner agrees to keep it).

## 3. Script, then verify against the spec

Hand over to `fusion-modeling`: the main body from the spec's first lines, run, check `result` (bounding box =
spec), screenshot; then each feature. Read the screenshot **against the drawing**: same view if you can
(`fusion-files` camera recipe), and say what differs. When the numbers or the picture disagree with the spec,
fix the script, not the spec; when the owner changes their mind, bump the spec to v2 in the README first.

## 4. Record

In `my_designs/<name>/README.md`: the spec, the brief (image), the status table. If the design is worth sharing,
move it to `examples/<name>/` with the brief next to it: a sketch-plus-result pair is the best teaching example
this repo can have. Put what you learned about reading drawings into this skill and
[docs/lessons_log.md](../../../docs/lessons_log.md).

## Hand-off checklist

- [ ] the object was repeated back in one sentence and the owner agreed
- [ ] a numbered spec in mm exists, guesses marked, parameters named, up-direction stated
- [ ] the owner said OK to the spec before the script was written
- [ ] after the build: `result` and the screenshot were compared with the spec line by line
- [ ] the brief (sketch/photo) and spec are saved with the design
