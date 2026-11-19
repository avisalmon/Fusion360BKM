# The part library: real parts from a real store

Each person who uses this blueprint keeps their own library here, in a folder named after them
(`library/<your_name>/`). `library/avi_salmon/` is Avi's: an example, and a reference for friends who
borrow parts from him. Start yours by telling the chat "add a part to my library" and showing it a part.
Updates pulled from the blueprint never touch your folder.

One folder per part:

```text
library/<owner>/<part_id>/
  part.json        what the part is, where it lives in the store (location, quantity), its pins with
                   warnings, the footprint spec, every dimension with where it came from, its status
  photos/          the owner's photos, turned upright and stripped of metadata (scripts/library_photo.py)
  <part_id>.lbr    the Fusion/EAGLE library for this one part, generated: never edit it by hand
  fusion/          screenshots of the symbol and footprint as Fusion drew them
```

```powershell
python scripts\library_photo.py <phone photo> library\<owner>\<part>\photos\top.jpg
python scripts\library_build.py library\<owner>          # every part's .lbr from its part.json
```

In a circuit script: `ecad("USE '<repo>/library/<owner>/<part>/<part>.lbr'")`, then
`ADD <DEVICESET>@<part_id>`. One part per `.lbr`: Fusion 2706 fails on a local library with two or more
(gotcha 47).

Round parts (a buzzer) give `body_diameter` instead of `body`; `symbol_half_width` (grid steps, default 5)
narrows the symbol of a part with few pins.

Not done yet: the 3D models, and the browsable page of the whole library.
