"""Helpers injected into every script executed through CopilotBridge.

Fusion's internal length unit is **cm**. Everything here takes **mm** and
converts, so scripts can be written in millimetres.

Exposed names are listed in __all__.
"""

import math
import os

import adsk.core
import adsk.fusion

__all__ = [
    "MM",
    "mm",
    "P",
    "V",
    "deg",
    "items",
    "design",
    "root",
    "new_design",
    "active_doc_name",
    "close_doc",
    "close_all_untitled",
    "new_component",
    "sketch_on",
    "rect",
    "prect",
    "eval_mm",
    "circle",
    "polygon",
    "mpt",
    "mrect",
    "mcircle",
    "sketch_normal",
    "extrude",
    "revolve",
    "fillet_all",
    "chamfer_all",
    "shell",
    "hole_at",
    "top_face",
    "combine",
    "move_body",
    "pattern_circular",
    "pattern_rect",
    "mirror_body",
    "add_param",
    "set_param",
    "params",
    "bodies",
    "body_info",
    "export_step",
    "export_stl",
    "export_f3d",
    "fit",
    "screenshot",
    "clear_design",
    "set_appearance_color",
    "ValueInput",
    "Point3D",
    "Vector3D",
]

MM = 0.1  # 1 mm in Fusion's cm world
ValueInput = adsk.core.ValueInput
Point3D = adsk.core.Point3D
Vector3D = adsk.core.Vector3D
_app = adsk.core.Application.get()


# --------------------------------------------------------------------------- units
def mm(x):
    """mm -> internal cm (float) or ValueInput when given a string expression."""
    if isinstance(x, str):
        return ValueInput.createByString(x)
    return float(x) * MM


def _vi_len(x):
    """Length -> ValueInput. Numbers are mm; strings are Fusion expressions / parameter names
    ('height', 'wall * 2', '12 mm') and stay linked to the parameters they reference."""
    if isinstance(x, str):
        return ValueInput.createByString(x)
    return ValueInput.createByReal(float(x) * MM)


def P(x=0.0, y=0.0, z=0.0):
    """Point3D from mm coordinates."""
    return Point3D.create(x * MM, y * MM, z * MM)


def V(x=0.0, y=0.0, z=0.0):
    """Vector3D from mm components."""
    return Vector3D.create(x * MM, y * MM, z * MM)


def deg(a):
    """degrees -> radians"""
    return math.radians(a)


def _iter(coll):
    """Index-based iteration over any Fusion collection (count/item)."""
    return [coll.item(i) for i in range(coll.count)]


items = _iter  # public alias for scripts: items(body.faces), items(sk.profiles), ...


# --------------------------------------------------------------------------- design access
def design():
    d = adsk.fusion.Design.cast(_app.activeProduct)
    if not d:
        raise RuntimeError("No active Fusion Design (open or create a design first).")
    return d


def root():
    return design().rootComponent


def active_doc_name():
    doc = _app.activeDocument
    return doc.name if doc else None


def close_doc(save=False, doc=None):
    """Close a document (default: the active one) without prompting. Returns True on success."""
    doc = doc or _app.activeDocument
    return bool(doc and doc.close(save))


def close_all_untitled():
    """Close every unsaved 'Untitled*' document (left-overs from failed runs)."""
    n = 0
    for d in _iter(_app.documents):
        if d.name.startswith("Untitled") and not d.isSaved:
            try:
                d.close(False)
                n += 1
            except Exception:
                pass
    return n


def new_design(name=None, parametric=True):
    """Create a fresh Fusion design document and make it active. Returns (design, root)."""
    doc = _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    d.designType = (
        adsk.fusion.DesignTypes.ParametricDesignType
        if parametric
        else adsk.fusion.DesignTypes.DirectDesignType
    )
    if name:
        try:
            d.rootComponent.name = name
        except Exception:
            pass
    return d, d.rootComponent


def clear_design():
    """Delete all bodies, sketches and sub-components in the active design's root."""
    r = root()
    for occ in _iter(r.allOccurrences):
        try:
            occ.deleteMe()
        except Exception:
            pass
    for b in _iter(r.bRepBodies):
        b.deleteMe()
    for s in _iter(r.sketches):
        s.deleteMe()
    for c in _iter(r.constructionPlanes):
        try:
            c.deleteMe()
        except Exception:
            pass


