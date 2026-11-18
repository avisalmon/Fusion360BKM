r"""Conclude a board: write its summary page, examples/NN_board/index.html, from the board's own files.

    python scripts\board_summary.py examples\10_led_switch_board           # write index.html
    python scripts\board_summary.py examples\10_led_switch_board --check   # exit 1 if it is stale

The page is how a board is concluded (fusion-electronics skill, last step). On it:
  verdict    ready to order or not, and why; what is still unverified (the README's "not yet" rows)
  quality    the four layers of checks: Fusion's ERC and board check (as factory.py recorded them in
             fusion/fusion_checks.json), pcb_check.py and factory_check.py (run now, on the files)
  schematic  drawn from fusion/board.sch; the board from fusion/board.brd, with layer switches;
             hover or tap a net anywhere and it lights up in both drawings, the legend and the tables
  factory    what the fab receives, drawn from the Gerbers alone (factory/preview_*.svg)
  netlist    each net traced: intent (checks.json) -> schematic -> board -> copper -> bare-board e-test
  parts, decisions (approved findings and their reasons), every check line, every file linked,
  how to rebuild, and the README's status table.
Nothing on the page is typed by hand, so it cannot drift from the files: a test runs --check.
Standard library only.
"""

import argparse
import html
import json
import math
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factory_check as fc  # noqa: E402
import pcb_check as pc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PALETTE = (
    "#e5484d",
    "#3e63dd",
    "#30a46c",
    "#f76b15",
    "#8e4ec6",
    "#12a594",
    "#d6409f",
    "#c29b00",
    "#0090ff",
    "#a18072",
)
GROUND = "#7d8799"  # ground nets are grey on every board, so the eye finds them
PIN_LEN = {"point": 0.0, "short": 2.54, "middle": 5.08, "long": 7.62}
esc = html.escape


