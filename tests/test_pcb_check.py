"""pcb_check.py on the real board 10 export (examples/10_led_switch_board/fusion), and on copies
broken on purpose: each check must catch the fault it exists for. Runs without Fusion (CI)."""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pcb_check as pc  # noqa: E402
import pcb_geom as g  # noqa: E402

EX = ROOT / "examples" / "10_led_switch_board"
BRD, SCH = EX / "fusion" / "board.brd", EX / "fusion" / "board.sch"
CHECKS = json.loads((EX / "checks.json").read_text(encoding="utf-8"))
FAB = json.loads(pc.DEFAULT_FAB.read_text(encoding="utf-8"))


def run(tmp_path, brd=None, sch=None, checks=CHECKS, fab=None):
    b, s = BRD, SCH
    if brd is not None:
        b = tmp_path / "b.brd"
        b.write_text(brd, encoding="utf-8")
    if sch is not None:
        s = tmp_path / "b.sch"
        s.write_text(sch, encoding="utf-8")
    f = pc.DEFAULT_FAB
    if fab is not None:
        f = tmp_path / "fab.json"
        f.write_text(json.dumps(fab), encoding="utf-8")
    return pc.run(b, s, f, checks)


def codes(rep, level="ERROR"):
    return {i["code"] for i in rep.items if i["level"] == level}


def brd_text():
    return BRD.read_text(encoding="utf-8")


def test_board_10_passes_clean():
    rep = pc.run(BRD, SCH, pc.DEFAULT_FAB, CHECKS)
    assert rep.count("ERROR") == 0 and rep.count("WARN") == 0, rep.items
    ok = codes(rep, "OK")
    assert {"NET-EXPECTED", "MATCH", "ROUTED", "BOARD-SIZE", "RULESET"} <= ok


def test_every_approval_has_a_reason():
    for a in CHECKS["approved"]:
        assert a.get("code") and a.get("match") and len(a.get("why", "")) > 10, a


def test_reads_the_board_as_fusion_made_it():
    b = pc.load_brd(BRD)
    assert set(b["elements"]) == {"J1", "SW1", "R1", "D1"}
    pads = {c["owner"]: c for c in b["copper"] if c["kind"] == "pad" and c["layers"] == (1,)}
    # J1's pads have no diameter in the library: drill 0.84 + 2 x 0.254 restring = 1.348 mm,
    # the size the Gerber flashes
    assert pads["J1.1"]["diameter"] == pytest.approx(1.348)
    # SW1 turned 270 degrees: pad 1 at (0, 2.54) lands at (17.54, 3.5)
    assert pads["SW1.1"]["center"] == pytest.approx((17.54, 3.5), abs=1e-6)


def test_a_broken_track_is_unrouted(tmp_path):
    t = brd_text().replace('x2="7.5" y2="15" width="0.5"', 'x2="9" y2="16.5" width="0.5"')
    assert t != brd_text()
    assert "UNROUTED" in codes(run(tmp_path, brd=t))


def test_a_crossing_track_is_a_short(tmp_path):
    extra = '<wire x1="5" y1="15" x2="12" y2="18.734" width="0.5" layer="1"/>'
    t = brd_text().replace('<signal name="VBAT">', '<signal name="VBAT">' + extra)
    assert "SHORT" in codes(run(tmp_path, brd=t))


def test_a_thin_track_breaks_the_width_rule(tmp_path):
    t = brd_text().replace('x2="5" y2="6.5" width="0.5"', 'x2="5" y2="6.5" width="0.08"')
    assert "TRACK-WIDTH" in codes(run(tmp_path, brd=t))


def test_copper_too_near_the_edge(tmp_path):
    t = brd_text()
    plain = re.search(r"<plain>.*?</plain>", t, re.S).group(0)
    t = t.replace(plain, plain.replace('y1="20"', 'y1="19.1"').replace('y2="20"', 'y2="19.1"'))
    assert "EDGE" in codes(run(tmp_path, brd=t))


def test_an_open_outline(tmp_path):
    t = brd_text().replace('<wire x1="30" y1="20" x2="0" y2="20" width="0" layer="20"/>', "")
    assert "OUTLINE" in codes(run(tmp_path, brd=t))


def test_a_hole_on_a_track(tmp_path):
    t = brd_text().replace("<plain>", '<plain><hole x="16" y="18.5" drill="3.2"/>')
    assert "HOLE-COPPER" in codes(run(tmp_path, brd=t))


def test_a_thin_ring_and_a_loose_fusion_rule(tmp_path):
    t = brd_text().replace(
        '<param name="rlMinPadTop" value="10mil"/>', '<param name="rlMinPadTop" value="2mil"/>'
    )
    # the ring is the larger of the library's diameter and drill x rvPadTop (25 %): lower both
    t = t.replace('<param name="rvPadTop" value="0.25"/>', '<param name="rvPadTop" value="0.05"/>')
    t = t.replace('drill="0.8128" diameter="1.8796"', 'drill="0.8128" diameter="0.9"')
    rep = run(tmp_path, brd=t)
    assert "RING" in codes(rep)
    assert "RULESET" in codes(rep, "WARN")


