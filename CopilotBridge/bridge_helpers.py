"""Helpers injected into every script executed through CopilotBridge.

Fusion's internal length unit is **cm**. Everything here takes **mm** and
converts, so scripts can be written in millimetres.

Exposed names are listed in __all__.
"""

import math
import os

import adsk.core
import adsk.electron
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
    "text",
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
    # electronics (EAGLE commands write, adsk.electron reads back; see fusion_reference.md)
    "ECAD_U",
    "ecad_new",
    "ecad_open",
    "ecad",
    "sch",
    "brd",
    "sch_place",
    "sch_pin",
    "sch_connect",
    "sch_wire",
    "sch_netlist",
    "brd_elements",
    "brd_move",
    "brd_outline",
    "brd_hole",
    "brd_pad",
    "brd_route",
    "brd_report",
    "brd_name_size",
    "sch_erc",
    "brd_errors",
    "ecad_export",
    "ecad_save",
    "cam_export",
    "repo_path",
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


def text(sk, string, height_mm, cx=0.0, cy=0.0, width_mm=None, font=None, bold=False):
    """Text centred at (cx, cy) in sketch mm, letters height_mm tall. Returns the SketchText.
    Text makes no sketch profiles: pass the SketchText itself to extrude(), e.g.
    extrude(t, 0.6, op='join', toward=(0, 0, 1)) to raise it, op='cut' to engrave.
    width_mm is the text box (default generous, so nothing wraps onto a second line)."""
    width_mm = width_mm or max(len(string), 1) * height_mm * 1.2
    half_h = height_mm * 0.8
    inp = sk.sketchTexts.createInput2(string, height_mm * MM)
    inp.setAsMultiLine(
        P(cx - width_mm / 2.0, cy - half_h),
        P(cx + width_mm / 2.0, cy + half_h),
        adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
        adsk.core.VerticalAlignments.MiddleVerticalAlignment,
        0,
    )
    if font:
        inp.fontName = font
    if bold:
        inp.textStyle = adsk.fusion.TextStyles.TextStyleBold
    return sk.sketchTexts.add(inp)


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


# --------------------------------------------------------------------------- electronics
# Fusion's electronics API is read-only (2706.1.17): every change is an EAGLE command sent with
# `Electron.run`, which returns "" whether it worked or not (gotcha 17). So each helper that writes
# reads the design back and raises when nothing changed. Coordinates in mm on the editor's grid.

ECAD_U = 320000  # EAGLE internal units per mm, as adsk.electron reports coordinates


def _wait_for(predicate, timeout_s=20.0):
    import time

    end = time.time() + timeout_s
    while time.time() < end:
        adsk.doEvents()
        if predicate():
            return True
        time.sleep(0.1)
    return False


def _product_type():
    p = _app.activeProduct
    return p.productType if p else None


def ecad(command):
    """Send one EAGLE command to the active schematic or board editor (no result comes back)."""
    _app.executeTextCommand("Electron.run " + command)
    adsk.doEvents()


def ecad_open(which, timeout_s=60.0):
    """Switch the active electronics design to 'sch', 'brd', '3d' or 'design' (the document that
    holds the schematic and board, the one to save) and wait until it is active. The first switch
    in a new design creates that editor's document and took over 20 s once (2026-11-18)."""
    cmd, ptype = {
        "design": ("SwitchDesignDocCmd", "EcadDesignProductType"),
        "sch": ("SwitchSchDocCmd", "SchematicProductType"),
        "brd": ("SwitchPcbDocCmd", "BoardProductType"),
        "3d": ("Switch3dPcbDocCmd", "DesignProductType"),
    }[which]
    _app.userInterface.commandDefinitions.itemById(cmd).execute()
    if not _wait_for(lambda: _product_type() == ptype, timeout_s):
        raise RuntimeError(f"ecad_open({which!r}): still {_product_type()} after {timeout_s} s")
    if which in ("sch", "brd"):
        # coordinates in commands are in the editor's grid unit; a new board is in mil, so
        # "MOVE (100 0)" meant 2.54 mm and dragged the wrong corner (gotcha 24)
        ecad("GRID MM ON")
        # answer EAGLE's yes/no questions with yes instead of a modal dialog that blocks the bridge
        # ("Part 'J1' has no user definable value. Change it anyway?", gotcha 21); every write is
        # read back anyway
        ecad("SET CONFIRM YES")
    return _app.activeProduct