def n(v):
    """A short number for SVG: 12.7, not 12.700000001."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def net_colors(names):
    out, i = {}, 0
    for name in names:
        if name.upper() in ("GND", "VSS", "0V", "AGND"):
            out[name] = GROUND
        else:
            out[name] = PALETTE[i % len(PALETTE)]
            i += 1
    return out


# ----------------------------------------------------------------------------- drawing helpers
def svg_text(x, y, size, rot, align, s, cls="t", fill=None):
    """EAGLE text (anchor, size = letter height, rot like 'MR90', align like 'bottom-center') as
    SVG, kept readable the way EAGLE shows it: 180 and 270 degrees turn back, mirror swaps sides."""
    mirror, a = pc.orientation(rot)
    align = align or "bottom-left"
    v, h = ("center", "center") if align == "center" else align.split("-")
    swap = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
    if mirror:
        h = swap.get(h, h)
    a %= 360
    if 90 < a <= 270:
        a -= 180
        h, v = swap.get(h, h), swap.get(v, v)
    anchor = {"left": "start", "center": "middle", "right": "end"}[h]
    base = {"bottom": "auto", "center": "central", "top": "hanging"}[v]
    tr = f' transform="rotate({n(-a)} {n(x)} {n(-y)})"' if a else ""
    style = f' fill="{fill}"' if fill else ""
    return (
        f'<text class="{cls}" x="{n(x)}" y="{n(-y)}" font-size="{n(size * 1.3)}" '
        f'text-anchor="{anchor}" dominant-baseline="{base}"{tr}{style}>{esc(s)}</text>'
    )


def shape_svg(sh, attrs, title=""):
    """A pcb_geom shape (('cap', a, b, r) or ('poly', points)) as an SVG element."""
    t = f"<title>{esc(title)}</title>" if title else ""
    if sh[0] == "cap":
        (ax, ay), (bx, by), r = sh[1], sh[2], sh[3]
        if math.dist((ax, ay), (bx, by)) < 1e-6:
            return f'<circle cx="{n(ax)}" cy="{n(-ay)}" r="{n(r)}" {attrs}>{t}</circle>'
        return (
            f'<line x1="{n(ax)}" y1="{n(-ay)}" x2="{n(bx)}" y2="{n(-by)}" '
            f'stroke-width="{n(2 * r)}" {attrs}>{t}</line>'
        )
    pts = " ".join(f"{n(x)},{n(-y)}" for x, y in sh[1])
    return f'<polygon points="{pts}" {attrs}>{t}</polygon>'


def view_box(pts, margin):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin
    return f"{n(x0)} {n(-y1)} {n(x1 - x0)} {n(y1 - y0)}"


# ----------------------------------------------------------------------------- schematic
def schematic_svg(sch_path, sch, colors):
    root = ET.parse(sch_path).getroot()
    libs = pc._libs(root)
    parts = {p.get("name"): p for p in root.iter("part")}
    net_of_pin = {}
    for net in root.iter("net"):
        for pr in net.iter("pinref"):
            net_of_pin[(pr.get("part"), pr.get("gate"), pr.get("pin"))] = net.get("name")
    body, pts, pin_at = [], [], {}
    for inst in root.iter("instance"):
        ref = inst.get("part")
        part = parts[ref]
        lib = libs.get((part.get("library"), part.get("library_urn", "")))
        ds = lib.find(f"devicesets/deviceset[@name='{part.get('deviceset')}']")
        gate = ds.find(f"gates/gate[@name='{inst.get('gate')}']")
        sym = lib.find(f"symbols/symbol[@name='{gate.get('symbol')}']")
        fn, mirror = pc._placer(float(inst.get("x")), float(inst.get("y")), inst.get("rot"))
        value = part.get("value", "")
        out = [f'<g class="part" data-part="{esc(ref)}"><title>{esc(ref)} {esc(value)}</title>']
        for w in sym.findall("wire"):
            if w.get("layer") != "94":
                continue
            q = [fn(p) for p in pc._wire_points(w)]
            pts += q
            out.append(
                f'<polyline class="sym" points="{" ".join(f"{n(x)},{n(-y)}" for x, y in q)}" '
                f'stroke-width="{n(max(float(w.get("width", 0)), 0.15))}"/>'
            )
        for c in sym.findall("circle"):
            if c.get("layer") != "94":
                continue
            (cx, cy), r, wd = (
                fn((float(c.get("x")), float(c.get("y")))),
                float(c.get("radius")),
                float(c.get("width", 0)),
            )
            pts.append((cx, cy))
            fill = (
                'class="symfill"' if wd == 0 else f'class="sym" stroke-width="{n(max(wd, 0.15))}"'
            )
            out.append(f'<circle cx="{n(cx)}" cy="{n(-cy)}" r="{n(r)}" {fill}/>')
        for r in sym.findall("rectangle"):
            if r.get("layer") != "94":
                continue
            x1, y1, x2, y2 = (float(r.get(k)) for k in ("x1", "y1", "x2", "y2"))
            q = [fn(p) for p in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
            pts += q
            out.append(
                f'<polygon class="symfill" points="{" ".join(f"{n(x)},{n(-y)}" for x, y in q)}"/>'
            )
        for pg in sym.findall("polygon"):
            if pg.get("layer") != "94":
                continue
            q = [fn((float(v.get("x")), float(v.get("y")))) for v in pg.findall("vertex")]
            out.append(
                f'<polygon class="symfill" points="{" ".join(f"{n(x)},{n(-y)}" for x, y in q)}"/>'
            )
        for p in sym.findall("pin"):
            _, pa = pc.orientation(p.get("rot"))
            length = PIN_LEN.get(p.get("length", "long"), 7.62)
            px, py = float(p.get("x")), float(p.get("y"))
            a0 = fn((px, py))
            a1 = fn(
                (px + length * math.cos(math.radians(pa)), py + length * math.sin(math.radians(pa)))
            )
            pts += [a0, a1]
            key = (ref, inst.get("gate"), p.get("name"))
            pin_at[key] = a0
            out.append(
                f'<line class="sym" x1="{n(a0[0])}" y1="{n(-a0[1])}" x2="{n(a1[0])}" y2="{n(-a1[1])}" stroke-width="0.15"/>'
            )
            if p.get("visible", "both") in ("pin", "both") and length:
                ux, uy = (a1[0] - a0[0]) / length, (a1[1] - a0[1]) / length
                d = math.degrees(math.atan2(uy, ux))
                out.append(
                    svg_text(
                        a1[0] + ux * 0.6,
                        a1[1] + uy * 0.6,
                        1.0,
                        f"R{d % 360:.0f}",
                        "center-left",
                        p.get("name"),
                        "pinname",
                    )
                )
        texts = []
        if inst.get("smashed") == "yes":
            for a in inst.findall("attribute"):
                if a.get("display", "value") != "off" and a.get("name") in ("NAME", "VALUE"):
                    texts.append(
                        (
                            float(a.get("x")),
                            float(a.get("y")),
                            pc.length(a.get("size")),
                            a.get("rot"),
                            a.get("align"),
                            a.get("name"),
                        )
                    )
        else:
            _, ia = pc.orientation(inst.get("rot"))
            for t in sym.findall("text"):
                if (t.text or "") in (">NAME", ">VALUE"):
                    tm, ta = pc.orientation(t.get("rot"))
                    x, y = fn((float(t.get("x")), float(t.get("y"))))
                    rot = f"{'M' if tm != mirror else ''}R{((-ta if mirror else ta) + ia) % 360:g}"
                    texts.append((x, y, pc.length(t.get("size")), rot, t.get("align"), t.text[1:]))
        for x, y, size, rot, align, what in texts:
            s = ref if what == "NAME" else value
            if s:
                out.append(
                    svg_text(x, y, size, rot, align, s, "name" if what == "NAME" else "value")
                )
                pts.append((x, y))
        out.append("</g>")
        body += out
    # nets: wires in the net's colour, a dot on every pin, the net's name on its longest wire
    for net in root.iter("net"):
        name = net.get("name")
        col = colors.get(name, GROUND)
        segs = []
        out = [
            f'<g class="net" data-net="{esc(name)}" style="--c:{col}"><title>{esc(name)}</title>'
        ]
        for w in net.iter("wire"):
            q = pc._wire_points(w)
            segs += list(zip(q, q[1:]))
            pts += q
            out.append(
                f'<polyline class="wire" points="{" ".join(f"{n(x)},{n(-y)}" for x, y in q)}"/>'
            )
        for j in net.iter("junction"):
            out.append(
                f'<circle class="dot" cx="{n(float(j.get("x")))}" cy="{n(-float(j.get("y")))}" r="0.55"/>'
            )
        for pr in net.iter("pinref"):
            p = pin_at.get((pr.get("part"), pr.get("gate"), pr.get("pin")))
            if p:
                out.append(
                    f'<circle class="dot" cx="{n(p[0])}" cy="{n(-p[1])}" r="0.45"><title>{esc(pr.get("part"))} pin {esc(pr.get("pin"))} · {esc(name)}</title></circle>'
                )
        labels = list(net.iter("label"))
        for lb in labels:
            out.append(
                svg_text(
                    float(lb.get("x")),
                    float(lb.get("y")),
                    pc.length(lb.get("size")) or 1.4,
                    lb.get("rot"),
                    "bottom-left",
                    name,
                    "netlabel",
                    col,
                )
            )
        if segs and not labels:
            a, b = max(segs, key=lambda s: math.dist(*s))
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if abs(a[1] - b[1]) < 1e-6:
                out.append(
                    svg_text(mx, my + 0.6, 1.4, "R0", "bottom-center", name, "netlabel", col)
                )
            else:
                out.append(
                    svg_text(mx - 0.6, my, 1.4, "R90", "bottom-center", name, "netlabel", col)
                )
        out.append("</g>")
        body += out
    # pins left free on purpose get a small cross, so "unconnected" is visibly a decision
    for key, p in pin_at.items():
        if key not in net_of_pin:
            body.append(
                f'<path class="nc" d="M{n(p[0] - 0.6)} {n(-p[1] - 0.6)}l1.2 1.2m0 -1.2l-1.2 1.2"><title>{esc(key[0])} pin {esc(key[2])}: not connected</title></path>'
            )
    return (
        f'<svg class="viz sch" viewBox="{view_box(pts, 4)}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Schematic">' + "".join(body) + "</svg>"
    )


# ----------------------------------------------------------------------------- board
def board_svg(brd, colors):
    loops, _ = pc.outline_loops(brd["outline"])
    edge = [p for lp in loops for p in lp]
    x0, x1 = min(p[0] for p in edge), max(p[0] for p in edge)
    y0, y1 = min(p[1] for p in edge), max(p[1] for p in edge)
    out = []
    for lp in loops:
        out.append(
            f'<polygon class="substrate" points="{" ".join(f"{n(x)},{n(-y)}" for x, y in lp)}"/>'
        )
    for layer, cls in ((16, "l-bottom"), (1, "l-top")):
        out.append(f'<g class="{cls}">')
        for c in brd["copper"]:
            if layer not in c["layers"]:
                continue
            sig = c["signal"]
            col = colors.get(sig, "#9aa3b5") if sig else "#9aa3b5"
            title = (
                f"{c['owner']} · {sig}"
                if c["kind"] in ("pad", "smd")
                else f"{sig} ({'bottom' if layer == 16 else 'top'})"
            )
            attr = f'data-net="{esc(sig)}" ' if sig else ""
            if c["shape"][0] == "cap" and c["kind"] == "track":
                attr += f'class="cu trk" stroke="{col}"'
            else:
                attr += f'class="cu pad" fill="{col}"'
            out.append(shape_svg(c["shape"], attr, title))
        out.append("</g>")
    out.append('<g class="l-drill">')
    seen = set()
    for c in brd["copper"]:
        if c.get("drill") and c["owner"] not in seen:
            seen.add(c["owner"])
            cx, cy = c["center"]
            out.append(
                f'<circle class="drill" cx="{n(cx)}" cy="{n(-cy)}" r="{n(c["drill"] / 2)}"/>'
            )
    for h in brd["holes"]:
        cx, cy = h["center"]
        out.append(
            f'<circle class="drill npth" cx="{n(cx)}" cy="{n(-cy)}" r="{n(h["drill"] / 2)}"><title>{esc(h["owner"])}, Ø{n(h["drill"])} mm</title></circle>'
        )
    out.append("</g>")
    out.append('<g class="l-silk">')
    for s in brd["silk"]:
        if s["layer"] in pc.SILK["top"]:
            out.append(shape_svg(s["shape"], 'class="silk"'))
    out.append("</g>")
    for lp in loops:
        out.append(f'<polygon class="edge" points="{" ".join(f"{n(x)},{n(-y)}" for x, y in lp)}"/>')
    out.append('<g class="l-labels">')
    for ref, e in sorted(brd["elements"].items()):
        bx = e["body"]
        cx, cy = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2) if bx else (e["x"], e["y"])
        out.append(
            f'<text class="ref" x="{n(cx)}" y="{n(-cy)}" text-anchor="middle" dominant-baseline="central" font-size="1.5">{esc(ref)}</text>'
        )
    out.append("</g>")
    # dimensions: the board's size, in the units the case will be designed in
    out.append(
        f'<g class="dim"><line x1="{n(x0)}" y1="{n(-y0 + 2)}" x2="{n(x1)}" y2="{n(-y0 + 2)}"/>'
        f'<text x="{n((x0 + x1) / 2)}" y="{n(-y0 + 3.6)}" text-anchor="middle" font-size="1.4">{x1 - x0:.2f} mm</text>'
        f'<line x1="{n(x1 + 2)}" y1="{n(-y0)}" x2="{n(x1 + 2)}" y2="{n(-y1)}"/>'
        f'<text x="{n(x1 + 3.4)}" y="{n(-(y0 + y1) / 2)}" text-anchor="middle" font-size="1.4" '
        f'transform="rotate(90 {n(x1 + 3.4)} {n(-(y0 + y1) / 2)})">{y1 - y0:.2f} mm</text></g>'
    )
    vb = f"{n(x0 - 2)} {n(-y1 - 2)} {n(x1 - x0 + 7)} {n(y1 - y0 + 7)}"
    return (
        f'<svg id="board" class="viz brd" viewBox="{vb}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Board, top view">' + "".join(out) + "</svg>"
    ), (x1 - x0, y1 - y0)


# ----------------------------------------------------------------------------- facts
def readme_facts(text):
    first = text.splitlines()[0].lstrip("# ").strip()
    m = re.match(r"(\d+)\s+(.*)", first)
    num, rest = (m[1], m[2]) if m else ("", first)
    title, _, tagline = rest.partition(":")
    paras = [
        p.strip()
        for p in text.split("\n\n")[1:]
        if p.strip() and not p.lstrip().startswith(("#", "|", "`", "!"))
    ]
    lead = " ".join(paras[0].split()) if paras else ""
    build = re.search(r"## Build and check\s*\n+```\w*\n(.*?)```", text, re.S)
    rows = []
    m = re.search(r"\| Step \| Done \|\n\|[-| ]+\|\n((?:\|.*\|\n?)+)", text)
    if m:
        for line in m[1].strip().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                rows.append((cells[0], cells[1]))
    return {
        "num": num,
        "title": title.strip(),
        "tagline": tagline.strip(),
        "lead": lead,
        "build": build[1].rstrip() if build else "",
        "journey": rows,
    }


def md_inline(s):
    """The little Markdown the README's table cells use: `code`, [text](link), **bold**."""
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)


