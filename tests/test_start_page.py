"""The start page is the link that goes to people. Hebrew by default (the course it points at is in
Hebrew), English one click away, the four stages all present, and every local link real."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def test_the_page_is_hebrew_first_with_english_beside_it():
    assert '<html lang="he" dir="rtl"' in HTML
    assert HTML.count('<span lang="he">') > 20
    assert HTML.count('<span lang="en">') > 20
    assert re.search(r"[\u0590-\u05FF]", HTML), "no Hebrew on a Hebrew-first page"


def test_the_page_shows_the_four_stages_in_order():
    ids = ['id="setup"', 'id="learn"', 'id="ai"', 'id="examples"']
    for must in ids:
        assert must in HTML, must
    positions = [HTML.index(i) for i in ids]
    assert positions == sorted(positions)


def test_stage_two_points_at_every_babook_lesson():
    for n in range(1, 8):
        assert f"https://babook.co.il/courses/fusion360/lesson/{n}/" in HTML, n


def test_the_page_hands_over_to_the_ai():
    for must in (
        "https://github.com/avisalmon/Fusion360BKM.git",
        "Git: Clone",
        "Tell me what to do",
        "תגיד לי מה לעשות",
        "code.visualstudio.com",
        "git-scm.com",
        "fusion.py doctor",
    ):
        assert must in HTML, must


def test_the_page_is_honest_about_what_the_setup_is():
    """Not an MCP, Fusion must be open: the two things people ask first."""
    assert "MCP" in HTML
    assert "architecture.md" in HTML


def test_local_links_and_images_exist():
    visible = re.sub(r"<!--.*?-->", "", HTML, flags=re.S)
    for href in re.findall(r'(?:href|src)="([^"#][^"]*)"', visible):
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        assert (ROOT / href).exists(), href


def test_storage_use_survives_blocked_storage():
    """Private windows and some school browsers throw on localStorage: any use must be guarded."""
    calls = re.findall(r"localStorage\.\w+", HTML)
    guarded = re.findall(r"try \{[^}]*localStorage\.\w+", HTML)
    assert calls and len(guarded) == len(calls)


def test_github_pages_serves_the_folders_as_they_are():
    """Without .nojekyll, GitHub Pages hides anything starting with a dot or an underscore."""
    assert (ROOT / ".nojekyll").exists()
