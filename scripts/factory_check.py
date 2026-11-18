r"""Simulate the factory: read the Gerber and drill files the way a fab does, and check them.

    python scripts\factory_check.py examples\10_led_switch_board\factory
        [--brd ...\fusion\board.brd] [--sch ...\fusion\board.sch]
        [--fab production\fab\jlcpcb_2layer.json]
        [--out DIR]   for the BOM, pick-and-place, previews and upload zip (default: the folder)

The board file and schematic are only the reference to compare with: everything about the board
itself is taken from the factory files, as the fab would see it. Standard library only.

  files      every layer is there and parses (RS-274X Gerber, Excellon drill), units known
  outline    the profile's size equals the board's
  drills     every hole in the drill file is a hole of the board, and the other way round; plated
             holes land on copper on both sides; mounting holes in the plated file are flagged
  copper     everything inside the outline; the smallest copper gap between different pieces of
             copper and the narrowest track, measured on the Gerbers, against the fab's limits
  etest      the factory's electrical test, simulated: copper pieces joined through plated holes
             give the netlist of the bare board; it must equal the schematic's (no opens, no shorts)
  mask       every pad has a solder-mask opening at least as large as the pad
  silk       silkscreen line width; silkscreen over mask openings (the fab removes it there)
  assembly   BOM.csv and CPL.csv in JLCPCB's columns, previews (preview_top.svg / _bottom.svg) and
             <name>_gerbers.zip ready to upload
Exit 1 on any ERROR.
"""

import argparse
import csv
import json
import math
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pcb_check as pc  # noqa: E402
import pcb_geom as g  # noqa: E402

LAYER_FILES = {  # role: (file name stem written by production/cam/two_layer.cam, required?)
    "copper_top": ("copper_top", True),
    "copper_bottom": ("copper_bottom", True),
    "profile": ("profile", True),
    "mask_top": ("soldermask_top", True),
    "mask_bottom": ("soldermask_bottom", True),
    "silk_top": ("silkscreen_top", False),
    "silk_bottom": ("silkscreen_bottom", False),
    "paste_top": ("solderpaste_top", False),
    "paste_bottom": ("solderpaste_bottom", False),
}