def ecad_new(grid_mm=1.27):
    """A new electronics design (schematic + board), with its schematic open on a mm grid."""
    _app.userInterface.commandDefinitions.itemById("NewElectronDesignDocumentCommand").execute()
    if not _wait_for(lambda: _product_type() == "EcadDesignProductType"):
        raise RuntimeError(f"ecad_new: no electronics design appeared ({_product_type()})")
    ecad_open("sch", timeout_s=90)
    ecad(f"GRID MM {grid_mm} ON")
    return sch()


def sch():
    s = adsk.electron.Schematic.cast(_app.activeProduct)
    if not s:
        raise RuntimeError(f"No schematic is active ({_product_type()}): ecad_open('sch') first.")
    return s


def brd():
    b = adsk.electron.Board.cast(_app.activeProduct)
    if not b:
        raise RuntimeError(f"No board is active ({_product_type()}): ecad_open('brd') first.")
    return b


def _part(name):
    for p in _iter(sch().parts):
        if p.name == name:
            return p
    return None


def _answer_value_prompt(wait_s=20):
    """Start scripts/fusion_dialog.ps1 in the background: it waits for EAGLE's "Value" box
    (class cStringDialog, an element named Value) and clicks OK. Windows only."""
    import subprocess

    here = os.path.dirname(__file__)
    ps1 = os.path.normpath(os.path.join(here, "..", "scripts", "fusion_dialog.ps1"))
    if os.name != "nt" or not os.path.exists(ps1):
        raise RuntimeError("power symbols need scripts/fusion_dialog.ps1 on Windows (gotcha 35)")
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1,
         "-WaitSec", str(wait_s), "-Class", "cStringDialog", "-Expect", "Value", "-Click", "OK"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def sch_place(add_name, ref, x, y, value=None, angle=0):
    """Place `add_name` (exactly as `fusion_parts.py search` prints it) as `ref` at x, y mm.
    `angle` is 0/90/180/270, or an EAGLE orientation such as 'MR0' (mirrored)."""
    if _part(ref):
        raise RuntimeError(f"{ref} is already in the schematic")
    orient = angle if str(angle).startswith(("R", "MR", "SR", "SMR")) else f"R{angle}"
    watcher = None
    if add_name.endswith("@Power_Symbols"):
        # a power symbol (GND, +9V) asks for its net name in a modal "Value" box on every ADD
        # (gotcha 35); nothing inside Fusion can answer it, so a separate process waits for that
        # one box and clicks OK, which keeps the name the library offers. Other dialogs: left alone.
        watcher = _answer_value_prompt()
    try:
        ecad(f"ADD {add_name} {ref} {orient} ({x} {y})")
    finally:
        if watcher is not None:
            try:
                watcher.wait(timeout=30)
            except Exception:
                watcher.kill()
    if not _part(ref):
        raise RuntimeError(
            f"ADD {add_name} placed nothing: the name is not in Fusion's libraries "
            "(look it up with scripts/fusion_parts.py; gotcha 20)"
        )
    if value is not None and value != _part(ref).value:
        # a part whose library fixes its value (deviceset.userValue false: J1's JST header) opens
        # a modal "change it anyway?" that SET CONFIRM YES does NOT answer (gotcha 21, re-tested
        # 2026-11-18 on a new design): it would block the bridge, so refuse instead of asking
        if not _part(ref).deviceset.userValue:
            raise RuntimeError(
                f"{ref}'s library fixes its value ({_part(ref).value!r}); pass value=None for it, "
                f"or pick a part whose value can be set (gotcha 21)"
            )
        ecad(f"VALUE {ref} '{value}'")
        if _part(ref).value != value:
            raise RuntimeError(f"VALUE {ref} did not take: the value is {_part(ref).value!r}")
    return _part(ref)


