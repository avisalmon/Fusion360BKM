"""factory_check.py on the real Gerber and drill files of board 10 (examples/10_led_switch_board/
factory, written by Fusion's CAM job), and on copies broken on purpose: a cut track must show as an
open in the simulated electrical test, a stray stroke as a short, a lost hole as missing."""

import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import factory_check as fc  # noqa: E402
import pcb_check as pc  # noqa: E402

EX = ROOT / "examples" / "10_led_switch_board"
GERBERS = [
    "copper_top",
    "copper_bottom",
    "profile",
    "soldermask_top",
    "soldermask_bottom",
    "silkscreen_top",
    "silkscreen_bottom",
    "solderpaste_top",
    "solderpaste_bottom",
]
BRD, SCH = EX / "fusion" / "board.brd", EX / "fusion" / "board.sch"
CHECKS = json.loads((EX / "checks.json").read_text(encoding="utf-8"))


def copy_factory(tmp_path):
    d = tmp_path / "factory"
    d.mkdir()
    for name in GERBERS:
        shutil.copy(EX / "factory" / f"{name}.gbr", d)
    for f in (EX / "factory").glob("*.xln"):
        shutil.copy(f, d)
    return d


def check(folder, tmp_path):
    return fc.run(folder, BRD, SCH, pc.DEFAULT_FAB, tmp_path / "out", CHECKS)


def codes(rep, level="ERROR"):
    return {i["code"] for i in rep.items if i["level"] == level}


def edit(path, old, new):
    t = path.read_text(encoding="utf-8")
    assert old in t, old
    path.write_text(t.replace(old, new, 1), encoding="utf-8")


def test_the_committed_factory_files_pass(tmp_path):
    rep = check(EX / "factory", tmp_path)
    assert rep.count("ERROR") == 0 and rep.count("WARN") == 0, rep.items
    assert {"FILES", "PROFILE", "DRILLS", "ETEST", "MASK", "BOM", "ZIP"} <= codes(rep, "OK")


def test_a_cut_track_is_an_open(tmp_path):
    d = copy_factory(tmp_path)
    # the last piece of VSW, into R1.1 (dropping its corner instead drew a diagonal across
    # SW1.2, and the check rightly called that a short)
    edit(d / "copper_top.gbr", "X109200Y110000D01*\n", "")
    rep = check(d, tmp_path)
    assert "OPEN" in codes(rep)


def test_a_stray_stroke_is_a_short(tmp_path):
    d = copy_factory(tmp_path)
    edit(d / "copper_top.gbr", "M02*", "D13*\nX50000Y150000D02*\nX75000Y150000D01*\nM02*")
    rep = check(d, tmp_path)
    assert "SHORT" in codes(rep)


def test_a_lost_hole_and_a_lost_layer(tmp_path):
    d = copy_factory(tmp_path)
    drill = next(d.glob("*.xln"))
    edit(drill, "X3500Y3500\n", "")
    (d / "profile.gbr").unlink()
    rep = check(d, tmp_path)
    assert {"DRILL-MISSING", "MISSING"} <= codes(rep)


def test_a_track_shrunk_below_the_fab(tmp_path):
    d = copy_factory(tmp_path)
    edit(d / "copper_top.gbr", "%ADD13C,0.500000*%", "%ADD13C,0.080000*%")
    assert "TRACK-WIDTH" in codes(check(d, tmp_path))


def test_bom_and_pick_and_place(tmp_path):
    check(EX / "factory", tmp_path)
    bom = list(csv.DictReader(open(tmp_path / "out" / "BOM.csv", encoding="utf-8")))
    assert {r["Designator"]: r["Comment"] for r in bom} == {
        "D1": "RED 5MM",
        "J1": "B2B-XH-A",
        "R1": "100R",
        "SW1": "SPDT",
    }
    cpl = {
        r["Designator"]: r
        for r in csv.DictReader(open(tmp_path / "out" / "CPL.csv", encoding="utf-8"))
    }
    assert cpl["SW1"]["Rotation"] == "270" and cpl["SW1"]["Mid X"] == "15.0000mm"
    assert (tmp_path / "out" / "board_gerbers.zip").stat().st_size > 1000


def test_gerber_reading():
    gb = fc.Gerber(
        "%FSLAX34Y34*%%MOMM*%%ADD10C,0.500000*%%ADD11R,1.0X2.0*%\n"
        "D10*X0Y0D02*X100000Y0D01*D11*X50000Y50000D03*G75*G03*X0Y0D02*\n"
        "D10*X0Y0D02*G03*X0Y0I10000J0D01*M02*"
    )
    kinds = [s["kind"] for s in gb.shapes]
    assert kinds[0] == "draw" and gb.shapes[0]["shape"][2] == pytest.approx((10.0, 0.0))
    assert gb.shapes[1]["kind"] == "flash" and gb.shapes[1]["aperture"] == pytest.approx(1.0)
    assert gb.ended and len(gb.shapes) > 10  # the full circle is drawn as short pieces
    hits, _ = fc.read_drill("M48\nMETRIC,TZ,000.000\nT1C0.800\n%\nT1\nX17540Y3500\nM30\n")
    assert hits == [(17.54, 3.5, 0.8)]
