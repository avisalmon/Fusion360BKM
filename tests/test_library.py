"""The part library (library/<owner>/<part>/): every part's record is complete, and no photo leaks
metadata (phone photos carry the phone's model and often the GPS position)."""

import json
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PARTS = sorted(p.parent for p in (ROOT / "library").glob("*/*/part.json"))
PHOTOS = sorted((ROOT / "library").glob("**/*.jp*g")) + sorted((ROOT / "library").glob("**/*.png"))


@pytest.mark.parametrize("photo", PHOTOS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_library_photo_carries_metadata(photo):
    im = Image.open(photo)
    assert len(im.getexif()) == 0, f"run python scripts\\library_photo.py on the original: {photo}"


@pytest.mark.parametrize("part", PARTS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_every_part_has_its_record(part):
    rec = json.loads((part / "part.json").read_text(encoding="utf-8"))
    assert rec["id"] == part.name
    for key in ("name", "category", "location", "pins", "photos", "status", "dimensions_mm"):
        assert rec.get(key) not in (None, "", [], {}), key
    numbers = [p[0] for p in rec["pins"]]
    assert numbers == list(range(1, len(numbers) + 1)), "pins numbered 1..N in order"
    for photo in rec["photos"].values():
        assert (part / photo).is_file(), photo
    for name, d in rec["dimensions_mm"].items():
        assert d.get("source"), f"{name}: every dimension says where it came from"


def test_every_parts_lbr_is_current_and_holds_one_part():
    """Fusion raised "unexpected condition ... assetAdded" on every ADD from a .lbr with two parts
    (gotcha 47): one part per file, generated from part.json, never edited by hand."""
    import xml.etree.ElementTree as ET

    sys.path.insert(0, str(ROOT / "scripts"))
    import library_build as lb

    for owner in sorted(p for p in (ROOT / "library").iterdir() if p.is_dir()):
        assert lb.main([str(owner), "--check"]) == 0, (
            f"run python scripts\\library_build.py {owner}"
        )
    for lbr in (ROOT / "library").glob("*/*/*.lbr"):
        sets = ET.parse(lbr).getroot().findall(".//devicesets/deviceset")
        assert len(sets) == 1, f"{lbr}: {len(sets)} parts in one file"
        assert lbr.stem == lbr.parent.name, "the library is named by its part's folder"


def test_supply_pins_must_be_wired_and_only_ground_joins_by_name():
    """A pwr pin joins the net of its own name with no wire; fine for GND, a trap for VCC."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import library_build as lb

    for part in PARTS:
        rec = lb.read_part(part)
        for num, name, kind, *_ in rec["pins"]:
            if kind == "power":
                assert name.upper() == "GND", f"{part.name} pin {num} {name}: use 'supply'"


def test_the_library_page_is_current_and_shows_every_part():
    """library/index.html is written by scripts/library_page.py from the parts' own files."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import library_page as lp

    assert lp.main(["--check"]) == 0, "run: python scripts/library_page.py"
    page = (ROOT / "library" / "index.html").read_text(encoding="utf-8")
    for pj in (ROOT / "library").glob("*/*/part.json"):
        assert f'id="{pj.parent.name}"' in page, pj.parent.name
    assert "Take one, give back two" in page and "לוקחים אחד, מחזירים שניים" in page
    assert 'data-mail="?subject=Take%20one%2C%20give%20back%20two' in page
    assert "north of Israel" in page
    # the owner's address is on the page only encoded, decoded by the browser (against bots)
    import base64

    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", page), "an email address in plain text"
    code = re.search(r'<body data-m="([^"]+)"', page).group(1)
    addr = base64.b64decode(code).decode()[::-1]
    assert re.fullmatch(r"[\w.+-]+@gmail\.com", addr), "the encoded address decodes to an address"
    # every local link and image on it exists
    for href in re.findall(r'(?:href|src)="([^"#][^"]*)"', page):
        if not href.startswith(("http://", "https://", "mailto:")):
            assert (ROOT / "library" / href).exists(), href
