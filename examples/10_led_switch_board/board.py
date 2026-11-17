r"""10_led_switch_board, step 2: the board. Run after circuit.py, on the design it built.

    python scripts\fusion.py run examples\10_led_switch_board\board.py 120

30 x 20 mm, two M3 holes along the bottom edge, every part on top, tracks 0.5 mm on the top
layer. Pad positions are read back from Fusion (brd_pad), never assumed; the corners keep each
track 2 mm or more from the other signals' pads.
"""

W, H = 30, 20
HOLES = [(3.5, 3.5), (26.5, 3.5)]
PLACE = [  # ref, x, y, angle: the slide switch along the bottom edge, for the case slot
    ("J1", 5, 15, 0),
    ("SW1", 15, 3.5, 270),
    ("R1", 16, 11, 0),
    ("D1", 25, 15, 0),
]

ecad_open("brd")
brd_outline(W, H)
for x, y in HOLES:
    brd_hole(x, y)
for ref, x, y, a in PLACE:
    brd_move(ref, x, y, a)
# SparkFun's parts print their names 0.61 mm high; the fab prints 1.0 mm and up legibly
brd_name_size(1.0)

j1, j2 = brd_pad("J1", "1"), brd_pad("J1", "2")
sw_c, sw_o = brd_pad("SW1", "2"), brd_pad("SW1", "1")  # common, and the "on" throw
r1, r2 = brd_pad("R1", "1"), brd_pad("R1", "2")
da, dk = brd_pad("D1", "A"), brd_pad("D1", "K")
ROUTES = {
    "VBAT": [j1, (j1[0], 6.5), (sw_c[0], 6.5), sw_c],
    "VSW": [sw_o, (sw_o[0], 8.5), (r1[0], 8.5), r1],
    "LED_A": [r2, (da[0], r2[1]), da],
    "GND": [dk, (dk[0], 18.8), (j2[0], 18.8), j2],
}
for signal, pts in ROUTES.items():
    brd_route(signal, pts)
ecad("WINDOW FIT")

report = brd_report()
result = {
    "all_routed": all(s["unrouted"] == 0 and s["tracks"] > 0 for s in report["signals"].values()),
    "pads": {"J1": (j1, j2), "SW1": (sw_o, sw_c), "R1": (r1, r2), "D1": (da, dk)},
    **report,
}
