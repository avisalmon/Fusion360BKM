"""Put a phone photo into a library part, safe to publish.

    python scripts\\library_photo.py <photo> library\\<owner>\\<part>\\photos\\<name>.jpg

Phone photos carry EXIF metadata (the phone's make and model, often the GPS position) and store
their rotation as a tag. This applies the rotation first, then writes the pixels alone (no
metadata), at most 2000 px on the long side. Stripping without rotating first left the photos
sideways (2026-11-19).
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps


def clean(src, dst, longest=2000):
    im = ImageOps.exif_transpose(Image.open(src))
    im.thumbnail((longest, longest))
    out = Image.frombytes(im.mode, im.size, im.tobytes())  # pixels only: no EXIF, no GPS
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, "JPEG", quality=88, optimize=True)
    return out.size


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    size = clean(argv[0], argv[1])
    print(f"wrote {argv[1]} {size[0]} x {size[1]}, no metadata")
    return 0


if __name__ == "__main__":
    sys.exit(main())
