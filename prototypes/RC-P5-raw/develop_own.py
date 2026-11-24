"""Route "own": the minimal pipeline. rawpy develop with one white balance and one exposure gain
for the whole set (set-wide, not per image), cropped to the JPEG frame, written as JPEG.

White balance: the median of the cameras' as-shot multipliers across the set.
Exposure: one linear gain that puts the set's median-of-medians luminance at TARGET_MEDIAN_LINEAR.
Everything else is libraw's default (AHD demosaic, camera matrix to sRGB, clip highlights).
"""

import argparse
import json

import numpy as np
import rawpy
from common import (
    CROP_H,
    CROP_LEFT,
    CROP_TOP,
    CROP_W,
    TARGET_MEDIAN_LINEAR,
    luminance,
    raw_files,
    route_dir,
    write_jpeg,
)


def develop_linear(path, wb, half=False):
    with rawpy.imread(str(path)) as raw:
        return raw.postprocess(
            user_wb=list(wb),
            gamma=(1, 1),
            no_auto_bright=True,
            output_bps=16,
            half_size=half,
        )


def srgb_oetf(lin):
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene")
    args = parser.parse_args()
    files = raw_files(args.scene)
    out = route_dir(args.scene, "own") / "images/dslr_images"
    out.mkdir(parents=True, exist_ok=True)

    wbs = []
    for f in files:
        with rawpy.imread(str(f)) as raw:
            w = np.array(raw.camera_whitebalance, dtype=float)
            wbs.append(w)
    wb = np.median(np.array(wbs), axis=0)
    wb[3] = wb[1]

    medians = []
    for f in files:
        lin = develop_linear(f, wb, half=True) / 65535.0
        t, left = CROP_TOP // 2, CROP_LEFT // 2
        view = lin[t : t + CROP_H // 2, left : left + CROP_W // 2]
        medians.append(float(np.median(luminance(view))))
    gain = TARGET_MEDIAN_LINEAR / float(np.median(medians))

    for f in files:
        lin = develop_linear(f, wb) / 65535.0
        lin = lin[CROP_TOP : CROP_TOP + CROP_H, CROP_LEFT : CROP_LEFT + CROP_W]
        rgb = np.round(srgb_oetf(lin * gain) * 255).astype(np.uint8)
        write_jpeg(out / f"{f.stem}.JPG", rgb)
        print(f.name, rgb.shape, flush=True)

    meta = {
        "white_balance_multipliers_rgbg": [round(float(x), 5) for x in wb],
        "gain": round(gain, 5),
        "gain_ev": round(float(np.log2(gain)), 4),
        "target_median_linear": TARGET_MEDIAN_LINEAR,
        "crop": [CROP_LEFT, CROP_TOP, CROP_W, CROP_H],
    }
    (route_dir(args.scene, "own") / "develop.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