def new_component(name, parent=None):
    """Create a new (empty) component as an occurrence under parent (default root).
    Returns the component."""
    parent = parent or root()
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


# --------------------------------------------------------------------------- sketching
def sketch_on(plane="xy", comp=None, name=None, offset_mm=0.0):
    """Create a sketch on 'xy'|'xz'|'yz', a ConstructionPlane, or a planar BRepFace.
    offset_mm creates an offset construction plane first."""
    comp = comp or root()
    if isinstance(plane, str):
        plane = {
            "xy": comp.xYConstructionPlane,
            "xz": comp.xZConstructionPlane,
            "yz": comp.yZConstructionPlane,
        }[plane.lower()]
    if offset_mm:
        inp = comp.constructionPlanes.createInput()
        inp.setByOffset(plane, _vi_len(offset_mm))
        plane = comp.constructionPlanes.add(inp)
    sk = comp.sketches.add(plane)
    if name:
        sk.name = name
    return sk


def rect(sk, x0, y0, x1, y1):
    """Two-point rectangle in sketch coordinates (mm). Returns the SketchLines."""
    return sk.sketchCurves.sketchLines.addTwoPointRectangle(P(x0, y0), P(x1, y1))


def eval_mm(x):
    """Evaluate a length expression ('width', 'wall*2', '12 mm') with the design's parameters.
    Returns mm as a float."""
    if isinstance(x, str):
        return design().unitsManager.evaluateExpression(x, "mm") / MM
    return float(x)


def prect(sk, width, height, cx=0.0, cy=0.0):
    """Parametric rectangle centred on (cx, cy) in sketch coords (mm). width/height/cx/cy may be
    parameter expressions ('length', 'width - 2*wall', 'width + 15 mm'); the rectangle is fully
    constrained (horizontal/vertical, centred via a midpoint constraint, driving dimensions), so
    editing the parameters in Fusion resizes/moves it. Returns the SketchLines."""
    w, h = eval_mm(width), eval_mm(height)
    cxv, cyv = eval_mm(cx), eval_mm(cy)
    lines = sk.sketchCurves.sketchLines.addTwoPointRectangle(
        P(cxv - w / 2, cyv - h / 2), P(cxv + w / 2, cyv + h / 2)
    )
    ls = _iter(lines)
    gc = sk.geometricConstraints
    dims = sk.sketchDimensions
    HORIZ = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
    VERT = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
    horiz = [
        line
        for line in ls
        if abs(line.startSketchPoint.geometry.y - line.endSketchPoint.geometry.y) < 1e-9
    ]
    vert = [
        line
        for line in ls
        if abs(line.startSketchPoint.geometry.x - line.endSketchPoint.geometry.x) < 1e-9
    ]
    for line in horiz:
        try:
            gc.addHorizontal(line)
        except Exception:
            pass
    for line in vert:
        try:
            gc.addVertical(line)
        except Exception:
            pass
    corners = [line.startSketchPoint for line in ls]
    p_min = min(corners, key=lambda p: p.geometry.x + p.geometry.y)
    p_max = max(corners, key=lambda p: p.geometry.x + p.geometry.y)
    diag = sk.sketchCurves.sketchLines.addByTwoPoints(p_min, p_max)
    diag.isConstruction = True
    if not isinstance(cx, str) and not isinstance(cy, str) and abs(cxv) < 1e-9 and abs(cyv) < 1e-9:
        centre = sk.originPoint
    elif not isinstance(cx, str) and not isinstance(cy, str):
        centre = sk.sketchPoints.add(P(cxv, cyv))
        centre.isFixed = True
    else:  # parametric centre: position it from the sketch origin
        centre = sk.sketchPoints.add(P(cxv, cyv))
        for val, expr, orient, aligned in (
            (cxv, cx, HORIZ, gc.addVerticalPoints),
            (cyv, cy, VERT, gc.addHorizontalPoints),
        ):
            if isinstance(expr, str) or abs(val) > 1e-9:
                dm = dims.addDistanceDimension(
                    sk.originPoint, centre, orient, P(cxv / 2 + 3, cyv / 2 + 3)
                )
                dm.parameter.expression = expr if isinstance(expr, str) else f"{val} mm"
            else:
                aligned(sk.originPoint, centre)
    gc.addMidPoint(centre, diag)
    dw = dims.addDistanceDimension(
        horiz[0].startSketchPoint, horiz[0].endSketchPoint, HORIZ, P(cxv, cyv - h / 2 - 4)
    )
    dh = dims.addDistanceDimension(
        vert[0].startSketchPoint, vert[0].endSketchPoint, VERT, P(cxv + w / 2 + 4, cyv)
    )
    if isinstance(width, str):
        dw.parameter.expression = width
    if isinstance(height, str):
        dh.parameter.expression = height
    return lines