# ----------------------------------------------------------------------------- Gerber
class Gerber:
    """The subset of RS-274X that Fusion/EAGLE writes: FS, MO, AD (C, R, O, P, OC8 macro), AM,
    LP, G01/G02/G03/G75, D01/D02/D03, regions G36/G37. Shapes come out in mm."""

    def __init__(self, text, name=""):
        self.name = name
        self.shapes = []  # {"shape", "kind": flash|draw|region, "aperture": size mm}
        self.apertures, self.macros = {}, set()
        self.unit, self.fmt, self.zeros = 1.0, (3, 4), "L"
        self.dark = True
        self.notes = []
        self.ended = False
        self._parse(text)

    def _num(self, s):
        neg = s.startswith("-")
        s = s.lstrip("+-")
        i, d = self.fmt
        if "." in s:
            v = float(s)
        elif self.zeros == "T":
            v = int(s.ljust(i + d, "0")) / 10**d
        else:
            v = int(s) / 10**d
        return (-v if neg else v) * self.unit

    def _aperture(self, code, spec):
        kind, _, params = spec.partition(",")
        ps = [float(p) * self.unit for p in params.split("X") if p] if params else []
        if kind == "C":
            self.apertures[code] = ("C", ps[0])
        elif kind in ("R", "O"):
            self.apertures[code] = (kind, ps[0], ps[1])
        elif kind == "P":
            self.apertures[code] = (
                "P",
                ps[0],
                int(ps[1] / self.unit),
                ps[2] / self.unit if len(ps) > 2 else 0,
            )
        elif kind == "OC8":
            self.apertures[code] = ("OC8", ps[0])
        else:
            self.apertures[code] = ("C", ps[0] if ps else 0)
            self.notes.append(f"aperture macro {kind} read as a circle")

    def _flash(self, ap, x, y):
        k = ap[0]
        if k == "C":
            return g.circle((x, y), ap[1]), ap[1]
        if k == "R":
            return g.rect(x, y, ap[1], ap[2]), min(ap[1], ap[2])
        if k == "O":
            w, h = ap[1], ap[2]
            if w >= h:
                return g.cap((x - (w - h) / 2, y), (x + (w - h) / 2, y), h / 2), h
            return g.cap((x, y - (h - w) / 2), (x, y + (h - w) / 2), w / 2), w
        if k == "OC8":
            return g.octagon(x, y, ap[1]), ap[1]
        if k == "P":
            d, n, rot = ap[1], ap[2], ap[3]
            return g.poly([g.rotate((d / 2, 0), rot + 360 * i / n, (x, y)) for i in range(n)]), d
        return g.circle((x, y), 0), 0

    def _parse(self, text):
        x = y = 0.0
        ap = None
        interp, dcode = "G01", None
        region, contour = False, []
        pos = 0
        while pos < len(text):
            if text[pos].isspace():
                pos += 1
                continue
            if text[pos] == "%":
                end = text.index("%", pos + 1)
                for cmd in text[pos + 1 : end].split("*"):
                    self._extended(cmd.strip())
                pos = end + 1
                continue
            end = text.find("*", pos)
            if end < 0:
                break
            word = text[pos:end].strip()
            pos = end + 1
            if not word or word.startswith("G04"):
                continue
            for gm in re.findall(r"G0?(\d+)", word):
                gn = int(gm)
                if gn in (1, 2, 3):
                    interp = f"G0{gn}"
                elif gn == 36:
                    region, contour = True, []
                elif gn == 37:
                    if len(contour) > 2:
                        self.shapes.append(
                            {
                                "shape": g.poly(contour),
                                "kind": "region",
                                "aperture": 0,
                                "dark": self.dark,
                            }
                        )
                    region, contour = False, []
            if word.startswith("M02"):
                self.ended = True
                break
            m = re.search(r"D(\d+)$", word)
            if m and int(m.group(1)) >= 10:
                ap = self.apertures.get(int(m.group(1)))
                continue
            if m:
                dcode = int(m.group(1))
            coords = dict(re.findall(r"([XYIJ])([+-]?[\d.]+)", word))
            if not coords and not m:
                continue
            nx = self._num(coords["X"]) if "X" in coords else x
            ny = self._num(coords["Y"]) if "Y" in coords else y
            if dcode == 3 and ap:
                sh, size = self._flash(ap, nx, ny)
                self.shapes.append(
                    {"shape": sh, "kind": "flash", "aperture": size, "dark": self.dark}
                )
            elif dcode == 1:
                pts = [(x, y), (nx, ny)]
                if interp in ("G02", "G03"):
                    cx = x + (self._num(coords["I"]) if "I" in coords else 0)
                    cy = y + (self._num(coords["J"]) if "J" in coords else 0)
                    pts = _arc((x, y), (nx, ny), (cx, cy), interp == "G03")
                if region:
                    contour += pts if not contour else pts[1:]
                elif ap:
                    r = ap[1] / 2 if ap[0] == "C" else min(ap[1:3]) / 2
                    for a, b in zip(pts, pts[1:]):
                        self.shapes.append(
                            {
                                "shape": g.cap(a, b, r),
                                "kind": "draw",
                                "aperture": 2 * r,
                                "dark": self.dark,
                            }
                        )
            elif dcode == 2 and region:
                if len(contour) > 2:
                    self.shapes.append(
                        {
                            "shape": g.poly(contour),
                            "kind": "region",
                            "aperture": 0,
                            "dark": self.dark,
                        }
                    )
                contour = [(nx, ny)]
            if region and dcode == 2 and not contour:
                contour = [(nx, ny)]
            x, y = nx, ny

    def _extended(self, cmd):
        if not cmd:
            return
        if cmd.startswith("FS"):
            m = re.match(r"FS([LT])A?X(\d)(\d)Y(\d)(\d)", cmd)
            if m:
                self.zeros, self.fmt = m.group(1), (int(m.group(2)), int(m.group(3)))
        elif cmd.startswith("MO"):
            self.unit = 25.4 if cmd[2:4] == "IN" else 1.0
        elif cmd.startswith("ADD"):
            m = re.match(r"ADD(\d+)([A-Za-z_0-9]+?)(,.*)?$", cmd)
            if m:
                self._aperture(int(m.group(1)), m.group(2) + (m.group(3) or ""))
        elif cmd.startswith("AM"):
            self.macros.add(cmd[2:])
        elif cmd.startswith("LP"):
            self.dark = cmd[2] == "D"
            if not self.dark and self.name.startswith("copper"):
                self.notes.append("clear polarity (LPC) used: copper cut-outs are not modelled")


