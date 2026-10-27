# examples: the catalogue (stage 4)

Every example is an object designed **from the chat** through the bridge, verified, and written up so you can
rebuild it, open it, and see exactly what was checked. The first ones mirror Avi Salmon's by-hand Fusion 360 course
on Babook (stage 2, Hebrew video lessons: https://babook.co.il/courses/fusion360/): watch the lesson, then see the
same object as a script. Pages with pictures: [examples/index.html](index.html) (also on GitHub Pages).

Each example has the same shape (checked by `tests/test_examples.py`):

```text
examples/NN_name/
  design.py       builds it: python scripts\fusion.py run examples\NN_name\design.py
  README.md       what it is, the lesson it mirrors, parameters, status table with evidence
  index.html      the page: screenshots, the script explained, what was verified, what it taught this repo
  media/          screenshots from Fusion (and brief.jpg when it started from a sketch or photo)
  <name>.f3d      the Fusion archive of the finished design (committed; open it without the bridge)
```

An example is listed as **verified** only after it was built in Fusion through the bridge, its `result` matched the
spec, and the screenshot was looked at; the page says when, in which Fusion version. Half-done designs live in
`my_designs/` (git-ignored). Building the next one is the `build-example` skill.

## Catalogue

| # | Example | Mirrors | Teaches | Status |
|---|---|---|---|---|
| 01 | `01_coin` a coin with a rim and raised text | Babook lesson 2 (installation and a coin) | sketch on XY, circle, extrude, a rim by a second extrude, text/emboss (helper to write) | to do (next) |
| 02 | `02_tweezers` | Babook lesson 3 | a thin profile, extrude, mirror, taper; the thickness as a parameter | to do |
| 03 | `03_key` | Babook lesson 4 | a profile with cuts, a pattern of teeth, a hole in the bow, fillets | to do |
| 04 | `04_vacuum_nozzle` | Babook lesson 5 | round to rectangle: `loft` (helper to write), shell, a fit on a real hose diameter | to do |
| 05 | `05_mug` | Babook lesson 6 | revolve, a handle by `sweep` along a path (helper to write), shell, fillets | to do |
| | *then the owner's ideas: an enclosure for a real board, a phone stand, a part from a hand-drawn sketch* | | | |

The starting point for your own design is not an example but the template:
[templates/parametric_box](../templates/parametric_box/README.md) (built, checked by numbers and by eye;
`fusion.py new <name>` copies it).