def circle(sk, cx, cy, d):
    """Circle by centre (mm) and diameter (mm)."""
    return sk.sketchCurves.sketchCircles.addByCenterRadius(P(cx, cy), d * MM / 2.0)


def polygon(sk, cx, cy, sides, circumradius_mm, rotation_deg=0.0):
    """Regular polygon as connected sketch lines. Returns list of SketchLine."""
    pts = []
    for i in range(sides):
        a = math.radians(rotation_deg) + 2 * math.pi * i / sides
        pts.append(P(cx + circumradius_mm * math.cos(a), cy + circumradius_mm * math.sin(a)))
    lines = []
    for i in range(sides):
        lines.append(sk.sketchCurves.sketchLines.addByTwoPoints(pts[i], pts[(i + 1) % sides]))
    return lines


# Model-space variants: give points in *model* mm coordinates (x, y, z) and let Fusion
# map them into the sketch's own coordinate system. This avoids guessing how the
# XZ/YZ planes orient their sketch axes.
def mpt(sk, x, y, z):
    """Model-space mm point -> sketch-space Point3D."""
    return sk.modelToSketchSpace(P(x, y, z))


def mrect(sk, p0, p1):
    """Rectangle from two opposite corners given as model-space (x, y, z) mm tuples."""
    return sk.sketchCurves.sketchLines.addTwoPointRectangle(mpt(sk, *p0), mpt(sk, *p1))


def mcircle(sk, center, d):
    """Circle with centre as model-space (x, y, z) mm tuple and diameter d (mm)."""
    return sk.sketchCurves.sketchCircles.addByCenterRadius(mpt(sk, *center), d * MM / 2.0)


def sketch_normal(sk):
    """Unit normal of a sketch plane in model space (= positive extrude direction)."""
    n = sk.xDirection.crossProduct(sk.yDirection)
    n.normalize()
    return n


# --------------------------------------------------------------------------- features
_OPS = {
    "new": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
    "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
    "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation,
    "component": adsk.fusion.FeatureOperations.NewComponentFeatureOperation,
}


def _profiles(sk_or_profiles):
    """Accept a Sketch (all profiles), a single Profile, or a list -> ObjectCollection."""
    coll = adsk.core.ObjectCollection.create()
    if isinstance(sk_or_profiles, adsk.fusion.Sketch):
        for p in _iter(sk_or_profiles.profiles):
            coll.add(p)
    elif isinstance(sk_or_profiles, (list, tuple)):
        for p in sk_or_profiles:
            coll.add(p)
    else:
        coll.add(sk_or_profiles)
    return coll


def _sketch_of(sk_or_profiles):
    if isinstance(sk_or_profiles, adsk.fusion.Sketch):
        return sk_or_profiles
    if isinstance(sk_or_profiles, (list, tuple)):
        sk_or_profiles = sk_or_profiles[0]
    return getattr(sk_or_profiles, "parentSketch", None)


def _signed_distance(sk_or_profiles, distance_mm, toward):
    """Flip the sign of distance_mm so the extrude heads along model vector `toward`."""
    if toward is None:
        return distance_mm
    sk = _sketch_of(sk_or_profiles)
    if sk is None:
        return distance_mm
    t = toward if isinstance(toward, Vector3D) else Vector3D.create(*toward)
    if sketch_normal(sk).dotProduct(t) >= 0:
        return distance_mm
    return f"-({distance_mm})" if isinstance(distance_mm, str) else -distance_mm


