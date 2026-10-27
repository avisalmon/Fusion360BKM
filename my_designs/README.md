# my_designs - your own parts (not committed)

`python scripts\fusion.py new <name>` creates `my_designs\<name>\design.py` and `README.md` from
`templates\parametric_box`. Everything in this folder except this file is git-ignored, so you can
experiment freely; nothing leaves your computer unless you copy a finished design to `examples/`.

Typical loop (all from chat):

1. say what you want in words, or point at a sketch / photo (`sketch-to-design` skill)
2. the assistant writes or edits `design.py`, then `python scripts\fusion.py run my_designs\<name>\design.py`
3. it checks the result by numbers (`fusion.py info`) and by eye (`fusion.py shot`) and tells you
   what it saw - including what is wrong
4. iterate; when happy: `python scripts\fusion.py export <name>` writes STL/STEP/F3D to `exports\`
5. tick the status table in the design's README with real evidence
