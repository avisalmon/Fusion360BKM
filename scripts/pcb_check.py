r"""Check a board the way a careful reviewer and the factory would, from Fusion's EAGLE export.

    python scripts\pcb_check.py examples\10_led_switch_board\fusion\board.brd
        [--sch ...\board.sch]  (default: the .sch next to the .brd)
        [--fab production\fab\jlcpcb_2layer.json] [--checks ...\checks.json] [--json report.json]

Standard library only; no Fusion needed (CI runs it on the committed export). Exit 1 on any ERROR.

Sections:
  netlist   the schematic's own nets: single-pin nets, pins left unconnected, parts shorted across
            their own pins, unnamed nets, missing values; and the intended netlist from
            checks.json ("nets"), if given
  match     schematic against board: same parts, packages, values, and the same pads in each net
  parts     part bodies overlapping, parts without a 3D model, parts without an MPN (info)
  routing   every signal's pads joined by copper (tracks, pads, vias); stray tracks
  rules     our own rule check against the fab profile: track width, copper clearance and shorts,
            copper to board edge, everything inside the outline, drills, annular rings, hole
            spacing, holes to copper, silkscreen line width, text height and silk on pads
  ruleset   Fusion's own design rules (in the export) compared with the fab's: a looser Fusion
            rule means Fusion's check passes what the fab rejects
checks.json may approve a finding ("approved": [{"code", "match", "why"}]): it stays in the
report as APPROVED, with the reason, and no longer fails the check.
"""

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pcb_geom as g  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FAB = ROOT / "production" / "fab" / "jlcpcb_2layer.json"
FLIP = {
    1: 16,
    16: 1,
    21: 22,
    22: 21,
    25: 26,
    26: 25,
    27: 28,
    28: 27,
    29: 30,
    30: 29,
    31: 32,
    32: 31,
}
SILK = {"top": (21, 25), "bottom": (22, 26)}  # tPlace + tNames: what the CAM job prints
COPPER = (1, 16)
BODY = (21, 22, 39, 40, 51, 52)  # placement, keep-out and documentation drawings: the body


def length(v, default=0.0):
    """'6mil', '0.35mm', '0.1in', '12' (mm) -> mm."""
    if v is None or v == "":
        return default
    v = str(v).strip()
    for unit, k in (("mil", 0.0254), ("mm", 1.0), ("mic", 0.001), ("in", 25.4)):
        if v.endswith(unit):
            return float(v[: -len(unit)]) * k
    return float(v)


def orientation(rot):
    """EAGLE 'MR270' -> (mirrored, 270.0)."""
    rot = rot or "R0"
    return "M" in rot, float("".join(c for c in rot if c.isdigit() or c == ".") or 0)


class Report:
    def __init__(self, approvals=()):
        self.items = []
        self.approvals = list(approvals)

    def add(self, level, section, code, msg):
        if level in ("ERROR", "WARN"):
            for a in self.approvals:
                if a.get("code") == code and a.get("match", "") in msg:
                    level = "APPROVED"
                    msg = f"{msg} (approved: {a.get('why', 'no reason given')})"
                    break
        self.items.append({"level": level, "section": section, "code": code, "message": msg})

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)

    def problems(self, section):
        return sum(1 for i in self.items if i["section"] == section and i["level"] != "OK")


# ----------------------------------------------------------------------------- schematic
def _libs(root):
    return {(lb.get("name"), lb.get("urn", "")): lb for lb in root.iter("library")}


def load_sch(path):
    root = ET.parse(path).getroot()
    libs = _libs(root)
    parts = {}
    for p in root.iter("part"):
        lib = libs.get((p.get("library"), p.get("library_urn", "")))
        ds = dev = None
        if lib is not None:
            ds = lib.find(f"devicesets/deviceset[@name='{p.get('deviceset')}']")
        if ds is not None:
            dev = ds.find(f"devices/device[@name='{p.get('device', '')}']")
        connects = {}
        if dev is not None:
            for c in dev.iter("connect"):
                connects[(c.get("gate"), c.get("pin"))] = c.get("pad").split()
        # pins of direction "pwr" join the net of their own name (GND@14 joins GND) with no wire:
        # EAGLE's supply pins, and Fusion's board puts their pads on that signal (board 12)
        supply = {}
        if ds is not None and lib is not None:
            for g in ds.iter("gate"):
                sym = lib.find(f"symbols/symbol[@name='{g.get('symbol')}']")
                for pin in sym.iter("pin") if sym is not None else ():
                    if pin.get("direction") == "pwr":
                        supply[(g.get("name"), pin.get("name"))] = pin.get("name").split("@")[0]
        parts[p.get("name")] = {
            "package": dev.get("package") if dev is not None else None,
            "value": p.get("value", ""),
            "uservalue": ds is not None and ds.get("uservalue") == "yes",
            "connects": connects,
            "supply": supply,
            "found": dev is not None,
        }
    nets, used = {}, set()
    for n in root.iter("net"):
        pads = nets.setdefault(n.get("name"), set())
        for pr in n.iter("pinref"):
            key = (pr.get("part"), pr.get("gate"), pr.get("pin"))
            used.add(key)
            for pad in parts.get(key[0], {}).get("connects", {}).get(key[1:], []):
                pads.add(f"{key[0]}.{pad}")
    for ref, p in parts.items():
        for (gate, pin), net in p["supply"].items():
            if (ref, gate, pin) not in used and (gate, pin) in p["connects"]:
                used.add((ref, gate, pin))
                for pad in p["connects"][(gate, pin)]:
                    nets.setdefault(net, set()).add(f"{ref}.{pad}")
    unconnected = [
        (ref, pin, pads)
        for ref, p in parts.items()
        if p["package"]
        for (gate, pin), pads in p["connects"].items()
        if (ref, gate, pin) not in used
    ]
    return {"parts": parts, "nets": nets, "unconnected": unconnected}