def extrude(
    sk_or_profiles, distance_mm, op="new", comp=None, symmetric=False, taper_deg=0.0, toward=None
):
    """Extrude profile(s) by distance (mm, negative = other direction). Returns ExtrudeFeature.
    distance_mm may be a parameter expression string ('height', 'wall + 1 mm') -> stays linked.
    op: 'new' | 'join' | 'cut' | 'intersect' | 'component'.
    toward: optional model-space direction tuple, e.g. (1, 0, 0) -> extrude heads to +X
            regardless of how the sketch plane is oriented."""
    comp = comp or root()
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(_profiles(sk_or_profiles), _OPS[op])
    dist = _vi_len(_signed_distance(sk_or_profiles, distance_mm, toward))
    if symmetric:
        inp.setSymmetricExtent(dist, True)
    else:
        inp.setDistanceExtent(False, dist)
    if taper_deg:
        inp.taperAngle = ValueInput.createByReal(math.radians(taper_deg))
    return ext.add(inp)


def revolve(sk_or_profiles, axis, angle_deg=360.0, op="new", comp=None):
    """Revolve profile(s) around axis (SketchLine / ConstructionAxis / 'x'|'y'|'z')."""
    comp = comp or root()
    if isinstance(axis, str):
        axis = {
            "x": comp.xConstructionAxis,
            "y": comp.yConstructionAxis,
            "z": comp.zConstructionAxis,
        }[axis.lower()]
    rev = comp.features.revolveFeatures
    inp = rev.createInput(_profiles(sk_or_profiles), axis, _OPS[op])
    inp.setAngleExtent(False, ValueInput.createByReal(math.radians(angle_deg)))
    return rev.add(inp)


def _edges_of(body, predicate=None):
    coll = adsk.core.ObjectCollection.create()
    for e in _iter(body.edges):
        if predicate is None or predicate(e):
            coll.add(e)
    return coll


def fillet_all(body, radius_mm, predicate=None, comp=None):
    """Fillet every edge of body (optionally filtered by predicate(edge)->bool).
    radius may be an expression."""
    comp = comp or body.parentComponent
    fil = comp.features.filletFeatures
    edges = _edges_of(body, predicate)
    if edges.count == 0:
        return None
    inp = fil.createInput()
    inp.edgeSetInputs.addConstantRadiusEdgeSet(edges, _vi_len(radius_mm), True)
    return fil.add(inp)


def chamfer_all(body, distance_mm, predicate=None, comp=None):
    comp = comp or body.parentComponent
    cham = comp.features.chamferFeatures
    edges = _edges_of(body, predicate)
    if edges.count == 0:
        return None
    inp = cham.createInput2()
    inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, _vi_len(distance_mm), True)
    return cham.add(inp)


def shell(body, open_faces, thickness_mm, comp=None):
    """Hollow a body, removing open_faces (a face or list of faces).
    thickness may be an expression."""
    comp = comp or body.parentComponent
    coll = adsk.core.ObjectCollection.create()
    for f in open_faces if isinstance(open_faces, (list, tuple)) else [open_faces]:
        coll.add(f)
    inp = comp.features.shellFeatures.createInput(coll, False)
    inp.insideThickness = _vi_len(thickness_mm)
    return comp.features.shellFeatures.add(inp)


def top_face(body, axis="z"):
    """Planar face of body with the highest centroid along axis ('x'|'y'|'z');
    use '-z' etc. for the lowest."""
    sign = -1.0 if axis.startswith("-") else 1.0
    ax = axis.lstrip("+-").lower()
    best, best_v = None, -1e99
    for f in _iter(body.faces):
        if f.geometry.objectType != adsk.core.Plane.classType():
            continue
        v = sign * getattr(f.centroid, ax)
        if v > best_v:
            best, best_v = f, v
    return best


