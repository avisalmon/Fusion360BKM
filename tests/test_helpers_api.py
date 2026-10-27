"""The helpers are what every design script is written against, and they can only be *run* inside
Fusion (they import `adsk`). What can be checked here without Fusion: that the names they promise
exist, that lengths are taken in millimetres, and that the reference documents every one of them."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELPERS = ROOT / "CopilotBridge" / "bridge_helpers.py"
REFERENCE = ROOT / "docs" / "fusion_reference.md"
TREE = ast.parse(HELPERS.read_text(encoding="utf-8"))


def exported():
    for node in TREE.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            return [ast.literal_eval(elt) for elt in node.value.elts]
    raise AssertionError("bridge_helpers.py has no __all__")


def defined_at_top_level():
    names = set()
    for node in TREE.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
    return names


def test_every_promised_name_is_defined():
    missing = set(exported()) - defined_at_top_level()
    assert not missing, missing


def test_no_name_is_promised_twice():
    names = exported()
    assert len(names) == len(set(names))


def test_private_helpers_are_not_exported():
    assert not [n for n in exported() if n.startswith("_")]


def test_the_module_works_in_millimetres():
    """Fusion's API is in cm (gotcha 4); the whole point of the helpers is that scripts never
    see it."""
    text = HELPERS.read_text(encoding="utf-8")
    assert re.search(r"^MM = 0\.1\b", text, re.M), "MM must be 1 mm in Fusion's cm world"
    assert "mm" in (ast.get_docstring(TREE) or ""), "the docstring must say the unit"


def test_the_reference_documents_every_exported_helper():
    """A helper that is not in docs/fusion_reference.md does not exist for the assistant."""
    block = re.search(
        r"## The helper API.*?```text\n(.*?)```", REFERENCE.read_text(encoding="utf-8"), re.S
    )
    assert block, "fusion_reference.md lost its helper API block"
    documented = set(re.findall(r"\b([A-Za-z_]\w*)\s*(?:\(|=|,|$)", block[1], re.M))
    missing = [n for n in exported() if n not in documented]
    assert not missing, f"not in the reference's helper block: {missing}"


def test_the_reference_does_not_promise_helpers_that_do_not_exist():
    block = re.search(
        r"## The helper API.*?```text\n(.*?)```", REFERENCE.read_text(encoding="utf-8"), re.S
    )
    calls = set(re.findall(r"^(?:[\w, ]*=\s*)?([a-z_]\w*)\(", block[1], re.M))
    calls |= set(re.findall(r";\s*([a-z_]\w*)\(", block[1]))
    phantom = calls - set(exported()) - {"lambda"}
    assert not phantom, phantom


def test_only_the_standard_library_and_adsk_are_imported():
    """Fusion's embedded Python has no third-party packages: nothing to pip install, ever."""
    for node in TREE.body:
        if isinstance(node, ast.Import):
            tops = {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            tops = {(node.module or "").split(".")[0]}
        else:
            continue
        assert tops <= {"os", "math", "adsk", "json", "re", "sys", "time", "traceback"}, tops