FUSION_CODES = {"erc": "FUSION-ERC", "board_errors": "FUSION-BOARD"}


def approve_fusion_findings(fusion, approved):
    """A Fusion finding is approved in Fusion (its Approve button) or in checks.json with code
    FUSION-ERC / FUSION-BOARD and a `match` from its description. Fusion's API cannot approve
    (Error.state has no setter, 2706.1.17), and a click in Fusion is lost on every rebuild from the
    scripts, so the repo's approval is the one that lasts."""
    for key, code in FUSION_CODES.items():
        for e in fusion.get(key, []):
            for a in approved:
                if (
                    e.get("state") != "approved"
                    and a.get("code") == code
                    and a.get("match", "") in e.get("description", "")
                ):
                    e["state"] = "approved"
                    e["why"] = a.get("why", "no reason given")


def run_checks(folder):
    brd_path = next(iter(sorted((folder / "fusion").glob("*.brd"))))
    sch_path = brd_path.with_suffix(".sch")
    cpath = folder / "checks.json"
    checks = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else {}
    fab_path = ROOT / "production" / "fab" / f"{checks.get('fab', 'jlcpcb_2layer')}.json"
    pcb = pc.run(brd_path, sch_path, fab_path, checks)
    with tempfile.TemporaryDirectory() as tmp:  # the page must not rewrite the committed outputs
        fac = fc.run(folder / "factory", brd_path, sch_path, fab_path, tmp, checks)
    fpath = folder / "fusion" / "fusion_checks.json"
    fusion = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else None
    if fusion is not None:
        approve_fusion_findings(fusion, checks.get("approved", []))
    return {
        "brd_path": brd_path,
        "sch_path": sch_path,
        "checks": checks,
        "fab_path": fab_path,
        "fab": json.loads(fab_path.read_text(encoding="utf-8")),
        "pcb": pcb,
        "fac": fac,
        "fusion": fusion,
        "brd": pc.load_brd(brd_path),
        "sch": pc.load_sch(sch_path),
    }


