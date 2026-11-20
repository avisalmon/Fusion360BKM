r"""12_tiny_arcade, step 5: the case, with the power bank under the board. Run after board.py.

    python scripts\fusion.py run examples\12_tiny_arcade\case.py 600

Three kinds of printed part, each printed flat with no supports:
* Body: an open box. The power bank lies on its floor, its ports facing the left wall, where a slot
  shows them (charge it, see its lights, plug the cable in). Printed open side up.
* Cover: a flat top plate. The board hangs from four posts under it (four M3 x 8 screws from
  below, through the board's holes). Four corner columns reach down to just above the bank and are
  held by four M3 x 8 screws through the body's end walls. Over the screen a block comes down to the
  glass, so the window is not a deep hole. Printed top face down.
* Six button caps: they stand on the buttons and come up through the cover; a flange under the
  cover keeps them in.
A short USB cable (10 cm, the owner's choice) runs outside on the left face from the bank's port to
the ESP32's micro-USB, which has its own opening above the slot.

The board and its parts are built here as reference bodies, from the same sources as board3d.py:
board.py (where each part is), the library's part.json (each part's model). The ESP32 is soldered
straight onto the board (the owner's choice 2026-11-20). The script ends by intersecting every
printed part with every reference body: all must be 0 mm3, or the case hits something.
Every number below is in mm; change it here and run again.
"""

import json
import math

import adsk.core
import adsk.fusion

# --- the numbers -----------------------------------------------------------------------------
BANK = (100.0, 70.0, 15.0)  # the power bank: the owner's working size 2026-11-20, to be measured
BANK_CLR = 0.3  # around the bank, each side
WALL, FLOOR, PLATE = 2.0, 1.6, 2.0  # body walls, body floor, cover plate
BOARD_T = 1.6  # the board's thickness (the order's default)
UNDER = 2.5  # under the board: the soldered leads and the M3 screw heads
GAP_BANK = 1.0  # between the bank's top and the lowest thing above it
GAP_TOP = 0.5  # above the tallest part on the board
CORNER_R = 3.0  # the case's outer corners
POST_D, PILOT_D, PILOT_DEPTH = 6.0, 2.5, 8.0  # posts under the cover; M3 screws cut their thread
COL, COL_CLR, SCREW_CLR_D = 6.8, 0.2, 3.4  # corner columns; their gap to the walls; M3 clearance
CAP_BASE_D, CAP_FLANGE_D, CAP_STEM_D, CAP_HOLE_D = 5.0, 8.6, 6.0, 6.8
CAP_FLANGE_T, CAP_PLAY, CAP_PROUD = 1.0, 0.2, 1.5  # flange; its gap to the cover; above the cover
BUZZER_HOLE_D, BUZZER_HOLE_R = 2.0, 3.5
SLOT_W, SLOT_H = (
    50.0,
    10.0,
)  # the bank's ports, centred on the left wall (its ports not yet measured)
USB_W, USB_H = 12.0, 8.0  # around the micro-USB plug's moulding

LIB = repo_path("library", "avi_salmon")
EX = repo_path("examples", "12_tiny_arcade")
PARTS = {
    "U1": "esp32_devkitc_38",
    "DISP1": "oled_096_i2c",
    "BZ1": "buzzer_tmb12a03",
    **{f"SW{i}": "tact_switch_6x6" for i in range(1, 7)},
}
CAPS = {"SW1": "A", "SW2": "B", "SW3": "UP", "SW4": "DOWN", "SW5": "LEFT", "SW6": "RIGHT"}
COLOURS = {"esp32_devkitc_38": (30, 30, 30), "oled_096_i2c": (20, 60, 140),
           "buzzer_tmb12a03": (25, 25, 25), "tact_switch_6x6": (60, 60, 60)}  # fmt: skip