def sch_pin(ref, pin):
    """(x, y) in mm of a placed part's pin, plus the instance origin, for drawing nets."""
    p = _part(ref)
    if not p:
        raise RuntimeError(f"no part {ref}")
    for inst in _iter(p.instances):
        for pn in _iter(inst.gate.symbol.pins):
            if pn.name == pin:
                return (pn.x / ECAD_U, pn.y / ECAD_U), (inst.x / ECAD_U, inst.y / ECAD_U)
    names = [pn.name for inst in _iter(p.instances) for pn in _iter(inst.gate.symbol.pins)]
    raise RuntimeError(f"{ref} has no pin {pin!r}; its pins: {names}")


def sch_connect(net, ref, pin, stub_mm=5.08, label=True):
    """A short wire from the pin, pointing away from the part, named `net`. Pins whose stubs share
    a name are one net; no wire ever crosses another part (and so never joins a pin by accident)."""
    (px, py), (ox, oy) = sch_pin(ref, pin)
    dx, dy = px - ox, py - oy
    if abs(dx) >= abs(dy):
        ex, ey = px + (stub_mm if dx >= 0 else -stub_mm), py
    else:
        ex, ey = px, py + (stub_mm if dy >= 0 else -stub_mm)
    ecad(f"NET {net} ({px} {py}) ({ex} {ey})")
    if label:
        ecad(f"LABEL ({ex} {ey}) ({ex} {ey})")
    if (ref, pin) not in sch_netlist().get(net, []):
        raise RuntimeError(f"NET {net} did not reach {ref}.{pin}")


def sch_wire(net, a, b, via=()):
    """A visible wire named `net` from pin `a` to pin `b`, e.g. ("J1", "1"), through the corner
    points `via` [(x, y), ...] in mm. Choose corners that pass no other pin: a wire end on a pin
    joins it (the final netlist check in a circuit script catches a wrong join)."""
    (ax, ay), _ = sch_pin(*a)
    (bx, by), _ = sch_pin(*b)
    pts = [(ax, ay), *via, (bx, by)]
    ecad(f"NET {net} " + " ".join(f"({x} {y})" for x, y in pts))
    joined = sch_netlist().get(net, [])
    missing = [p for p in (tuple(a), tuple(b)) if p not in joined]
    if missing:
        raise RuntimeError(f"NET {net} did not reach {missing}; it joins {joined}")


def sch_netlist():
    """{net name: [(part, pin), ...]} read from the schematic."""
    out = {}
    for n in _iter(sch().nets):
        out[n.name] = sorted((r.part.name, r.pin.name) for r in _iter(n.pinRefs))
    return out


def brd_elements():
    """{name: (x_mm, y_mm, angle)} for every part on the board."""
    return {e.name: (e.x / ECAD_U, e.y / ECAD_U, e.angle) for e in _iter(brd().elements)}


def brd_move(ref, x, y, angle=None):
    """Rotate a board part to `angle`, then move it to x, y mm, and check it got there.
    (Rotating after the move shifted SW1 by 1 mm: rotate first.) The name is quoted: bare, R1
    reads as an angle ("R" and a number) and ROTATE did nothing, silently (gotcha 36)."""
    if angle is not None:
        ecad(f"ROTATE =R{angle} '{ref}'")
    ecad(f"MOVE {ref} ({x} {y})")
    ex, ey, ea = brd_elements()[ref]
    if abs(ex - x) > 0.01 or abs(ey - y) > 0.01:
        raise RuntimeError(f"MOVE {ref}: it is at ({ex:.2f}, {ey:.2f}), not ({x}, {y})")
    if angle is not None and abs((ea - angle) % 360) > 0.01:
        raise RuntimeError(f"ROTATE {ref}: it is at {ea} degrees, not {angle}")


def _outline():
    return [
        (w.x1 / ECAD_U, w.y1 / ECAD_U, w.x2 / ECAD_U, w.y2 / ECAD_U)
        for w in _iter(brd().wires)
        if w.layer == 20
    ]


