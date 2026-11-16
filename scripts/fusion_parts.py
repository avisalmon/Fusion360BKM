#!/usr/bin/env python
r"""fusion_parts.py - find the exact name of a part in Fusion's electronics libraries.

    python scripts\fusion_parts.py libs                 # libraries Fusion has cached here
    python scripts\fusion_parts.py search led 5mm       # parts matching every word
    python scripts\fusion_parts.py search jst 2 --lib Connector --tht
    python scripts\fusion_parts.py show "LED5MM@SparkFun-LED"   # pins, pads, attributes, 3D

Why it exists: an EAGLE `ADD <device>@<library>` with a name Fusion does not have places
nothing and says nothing (gotchas 17 and 20). Fusion keeps every managed library it has used
as EAGLE XML under %LOCALAPPDATA%\Autodesk\Autodesk Fusion 360\Electron\<id>\lbr\, so we
read those files instead of guessing. The name printed after ADD is the one to send:
`Electron.run ADD <name> <ref> R0 (x y)` (or `sch_place` in the helpers).
Standard library only.
"""

import argparse
import glob
import os
import sys
import xml.etree.ElementTree as ET


def cache_dirs():
    base = os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "Autodesk", "Autodesk Fusion 360", "Electron"
    )
    return sorted(glob.glob(os.path.join(base, "*", "lbr")))


def library_files(dirs=None):
    """{library name: path}. A library can be cached in several versions; the newest file wins."""
    found = {}
    for d in dirs if dirs is not None else cache_dirs():
        for path in glob.glob(os.path.join(d, "*", "*.lbr")):
            name = os.path.splitext(os.path.basename(path))[0]
            if name not in found or os.path.getmtime(path) > os.path.getmtime(found[name]):
                found[name] = path
    return dict(sorted(found.items(), key=lambda kv: kv[0].lower()))


def full_name(deviceset, device, technology=""):
    """EAGLE's rule: '?' in the set name takes the device name and '*' the technology;
    without them, both are appended."""
    name = deviceset
    name = name.replace("?", device) if "?" in name else name + device
    return name.replace("*", technology) if "*" in name else name + technology


def _text(el):
    return " ".join((el.text or "").split()) if el is not None else ""


def parts(lib_name, path):
    """Every placeable part in one library file, as dicts."""
    root = ET.parse(path).getroot()
    lib = root.find("./drawing/library")
    packages = {p.get("name"): p for p in lib.iterfind("./packages/package")}
    out = []
    for ds in lib.iterfind("./devicesets/deviceset"):
        for dev in ds.iterfind("./devices/device"):
            techs = dev.findall("./technologies/technology") or [None]
            for tech in techs:
                tname = tech.get("name", "") if tech is not None else ""
                attrs = {
                    a.get("name"): a.get("value", "")
                    for a in (tech.iterfind("attribute") if tech is not None else [])
                }
                pkg = dev.get("package") or ""
                pk = packages.get(pkg)
                pads = len(pk.findall("pad")) + len(pk.findall("smd")) if pk is not None else 0
                out.append(
                    {
                        "add": full_name(ds.get("name"), dev.get("name", ""), tname)
                        + "@"
                        + lib_name,
                        "library": lib_name,
                        "prefix": ds.get("prefix", ""),
                        "package": pkg,
                        "pads": pads,
                        "smd": pk is not None and bool(pk.findall("smd")),
                        "has_3d": bool(dev.findall("./package3dinstances/package3dinstance")),
                        # Fusion 2706.1.17 crashes ("PlacePartWorker ... assetAdded") when
                        # ADD names a part whose technology is "_" (gotcha 22): by hand only
                        "scriptable": tname != "_",
                        "description": _text(ds.find("description"))[:200],
                        "attributes": {k: v for k, v in attrs.items() if v},
                        "_ds": ds,
                        "_dev": dev,
                        "_pkg": pk,
                    }
                )
    return out


def search(words, lib=None, dirs=None, tht=False, smd=False):
    words = [w.lower() for w in words]
    hits = []
    for name, path in library_files(dirs).items():
        if lib and lib.lower() not in name.lower():
            continue
        for p in parts(name, path):
            hay = " ".join(
                [p["add"], p["package"], p["description"], " ".join(p["attributes"].values())]
            ).lower()
            if (
                all(w in hay for w in words)
                and not (tht and p["smd"])
                and not (smd and not p["smd"])
            ):
                hits.append(p)
    return sorted(hits, key=lambda p: not p["scriptable"])


def show(add_name, dirs=None):
    want = add_name.split("@")[-1].lower()
    for name, path in library_files(dirs).items():
        if name.lower() != want:
            continue
        for p in parts(name, path):
            if p["add"].lower() == add_name.lower():
                return p
    return None


def describe(p):
    lines = [
        f"ADD {p['add']}",
        f"  prefix {p['prefix']}  footprint {p['package']}  pads {p['pads']}"
        f"  {'SMD' if p['smd'] else 'through-hole'}  3D model {'yes' if p['has_3d'] else 'no'}",
    ]
    if not p["scriptable"]:
        lines.append(
            "  WARNING: technology '_' crashes Fusion's ADD command (gotcha 22): "
            "place it by hand or pick another"
        )
    if p["description"]:
        lines.append(f"  {p['description']}")
    for k, v in p["attributes"].items():
        lines.append(f"  {k} = {v}")
    connects = [
        (c.get("gate"), c.get("pin"), c.get("pad"))
        for c in p["_dev"].iterfind("./connects/connect")
    ]
    if connects:
        lines.append("  pin -> pad: " + ", ".join(f"{g}.{pin}->{pad}" for g, pin, pad in connects))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("libs")
    s = sub.add_parser("search")
    s.add_argument("words", nargs="+")
    s.add_argument("--lib")
    s.add_argument("--tht", action="store_true", help="through-hole only")
    s.add_argument("--smd", action="store_true", help="surface-mount only")
    s.add_argument("--max", type=int, default=40)
    sh = sub.add_parser("show")
    sh.add_argument("name")
    a = ap.parse_args(argv)
    if not cache_dirs():
        print(
            "No Fusion electronics library cache found. "
            "Open an electronics design in Fusion once, then retry."
        )
        return 2
    if a.cmd == "libs":
        for name, path in library_files().items():
            print(f"{name:34} {os.path.getsize(path) // 1024:6} KB")
        return 0
    if a.cmd == "search":
        hits = search(a.words, a.lib, tht=a.tht, smd=a.smd)
        for p in hits[: a.max]:
            flag = "" if p["scriptable"] else "  (crashes ADD: by hand only)"
            print(
                f"{p['add']:48} {p['package']:28} pads {p['pads']:<3} "
                f"{'SMD' if p['smd'] else 'THT'}{flag}"
            )
        print(f"{len(hits)} match(es)" + (f", first {a.max} shown" if len(hits) > a.max else ""))
        return 0 if hits else 1
    p = show(a.name)
    if not p:
        print(f"{a.name}: not found. Search first: fusion_parts.py search <words>")
        return 1
    print(describe(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
