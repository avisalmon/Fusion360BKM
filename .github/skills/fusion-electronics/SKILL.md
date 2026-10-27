---
name: fusion-electronics
description: >
  The research-first playbook for the next stage of this blueprint, Fusion's Electronics workspace
  (schematics, PCB layout, footprints, 3D PCB into an enclosure). Nothing in it is verified yet: it says
  exactly what is known, what to probe in the running Fusion first, how to record findings in the
  reference before using them, and the fallback plan (generate EAGLE-compatible files and import them).
  Use it to plan and research; never to claim an electronics capability that has not been tried.
  TRIGGER: "schematic", "circuit", "pcb", "board layout", "footprint", "electronics workspace",
  "eagle", "gerber", "component library", "put the board in the box", "pcb outline", "3d pcb", "design
  the circuit", "wire up", "netlist", "bom".
---

# Fusion electronics (research first; not yet verified)

The owner's goal for this blueprint is 3D parts **and** electronics, then the two fitted together (a PCB designed in
Fusion, its 3D model dropped into an enclosure designed from the same chat). Fusion has an Electronics workspace
(the former EAGLE) for that. **This repo has not yet driven it from the bridge, and the API side is not
established.** Everything in this skill is a plan, tagged, to be turned into facts in
[docs/fusion_reference.md](../../../docs/fusion_reference.md) as it is tried. Part of the journey
([design-with-fusion](../design-with-fusion/SKILL.md), Phase 5).

## What is known, with tags

| Statement | Tag |
|---|---|
| Fusion has an Electronics workspace with schematic and 2D PCB editors and a "3D PCB" document that places the board as a 3D body in a design | [community] Autodesk marketing and forum posts; not opened here yet |
| The electronics documents are separate document types from a Design (`DesignProductType`); `ping` reports the active product type | [verified] for the Design type only |
| The Python API for the Electronics workspace is thin compared with the Design API | [community] forum consensus as of 2024-2025; must be re-checked on this Fusion version |
| EAGLE's `.sch` / `.brd` XML format and `.scr` script commands are documented and Fusion imports EAGLE files | [community] EAGLE documentation; import into this Fusion not tried |
| A PCB's 3D body can be inserted into a Design and positioned, then the enclosure's standoffs and cutouts derived from it | [unverified]: the integration step this blueprint is aiming for |

## The research steps (in order; record each result in the reference before the next)

1. **Probe the running Fusion** for electronics in the API, from the chat, no guessing:
   ```powershell
   python scripts\fusion.py exec "import adsk; result = sorted(n for n in dir(adsk) if not n.startswith('_'))"
   python scripts\fusion.py exec "result = sorted(n for n in dir(adsk.fusion) if 'lectr' in n or 'PCB' in n or 'Pcb' in n or 'Schem' in n)"
   python scripts\fusion.py exec "result = [p.productType for p in items(app.activeDocument.products)]"
   ```
   Then, with the owner creating a new Electronics Design / Schematic / PCB document by hand in Fusion
   (*File > New Electronics Design*; confirm the menu text when you see it), run `ping` and the products probe
   again: what product types appear, what `app.activeProduct` is, what `dir()` offers. Write every finding into
   the reference with `[verified]` and the Fusion version.
2. **Decide the route** from what step 1 shows:
   * API objects exist for schematics/boards -> wrap the smallest useful thing (create a document, place a part,
     read the board outline) in `bridge_helpers.py`, verify, record.
   * The API is only "open a document" -> the **file route**: generate EAGLE-compatible `.sch`/`.brd` XML or an
     `.scr` script from Python, import it into Fusion, read the result back. Needs the EAGLE file format facts
     with sources in the reference first.
   * Neither works -> say so plainly in the roadmap; the owner can still design the PCB by hand in Fusion and
     this chat does the enclosure around its exported 3D body (STEP import, `fusion-files`).
3. **The integration target** (the point of all this): board outline + mounting holes + tall-component
   keep-outs -> an enclosure script (`templates/parametric_box` is the start) whose standoff pitch, pilot holes
   and connector cutouts are parameters fed from the board. First with numbers typed in from a datasheet or a
   measured board; later read from the board document if the API allows.
4. **Each new capability** becomes: a fact row in the reference, a helper or recipe in a skill, an example in
   `examples/`, a roadmap line moved from "not yet" to "verified here" with the evidence.

## Rules while in this territory

* **Say "not verified yet" before every electronics claim** until the reference says otherwise (CLAUDE.md rules 3
  and 8). Do not promise the owner a schematic from chat until step 1 is done.
* Facts come with sources: Autodesk's API reference (https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-A92A4B10-3781-4925-94C6-47DA85A4F65A),
  the EAGLE documentation, or a probe in the running Fusion, each tagged.
* Keep the 3D flow working: the electronics research never edits the Design helpers without their tests.
* Land results in [docs/blueprint_roadmap.md](../../../docs/blueprint_roadmap.md),
  [docs/lessons_log.md](../../../docs/lessons_log.md) and this skill after each session, even when the result is
  "this does not work on 2706.1.14".

## Hand-off checklist

- [ ] the owner was told plainly what is and is not verified about electronics
- [ ] every probe result is in the reference with a tag and the Fusion version
- [ ] the chosen route (API / file / by-hand-plus-enclosure) is written in the roadmap with the reason
- [ ] no electronics capability was claimed that was not seen working
