"""06_sketched_box: an open-top tray read from the owner's paper sketch (media/brief.jpg).
Spec v1, agreed in chat on 2026-10-27: outer 100 x 80 x 27 mm, open top, 2 mm walls and floor,
4 x dia 6 mm through-holes in the floor with centres 10 mm from the outer edges, sharp corners.
All dimensions in mm. Run:  python scripts\\fusion.py run examples\\06_sketched_box\\design.py
Change `length`, `width`, `height`, `wall`, `hole_d` in Modify > Change Parameters and the tray
follows; the hole positions are numbers computed from the parameters when the script runs.
"""

d, r = new_design("SketchedBox")

# ---- parameters: every number written on the sketch, plus one GUESS ----
add_param("length", "100 mm", "mm", "outer length (the 100 on the sketch)")
add_param("width", "80 mm", "mm", "outer width (the 80)")
add_param("height", "27 mm", "mm", "outer height (the 27)")
add_param("wall", "2 mm", "mm", "wall and floor thickness ('2mm thick')")
add_param("hole_d", "6 mm", "mm", "hole diameter ('4 holes 6 mm')")
add_param("hole_inset", "10 mm", "mm", "hole centre to outer edge (GUESS: not on the sketch)")

# ---- tray: box extruded from the floor plane, then shelled open from the top ----
sk = sketch_on("xy", name="outline")
prect(sk, "length", "width")
tray = extrude(sk, "height", "new").bodies.item(0)
tray.name = "Tray"
shell(tray, top_face(tray), "wall")

# ---- four floor holes: sketched on the underside (z = 0), cut upward through the floor ----
hx, hy, hd = eval_mm("length/2 - hole_inset"), eval_mm("width/2 - hole_inset"), eval_mm("hole_d")
sk2 = sketch_on("xy", name="floor holes")
for sx in (-1, 1):
    for sy in (-1, 1):
        circle(sk2, sx * hx, sy * hy, hd)
extrude(sk2, "wall", "cut", toward=(0, 0, 1))

set_appearance_color(tray, 40, 120, 200)

fit()
result = {"doc": active_doc_name(), "bodies": body_info(), "params": params()}