def hole_at(face, x_mm, y_mm, diameter_mm, depth_mm=None, comp=None):
    """Simple drilled hole on a planar face at sketch-space (x, y) mm. depth None = through all."""
    comp = comp or face.body.parentComponent
    sk = comp.sketches.add(face)
    circle(sk, x_mm, y_mm, diameter_mm)
    prof = sk.profiles.item(sk.profiles.count - 1)
    for i in range(sk.profiles.count):  # pick the profile bounded by our circle
        p = sk.profiles.item(i)
        if abs(p.areaProperties().area - math.pi * (diameter_mm * MM / 2) ** 2) < 1e-6:
            prof = p
            break
    ext = comp.features.extrudeFeatures
    inp = ext.createInput(_profiles(prof), _OPS["cut"])
    if depth_mm is None:
        inp.setAllExtent(adsk.fusion.ExtentDirections.NegativeExtentDirection)
    else:
        inp.setDistanceExtent(False, ValueInput.createByReal(-depth_mm * MM))
    return ext.add(inp)


def combine(target, tools, op="join", keep_tools=False, comp=None):
    """Boolean combine. tools: body or list of bodies. op: 'join'|'cut'|'intersect'."""
    comp = comp or target.parentComponent
    coll = adsk.core.ObjectCollection.create()
    for t in tools if isinstance(tools, (list, tuple)) else [tools]:
        coll.add(t)
    inp = comp.features.combineFeatures.createInput(target, coll)
    inp.operation = _OPS[op]
    inp.isKeepToolBodies = keep_tools
    return comp.features.combineFeatures.add(inp)


def move_body(body, dx=0.0, dy=0.0, dz=0.0, comp=None):
    """Translate a body by (dx, dy, dz) mm."""
    comp = comp or body.parentComponent
    coll = adsk.core.ObjectCollection.create()
    coll.add(body)
    m = adsk.core.Matrix3D.create()
    m.translation = V(dx, dy, dz)
    inp = comp.features.moveFeatures.createInput2(coll)
    inp.defineAsFreeMove(m)
    return comp.features.moveFeatures.add(inp)


def pattern_circular(features_or_bodies, axis, count, angle_deg=360.0, comp=None):
    comp = comp or root()
    if isinstance(axis, str):
        axis = {
            "x": comp.xConstructionAxis,
            "y": comp.yConstructionAxis,
            "z": comp.zConstructionAxis,
        }[axis.lower()]
    coll = adsk.core.ObjectCollection.create()
    for f in (
        features_or_bodies
        if isinstance(features_or_bodies, (list, tuple))
        else [features_or_bodies]
    ):
        coll.add(f)
    pats = comp.features.circularPatternFeatures
    inp = pats.createInput(coll, axis)
    inp.quantity = ValueInput.createByReal(count)
    inp.totalAngle = ValueInput.createByString(f"{angle_deg} deg")
    inp.isSymmetric = False
    return pats.add(inp)


def pattern_rect(features_or_bodies, count_x, spacing_x_mm, count_y=1, spacing_y_mm=0.0, comp=None):
    comp = comp or root()
    coll = adsk.core.ObjectCollection.create()
    for f in (
        features_or_bodies
        if isinstance(features_or_bodies, (list, tuple))
        else [features_or_bodies]
    ):
        coll.add(f)
    pats = comp.features.rectangularPatternFeatures
    inp = pats.createInput(
        coll,
        comp.xConstructionAxis,
        ValueInput.createByReal(count_x),
        ValueInput.createByReal(spacing_x_mm * MM),
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType,
    )
    if count_y > 1:
        inp.setDirectionTwo(
            comp.yConstructionAxis,
            ValueInput.createByReal(count_y),
            ValueInput.createByReal(spacing_y_mm * MM),
        )
    return pats.add(inp)


def mirror_body(body, plane="yz", comp=None):
    comp = comp or body.parentComponent
    if isinstance(plane, str):
        plane = {
            "xy": comp.xYConstructionPlane,
            "xz": comp.xZConstructionPlane,
            "yz": comp.yZConstructionPlane,
        }[plane.lower()]
    coll = adsk.core.ObjectCollection.create()
    coll.add(body)
    inp = comp.features.mirrorFeatures.createInput(coll, plane)
    return comp.features.mirrorFeatures.add(inp)