# --- the board, as board.py placed it ----------------------------------------------------------
BRD = {}
PLACE = {}
for line in open(f"{EX}/board.py", encoding="utf-8"):
    s = line.strip()
    if s.startswith(("W, H =", "HOLES =")):
        exec(s.split("#")[0], {}, BRD)
    if s.startswith('("') and s.count(",") >= 3 and s.split('"')[1] in PARTS:
        nums = s.split("(", 1)[1].split(")")[0].split(",")[1:4]
        PLACE[s.split('"')[1]] = tuple(float(v) for v in nums)
BW, BH, HOLES = BRD["W"], BRD["H"], BRD["HOLES"]

# --- derived heights and positions (case frame: the inside corner of the body at x = y = 0,
# the underside of the body's floor at z = 0) ---------------------------------------------------
IX, IY = BANK[0] + 2 * BANK_CLR, BANK[1] + 2 * BANK_CLR  # inside of the body
BANK_TOP = FLOOR + BANK[2]
ZB = BANK_TOP + GAP_BANK + UNDER  # underside of the board
ZT = ZB + BOARD_T  # top of the board
BX, BY = (IX - BW) / 2, (IY - BH) / 2  # the board, centred between the corner columns
assert BX >= COL + 0.5 - 1e-6, "the board does not fit between the corner columns"
COL_Z0 = BANK_TOP + 0.3  # the columns stop just above the bank and keep it down


def items(coll):
    return [coll.item(i) for i in range(coll.count)]


def place(ref, x, y):
    """A point of a part's footprint frame, in the case frame."""
    ex, ey, angle = PLACE[ref]
    a = math.radians(angle)
    return BX + ex + x * math.cos(a) - y * math.sin(a), BY + ey + x * math.sin(a) + y * math.cos(a)


def block(comp, z0, h, x0, y0, x1, y1):
    sk = sketch_on("xy", comp, offset_mm=z0)
    rect(sk, x0, y0, x1, y1)
    return extrude(sk, h, comp=comp).bodies.item(0)


def rod(comp, z0, h, cx, cy, d):
    sk = sketch_on("xy", comp, offset_mm=z0)
    circle(sk, cx, cy, d)
    return extrude(sk, h, comp=comp).bodies.item(0)


def rod_x(comp, x0, length, cy, cz, d):
    """A cylinder along +x, starting at x0."""
    sk = sketch_on("yz", comp, offset_mm=x0)
    mcircle(sk, (x0, cy, cz), d)
    return extrude(sk, length, comp=comp, toward=(1, 0, 0)).bodies.item(0)


def union(target, tools):
    if tools:
        combine(target, tools, "join")
    return target


def cut(target, tools):
    combine(target, tools, "cut")
    return target


def outer_corner(x, y):
    return (
        min(abs(x + WALL), abs(x - IX - WALL)) < 1e-3
        and min(abs(y + WALL), abs(y - IY - WALL)) < 1e-3
    )


def vertical_outer_edge(edge):
    a, b = edge.startVertex.geometry, edge.endVertex.geometry
    return abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and outer_corner(a.x * 10, a.y * 10)


new_design("Tiny Arcade case")
top = root()

# --- the reference: the bank, the board, the parts --------------------------------------------
ref = new_component("Board and bank (reference)", top)
bank = block(ref, FLOOR, BANK[2], BANK_CLR, BANK_CLR, BANK_CLR + BANK[0], BANK_CLR + BANK[1])
bank.name = "power bank"
set_appearance_color(bank, 200, 200, 200)
board = block(ref, ZB, BOARD_T, BX, BY, BX + BW, BY + BH)
cut(board, [rod(ref, ZB - 1, BOARD_T + 2, BX + hx, BY + hy, 3.2) for hx, hy in HOLES])
board.name = "board"
set_appearance_color(board, 20, 110, 50)
refs = [bank, board]
tallest = ZT
usb = None  # the ESP32's micro-USB socket: (y, z) of its centre
plungers = {}
for r, pid in PARTS.items():
    model = json.load(open(f"{LIB}/{pid}/part.json", encoding="utf-8-sig"))["model"]
    turned = round(PLACE[r][2]) % 180
    made = []
    for cx, cy, z0, w, d, h, *src in model["boxes"]:
        x, y = place(r, cx, cy)
        w, d = (d, w) if turned else (w, d)
        made.append(block(ref, ZT + z0, h, x - w / 2, y - d / 2, x + w / 2, y + d / 2))
        if src and str(src[0]).startswith("micro-USB"):
            usb = (y, ZT + z0 + h / 2)
    for cx, cy, z0, dia, h, *_ in model["cylinders"]:
        x, y = place(r, cx, cy)
        made.append(rod(ref, ZT + z0, h, x, y, dia))
        plungers[r] = ZT + z0 + h
    for b in made:
        b.name = r
        set_appearance_color(b, *COLOURS[pid])
        tallest = max(tallest, b.boundingBox.maxPoint.z * 10)
    refs += made