# ----------------------------------------------------------------------------- board
def _rules(root):
    dr = root.find(".//designrules")
    return {p.get("name"): p.get("value") for p in (dr.iter("param") if dr is not None else [])}


def _restring(rules, drill, kind, side):
    rv = float(rules.get(f"rv{kind}{side}", 0.25))
    lo = length(rules.get(f"rlMin{kind}{side}", "10mil"))
    hi = length(rules.get(f"rlMax{kind}{side}", "20mil"))
    return min(max(drill * rv, lo), hi)


def pad_diameter(pad, rules, layer):
    """A through-hole pad's copper diameter on a layer, as Fusion makes it: the library's diameter,
    grown to the drill plus the restring rule if that is bigger (J1's pads have no diameter: 0.84
    drill + 2 x 0.254 = 1.348 mm, which is what the Gerber flashes)."""
    drill = length(pad.get("drill"))
    side = "Top" if layer == 1 else "Bottom"
    return max(length(pad.get("diameter")), drill + 2 * _restring(rules, drill, "Pad", side))


def _pad_shape(pad, d):
    x, y = float(pad.get("x")), float(pad.get("y"))
    _, rot = orientation(pad.get("rot"))
    shape = pad.get("shape", "round")
    e = float(pad.get("elongation", 100)) / 100
    if shape == "square":
        return g.rect(x, y, d, d, rot)
    if shape == "octagon":
        return g.octagon(x, y, d, rot)
    if shape == "long":
        a, b = g.rotate((-d * e / 2, 0), rot, (x, y)), g.rotate((d * e / 2, 0), rot, (x, y))
        return g.cap(a, b, d / 2)
    if shape == "offset":
        return g.cap((x, y), g.rotate((d * e, 0), rot, (x, y)), d / 2)
    return g.circle((x, y), d)


def _placer(x, y, rot):
    mirror, angle = orientation(rot)

    def fn(p):
        return g.rotate((-p[0] if mirror else p[0], p[1]), angle, (x, y))

    return fn, mirror


def _wire_points(w):
    p1 = (float(w.get("x1")), float(w.get("y1")))
    p2 = (float(w.get("x2")), float(w.get("y2")))
    return g.arc_points(p1, p2, float(w.get("curve", 0)))


def _wire_shapes(w, fn=lambda p: p):
    pts = _wire_points(w)
    r = float(w.get("width", 0)) / 2
    return [g.cap(fn(a), fn(b), r) for a, b in zip(pts, pts[1:])]


def _side(layer, mirror):
    return FLIP.get(layer, layer) if mirror else layer


def _load_signals(root, rules, out):
    pad_signal = {}
    for s in root.iter("signal"):
        name = s.get("name")
        sig = out["signals"].setdefault(name, {"contacts": set()})
        for c in s.iter("contactref"):
            sig["contacts"].add(f"{c.get('element')}.{c.get('pad')}")
            pad_signal[(c.get("element"), c.get("pad"))] = name
        for w in s.findall("wire"):
            layer = int(w.get("layer"))
            if layer in COPPER:
                for sh in _wire_shapes(w):
                    out["copper"].append(
                        {
                            "kind": "track",
                            "signal": name,
                            "layers": (layer,),
                            "shape": sh,
                            "owner": f"track {name}",
                        }
                    )
        for v in s.findall("via"):
            drill = length(v.get("drill"))
            d = max(length(v.get("diameter")), drill + 2 * _restring(rules, drill, "Via", "Outer"))
            c = (float(v.get("x")), float(v.get("y")))
            out["copper"].append(
                {
                    "kind": "via",
                    "signal": name,
                    "layers": COPPER,
                    "shape": g.circle(c, d),
                    "owner": f"via {name}",
                    "drill": drill,
                    "center": c,
                    "diameter": d,
                }
            )
        out["polygons"] += len(s.findall("polygon"))
    return pad_signal