def mentions(items, name, sections=None, codes=None, levels=("ERROR", "WARN")):
    pat = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
    return [
        i
        for i in items
        if i["level"] in levels
        and (sections is None or i["section"] in sections)
        and (codes is None or i["code"] in codes)
        and pat.search(i["message"])
    ]


def netlist_rows(d):
    sch, brd, checks = d["sch"], d["brd"], d["checks"]
    intent = checks.get("nets", {})
    names = list(intent) + sorted(x for x in sch["nets"] if x not in intent and sch["nets"][x])
    etest_ran = any(
        i["section"] == "etest" and i["level"] in ("OK", "ERROR") for i in d["fac"].items
    )
    rows = []
    for name in names:
        tokens = intent.get(name)
        want = set().union(*(pc.ref_pads(t, sch) for t in tokens)) if tokens else None
        have = set(sch["nets"].get(name, set()))
        board = set(brd["signals"].get(name, {}).get("contacts", set()))
        rows.append(
            {
                "name": name,
                "tokens": tokens or sorted(have),
                "pads": sorted(have or want or []),
                "intent": None if want is None else want == have,
                "board": bool(board) and board == have,
                "routed": bool(board) and not mentions(d["pcb"].items, name, ("routing",)),
                "etest": None
                if not etest_ran
                else not mentions(d["fac"].items, name, ("etest",), levels=("ERROR",)),
            }
        )
    return rows


def verdict(d):
    reasons = []
    f = d["fusion"]
    if f is None:
        reasons.append("Fusion's own checks are not recorded: run factory.py in Fusion")
    else:
        for key, what in (("erc", "Fusion's ERC"), ("board_errors", "Fusion's board check")):
            left = [e for e in f.get(key, []) if e.get("state") != "approved"]
            if left:
                reasons.append(f"{what}: {len(left)} finding(s) not approved")
    for rep, what in ((d["pcb"], "our board check"), (d["fac"], "the factory simulation")):
        e, w = rep.count("ERROR"), rep.count("WARN")
        if e or w:
            reasons.append(f"{what}: {e} error(s), {w} warning(s)")
    return not reasons, reasons


def approvals_used(d):
    out = []
    for a in d["checks"].get("approved", []):
        hits = [
            tool
            for tool, rep in (("board check", d["pcb"]), ("factory", d["fac"]))
            for i in rep.items
            if i["level"] == "APPROVED"
            and i["code"] == a.get("code")
            and a.get("match", "") in i["message"]
        ]
        hits += [
            "Fusion"
            for key, code in FUSION_CODES.items()
            for e in (d["fusion"] or {}).get(key, [])
            if a.get("code") == code and a.get("match", "") in e.get("description", "")
        ]
        out.append((a, sorted(set(hits)), len(hits)))
    return out


def smallest_gap(fac):
    vals = [
        float(m[1])
        for i in fac.items
        if i["code"] == "CLEARANCE" and i["level"] == "INFO"
        for m in [re.search(r"gap: ([\d.]+) mm", i["message"])]
        if m
    ]
    return min(vals) if vals else None


FILE_NOTES = {
    "README.md": "the story: what the board does, its parts and why, status",
    "circuit.py": "step 1, in Fusion: the schematic (parts, values, wires)",
    "board.py": "step 2, in Fusion: outline, holes, placement, routing",
    "factory.py": "step 3, in Fusion: ERC and board check, save, export, Gerbers",
    "checks.json": "the design intent (nets written by hand) and the approved findings",
    "fusion_checks.json": "Fusion's ERC and board check findings, recorded by factory.py",
    "BOM.csv": "bill of materials, JLCPCB columns",
    "CPL.csv": "pick-and-place (component placement list), JLCPCB columns",
    "preview_top.svg": "top side, drawn from the Gerbers",
    "preview_bottom.svg": "bottom side as seen from below, drawn from the Gerbers",
}
ROLE_NOTES = {
    "copper_top": "copper, top",
    "copper_bottom": "copper, bottom",
    "profile": "the board's outline (where the fab cuts)",
    "mask_top": "solder mask openings, top",
    "mask_bottom": "solder mask openings, bottom",
    "silk_top": "silkscreen (printing), top",
    "silk_bottom": "silkscreen (printing), bottom",
    "paste_top": "solder paste stencil, top",
    "paste_bottom": "solder paste stencil, bottom",
}


def file_rows(folder, brd_stem):
    stems = {stem: role for role, (stem, _) in fc.LAYER_FILES.items()}
    groups = []
    src = [p for p in sorted(folder.iterdir()) if p.is_file() and p.name != "index.html"]
    groups.append(("Source (the board is these)", src))
    groups.append(("Fusion's export (what the checks read)", sorted((folder / "fusion").glob("*"))))
    groups.append(
        (
            "Factory files (made by Fusion's CAM job and factory_check.py)",
            sorted((folder / "factory").glob("*")),
        )
    )
    groups.append(("Pictures", sorted((folder / "media").glob("*"))))
    out = []
    for title, files in groups:
        rows = []
        for p in files:
            rel = p.relative_to(folder).as_posix()
            if p.suffix == ".sch":
                note = "schematic, EAGLE 9 XML (opens in Fusion and EAGLE)"
            elif p.suffix == ".brd":
                note = "board, EAGLE 9 XML"
            elif p.suffix in (".xln", ".drl"):
                note = "drill file (Excellon): every hole, plated and not"
            elif p.suffix == ".gbr":
                note = "Gerber: " + ROLE_NOTES.get(stems.get(p.stem, ""), "a layer")
            elif p.name == f"{brd_stem}_gerbers.zip":
                note = "<b>upload this to the fab</b>: every Gerber and the drill file"
            elif p.parent.name == "media":
                note = (
                    "screenshot from Fusion"
                    if not p.stem.startswith("factory")
                    else "the factory view, rendered"
                )
            else:
                note = FILE_NOTES.get(p.name, "")
            rows.append((rel, p.stat().st_size, note))
        if rows:
            out.append((title, rows))
    return out


