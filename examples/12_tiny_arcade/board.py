r"""12_tiny_arcade, step 2: the board outline, holes and placement. Run after circuit.py.

    python scripts\fusion.py run examples\12_tiny_arcade\board.py 240

Then STOP: the owner reviews the placement in Fusion, moves what they like and agrees the board size
and holes; their placement is read back into PLACE below, and only then route.py lays the tracks
(fusion-electronics, step 3).

First proposal (2026-11-19), small and laid out like the owner's "ESP32 Tiny Arcade": the ESP32
along the top with its USB socket at the left edge (a cable must reach it), the screen bottom left,
the direction pad in the middle, A and B to the right (B lower, A higher, as on a game pad), the
buzzer top right. Every part on top.
"""

W, H = 86, 64
# M3, 3.5 mm in from the edges; the top-left corner is under the ESP32, that hole moves right
HOLES = [(3.5, 3.5), (W - 3.5, 3.5), (W - 3.5, H - 3.5), (60.5, H - 3.5)]
PLACE = [  # ref, x, y, angle (the footprint's origin is the centre of its pins)
    ("U1", 28.2, 48.5, 270),  # pin 1 (3V3) end to the right, the USB end to the left edge
    ("DISP1", 22, 30, 0),  # pins along its top edge, the glass below them
    ("BZ1", 72, 50, 0),
    ("SW3", 50, 26, 0),  # UP
    ("SW4", 50, 8, 0),  # DOWN
    ("SW5", 41, 17, 0),  # LEFT
    ("SW6", 59, 17, 0),  # RIGHT
    ("SW2", 70, 12, 0),  # B
    ("SW1", 78.5, 21, 0),  # A
]

ecad_open("brd")
brd_outline(W, H)
for x, y in HOLES:
    brd_hole(x, y)
for ref, x, y, a in PLACE:
    brd_move(ref, x, y, a)
brd_name_size(1.0)
ecad("WINDOW FIT")

result = brd_report()
# the ESP32's GND pins join GND by name (pins of the "power" kind): the board's GND signal must
# hold them, since no schematic wire does
gnd = next(s for s in brd().signals if s.name == "GND")
result["gnd_pads_of_U1"] = sorted(c.contact.name for c in gnd.contactRefs if c.element.name == "U1")