def _load_plain(root, out):
    plain = root.find(".//plain")
    if plain is None:
        return
    for w in plain.findall("wire"):
        layer = int(w.get("layer"))
        pts = _wire_points(w)
        if layer == 20:
            out["outline"] += list(zip(pts, pts[1:]))
        elif layer in SILK["top"] + SILK["bottom"]:
            for sh in _wire_shapes(w):
                out["silk"].append(
                    {
                        "layer": layer,
                        "shape": sh,
                        "width": float(w.get("width", 0)),
                        "owner": "board",
                    }
                )
    for h in plain.findall("hole"):
        out["holes"].append(
            {
                "center": (float(h.get("x")), float(h.get("y"))),
                "drill": length(h.get("drill")),
                "owner": "board hole",
            }
        )
    for t in plain.findall("text"):
        out["texts"].append(
            {
                "layer": int(t.get("layer")),
                "size": length(t.get("size")),
                "text": t.text or "",
                "owner": "board",
            }
        )


def _load_element(e, pkg, rules, pad_signal, out):
    name = e.get("name")
    fn, mirror = _placer(float(e.get("x")), float(e.get("y")), e.get("rot"))
    el = out["elements"][name]
    for p in pkg.findall("pad"):
        el["pads"].append(p.get("name"))
        drill = length(p.get("drill"))
        for layer in COPPER:
            d = pad_diameter(p, rules, layer)
            out["copper"].append(
                {
                    "kind": "pad",
                    "signal": pad_signal.get((name, p.get("name"))),
                    "layers": (layer,),
                    "shape": g.transform(_pad_shape(p, d), fn),
                    "owner": f"{name}.{p.get('name')}",
                    "drill": drill,
                    "center": fn((float(p.get("x")), float(p.get("y")))),
                    "diameter": d,
                }
            )
    for p in pkg.findall("smd"):
        el["pads"].append(p.get("name"))
        _, rot = orientation(p.get("rot"))
        sh = g.rect(
            float(p.get("x")), float(p.get("y")), length(p.get("dx")), length(p.get("dy")), rot
        )
        out["copper"].append(
            {
                "kind": "smd",
                "signal": pad_signal.get((name, p.get("name"))),
                "layers": (_side(int(p.get("layer", 1)), mirror),),
                "shape": g.transform(sh, fn),
                "owner": f"{name}.{p.get('name')}",
            }
        )
    for h in pkg.findall("hole"):
        out["holes"].append(
            {
                "center": fn((float(h.get("x")), float(h.get("y")))),
                "drill": length(h.get("drill")),
                "owner": f"{name} hole",
            }
        )
    silk_layers = SILK["top"] + SILK["bottom"]
    for w in pkg.findall("wire"):
        layer = _side(int(w.get("layer")), mirror)
        if layer in silk_layers:
            for sh in _wire_shapes(w, fn):
                out["silk"].append(
                    {"layer": layer, "shape": sh, "width": float(w.get("width", 0)), "owner": name}
                )
    for c in pkg.findall("circle"):
        layer = _side(int(c.get("layer")), mirror)
        if layer in silk_layers:
            cx, cy, r = float(c.get("x")), float(c.get("y")), float(c.get("radius"))
            wd = float(c.get("width", 0))
            pts = [
                (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                for a in range(0, 361, 15)
            ]
            for a, b in zip(pts, pts[1:]):
                out["silk"].append(
                    {
                        "layer": layer,
                        "shape": g.cap(fn(a), fn(b), wd / 2),
                        "width": wd,
                        "owner": name,
                    }
                )
    # the name and value texts: a smashed part carries its own (movable) copies as attributes
    texts = []
    if e.get("smashed") == "yes":
        for a in e.findall("attribute"):
            if (
                a.get("layer")
                and a.get("display", "value") != "off"
                and a.get("name") in ("NAME", "VALUE")
            ):
                texts.append((int(a.get("layer")), length(a.get("size")), a.get("name").lower()))
    else:
        for t in pkg.findall("text"):
            texts.append((_side(int(t.get("layer")), mirror), length(t.get("size")), t.text or ""))
    for layer, size, text in texts:
        out["texts"].append({"layer": layer, "size": size, "text": text, "owner": name})
    # the part's body, from its outline drawings: for the overlap check
    pts = []
    for w in pkg.findall("wire"):
        if int(w.get("layer")) in BODY:
            pts += [fn(q) for q in _wire_points(w)]
    for c in pkg.findall("circle"):
        if int(c.get("layer")) in BODY:
            cx, cy, r = float(c.get("x")), float(c.get("y")), float(c.get("radius"))
            pts += [fn((cx + dx, cy + dy)) for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r))]
    for r in pkg.findall("rectangle"):
        if int(r.get("layer")) in BODY:
            x1, y1, x2, y2 = (float(r.get(k)) for k in ("x1", "y1", "x2", "y2"))
            pts += [fn(q) for q in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
    if pts:
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        el["body"] = (min(xs), min(ys), max(xs), max(ys))


def library_model(lib_name):
    """A part from our own library (library/<owner>/<part>/, one part per .lbr named as its folder)
    carries its 3D model in part.json, which board3d.py and case.py build from: its path, or ''."""
    if not lib_name:
        return ""
    for pj in sorted((ROOT / "library").glob(f"*/{lib_name}/part.json")):
        model = json.loads(pj.read_text(encoding="utf-8-sig")).get("model") or {}
        if model.get("boxes") or model.get("cylinders"):
            return pj.relative_to(ROOT).as_posix()
    return ""


def load_brd(path):
    root = ET.parse(path).getroot()
    rules = _rules(root)
    libs = _libs(root)
    out = {
        "rules": rules,
        "elements": {},
        "copper": [],
        "holes": [],
        "silk": [],
        "texts": [],
        "outline": [],
        "signals": {},
        "polygons": 0,
    }
    pad_signal = _load_signals(root, rules, out)
    _load_plain(root, out)
    for e in root.iter("element"):
        lib = libs.get((e.get("library"), e.get("library_urn", "")))
        pkg = lib.find(f"packages/package[@name='{e.get('package')}']") if lib is not None else None
        out["elements"][e.get("name")] = {
            "package": e.get("package"),
            "value": e.get("value", ""),
            "x": float(e.get("x")),
            "y": float(e.get("y")),
            "rot": e.get("rot", "R0"),
            "mirror": orientation(e.get("rot"))[0],
            "pads": [],
            "found": pkg is not None,
            "model3d": e.get("package3d_urn", "") or library_model(e.get("library", "")),
            "body": None,
            "attributes": {
                a.get("name"): (a.get("value") or "").strip() for a in e.findall("attribute")
            },
        }
        if pkg is not None:
            _load_element(e, pkg, rules, pad_signal, out)
    return out


def outline_loops(segments, tol=0.01):
    """Chain outline segments into closed loops; returns (loops, the open ends if any)."""
    segs = list(segments)
    loops = []
    while segs:
        a, b = segs.pop(0)
        loop = [a, b]
        while math.dist(loop[0], loop[-1]) > tol:
            for i, (p, q) in enumerate(segs):
                if math.dist(p, loop[-1]) <= tol:
                    loop.append(q)
                    break
                if math.dist(q, loop[-1]) <= tol:
                    loop.append(p)
                    break
            else:
                return loops, [loop[0], loop[-1]]
            segs.pop(i)
        loops.append(loop[:-1])
    return loops, []


def inside_board(p, loops):
    return sum(g.inside(p, lp) for lp in loops) % 2 == 1


# ----------------------------------------------------------------------------- checks
def ref_pads(token, sch):
    """'SW1.P' (a pin) or 'SW1.2' (a pad) -> {'SW1.2'}."""
    ref, _, x = token.partition(".")
    part = sch["parts"].get(ref)
    if part is None:
        return {token}
    pads = {p for ps in part["connects"].values() for p in ps}
    if x in pads:
        return {f"{ref}.{x}"}
    found = [ps for (_gate, pin), ps in part["connects"].items() if pin == x]
    return {f"{ref}.{p}" for p in found[0]} if found else {token}


def check_netlist(sch, checks, rep):
    S = "netlist"
    for ref, p in sorted(sch["parts"].items()):
        if not p["found"]:
            rep.add(
                "ERROR", S, "PART-UNKNOWN", f"{ref}: its device is not in the schematic's libraries"
            )
        if p["uservalue"] and not p["value"].strip():
            rep.add("WARN", S, "PART-NOVALUE", f"{ref} has no value (its BOM line will be empty)")
    pads_of = {}
    for name, pads in sorted(sch["nets"].items()):
        if len(pads) < 2:
            rep.add(
                "ERROR",
                S,
                "NET-SINGLE",
                f"net {name} reaches only {sorted(pads) or 'no pad'}: a wire to nowhere",
            )
        if name.startswith("N$"):
            rep.add(
                "WARN",
                S,
                "NET-UNNAMED",
                f"net {name} has an automatic name; name it for the reader",
            )
        for pad in pads:
            pads_of.setdefault(pad.split(".")[0], {})[pad] = name
    for ref, m in sorted(pads_of.items()):
        nets = set(m.values())
        n_pads = sum(len(ps) for ps in sch["parts"][ref]["connects"].values())
        if len(m) >= 2 and len(nets) == 1 and len(m) == n_pads:
            rep.add(
                "ERROR",
                S,
                "PART-SHORTED",
                f"{ref}: all its pads are on net {nets.pop()}, so it is shorted out",
            )
    ok = set()
    for tok in checks.get("unconnected_ok", []):
        ok |= ref_pads(tok, sch)
    for ref, pin, pads in sch["unconnected"]:
        meant = {f"{ref}.{p}" for p in pads} <= ok
        rep.add(
            "OK" if meant else "WARN",
            S,
            "PIN-UNCONNECTED",
            f"{ref} pin {pin} (pad {', '.join(pads)}) is connected to nothing"
            + (" (meant: checks.json unconnected_ok)" if meant else ""),
        )
    want = checks.get("nets")
    if want:
        n_before = len(rep.items)
        got = {n: set(p) for n, p in sch["nets"].items()}
        for name, toks in sorted(want.items()):
            exp = set().union(*(ref_pads(t, sch) for t in toks))
            if name not in got:
                rep.add(
                    "ERROR",
                    S,
                    "NET-EXPECTED",
                    f"net {name} is in the design intent but not in the schematic",
                )
            elif got[name] != exp:
                rep.add(
                    "ERROR",
                    S,
                    "NET-EXPECTED",
                    f"net {name}: schematic {sorted(got[name])}, intended {sorted(exp)}",
                )
        for name in sorted(set(got) - set(want)):
            rep.add(
                "ERROR",
                S,
                "NET-EXPECTED",
                f"net {name} is in the schematic but not in the design intent",
            )
        if len(rep.items) == n_before:
            rep.add(
                "OK",
                S,
                "NET-EXPECTED",
                f"the schematic's {len(want)} nets are exactly the intended ones",
            )
    if not rep.problems(S):
        rep.add(
            "OK", S, "NETLIST", f"{len(sch['nets'])} nets, {len(sch['parts'])} parts: no problems"
        )


def check_match(sch, brd, rep):
    S = "match"
    sp = {r: p for r, p in sch["parts"].items() if p["package"]}
    for ref in sorted(set(sp) - set(brd["elements"])):
        rep.add("ERROR", S, "PART-MISSING", f"{ref} is in the schematic but not on the board")
    for ref in sorted(set(brd["elements"]) - set(sp)):
        rep.add("ERROR", S, "PART-EXTRA", f"{ref} is on the board but not in the schematic")
    for ref in sorted(set(sp) & set(brd["elements"])):
        b = brd["elements"][ref]
        if sp[ref]["package"] != b["package"]:
            rep.add(
                "ERROR",
                S,
                "PART-PACKAGE",
                f"{ref}: schematic says {sp[ref]['package']}, board has {b['package']}",
            )
        if sp[ref]["value"] and sp[ref]["value"] != b["value"]:
            rep.add(
                "ERROR",
                S,
                "PART-VALUE",
                f"{ref}: schematic value {sp[ref]['value']!r}, board {b['value']!r}",
            )
    sn = {n: p for n, p in sch["nets"].items() if p}
    bn = {n: s["contacts"] for n, s in brd["signals"].items() if s["contacts"]}
    by_pads = {frozenset(p): n for n, p in bn.items()}
    for name, pads in sorted(sn.items()):
        if bn.get(name) == pads:
            continue
        other = by_pads.get(frozenset(pads))
        if other:
            rep.add("WARN", S, "NET-RENAMED", f"net {name} is called {other} on the board")
        else:
            rep.add(
                "ERROR",
                S,
                "NET-DIFFERS",
                f"net {name}: schematic {sorted(pads)}, board {sorted(bn.get(name, []))}",
            )
    sch_sets = {frozenset(p) for p in sn.values()}
    for name in sorted(set(bn) - set(sn)):
        if frozenset(bn[name]) not in sch_sets:
            rep.add(
                "ERROR", S, "NET-DIFFERS", f"signal {name} is on the board but not in the schematic"
            )
    if not rep.problems(S):
        rep.add(
            "OK",
            S,
            "MATCH",
            f"board and schematic agree: {len(sp)} parts, {len(sn)} nets, same pads",
        )


def touching(a, b):
    if not set(a["layers"]) & set(b["layers"]):
        return False
    return g.near(a["shape"], b["shape"], 0.001) and g.gap(a["shape"], b["shape"]) <= 0.001


def check_parts(brd, rep):
    S = "parts"
    els = sorted(brd["elements"].items())
    for i, (a, ea) in enumerate(els):
        for b, eb in els[:i]:
            if ea["mirror"] != eb["mirror"] or not ea["body"] or not eb["body"]:
                continue
            (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = ea["body"], eb["body"]
            w, h = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
            if w > 0.05 and h > 0.05:
                rep.add(
                    "WARN",
                    S,
                    "PART-OVERLAP",
                    f"the bodies of {b} and {a} overlap by {w:.2f} x {h:.2f} mm (outline boxes)",
                )
    for ref, e in els:
        if not e["found"]:
            rep.add(
                "ERROR",
                S,
                "PART-UNKNOWN",
                f"{ref}: package {e['package']} is not in the board's libraries",
            )
        if not e["model3d"]:
            rep.add(
                "WARN",
                S,
                "PART-3D",
                f"{ref} has no 3D model: the board in 3D and the case will miss it",
            )
    no_mpn = [ref for ref, e in els if not e["attributes"].get("MPN")]
    if no_mpn:
        rep.add(
            "INFO",
            S,
            "PART-MPN",
            f"no manufacturer part number (MPN) for {', '.join(no_mpn)}: "
            "the BOM names them by value only",
        )
    flagged = [
        i for i in rep.items if i["section"] == S and i["level"] in ("ERROR", "WARN", "APPROVED")
    ]
    if not flagged:
        rep.add("OK", S, "PARTS", f"{len(els)} parts: bodies apart, each with a 3D model")


def check_routing(brd, rep):
    S = "routing"
    for name, sig in sorted(brd["signals"].items()):
        items = [c for c in brd["copper"] if c["signal"] == name]
        grp = g.Groups()
        for i in range(len(items)):
            grp.find(i)
            for j in range(i):
                # a through-hole pad is listed once per copper layer: the plated hole joins them
                same_pad = items[i]["kind"] == "pad" and items[i]["owner"] == items[j]["owner"]
                if same_pad or touching(items[i], items[j]):
                    grp.join(i, j)
        pad_groups = {}
        for i, c in enumerate(items):
            if c["owner"] in sig["contacts"]:
                pad_groups.setdefault(grp.find(i), set()).add(c["owner"])
        if len(sig["contacts"]) > 1 and len(pad_groups) > 1:
            pieces = " | ".join(", ".join(sorted(p)) for p in pad_groups.values())
            rep.add(
                "ERROR",
                S,
                "UNROUTED",
                f"signal {name} is in {len(pad_groups)} separate pieces: {pieces}",
            )
        stray = {grp.find(i) for i, c in enumerate(items) if c["kind"] in ("track", "via")} - set(
            pad_groups
        )
        if stray:
            rep.add(
                "WARN",
                S,
                "STRAY-COPPER",
                f"signal {name} has {len(stray)} track piece(s) touching none of its pads",
            )
    if brd["polygons"]:
        rep.add(
            "WARN",
            S,
            "POLYGONS",
            f"{brd['polygons']} copper pour(s): this check does not model pours yet",
        )
    if not rep.problems(S):
        rep.add(
            "OK",
            S,
            "ROUTED",
            f"all {len(brd['signals'])} signals are joined by copper, nothing stray",
        )


def _limit(fab, key, value, rep, section, code, what, level="ERROR"):
    """Compare a measured value with the fab profile: under `min` -> `level` (ERROR, or WARN for
    cosmetic things like silkscreen), under `recommended` -> WARN."""
    lim = fab.get(key, {})
    lo, rec = lim.get("min"), lim.get("recommended")
    if lo is not None and value < lo - 1e-9:
        rep.add(level, section, code, f"{what}: {value:.3f} mm, the fab's minimum is {lo} mm")
    elif rec is not None and value < rec - 1e-9:
        rep.add(
            "WARN",
            section,
            code,
            f"{what}: {value:.3f} mm, legal (min {lo}) but under the recommended {rec} mm",
        )


def _check_outline(brd, fab, rep, S):
    loops, open_ends = outline_loops(brd["outline"])
    if not loops or open_ends:
        rep.add(
            "ERROR",
            S,
            "OUTLINE",
            f"the board outline (layer 20) is not closed: open near {open_ends}",
        )
        return None
    xs = [p[0] for lp in loops for p in lp]
    ys = [p[1] for lp in loops for p in lp]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    size = fab.get("board_size", {})
    lo, hi = size.get("min", [0, 0]), size.get("max", [1e9, 1e9])
    if min(w, h) < min(lo) or max(w, h) > max(hi):
        rep.add(
            "ERROR",
            S,
            "BOARD-SIZE",
            f"board {w:.2f} x {h:.2f} mm is outside the fab's {lo} to {hi} mm",
        )
    else:
        rep.add("OK", S, "BOARD-SIZE", f"board {w:.2f} x {h:.2f} mm, {len(loops)} outline loop(s)")
    return loops


def _check_copper(brd, fab, rep, S, loops):
    for c in brd["copper"]:
        if c["kind"] == "track":
            _limit(
                fab, "track_width", 2 * c["shape"][3], rep, S, "TRACK-WIDTH", f"{c['owner']} width"
            )
    cc = fab.get("copper_clearance", {})
    near_mm = 3 * max(cc.get("min", 0.1), cc.get("recommended", 0.15))
    for layer in COPPER:
        items = [c for c in brd["copper"] if layer in c["layers"]]
        for i, a in enumerate(items):
            for b in items[:i]:
                if a["owner"] == b["owner"] or (a["signal"] and a["signal"] == b["signal"]):
                    continue
                if not g.near(a["shape"], b["shape"], near_mm):
                    continue
                d = g.gap(a["shape"], b["shape"])
                where = f"{a['owner']} and {b['owner']} (layer {layer})"
                if d <= 0:
                    rep.add("ERROR", S, "SHORT", f"{where} touch: a short circuit")
                else:
                    key = (
                        "smd_pad_to_pad" if a["kind"] == b["kind"] == "smd" else "copper_clearance"
                    )
                    _limit(fab, key, d, rep, S, "CLEARANCE", f"{where} gap")
    if loops:
        segs = [(lp[i], lp[(i + 1) % len(lp)]) for lp in loops for i in range(len(lp))]
        for c in brd["copper"]:
            sh = c["shape"]
            if not inside_board(sh[1] if sh[0] == "cap" else sh[1][0], loops):
                rep.add("ERROR", S, "OUTSIDE", f"{c['owner']} is outside the board outline")
            else:
                _limit(
                    fab,
                    "copper_to_edge",
                    g.gap_to_lines(sh, segs),
                    rep,
                    S,
                    "EDGE",
                    f"{c['owner']} to board edge",
                )
        for h in brd["holes"]:
            if not inside_board(h["center"], loops):
                rep.add(
                    "ERROR",
                    S,
                    "OUTSIDE",
                    f"{h['owner']} at {h['center']} is outside the board outline",
                )


def _check_holes(brd, fab, rep, S):
    plated = {}
    for c in brd["copper"]:
        if c.get("drill"):
            plated.setdefault((c["owner"], c["center"]), c)
    dmin, dmax = fab.get("drill", {}).get("min", 0), fab.get("drill", {}).get("max", 99)
    for c in plated.values():
        if not dmin <= c["drill"] <= dmax:
            rep.add(
                "ERROR",
                S,
                "DRILL",
                f"{c['owner']} drill {c['drill']:.3f} mm is outside the fab's {dmin}-{dmax} mm",
            )
        _limit(
            fab,
            "annular_ring",
            (c["diameter"] - c["drill"]) / 2,
            rep,
            S,
            "RING",
            f"{c['owner']} annular ring",
        )
    for h in brd["holes"]:
        if h["drill"] < fab.get("npth_drill", {}).get("min", 0) or h["drill"] > dmax:
            rep.add(
                "ERROR",
                S,
                "DRILL",
                f"{h['owner']} {h['drill']} mm is outside the fab's non-plated hole range",
            )
    holes = [(c["owner"], c["center"], c["drill"]) for c in plated.values()]
    holes += [(h["owner"], h["center"], h["drill"]) for h in brd["holes"]]
    for i, (oa, ca, da) in enumerate(holes):
        for ob, cb, db in holes[:i]:
            _limit(
                fab,
                "pad_hole_to_hole",
                math.dist(ca, cb) - da / 2 - db / 2,
                rep,
                S,
                "HOLE-SPACING",
                f"holes of {oa} and {ob}",
            )
    for h in brd["holes"]:
        hs = g.circle(h["center"], h["drill"])
        for c in brd["copper"]:
            if g.near(hs, c["shape"], 1.0):
                _limit(
                    fab,
                    "npth_to_copper",
                    g.gap(hs, c["shape"]),
                    rep,
                    S,
                    "HOLE-COPPER",
                    f"{h['owner']} to {c['owner']}",
                )
    for c in plated.values():
        hs = g.circle(c["center"], c["drill"])
        for t in brd["copper"]:
            if t["kind"] == "track" and t["signal"] != c["signal"] and g.near(hs, t["shape"], 1.0):
                _limit(
                    fab,
                    "pth_hole_to_track",
                    g.gap(hs, t["shape"]),
                    rep,
                    S,
                    "HOLE-TRACK",
                    f"hole of {c['owner']} to {t['owner']}",
                )


def _check_silk(brd, fab, rep, S):
    wmin = fab.get("silk_line_width", {}).get("min", 0)
    thin = sorted({s["owner"] for s in brd["silk"] if s["width"] < wmin})
    if thin:
        rep.add(
            "WARN",
            S,
            "SILK-WIDTH",
            f"silkscreen lines under {wmin} mm in {', '.join(thin)} "
            "(they may print faint or not at all)",
        )
    tmin = fab.get("silk_text_height", {}).get("min", 0)
    for t in brd["texts"]:
        if t["layer"] in SILK["top"] + SILK["bottom"] and t["size"] < tmin:
            rep.add(
                "WARN",
                S,
                "SILK-TEXT",
                f"{t['owner']} {t['text'] or 'text'} is {t['size']:.2f} mm high; "
                f"the fab prints {tmin} mm and up legibly",
            )
    smin = fab.get("silk_to_pad", {}).get("min", 0)
    seen = set()
    for s in brd["silk"]:
        side = 1 if s["layer"] in SILK["top"] else 16
        for c in brd["copper"]:
            if c["kind"] == "track" or side not in c["layers"] or (s["owner"], c["owner"]) in seen:
                continue
            if g.near(s["shape"], c["shape"], smin) and g.gap(s["shape"], c["shape"]) < smin:
                seen.add((s["owner"], c["owner"]))
                rep.add(
                    "WARN",
                    S,
                    "SILK-PAD",
                    f"{s['owner']} silkscreen comes within {smin} mm of pad {c['owner']} "
                    "(the fab clips it)",
                )


def check_rules(brd, fab, rep):
    S = "rules"
    loops = _check_outline(brd, fab, rep, S)
    _check_copper(brd, fab, rep, S, loops)
    _check_holes(brd, fab, rep, S)
    _check_silk(brd, fab, rep, S)
    if not rep.problems(S):
        rep.add(
            "OK", S, "RULES", f"every rule of the fab profile passes ({fab.get('name', 'fab')})"
        )


RULESET = [  # Fusion's rule name, the fab profile key, what it is
    ("mdWireWire", "copper_clearance", "track to track"),
    ("mdWirePad", "copper_clearance", "track to pad"),
    ("mdPadPad", "copper_clearance", "pad to pad"),
    ("mdWireVia", "copper_clearance", "track to via"),
    ("mdPadVia", "copper_clearance", "pad to via"),
    ("mdViaVia", "copper_clearance", "via to via"),
    ("mdSmdSmd", "smd_pad_to_pad", "SMD to SMD"),
    ("mdCopperDimension", "copper_to_edge", "copper to edge"),
    ("msWidth", "track_width", "minimum track width"),
    ("msDrill", "drill", "minimum drill"),
    ("rlMinPadTop", "annular_ring", "minimum pad ring (top)"),
    ("rlMinPadBottom", "annular_ring", "minimum pad ring (bottom)"),
]


def check_ruleset(brd, fab, rep):
    S = "ruleset"
    compared = loose = 0
    for name, key, what in RULESET:
        if name not in brd["rules"] or fab.get(key, {}).get("min") is None:
            continue
        compared += 1
        v, lo = length(brd["rules"][name]), fab[key]["min"]
        if v < lo - 1e-9:
            loose += 1
            rep.add(
                "WARN",
                S,
                "RULESET",
                f"Fusion's {what} rule ({name} = {v:.3f} mm) is looser than the fab's {lo} mm",
            )
    rep.add(
        "OK" if not loose else "INFO",
        S,
        "RULESET",
        f"Fusion's rule set compared with the fab: {compared} rules, {loose} looser",
    )


# ----------------------------------------------------------------------------- main
def run(brd_path, sch_path=None, fab_path=DEFAULT_FAB, checks=None):
    checks = checks or {}
    fab = json.loads(Path(fab_path).read_text(encoding="utf-8"))
    rep = Report(checks.get("approved", []))
    brd = load_brd(brd_path)
    if sch_path and Path(sch_path).exists():
        sch = load_sch(sch_path)
        check_netlist(sch, checks, rep)
        check_match(sch, brd, rep)
    else:
        rep.add(
            "WARN", "netlist", "NO-SCHEMATIC", "no .sch given: netlist and match checks skipped"
        )
    check_parts(brd, rep)
    check_routing(brd, rep)
    check_rules(brd, fab, rep)
    check_ruleset(brd, fab, rep)
    return rep


def print_report(rep, title):
    print(title)
    section = None
    for i in rep.items:
        if i["section"] != section:
            section = i["section"]
            print(f"\n[{section}]")
        print(f"  {i['level']:8} {i['code']:16} {i['message']}")
    print(
        f"\n{rep.count('ERROR')} errors, {rep.count('WARN')} warnings, "
        f"{rep.count('APPROVED')} approved"
    )


def find_checks(brd):
    for p in (brd.parent / "checks.json", brd.parent.parent / "checks.json"):
        if p.exists():
            return p
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a Fusion board export (EAGLE .brd + .sch).")
    ap.add_argument("brd")
    ap.add_argument("--sch")
    ap.add_argument("--fab", default=str(DEFAULT_FAB))
    ap.add_argument("--checks", help="checks.json (default: next to the .brd, or one folder up)")
    ap.add_argument("--json", help="also write the report as JSON")
    a = ap.parse_args(argv)
    brd = Path(a.brd)
    sch = Path(a.sch) if a.sch else brd.with_suffix(".sch")
    cpath = Path(a.checks) if a.checks else find_checks(brd)
    checks = json.loads(cpath.read_text(encoding="utf-8")) if cpath else {}
    rep = run(brd, sch, a.fab, checks)
    print_report(rep, f"pcb_check: {brd} (fab: {Path(a.fab).name}; checks: {cpath or 'none'})")
    if a.json:
        Path(a.json).write_text(json.dumps(rep.items, indent=2), encoding="utf-8")
    return 1 if rep.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