def test_a_stricter_fab_is_applied(tmp_path):
    fab = dict(FAB, copper_clearance={"min": 0.7})
    assert "CLEARANCE" in codes(run(tmp_path, fab=fab))


def test_a_missing_connection_in_the_schematic(tmp_path):
    t = SCH.read_text(encoding="utf-8")
    m = re.search(r'<net name="LED_A".*?</net>', t, re.S).group(0)
    broken = re.sub(r'<pinref part="R1"[^>]*/>', "", m)
    rep = run(tmp_path, sch=t.replace(m, broken))
    assert {"NET-SINGLE", "NET-EXPECTED", "NET-DIFFERS"} <= codes(rep)


def test_the_intent_catches_a_rewired_schematic(tmp_path):
    checks = dict(CHECKS, nets=dict(CHECKS["nets"], VSW=["SW1.S", "R1.1"]))
    assert "NET-EXPECTED" in codes(run(tmp_path, checks=checks))


def test_an_unplanned_unconnected_pin_is_a_warning(tmp_path):
    checks = {k: v for k, v in CHECKS.items() if k != "unconnected_ok"}
    assert "PIN-UNCONNECTED" in codes(run(tmp_path, checks=checks), "WARN")


def test_netlist_rules_on_their_own():
    sch = {
        "parts": {
            "R9": {
                "package": "R",
                "value": "",
                "uservalue": True,
                "found": True,
                "connects": {("G$1", "1"): ["1"], ("G$1", "2"): ["2"]},
            },
        },
        "nets": {"N$1": {"R9.1", "R9.2"}},
        "unconnected": [],
    }
    rep = pc.Report()
    pc.check_netlist(sch, {}, rep)
    assert {"PART-SHORTED"} <= codes(rep)
    assert {"PART-NOVALUE", "NET-UNNAMED"} <= codes(rep, "WARN")


def test_approval_needs_the_matching_text():
    rep = pc.Report([{"code": "LCSC", "match": "J1", "why": "hand soldered"}])
    rep.add("WARN", "s", "LCSC", "no LCSC part number for J1")
    rep.add("WARN", "s", "LCSC", "no LCSC part number for U7")
    assert [i["level"] for i in rep.items] == ["APPROVED", "WARN"]


def test_geometry():
    assert g.gap(g.circle((0, 0), 2), g.circle((3, 0), 2)) == pytest.approx(1.0)
    assert g.gap(g.cap((0, 0), (10, 0), 0.25), g.rect(5, 1, 1, 1)) == pytest.approx(0.25)
    assert g.gap(g.octagon(0, 0, 2), g.circle((0, 0), 0.5)) < 0
    half = g.arc_points((1, 0), (-1, 0), 180, 90)
    assert half[1] == pytest.approx((0, 1), abs=1e-9)
    assert pc.length("6mil") == pytest.approx(0.1524) and pc.length("0.35mm") == 0.35
    assert pc.orientation("MR270") == (True, 270.0)


def test_parts_on_top_of_each_other(tmp_path):
    t = brd_text().replace('base_value="100R" x="16" y="11"', 'base_value="100R" x="24" y="15"')
    assert "PART-OVERLAP" in codes(run(tmp_path, brd=t), "WARN")


def test_a_part_without_a_3d_model(tmp_path):
    t = brd_text().replace(' package3d_urn="urn:adsk.eagle:package:39353/2"', "")
    assert "PART-3D" in codes(run(tmp_path, brd=t), "WARN")


def test_supply_pins_join_their_net_by_name():
    """Board 12: the ESP32's GND@14, GND@20, GND@26 are "pwr" pins with no wire. Fusion's board puts
    their pads on GND; the schematic must too, or board and schematic look different."""
    sch = pc.load_sch(ROOT / "examples" / "12_tiny_arcade" / "fusion" / "board.sch")
    assert {"U1.14", "U1.20", "U1.26"} <= sch["nets"]["GND"]
    assert not [u for u in sch["unconnected"] if u[1].startswith("GND")]


def test_a_part_from_our_library_has_its_3d_model_in_part_json():
    """Board 12's parts come from library/avi_salmon, whose part.json carries the model that
    board3d.py and case.py build: no PART-3D warning; a library with no such model still warns."""
    els = pc.load_brd(ROOT / "examples" / "12_tiny_arcade" / "fusion" / "board.brd")["elements"]
    assert els["U1"]["model3d"] == "library/avi_salmon/esp32_devkitc_38/part.json"
    assert all(e["model3d"] for e in els.values())
    assert pc.library_model("no_such_part") == ""
