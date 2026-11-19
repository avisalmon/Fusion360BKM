r"""12_tiny_arcade, step 4: the board in 3D, with every part as a 3D object. Run after factory.py.

    python scripts\fusion.py run examples\12_tiny_arcade\board3d.py 300

Opens Fusion's 3D board (its board body is 86 x 64 x 1.5 mm, in the board's own x, y), and builds
each part from the "model" in its library part.json (boxes and cylinders, every size with its
source), turned and moved to where the part sits on the board, in a component "Parts 3D" with one
component per part. How a part is mounted belongs to this board, not to the part: MOUNT lifts it.
The result gives each part's bounding box in mm, which the box (case) is designed around.
"""

import json
import math

import adsk.core
import adsk.fusion

LIB = repo_path("library", "avi_salmon")
PARTS = {  # ref: the library part
    "U1": "esp32_devkitc_38",
    "DISP1": "oled_096_i2c",
    "BZ1": "buzzer_tmb12a03",
    **{f"SW{i}": "tact_switch_6x6" for i in range(1, 7)},
}
BOARD_TOP = 1.5  # the 3D board's body is 1.5 mm thick, read from Fusion 2026-11-19
# the ESP32 plugs into two female headers, as on the owner's Tiny Arcade (8.5 mm, the standard
# 2.54 mm female header; an assumption until the owner says how this board will be built)
MOUNT = {"U1": 8.5}
FEMALE_HEADERS = [  # ref, cx, cy (footprint frame), w, d, h
    ("U1", -12.7, 0, 2.5, 48.3, 8.5),
    ("U1", 12.7, 0, 2.5, 48.3, 8.5),
]
COLOURS = {"esp32_devkitc_38": (30, 30, 30), "oled_096_i2c": (20, 60, 140),
           "buzzer_tmb12a03": (25, 25, 25), "tact_switch_6x6": (60, 60, 60)}  # fmt: skip


def items(coll):
    return [coll.item(i) for i in range(coll.count)]


def place(ex, ey, angle, x, y):
    """A point of the footprint's frame, on the board: turned by the part's angle, then moved."""
    a = math.radians(angle)
    return ex + x * math.cos(a) - y * math.sin(a), ey + x * math.sin(a) + y * math.cos(a)


def box(comp, ex, ey, angle, cx, cy, z0, w, d, h):
    x, y = place(ex, ey, angle, cx, cy)
    if round(angle) % 180:
        w, d = d, w
    sk = sketch_on("xy", comp, offset_mm=z0)
    rect(sk, x - w / 2, y - d / 2, x + w / 2, y + d / 2)
    return extrude(sk, h, comp=comp).bodies.item(0)


def cylinder(comp, ex, ey, angle, cx, cy, z0, dia, h):
    x, y = place(ex, ey, angle, cx, cy)
    sk = sketch_on("xy", comp, offset_mm=z0)
    circle(sk, x, y, dia)
    return extrude(sk, h, comp=comp).bodies.item(0)


ecad_open("3d", timeout_s=120)
des = adsk.fusion.Design.cast(app.activeProduct)
top = des.rootComponent
for occ in list(items(top.occurrences)):  # an earlier run's parts
    if occ.component.name == "Parts 3D":
        occ.deleteMe()
holder = new_component("Parts 3D", top)

# each part's position and angle on the board: board.py's PLACE, which put it there
PLACE = {}
for line in open(repo_path("examples", "12_tiny_arcade", "board.py"), encoding="utf-8"):
    s = line.strip()
    if s.startswith('("') and s.count(",") >= 3 and s.split('"')[1] in PARTS:
        ref = s.split('"')[1]
        nums = s.split("(", 1)[1].split(")")[0].split(",")[1:4]
        PLACE[ref] = tuple(float(v) for v in nums)

report = {}
for ref, pid in PARTS.items():
    model = json.load(open(f"{LIB}/{pid}/part.json", encoding="utf-8-sig"))["model"]
    ex, ey, angle = PLACE[ref]
    comp = new_component(ref, holder)
    lift = BOARD_TOP + MOUNT.get(ref, 0.0)
    made = []
    for cx, cy, z0, w, d, h, *_ in model["boxes"]:
        made.append(box(comp, ex, ey, angle, cx, cy, lift + z0, w, d, h))
    for cx, cy, z0, dia, h, *_ in model["cylinders"]:
        made.append(cylinder(comp, ex, ey, angle, cx, cy, lift + z0, dia, h))
    for r, cx, cy, w, d, h in FEMALE_HEADERS:
        if r == ref:
            made.append(box(comp, ex, ey, angle, cx, cy, BOARD_TOP, w, d, h))
    for b in made:
        set_appearance_color(b, *COLOURS[pid])
    bb = None
    for b in made:
        x = b.boundingBox
        v = [x.minPoint.x, x.minPoint.y, x.minPoint.z, x.maxPoint.x, x.maxPoint.y, x.maxPoint.z]
        bb = (
            v
            if bb is None
            else [min(bb[i], v[i]) for i in range(3)] + [max(bb[i], v[i]) for i in range(3, 6)]
        )
    report[ref] = [round(v * 10, 2) for v in bb]

fit()
result = {"parts_bbox_mm": report}