ZC = tallest + GAP_TOP  # underside of the cover plate = top of the body's walls
HZ = (COL_Z0 + ZC) / 2  # height of the end-wall screws

# --- the body ------------------------------------------------------------------------------------
case = new_component("Case", top)
body_c = new_component("Body", case)
body = block(body_c, 0, ZC, -WALL, -WALL, IX + WALL, IY + WALL)
fillet_all(body, CORNER_R, vertical_outer_edge)
cut(body, [block(body_c, FLOOR, ZC, 0, 0, IX, IY)])
left = -WALL - 1
cut(
    body,
    [
        # the bank's ports, lights and the cable's plug
        block(
            body_c,
            FLOOR + (BANK[2] - SLOT_H) / 2,
            SLOT_H,
            left,
            IY / 2 - SLOT_W / 2,
            1,
            IY / 2 + SLOT_W / 2,
        ),
        # the ESP32's micro-USB: open to the top, the cover closes it
        block(body_c, usb[1] - USB_H / 2, ZC, left, usb[0] - USB_W / 2, 1, usb[0] + USB_W / 2),
    ]
    + [
        rod_x(body_c, x0, WALL + 2, y, HZ, SCREW_CLR_D)
        for x0 in (left, IX - 1)
        for y in (COL / 2, IY - COL / 2)
    ],
)
body.name = "body"
set_appearance_color(body, 230, 120, 30)

# --- the cover -----------------------------------------------------------------------------------
cover_c = new_component("Cover", case)
cover = block(cover_c, ZC, PLATE, -WALL, -WALL, IX + WALL, IY + WALL)
fillet_all(cover, CORNER_R, vertical_outer_edge)
posts = [rod(cover_c, ZT, ZC - ZT + 0.01, BX + hx, BY + hy, POST_D) for hx, hy in HOLES]
corners = [(COL_CLR, COL_CLR), (IX - COL, COL_CLR), (COL_CLR, IY - COL), (IX - COL, IY - COL)]
columns = [
    block(cover_c, COL_Z0, ZC - COL_Z0 + 0.01, x, y, x + COL - COL_CLR, y + COL - COL_CLR)
    for x, y in corners
]
gx, gy = place("DISP1", 0, -12.25)  # the screen's glass: centre (from the OLED's model)
GW, GD, GTOP = 26.7, 19.26, ZT + 3.7 + 1.4
bezel = block(
    cover_c,
    GTOP + GAP_TOP,
    ZC - GTOP - GAP_TOP + 0.01,
    gx - GW / 2 - 1,
    gy - GD / 2 - 1,
    gx + GW / 2 + 1,
    gy + GD / 2 + 1,
)
union(cover, posts + columns + [bezel])
holes = [rod(cover_c, ZT - 1, PILOT_DEPTH + 1, BX + hx, BY + hy, PILOT_D) for hx, hy in HOLES]
holes += [
    rod_x(cover_c, -1, COL + 1, COL / 2, HZ, PILOT_D),
    rod_x(cover_c, -1, COL + 1, IY - COL / 2, HZ, PILOT_D),
]
holes += [rod_x(cover_c, IX - COL, COL + 1, y, HZ, PILOT_D) for y in (COL / 2, IY - COL / 2)]
holes.append(
    block(
        cover_c,
        GTOP,
        ZC + PLATE - GTOP + 1,
        gx - GW / 2 + 1.5,
        gy - GD / 2 + 1.5,
        gx + GW / 2 - 1.5,
        gy + GD / 2 - 1.5,
    )
)  # the window
holes += [rod(cover_c, ZC - 1, PLATE + 2, *place(sw, 0, 0), CAP_HOLE_D) for sw in CAPS]
bzx, bzy = place("BZ1", 0, 0)
holes.append(rod(cover_c, ZC - 1, PLATE + 2, bzx, bzy, BUZZER_HOLE_D))
holes += [
    rod(
        cover_c,
        ZC - 1,
        PLATE + 2,
        bzx + BUZZER_HOLE_R * math.cos(a),
        bzy + BUZZER_HOLE_R * math.sin(a),
        BUZZER_HOLE_D,
    )
    for a in (math.radians(45 + 90 * k) for k in range(4))
]
cut(cover, holes)
cover.name = "cover"
set_appearance_color(cover, 240, 240, 235)

