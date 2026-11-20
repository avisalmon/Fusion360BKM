r"""12_tiny_arcade, step 5: the case, version 2: a rounded handheld, the board open on top, the
power bank inside under it. Run after board.py.

    python scripts\fusion.py run examples\12_tiny_arcade\case.py 600

The owner's brief (2026-11-20): rounded, modern, the battery under the board, the screen and the
buttons open so they are pressed and seen directly. (Version 1, a closed box with button caps, is in
git history: "too boxy".)

Two printed parts, each printed flat with no supports:
* Body: a rounded shell (corners of radius 30 seen from above, a rounded bottom edge), 140 x 82 mm.
  The bank lies in it; ribs stop it sliding. Its ends are grips, the thumbs land on A and B (left)
  and the direction pad (right). A port bay in the left end shows the bank's ports and lights.
  Printed open side up.
* Deck: the lid, the same outline. The board sits on four posts on it (4 x M3 x 8 from above,
  through the board's holes), inside a raised rim that guards its edges and is open at the ESP32's
  USB. Four M3 x 10 screws through the deck into columns in the grips hold the two together.
  Printed flat side down.
A short cable (10 cm) runs outside, from the bank's port bay over the left grip to the ESP32's USB.

The board, its parts and the bank are built as reference bodies (board.py says where each part is,
the library's part.json what it looks like), and the script ends by intersecting every printed part
with every reference body: all must be 0 mm3. Every number is in mm at the top; change and re-run.
"""

import json
import math

import adsk.core
import adsk.fusion

# --- the numbers -----------------------------------------------------------------------------
BANK = (100.0, 70.0, 15.0)  # the power bank: the owner's working size 2026-11-20, to be measured
BANK_R, BANK_EDGE = 4.0, 2.0  # its corners seen from above, its top and bottom edges (assumed)
BANK_CLR = 0.5  # around the bank, each side
L, W, R = 140.0, 82.0, 30.0  # the outline seen from above: length, width, corner radius
WALL, BOTTOM_R, DECK_T, DECK_EDGE = (
    2.4,
    4.0,
    3.0,
    1.5,
)  # shell wall; bottom edge; deck; its top edge
POST_H, POST_D, PILOT_D = 4.0, 6.0, 2.5  # board posts (room for the soldered leads under the board)
RIM_GAP, RIM_T, RIM_ABOVE = (
    1.0,
    2.0,
    0.5,
)  # the rim: gap to the board, thickness, above the board top
GRIP_SCREWS = [(58.0, 18.0), (58.0, -18.0), (-58.0, 18.0), (-58.0, -18.0)]  # from the centre
COLUMN_D, SCREW_CLR_D = 7.0, 3.4
BAY_W, BAY_H = 40.0, 11.0  # the bank's port bay (its ports are not measured yet)
USB_NOTCH = 14.0  # the rim's opening at the ESP32's USB
BOARD_T = 1.6

LIB = repo_path("library", "avi_salmon")
EX = repo_path("examples", "12_tiny_arcade")
PARTS = {
    "U1": "esp32_devkitc_38",
    "DISP1": "oled_096_i2c",
    "BZ1": "buzzer_tmb12a03",
    **{f"SW{i}": "tact_switch_6x6" for i in range(1, 7)},
}
COLOURS = {"esp32_devkitc_38": (30, 30, 30), "oled_096_i2c": (20, 60, 140),
           "buzzer_tmb12a03": (25, 25, 25), "tact_switch_6x6": (60, 60, 60)}  # fmt: skip

# --- the board, as board.py placed it ----------------------------------------------------------
BRD, PLACE = {}, {}
for line in open(f"{EX}/board.py", encoding="utf-8"):
    s = line.strip()
    if s.startswith(("W, H =", "HOLES =")):
        exec(s.split("#")[0], {}, BRD)
    if s.startswith('("') and s.count(",") >= 3 and s.split('"')[1] in PARTS:
        nums = s.split("(", 1)[1].split(")")[0].split(",")[1:4]
        PLACE[s.split('"')[1]] = tuple(float(v) for v in nums)
BW, BH, HOLES = BRD["W"], BRD["H"], BRD["HOLES"]

# --- heights (z = 0 under the body) and the board's place (the outline's centre at x = y = 0) ---
BODY_H = WALL + BANK[2] + BANK_CLR  # the body's rim = the deck's underside
ZD = BODY_H + DECK_T  # the deck's top
ZB = ZD + POST_H  # the board's underside
ZT = ZB + BOARD_T  # the board's top
BX, BY = -BW / 2, -BH / 2


def place(ref, x, y):
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


def is_vertical(edge):
    a, b = edge.startVertex.geometry, edge.endVertex.geometry
    return abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and abs(a.z - b.z) > 1e-6


def at_z(z_mm):
    def pred(edge):
        bb = edge.boundingBox
        return abs(bb.minPoint.z * 10 - z_mm) < 1e-3 and abs(bb.maxPoint.z * 10 - z_mm) < 1e-3

    return pred


