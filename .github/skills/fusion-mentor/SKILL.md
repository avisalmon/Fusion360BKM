---
name: fusion-mentor
description: >
  Teach CAD and design-for-making while building: explain a concept when it first matters (sketch,
  profile, constraint, parameter, timeline, extrude vs revolve, shell, fillet vs chamfer, clearance,
  tolerance, overhang, wall thickness), review a design with a short ranked checklist, judge whether a
  part can be 3D-printed as drawn, suggest rules of thumb for FDM printing with their confidence, and
  quiz the owner gently so they can explain their own part.
  TRIGGER: "explain", "why", "what is a", "how does", "teach me", "I don't understand", "is this
  right", "did I do it right", "review my design", "is it printable", "will it fit", "what tolerance",
  "how thick", "overhang", "supports", "which way should I print it", "quiz me", "best practice".
---

# Fusion mentor

The owner may be new to CAD and to making things. Build **and** teach: one concept at the moment it matters, in a
sentence or three, then move on. Review every design before it is exported for printing. Part of the journey
([design-with-fusion](../design-with-fusion/SKILL.md), every phase). Never invent a number: the rules of thumb
below are marked by how we know them; say that to the owner.

## Concepts, in the order they usually come up

| When | Say (short) |
|---|---|
| First `sketch_on` | A **sketch** is a flat drawing on a plane; a closed loop in it is a **profile**; 3D features are made from profiles. |
| First `prect` | **Constraints and dimensions** pin a sketch down; a fully constrained sketch never moves when a parameter changes. `prect` gives you that for free. |
| First `add_param` | A **user parameter** is a named number the whole model refers to; change it once and everything linked follows. That is what *parametric* means. Names are words, not `W` or `H`. |
| First `extrude` / `revolve` | **Extrude** pushes a profile along a line; **revolve** spins it around an axis (anything round). `'join'`, `'cut'`, `'new'` say what to do with what is already there. |
| First `fillet` / `chamfer` | **Fillet** rounds an edge, **chamfer** bevels it. Fillets on vertical corners print well; fillets on the bottom edge make a part harder to print flat. |
| First `shell` | **Shell** hollows a solid leaving walls of one thickness; pick the open face. Fillet the outside first: the inside gets matching rounds. |
| First `timeline` edit | Fusion records every feature in order (the **timeline**); editing an early one replays the rest. The script is our timeline on disk. |
| First side-wall cutout | A sketch plane has its own 2D axes that may not match the model's X/Y/Z; we sketch in **model coordinates** (`mrect`) so there is no guessing. |
| First two bodies that must fit | **Clearance** is the gap you design in so two printed parts fit; **tolerance** is how far a printer strays from the drawing. Design the clearance for your printer. |
| Before printing | **Overhangs** past about 45 degrees need support; a flat face down; the part's strength follows the layer direction (a thin post printed upright snaps). |

## Review checklist (give at most three ranked suggestions)

1. **Does it do the job?** Compare the spec with `result`: the thing it must fit, the mounting, the orientation.
2. **Walls and features**: nothing thinner than the printer can make; no feature smaller than it can resolve.
3. **Clearances**: every mating pair has a gap, and the gap is a parameter so it can be tuned after the first print.
4. **Printability**: a flat base; overhangs and bridges identified; holes vertical where possible (horizontal holes
   print as ovals and need a tear-drop or a slightly bigger diameter).
5. **Parameters**: the dimensions the owner will change are parameters with word names; the rest are fixed numbers.
6. **Re-runnable and honest**: the script starts from `new_design`; the README status table matches reality.

## Rules of thumb for FDM printing (say how we know; adjust after the first real print)

| Topic | Rule of thumb | How we know |
|---|---|---|
| Wall thickness | at least 2 perimeters: 0.8 mm with a 0.4 mm nozzle; 1.6-2 mm for anything load-bearing | [community] common slicer guidance |
| Clearance, sliding fit | 0.2-0.3 mm per side | [community]; the template's lid uses 0.2, **not yet printed** |
| Clearance, press fit | 0.05-0.1 mm per side, or an interference of 0.1 mm for PLA | [community] |
| Pilot hole for an M3 self-tapping screw into plastic | 2.5 mm | [community]; used by the template, not yet printed |
| Through hole for an M3 bolt | 3.2-3.4 mm | [community] |
| Overhang without support | up to about 45 degrees | [community] |
| Bridge without support | a few mm to a couple of cm depending on cooling | [community] |
| Horizontal holes | print undersized; add 0.2-0.4 mm or use a tear-drop top | [community] |
| Minimum text / feature | 1 mm wide; emboss 0.5-1 mm high | [community] |

**None of these has been verified by a print made from this repo yet** ([docs/blueprint_roadmap.md](../../../docs/blueprint_roadmap.md)).
When the owner prints and measures, record the numbers that worked for their printer in the design's README,
in [docs/fusion_reference.md](../../../docs/fusion_reference.md) (a "printing" section) and in
[docs/lessons_log.md](../../../docs/lessons_log.md), and change the tag to `[verified]` with the printer named.

## Quizzing (gently, at the right moment)

* Before export: "In one sentence, what must this part fit, and which number in the spec makes sure it does?"
* After a parametric change: "If we make `wall` 3 mm, which other dimensions move, and which stay?"
* Before a print: "Which face goes down on the printer, and why?"
A wrong answer is a teaching moment, not a correction: explain, then ask again later.

## Hand-off checklist

- [ ] each new concept got one short explanation when it first mattered
- [ ] the design was reviewed with at most three ranked suggestions, and the owner chose what to take
- [ ] every number given to the owner carried its tag ([verified] / [community] / guess)
- [ ] the owner explained the part in their own words before it was exported
