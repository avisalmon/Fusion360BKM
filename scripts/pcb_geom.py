"""Plane geometry for the board checks (pcb_check.py, factory_check.py); standard library only.

Every piece of copper, silkscreen or drill is one of two shapes, in mm:
  ("cap", (ax, ay), (bx, by), r)   a capsule: the points within r of the segment a-b
                                   (a round pad is a capsule with a == b; a track is a capsule)
  ("poly", [(x, y), ...])          a convex polygon (square, octagon or SMD pads, Gerber regions)
gap(s, t) is the clearance between two shapes: > 0 apart, <= 0 touching or overlapping.
"""

import math


def cap(a, b, r):
    return ("cap", (float(a[0]), float(a[1])), (float(b[0]), float(b[1])), float(r))


def circle(c, d):
    return cap(c, c, d / 2)


def poly(points):
    return ("poly", [(float(x), float(y)) for x, y in points])


def rect(cx, cy, w, h, angle=0.0):
    """A w x h rectangle centred on cx, cy, turned by `angle` degrees."""
    return poly(
        rotate_all(
            [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], angle, (cx, cy)
        )
    )


def octagon(cx, cy, d, angle=0.0):
    """EAGLE's octagon pad: flats d apart (so its corners reach d / 2 / cos 22.5 deg)."""
    rr = d / 2 / math.cos(math.radians(22.5))
    pts = [
        (rr * math.cos(math.radians(22.5 + 45 * i)), rr * math.sin(math.radians(22.5 + 45 * i)))
        for i in range(8)
    ]
    return poly(rotate_all(pts, angle, (cx, cy)))


def rotate(p, angle, about=(0.0, 0.0)):
    a = math.radians(angle)
    x, y = p
    return (
        about[0] + x * math.cos(a) - y * math.sin(a),
        about[1] + x * math.sin(a) + y * math.cos(a),
    )


def rotate_all(points, angle, offset=(0.0, 0.0)):
    return [rotate(p, angle, offset) for p in points]


def transform(shape, fn):
    """Apply a point function (move/turn/mirror) to every point of a shape."""
    if shape[0] == "cap":
        return ("cap", fn(shape[1]), fn(shape[2]), shape[3])
    return ("poly", [fn(p) for p in shape[1]])


def arc_points(p1, p2, curve_deg, step_deg=10.0):
    """An EAGLE arc (a wire with `curve`: degrees counter-clockwise from p1 to p2) as points."""
    if not curve_deg:
        return [p1, p2]
    (x1, y1), (x2, y2) = p1, p2
    th = math.radians(curve_deg)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    c = math.hypot(dx, dy) / 2
    if c == 0:
        return [p1, p2]
    h = c / math.tan(th / 2)
    cx, cy = mx - dy / (2 * c) * h, my + dx / (2 * c) * h
    a0 = math.atan2(y1 - cy, x1 - cx)
    r = math.hypot(x1 - cx, y1 - cy)
    n = max(2, math.ceil(abs(curve_deg) / step_deg))
    return [
        (cx + r * math.cos(a0 + th * i / n), cy + r * math.sin(a0 + th * i / n))
        for i in range(n + 1)
    ]


# ----------------------------------------------------------------------------- distances
def _pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_cross(a, b, c, d):
    d1, d2, d3, d4 = _cross(c, d, a), _cross(c, d, b), _cross(a, b, c), _cross(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and 0 not in (d1, d2, d3, d4)


def seg_seg(a, b, c, d):
    if _segments_cross(a, b, c, d):
        return 0.0
    return min(_pt_seg(a, c, d), _pt_seg(b, c, d), _pt_seg(c, a, b), _pt_seg(d, a, b))


def inside(p, points):
    """Point in polygon (even-odd rule); `points` closed implicitly."""
    x, y = p
    hit = False
    n = len(points)
    for i in range(n):
        (x1, y1), (x2, y2) = points[i], points[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def _edges(points):
    return [(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]


def gap(s, t):
    """Clearance between two shapes in mm: > 0 apart, <= 0 touching or overlapping."""
    if s[0] == "poly" and t[0] == "cap":
        s, t = t, s
    if s[0] == "cap" and t[0] == "cap":
        return seg_seg(s[1], s[2], t[1], t[2]) - s[3] - t[3]
    if s[0] == "cap":
        a, b, r = s[1], s[2], s[3]
        if inside(a, t[1]) or inside(b, t[1]):
            return -r
        return min(seg_seg(a, b, c, d) for c, d in _edges(t[1])) - r
    if any(inside(p, t[1]) for p in s[1]) or any(inside(p, s[1]) for p in t[1]):
        return -1.0
    return min(seg_seg(a, b, c, d) for a, b in _edges(s[1]) for c, d in _edges(t[1]))


def bbox(shape):
    if shape[0] == "cap":
        (ax, ay), (bx, by), r = shape[1], shape[2], shape[3]
        return min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r
    xs = [p[0] for p in shape[1]]
    ys = [p[1] for p in shape[1]]
    return min(xs), min(ys), max(xs), max(ys)


def near(s, t, margin):
    """Cheap test before gap(): could s and t be closer than `margin`?"""
    a, b = bbox(s), bbox(t)
    return not (
        a[2] + margin < b[0] or b[2] + margin < a[0] or a[3] + margin < b[1] or b[3] + margin < a[1]
    )


def gap_to_lines(shape, segments):
    """Clearance from a shape to a set of plain line segments (the board outline)."""
    line = [cap(a, b, 0) for a, b in segments]
    return min(gap(shape, ln) for ln in line) if line else math.inf


# ----------------------------------------------------------------------------- connectivity
class Groups:
    """Union-find: which items are joined into one piece of copper."""

    def __init__(self):
        self.up = {}

    def find(self, x):
        self.up.setdefault(x, x)
        while self.up[x] != x:
            self.up[x] = self.up[self.up[x]]
            x = self.up[x]
        return x

    def join(self, a, b):
        self.up[self.find(a)] = self.find(b)

    def groups(self):
        out = {}
        for x in list(self.up):
            out.setdefault(self.find(x), set()).add(x)
        return list(out.values())