def brd_outline(width, height):
    """Make the board a width x height mm rectangle with its corner at 0, 0, by dragging the
    corners of the rectangle Fusion starts with. Deleting outline wires through the API raised
    "unexpected condition" dialogs until Fusion had to be killed (gotcha 25): nothing is deleted."""
    segs = _outline()
    xs = [v for s in segs for v in (s[0], s[2])]
    ys = [v for s in segs for v in (s[1], s[3])]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    if len(segs) != 4 or (x0, y0) != (0, 0):
        raise RuntimeError(f"brd_outline expects the starting rectangle at 0,0; found {segs}")
    ecad(f"MOVE ({x1} {y0}) ({width} 0)")
    ecad(f"MOVE ({x1} {y1}) ({width} {height})")
    ecad(f"MOVE ({x0} {y1}) (0 {height})")
    want = {(0, 0), (width, 0), (width, height), (0, height)}
    got = {(round(s[0], 3), round(s[1], 3)) for s in _outline()}
    if got != want:
        raise RuntimeError(f"outline corners are {sorted(got)}, not {sorted(want)}")
    return _outline()


def brd_hole(x, y, drill=3.2):
    """A plain (non-plated) mounting hole, e.g. 3.2 mm for M3."""
    before = brd().holes.count
    ecad(f"HOLE {drill} ({x} {y})")
    if brd().holes.count != before + 1:
        raise RuntimeError(f"HOLE at ({x}, {y}) did not appear")


def brd_pad(ref, pad):
    """Absolute (x, y) mm of a board part's pad: the footprint's own coordinates turned by the
    part's angle (and mirror) and moved to its position."""
    for e in _iter(brd().elements):
        if e.name != ref:
            continue
        for c in _iter(e.package.contacts):
            if c.name == pad:
                lx, ly = c.x / ECAD_U, c.y / ECAD_U
                if e.mirror:
                    lx = -lx
                a = math.radians(e.angle)
                x = e.x / ECAD_U + lx * math.cos(a) - ly * math.sin(a)
                y = e.y / ECAD_U + lx * math.sin(a) + ly * math.cos(a)
                return round(x, 4), round(y, 4)
        names = [c.name for c in _iter(e.package.contacts)]
        raise RuntimeError(f"{ref} has no pad {pad!r}; its pads: {names}")
    raise RuntimeError(f"no part {ref} on the board")


# Copper layers of Fusion's live board: top is 1, bottom is 304 (Fusion numbers 64 copper layers,
# 1-16 then 257-304). Layer 16 is "Route16", an inner layer a 2-layer board does not have: tracks
# there connect to nothing, yet the EAGLE export writes both 16 and 304 as "16 Bottom", so the file
# looks right (gotcha 37). The exported .brd and the scripts that read it keep EAGLE's 1 and 16.
BRD_LAYERS = {"top": 1, "bottom": 304}


def brd_route(signal, points, width=0.5, layer="top"):
    """A copper track for `signal` through `points` [(x, y), ...] mm on layer "top" or "bottom".
    Start and end on the signal's pads; corners must not touch another signal's pad. A track may
    change layer only at a through-hole pad (no vias here), so one route stays on one layer."""
    if layer not in BRD_LAYERS:
        raise ValueError(
            f"layer {layer!r}: use 'top' or 'bottom' (bottom is Fusion's layer 304, not 16; "
            "16 is an inner layer, gotcha 37)"
        )
    ecad(f"LAYER {BRD_LAYERS[layer]}")
    # one WIRE per straight piece: a multi-point WIRE was re-bent by Fusion into 45-degree
    # corners of its own choosing (SET WIRE_BEND 2 did not stop it; gotcha 26)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        ecad(f"WIRE '{signal}' {width} ({x0} {y0}) ({x1} {y1})")