# --------------------------------------------------------------------------- parameters
def add_param(name, expression, unit="mm", comment=""):
    """Add (or update) a user parameter, e.g. add_param('width', '40 mm')."""
    ups = design().userParameters
    existing = ups.itemByName(name)
    if existing:
        existing.expression = expression
        return existing
    return ups.add(name, ValueInput.createByString(expression), unit, comment)


def set_param(name, expression):
    p = design().allParameters.itemByName(name)
    if not p:
        raise KeyError(f"parameter {name!r} not found")
    p.expression = expression
    return p


def params():
    return {p.name: p.expression for p in _iter(design().allParameters)}


# --------------------------------------------------------------------------- inspect / export
def bodies(comp=None):
    comp = comp or root()
    return [comp.bRepBodies.item(i) for i in range(comp.bRepBodies.count)]


def body_info(comp=None):
    """List bodies with volume (cm3), bounding box (mm) and face/edge counts."""
    info = []
    for b in bodies(comp):
        bb = b.boundingBox
        info.append(
            {
                "name": b.name,
                "volume_cm3": round(b.volume, 4),
                "bbox_mm": {
                    "min": [
                        round(bb.minPoint.x / MM, 3),
                        round(bb.minPoint.y / MM, 3),
                        round(bb.minPoint.z / MM, 3),
                    ],
                    "max": [
                        round(bb.maxPoint.x / MM, 3),
                        round(bb.maxPoint.y / MM, 3),
                        round(bb.maxPoint.z / MM, 3),
                    ],
                },
                "faces": b.faces.count,
                "edges": b.edges.count,
            }
        )
    return info


def _ensure_dir(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return os.path.abspath(path)


def export_step(path):
    path = _ensure_dir(path)
    em = design().exportManager
    return em.execute(em.createSTEPExportOptions(path, root()))


def export_stl(path, body=None, refinement="high"):
    path = _ensure_dir(path)
    em = design().exportManager
    opts = em.createSTLExportOptions(body or root(), path)
    opts.meshRefinement = {
        "low": adsk.fusion.MeshRefinementSettings.MeshRefinementLow,
        "medium": adsk.fusion.MeshRefinementSettings.MeshRefinementMedium,
        "high": adsk.fusion.MeshRefinementSettings.MeshRefinementHigh,
    }[refinement]
    return em.execute(opts)


def export_f3d(path):
    path = _ensure_dir(path)
    em = design().exportManager
    return em.execute(em.createFusionArchiveExportOptions(path, root()))


def fit():
    _app.activeViewport.fit()


def screenshot(path, width=1280, height=800, do_fit=True):
    path = _ensure_dir(path)
    vp = _app.activeViewport
    if do_fit:
        vp.fit()
    return vp.saveAsImageFile(path, width, height)


def _base_appearance():
    """A plain plastic appearance from the stock library to clone for solid colours."""
    lib = None
    for lib_name in ("Fusion Appearance Library", "Fusion 360 Appearance Library"):
        lib = _app.materialLibraries.itemByName(lib_name)
        if lib:
            break
    if not lib:
        return None
    for cand in (
        "Plastic - Matte (Yellow)",
        "Plastic - Matte (Black)",
        "Paint - Enamel Glossy (Yellow)",
    ):
        base = lib.appearances.itemByName(cand)
        if base:
            return base
    for a in _iter(lib.appearances):  # fallback: first plastic with a colour property
        if "Plastic" in a.name:
            for prop in _iter(a.appearanceProperties):
                if prop.objectType == adsk.core.ColorProperty.classType():
                    return a
    return None


def set_appearance_color(body, r, g, b, name=None):
    """Give a body a solid colour appearance (0-255 RGB)."""
    d = design()
    name = name or f"Copilot RGB {r}-{g}-{b}"
    existing = d.appearances.itemByName(name)
    if existing:
        body.appearance = existing
        return existing
    base = _base_appearance()
    if not base:
        return None
    new = d.appearances.addByCopy(base, name)
    for prop in _iter(new.appearanceProperties):
        if prop.objectType == adsk.core.ColorProperty.classType():
            try:
                prop.value = adsk.core.Color.create(r, g, b, 255)
            except Exception:
                pass
    body.appearance = new
    return new
