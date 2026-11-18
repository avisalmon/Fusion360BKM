r"""11_blinker_555, step 2: the board. Run after circuit.py, on the design it built.

    python scripts\fusion.py run examples\11_blinker_555\board.py 180

50 x 40 mm, an M3 hole in each corner, every part on top. Two layers and no vias: a track may
change layer only at a through-hole pad, so each route below stays on one layer from pad to pad.
The classic 555 trick: pins 4 and 8 (+9V) and pins 2 and 6 (THR) both cross under the chip,
diagonally, so one link runs on the top copper and the other on the bottom, where they cannot
touch. GND runs on the bottom; +9V and the signals on the top. Pad positions are read back from
Fusion (brd_pad), never assumed; the corners are chosen from them.
"""

W, H = 50, 40
HOLES = [(4, 4), (46, 4), (4, 36), (46, 36)]
TOP, BOTTOM = "top", "bottom"  # Fusion's layers 1 and 304 (not 16: gotcha 37)
PLACE = [  # ref, x, y, angle: U1 in the middle, the timing parts to its right, the LED to its left
    ("U1", 24, 22, 0),  # pin 1 top left, pins 1-4 down the left side, 5-8 up the right side
    ("R1", 33, 28.35, 90),  # pad 1 (DIS) level with U1 pin 7, pad 2 (+9V) above
    ("R2", 38, 18.19, 90),  # pad 2 (DIS) level with pin 7, pad 1 (THR) below
    ("C1", 42.5, 13.11, 180),  # + (pad 1) facing R2, - (pad 2) outwards
    ("C2", 28.13, 12.5, 270),  # under pin 5 (CV): pad 1 up, pad 2 (GND) down
    ("R3", 14, 15.65, 90),  # pad 2 level with pin 3 (OUT), pad 1 down to the LED
    ("D1", 9, 10.57, 180),  # anode facing R3, cathode (GND) outwards
    ("J1", 12, 33, 0),  # the battery clip's header, top left
]

ecad_open("brd")
brd_outline(W, H)
for x, y in HOLES:
    brd_hole(x, y)
for ref, x, y, a in PLACE:
    brd_move(ref, x, y, a)
brd_name_size(1.0)

u = {n: brd_pad("U1", str(n)) for n in range(1, 9)}
j1, j2 = brd_pad("J1", "1"), brd_pad("J1", "2")
r1_1, r1_2 = brd_pad("R1", "1"), brd_pad("R1", "2")
r2_1, r2_2 = brd_pad("R2", "1"), brd_pad("R2", "2")
r3_1, r3_2 = brd_pad("R3", "1"), brd_pad("R3", "2")
c1p, c1m = brd_pad("C1", "1"), brd_pad("C1", "2")
c2_1, c2_2 = brd_pad("C2", "1"), brd_pad("C2", "2")
da, dk = brd_pad("D1", "A"), brd_pad("D1", "K")

x_mid_top, x_mid_bot = u[1][0] + 2.63, u[8][0] - 2.63  # the two lanes between U1's pin rows
y_top, y_low, y_gnd = 37, 7, 28
# every route starts and ends on a pad: a WIRE ending on the corner of another track made Fusion
# report "unexpected condition ... pusher.cpp" (gotcha 38), so a net of many pins is a chain
ROUTES = [  # signal, layer, points
    ("+9V", TOP, [j1, (j1[0], y_top), (r1_2[0], y_top), r1_2]),
    ("+9V", TOP, [u[8], (u[8][0], r1_2[1]), r1_2]),
    ("+9V", TOP, [u[4], (x_mid_top, u[4][1]), (x_mid_top, u[8][1]), u[8]]),  # 4 to 8 under U1
    ("THR", BOTTOM, [u[2], (x_mid_bot, u[2][1]), (x_mid_bot, u[6][1]), u[6]]),  # 2 to 6 under U1
    ("THR", TOP, [u[6], (u[6][0] + 2.87, u[6][1]), (u[6][0] + 2.87, r2_1[1]), r2_1]),
    ("THR", TOP, [r2_1, c1p]),
    ("DIS", TOP, [u[7], r1_1, r2_2]),
    ("CV", TOP, [u[5], c2_1]),
    ("OUT", TOP, [u[3], r3_2]),
    ("LED_A", TOP, [r3_1, da]),
    ("GND", BOTTOM, [dk, (dk[0], y_low), (c2_2[0], y_low), c2_2]),
    ("GND", BOTTOM, [c2_2, (c2_2[0] + 2.37, c2_2[1]), (c2_2[0] + 2.37, 9.5), (c1m[0], 9.5), c1m]),
    ("GND", BOTTOM, [dk, (dk[0], y_gnd), (j2[0], y_gnd), j2]),
    ("GND", BOTTOM, [j2, (u[1][0], j2[1]), u[1]]),
]
for signal, layer, pts in ROUTES:
    brd_route(signal, pts, layer=layer)
ecad("WINDOW FIT")

report = brd_report()
result = {
    "all_routed": all(
        s["unrouted"] == 0 and s["tracks"] > 0 and not s["stray"]
        for s in report["signals"].values()
    ),
    "pads": {
        "U1": u, "J1": (j1, j2), "R1": (r1_1, r1_2), "R2": (r2_1, r2_2), "R3": (r3_1, r3_2),
        "C1": (c1p, c1m), "C2": (c2_1, c2_2), "D1": (da, dk),
    },
    **report,
}