def _arc(p, q, c, ccw, step=10.0):
    a0 = math.atan2(p[1] - c[1], p[0] - c[0])
    a1 = math.atan2(q[1] - c[1], q[0] - c[0])
    r = math.dist(p, c)
    sweep = a1 - a0
    if ccw and sweep <= 0:
        sweep += 2 * math.pi
    if not ccw and sweep >= 0:
        sweep -= 2 * math.pi
    n = max(2, math.ceil(abs(math.degrees(sweep)) / step))
    return [
        (c[0] + r * math.cos(a0 + sweep * i / n), c[1] + r * math.sin(a0 + sweep * i / n))
        for i in range(n + 1)
    ]


def read_drill(text):
    """Excellon: -> (hits [(x, y, diameter)], notes)."""
    tools, hits, notes = {}, [], []
    unit, dec, zeros = 1.0, 3, "TZ"
    tool = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("METRIC", "INCH")):
            unit = 1.0 if line.startswith("METRIC") else 25.4
            if "LZ" in line:
                zeros = "LZ"
            m = re.search(r"(0+)\.(0+)", line)
            if m:
                dec = len(m.group(2))
                intd = len(m.group(1))
            else:
                intd = 3
            continue
        m = re.match(r"T(\d+)C([\d.]+)", line)
        if m:
            tools[int(m.group(1))] = float(m.group(2)) * unit
            continue
        m = re.match(r"T(\d+)$", line)
        if m:
            tool = int(m.group(1))
            continue
        if line.startswith("G85"):
            notes.append("slots (G85) are not checked")
        m = re.match(r"X([+-]?[\d.]+)Y([+-]?[\d.]+)", line)
        if m and tool in tools:

            def val(s):
                if "." in s:
                    return float(s) * unit
                neg = s.startswith("-")
                s = s.lstrip("+-")
                v = int(s.ljust(intd + dec, "0")) / 10**dec if zeros == "LZ" else int(s) / 10**dec
                return (-v if neg else v) * unit

            hits.append((val(m.group(1)), val(m.group(2)), tools[tool]))
    return hits, notes


# ----------------------------------------------------------------------------- the checks
def find_files(folder):
    files = {}
    for role, (stem, _) in LAYER_FILES.items():
        found = sorted(Path(folder).rglob(f"{stem}.gbr"))
        if found:
            files[role] = found[0]
    drills = sorted(Path(folder).rglob("*.xln")) + sorted(Path(folder).rglob("*.drl"))
    return files, drills