def rounded(comp, z0, h, w, d, r, cx=0.0, cy=0.0):
    """A box w x d x h centred on (cx, cy), its vertical edges rounded with radius r."""
    b = block(comp, z0, h, cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
    if r > 0:
        fillet_all(b, r, is_vertical)
    return b


def union(target, tools):
    if tools:
        combine(target, tools, "join")
    return target


def cut(target, tools):
    combine(target, tools, "cut")
    return target


new_design("Tiny Arcade case")
top = root()

# --- the reference: the bank, the board, the parts --------------------------------------------
ref = new_component("Board and bank (reference)", top)
bank = rounded(ref, WALL, BANK[2], BANK[0], BANK[1], BANK_R)
fillet_all(bank, BANK_EDGE, lambda e: not is_vertical(e))
bank.name = "power bank"
set_appearance_color(bank, 200, 200, 200)
board = block(ref, ZB, BOARD_T, BX, BY, BX + BW, BY + BH)
cut(board, [rod(ref, ZB - 1, BOARD_T + 2, BX + hx, BY + hy, 3.2) for hx, hy in HOLES])
board.name = "board"
set_appearance_color(board, 20, 110, 50)
refs = [bank, board]
usb = None  # the ESP32's micro-USB socket: y of its centre
for r, pid in PARTS.items():
    model = json.load(open(f"{LIB}/{pid}/part.json", encoding="utf-8-sig"))["model"]
    turned = round(PLACE[r][2]) % 180
    made = []
    for cx, cy, z0, w, d, h, *src in model["boxes"]:
        x, y = place(r, cx, cy)
        w, d = (d, w) if turned else (w, d)
        made.append(block(ref, ZT + z0, h, x - w / 2, y - d / 2, x + w / 2, y + d / 2))
        if src and str(src[0]).startswith("micro-USB"):
            usb = y
    for cx, cy, z0, dia, h, *_ in model["cylinders"]:
        x, y = place(r, cx, cy)
        made.append(rod(ref, ZT + z0, h, x, y, dia))
    for b in made:
        b.name = r
        set_appearance_color(b, *COLOURS[pid])
    refs += made

case = new_component("Case", top)

# --- the body: a rounded shell, open on top -----------------------------------------------------
body_c = new_component("Body", case)
body = rounded(body_c, 0, BODY_H, L, W, R)
fillet_all(body, BOTTOM_R, at_z(0))
shell(body, [top_face(body)], WALL)
ENDS = BANK[0] / 2 + BANK_CLR  # where the bank's ends are
columns = [rod(body_c, 0.5, BODY_H - 0.5, x, y, COLUMN_D) for x, y in GRIP_SCREWS]
ribs = [block(body_c, 0.5, WALL + 8, x0, y - 5, x0 + 2, y + 5)
        for x0 in (ENDS, -ENDS - 2) for y in (-28, 28)]  # fmt: skip
union(body, columns + ribs)
cut(body, [rod(body_c, BODY_H - 8, 9, x, y, PILOT_D) for x, y in GRIP_SCREWS])
bay_z = WALL + (BANK[2] - BAY_H) / 2
cut(body, [block(body_c, bay_z, BAY_H, -L / 2 - 1, -BAY_W / 2, -ENDS + 1, BAY_W / 2)])
body.name = "body"
set_appearance_color(body, 38, 42, 52)

# --- the deck: the lid, the board on posts inside a rim ------------------------------------------
deck_c = new_component("Deck", case)
deck = rounded(deck_c, BODY_H, DECK_T, L, W, R)
fillet_all(deck, DECK_EDGE, at_z(ZD))
rim_h = ZT + RIM_ABOVE - ZD
rim = rounded(
    deck_c, ZD - 0.01, rim_h + 0.01, BW + 2 * (RIM_GAP + RIM_T), BH + 2 * (RIM_GAP + RIM_T), 5.0
)
inside = rounded(deck_c, ZD - 1, rim_h + 2, BW + 2 * RIM_GAP, BH + 2 * RIM_GAP, 3.0)
notch = block(
    deck_c, ZD + 0.5, rim_h + 1, BX - 10, usb - USB_NOTCH / 2, BX + 1, usb + USB_NOTCH / 2
)
cut(rim, [inside, notch])
posts = [rod(deck_c, ZD - 0.01, POST_H + 0.01, BX + hx, BY + hy, POST_D) for hx, hy in HOLES]
union(deck, [rim] + posts)
cut(
    deck,
    [rod(deck_c, BODY_H - 1, DECK_T + POST_H + 2, BX + hx, BY + hy, PILOT_D) for hx, hy in HOLES],
)
cut(deck, [rod(deck_c, BODY_H - 1, DECK_T + 2, x, y, SCREW_CLR_D) for x, y in GRIP_SCREWS])
deck.name = "deck"
set_appearance_color(deck, 236, 236, 230)

# --- proof: nothing printed overlaps anything else -----------------------------------------------
tbm = adsk.fusion.TemporaryBRepManager.get()


def overlap_mm3(a, b):
    t = tbm.copy(a)
    tbm.booleanOperation(t, tbm.copy(b), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return t.volume * 1000


printed = [body, deck]
clashes = {}
for i, p in enumerate(printed):
    for other in refs + printed[i + 1 :]:
        v = overlap_mm3(p, other)
        if v > 0.001:
            clashes[f"{p.name} x {other.name}"] = round(v, 3)

fit()


def bbox(b):
    x = b.boundingBox
    return [round(v * 10, 2) for v in (x.minPoint.x, x.minPoint.y, x.minPoint.z,
                                       x.maxPoint.x, x.maxPoint.y, x.maxPoint.z)]  # fmt: skip


tallest = max(b.boundingBox.maxPoint.z * 10 for b in refs)
result = {
    "outline_mm": [L, W],
    "heights_mm": {
        "body": BODY_H,
        "deck_top": ZD,
        "board_top": round(ZT, 2),
        "rim_top": round(ZT + RIM_ABOVE, 2),
        "tallest_part": round(tallest, 2),
    },  # fmt: skip
    "bodies": {b.name: {"bbox": bbox(b), "volume_cm3": round(b.volume, 2)} for b in printed},
    "clashes_mm3": clashes,
}
