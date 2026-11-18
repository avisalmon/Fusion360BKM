r"""11_blinker_555, step 2b: the tracks. Run after board.py, once the owner agreed the placement.

    python scripts\fusion.py run examples\11_blinker_555\route.py 180

Two layers and no vias: a track may change layer only at a through-hole pad, so each route below
stays on one layer from pad to pad. The classic 555 trick: pins 4 and 8 (+9V) and pins 2 and 6 (THR)
both cross under the chip, diagonally, so one link runs on the top copper and the other on the
bottom, where they cannot touch. GND runs on the bottom; +9V and the signals on the top. Pad
positions are read back from Fusion (brd_pad), never assumed; the corners are chosen from them, and
the 45-degree pieces are computed so they stay at 45 degrees.
"""

TOP, BOTTOM = "top", "bottom"  # Fusion's layers 1 and 304 (not 16: gotcha 37)

ecad_open("brd")
u = {n: brd_pad("U1", str(n)) for n in range(1, 9)}
j1, j2 = brd_pad("J1", "1"), brd_pad("J1", "2")
r1_1, r1_2 = brd_pad("R1", "1"), brd_pad("R1", "2")
r2_1, r2_2 = brd_pad("R2", "1"), brd_pad("R2", "2")
r3_1, r3_2 = brd_pad("R3", "1"), brd_pad("R3", "2")
c1p, c1m = brd_pad("C1", "1"), brd_pad("C1", "2")
c2_1, c2_2 = brd_pad("C2", "1"), brd_pad("C2", "2")
da, dk = brd_pad("D1", "A"), brd_pad("D1", "K")

x_mid_top, x_mid_bot = u[1][0] + 2.63, u[8][0] - 2.63  # the two lanes between U1's pin rows
y_gnd = j2[1] - 2.54  # GND from the LED to J1 passes one pitch under the header
y_c1 = c2_2[1] + 4.35  # GND from C2 to C1, clear of the corner hole and of R2/C1's top pads
# every route starts and ends on a pad: a WIRE ending on the corner of another track made Fusion
# report "unexpected condition ... pusher.cpp" (gotcha 38), so a net of many pins is a chain
ROUTES = [  # signal, layer, points
    ("+9V", TOP, [j1, (j1[0], r1_2[1]), r1_2]),  # up from the header, across the top to R1
    ("+9V", TOP, [u[8], (u[8][0], r1_2[1] - (r1_2[0] - u[8][0])), r1_2]),  # pin 8 up, 45 deg in
    ("+9V", TOP, [u[4], (x_mid_top, u[4][1]), (x_mid_top, u[8][1]), u[8]]),  # 4 to 8 under U1
    ("THR", BOTTOM, [u[2], (x_mid_bot, u[2][1]), (x_mid_bot, u[6][1]), u[6]]),  # 2 to 6 under U1
    ("THR", TOP, [u[6], (u[6][0] + 2.87, u[6][1]), (u[6][0] + 2.87, r2_1[1]), r2_1]),
    ("THR", TOP, [r2_1, c1p]),  # R2, C1+ and pin 5's row: one straight line
    ("DIS", TOP, [u[7], r1_1]),  # one diagonal from pin 7 to R1's far pad
    ("DIS", TOP, [r1_1, (r2_2[0], r1_1[1] - (r1_1[0] - r2_2[0])), r2_2]),
    ("CV", TOP, [u[5], c2_1]),  # C2 sits straight under pin 5
    ("OUT", TOP, [u[3], (u[3][0] - (r3_2[1] - u[3][1]), r3_2[1]), r3_2]),
    ("LED_A", TOP, [r3_1, (da[0] + (da[1] - r3_1[1]), r3_1[1]), da]),
    ("GND", BOTTOM, [dk, (dk[0] + (dk[1] - c2_2[1]), c2_2[1]), c2_2]),  # LED to C2, low
    ("GND", BOTTOM, [c2_2, (c2_2[0] + 3.6, c2_2[1]), (c2_2[0] + 7.95, y_c1), (c1m[0], y_c1), c1m]),
    ("GND", BOTTOM, [dk, (dk[0], y_gnd), (j2[0], y_gnd), j2]),  # LED up to the header
    ("GND", BOTTOM, [j2, (u[1][0], j2[1]), u[1]]),  # header to pin 1
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
    "signals": report["signals"],
}
