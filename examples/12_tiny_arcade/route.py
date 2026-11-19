r"""12_tiny_arcade, step 2b: the tracks. Run after board.py, once the owner agreed the placement.

    python scripts\fusion.py run examples\12_tiny_arcade\route.py 300

Two layers, no vias: every track starts and ends on a pad (gotcha 38), and two tracks cross only
on different layers. The plan:
* Bottom: the four direction tracks leave the ESP32's top row and run under the module at four
  levels, the pin furthest right at the highest level and the furthest right column, so none
  crosses another; B runs round the module's left end, down the left edge. SCL, and GND between
  the ESP32's three GND pins and the screen.
* Top: A, SDA, the buzzer, 3V3 (down through the gap between pins 27 and 28), every button's two
  pad pairs (its legs are joined inside, but the board must say so in copper) and the ground
  joining the buttons, the screen and the buzzer.
Tracks 0.4 mm. Pads are read back from Fusion (brd_pad), never assumed; the corners are numbers
fitted to the agreed placement in board.py.
"""

WIDTH = 0.4

TOP = [  # signal, from pad, to pad, corners (mm)
    ("BTN_A", "U1.32", "SW1.3", [(20.58, 27.06)]),
    ("SDA", "U1.25", "DISP1.4", [(38.36, 30.5), (35.97, 30.5)]),
    ("3V3", "U1.1", "DISP1.2", [(51.06, 58), (32.01, 58), (32.01, 30.5), (30.89, 30.5)]),
    ("BUZZER", "U1.21", "BZ1.1", [(48.52, 38.5), (57, 38.5), (57, 55.08)]),
    # each button: contact 1 to its twin 3, contact 2 to its twin 4
    *[(sig, f"{sw}.1", f"{sw}.3", []) for sw, sig in [
        ("SW1", "BTN_A"), ("SW2", "BTN_B"), ("SW3", "BTN_UP"), ("SW4", "BTN_DOWN"),
        ("SW5", "BTN_LEFT"), ("SW6", "BTN_RIGHT")]],
    *[("GND", f"{sw}.2", f"{sw}.4", []) for sw in ("SW1", "SW2", "SW3", "SW4", "SW5", "SW6")],
    # ground: B to A to the screen; the ESP32 to UP; UP, LEFT and DOWN to RIGHT; RIGHT to the buzzer
    ("GND", "SW2.4", "SW1.4", [(14.5, 8.75), (14.5, 21), (13.17, 21)]),
    ("GND", "SW1.4", "DISP1.1", [(28.35, 22.56)]),
    ("GND", "U1.20", "SW3.2", [(51.06, 33.5), (60, 33.5), (60, 26.29)]),
    ("GND", "SW3.4", "SW6.2", [(68.49, 19.5), (70.99, 19.5)]),
    ("GND", "SW5.4", "SW6.2", []),
    ("GND", "SW4.4", "SW6.2", [(70.99, 8.29)]),
    ("GND", "SW6.4", "BZ1.2", [(79.8, 17.29), (79.8, 55.08)]),
]  # fmt: skip

BOTTOM = [
    ("BTN_B", "U1.15", "SW2.1", [(15.5, 38.5), (2.6, 38.5), (2.6, 13.25)]),
    ("GND", "U1.14", "DISP1.1", [(18.04, 40.5), (26.93, 40.5), (26.93, 28.73)]),
    ("GND", "DISP1.1", "U1.26", [(28.35, 33.9), (35.82, 33.9)]),
    ("GND", "U1.26", "U1.20", [(35.82, 37.5), (51.06, 37.5)]),
    ("SCL", "U1.22", "DISP1.3", [(45.98, 32.5), (33.43, 32.5)]),
    # the direction pad: DOWN lowest and furthest left ... RIGHT highest and furthest right
    ("BTN_DOWN", "U1.10", "SW4.1",
     [(28.2, 51), (52.4, 51), (52.4, 33), (50, 33), (50, 12.79)]),
    ("BTN_LEFT", "U1.9", "SW5.1", [(30.74, 53), (53.6, 53), (53.6, 23.5), (52.99, 23.5)]),
    ("BTN_UP", "U1.8", "SW3.1", [(33.28, 55), (61.99, 55)]),
    ("BTN_RIGHT", "U1.7", "SW6.3", [(35.82, 57), (77.49, 57)]),
]  # fmt: skip


def pad(name):
    ref, num = name.split(".")
    return brd_pad(ref, num)


ecad_open("brd")
for layer, routes in (("top", TOP), ("bottom", BOTTOM)):
    for sig, a, b, via in routes:
        brd_route(sig, [pad(a), *via, pad(b)], WIDTH, layer)
ecad("WINDOW FIT")
result = brd_report()
result["unrouted"] = {s: v["unrouted"] for s, v in result["signals"].items() if v["unrouted"]}
result["stray"] = {s: v["stray"] for s, v in result["signals"].items() if v["stray"]}
