r"""12_tiny_arcade, step 5: the case (version 2, a rounded handheld) and its production files.
Run after board.py and factory.py.

    python scripts\fusion.py run examples\12_tiny_arcade\case.py 900

The owner's brief (2026-11-20): rounded, modern, the power bank under the board, the screen and the
buttons open so they are pressed and seen directly. (Version 1, a closed box with button caps, is in
git history: "too boxy".)

Two printed parts, each printed flat with no supports:
* Body: a rounded shell (corners of radius 30 seen from above, a rounded bottom edge), 140 x 82 mm.
  The bank lies in it; ribs stop it sliding. Its ends are grips; the thumbs land on A and B (left)
  and the direction pad (right). A port bay in the left end shows the bank's ports and lights.
  Printed open side up.
* Deck: the lid, the same outline. The board sits on four posts on it (4 x M3 x 8 from above,
  through the board's holes), inside a raised rim that guards its edges and is open at the ESP32's
  USB. Four M3 x 10 screws through the deck into columns in the grips hold the two together.
  Printed flat side down.
A short cable (10 cm) runs outside, from the bank's port bay over the left grip to the ESP32's USB.

The board, its parts, the bank and the eight screws are in the design too (board.py says where each
part is, the library's part.json what it looks like), and every printed part is intersected with
every one of them: all must be 0 mm3. Then the script writes the production files into production/:
the STL of each printed part, the design (.f3d), the whole assembly (.step), a true-size paper
template of the top, the bill of materials for everything (BOM.csv) and production.json (the
assembly steps, the fit checks, the thumb distances), which board_summary.py puts on the page; and
the pictures into media/, an exploded view among them. Every number is in mm at the top.
"""

import csv
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
# M3 pan-head screws, ISO 7045: head 5.6 across, 2.4 high (drawn as a plain cylinder)
SCREW_HEAD_D, SCREW_HEAD_H, SCREW_D = 5.6, 2.4, 3.0
BOARD_SCREW_L, DECK_SCREW_L = 8.0, 10.0
PLA_G_CM3 = 1.24  # PLA's density, about (the common datasheet value)
BANK_LINK = "https://he.aliexpress.com/item/1005012889986559.html"

LIB = repo_path("library", "avi_salmon")
EX = repo_path("examples", "12_tiny_arcade")
OUT = f"{EX}/production"
PARTS = {
    "U1": "esp32_devkitc_38",
    "DISP1": "oled_096_i2c",
    "BZ1": "buzzer_tmb12a03",
    **{f"SW{i}": "tact_switch_6x6" for i in range(1, 7)},
}
BUTTONS = {"SW1": "A", "SW2": "B", "SW3": "UP", "SW4": "DOWN", "SW5": "LEFT", "SW6": "RIGHT"}
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


close_all_untitled()
new_design("Tiny Arcade case")
top = root()

# --- the power bank, the board and its parts (what the case holds) ------------------------------
bank_c = new_component("Power bank", top)
bank = rounded(bank_c, WALL, BANK[2], BANK[0], BANK[1], BANK_R)
fillet_all(bank, BANK_EDGE, lambda e: not is_vertical(e))
bank.name = "power bank"
set_appearance_color(bank, 200, 200, 200)

board_c = new_component("Board", top)
board = block(board_c, ZB, BOARD_T, BX, BY, BX + BW, BY + BH)
cut(board, [rod(board_c, ZB - 1, BOARD_T + 2, BX + hx, BY + hy, 3.2) for hx, hy in HOLES])
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
        made.append(block(board_c, ZT + z0, h, x - w / 2, y - d / 2, x + w / 2, y + d / 2))
        if src and str(src[0]).startswith("micro-USB"):
            usb = y
    for cx, cy, z0, dia, h, *_ in model["cylinders"]:
        x, y = place(r, cx, cy)
        made.append(rod(board_c, ZT + z0, h, x, y, dia))
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