def brd_report():
    """What the board holds: outline, holes, parts, and per signal the copper tracks (top and
    bottom), copper on any other layer (`stray`: an inner layer connects nothing on 2 layers), and
    the connections still unrouted (airwires, layer 19; zero-length ones count too)."""
    b = brd()
    copper = set(BRD_LAYERS.values())
    sig = {}
    for s in _iter(b.signals):
        ws = _iter(s.wires)
        sig[s.name] = {
            "tracks": sum(1 for w in ws if w.layer in copper),
            "stray": sorted({w.layer for w in ws if w.layer not in copper and w.layer != 19}),
            "unrouted": sum(1 for w in ws if w.layer == 19),
        }
    return {
        "outline": _outline(),
        "holes": [(h.x / ECAD_U, h.y / ECAD_U, h.drill / ECAD_U) for h in _iter(b.holes)],
        "parts": brd_elements(),
        "signals": sig,
    }


def _settle(seconds):
    """Let Fusion finish work started by a UI command (it runs on this same thread)."""
    import time

    end = time.time() + seconds
    while time.time() < end:
        adsk.doEvents()
        time.sleep(0.1)


_ERR_TYPE = {0: "warning", 1: "error", 2: "consistency", 3: "airwire", 4: "airwire"}
_ERR_STATE = {0: "active", 1: "processed", 2: "approved"}


def _errors(product):
    return [
        {
            "type": _ERR_TYPE.get(e.errorType, str(e.errorType)),
            "state": _ERR_STATE.get(e.state, str(e.state)),
            "description": e.description,
            "parts": [p for p in (e.s1, e.s2, e.s3, e.s4, e.s5, e.s6) if p],
            "layer": e.layer,
            "x": round(e.x / ECAD_U, 3),
            "y": round(e.y / ECAD_U, 3),
        }
        for e in _iter(product.errors)
    ]


def sch_erc():
    """Run Fusion's electrical rule check on the schematic and return its findings (the list in
    Fusion's Errors panel), e.g. {'type': 'error', 'description': 'Part SW1 has no value', ...}."""
    ecad_open("sch")
    _app.userInterface.commandDefinitions.itemById("Electron::ERC").execute()
    _settle(4)
    if not sch().checked:
        raise RuntimeError("the ERC did not run (the schematic is not marked checked)")
    return _errors(sch())


def brd_errors():
    """Fusion's own board check ('Check Design Rules', Electron::Errors) and its findings. Fusion
    checks as you edit: its router refuses a track or hole that breaks a rule (a stray wire stopped
    0.15 mm short of GND; a hole on a track was not placed), and the list here holds what is left,
    such as unrouted airwires. Board.checked stays False on 2706.1.17 even after the check."""
    ecad_open("brd")
    _app.userInterface.commandDefinitions.itemById("Electron::Errors").execute()
    _settle(4)
    return _errors(brd())


def ecad_export(folder, stem):
    """Write the design as EAGLE 9 XML: <folder>/<stem>.sch and <stem>.brd, the files that
    scripts/pcb_check.py and factory_check.py read (no Fusion needed after this)."""
    os.makedirs(folder, exist_ok=True)
    out = {}
    for which in ("sch", "brd"):
        p = ecad_open(which)
        path = os.path.join(folder, f"{stem}.{which}")
        em = p.exportManager
        if which == "sch":
            opts = em.createEagleSchExportOptions(path)
        else:
            opts = em.createEagleBrdExportOptions(path)
        if not em.execute(opts) or not os.path.exists(path):
            raise RuntimeError(f"export of {path} failed")
        out[which] = path
    return out