# --- the button caps -----------------------------------------------------------------------------
caps_c = new_component("Caps", case)
caps = []
for sw, label in CAPS.items():
    x, y = place(sw, 0, 0)
    z0 = plungers[sw] + CAP_PLAY
    zf = ZC - CAP_PLAY - CAP_FLANGE_T
    cap = rod(caps_c, z0, zf - z0, x, y, CAP_BASE_D)
    union(
        cap,
        [
            rod(caps_c, zf, CAP_FLANGE_T, x, y, CAP_FLANGE_D),
            rod(
                caps_c,
                zf + CAP_FLANGE_T - 0.01,
                ZC + PLATE + CAP_PROUD - zf - CAP_FLANGE_T + 0.01,
                x,
                y,
                CAP_STEM_D,
            ),
        ],
    )
    cap.name = f"cap {label}"
    set_appearance_color(cap, 200, 30, 30) if label in ("A", "B") else set_appearance_color(
        cap, 40, 40, 40
    )
    caps.append(cap)

# --- proof: nothing printed overlaps anything else -----------------------------------------------
tbm = adsk.fusion.TemporaryBRepManager.get()


def overlap_mm3(a, b):
    t = tbm.copy(a)
    tbm.booleanOperation(t, tbm.copy(b), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return t.volume * 1000


printed = [body, cover, *caps]
clashes = {}
for i, p in enumerate(printed):
    for other in refs + printed[i + 1 :]:
        v = overlap_mm3(p, other)
        if v > 0.001:
            clashes[f"{p.name} x {other.name}"] = round(v, 3)

fit()


def bbox(b):
    x = b.boundingBox
    return [
        round(v * 10, 2)
        for v in (
            x.minPoint.x,
            x.minPoint.y,
            x.minPoint.z,
            x.maxPoint.x,
            x.maxPoint.y,
            x.maxPoint.z,
        )
    ]


result = {
    "outside_mm": [round(IX + 2 * WALL, 2), round(IY + 2 * WALL, 2), round(ZC + PLATE, 2)],
    "heights_mm": {
        "bank_top": BANK_TOP,
        "board_under": ZB,
        "board_top": ZT,
        "tallest_part": round(tallest, 2),
        "cover_under": round(ZC, 2),
        "cover_top": round(ZC + PLATE, 2),
        "caps_top": round(ZC + PLATE + CAP_PROUD, 2),
    },
    "board_offset_mm": [BX, BY],
    "usb_centre_yz": [round(usb[0], 2), round(usb[1], 2)],
    "bodies": {b.name: {"bbox": bbox(b), "volume_cm3": round(b.volume, 2)} for b in printed},
    "clashes_mm3": clashes,
}
