r"""11_blinker_555, step 2: the board outline, holes and placement. Run after circuit.py.

    python scripts\fusion.py run examples\11_blinker_555\board.py 180

Then STOP: the owner reviews the placement in Fusion, moves what they like and agrees the board size
and holes; their placement is read back into PLACE below, and only then route.py lays the tracks
(fusion-electronics, step 3).

45 x 31 mm, four M3 holes, every part on top. The placement is the owner's (moved by hand in Fusion
on 2026-11-18, read back with brd_elements(), the whole group shifted 2 mm down and left when the
board was shrunk from 50 x 40):U1 in the middle, C2 straight under pin 5
(CV), R2 and C1 to the right on pin 5's row, R1 lying across the top, R3 and the LED to the left,
the battery clip's header J1 top left.
"""

W, H = 45, 31
# M3, 3.5 mm in from the edges; the fourth is not in its corner but to the right of R2, so the board
# could lose its empty top strip (R1's pad would have been under the screw head; agreed 2026-11-18)
HOLES = [(3.5, 3.5), (W - 3.5, 3.5), (3.5, H - 3.5), (W - 3.5, 21.5)]
PLACE = [  # ref, x, y, angle
    ("U1", 23.27, 14.92, 0),  # pin 1 top left, pins 1-4 down the left side, 5-8 up the right side
    ("R1", 33.54, 26.35, 180),  # lying across the top: pad 2 (+9V) left, pad 1 (DIS) right
    ("R2", 36, 16.19, 90),  # pad 1 (THR) level with pin 5, pad 2 (DIS) up
    ("C1", 40.5, 11.11, 180),  # + (pad 1) facing R2 on the same row, - (pad 2) outwards
    ("C2", 27.4, 5.42, 270),  # straight under pin 5 (CV): pad 1 up, pad 2 (GND) down
    ("R3", 14.54, 12.38, 90),  # pad 2 (OUT) up, pad 1 down to the LED
    ("D1", 4.46, 12.38, 180),  # anode facing R3, cathode (GND) outwards
    ("J1", 10, 23.38, 0),  # the battery clip's header, top left
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
