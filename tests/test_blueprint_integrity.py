"""Guards for the repository itself: what git may and may not carry, and what CI must run.
Each one stands for a mistake that is easy to make once and hard to undo (a 300 KB `.f3d` per
run in the history, an STL mangled by line-ending conversion, a port file from another computer)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CAD = ("*.stl", "*.step", "*.f3d", "*.3mf", "*.obj")


def test_exports_personal_designs_and_the_port_file_are_ignored():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for rule in ("env/", ".env", "exports/", "bridge/", "my_designs/*", "!my_designs/README.md"):
        assert rule in ignore, rule
    for cad in CAD:
        assert cad in ignore, cad


def test_examples_keep_their_fusion_archive():
    """The one CAD file git carries: the example's `.f3d`, like the DE10 BKMs' `.qar`."""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "!examples/**/*.f3d" in ignore
    assert ignore.index("*.f3d") < ignore.index("!examples/**/*.f3d"), (
        "the exception must come after the rule"
    )


def test_cad_files_and_pictures_are_binary_to_git():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in CAD + ("*.png", "*.jpg"):
        assert re.search(rf"^{re.escape(pattern)}\s+binary\s*$", attributes, re.M), pattern
    assert re.search(r"^\* text=auto eol=lf", attributes, re.M)


@pytest.mark.skipif(not (ROOT / ".git").exists() or not shutil.which("git"), reason="no git repo")
def test_no_exports_or_personal_designs_are_tracked():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    ).stdout.splitlines()
    bad = [
        path
        for path in tracked
        if path.startswith(("exports/", "bridge/", "env/"))
        or (path.startswith("my_designs/") and path != "my_designs/README.md")
        or (path.endswith(".f3d") and not path.startswith("examples/"))
        or path.endswith((".stl", ".step", ".3mf"))
    ]
    assert not bad, bad


def test_ci_lints_tests_and_checks_the_skills():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for step in ("pytest", "ruff check", "python scripts/sync_skills.py --check", "gitleaks"):
        assert step in ci, step
    assert "Fusion cannot run in CI" in ci, "say why the designs are only parsed here"


def test_the_dev_requirements_point_at_a_real_install_guide():
    text = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    guide = re.search(r"docs/procedures/\S+\.md", text)
    assert guide and (ROOT / guide[0]).is_file()


def test_the_add_in_manifest_starts_with_fusion():
    """The whole setup story ("restart Fusion once") depends on runOnStartup."""
    manifest = (ROOT / "CopilotBridge" / "CopilotBridge.manifest").read_text(encoding="utf-8")
    assert re.search(r'"runOnStartup"\s*:\s*true', manifest)
