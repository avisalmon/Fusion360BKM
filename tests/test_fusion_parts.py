"""fusion_parts.py reads Fusion's cached EAGLE libraries. These tests use a tiny library written
here, so they run on any computer (CI has no Fusion): the ADD name follows EAGLE's rule, search
needs every word, the `_` technology that crashes Fusion's ADD (gotcha 22) is flagged, and the 3D
flag is per part, not per library."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fusion_parts as fp  # noqa: E402

LBR = """<?xml version="1.0" encoding="UTF-8"?>
<eagle version="9.7.0"><drawing><library>
<packages>
  <package name="AX10">
    <pad name="1" x="0" y="0" drill="0.8"/><pad name="2" x="10.16" y="0" drill="0.8"/>
  </package>
  <package name="R0603">
    <smd name="1" x="0" y="0" dx="1" dy="1" layer="1"/>
    <smd name="2" x="1.6" y="0" dx="1" dy="1" layer="1"/>
  </package>
</packages>
<devicesets>
  <deviceset name="RES_" prefix="R" uservalue="yes">
   <description>Fixed resistor</description><devices>
    <device name="AXIAL-10.16MM" package="AX10">
      <connects><connect gate="G$1" pin="1" pad="1"/></connects>
      <package3dinstances><package3dinstance package3d_urn="urn:x"/></package3dinstances>
      <technologies>
        <technology name=""><attribute name="MPN" value="CF14"/></technology>
      </technologies></device>
    <device name="0603" package="R0603">
      <technologies><technology name="_"/></technologies></device>
  </devices></deviceset>
  <deviceset name="LED?-*" prefix="D"><devices>
    <device name="3MM" package="AX10">
      <technologies><technology name="RED"/></technologies></device>
  </devices></deviceset>
</devicesets></library></drawing></eagle>"""


def make_cache(tmp_path):
    d = tmp_path / "lbr" / "adsk.eagle_library_1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "Test.lbr").write_text(LBR, encoding="utf-8")
    return [str(tmp_path / "lbr")]


def test_full_name_follows_eagles_rule():
    assert fp.full_name("RES_", "AXIAL-10.16MM") == "RES_AXIAL-10.16MM"
    assert fp.full_name("LED?-*", "3MM", "RED") == "LED3MM-RED"
    assert fp.full_name("R", "0603", "_") == "R0603_"


def test_search_needs_every_word_and_reports_pads_and_smd(tmp_path):
    dirs = make_cache(tmp_path)
    hits = fp.search(["resistor", "axial"], dirs=dirs)
    assert [h["add"] for h in hits] == ["RES_AXIAL-10.16MM@Test"]
    assert hits[0]["pads"] == 2 and not hits[0]["smd"] and hits[0]["attributes"] == {"MPN": "CF14"}
    assert [h["add"] for h in fp.search(["resistor"], dirs=dirs, smd=True)] == ["RES_0603_@Test"]


def test_the_underscore_technology_is_flagged_and_sorted_last(tmp_path):
    hits = fp.search(["resistor"], dirs=make_cache(tmp_path))
    assert [h["scriptable"] for h in hits] == [True, False]


def test_the_3d_flag_is_per_part(tmp_path):
    hits = {h["add"]: h["has_3d"] for h in fp.search(["resistor"], dirs=make_cache(tmp_path))}
    assert hits == {"RES_AXIAL-10.16MM@Test": True, "RES_0603_@Test": False}


def test_show_finds_one_part_and_describes_its_pins(tmp_path):
    p = fp.show("res_axial-10.16mm@test", dirs=make_cache(tmp_path))
    assert p and "G$1.1->1" in fp.describe(p)
    assert fp.show("NOPE@Test", dirs=make_cache(tmp_path)) is None