# ----------------------------------------------------------------------------- page
CSS = """
:root { --pcb: #1f6b3a; --pcb-edge: #d9b44a; --hole: #0f1218; --silk: #f5f5f0; --chip: #eef1f5;
  --err: #cf222e; --hl: rgba(31,111,235,.10); --paper: #fbfcfd; --sym: #1d2330; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --chip: #222936; --err: #ff7b72;
  --hl: rgba(88,166,255,.14); --paper: #12161d; --sym: #d5dbe6; } }
:root[data-theme="dark"] { --chip: #222936; --err: #ff7b72; --hl: rgba(88,166,255,.14); --paper: #12161d; --sym: #d5dbe6; }
main { max-width: 1040px; }
.verdict { display: flex; gap: 14px; align-items: flex-start; padding: 16px 18px; border-radius: 12px; margin: 14px 0 6px;
  border: 1px solid var(--ok); background: var(--panel); }
.verdict.bad { border-color: var(--err); }
.verdict .mark { flex: none; width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
  font-weight: 700; color: #fff; background: var(--ok); font-size: 19px; }
.verdict.bad .mark { background: var(--err); }
.verdict h2 { border: 0; margin: 0 0 2px; padding: 0; font-size: 20px; }
.verdict p { margin: 2px 0; color: var(--muted); }
.verdict ul { margin: 6px 0 0; padding-left: 18px; color: var(--muted); font-size: 15px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 14px 0; }
.tile { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
.tile b { display: block; font-size: 21px; line-height: 1.2; }
.tile span { font-size: 13px; color: var(--muted); }
.layers { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.layer { background: var(--panel); border: 1px solid var(--line); border-left: 5px solid var(--ok); border-radius: 10px; padding: 12px 14px; }
.layer.bad { border-left-color: var(--err); }
.layer.none { border-left-color: var(--warn); }
.layer h3 { margin: 0 0 4px; font-size: 15px; }
.layer .big { font-size: 20px; font-weight: 700; }
.layer p { margin: 4px 0 0; font-size: 13px; color: var(--muted); }
.views { display: grid; grid-template-columns: 1fr; gap: 14px; }
@media (min-width: 900px) { .views.two { grid-template-columns: 1.35fr 1fr; } }
figure { margin: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 10px; }
figcaption { font-size: 13px; color: var(--muted); padding: 6px 4px 0; }
svg.viz { display: block; width: 100%; height: auto; max-height: 460px; }
svg.sch { background: var(--paper); border-radius: 8px; }
.sch .sym { fill: none; stroke: var(--sym); stroke-linecap: round; stroke-linejoin: round; }
.sch .symfill { fill: var(--sym); }
.sch text { fill: var(--sym); font-family: ui-monospace, Consolas, monospace; }
.sch .value, .sch .pinname { fill: var(--muted); }
.sch .wire { fill: none; stroke: var(--c); stroke-width: .3; stroke-linecap: round; stroke-linejoin: round; }
.sch .dot { fill: var(--c); }
.sch .netlabel { font-weight: 700; }
.sch .nc { stroke: var(--err); stroke-width: .25; fill: none; }
.net, [data-net] { cursor: pointer; transition: opacity .15s; }
.brd .substrate { fill: var(--pcb); }
.brd .edge { fill: none; stroke: var(--pcb-edge); stroke-width: .2; }
.brd .trk { fill: none; stroke-linecap: round; }
.brd .l-bottom { opacity: .45; }
.brd .drill { fill: var(--hole); }
.brd .silk { fill: var(--silk); stroke: var(--silk); }
.brd line.silk { fill: none; stroke-linecap: round; }
.brd .ref { fill: #fff; font: 700 1.5px system-ui, sans-serif; paint-order: stroke; stroke: rgba(0,0,0,.55); stroke-width: .35px; pointer-events: none; }
.brd .dim line { stroke: var(--muted); stroke-width: .12; }
.brd .dim text { fill: var(--muted); font-family: system-ui, sans-serif; }
.hide-top .l-top, .hide-bottom .l-bottom, .hide-silk .l-silk, .hide-labels .l-labels { display: none; }
body.focus .viz [data-net]:not(.on) { opacity: .12; }
body.focus .viz [data-net].on .wire { stroke-width: .55; }
body.focus tr[data-net].on, body.focus .chip.on { background: var(--hl); }
.legend { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 4px; align-items: center; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--panel); font: 600 13px ui-monospace, Consolas, monospace; cursor: pointer; }
.chip i { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
#netinfo { font-size: 13px; color: var(--muted); min-height: 1.5em; margin: 2px 0 8px; }
.switches { display: flex; flex-wrap: wrap; gap: 14px; font-size: 14px; margin: 8px 2px 2px; }
.switches label { cursor: pointer; }
.factory { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.factory img { width: 100%; height: auto; display: block; border-radius: 6px; }
@media (max-width: 600px) { .factory { grid-template-columns: 1fr; } }
.shots { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.shots img { width: 100%; border-radius: 6px; display: block; }
.y { color: var(--ok); font-weight: 700; } .x { color: var(--err); font-weight: 700; } .q { color: var(--warn); font-weight: 700; }
.lv { display: inline-block; min-width: 76px; text-align: center; font: 700 11px system-ui, sans-serif; padding: 2px 6px; border-radius: 5px;
  background: var(--chip); color: var(--muted); letter-spacing: .03em; }
.lv.ERROR { background: var(--err); color: #fff; } .lv.WARN { background: var(--warn); color: #fff; }
.lv.APPROVED { color: var(--warn); border: 1px solid var(--warn); background: none; } .lv.OK { color: var(--ok); }
details { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; margin: 8px 0; }
details > summary { cursor: pointer; padding: 10px 14px; font-weight: 600; }
details > div { padding: 0 14px 10px; }
td code, td.mono { font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
td.num { text-align: right; white-space: nowrap; color: var(--muted); font-size: 13px; }
tr.todo td:last-child { color: var(--warn); }
.dl { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
"""

