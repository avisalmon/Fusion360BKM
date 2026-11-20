"""A board's summary page (examples/NN_board/index.html) is generated from its files by
scripts/board_summary.py. These tests keep every board's page current, and prove the page reports
what the files say, including bad news."""

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import board_summary as bs  # noqa: E402

BOARD10 = ROOT / "examples" / "10_led_switch_board"
# the page concludes a board, so it is owed once the board has its EAGLE export; a board still at
# the schematic step (no fusion/*.brd yet) has nothing to conclude
BOARDS = sorted(
    p
    for p in (ROOT / "examples").iterdir()
    if (p / "circuit.py").exists() and any((p / "fusion").glob("*.brd"))
)


@pytest.mark.parametrize("folder", BOARDS, ids=lambda p: p.name)
def test_every_board_page_is_current(folder, monkeypatch):
    """Stale means the page says something the files no longer do: regenerate it."""
    assert (folder / "index.html").exists(), f"run python scripts\\board_summary.py {folder}"
    assert bs.main([str(folder), "--check"]) == 0, f"run python scripts\\board_summary.py {folder}"


def test_the_page_carries_every_part_of_the_conclusion():
    page = bs.page(BOARD10.relative_to(ROOT))
    for heading in (
        "Ready to order the bare board",
        "Quality: four layers of checks",
        "The circuit and the board",
        "What the factory receives",
        "The netlist, traced from intent to copper",
        "Parts",
        "Decisions: findings accepted",
        "Every check, line by line",
        "Every file",
        "Rebuild it from nothing",
        "Status, step by step",
    ):
        assert heading in page, heading
    for net in ("VBAT", "VSW", "LED_A", "GND"):
        assert page.count(f'data-net="{net}"') >= 4, f"{net}: schematic, board, legend, table"
    for href in re.findall(r'(?:href|src)="([^"#][^"]*)"', page):
        if not href.startswith(("http://", "https://")):
            assert (BOARD10 / href).resolve().exists(), href
    assert "Not verified yet" in page, "the README's 'not yet' rows are carried to the verdict"


def _copy_board(tmp_path):
    """A copy of board 10 placed inside the repo layout the script expects (examples/<name>)."""
    dst = ROOT / "examples" / "_tmp_board_summary_test"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(BOARD10, dst)
    return dst


def test_a_wrong_intent_turns_the_verdict_and_the_netlist_red(tmp_path):
    dst = _copy_board(tmp_path)
    try:
        c = json.loads((dst / "checks.json").read_text(encoding="utf-8"))
        c["nets"]["VSW"] = ["SW1.S", "R1.1"]  # the intent names the other throw
        (dst / "checks.json").write_text(json.dumps(c), encoding="utf-8")
        page = bs.page(dst.relative_to(ROOT))
        assert "Not ready to order" in page
        assert "our board check: 2 error(s)" in page or "our board check: 1 error(s)" in page
        assert "✗ differs" in page
    finally:
        shutil.rmtree(dst)


def test_missing_fusion_results_and_stale_approvals_are_said_plainly(tmp_path):
    dst = _copy_board(tmp_path)
    try:
        (dst / "fusion" / "fusion_checks.json").unlink()
        c = json.loads((dst / "checks.json").read_text(encoding="utf-8"))
        c["approved"].append({"code": "SHORT", "match": "nowhere", "why": "old decision"})
        (dst / "checks.json").write_text(json.dumps(c), encoding="utf-8")
        page = bs.page(dst.relative_to(ROOT))
        assert "Not ready to order" in page
        assert "Fusion&#x27;s own checks are not recorded" in page
        assert "nothing: stale, remove it" in page
    finally:
        shutil.rmtree(dst)


