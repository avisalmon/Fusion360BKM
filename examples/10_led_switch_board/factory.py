r"""10_led_switch_board, step 3: Fusion's own checks, then the files for the factory.

    python scripts\fusion.py run examples\10_led_switch_board\factory.py 300

Run after circuit.py and board.py, on the design they built. It runs Fusion's electrical rule
check (ERC) and board check, saves the design to the Fusion cloud (CAM output needs a saved
design), exports it as EAGLE XML to fusion/ and writes Gerber and drill files to factory/.
Then, without Fusion:

    python scripts\pcb_check.py examples\10_led_switch_board\fusion\board.brd
    python scripts\factory_check.py examples\10_led_switch_board\factory
"""

import os

HERE = repo_path("examples", "10_led_switch_board")

erc = sch_erc()
board_errors = brd_errors()
saved_as = ecad_save("10_led_switch_board", description="built by examples/10_led_switch_board")
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