JS = """
(() => {
  let pinned = null;
  const info = document.getElementById('netinfo');
  function show(net) {
    document.body.classList.toggle('focus', !!net);
    document.querySelectorAll('[data-net]').forEach(el => el.classList.toggle('on', el.dataset.net === net));
    if (info) info.textContent = net ? (NETS[net] || net) : 'Hover or tap a net, in a drawing, the legend or a table, to follow it everywhere.';
  }
  document.addEventListener('mouseover', e => {
    if (pinned) return;
    const t = e.target.closest('[data-net]');
    show(t ? t.dataset.net : null);
  });
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-net]');
    pinned = t && t.dataset.net !== pinned ? t.dataset.net : null;
    show(pinned);
  });
  document.querySelectorAll('input[data-layer]').forEach(cb => cb.addEventListener('change', () =>
    document.getElementById('board').classList.toggle('hide-' + cb.dataset.layer, !cb.checked)));
  show(null);
})();
"""


def yes(v, ok="yes", bad="no", unknown="not run"):
    if v is None:
        return f'<span class="q">{unknown}</span>'
    return f'<span class="y">✓ {ok}</span>' if v else f'<span class="x">✗ {bad}</span>'


def kb(size):
    return f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"


def report_html(rep, title, cmd):
    e, w, a = rep.count("ERROR"), rep.count("WARN"), rep.count("APPROVED")
    parts = [
        f"<h3>{esc(title)}</h3><p><code>{esc(cmd)}</code>: <b>{e} errors, {w} warnings, {a} approved</b></p>"
    ]
    sections = []
    for i in rep.items:
        if i["section"] not in sections:
            sections.append(i["section"])
    for s in sections:
        items = [i for i in rep.items if i["section"] == s]
        bad = any(i["level"] in ("ERROR", "WARN") for i in items)
        worst = next(
            (
                lv
                for lv in ("ERROR", "WARN", "APPROVED", "INFO", "OK")
                if any(i["level"] == lv for i in items)
            ),
            "OK",
        )
        rows = "".join(
            f'<tr><td><span class="lv {i["level"]}">{i["level"]}</span></td><td class="mono">{esc(i["code"])}</td>'
            f"<td>{esc(i['message'])}</td></tr>"
            for i in items
        )
        parts.append(
            f'<details{" open" if bad else ""}><summary><span class="lv {worst}">{worst}</span> {esc(s)} '
            f'<span style="color:var(--muted);font-weight:400">({len(items)} line{"s" if len(items) != 1 else ""})</span></summary>'
            f'<div class="tablewrap"><table>{rows}</table></div></details>'
        )
    return "".join(parts)