def ecad_save(
    name, folder="Fusion360BKM", project="Default Project", description="built by script"
):
    """Save the electronics design to the Fusion cloud, as a vehicle only. The source of truth is
    this repo (the board's scripts, its EAGLE export and its factory files); the cloud copy exists
    because Fusion makes CAM output only from a saved design (gotcha 28). So each board has exactly
    one cloud copy, overwritten on every build: earlier files under `name` in <project>/<folder>
    are closed (unsaved) and deleted, then the new design is saved in their place. That also keeps
    Fusion Personal's limited number of documents free. A design that is already saved gets a new
    version of the same file. It saves the design document, whatever editor is open: saveAs on the
    board document renamed only that tab and never finished (gotcha 39)."""
    if _product_type() != "EcadDesignProductType":
        ecad_open("design")
    doc = _app.activeDocument
    if doc.dataFile is not None:
        doc.save(description)
    else:
        projects = [p for p in _iter(_app.data.activeHub.dataProjects) if p.name == project]
        if not projects:
            raise RuntimeError(f"no Fusion project called {project!r}")
        root = projects[0].rootFolder
        found = [f for f in _iter(root.dataFolders) if f.name == folder]
        target = found[0] if found else root.dataFolders.add(folder)
        old = [f for f in _iter(target.dataFiles) if f.name == name]
        ids = {f.id for f in old}
        for d in list(_iter(_app.documents)):
            if d.dataFile is not None and d.dataFile.id in ids:
                d.close(False)
        # the design (.fprj) first: its schematic and board files refuse deletion while it holds
        # them ("InternalValidationError : res"), and are free once it is gone
        for f in sorted(old, key=lambda f: f.fileExtension != "fprj"):
            if not f.deleteMe():
                raise RuntimeError(f"could not delete the old cloud copy {name}.{f.fileExtension}")
        doc.saveAs(name, target, description, "")
    if not _wait_for(lambda: doc.dataFile is not None and doc.isSaved, timeout_s=60):
        raise RuntimeError("the design did not finish saving in 60 s")
    return doc.name


def cam_export(dest, job=None):
    """Gerber and drill files from a CAM job (default: production/cam/two_layer.cam) into `dest`,
    through the hidden Electron.mfgexport text command. Fusion writes to <the parent of the folder
    it is given>/<job>/<job>.gbr/CAMOutputs/..., so this runs it in a scratch folder and copies the
    files to `dest`, flat. Needs a saved design (ecad_save); paths must not contain spaces."""
    import glob
    import shutil
    import tempfile

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    job = job or os.path.join(here, "production", "cam", "two_layer.cam")
    scratch = tempfile.mkdtemp(prefix="fusion_cam_")
    if " " in job or " " in scratch:
        raise RuntimeError(f"Electron.mfgexport breaks on spaces in paths: {job} / {scratch}")
    ecad_open("brd")
    try:
        said = _app.executeTextCommand(f"Electron.mfgexport {os.path.join(scratch, 'out')} {job}")
        pattern = os.path.join(scratch, "**", "*")
        files = [f for f in glob.glob(pattern, recursive=True) if os.path.isfile(f)]
        if not files:
            raise RuntimeError(f"Electron.mfgexport said {said!r} but wrote no files")
        os.makedirs(dest, exist_ok=True)
        for f in files:
            shutil.copy2(f, os.path.join(dest, os.path.basename(f)))
        return sorted(os.path.basename(f) for f in files)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def brd_name_size(size=1.0):
    """Make every part name printed on the silkscreen (layers 25/26) at least `size` mm tall.
    Fusion's API has no text positions, so the board is exported to find each name's anchor, and
    CHANGE SIZE is sent at that point; a second export confirms it (SparkFun's parts name
    themselves 0.61 mm high; the fab prints 1.0 mm and up legibly)."""
    import tempfile
    import xml.etree.ElementTree as ET

    def names():
        path = os.path.join(tempfile.mkdtemp(prefix="fusion_brd_"), "b.brd")
        b = brd()
        b.exportManager.execute(b.exportManager.createEagleBrdExportOptions(path))
        out = {}
        for e in ET.parse(path).getroot().iter("element"):
            for a in e.findall("attribute"):
                if a.get("name") == "NAME" and a.get("layer") in ("25", "26"):
                    out[e.get("name")] = (
                        float(a.get("x")),
                        float(a.get("y")),
                        float(a.get("size")),
                    )
        return out

    ecad_open("brd")
    small = {ref: v for ref, v in names().items() if v[2] < size - 1e-6}
    for x, y, _ in small.values():
        ecad(f"CHANGE SIZE {size} ({x} {y})")
    after = names()
    still = [ref for ref in small if after[ref][2] < size - 1e-6]
    if still:
        raise RuntimeError(f"name text of {still} did not change size")
    return sorted(small)


def repo_path(*parts):
    """A path inside this repository (scripts run through the bridge have no __file__)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *parts)