def _copper_groups(layers, plated_hits):
    """Join copper into pieces: shapes touching on a layer; the two sides through plated holes."""
    grp = g.Groups()
    items = [(side, i, s) for side in ("top", "bottom") for i, s in enumerate(layers[side])]
    for side in ("top", "bottom"):
        sh = layers[side]
        for i in range(len(sh)):
            grp.find((side, i))
            for j in range(i):
                if (
                    g.near(sh[i]["shape"], sh[j]["shape"], 0.001)
                    and g.gap(sh[i]["shape"], sh[j]["shape"]) <= 0.001
                ):
                    grp.join((side, i), (side, j))
    for x, y, d in plated_hits:
        on = [(side, i) for side, i, s in items if g.gap(g.circle((x, y), 0.001), s["shape"]) <= 0]
        for a, b in zip(on, on[1:]):
            grp.join(a, b)
    return grp, items


def run(folder, brd_path, sch_path, fab_path, out=None, checks=None):
    fab = json.loads(Path(fab_path).read_text(encoding="utf-8"))
    rep = pc.Report((checks or {}).get("approved", []))
    folder = Path(folder)
    out = Path(out) if out else folder
    files, drill_files = find_files(folder)
    # ---- files
    S = "files"
    gb = {}
    for role, (stem, required) in LAYER_FILES.items():
        if role not in files:
            rep.add("ERROR" if required else "WARN", S, "MISSING", f"no {stem}.gbr in {folder}")
            continue
        gb[role] = Gerber(files[role].read_text(encoding="utf-8", errors="replace"), role)
        if not gb[role].ended:
            rep.add(
                "ERROR", S, "TRUNCATED", f"{files[role].name} does not end with M02: cut short?"
            )
        for n in sorted(set(gb[role].notes)):
            rep.add("WARN", S, "GERBER", f"{files[role].name}: {n}")
    hits = []
    if not drill_files:
        rep.add("ERROR", S, "MISSING", f"no drill file (*.xln / *.drl) in {folder}")
    for f in drill_files:
        h, notes = read_drill(f.read_text(encoding="utf-8", errors="replace"))
        hits += h
        for n in notes:
            rep.add("WARN", S, "DRILL-FILE", f"{f.name}: {n}")
    if not rep.problems(S):
        rep.add(
            "OK",
            S,
            "FILES",
            f"{len(gb)} Gerber layers and {len(drill_files)} drill file(s), {len(hits)} holes",
        )
    brd = pc.load_brd(brd_path)
    sch = pc.load_sch(sch_path) if sch_path and Path(sch_path).exists() else None
    # ---- outline
    S = "outline"
    if "profile" in gb and gb["profile"].shapes:
        boxes = [g.bbox(s["shape"]) for s in gb["profile"].shapes]
        # the profile is drawn with a line; its centre line is the board edge
        lw = max(s["aperture"] for s in gb["profile"].shapes) / 2
        px0, py0 = min(b[0] for b in boxes) + lw, min(b[1] for b in boxes) + lw
        px1, py1 = max(b[2] for b in boxes) - lw, max(b[3] for b in boxes) - lw
        loops, _ = pc.outline_loops(brd["outline"])
        bx = [p[0] for lp in loops for p in lp]
        by = [p[1] for lp in loops for p in lp]
        same = (
            bx
            and max(abs(px0 - min(bx)), abs(py0 - min(by)), abs(px1 - max(bx)), abs(py1 - max(by)))
            < 0.05
        )
        rep.add(
            "OK" if same else "ERROR",
            S,
            "PROFILE",
            f"profile {px1 - px0:.2f} x {py1 - py0:.2f} mm at ({px0:.2f}, {py0:.2f})"
            + (
                "; same as the board"
                if same
                else f"; the board is {max(bx) - min(bx):.2f} x {max(by) - min(by):.2f} mm"
            ),
        )
        board_box = (px0, py0, px1, py1)
    else:
        rep.add(
            "ERROR", S, "PROFILE", "the profile layer is empty: the fab will not know where to cut"
        )
        board_box = None
    # ---- drills
    S = "drills"
    want = []
    for c in brd["copper"]:
        if c.get("drill") and c["layers"] == (1,) or c["kind"] == "via":
            want.append((c["center"][0], c["center"][1], c["drill"], c["owner"], True))
    want += [(h["center"][0], h["center"][1], h["drill"], h["owner"], False) for h in brd["holes"]]
    left = list(hits)
    for x, y, d, owner, plated in want:
        m = next(
            (h for h in left if math.dist((x, y), h[:2]) < 0.02 and abs(h[2] - d) < 0.02), None
        )
        if m is None:
            rep.add(
                "ERROR",
                S,
                "DRILL-MISSING",
                f"{owner}: no {d:.3f} mm hole at ({x:.3f}, {y:.3f}) in the drill file",
            )
            continue
        left.remove(m)
        if not plated:
            rep.add(
                "WARN",
                S,
                "NPTH-PLATED",
                f"{owner} ({d} mm) is in the plated drill file: the fab will plate it; "
                "fine for a screw "
                "hole, otherwise ask for it non-plated",
            )
    for x, y, d in left:
        rep.add(
            "ERROR",
            S,
            "DRILL-EXTRA",
            f"a {d:.3f} mm hole at ({x:.3f}, {y:.3f}) that the board does not have",
        )
    plated_hits = [(x, y, d) for x, y, d, _o, p in want if p]
    layers = {
        "top": [s for s in gb.get("copper_top", Gerber("")).shapes if s["dark"]],
        "bottom": [s for s in gb.get("copper_bottom", Gerber("")).shapes if s["dark"]],
    }
    for x, y, d in plated_hits:
        for side in ("top", "bottom"):
            if not any(g.gap(g.circle((x, y), d), s["shape"]) <= -d / 2 for s in layers[side]):
                rep.add(
                    "ERROR",
                    S,
                    "HOLE-OFF-COPPER",
                    f"plated hole at ({x:.2f}, {y:.2f}) has no pad around it on the {side}",
                )
    if not rep.problems(S) or all(
        i["code"] == "NPTH-PLATED" for i in rep.items if i["section"] == S and i["level"] != "OK"
    ):
        rep.add(
            "OK", S, "DRILLS", f"{len(hits)} holes in the drill file, each one a hole of the board"
        )
    # ---- copper
    S = "copper"
    if board_box:
        for side in ("top", "bottom"):
            for s in layers[side]:
                b = g.bbox(s["shape"])
                if (
                    b[0] < board_box[0]
                    or b[1] < board_box[1]
                    or b[2] > board_box[2]
                    or b[3] > board_box[3]
                ):
                    rep.add(
                        "ERROR",
                        S,
                        "OUTSIDE",
                        f"{side} copper at {tuple(round(v, 2) for v in b)} is outside the profile",
                    )
    grp, items = _copper_groups(layers, plated_hits)
    for side in ("top", "bottom"):
        draws = [s["aperture"] for s in layers[side] if s["kind"] == "draw"]
        if draws:
            pc._limit(
                fab,
                "track_width",
                min(draws),
                rep,
                S,
                "TRACK-WIDTH",
                f"narrowest {side} track on the Gerber",
            )
        best = None
        sh = layers[side]
        for i in range(len(sh)):
            for j in range(i):
                if grp.find((side, i)) == grp.find((side, j)) or not g.near(
                    sh[i]["shape"], sh[j]["shape"], 1.0
                ):
                    continue
                d = g.gap(sh[i]["shape"], sh[j]["shape"])
                if best is None or d < best[0]:
                    best = (d, g.bbox(sh[i]["shape"]))
        if best:
            where = (
                f"near ({(best[1][0] + best[1][2]) / 2:.2f}, {(best[1][1] + best[1][3]) / 2:.2f})"
            )
            if best[0] <= 0:
                rep.add("ERROR", S, "SHORT", f"{side}: two pieces of copper touch {where}")
            else:
                pc._limit(
                    fab,
                    "copper_clearance",
                    best[0],
                    rep,
                    S,
                    "CLEARANCE",
                    f"smallest {side} copper gap {where}",
                )
                rep.add(
                    "INFO", S, "CLEARANCE", f"smallest {side} copper gap: {best[0]:.3f} mm {where}"
                )
    if not rep.problems(S):
        rep.add(
            "OK", S, "COPPER", "copper inside the profile, widths and gaps within the fab's limits"
        )
    # ---- e-test: the bare board's netlist from copper alone
    S = "etest"
    pad_group = {}
    for c in brd["copper"]:
        if c["kind"] in ("pad", "smd"):
            side = "top" if c["layers"] == (1,) else "bottom"
            pt = c["center"] if c.get("center") else g.bbox(c["shape"])[:2]
            if c["kind"] == "smd":
                b = g.bbox(c["shape"])
                pt = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            hit = next(
                (
                    i
                    for sd, i, s in items
                    if sd == side and g.gap(g.circle(pt, 0.001), s["shape"]) <= 0
                ),
                None,
            )
            if hit is None:
                if c["kind"] == "smd" or side == "top":
                    rep.add(
                        "ERROR",
                        S,
                        "PAD-MISSING",
                        f"pad {c['owner']} has no copper on the {side} Gerber",
                    )
                continue
            pad_group.setdefault(c["owner"], grp.find((side, hit)))
    pieces = {}
    for owner, gid in pad_group.items():
        pieces.setdefault(gid, set()).add(owner)
    if sch:
        nets = {n: p for n, p in sch["nets"].items() if p}
        net_of = {pad: n for n, ps in nets.items() for pad in ps}
        for n, ps in sorted(nets.items()):
            gs = {pad_group.get(p) for p in ps}
            if len(gs) > 1:
                rep.add(
                    "ERROR",
                    S,
                    "OPEN",
                    f"net {n} is split on the bare board: {sorted(ps)} are not all joined",
                )
        for gid, ps in pieces.items():
            ns = {net_of.get(p, f"(unconnected {p})") for p in ps}
            if len(ns) > 1:
                rep.add(
                    "ERROR", S, "SHORT", f"copper joins {sorted(ps)}, which belong to {sorted(ns)}"
                )
        if not rep.problems(S):
            rep.add(
                "OK",
                S,
                "ETEST",
                f"bare-board netlist = schematic: {len(nets)} nets, no opens, no shorts "
                f"({len(pad_group)} pads probed)",
            )
    else:
        rep.add("WARN", S, "ETEST", "no schematic to compare with: netlist from copper only")
    # ---- mask
    S = "mask"
    for side, role in (("top", "mask_top"), ("bottom", "mask_bottom")):
        openings = [s for s in gb.get(role, Gerber("")).shapes if s["dark"]]
        for s in layers[side]:
            if s["kind"] != "flash":
                continue
            b = g.bbox(s["shape"])
            c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            op = next((o for o in openings if g.gap(g.circle(c, 0.001), o["shape"]) <= 0), None)
            if op is None:
                rep.add(
                    "WARN",
                    S,
                    "MASK-COVERED",
                    f"{side} pad at ({c[0]:.2f}, {c[1]:.2f}) has no solder-mask opening",
                )
            elif op["aperture"] + 1e-6 < s["aperture"]:
                rep.add(
                    "WARN",
                    S,
                    "MASK-SMALL",
                    f"{side} pad at ({c[0]:.2f}, {c[1]:.2f}): mask opening smaller than the pad",
                )
    if not rep.problems(S):
        rep.add("OK", S, "MASK", "every pad has a solder-mask opening at least as large as the pad")
    # ---- silk
    S = "silk"
    for side in ("top", "bottom"):
        shapes = gb.get(f"silk_{side}", Gerber("")).shapes
        # Fusion fills shapes it cannot draw with one line (a flat-ended thick arc, like the LED's
        # outline) by hatching them with hundreds of 0.0254 mm strokes: those print as the filled
        # shape, so a hairline aperture used for many strokes is a fill, not a thin line
        uses = {}
        for s in shapes:
            if s["kind"] == "draw":
                uses[s["aperture"]] = uses.get(s["aperture"], 0) + 1
        fills = {a for a, n in uses.items() if a < 0.05 and n > 20}
        silk = [
            s for s in shapes if s["dark"] and s["kind"] == "draw" and s["aperture"] not in fills
        ]
        if not silk:
            continue
        thin = min(s["aperture"] for s in silk)
        pc._limit(
            fab,
            "silk_line_width",
            thin,
            rep,
            S,
            "SILK-WIDTH",
            f"thinnest {side} silkscreen line",
            "WARN",
        )
        openings = [o for o in gb.get(f"mask_{side}", Gerber("")).shapes if o["dark"]]
        hit = {}
        for s in silk:
            for o in openings:
                if g.near(s["shape"], o["shape"], 0) and g.gap(s["shape"], o["shape"]) < 0:
                    b = g.bbox(o["shape"])
                    hit.setdefault((round((b[0] + b[2]) / 2, 2), round((b[1] + b[3]) / 2, 2)), 0)
                    hit[(round((b[0] + b[2]) / 2, 2), round((b[1] + b[3]) / 2, 2))] += 1
        for (x, y), n in sorted(hit.items()):
            rep.add(
                "WARN",
                S,
                "SILK-ON-PAD",
                f"{side}: {n} silkscreen stroke(s) run into the mask opening of the pad at "
                f"({x}, {y}); the fab removes silk there",
            )
    if not rep.problems(S):
        rep.add("OK", S, "SILK", "silkscreen lines wide enough and clear of the pads")
    # ---- assembly outputs
    S = "assembly"
    out.mkdir(parents=True, exist_ok=True)
    bom, missing = write_bom(brd, out / "BOM.csv")
    write_cpl(brd, out / "CPL.csv")
    rep.add(
        "OK",
        S,
        "BOM",
        f"BOM.csv: {len(bom)} lines, CPL.csv: {len(brd['elements'])} parts (JLCPCB columns)",
    )
    if missing:
        rep.add(
            "WARN",
            S,
            "LCSC",
            f"no LCSC part number for {', '.join(missing)}: JLCPCB cannot assemble these; "
            "solder them yourself or add an LCSC attribute",
        )
    write_svg(gb, hits, board_box, "top", out / "preview_top.svg")
    write_svg(gb, hits, board_box, "bottom", out / "preview_bottom.svg")
    z = out / f"{Path(brd_path).stem}_gerbers.zip"
    # a fixed date and order: the same files give the same zip, so it can live in git and be
    # downloaded from the board's summary page
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(list(files.values()) + drill_files, key=lambda p: p.name):
            info = zipfile.ZipInfo(f.name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, f.read_bytes())
    rep.add("OK", S, "ZIP", f"{z.name}: {len(files) + len(drill_files)} files to upload")
    return rep


