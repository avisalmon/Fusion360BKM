# Production: what a board is checked against, and how its factory files are made

* `fab/jlcpcb_2layer.json`: JLCPCB's limits for a standard 2-layer FR-4 board with 1 oz copper, with the page they
  came from and the date read. `scripts/pcb_check.py` and `scripts/factory_check.py` use it by default (`--fab` for
  another fab: copy the file, fill in that fab's numbers with their source).
* `cam/two_layer.cam`: the CAM job `cam_export()` hands to Fusion. Made from Fusion's own `example_2_layer.cam`
  with the ODB++ and drawing outputs removed and plain file names: Gerber RS-274X for copper, profile, solder mask,
  paste and silkscreen (top and bottom), and one Excellon drill file.

How it all fits, every check and what is not checked yet:
[docs/procedures/board_checks_and_factory.md](../docs/procedures/board_checks_and_factory.md).
