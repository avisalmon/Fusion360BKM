"""scripts/fusion.py is the one command between the repo and Fusion. Fusion itself is not here
(GUI, licence), so these tests cover the logic that does not need it: the usage, the names it
accepts, where the port comes from, how a new design is made from the template, and how it
judges the add-in link."""

import ast
from pathlib import Path

import pytest

from scripts import fusion

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = (
    "doctor",
    "install",
    "launch",
    "ping",
    "new",
    "run",
    "exec",
    "info",
    "shot",
    "export",
    "dialog",
)


def test_help_lists_every_command_and_exits_clean(capsys):
    assert fusion.main([]) == 0
    assert fusion.main(["--help"]) == 0
    out = capsys.readouterr().out
    for cmd in COMMANDS:
        assert f"fusion.py {cmd}" in out, cmd


def test_main_dispatches_every_documented_command():
    """The docstring and the dispatcher must agree, or the help lies."""
    source = (ROOT / "scripts" / "fusion.py").read_text(encoding="utf-8")
    for cmd in COMMANDS:
        assert f'cmd == "{cmd}"' in source, cmd


def test_an_unknown_command_is_refused_with_the_usage(capsys):
    assert fusion.main(["frobnicate"]) == 2
    assert "unknown command frobnicate" in capsys.readouterr().out


def test_run_and_export_without_a_target_say_what_is_missing(capsys):
    assert fusion.main(["run"]) == 2
    assert fusion.main(["export"]) == 2
    out = capsys.readouterr().out
    assert "which script" in out and "which name" in out


@pytest.mark.parametrize("name", ["a", "box", "my_bracket", "box2", "a" * 41])
def test_design_names_that_are_safe_folder_names_pass(name):
    assert fusion.NAME_RE.match(name)


@pytest.mark.parametrize(
    "name", ["", "My Bracket", "2box", "a-b", "a" * 42, "box.py", "../x", "Box"]
)
def test_design_names_that_would_make_odd_folders_are_refused(name):
    assert not fusion.NAME_RE.match(name)


def test_the_port_is_read_from_the_bridge_file_and_falls_back_to_8787(tmp_path, monkeypatch):
    port_file = tmp_path / "port.txt"
    monkeypatch.setattr(fusion, "PORT_FILE", str(port_file))
    assert fusion._port() == 8787, "no file yet: the default"
    port_file.write_text("8796\n", encoding="utf-8")
    assert fusion._port() == 8796, "the add-in fell back to another port and said so"
    port_file.write_text("not a number", encoding="utf-8")
    assert fusion._port() == 8787


def test_new_copies_the_template_and_renames_the_design(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fusion, "MY_DESIGNS", str(tmp_path / "my_designs"))
    assert fusion.new("my_part") == 0
    folder = tmp_path / "my_designs" / "my_part"
    script = (folder / "design.py").read_text(encoding="utf-8")
    ast.parse(script)
    assert 'new_design("my_part")' in script
    assert "ParametricBox" not in script
    readme = (folder / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# my_part")
    assert "fusion.py export my_part" in readme
    assert "| Step | Done | Evidence |" in readme, "every design carries an honest status table"
    out = capsys.readouterr().out
    assert "fusion.py run" in out, "the next command is printed, not left to be guessed"


def test_new_refuses_to_overwrite_and_refuses_bad_names(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fusion, "MY_DESIGNS", str(tmp_path / "my_designs"))
    assert fusion.new("part") == 0
    assert fusion.new("part") == 2
    assert "already exists" in capsys.readouterr().out
    assert fusion.new("Bad Name") == 2
    assert fusion.new("") == 2


def test_run_strips_the_bom_that_windows_editors_write(tmp_path, monkeypatch):
    """Notepad and PowerShell's Set-Content -Encoding UTF8 prefix a BOM; Python inside Fusion
    would reject it as an invalid character on line 1, so `run` must not forward it."""
    script = tmp_path / "design.py"
    script.write_bytes(b"\xef\xbb\xbfresult = 1\n")
    seen = {}
    monkeypatch.setattr(fusion, "run_code", lambda code, **kw: seen.setdefault("code", code))
    fusion.run_file(str(script))
    assert seen["code"] == "result = 1\n"


def test_printing_never_crashes_on_a_cp1252_console():
    """The tool reconfigures stdout to UTF-8 with replacement before `main`, so a Hebrew document
    name or a stray BOM echoed in a traceback is printed, not turned into a UnicodeEncodeError."""
    source = (ROOT / "scripts" / "fusion.py").read_text(encoding="utf-8")
    tail = source[source.index('if __name__ == "__main__":') :]
    assert 'reconfigure(encoding="utf-8", errors="replace")' in tail
    assert "ensure_ascii=False" in source, "results are printed as they are, not escaped"


def test_addin_status_missing_when_fusion_has_no_link(tmp_path, monkeypatch):
    monkeypatch.setattr(fusion, "addins_dir", lambda: str(tmp_path))
    state, detail = fusion.addin_status()
    assert state == "missing"
    assert detail.endswith("CopilotBridge")


def test_addin_status_ok_when_the_link_is_this_repo(tmp_path, monkeypatch):
    link = tmp_path / "CopilotBridge"
    link.mkdir()
    (link / "CopilotBridge.manifest").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fusion, "addins_dir", lambda: str(tmp_path))
    monkeypatch.setattr(fusion, "ADDIN_SRC", str(link))
    state, _detail = fusion.addin_status()
    assert state == "ok"


def test_addin_status_elsewhere_when_the_link_points_at_an_old_copy(tmp_path, monkeypatch):
    """The repo moved (gotcha 13): doctor must say so and point at `install`."""
    link = tmp_path / "AddIns" / "CopilotBridge"
    link.mkdir(parents=True)
    (link / "CopilotBridge.manifest").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fusion, "addins_dir", lambda: str(tmp_path / "AddIns"))
    monkeypatch.setattr(fusion, "ADDIN_SRC", str(tmp_path / "new_repo" / "CopilotBridge"))
    state, detail = fusion.addin_status()
    assert state == "elsewhere"
    assert "->" in detail


def test_the_tool_needs_only_the_standard_library():
    """Any Python 3.10+ runs it, with nothing installed; that is the promise in the README."""
    tree = ast.parse((ROOT / "scripts" / "fusion.py").read_text(encoding="utf-8"))
    stdlib = {"json", "os", "re", "shutil", "subprocess", "sys", "time", "urllib"}
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert {a.name.split(".")[0] for a in node.names} <= stdlib
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in stdlib


def test_the_blocked_hint_names_the_fix():
    """`ping` answering but jobs timing out is the most confusing failure; the hint must say
    `dialog`."""
    assert "fusion.py dialog" in fusion.BLOCKED_HINT
    assert "modal dialog" in fusion.BLOCKED_HINT
    assert "fusion.py doctor" in fusion.UNREACHABLE_HINT
