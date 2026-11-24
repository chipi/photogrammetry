"""Per-image camera white balance, black/white levels and EXIF-style facts from the NEFs."""

import sys
from pathlib import Path

import numpy as np
import rawpy

RAW_DIR = (
    Path.home()
    / ".cache/recce/datasets/eth3d"
    / (sys.argv[1] if len(sys.argv) > 1 else "pipes")
    / "raw/images/dslr_images"
)

wbs = []
for f in sorted(RAW_DIR.glob("*.NEF")):
    r = rawpy.imread(str(f))
    wb = np.array(r.camera_whitebalance[:3])
    wbs.append(wb / wb[1])
    print(
        f.name,
        np.round(wb / wb[1], 4),
        r.black_level_per_channel,
        r.white_level,
        r.sizes.raw_width,
        r.sizes.raw_height,
    )
wbs = np.array(wbs)
print("median", np.median(wbs, 0), "std", wbs.std(0))