# --- the screws: a head on the surface, a shank into the hole -----------------------------------
screws = []  # (component, head body, shank body)
for name, z_seat, length, spots in (
    ("Board screws M3x8", ZT, BOARD_SCREW_L, [(BX + hx, BY + hy) for hx, hy in HOLES]),
    ("Deck screws M3x10", ZD, DECK_SCREW_L, GRIP_SCREWS),
):
    sc = new_component(name, top)
    for x, y in spots:
        head = rod(sc, z_seat, SCREW_HEAD_H, x, y, SCREW_HEAD_D)
        shank = rod(sc, z_seat - length, length, x, y, SCREW_D)
        for b in (head, shank):
            b.name = name.split()[0].lower() + " screw"
            set_appearance_color(b, 160, 160, 165)
        screws.append((sc, head, shank))

# --- proof: nothing overlaps what it must not -----------------------------------------------------
tbm = adsk.fusion.TemporaryBRepManager.get()


def overlap_mm3(a, b):
    t = tbm.copy(a)
    tbm.booleanOperation(t, tbm.copy(b), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return t.volume * 1000


printed = [body, deck]
heads = [h for _, h, _ in screws]
shanks = [s for _, _, s in screws]
pairs = [(p, o) for i, p in enumerate(printed) for o in refs + printed[i + 1 :]]
pairs += [
    (h, o) for h in heads for o in refs + printed
]  # a head sits on its surface, inside nothing
pairs += [(s, o) for s in shanks for o in refs]  # a shank passes the board's 3.2 mm hole; it bites
# into the printed parts' 2.5 mm holes on purpose (that is its thread), so those are not counted
clashes = {}
for a, b in pairs:
    v = overlap_mm3(a, b)
    if v > 0.001:
        clashes[f"{a.name} x {b.name}"] = round(v, 3)
for sc, head, shank in screws:  # one body per screw, now that each half was checked
    combine(head, shank, "join")

# --- the thumbs: how far each button is from the case's end and its front edge -------------------
reach = {}
for sw, label in BUTTONS.items():
    x, y = place(sw, 0, 0)
    reach[label] = {"from_end": round(L / 2 - abs(x), 1), "from_front": round(y + W / 2, 1)}

# --- production files ---------------------------------------------------------------------------
files = {
    "body_stl": "production/tiny_arcade_case_body.stl",
    "deck_stl": "production/tiny_arcade_case_deck.stl",
    "f3d": "production/tiny_arcade_case.f3d",
    "step": "production/tiny_arcade_assembly.step",
    "template": "production/template_top_1to1.svg",
    "bom": "production/BOM.csv",
}
export_stl(f"{EX}/{files['body_stl']}", body)
export_stl(f"{EX}/{files['deck_stl']}", deck)
export_step(f"{EX}/{files['step']}")
export_f3d(f"{EX}/{files['f3d']}")


def svg_template():
    """The top at true size (mm), to print on paper at 100 % and hold before printing plastic."""
    pad = 6

    def X(x):
        return round(x + L / 2 + pad, 2)

    def Y(y):
        return round(W / 2 + pad - y, 2)

    def rrect(cx, cy, w, d, r, style):
        x, y = X(cx - w / 2), Y(cy + d / 2)
        return f'<rect x="{x}" y="{y}" width="{w}" height="{d}" rx="{r}" {style}/>'

    def ring(cx, cy, r, style):
        return f'<circle cx="{X(cx)}" cy="{Y(cy)}" r="{r}" {style}/>'

    def text(x, y, size, words, anchor="start"):
        return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{words}</text>'

    thin = 'fill="none" stroke="#333" stroke-width="0.25"'
    sw_, sh_ = L + 2 * pad, W + 2 * pad + 20
    rim_w, rim_d = BW + 2 * (RIM_GAP + RIM_T), BH + 2 * (RIM_GAP + RIM_T)
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw_}mm" height="{sh_}mm" '
        f'viewBox="0 0 {sw_} {sh_}" font-family="sans-serif">',
        rrect(0, 0, L, W, R, 'fill="#eee" stroke="#000" stroke-width="0.3"'),
        rrect(0, 0, rim_w, rim_d, 5, 'fill="#fff" stroke="#888" stroke-width="0.2"'),
        rrect(0, 0, BW, BH, 0, 'fill="#cfe8d4" stroke="#2a7" stroke-width="0.2"'),
    ]
    gx, gy = place("DISP1", 0, -12.25)
    s.append(rrect(gx, gy, 26.7, 19.26, 0.5, 'fill="#235" stroke="none"'))
    ux, uy = place("U1", 0, 0)
    s.append(rrect(ux, uy, 54.4, 27.9, 0.5, thin + ' stroke-dasharray="1 1"'))
    s.append(ring(*place("BZ1", 0, 0), 6, thin))
    for sw, label in BUTTONS.items():
        x, y = place(sw, 0, 0)
        s.append(rrect(x, y, 6, 6, 0.5, 'fill="#444"'))
        s.append(ring(x, y, 1.75, 'fill="#c33"'))
        s.append(text(X(x), Y(y) - 4.5, 3, label, "middle"))
    for x, y in [(BX + hx, BY + hy) for hx, hy in HOLES] + GRIP_SCREWS:
        s.append(ring(x, y, 1.6, 'fill="none" stroke="#000" stroke-width="0.2"'))
    y0 = W + 2 * pad + 4
    s.append(
        f'<line x1="{pad}" y1="{y0}" x2="{pad + 50}" y2="{y0}" stroke="#000" stroke-width="0.5"/>'
    )
    s.append(
        text(
            pad,
            y0 + 5,
            3.2,
            'this line is 50 mm: measure it after printing (print at 100 %, no "fit to page")',
        )
    )
    s.append(text(pad, y0 + 10, 3.2, "Tiny Arcade, the top at true size: the outline, the board, "
                                     "the buttons (red: the plunger you press)"))  # fmt: skip
    s.append("</svg>")
    return "\n".join(s) + "\n"