def page(folder):
    folder = Path(folder)
    rel = folder.resolve().relative_to(ROOT).as_posix()
    facts = readme_facts((folder / "README.md").read_text(encoding="utf-8"))
    d = run_checks(folder)
    sch, brd, checks, fab = d["sch"], d["brd"], d["checks"], d["fab"]
    order = list(checks.get("nets", {})) + sorted(
        x for x in sch["nets"] if x not in checks.get("nets", {})
    )
    colors = net_colors(order)
    sch_svg = schematic_svg(d["sch_path"], sch, colors)
    brd_svg, (bw, bh) = board_svg(brd, colors)
    ready, reasons = verdict(d)
    nets = netlist_rows(d)
    todo = [step for step, done in facts["journey"] if done.lower().startswith("not yet")]
    gap = smallest_gap(d["fac"])
    tracks = [2 * c["shape"][3] for c in brd["copper"] if c["kind"] == "track"]
    drilled = {c["owner"] for c in brd["copper"] if c.get("drill")}
    layers_used = sorted({ly for c in brd["copper"] for ly in c["layers"]})
    title = f"Board {facts['num']}: {facts['title']}" if facts["num"] else facts["title"]
    h = []
    h.append(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n"
        f'<meta name="description" content="{esc(facts["lead"][:240])}">\n'
        f'<link rel="stylesheet" href="../example.css">\n<style>{CSS}</style>\n</head>\n<body>\n<main>\n'
        f'<nav class="crumbs"><a href="../../index.html">Fusion 360 BKM</a> / <a href="../index.html">Examples</a> / {esc(facts["num"])}</nav>\n'
        f'<h1>{esc(title)}</h1>\n<p class="lead">{esc(facts["tagline"].capitalize() + ". " if facts["tagline"] else "")}{esc(facts["lead"])}</p>\n'
    )
    # ---- verdict
    if ready:
        head = "Ready to order the bare board"
        sub = "Every check below passes: Fusion's own, ours against the fab's limits, and the simulated factory."
    else:
        head = "Not ready to order"
        sub = "Fix these first:"
    items = "".join(f"<li>{esc(r)}</li>" for r in reasons)
    if todo:
        items += "".join(f"<li>Not verified yet: {md_inline(t)}</li>" for t in todo)
    h.append(
        f'<section class="verdict{"" if ready else " bad"}"><div class="mark">{"✓" if ready else "!"}</div><div>'
        f"<h2>{head}</h2><p>{sub}</p><ul>{items}</ul></div></section>\n"
    )
    zipname = f"{d['brd_path'].stem}_gerbers.zip"
    h.append('<div class="dl">')
    if (folder / "factory" / zipname).exists():
        h.append(
            f'<a class="btn" href="factory/{zipname}" download>Download {zipname} (upload this to the fab)</a>'
        )
    h.append(
        '<a class="btn alt" href="#files">Every file</a><a class="btn alt" href="README.md">README</a></div>\n'
    )
    # ---- at a glance
    tiles = [
        (f"{bw:.0f} × {bh:.0f} mm", "board size"),
        (f"{len(layers_used)} layers", "copper"),
        (str(len(brd["elements"])), "parts"),
        (str(len([x for x in sch["nets"] if sch["nets"][x]])), "nets"),
        (str(len(drilled) + len(brd["holes"])), "holes"),
        (f"{min(tracks):.2f} mm" if tracks else "-", "narrowest track"),
        (f"{gap:.3f} mm" if gap is not None else "-", "smallest copper gap"),
        (fab["name"].split(" ")[0], f"fab, limits read {fab.get('read', '?')}"),
    ]
    h.append(
        '<div class="tiles">'
        + "".join(f'<div class="tile"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in tiles)
        + "</div>\n"
    )
    # ---- quality: the four layers
    h.append(
        "<h2>Quality: four layers of checks</h2>\n<p>Each layer catches what the others cannot "
        '(<a href="../../docs/procedures/board_checks_and_factory.md">how they work</a>).</p>\n<div class="layers">'
    )
    f = d["fusion"]
    for key, name, what in (
        ("erc", "1. Fusion's ERC", "the schematic's electrical rules"),
        ("board_errors", "2. Fusion's board check", "airwires, overlaps, Fusion's rules"),
    ):
        if f is None:
            h.append(
                f'<div class="layer none"><h3>{name}</h3><div class="big">not recorded</div><p>run factory.py in Fusion</p></div>'
            )
            continue
        lst = f.get(key, [])
        left = [e for e in lst if e.get("state") != "approved"]
        detail = "; ".join(e.get("description", "") for e in left[:3])
        h.append(
            f'<div class="layer{" bad" if left else ""}"><h3>{name}</h3><div class="big">'
            f"{'clean' if not left else f'{len(left)} open'}</div><p>{esc(what)}. Run {esc(f.get('date', '?'))}, "
            f"Fusion {esc(f.get('fusion', '?'))}{': ' + esc(detail) if detail else ''}"
            f"{f'; {len(lst) - len(left)} approved, with reasons (below)' if len(lst) - len(left) else ''}</p></div>"
        )
    for rep, name, what in (
        (d["pcb"], "3. Our board check", "netlist, schematic = board, routing, the fab's limits"),
        (
            d["fac"],
            "4. The simulated factory",
            "the Gerbers and drill file, read as the fab does; the e-test",
        ),
    ):
        e, w, a = rep.count("ERROR"), rep.count("WARN"), rep.count("APPROVED")
        h.append(
            f'<div class="layer{" bad" if e or w else ""}"><h3>{name}</h3><div class="big">{e} errors · {w} warnings</div>'
            f"<p>{esc(what)}. {a} approved, with reasons (below).</p></div>"
        )
    h.append("</div>\n")
    # ---- drawings
    legend = "".join(
        f'<span class="chip" data-net="{esc(x)}"><i style="background:{colors[x]}"></i>{esc(x)}</span>'
        for x in order
        if sch["nets"].get(x)
    )
    nets_js = {r["name"]: f"{r['name']}: {', '.join(r['pads'])}" for r in nets}
    h.append(
        "<h2>The circuit and the board</h2>\n"
        f'<div class="legend">{legend}</div><div id="netinfo"></div>\n'
        '<div class="views two">'
        f'<figure>{sch_svg}<figcaption>Schematic, drawn from <a href="fusion/{d["sch_path"].name}">fusion/{d["sch_path"].name}</a>. '
        "Net names on the wires; a red cross marks a pin left free on purpose.</figcaption></figure>"
        f'<figure>{brd_svg}<div class="switches">'
        '<label><input type="checkbox" data-layer="top" checked> top copper</label>'
        '<label><input type="checkbox" data-layer="bottom" checked> bottom copper</label>'
        '<label><input type="checkbox" data-layer="silk" checked> silkscreen</label>'
        '<label><input type="checkbox" data-layer="labels" checked> part names</label></div>'
        f'<figcaption>Board, top view, drawn from <a href="fusion/{d["brd_path"].name}">fusion/{d["brd_path"].name}</a>; '
        "bottom copper shows through, faded. Copper is coloured by net.</figcaption></figure></div>\n"
    )
    shots = [p for p in ("media/schematic.png", "media/board.png") if (folder / p).exists()]
    if (folder / "factory" / "preview_top.svg").exists():
        h.append(
            "<h3>What the factory receives</h3><p>Drawn from the Gerber and drill files alone, as the fab's viewer "
            "draws them: copper under the mask, mask openings (gold), silkscreen, holes.</p>"
            '<div class="factory"><figure><img src="factory/preview_top.svg" alt="Top side from the Gerbers"><figcaption>top</figcaption></figure>'
            '<figure><img src="factory/preview_bottom.svg" alt="Bottom side from the Gerbers"><figcaption>bottom, seen from below</figcaption></figure></div>\n'
        )
    if shots:
        h.append(
            '<h3>In Fusion</h3><div class="shots">'
            + "".join(
                f'<figure><img src="{p}" alt="{esc(Path(p).stem)} in Fusion" loading="lazy"><figcaption>{esc(Path(p).stem)}, screenshot from Fusion</figcaption></figure>'
                for p in shots
            )
            + "</div>\n"
        )
    # ---- netlist
    h.append(
        "<h2>The netlist, traced from intent to copper</h2>\n<p>Each net, followed through every stage. The intent is "
        '<a href="checks.json">checks.json</a>, written by hand from the agreed circuit, so a wire to the wrong pin shows up here.</p>'
        '<div class="tablewrap"><table><tr><th>Net</th><th>Connects</th><th>As intended</th><th>Board = schematic</th>'
        "<th>Routed</th><th>Bare-board e-test</th></tr>"
    )
    for r in nets:
        tok = []
        for t in r["tokens"]:
            pads = sorted(pc.ref_pads(t, sch))
            extra = (
                f' <span style="color:var(--muted)">(pad {", ".join(p.split(".", 1)[1] for p in pads)})</span>'
                if pads != [t]
                else ""
            )
            tok.append(f"<code>{esc(t)}</code>{extra}")
        h.append(
            f'<tr data-net="{esc(r["name"])}"><td><span class="chip" data-net="{esc(r["name"])}"><i style="background:{colors.get(r["name"], GROUND)}"></i>{esc(r["name"])}</span></td>'
            f"<td>{', '.join(tok)}</td><td>{yes(r['intent'], 'yes', 'differs', 'not in the intent')}</td>"
            f"<td>{yes(r['board'], 'same', 'differs')}</td><td>{yes(r['routed'], 'joined', 'open')}</td>"
            f"<td>{yes(r['etest'], 'passes', 'fails')}</td></tr>"
        )
    h.append("</table></div>\n")
    free = checks.get("unconnected_ok", [])
    if free:
        h.append(
            f"<p>Left free on purpose: {', '.join(f'<code>{esc(x)}</code>' for x in free)}.</p>\n"
        )
    # ---- parts
    h.append(
        '<h2>Parts</h2><div class="tablewrap"><table><tr><th>Ref</th><th>Value</th><th>Footprint</th><th>Side</th>'
        "<th>3D model</th><th>MPN</th><th>LCSC</th></tr>"
    )
    for ref, e in sorted(brd["elements"].items()):
        lcsc = next((e["attributes"][k] for k in fc.LCSC_KEYS if e["attributes"].get(k)), "")
        h.append(
            f'<tr><td><b>{esc(ref)}</b></td><td>{esc(e["value"])}</td><td class="mono">{esc(e["package"])}</td>'
            f"<td>{'bottom' if e['mirror'] else 'top'}</td><td>{yes(bool(e['model3d']), 'yes', 'missing')}</td>"
            f'<td class="mono">{esc(e["attributes"].get("MPN", "")) or "-"}</td><td class="mono">{esc(lcsc) or "-"}</td></tr>'
        )
    h.append(
        '</table></div><p>The same as <a href="factory/BOM.csv">BOM.csv</a> and <a href="factory/CPL.csv">CPL.csv</a>; '
        "the README says why each part was chosen.</p>\n"
    )
    # ---- decisions
    used = approvals_used(d)
    if used:
        h.append(
            "<h2>Decisions: findings accepted, with the reason</h2>\n<p>An approval is a decision, not silence: the finding "
            "stays in the report, marked APPROVED. One that matches nothing any more is stale and is flagged.</p>"
            '<div class="tablewrap"><table><tr><th>Finding</th><th>Matches</th><th>Why it is fine</th><th>Seen in</th></tr>'
        )
        for a, tools, count in used:
            seen = (
                esc(", ".join(tools)) + (f" ({count})" if count > 1 else "")
                if tools
                else '<span class="x">nothing: stale, remove it</span>'
            )
            h.append(
                f'<tr><td class="mono">{esc(a.get("code", ""))}</td><td><code>{esc(a.get("match", ""))}</code></td>'
                f"<td>{esc(a.get('why', ''))}</td><td>{seen}</td></tr>"
            )
        h.append("</table></div>\n")
    # ---- full reports
    brd_rel = f"{rel}/fusion/{d['brd_path'].name}"
    h.append("<h2>Every check, line by line</h2>\n")
    if f is not None:
        rows = (
            "".join(
                f'<tr><td><span class="lv {"OK" if e.get("state") == "approved" else "ERROR"}">{esc(e.get("state", ""))}</span></td>'
                f"<td>{esc(e.get('type', ''))}</td><td>{esc(e.get('description', ''))}"
                f"{' (approved: ' + esc(e['why']) + ')' if e.get('why') else ''}</td></tr>"
                for key in ("erc", "board_errors")
                for e in f.get(key, [])
            )
            or '<tr><td><span class="lv OK">OK</span></td><td colspan="2">no findings in Fusion\'s ERC or board check</td></tr>'
        )
        h.append(
            f'<h3>Fusion</h3><p>Recorded in <a href="fusion/fusion_checks.json">fusion/fusion_checks.json</a> by factory.py.</p>'
            f'<div class="tablewrap"><table>{rows}</table></div>'
        )
    h.append(
        report_html(
            d["pcb"],
            "Our board check",
            f"python scripts\\pcb_check.py {brd_rel}".replace("/", "\\"),
        )
    )
    h.append(
        report_html(
            d["fac"],
            "The simulated factory",
            f"python scripts\\factory_check.py {rel}/factory".replace("/", "\\"),
        )
    )
    # ---- files
    h.append(
        '<h2 id="files">Every file</h2>\n<p>The repo holds the board; Fusion\'s cloud copy is only a vehicle, overwritten '
        "on every build.</p>"
    )
    for title_, rows in file_rows(folder, d["brd_path"].stem):
        h.append(
            f'<h3>{esc(title_)}</h3><div class="tablewrap"><table>'
            + "".join(
                f'<tr><td class="mono"><a href="{esc(r)}">{esc(r)}</a></td><td>{note}</td><td class="num">{kb(size)}</td></tr>'
                for r, size, note in rows
            )
            + "</table></div>"
        )
    shared = [
        (
            f"../../production/fab/{d['fab_path'].name}",
            f"the fab's limits: {fab['name']}, read {fab.get('read', '?')} from {fab.get('source', '')}",
        ),
        ("../../production/cam/two_layer.cam", "the CAM job that makes the Gerbers and drill file"),
        (
            "../../docs/procedures/board_checks_and_factory.md",
            "how every check works, and what each finding means",
        ),
    ]
    h.append(
        '<h3>Shared by every board</h3><div class="tablewrap"><table>'
        + "".join(
            f'<tr><td class="mono"><a href="{esc(p)}">{esc(p.replace("../../", ""))}</a></td><td>{esc(t)}</td></tr>'
            for p, t in shared
        )
        + "</table></div>\n"
    )
    # ---- rebuild and journey
    if facts["build"]:
        h.append(
            f"<h2>Rebuild it from nothing</h2>\n<pre><code>{esc(facts['build'])}</code></pre>\n"
        )
    if facts["journey"]:
        h.append(
            '<h2>Status, step by step</h2><div class="tablewrap"><table><tr><th>Step</th><th>Done</th></tr>'
            + "".join(
                f'<tr class="{"todo" if done.lower().startswith("not yet") else ""}"><td>{md_inline(step)}</td><td>{md_inline(done)}</td></tr>'
                for step, done in facts["journey"]
            )
            + "</table></div>\n"
        )
    h.append(
        f"<footer>Generated by <code>python scripts\\board_summary.py {esc(rel)}</code> from the files above; nothing here is "
        "typed by hand. A test fails when this page is older than the files.</footer>\n"
        f"</main>\n<script>const NETS = {json.dumps(nets_js, ensure_ascii=False)};{JS}</script>\n</body>\n</html>\n"
    )
    return "".join(h)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Write a board's summary page (index.html) from its files."
    )
    ap.add_argument("folder", help="the board's example folder, e.g. examples\\10_led_switch_board")
    ap.add_argument(
        "--check", action="store_true", help="exit 1 if the committed page differs from a fresh one"
    )
    a = ap.parse_args(argv)
    folder = Path(a.folder).resolve()
    os.chdir(
        ROOT
    )  # messages name files relative to the repo, so the page is the same on every machine
    folder = folder.relative_to(ROOT)
    text = page(folder)
    target = folder / "index.html"
    if a.check:
        old = target.read_bytes().decode("utf-8").replace("\r\n", "\n") if target.exists() else ""
        if old != text:
            print(f"{target} is stale: run python scripts\\board_summary.py {folder}")
            return 1
        print(f"{target} is up to date")
        return 0
    target.write_bytes(text.encode("utf-8"))
    print(f"wrote {target} ({len(text) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
