"""Reference route "darktable_default": darktable-cli (external process) with its stock settings and
no XMP, so every image gets the same default scene-referred edit and its own as-shot white balance.
Not one of the brief's three routes: it separates "darktable" from "Chemigram's baseline XMP"
when the Chemigram route's colour is judged.
"""

import subprocess
import sys

from common import (
    CROP_H,
    CROP_LEFT,
    CROP_TOP,
    CROP_W,
    RUNS,
    raw_files,
    read_rgb,
    route_dir,
    write_jpeg,
)

scene = sys.argv[1]
out = route_dir(scene, "darktable_default") / "images/dslr_images"
out.mkdir(parents=True, exist_ok=True)
tmp = RUNS / scene / "darktable_default_png"
tmp.mkdir(parents=True, exist_ok=True)
for f in raw_files(scene):
    png = tmp / f"{f.stem}.png"
    png.unlink(missing_ok=True)
    subprocess.run(  # noqa: S603 - external process by design (GPL boundary)
        [
            "/usr/bin/darktable-cli",
            str(f),
            str(png),
            "--core",
            "--configdir",
            str(RUNS / "dtconf2"),
        ],
        check=True,
        capture_output=True,
    )
    rgb = read_rgb(png)[CROP_TOP : CROP_TOP + CROP_H, CROP_LEFT : CROP_LEFT + CROP_W]
    if rgb.shape != (CROP_H, CROP_W, 3):
        raise SystemExit(f"{png}: crop gave {rgb.shape}")
    write_jpeg(out / f"{f.stem}.JPG", rgb)
    print(f.stem, rgb.shape, flush=True)
