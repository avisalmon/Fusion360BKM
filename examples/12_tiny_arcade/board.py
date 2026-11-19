r"""12_tiny_arcade, step 2: the board outline, holes and placement. Run after circuit.py.

    python scripts\fusion.py run examples\12_tiny_arcade\board.py 240

Then STOP: the owner reviews the placement in Fusion, moves what they like and agrees the board size
and holes; their placement is read back into PLACE below, and only then route.py lays the tracks
(fusion-electronics, step 3).

The first proposal (2026-11-19) had the screen bottom left, the direction pad in the middle and A
and B on the right. The owner moved it into a console: A and B on the left, the screen in the
middle, the direction pad on the right, the buzzer top right; the ESP32 along the top with its USB
socket at the left edge (a cable must reach it). Every part on top.
"""

W, H = 86, 64
# M3, 3.5 mm in from the edges; the top-left corner is under the ESP32, that hole moves right
HOLES = [(3.5, 3.5), (W - 3.5, 3.5), (W - 3.5, H - 3.5), (60.5, H - 3.5)]
PLACE = [  # ref, x, y, angle (the footprint's origin is the centre of its pins)
    # the owner's placement, moved by hand in Fusion and read back with brd_elements(), 2026-11-19:
    # a game console, A and B on the left, the screen in the middle, the direction pad on the right
    ("U1", 28.2, 48.5, 270),  # pin 1 (3V3) end to the right, the USB end to the left edge
    ("DISP1", 32.16, 28.73, 0),  # pins along its top edge, the glass below them
    ("BZ1", 70.73, 55.08, 0),
    ("SW1", 9.92, 24.81, 0),  # A
    ("SW2", 8.0, 11.0, 0),  # B: moved 1.5 mm right and up off the corner screw (agreed 2026-11-19)
    ("SW3", 65.24, 28.54, 0),  # UP
    ("SW4", 65.24, 10.54, 0),  # DOWN
    ("SW5", 56.24, 19.54, 0),  # LEFT
    ("SW6", 74.24, 19.54, 0),  # RIGHT
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
