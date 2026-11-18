r"""11_blinker_555, step 3: Fusion's own checks, then the files for the factory.

    python scripts\fusion.py run examples\11_blinker_555\factory.py 300

Run after circuit.py and board.py, on the design they built. It runs Fusion's electrical rule
check (ERC) and board check, saves the design to the Fusion cloud (CAM output needs a saved
design), records both checks in fusion/fusion_checks.json, exports the design as EAGLE XML to
fusion/ and writes Gerber and drill files to factory/.
Then, without Fusion:

    python scripts\pcb_check.py examples\11_blinker_555\fusion\board.brd
    python scripts\factory_check.py examples\11_blinker_555\factory
"""

import datetime
import json
import os

import adsk.core

HERE = repo_path("examples", "11_blinker_555")

erc = sch_erc()
board_errors = brd_errors()
# Fusion's own findings are kept with the export, so the summary page can show them without Fusion
os.makedirs(os.path.join(HERE, "fusion"), exist_ok=True)
fusion_checks = {
    "date": datetime.date.today().isoformat(),
    "fusion": adsk.core.Application.get().version,
    "erc": erc,
    "board_errors": board_errors,
}
checks_path = os.path.join(HERE, "fusion", "fusion_checks.json")
with open(checks_path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(fusion_checks, indent=2) + "\n")
saved_as = ecad_save("11_blinker_555", description="built by examples/11_blinker_555")
exported = ecad_export(os.path.join(HERE, "fusion"), "board")
factory_files = cam_export(os.path.join(HERE, "factory"))
result = {
    "erc_clean": not [e for e in erc if e["state"] != "approved"],
    "erc": erc,
    "board_clean": not [e for e in board_errors if e["state"] != "approved"],
    "board_errors": board_errors,
    "saved_as": saved_as,
    "exported": exported,
    "factory_files": factory_files,
}
