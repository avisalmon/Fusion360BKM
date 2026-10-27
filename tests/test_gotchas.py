"""The gotchas table is pointed at by number from skills, docs and lessons. Numbers must never
move, every row must say how we know, and no page may point at a row that is not there."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOTCHAS = (ROOT / "docs" / "procedures" / "gotchas.md").read_text(encoding="utf-8")
ROW = re.compile(r"^\|\s*(\d+)\s*\|(.*)\|$", re.M)
SKIP = {"env", ".git", ".ruff_cache", ".pytest_cache", "exports", "bridge", ".github"}


def rows():
    return [(int(m[1]), [c.strip() for c in m[2].split("|")]) for m in ROW.finditer(GOTCHAS)]


def test_numbers_run_from_one_without_gaps_or_repeats():
    numbers = [n for n, _ in rows()]
    assert numbers == list(range(1, len(numbers) + 1)), numbers


def test_every_row_has_a_gotcha_a_fix_and_how_we_know():
    for number, cells in rows():
        assert len(cells) == 3, (number, cells)
        for cell in cells:
            assert cell, f"gotcha {number} has an empty cell"


def test_the_rows_the_blueprint_relies_on_are_where_it_says():
    """Skills and the reference were written against these numbers."""
    by_number = dict(rows())
    assert "twice" in by_number[5][0], "gotcha 5 is the add-in loading twice through the junction"
    assert "YZ" in by_number[7][0], "gotcha 7 is the sketch-axis mapping on the YZ plane"
    assert "modal dialog" in by_number[1][0].lower() or "modal" in by_number[1][0]


def test_no_page_points_at_a_gotcha_that_does_not_exist():
    last = max(n for n, _ in rows())
    pointers = []
    for path in ROOT.rglob("*.md"):
        if SKIP & set(path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8")
        for n in re.findall(r"\bgotcha #?(\d+)\b", text, re.I):
            if int(n) > last:
                pointers.append(f"{path.relative_to(ROOT)}: gotcha {n} (table ends at {last})")
    assert not pointers, "\n".join(pointers)


def test_the_table_says_it_is_never_renumbered():
    assert "never renumbered" in GOTCHAS
