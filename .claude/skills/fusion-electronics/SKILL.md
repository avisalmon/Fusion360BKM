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

Researched 2026-11-16 from Autodesk's documentation and release notes; **none of it has been tried from this bridge yet**.
Tags: `[doc]` Autodesk or vendor documentation, `[forum]` community or third-party, `[uncertain]` inferred,
`[verified]` seen working here (with the Fusion version).

| Statement | Tag |
|---|---|
| Fusion has an official electronics Python API, `adsk.electron`, since build 2703.1.11 (May 2026): cast `app.activeProduct` to `Schematic`, `Board`, `Library` or `EcadDesign`; the model mirrors EAGLE's ULP (sheets/instances, elements/signals, deviceSets/devices). https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ElectronicsIntro.htm | [doc] |
| That API is a **read-only preview**: no creating or editing layout content. Its only output is `exportManager` -> EAGLE 9.6.2 `.sch` / `.brd` / `.lbr` XML. No CAM/Gerber, no import. https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ElectronicsExport.htm | [doc] |
| Every electronics editor has an EAGLE-style command line: `RUN file.ulp` runs a ULP, `SCRIPT file.scr` runs a command script. https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECD-EXECUTE-ULP-REF.htm | [doc] |
| Those commands can be sent from Python with `app.executeTextCommand` (`Electron.run ...`): fire-and-forget, no result back; interactive commands (bare `ADD`, `MOVE`, `EDIT`) hang; paths with spaces break; a new board is on an inch grid until `GRID MM`; move parts by name (`MOVE 'R1' (x y)`). Not documented by Autodesk. https://wiki.adom.inc/adom/fusion-bridge/files/README.md | [forum] |
| September 2026 added a `NETROUTE` command "for schematic autorouting, scripting, automation and AI-driven workflows"; its syntax is not documented | [doc] release notes, syntax [uncertain] |
| EAGLE `.sch` + `.brd` uploaded **together** become one linked electronics design; one at a time loses the link. Safe format target: EAGLE 9.6.x XML | [doc] / format [uncertain] |
| Libraries live in the cloud (the Fusion hub), are switched on in the Library Manager and placed from the Place panel; a component = symbol + footprint + 3D package + attributes. Local EAGLE `.lbr` files import and convert to managed libraries. https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECAD-CUSTOM-LIB-CPT.htm | [doc] |
| Parts from vendors: SnapMagic (plugin or `.lbr`) and Ultra Librarian (`.lbr`); **no native LCSC/EasyEDA import** | [doc] / [forum] |
| "Update design from library" (or the `UPDATE` command) pulls library changes into a design; an unmanaged library with the same name as a managed one blocks it | [doc] / [forum] |
| Factory files: CAM Processor -> Gerber RS274X (X2 optional), Excellon drill, Assembly BOM and pick-and-place CSV; design rules load from a `.dru` in the DRC dialog. JLCPCB's guide (2026-09) says to rename the CPL headers and add an `LCSC` part-number attribute per part. https://jlcpcb.com/help/article/how-to-generate-bom-and-cpl-from-fusion360 | [doc] |
| JLCPCB `.dru` / CAM jobs for EAGLE are community files, some with values that differ from JLCPCB's site: check against JLCPCB's current capabilities before use | [forum] |
| No documented way to run a CAM job from a script; ULPs (`bom.ulp`, `mount.ulp`) can write BOM and placement files | [uncertain] / [doc] |
| 2D board and 3D PCB are linked documents; changes are **pulled** (an "out of date" mark you accept). Board outline can be derived from a sketch ("associative PCB"); Autodesk advises outline first, then enclosure. https://help.autodesk.com/cloudhelp/ENU/Fusion-ECAD/files/ECD-SYNC-2D-AND-3D-TSK.htm | [doc] |
| The 3D PCB's board and components are ordinary bodies in a Design, so the Design API can measure the outline and holes for an enclosure | [uncertain] |
| EAGLE itself ended 2026-06-07; Fusion's Python moved to 3.14 in January 2026 | [doc] |

**The routes this suggests** (to be confirmed by the probes below): *read* with `adsk.electron`; *write* with
EAGLE command scripts sent through `executeTextCommand`, or with generated EAGLE 9.6 XML imported as a pair;
*factory files* from the CAM Processor with a JLCPCB rule set we checked ourselves; *the case* with the normal
Design API around the 3D PCB.

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
