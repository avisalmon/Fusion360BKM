r"""10_led_switch_board: battery connector, slide switch, resistor, LED.

The first board from the chat. Drawn as one visible loop, so the schematic reads as the circuit:

    J1.1 --VBAT--> SW1 --VSW--> R1 --LED_A--> D1 --GND--> back to J1.2

    python scripts\fusion.py run examples\10_led_switch_board\circuit.py 120

Part names come from `scripts/fusion_parts.py` (Fusion's own libraries, each with a 3D model).
Positions in mm on a 1.27 mm grid; the corners were chosen from the pins' read-back positions
so that no wire passes another pin. Schematic first; board, case and factory files follow.
"""

# Every part gets a value: the ERC calls a missing one an error, and the BOM line needs it
# (D1's library fixes its value; ecad_open answers Fusion's "change it anyway?" with yes).
PARTS = [  # ref, part as Fusion names it, value, x, y, orientation
    ("J1", "B2B-XH-A@Connector", None, 20.32, 30.48, "MR0"),  # mirrored: pins face the loop
    ("SW1", "SWITCH-SPDT-PTH-11.6X4.0MM@SparkFun-Switches", "SPDT", 40.64, 40.64, 0),
    ("R1", "RESISTOR_AXIAL-10.16MM-PITCH@Tinkercad", "100R", 66.04, 40.64, 0),
    ("D1", "LED5MM@SparkFun-LED", "RED 5MM", 86.36, 30.48, 0),
]

WIRES = [  # net, from pin, to pin, corners (mm)
    ("VBAT", ("J1", "1"), ("SW1", "P"), [(30.48, "J1.1y"), (30.48, 40.64)]),
    ("VSW", ("SW1", "O"), ("R1", "1"), [(53.34, 43.18), (53.34, 40.64)]),
    ("LED_A", ("R1", "2"), ("D1", "A"), [(86.36, 40.64)]),
    ("GND", ("D1", "C"), ("J1", "2"), [(86.36, 20.32), (27.94, 20.32), (27.94, "J1.2y")]),
]

ecad_new()
for ref, name, value, x, y, orient in PARTS:
    sch_place(name, ref, x, y, value, orient)
for net, a, b, via in WIRES:
    # a corner may follow a pin's height ("J1.1y"): read it back rather than assume the symbol
    pts = [(x, sch_pin(*y[:-1].split("."))[0][1] if isinstance(y, str) else y) for x, y in via]
    sch_wire(net, a, b, pts)
ecad("WINDOW FIT")

got = sch_netlist()
want = {net: sorted([a, b]) for net, a, b, _ in WIRES}
result = {"nets_match": got == want, "netlist": got}
