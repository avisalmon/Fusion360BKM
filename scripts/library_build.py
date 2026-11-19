"""Build an owner's Fusion/EAGLE library from their parts.

    python scripts\\library_build.py library\\avi_salmon          # each part's <part>\\<part>.lbr
    python scripts\\library_build.py library\\avi_salmon --check  # exit 1 if a .lbr is stale

Every part is a folder with a part.json (pins, footprint spec, location, photos), and its .lbr is
generated from those files, so it cannot drift from them: symbol, footprint (package), the
pin-to-pad map (device), and the part's store location and quantity as attributes. The 3D model
is not in the .lbr (EAGLE XML only refers to a 3D package by its cloud URN).
"""

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parent.parent
G = 2.54  # EAGLE's 0.1 inch grid: symbol pins must sit on it

# the layers a library needs (numbers and names as in Fusion's own libraries)
LAYERS = [
    (1, "Top"), (16, "Bottom"), (17, "Pads"), (18, "Vias"), (20, "Dimension"), (21, "tPlace"),
    (22, "bPlace"), (25, "tNames"), (26, "bNames"), (27, "tValues"), (28, "bValues"),
    (29, "tStop"), (30, "bStop"), (39, "tKeepout"), (40, "bKeepout"), (41, "tRestrict"),
    (42, "bRestrict"), (44, "Drills"), (45, "Holes"), (46, "Milling"), (51, "tDocu"),
    (52, "bDocu"), (91, "Nets"), (92, "Busses"), (93, "Pins"), (94, "Symbols"), (95, "Names"),
    (96, "Values"), (97, "Info"), (98, "Guide"),
]  # fmt: skip

# "power" (GND only): EAGLE's pwr, which joins the net of the pin's own name with no wire
# drawn (airwires between two parts' GND, 2026-11-19). "supply" (3V3, 5V, VCC): an ordinary pin
# that must be wired, so the schematic shows which voltage feeds what (a pwr VCC would join any
# net named "VCC").
DIRECTION = {"power": "pwr", "supply": "pas", "input": "in", "io": "io", "nc": "nc",
             "output": "out", "pas": "pas"}  # fmt: skip


def f(x):
    """A coordinate as EAGLE writes it: no float noise, no trailing zeros."""
    return f"{round(x, 4):g}"


def pin_names(pins):
    """EAGLE needs unique pin names: a name used more than once gets @<pin number>, the way
    SparkFun's libraries write GND@1, GND@21 (the schematic still shows GND)."""
    count = {}
    for _, name, *_ in pins:
        count[name] = count.get(name, 0) + 1
    return {n: (name if count[name] == 1 else f"{name}@{n}") for n, name, *_ in pins}


def footprint_pads(fp):
    """(number, x, y) of every pad, origin at the centre of the pins, seen from above; pad 1 is
    drawn square. dual_row: 1..N down the left row, N+1..2N down the right row. single_row:
    1..N from left to right."""
    n, p = fp["per_row"], fp["pitch"]
    if fp["type"] == "single_row":
        left = -(n - 1) * p / 2
        return [(i + 1, left + i * p, 0.0) for i in range(n)]
    s = fp["row_spacing"]
    top = (n - 1) * p / 2
    pads = []
    for i in range(n):
        pads.append((i + 1, -s / 2, top - i * p))
    for i in range(n):
        pads.append((n + i + 1, s / 2, top - i * p))
    return pads


def package_xml(fp):
    out = [f'<package name="{fp["name"]}">']
    out.append(f"<description>{escape(fp.get('why', ''))}</description>")
    for num, x, y in footprint_pads(fp):
        shape = ' shape="square"' if num == 1 else ""
        out.append(
            f'<pad name="{num}" x="{f(x)}" y="{f(y)}" drill="{f(fp["drill"])}" '
            f'diameter="{f(fp["pad"])}"{shape}/>'
        )
    cx, cy = fp.get("body_centre", (0, 0))  # the body's centre, measured from the pins' centre
    if "body_diameter" in fp:  # a round part (a buzzer): a circle instead of a rectangle
        w = h = fp["body_diameter"]
        for layer in (21, 51):
            out.append(
                f'<circle x="{f(cx)}" y="{f(cy)}" radius="{f(w / 2)}" width="0.2" layer="{layer}"/>'
            )
    else:
        w, h = fp["body"]
        corners = [(cx - w / 2, cy + h / 2), (cx + w / 2, cy + h / 2), (cx + w / 2, cy - h / 2),
                   (cx - w / 2, cy - h / 2)]  # fmt: skip
        for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1]):
            for layer in (21, 51):  # silkscreen and the documentation layer
                out.append(
                    f'<wire x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" width="0.2" '
                    f'layer="{layer}"/>'
                )
    out.append(f'<text x="{f(cx)}" y="{f(cy + h / 2 + 1)}" size="1.27" layer="25" '
               'align="bottom-center">>NAME</text>')  # fmt: skip
    out.append(f'<text x="{f(cx)}" y="{f(cy - h / 2 - 1)}" size="1.27" layer="27" '
               'align="top-center">>VALUE</text>')  # fmt: skip
    out.append("</package>")
    return "\n".join(out)


