#!/usr/bin/env python
"""fusion.py - the whole flow between this repo and Autodesk Fusion, in one command.

    python scripts\\fusion.py doctor           # what is installed? is Fusion up? bridge answering?
    python scripts\\fusion.py install          # link the CopilotBridge add-in into Fusion (once)
    python scripts\\fusion.py launch           # start Fusion and wait until the bridge answers
    python scripts\\fusion.py ping             # {"fusion": "2706...", "bridge": "0.1.1", "doc": ..}
    python scripts\\fusion.py new my_bracket   # my_designs\\my_bracket\\design.py + README
    python scripts\\fusion.py run my_designs\\my_bracket\\design.py [timeout_s]  # build in Fusion
    python scripts\\fusion.py exec "print(body_info())"                           # one-liners
    python scripts\\fusion.py info             # bodies, bounding boxes, volumes, parameters
    python scripts\\fusion.py shot [exports\\view.png] [W H]           # viewport screenshot
    python scripts\\fusion.py export my_bracket [--stl] [--step] [--f3d]   # exports\\my_bracket.*
    python scripts\\fusion.py dialog [args for fusion_dialog.ps1]      # see / dismiss a dialog

Talks to the CopilotBridge add-in over HTTP on 127.0.0.1 (port in bridge\\port.txt, 8787 default).
Exit code 0 on success, 1 if the script raised inside Fusion, 2 if the bridge is unreachable.
Only the standard library is used, so any Python 3.10+ runs it.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT_FILE = os.path.join(ROOT, "bridge", "port.txt")
ADDIN_SRC = os.path.join(ROOT, "CopilotBridge")
TEMPLATE = os.path.join(ROOT, "templates", "parametric_box")
MY_DESIGNS = os.path.join(ROOT, "my_designs")
EXPORTS = os.path.join(ROOT, "exports")
DIALOG_PS1 = os.path.join(HERE, "fusion_dialog.ps1")
DEFAULT_PORT = 8787
UNREACHABLE = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

BLOCKED_HINT = (
    "Fusion answered but its main thread did not run the job: a modal dialog is probably open\n"
    "(update prompt, 'Active Sessions Exceeded', a save prompt).\n"
    "Run: python scripts\\fusion.py dialog"
)
UNREACHABLE_HINT = (
    "-> is Fusion running with the CopilotBridge add-in? python scripts\\fusion.py doctor, "
    "then python scripts\\fusion.py launch"
)


def addins_dir():
    """Where Fusion looks for add-ins (Windows path verified here; macOS path from Autodesk's
    docs)."""
    if sys.platform == "win32":
        return os.path.join(
            os.environ.get("APPDATA", ""), "Autodesk", "Autodesk Fusion 360", "API", "AddIns"
        )
    return os.path.expanduser(
        "~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
    )


def _port():
    try:
        with open(PORT_FILE, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return DEFAULT_PORT


def _request(path, payload=None, timeout=130):
    url = f"http://127.0.0.1:{_port()}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ----------------------------------------------------------------------------- talking to Fusion
def ping(quiet=False):
    """The bridge's answer, or None. A server that answers without a result means a blocked
    Fusion."""
    try:
        r = _request("/ping", timeout=35)
    except UNREACHABLE as e:
        if not quiet:
            print(f"bridge unreachable on port {_port()}: {e}")
        return None
    if not r.get("ok") or r.get("result") is None:
        if not quiet:
            print(BLOCKED_HINT)
            if r.get("error"):
                print(r["error"].strip().splitlines()[-1])
        return {"blocked": True, "raw": r}
    if not quiet:
        print(json.dumps(r.get("result"), indent=2))
    return r


def _print_job(r):
    if r.get("stdout"):
        print(r["stdout"], end="" if r["stdout"].endswith("\n") else "\n")
    if r.get("helpers_error"):
        print("[helpers failed to import]\n" + r["helpers_error"])
    if r.get("result") is not None:
        print("result =", json.dumps(r["result"], indent=2, ensure_ascii=False))
    if not r.get("ok"):
        print("--- ERROR inside Fusion ---")
        print(r.get("error"))
        return 1
    return 0


def run_code(code, name="<copilot>", timeout=120):
    try:
        r = _request(
            "/exec", {"code": code, "name": name, "timeout": timeout}, timeout=timeout + 10
        )
    except UNREACHABLE as e:
        print(f"bridge unreachable on port {_port()}: {e}\n{UNREACHABLE_HINT}")
        return 2
    return _print_job(r)


def run_file(path, timeout=120):
    path = os.path.abspath(path)
    # utf-8-sig: Notepad and PowerShell's Set-Content write a BOM, which Python
    # inside Fusion would reject as "invalid non-printable character U+FEFF".
    with open(path, encoding="utf-8-sig") as f:
        return run_code(f.read(), name=path, timeout=timeout)


def screenshot(path=None, width=1280, height=800):
    path = os.path.abspath(path or os.path.join(EXPORTS, "view.png"))
    try:
        r = _request("/screenshot", {"path": path, "width": width, "height": height}, timeout=70)
    except UNREACHABLE as e:
        print(f"bridge unreachable: {e}\n{UNREACHABLE_HINT}")
        return 2
    print(json.dumps(r.get("result") or r.get("error"), indent=2))
    return 0 if r.get("ok") else 1


def info():
    return run_code(
        'result = {"doc": active_doc_name(), "bodies": body_info(), "params": params()}', "<info>"
    )


EXPORT_CODE = """
import os
name, want = %(name)r, %(want)r
out = os.path.join(%(exports)r, name)
files = []
if 'step' in want:
    export_step(out + '.step'); files.append(out + '.step')
