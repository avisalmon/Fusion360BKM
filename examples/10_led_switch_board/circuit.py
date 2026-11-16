r"""10_led_switch_board: battery connector, slide switch, resistor, LED.

The first board from the chat.

    python scripts\fusion.py run examples\10_led_switch_board\circuit.py

Part names come from `scripts/fusion_parts.py` (Fusion's own libraries, each with a 3D model).
Schematic first; the board, the case and the factory files come in the next steps of README.md.
"""

PARTS = [  # ref, part as Fusion names it, value, x, y (mm, schematic)
    ("J1", "B2B-XH-A@Connector", None, 10.16, 30.48),
    ("SW1", "SWITCH-SPDT-PTH-11.6X4.0MM@SparkFun-Switches", None, 40.64, 30.48),
    ("R1", "RESISTOR_AXIAL-10.16MM-PITCH@Tinkercad", "100R", 71.12, 30.48),
    ("D1", "LED5MM@SparkFun-LED", None, 101.6, 30.48),
]

NETS = {  # net name: the pins it joins
    "VBAT": [("J1", "1"), ("SW1", "P")],
    "VSW": [("SW1", "O"), ("R1", "1")],
    "LED_A": [("R1", "2"), ("D1", "A")],
    "GND": [("D1", "C"), ("J1", "2")],
}

ecad_new()
for ref, name, value, x, y in PARTS:
    sch_place(name, ref, x, y, value)
for net, pins in NETS.items():
    for ref, pin in pins:
        sch_connect(net, ref, pin)
ecad("WINDOW FIT")

got = sch_netlist()
want = {net: sorted(pins) for net, pins in NETS.items()}
result = {"nets_match": got == want, "netlist": got, "parts": [p[0] for p in PARTS]}