def symbol_xml(part, names):
    """The pins in their physical order (left row on the left, right row on the right), so the
    schematic reads like the board in your hand."""
    fp = part["footprint"]
    n = fp["per_row"]
    top = (n - 1) * G / 2
    half_w = fp.get("symbol_half_width", 5) * G  # in grid steps; a two-pin part needs less
    out = [f'<symbol name="{fp["name"]}">']
    box = [(-half_w, top + G), (half_w, top + G), (half_w, -top - G), (-half_w, -top - G)]
    for (x1, y1), (x2, y2) in zip(box, box[1:] + box[:1]):
        out.append(
            f'<wire x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" width="0.254" layer="94"/>'
        )
    for num, _name, kind, *_ in part["pins"]:
        left = num <= n
        i = (num - 1) % n
        x = -half_w - 2 * G if left else half_w + 2 * G
        rot = "" if left else ' rot="R180"'
        out.append(
            f'<pin name={quoteattr(names[num])} x="{f(x)}" y="{f(top - i * G)}" length="middle" '
            f'direction="{DIRECTION[kind]}"{rot}/>'
        )
    out.append(f'<text x="{f(-half_w)}" y="{f(top + 2 * G)}" size="1.778" layer="95">>NAME</text>')
    out.append(
        f'<text x="{f(-half_w)}" y="{f(-top - 3 * G)}" size="1.778" layer="96">>VALUE</text>'
    )
    out.append("</symbol>")
    return "\n".join(out)


def deviceset_xml(part, names):
    fp = part["footprint"]
    desc = f"{part['name']}. {part['description']} Store location: {part['location']}."
    out = [f'<deviceset name="{fp["name"]}" prefix="{part.get("prefix", "U")}" uservalue="no">']
    out.append(f"<description>{escape(desc)}</description>")
    out.append(f'<gates><gate name="G$1" symbol="{fp["name"]}" x="0" y="0"/></gates>')
    out.append(f'<devices><device name="" package="{fp["name"]}"><connects>')
    for num, *_ in part["pins"]:
        out.append(f'<connect gate="G$1" pin={quoteattr(names[num])} pad="{num}"/>')
    out.append('</connects><technologies><technology name="">')
    attrs = {"LOCATION": part["location"], "QUANTITY": part.get("quantity")}
    attrs.update(part.get("attributes", {}))
    for k, v in attrs.items():
        if v not in (None, ""):
            out.append(f"<attribute name={quoteattr(k)} value={quoteattr(str(v))}/>")
    out.append("</technology></technologies></device></devices></deviceset>")
    return "\n".join(out)


def part_folders(folder):
    return sorted(p.parent for p in Path(folder).glob("*/part.json"))


def read_part(part_folder):
    # utf-8-sig: PowerShell's Set-Content writes a BOM, which json rejects
    return json.loads((Path(part_folder) / "part.json").read_text(encoding="utf-8-sig"))


def build(part):
    """One part's .lbr. One part per file: Fusion 2706.1.17 raised "unexpected condition ...
    PlacePartWorker.cpp ... assetAdded" on every ADD from a local .lbr holding two or more parts
    (with or without attributes or urn ids), and never with one (gotcha 47)."""
    names = pin_names(part["pins"])
    layers = "\n".join(
        f'<layer number="{n}" name="{name}" color="7" fill="1" visible="yes" active="yes"/>'
        for n, name in LAYERS
    )
    body = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE eagle SYSTEM "eagle.dtd">',
        '<eagle version="9.6.2">',
        "<drawing>",
        '<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" '
        'display="no" altdistance="0.01" altunitdist="inch" altunit="inch"/>',
        f"<layers>\n{layers}\n</layers>",
        "<library>",
        f"<description>{escape(part['name'])}. Store location: {escape(str(part['location']))}. "
        "Generated by scripts/library_build.py from part.json; do not edit.</description>",
        f"<packages>\n{package_xml(part['footprint'])}\n</packages>",
        f"<symbols>\n{symbol_xml(part, names)}\n</symbols>",
        f"<devicesets>\n{deviceset_xml(part, names)}\n</devicesets>",
        "</library>",
        "</drawing>",
        "</eagle>",
        "",
    ]
    return "\n".join(body)


def add_name(part):
    """What a circuit script passes to ADD: <deviceset>@<library>, the library named by its file."""
    return f"{part['footprint']['name']}@{part['id']}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build each part's .lbr from its part.json")
    ap.add_argument("folder", help="the owner's library folder, e.g. library\\avi_salmon")
    ap.add_argument("--check", action="store_true", help="exit 1 if a .lbr is stale")
    a = ap.parse_args(argv)
    stale = 0
    for pf in part_folders(a.folder):
        part = read_part(pf)
        if "footprint" not in part:
            print(f"{pf.name}: no footprint yet, no .lbr")
            continue
        target = pf / f"{part['id']}.lbr"
        text = build(part)
        if a.check:
            old = (
                target.read_bytes().decode("utf-8").replace("\r\n", "\n") if target.exists() else ""
            )
            if old != text:
                print(f"{target} is stale: run python scripts\\library_build.py {a.folder}")
                stale += 1
            continue
        target.write_bytes(text.encode("utf-8"))
        print(f"wrote {target}  (ADD {add_name(part)})")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