with open(f"{EX}/{files['template']}", "w", encoding="utf-8", newline="\n") as f:
    f.write(svg_template())

mass = {b.name: round(b.volume * PLA_G_CM3, 1) for b in printed}
THREAD = "cuts its own thread in the 2.5 mm hole"
bom = []  # item, qty, part, where it goes, source, notes
bom.append(
    [
        "PCB",
        1,
        f"Tiny Arcade board, {BW:g} x {BH:g} mm, 2 layers, FR-4 {BOARD_T} mm",
        "the base of everything",
        "a PCB fab (JLCPCB): upload factory/board_gerbers.zip",
        "checked: see the board's checks above",
    ]
)
with open(f"{EX}/factory/BOM.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        refs_ = [r.strip() for r in row["Designator"].split(",")]
        lib_part = PARTS[refs_[0]]
        pj = json.load(open(f"{LIB}/{lib_part}/part.json", encoding="utf-8-sig"))
        where = f"the owner's store, library/avi_salmon/{lib_part} (location: {pj.get('location')})"
        bom.append(
            [row["Comment"], len(refs_), pj["name"], ", ".join(refs_), where, "soldered by hand"]
        )
for b, f_ in ((body, files["body_stl"]), (deck, files["deck_stl"])):
    what = f"printed in PLA, {b.volume:.1f} cm3 solid (at most {mass[b.name]} g)"
    bom.append([f"case {b.name}", 1, what, "the case", f_, "flat, no supports: see Print"])
SHOP = "hardware store"
bom.append(["M3x8", len(HOLES), "M3 x 8 mm pan-head screw (ISO 7045)",
            "board onto the deck's posts", SHOP, THREAD])  # fmt: skip
bom.append(["M3x10", len(GRIP_SCREWS), "M3 x 10 mm pan-head screw (ISO 7045)",
            "deck into the body's grip columns", SHOP, THREAD])  # fmt: skip
bank_size = f"about {BANK[0]:g} x {BANK[1]:g} x {BANK[2]:g} mm"
bom.append(["power bank", 1, f"power bank 5000 mAh, {bank_size}",
            "inside the body, ports to the left", BANK_LINK,
            "size assumed until measured"])  # fmt: skip
bom.append(["cable", 1, "USB-A to micro-USB cable, about 10 cm",
            "the bank's port bay to the ESP32's USB", "any",
            "outside, over the left grip"])  # fmt: skip
with open(f"{EX}/{files['bom']}", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["Item", "Qty", "Part", "Where it goes", "Source", "Notes"])
    w.writerows(bom)

production = {
    "about": "written by case.py; board_summary.py puts it on the page",
    "outline_mm": [L, W, round(ZD, 2)],
    "printed": [
        {
            "name": "Body",
            "file": files["body_stl"],
            "volume_cm3": round(body.volume, 2),
            "mass_g_solid": mass["body"],
            "orient": "open side up (as drawn)",
            "why": "the rounded bottom edge (radius 4) rises gently from the bed; "
            "nothing hangs in the air",
        },
        {
            "name": "Deck",
            "file": files["deck_stl"],
            "volume_cm3": round(deck.volume, 2),
            "mass_g_solid": mass["deck"],
            "orient": "flat side down (as drawn)",
            "why": "the posts and the rim grow straight up from a flat plate",
        },
    ],
    "print_settings": "PLA, 0.2 mm layers, 0.4 mm nozzle, 4 walls (the 2.4 mm walls print solid), "
    "20 % infill, no supports: the 3D printing rules of thumb in docs/fusion_reference.md",
    "assembly": [
        "Solder the parts onto the board: the ESP32 straight on (its pin strips' plastic on the "
        "board), the screen, the buzzer (+ to the square pad), the six buttons. Clip the leads "
        "under the board to 2 mm or less.",
        f"Screw the board onto the deck's four posts: {len(HOLES)} x M3 x 8 from above, through "
        "the board's holes. Turn each one until it is snug, no further: it cuts its thread in the "
        "plastic.",
        "Lay the power bank in the body, its ports toward the port bay in the left end.",
        f"Lay the deck on the body and screw it down: {len(GRIP_SCREWS)} x M3 x 10 through the "
        "deck into the columns in the grips.",
        "Plug the cable into the bank (through the port bay) and into the ESP32's micro-USB (at "
        "the gap in the rim). Charge the bank through the same bay.",
    ],
    "fit": {"pairs_checked": len(pairs), "clashes_mm3": clashes},
    "thumbs_mm": reach,
    "files": files,
    "assumed": "the bank (100 x 70 x 15 mm, its ports and button), the buttons' height (5 mm), the "
    "screen's and the buzzer's heights: each from a listing or a common size, to be measured",
}
with open(f"{OUT}/production.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(production, f, indent=1, ensure_ascii=False)
    f.write("\n")

# --- pictures -----------------------------------------------------------------------------------
vp = app.activeViewport
V = adsk.core.ViewOrientations
occ = {o.component.name: o for o in top.allOccurrences}


def view(orient, name, hide=()):
    for n, o in occ.items():
        o.isLightBulbOn = n not in hide
    cam = vp.camera
    cam.viewOrientation = orient
    cam.isFitView = True
    vp.camera = cam
    screenshot(f"{EX}/media/{name}.png", 1600, 1000)


view(V.FrontViewOrientation, "case_v2_front")
view(V.IsoTopLeftViewOrientation, "case_v2_left")
view(V.TopViewOrientation, "case_v2_top")
view(V.IsoTopRightViewOrientation, "case_v2_open", hide=("Deck", "Board", "Board screws M3x8"))
lift = {"Power bank": 25, "Deck": 45, "Deck screws M3x10": 65, "Board": 70, "Board screws M3x8": 95}
for n, dz in lift.items():
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, 0, dz / 10)
    occ[n].transform2 = m
view(V.IsoTopRightViewOrientation, "case_exploded")
for n in lift:
    occ[n].transform2 = adsk.core.Matrix3D.create()
view(V.IsoTopRightViewOrientation, "case_v2")


def bbox(b):
    x = b.boundingBox
    return [round(v * 10, 2) for v in (x.minPoint.x, x.minPoint.y, x.minPoint.z,
                                       x.maxPoint.x, x.maxPoint.y, x.maxPoint.z)]  # fmt: skip


result = {
    "outline_mm": [L, W],
    "heights_mm": {
        "body": BODY_H,
        "deck_top": ZD,
        "board_top": round(ZT, 2),
        "rim_top": round(ZT + RIM_ABOVE, 2),
    },  # fmt: skip
    "bodies": {b.name: {"bbox": bbox(b), "volume_cm3": round(b.volume, 2)} for b in printed},
    "fit": production["fit"],
    "thumbs_mm": reach,
}