def test_a_fusion_finding_is_approved_only_by_a_matching_reason_in_checks_json(tmp_path):
    """Fusion's API cannot approve (Error.state has no setter) and a click in Fusion is lost on a
    rebuild, so checks.json approves Fusion's findings too: FUSION-ERC / FUSION-BOARD."""
    dst = _copy_board(tmp_path)
    erc = "POWER pin U1 V+ connected to +9V"
    finding = {"type": "error", "state": "active", "description": erc}
    try:
        f = json.loads((dst / "fusion" / "fusion_checks.json").read_text(encoding="utf-8"))
        f["erc"] = [finding]
        (dst / "fusion" / "fusion_checks.json").write_text(json.dumps(f), encoding="utf-8")
        page = bs.page(dst.relative_to(ROOT))
        assert "Fusion&#x27;s ERC: 1 finding(s) not approved" in page

        c = json.loads((dst / "checks.json").read_text(encoding="utf-8"))
        c["approved"].append({"code": "FUSION-BOARD", "match": "V+", "why": "wrong check"})
        (dst / "checks.json").write_text(json.dumps(c), encoding="utf-8")
        assert "Fusion&#x27;s ERC: 1 finding(s) not approved" in bs.page(dst.relative_to(ROOT))

        why = "V+ is the 555's 9 V pin"
        c["approved"][-1] = {"code": "FUSION-ERC", "match": "U1 V+", "why": why}
        (dst / "checks.json").write_text(json.dumps(c), encoding="utf-8")
        page = bs.page(dst.relative_to(ROOT))
        assert "Ready to order the bare board" in page
        assert "approved: V+ is the 555&#x27;s 9 V pin" in page
    finally:
        shutil.rmtree(dst)


def test_the_page_is_the_same_whether_text_files_have_crlf_or_lf(tmp_path):
    """Windows checks text out with CRLF, CI's Linux with LF: the file sizes on the page made every
    page stale on CI (2026-11-19, gotcha 45)."""
    dst = _copy_board(tmp_path)
    try:
        f = dst / "checks.json"
        lf = f.read_bytes().replace(b"\r\n", b"\n")
        f.write_bytes(lf)
        page_lf = bs.page(dst.relative_to(ROOT))
        f.write_bytes(lf.replace(b"\n", b"\r\n"))
        assert bs.page(dst.relative_to(ROOT)) == page_lf
    finally:
        shutil.rmtree(dst)


def test_files_are_listed_in_the_same_order_on_windows_and_linux():
    """Windows sorts Paths ignoring case (board_gerbers.zip before BOM.csv), Linux does not."""
    for _, rows in bs.file_rows(BOARD10.relative_to(ROOT), "board"):
        names = [r[0].rsplit("/", 1)[-1] for r in rows]
        assert names == sorted(names), names


def test_text_is_kept_readable_the_way_eagle_shows_it():
    upside_down = bs.svg_text(0, 0, 1, "R180", "bottom-left", "R1")
    assert "rotate" not in upside_down and 'text-anchor="end"' in upside_down
    mirrored = bs.svg_text(0, 0, 1, "MR0", "bottom-left", "J1")
    assert 'text-anchor="end"' in mirrored
    sideways = bs.svg_text(0, 0, 1, "R270", "center", "D1")
    assert "rotate(-90" in sideways


def test_the_3d_board_and_the_case_are_on_the_page_with_the_readmes_words():
    page = bs.page(ROOT / "examples" / "12_tiny_arcade")
    section = page.split("<h2>The board in 3D, and its case</h2>", 1)[1].split("<h2>", 1)[0]
    assert 'src="media/board3d.png"' in section
    assert 'src="media/case_v2.png"' in section
    assert "<figcaption>The case, version 2</figcaption>" in section  # the README's alt text
    assert 'href="case.py"' in section
    # a board with no 3D pictures has no such section
    assert "The board in 3D, and its case" not in bs.page(ROOT / "examples" / "10_led_switch_board")


def test_the_production_package_is_on_the_page():
    """Board 12: the case script's production files: print, fit, thumbs, assembly, BOM."""
    folder = ROOT / "examples" / "12_tiny_arcade"
    page = bs.page(folder)
    section = page.split("<h2>Production: print, assemble, everything to buy</h2>", 1)[1].split(
        "<h2>", 1
    )[0]
    for f in ("tiny_arcade_case_body.stl", "tiny_arcade_case_deck.stl", "template_top_1to1.svg"):
        assert f in section and (folder / "production" / f).exists()
    assert "nothing overlaps (0 mm3)" in section
    assert "<li>" in section and "media/case_exploded.png" in section
    for item in ("PCB", "TACT_SWITCH_6X6", "M3x8", "M3x10", "power bank", "cable"):
        assert f"<td>{item}</td>" in section
    # every production file is listed with what it is for
    assert "<b>print this</b>" in page
    assert "Production: print" not in bs.page(ROOT / "examples" / "10_led_switch_board")
