# Documentation map

Start with the [README](../README.md) (the four stages) or the start page ([index.html](../index.html), Hebrew + English).

| File | What it is for |
|---|---|
| [get_started.md](get_started.md) | **Stage 1 for the human**: install Fusion and sign in, VS Code, Git, the chat, clone; then say "Tell me what to do" |
| [journey_checklist.md](journey_checklist.md) | The whole road as checkboxes (Phases 0-5); the chat orients from it and ticks it |
| [architecture.md](architecture.md) | How the chat drives Fusion: the add-in, the HTTP bridge, the main thread; why it is not an MCP |
| [fusion_reference.md](fusion_reference.md) | Every Fusion fact this repo relies on, each with a source and a `[verified]` / `[community]` / `[unverified]` tag; the helper API |
| [procedures/install_bridge.md](procedures/install_bridge.md) | Link the add-in, start Fusion, `doctor`, `ping`, the update dialog |
| [procedures/design_flow.md](procedures/design_flow.md) | Words or a sketch -> spec -> script -> run -> verify by numbers and by eye -> export |
| [procedures/files_and_export.md](procedures/files_and_export.md) | Open `.f3d`, import STEP/STL, export STL/STEP/F3D, screenshots, saving |
| [procedures/gotchas.md](procedures/gotchas.md) | Numbered table of what went wrong and the fix (never renumbered) |
| [lessons_log.md](lessons_log.md) | What's new in this guide, by date (the README's "Last updated" is stamped from it) |
| [blueprint_roadmap.md](blueprint_roadmap.md) | What was verified here, what was not yet, what is not covered; known limits |
| [backlog.md](backlog.md) | What to do next: the example series, helpers to write, electronics research |
| [spec.md](spec.md) | What this repo is, for whom, the decisions behind it, what is out of scope |

The learning path by hand (stage 2) is not in this repo: it is Avi Salmon's Fusion 360 course on Babook,
https://babook.co.il/courses/fusion360/ (Hebrew video lessons). The examples (stage 4) are in
[../examples/](../examples/README.md).
