"""The template is the known-good start every design is copied from. Fusion is not here to run it,
so these tests hold it to the rules a script must follow (CLAUDE.md rule 5 and the design-flow
procedure): re-runnable, in millimetres, parametric with word names, and ending in evidence."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "parametric_box"
SCRIPT = (TEMPLATE / "design.py").read_text(encoding="utf-8")
UNIT_SYMBOLS = {
    "W",
    "H",
    "A",
    "V",
    "F",
    "m",
    "s",
    "N",
    "J",
    "K",
    "Pa",
    "Hz",
    "mm",
    "cm",
    "in",
    "deg",
}


def test_the_template_parses():
    ast.parse(SCRIPT)


def test_the_template_starts_fresh_and_is_named_for_the_renamer():
    """`fusion.py new` replaces exactly this call; change it and `new` silently stops renaming."""
    assert re.search(r"""new_design\((['"])ParametricBox\1\)""", SCRIPT)
    assert SCRIPT.index("new_design(") < SCRIPT.index("add_param(")


def test_the_template_ends_with_evidence():
    """`result` is what `fusion.py run` prints: the bodies' sizes and the parameters, to check
    against the spec."""
    tree = ast.parse(SCRIPT)
    assigned = [
        t.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    ]
    assert "result" in assigned
    assert "body_info()" in SCRIPT and "params()" in SCRIPT


def test_parameters_have_word_names_not_unit_symbols():
    """Gotcha 6: `W`, `H`, `A`, `V`, `F`, `m`, `s` fail with `param name is not valid`."""
    names = re.findall(r"""add_param\(\s*['"]([^'"]+)['"]""", SCRIPT)
    assert len(names) >= 6, (
        "a parametric template with fewer than six parameters is not much of one"
    )
    for name in names:
        assert name not in UNIT_SYMBOLS, name
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name), name


def test_dimensions_reference_parameters_not_magic_numbers():
    """A box whose extrude says `25` is not parametric; it must say `"height"`."""
    for must in ('prect(sk, "length", "width")', '"height"', '"wall"'):
        assert must in SCRIPT, must


def test_the_readme_tells_the_truth_about_its_status():
    readme = (TEMPLATE / "README.md").read_text(encoding="utf-8")
    assert "| Step | Done |" in readme
    for picture in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", readme):
        assert (TEMPLATE / picture).exists(), picture
    assert "design.py" in readme


def test_the_pictures_are_there():
    """The README's evidence of the eye check: at least the plain view and the resized view."""
    pngs = {p.name for p in TEMPLATE.glob("*.png")}
    assert {"parametric_box.png", "parametric_box_resized.png"} <= pngs