if 'f3d' in want:
    export_f3d(out + '.f3d'); files.append(out + '.f3d')
if 'stl' in want:
    bs = bodies()
    if len(bs) > 1:
        for b in bs:
            safe = ''.join(c if c.isalnum() else '_' for c in b.name).strip('_').lower()
            p = out + '_' + safe + '.stl'
            export_stl(p, b); files.append(p)
    export_stl(out + '.stl'); files.append(out + '.stl')
result = {'doc': active_doc_name(),
          'files': [{'file': os.path.relpath(f, %(root)r),
                     'kb': round(os.path.getsize(f) / 1024, 1)}
                    for f in files]}
"""


def export(name, formats):
    """Export the active design to exports/<name>.* (STL per body and whole, STEP, F3D)."""
    want = formats or ["stl", "step", "f3d"]
    code = EXPORT_CODE % {"name": name, "want": want, "exports": EXPORTS, "root": ROOT}
    return run_code(code, "<export>", timeout=180)


# ----------------------------------------------------------------------------- the computer
def _shortcut_target(lnk):
    ps = '(New-Object -ComObject WScript.Shell).CreateShortcut("%s").TargetPath' % lnk
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _find_fusion_exe():
    """Prefer the Start-Menu launcher (it runs the updater); fall back to any FusionLauncher.exe."""
    if sys.platform != "win32":
        mac = "/Applications/Autodesk Fusion.app"
        return mac if os.path.exists(mac) else None
    lnk = os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Autodesk",
        "Autodesk Fusion.lnk",
    )
    if os.path.exists(lnk):
        target = _shortcut_target(lnk)
        if target and os.path.exists(target):
            return target
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Autodesk", "webdeploy", "production")
    if not os.path.isdir(base):
        return None
    launchers = []
    for d in os.listdir(base):
        exe = os.path.join(base, d, "FusionLauncher.exe")
        if os.path.exists(exe):
            # the launcher-only folder (no Fusion360.exe next to it) is the one that updates
            launchers.append((os.path.exists(os.path.join(base, d, "Fusion360.exe")), exe))
    launchers.sort()
    return launchers[0][1] if launchers else None


def fusion_running():
    """True when a Fusion process exists (Windows: tasklist; macOS: pgrep)."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Fusion360.exe", "/NH"],
                capture_output=True,
                text=True,
                timeout=20,
            ).stdout
            return "Fusion360.exe" in out
        return subprocess.run(["pgrep", "-f", "Fusion"], capture_output=True).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _same_path(a, b):
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except OSError:
        return False


def _is_junction(path):
    try:
        return bool(os.lstat(path).st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, AttributeError):
        return False


