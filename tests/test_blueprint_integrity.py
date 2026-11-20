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


def must_not_be_tracked(path):
    """Exports, the bridge's files, the virtualenv and the owner's designs stay out of git. Two
    exceptions, both in .gitignore: an example's Fusion archive, and an example's production package
    (examples/NN_name/production/*.stl|.step, the owner's call 2026-11-20)."""
    if path.startswith(("exports/", "bridge/", "env/")):
        return True
    if path.startswith("my_designs/") and path != "my_designs/README.md":
        return True
    if path.endswith(".f3d"):
        return not path.startswith("examples/")
    if path.endswith((".stl", ".step")):
        return not re.fullmatch(r"examples/\d\d_[a-z0-9_]+/production/[^/]+", path)
    return path.endswith(".3mf")


def test_the_tracking_rule_rejects_what_it_should():
    assert not must_not_be_tracked("examples/12_tiny_arcade/production/tiny_arcade_case_body.stl")
    assert not must_not_be_tracked("examples/12_tiny_arcade/production/tiny_arcade_assembly.step")
    assert not must_not_be_tracked("examples/12_tiny_arcade/production/tiny_arcade_case.f3d")
    for path in (
        "examples/12_tiny_arcade/case_body.stl",  # not in production/
        "examples/12_tiny_arcade/production/sub/x.stl",
        "exports/phone_stand.stl",
        "my_designs/phone_stand/phone_stand.step",
        "phone_stand.f3d",
        "env/Lib/site.py",
        "examples/12_tiny_arcade/production/x.3mf",
    ):
        assert must_not_be_tracked(path), path


@pytest.mark.skipif(not (ROOT / ".git").exists() or not shutil.which("git"), reason="no git repo")
def test_no_exports_or_personal_designs_are_tracked():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    ).stdout.splitlines()
    bad = [path for path in tracked if must_not_be_tracked(path)]
    assert not bad, bad


def test_ci_lints_tests_and_checks_the_skills():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for step in ("pytest", "ruff check", "python scripts/sync_skills.py --check", "gitleaks"):
        assert step in ci, step
    assert "Fusion cannot run in CI" in ci, "say why the designs are only parsed here"


def test_the_checks_we_run_before_a_commit_are_the_checks_ci_runs():
    """A push of 18 commits failed CI on `ruff format --check`, which CLAUDE.md's list left out
    (2026-11-19). Every check command in ci.yml must be in rule 7 and the skills that repeat it."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    runs = [r for r in re.findall(r"^\s*(?:- )?run: (\S.*)$", ci, re.M) if r != "|"]  # | = gitleaks
    checks = [c.strip() for r in runs for c in r.split("&&") if not c.strip().startswith("pip ")]
    assert "ruff format --check ." in checks, checks
    for doc in (
        "CLAUDE.md",
        ".claude/skills/build-example/SKILL.md",
        ".claude/skills/publish-to-github/SKILL.md",
    ):
        text = (ROOT / doc).read_text(encoding="utf-8")
        for check in checks:
            name = check.replace("python scripts/", "")
            assert name in text, f"{doc} does not list CI's check: {check}"


def test_the_dev_requirements_point_at_a_real_install_guide():
    text = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    guide = re.search(r"docs/procedures/\S+\.md", text)
    assert guide and (ROOT / guide[0]).is_file()


def test_the_add_in_manifest_starts_with_fusion():
    """The whole setup story ("restart Fusion once") depends on runOnStartup."""
    manifest = (ROOT / "CopilotBridge" / "CopilotBridge.manifest").read_text(encoding="utf-8")
    assert re.search(r'"runOnStartup"\s*:\s*true', manifest)


def test_text_files_carry_no_control_characters():
    r"""A scripted edit once turned `scripts\board_summary.py` into
    `scripts<backspace>oard_summary.py` in a skill (a shell here-doc ate the backslash;
    gotcha 41). Tabs and newlines only."""
    bad = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    found = []
    for pattern in ("*.md", "*.py", "*.ps1", "*.json", "*.html"):
        for p in ROOT.rglob(pattern):
            if {"env", ".git", "node_modules", "exports", "bridge"} & set(p.parts):
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if bad.search(line):
                    found.append(f"{p.relative_to(ROOT)}:{n}")
    assert not found, found
