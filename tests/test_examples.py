"""Every example is a promise: a script, its archive, pictures, a page, and what was verified.
These tests hold each `examples/NN_name/` to the contract in the `build-example` skill, and they
pass with zero examples (the catalogue's slots are "to do" until something is built and seen)."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
FOLDER = re.compile(r"^(\d{2})_([a-z][a-z0-9_]*)$")
CATALOGUE = (EXAMPLES / "index.html").read_text(encoding="utf-8")
CATALOGUE_MD = (EXAMPLES / "README.md").read_text(encoding="utf-8")


def example_dirs():
    return sorted(p for p in EXAMPLES.iterdir() if p.is_dir())


def test_every_folder_in_examples_is_a_numbered_example():
    for folder in example_dirs():
        assert FOLDER.match(folder.name), f"{folder.name}: expected NN_name"


def test_example_numbers_do_not_collide():
    numbers = [FOLDER.match(p.name)[1] for p in example_dirs()]
    assert len(numbers) == len(set(numbers)), numbers


def test_the_folder_rule_rejects_what_it_should():
    for bad in ("coin", "1_coin", "01-coin", "01_Coin", "01_", "media"):
        assert not FOLDER.match(bad), bad
    assert FOLDER.match("01_coin")


@pytest.mark.parametrize("folder", example_dirs(), ids=lambda p: p.name)
def test_the_example_has_everything_the_contract_asks_for(folder):
    slug = FOLDER.match(folder.name)[2]
    for required in ("design.py", "README.md", "index.html", "media", f"{slug}.f3d"):
        assert (folder / required).exists(), f"{folder.name}/{required}"
    assert list((folder / "media").glob("*.png")), f"{folder.name}/media has no .png: no eye check"


@pytest.mark.parametrize("folder", example_dirs(), ids=lambda p: p.name)
def test_the_example_script_follows_the_rules(folder):
    script = (folder / "design.py").read_text(encoding="utf-8")
    ast.parse(script)
    assert "new_design(" in script, "an example starts from nothing, so it can be re-run"
    assert re.search(r"^result\s*=", script, re.M), "an example ends with evidence"
    for name in re.findall(r"""add_param\(\s*['"]([^'"]+)['"]""", script):
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name), f"parameter {name!r}: word names only"


@pytest.mark.parametrize("folder", example_dirs(), ids=lambda p: p.name)
def test_the_example_page_and_readme_carry_evidence(folder):
    slug = FOLDER.match(folder.name)[2]
    page = (folder / "index.html").read_text(encoding="utf-8")
    readme = (folder / "README.md").read_text(encoding="utf-8")
    assert "../example.css" in page
    assert f"{slug}.f3d" in page, "the archive is offered for download"
    for heading in ("What was verified", "What it taught"):
        assert heading in page, heading
    assert "| Step | Done |" in readme
    assert "babook.co.il" in readme or "Babook" in readme, "say which by-hand lesson it mirrors"
    for src in re.findall(r'src="(media/[^"]+)"', page):
        assert (folder / src).exists(), src


@pytest.mark.parametrize("folder", example_dirs(), ids=lambda p: p.name)
def test_the_example_is_in_the_catalogue(folder):
    assert f'href="{folder.name}/index.html"' in CATALOGUE, f"no card for {folder.name}"
    assert folder.name in CATALOGUE_MD, f"no row for {folder.name} in examples/README.md"


def test_the_catalogue_links_resolve():
    for href in re.findall(r'href="([^"#][^"]*)"', CATALOGUE):
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        assert (EXAMPLES / href).resolve().exists(), href


def test_built_cards_are_links_and_todo_cards_are_not():
    """A card that says "built" must lead somewhere; a card that says "to do" must not pretend
    to."""
    for card in re.findall(r"<(a|div) class=\"card\"[^>]*>(.*?)</\1>", CATALOGUE, re.S):
        tag, body = card
        if 'class="tag todo"' in body:
            assert tag == "div", body[:80]
        else:
            assert tag == "a", body[:80]