def addin_status():
    """('ok' | 'elsewhere' | 'missing', detail) for the add-in link inside Fusion's AddIns
    folder."""
    link = os.path.join(addins_dir(), "CopilotBridge")
    manifest = os.path.join(link, "CopilotBridge.manifest")
    if not os.path.exists(manifest):
        return "missing", link
    if _same_path(link, ADDIN_SRC):
        return "ok", link + " -> " + ADDIN_SRC
    return "elsewhere", link + " -> " + os.path.realpath(link)


def doctor():
    """One table: what is there, what is missing, and the next command."""
    rows = []

    def row(state, what, detail=""):
        rows.append((state, what, detail))

    row("OK", f"Python {sys.version.split()[0]}", sys.executable)
    exe = _find_fusion_exe()
    row("OK" if exe else "MISS", "Autodesk Fusion installed", exe or "not found: install Fusion")
    state, detail = addin_status()
    if state == "ok":
        row("OK", "CopilotBridge add-in linked into Fusion", detail)
    elif state == "elsewhere":
        row("WARN", "CopilotBridge linked to another folder", detail + "  (fusion.py install)")
    else:
        row("MISS", "CopilotBridge add-in not installed", "run: python scripts\\fusion.py install")
    running = fusion_running()
    row(
        "OK" if running else "MISS",
        "Fusion running",
        "" if running else "python scripts\\fusion.py launch",
    )
    port_known = os.path.exists(PORT_FILE)
    row(
        "OK" if port_known else "WARN",
        f"bridge port {_port()}",
        PORT_FILE if port_known else "no port file yet; assuming 8787",
    )
    answer = ping(quiet=True) if running else None
    if answer and not answer.get("blocked"):
        res = answer.get("result") or {}
        row(
            "OK",
            f"bridge {res.get('bridge')} answers",
            f"Fusion {res.get('fusion')}, document: {res.get('doc')}",
        )
    elif answer:
        row(
            "MISS",
            "bridge answers but Fusion's main thread is blocked",
            "a modal dialog? python scripts\\fusion.py dialog",
        )
    elif running:
        row(
            "MISS",
            "bridge does not answer",
            "add-in not running: Fusion > Utilities > Scripts and Add-Ins, or restart Fusion",
        )
    else:
        row("MISS", "bridge does not answer", "Fusion is not running")

    width = max(len(what) for _, what, _ in rows)
    for state, what, detail in rows:
        print(f"[{state:4}] {what:{width}}  {detail}")
    bad = [r for r in rows if r[0] != "OK"]
    if not bad:
        print("\nEverything needed is in place. Next: python scripts\\fusion.py new <name>")
        return 0
    print(f"\n{len(bad)} thing(s) to fix, in the order above.")
    return 2


def install(force=False):
    """Link CopilotBridge/ into Fusion's AddIns folder (a junction on Windows, a symlink
    elsewhere)."""
    target_dir = addins_dir()
    link = os.path.join(target_dir, "CopilotBridge")
    state, detail = addin_status()
    if state == "ok":
        print("already installed:", detail)
        return 0
    os.makedirs(target_dir, exist_ok=True)
    if os.path.lexists(link):
        is_link = os.path.islink(link) or (sys.platform == "win32" and _is_junction(link))
        if not is_link and not force:
            print(f"{link} exists and is a real folder. Move it away, or re-run with --force.")
            return 2
        if is_link:
            os.rmdir(link) if sys.platform == "win32" else os.unlink(link)
        else:
            shutil.rmtree(link)
    if sys.platform == "win32":
        done = subprocess.run(
            ["cmd", "/c", "mklink", "/J", link, ADDIN_SRC], capture_output=True, text=True
        )
        if done.returncode != 0:
            print("mklink failed:", done.stderr.strip() or done.stdout.strip())
            return 2
    else:
        os.symlink(ADDIN_SRC, link)
    state, detail = addin_status()
    print(("installed: " if state == "ok" else "something is off: ") + detail)
    print(
        "Fusion loads add-ins at start-up: restart Fusion (or enable CopilotBridge under "
        "Utilities > Scripts and Add-Ins), then: python scripts\\fusion.py ping"
    )
    return 0 if state == "ok" else 2


