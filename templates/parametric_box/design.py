"""Template: parametric electronics enclosure (base + snap lid) built from chat.
All dimensions in mm. Run:  python scripts\\fusion.py run templates\\parametric_box\\design.py
The main dimensions are driven by user parameters (Modify > Change Parameters in Fusion):
change `length`, `width`, `height`, `wall`, `corner_r`, `lid_t`, `lip_h` and the model updates.
`python scripts\\fusion.py new <name>` copies this file to my_designs\\<name>\\design.py.
"""

d, r = new_design("ParametricBox")

# ---- parameters ----
# NB: avoid single letters like W/H - they clash with Fusion's unit symbols (watt, henry).
add_param("length", "80 mm", "mm", "outer length")
add_param("width", "50 mm", "mm", "outer width")
add_param("height", "25 mm", "mm", "base height")
add_param("wall", "2 mm", "mm", "wall thickness")
add_param("corner_r", "4 mm", "mm", "outer corner radius")
add_param("lid_t", "2 mm", "mm", "lid plate thickness")
add_param("lip_h", "3 mm", "mm", "lid lip height")
L, W, H, wall, corner_r = 80, 50, 25, 2, 4  # numeric copies for the non-parametric details

# ---- base: rounded box, shelled from the top (all parameter-driven) ----
sk = sketch_on("xy", name="base outline")
prect(sk, "length", "width")
base = extrude(sk, "height", "new").bodies.item(0)
base.name = "Base"
fillet_all(
    base,
    "corner_r",
    lambda e: (
        abs(e.geometry.startPoint.z - e.geometry.endPoint.z) > 1e-6
        if e.geometry.objectType == adsk.core.Line3D.classType()
        else False
    ),
)

top = top_face(base)
shell(base, top, "wall")

# ---- PCB standoffs with M3 pilot holes ----
pitch_x, pitch_y, standoff_d, standoff_h, pilot_d = 58, 30, 6, 5, 2.5
sk2 = sketch_on("xy", name="standoffs", offset_mm="wall")
for sx in (-1, 1):
    for sy in (-1, 1):
        circle(sk2, sx * pitch_x / 2, sy * pitch_y / 2, standoff_d)
standoffs = extrude(sk2, standoff_h, "join")
sk3 = sketch_on("xy", name="pilot holes", offset_mm=f"wall + {standoff_h} mm")
for sx in (-1, 1):
    for sy in (-1, 1):
        circle(sk3, sx * pitch_x / 2, sy * pitch_y / 2, pilot_d)
extrude(sk3, -(standoff_h - 0.8), "cut")

# ---- USB-C cutout on the +X wall (model-space coords, extrude heads to +X) ----
usb_z0 = wall + standoff_h + 1.5
sk4 = sketch_on("yz", name="usb cutout")
mrect(sk4, (0, -4.6, usb_z0), (0, 4.6, usb_z0 + 3.4))
usb = extrude(sk4, "length/2 + 1 mm", "cut", toward=(1, 0, 0))

# ---- vent slots on the -X wall ----
sk5 = sketch_on("yz", name="vents")
for i in range(-2, 3):
    mrect(sk5, (0, i * 6 - 1, 8), (0, i * 6 + 1, H - 6))
extrude(sk5, "length/2 + 1 mm", "cut", toward=(-1, 0, 0))

# ---- lid: plate + inner lip, built next to the base (offset in Y, so joins never touch it) ----
clearance = 0.2
add_param("lid_gap", "15 mm", "mm", "gap between base and lid in the layout")
yoff = "width + lid_gap"  # lid centre line follows the width parameter
sk6 = sketch_on("xy", name="lid plate")
prect(sk6, "length", "width", cy=yoff)
lid = extrude(sk6, "lid_t", "new").bodies.item(0)
lid.name = "Lid"
fillet_all(
    lid,
    "corner_r",
    lambda e: (
        abs(e.geometry.startPoint.z - e.geometry.endPoint.z) > 1e-6
        if e.geometry.objectType == adsk.core.Line3D.classType()
        else False
    ),
)
sk7 = sketch_on("xy", name="lid lip", offset_mm="lid_t")
prect(sk7, f"length - 2*wall - {2 * clearance} mm", f"width - 2*wall - {2 * clearance} mm", cy=yoff)
prect(
    sk7,
    f"length - 2*wall - {2 * clearance + 3} mm",
    f"width - 2*wall - {2 * clearance + 3} mm",
    cy=yoff,
)
# the ring between the two rectangles is the smaller-area profile
ring = sorted(items(sk7.profiles), key=lambda p: p.areaProperties().area)
extrude(ring[0], "lip_h", "join")

set_appearance_color(base, 40, 120, 200)
set_appearance_color(lid, 240, 160, 30)

fit()
result = {"doc": active_doc_name(), "bodies": body_info(), "params": params()}
