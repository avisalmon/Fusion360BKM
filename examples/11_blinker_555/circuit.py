r"""11_blinker_555: a 555 timer blinks a red LED about once a second, from a 9 V battery.

The second board from the chat, and the first with a chip: a net now joins three, four or
five pins (board 10's nets joined two). Classic astable circuit:

    +9V -- R1 1k -- DIS -- R2 68k -- THR -- C1 10uF -- GND        U1 pins 7 (DIS), 6+2 (THR)
    U1.OUT (pin 3) -- R3 680R -- D1 (red LED) -- GND               f = 1.44 / ((R1 + 2 R2) C1)
    U1.CV (pin 5) -- C2 10nF -- GND; U1.!RST (pin 4) and V+ (pin 8) to +9V    = 1.05 Hz

    python scripts\fusion.py run examples\11_blinker_555\circuit.py 180

How it is drawn, for the person reading it:
* Power goes through symbols: every +9V arrow and every GND bar is the same net, so a part
  touches its supply where it stands instead of a long wire around the sheet.
* Signals are visible wires. One crossing cannot be avoided: on the 555's symbol pin 6 (THR)
  sits above pin 7 (DIS), while on the R1-R2-C1 chain DIS comes first. A plain crossing, with no
  dot, is NOT a connection; a dot (a pin, or a wire ending on a wire) is.
* Corners are chosen from the pins' read-back positions so no wire passes another pin; the
  netlist check at the end catches a wrong join.
Part names come from scripts/fusion_parts.py. A part whose library fixes its value (J1, U1)
gets value None (gotcha 21).
"""

PARTS = [  # ref, part as Fusion names it, value (None: fixed by its library), x, y, orientation
    ("J1", "B2B-XH-A@Connector", None, 7.62, 66.04, "MR0"),  # battery leads; pins face right
    ("U1", "NE555_DIP@IC_Clock-Timing", None, 60.96, 66.04, 0),  # TI NE555P, DIP-8
    ("R1", "RESISTOR_AXIAL-10.16MM-PITCH@Tinkercad", "1k", 91.44, 81.28, 90),
    ("R2", "RESISTOR_AXIAL-10.16MM-PITCH@Tinkercad", "68k", 91.44, 66.04, 90),
    ("C1", "10UF-POLAR-RADIAL-2.5MM-25V-20%@SparkFun-Capacitors", "10uF", 91.44, 53.34, 0),
    ("C2", "CAPACITORCERAMIC-2.54MM@Tinkercad", "10nF", 33.02, 68.58, 0),
    ("R3", "RESISTOR_AXIAL-10.16MM-PITCH@Tinkercad", "680R", 78.74, 48.26, 90),
    ("D1", "LED5MM@SparkFun-LED", "RED 5MM", 78.74, 35.56, 0),
    # supply symbols: schematic only, no footprint; +9V's pin is at its origin, GND's 2.54 mm above
    ("P1", "+9V@Power_Symbols", None, 17.78, 73.66, 0),
    ("P2", "+9V@Power_Symbols", None, 43.18, 78.74, 0),
    ("P3", "+9V@Power_Symbols", None, 78.74, 78.74, 0),
    ("P4", "+9V@Power_Symbols", None, 91.44, 88.9, 0),
    ("G1", "GND@Power_Symbols", None, 20.32, 58.42, 0),
    ("G2", "GND@Power_Symbols", None, 27.94, 60.96, 0),
    ("G3", "GND@Power_Symbols", None, 43.18, 50.8, 0),
    ("G4", "GND@Power_Symbols", None, 91.44, 43.18, 0),
    ("G5", "GND@Power_Symbols", None, 78.74, 22.86, 0),
]

WIRES = [  # net, from pin, to pin, corners (mm)
    # power: each part to the supply symbol beside it
    ("+9V", ("J1", "1"), ("P1", "+9V"), [(17.78, 68.58)]),
    ("+9V", ("U1", "!RST"), ("P2", "+9V"), [(43.18, 73.66)]),  # pin 4 high: never reset
    ("+9V", ("U1", "V+"), ("P3", "+9V"), [(78.74, 73.66)]),
    ("+9V", ("R1", "2"), ("P4", "+9V"), []),
    ("GND", ("J1", "2"), ("G1", "GND"), [(20.32, 66.04)]),
    ("GND", ("C2", "2"), ("G2", "GND"), []),
    ("GND", ("U1", "GND"), ("G3", "GND"), [(43.18, 58.42)]),
    ("GND", ("C1", "-"), ("G4", "GND"), []),
    ("GND", ("D1", "C"), ("G5", "GND"), []),
    # the timing chain R1 - R2 - C1 and the chip's pins 7, 6 and 2
    ("DIS", ("R1", "1"), ("R2", "2"), []),
    ("DIS", ("U1", "DIS"), ("R2", "2"), [(81.28, 63.5), (81.28, 71.12)]),
    ("THR", ("R2", "1"), ("C1", "+"), []),
    ("THR", ("U1", "THR"), ("R2", "1"), [(86.36, 68.58), (86.36, 60.96)]),  # the one crossing
    ("THR", ("U1", "TR"), ("C1", "+"),  # pin 2: around under the chip, to C1's + side
     [(40.64, 63.5), (40.64, 15.24), (86.36, 15.24), (86.36, 55.88)]),
    # control voltage decoupled, and the output driving the LED
    ("CV", ("U1", "CV"), ("C2", "1"), []),
    ("OUT", ("U1", "OUT"), ("R3", "2"), [(78.74, 58.42)]),
    ("LED_A", ("R3", "1"), ("D1", "A"), []),
]

ecad_new()
for ref, name, value, x, y, orient in PARTS:
    sch_place(name, ref, x, y, value, orient)
for net, a, b, via in WIRES:
    sch_wire(net, a, b, via)
ecad("WINDOW FIT")

got = sch_netlist()
want = {}
for net, a, b, _ in WIRES:
    want.setdefault(net, set()).update([a, b])
want = {net: sorted(pins) for net, pins in want.items()}
result = {"nets_match": got == want, "netlist": got}
if got != want:
    result["want"] = want