LCSC_KEYS = ("LCSC", "LCSC_PART", "LCSC#", "JLCPCB", "JLC")


def write_bom(brd, path):
    rows, missing = {}, []
    for ref, e in sorted(brd["elements"].items()):
        lcsc = next((e["attributes"][k] for k in LCSC_KEYS if e["attributes"].get(k)), "")
        if not lcsc:
            missing.append(ref)
        key = (e["value"] or e["package"], e["package"], lcsc)
        rows.setdefault(key, []).append(ref)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, pkg, lcsc), refs in rows.items():
            w.writerow([value, ",".join(refs), pkg, lcsc])
    return rows, missing


def write_cpl(brd, path):
    """Mid X/Y is each part's origin in the library, which is its centre for most parts: check the
    placement in JLCPCB's preview before ordering assembly."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, e in sorted(brd["elements"].items()):
            _, angle = pc.orientation(e["rot"])
            w.writerow(
                [
                    ref,
                    f"{e['x']:.4f}mm",
                    f"{e['y']:.4f}mm",
                    "Bottom" if e["mirror"] else "Top",
                    f"{angle:g}",
                ]
            )


def _svg_shape(s, color, opacity=1.0):
    sh = s["shape"]
    if sh[0] == "cap":
        (ax, ay), (bx, by), r = sh[1], sh[2], sh[3]
        if (ax, ay) == (bx, by):
            return (
                f'<circle cx="{ax:.4f}" cy="{-ay:.4f}" r="{r:.4f}" '
                f'fill="{color}" opacity="{opacity}"/>'
            )
        return (
            f'<line x1="{ax:.4f}" y1="{-ay:.4f}" x2="{bx:.4f}" y2="{-by:.4f}" stroke="{color}" '
            f'stroke-width="{2 * r:.4f}" stroke-linecap="round" opacity="{opacity}"/>'
        )
    pts = " ".join(f"{x:.4f},{-y:.4f}" for x, y in sh[1])
    return f'<polygon points="{pts}" fill="{color}" opacity="{opacity}"/>'


def write_svg(gb, hits, box, side, path):
    """What the fab's viewer shows: green board, copper under the mask, openings, silk, holes.
    The bottom view is mirrored, as seen from below."""
    if not box:
        return
    m = 1.0
    x0, y0, x1, y1 = box
    flip = side == "bottom"
    body = [f'<rect x="{x0}" y="{-y1}" width="{x1 - x0}" height="{y1 - y0}" fill="#1f5f2e"/>']
    for s in gb.get(f"copper_{side}", Gerber("")).shapes:
        body.append(_svg_shape(s, "#3d8b4f"))
    for s in gb.get(f"mask_{side}", Gerber("")).shapes:
        body.append(_svg_shape(s, "#d8a24a"))
    for s in gb.get(f"silk_{side}", Gerber("")).shapes:
        body.append(_svg_shape(s, "#f4f4f4"))
    for x, y, d in hits:
        body.append(f'<circle cx="{x:.4f}" cy="{-y:.4f}" r="{d / 2:.4f}" fill="#111"/>')
    tr = f' transform="translate({x0 + x1} 0) scale(-1 1)"' if flip else ""
    vb = f"{x0 - m} {-y1 - m} {x1 - x0 + 2 * m} {y1 - y0 + 2 * m}"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{(x1 - x0 + 2) * 20:.0f}" '
        f'height="{(y1 - y0 + 2) * 20:.0f}"><rect x="{x0 - m}" y="{-y1 - m}" '
        f'width="{x1 - x0 + 2 * m}" '
        f'height="{y1 - y0 + 2 * m}" fill="#ffffff"/><g{tr}>' + "".join(body) + "</g></svg>"
    )
    Path(path).write_text(svg, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Simulate the factory on a folder of Gerber + drill files."
    )
    ap.add_argument("folder")
    ap.add_argument("--brd", help="default: the only .brd in ../fusion or next to the folder")
    ap.add_argument("--sch")
    ap.add_argument("--fab", default=str(pc.DEFAULT_FAB))
    ap.add_argument("--out")
    ap.add_argument("--checks", help="checks.json (default: next to the .brd, or one folder up)")
    a = ap.parse_args(argv)
    folder = Path(a.folder)
    brd = Path(a.brd) if a.brd else next(iter(sorted(folder.parent.rglob("*.brd"))), None)
    if brd is None:
        print("no .brd found: pass --brd")
        return 2
    sch = Path(a.sch) if a.sch else brd.with_suffix(".sch")
    cpath = Path(a.checks) if a.checks else pc.find_checks(brd)
    checks = json.loads(cpath.read_text(encoding="utf-8")) if cpath else {}
    rep = run(folder, brd, sch, a.fab, a.out, checks)
    pc.print_report(rep, f"factory_check: {folder} (board {brd.name}; fab {Path(a.fab).name})")
    return 1 if rep.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
