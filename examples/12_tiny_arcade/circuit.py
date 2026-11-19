r"""12_tiny_arcade: the Single Button kit (SingleButtonKitBKM) as a small game board, six buttons.

The first board built from the owner's own library (library/avi_salmon/): every part is a real part
from his store, with its pins confirmed on the part itself. The kit's wiring is kept, so its
programs (Flappy) run unchanged; five buttons are added on free pins:

    screen SCL / SDA -> G22 / G21, VCC -> 3V3, GND -> GND        (the kit's pins)
    buzzer + -> G23, - -> GND                                      (the kit's pin)
    A -> G4 (the kit's one button), B -> G13
    UP / DOWN / LEFT / RIGHT -> G33 / G26 / G25 / G32
    (chosen so the four tracks reach the direction pad on the board without crossing: the pin
    furthest right on the ESP32 goes to the button furthest right, 2026-11-19)
    every button's other contact -> GND; the program turns on the pin's internal pull-up
    (released reads 1, pressed 0), so no resistors

Pins avoided: 0, 2, 5, 12, 15 (they decide how the ESP32 starts), 1 and 3 (USB serial), 6-11
(flash), 34-39 (input-only with no internal pull-up).

    python scripts\fusion.py run examples\12_tiny_arcade\circuit.py 240

How it is drawn: the ESP32 in the middle; each button sits level with its pin on the side where
that pin is, so the five on the left reach their pins with one corner each, in the order of the
pins, and no wire crosses another. Ground and 3V3 go through supply symbols. The ESP32's three GND
pins and the screen's GND are the "power" kind: they join the GND net by name as well.
"""

LIB = "C:/Projects/Fusion360BKM/library/avi_salmon"
USES = ["esp32_devkitc_38", "oled_096_i2c", "buzzer_tmb12a03", "tact_switch_6x6"]
ESP = "ESP32_DEVKITC_38@esp32_devkitc_38"
OLED = "OLED_096_I2C_4P@oled_096_i2c"
BUZ = "BUZZER_TMB12A03@buzzer_tmb12a03"
SW = "TACT_SWITCH_6X6@tact_switch_6x6"
GND = "GND@Power_Symbols"
V33 = "3V3@Power_Symbols"

PARTS = [  # ref, part, x, y, orientation (our parts fix their own value)
    ("U1", ESP, 101.6, 76.2, 0),
    ("DISP1", OLED, 154.94, 90.17, 0),  # pins GND, VCC, SCL, SDA at x 137.16, y 93.98 .. 86.36
    ("BZ1", BUZ, 139.7, 105.41, 0),  # + at y 106.68, - at 104.14
    ("SW1", SW, 134.62, 67.31, 0),  # A, level with G4 (68.58) on the right
    # the left-hand buttons, turned 180 degrees: contact 1 faces the ESP32, contact 2 the ground
    ("SW6", SW, 50.8, 107.95, 180),  # RIGHT, contacts at y 106.68
    ("SW3", SW, 50.8, 95.25, 180),  # UP, 93.98
    ("SW5", SW, 50.8, 82.55, 180),  # LEFT, 81.28
    ("SW4", SW, 50.8, 69.85, 180),  # DOWN, 68.58
    ("SW2", SW, 50.8, 57.15, 180),  # B, 55.88
    ("P1", V33, 81.28, 104.14, 0),
    ("P2", V33, 132.08, 91.44, 90),  # beside the screen's VCC, pointing left
    ("G1", GND, 40.64, 99.06, 0),
    ("G2", GND, 40.64, 86.36, 0),
    ("G3", GND, 40.64, 73.66, 0),
    ("G4", GND, 40.64, 60.96, 0),
    ("G5", GND, 40.64, 48.26, 0),
    ("G6", GND, 144.78, 60.96, 0),
    ("G7", GND, 127.0, 99.06, 0),
    ("G8", GND, 129.54, 93.98, 270),  # beside the screen's GND, pointing left
]

WIRES = [  # net, from pin, to pin, corners (mm)
    # the direction pad and B: one corner each, the corners further out for the higher pins
    ("BTN_RIGHT", ("SW6", "1"), ("U1", "G32"), [(78.74, 106.68), (78.74, 83.82)]),
    ("BTN_UP", ("SW3", "1"), ("U1", "G33"), [(76.2, 93.98), (76.2, 81.28)]),
    ("BTN_LEFT", ("SW5", "1"), ("U1", "G25"), [(73.66, 81.28), (73.66, 78.74)]),
    ("BTN_DOWN", ("SW4", "1"), ("U1", "G26"), [(71.12, 68.58), (71.12, 76.2)]),
    ("BTN_B", ("SW2", "1"), ("U1", "G13"), [(68.58, 55.88), (68.58, 63.5)]),
    ("BTN_A", ("U1", "G4"), ("SW1", "1"), []),
    ("GND", ("SW6", "2"), ("G1", "GND"), []),
    ("GND", ("SW3", "2"), ("G2", "GND"), []),
    ("GND", ("SW5", "2"), ("G3", "GND"), []),
    ("GND", ("SW4", "2"), ("G4", "GND"), []),
    ("GND", ("SW2", "2"), ("G5", "GND"), []),
    ("GND", ("SW1", "2"), ("G6", "GND"), []),
    # the buzzer, up and over: + from G23, - to its own ground
    ("BUZZER", ("U1", "G23"), ("BZ1", "+"), [(121.92, 96.52), (121.92, 106.68)]),
    ("GND", ("BZ1", "-"), ("G7", "GND"), [(127.0, 104.14)]),
    # the screen: SDA straight across, SCL down one step, supply from the symbols beside it
    ("SDA", ("U1", "G21"), ("DISP1", "SDA"), []),
    ("SCL", ("U1", "G22"), ("DISP1", "SCL"), [(124.46, 93.98), (124.46, 88.9)]),
    ("3V3", ("DISP1", "VCC"), ("P2", "3V3"), []),
    ("GND", ("DISP1", "GND"), ("G8", "GND"), []),
    ("3V3", ("U1", "3V3"), ("P1", "3V3"), [(81.28, 99.06)]),
]

NAMES = [  # what each button does, printed beside it (the pins already name the screen's lines)
    ("RIGHT", 27.94, 106.68), ("UP", 27.94, 93.98), ("LEFT", 27.94, 81.28), ("DOWN", 27.94, 68.58),
    ("B", 27.94, 55.88), ("A", 147.32, 72.39),
]  # fmt: skip

# the ESP32's GND pins are of the "power" kind: they join GND by name, with no wire. The schematic's
# nets do not list them (read 2026-11-19); the board's GND signal does, checked in board.py

for i in range(app.documents.count - 1, -1, -1):  # earlier unsaved tries of this board
    d = app.documents.item(i)
    if d.name.startswith("Untitled") and not d.dataFile:
        d.close(False)
ecad_new()
for p in USES:
    ecad(f"USE '{LIB}/{p}/{p}.lbr'")
for ref, name, x, y, orient in PARTS:
    sch_place(name, ref, x, y, None, orient)
for net, a, b, via in WIRES:
    sch_wire(net, a, b, via)
for text, x, y in NAMES:
    ecad(f"TEXT '{text}' R0 ({x} {y})")
ecad("WINDOW FIT")

got = sch_netlist()
want = {}
for net, a, b, _ in WIRES:
    want.setdefault(net, set()).update([a, b])
want = {net: sorted(pins) for net, pins in want.items()}
result = {"nets_match": got == want, "netlist": got}
if got != want:
    result["want"] = want