def launch(wait_s=240):
    r = ping(quiet=True)
    if r and not r.get("blocked"):
        print("bridge already up")
        return 0
    if r:
        print(BLOCKED_HINT)
        return 2
    exe = _find_fusion_exe()
    if not exe:
        print(
            "Fusion not found "
            "(Windows: FusionLauncher.exe under %LOCALAPPDATA%\\Autodesk\\webdeploy)"
        )
        return 2
    print("starting", exe)
    if sys.platform == "win32":
        subprocess.Popen(
            [exe],
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        subprocess.Popen(["open", exe])
    t0 = time.time()
    while time.time() - t0 < wait_s:
        time.sleep(5)
        r = ping(quiet=True)
        if r and not r.get("blocked"):
            print(f"bridge up after {int(time.time() - t0)}s:", json.dumps(r.get("result")))
            return 0
        if r:
            print(f"  Fusion is up but blocked ({int(time.time() - t0)}s): a modal dialog?")
        else:
            print(f"  waiting for Fusion... {int(time.time() - t0)}s", flush=True)
    print(
        "gave up waiting for the bridge "
        "(Fusion may still be starting, or the add-in is not enabled)"
    )
    return 2


def dialog(args):
    if sys.platform != "win32":
        print(
            "fusion_dialog.ps1 uses Windows UI Automation; "
            "on macOS look at Fusion's window yourself."
        )
        return 2
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", DIALOG_PS1, *args]
    return subprocess.call(cmd)


# ----------------------------------------------------------------------------- designs
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")

DESIGN_README = """# {name}

## What it does

(One paragraph in the owner's words: what the part is, what it fits, which dimensions matter.)

## Parameters

| Name | Default | Meaning |
|---|---|---|
| `length` | 80 mm | outer length |

## Status (tick only what was done and seen, and say how)

| Step | Done | Evidence |
|---|---|---|
| Built in Fusion (`fusion.py run`) | [ ] | |
| Checked by numbers (`fusion.py info`: bounding box, volume, a key dimension) | [ ] | |
| Checked by eye (`fusion.py shot`, screenshot read back) | [ ] | |
| Exported (`fusion.py export {name}`) | [ ] | |
| Printed / machined and fits | [ ] | |
"""


def new(name):
    if not NAME_RE.match(name or ""):
        print(
            "name: lowercase letters, digits and _ only, starting with a letter (e.g. my_bracket)"
        )
        return 2
    dest = os.path.join(MY_DESIGNS, name)
    if os.path.exists(dest):
        print(f"{dest} already exists")
        return 2
    os.makedirs(dest)
    with open(os.path.join(TEMPLATE, "design.py"), encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"""new_design\((['"])ParametricBox\1\)""", f'new_design("{name}")', src, count=1)
    with open(os.path.join(dest, "design.py"), "w", encoding="utf-8") as f:
        f.write(src)
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
        f.write(DESIGN_README.format(name=name))
    rel = os.path.relpath(dest, ROOT)
    print(f"created {rel}\\design.py and {rel}\\README.md from the template")
    print(f"next: edit the script, then  python scripts\\fusion.py run {rel}\\design.py")
    return 0


# ----------------------------------------------------------------------------- entry point
def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "doctor":
        return doctor()
    if cmd == "install":
        return install(force="--force" in args)
    if cmd == "launch":
        return launch()
    if cmd == "ping":
        r = ping()
        return 0 if r and not r.get("blocked") else 2
    if cmd == "new":
        return new(args[0] if args else "")
    if cmd == "run":
        if not args:
            print("run: which script?")
            return 2
        return run_file(args[0], timeout=float(args[1]) if len(args) > 1 else 120)
    if cmd == "exec":
        return run_code(" ".join(args))
    if cmd == "info":
        return info()
    if cmd == "shot":
        p = args[0] if args else None
        w = int(args[1]) if len(args) > 1 else 1280
        h = int(args[2]) if len(args) > 2 else 800
        return screenshot(p, w, h)
    if cmd == "export":
        names = [a for a in args if not a.startswith("--")]
        formats = [a[2:] for a in args if a.startswith("--")]
        if not names:
            print("export: which name? (files go to exports\\<name>.*)")
            return 2
        return export(names[0], formats)
    if cmd == "dialog":
        return dialog(args)
    print("unknown command", cmd)
    print(__doc__)
    return 2


if __name__ == "__main__":
    # Fusion answers in UTF-8 (Hebrew document names, the odd BOM echoed in a traceback);
    # a cp1252 console must never make the tool itself crash while printing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
