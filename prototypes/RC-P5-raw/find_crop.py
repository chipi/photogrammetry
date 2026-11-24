"""Find where the JPEG frame sits inside the NEF frame, by phase correlation of luma patches.

ETH3D's JPEGs are 6048x4032; libraw reports the NEF as 6080x4044. The GT intrinsics assume the
JPEG frame, so the RAW-developed images are cropped to it. This prints the (left, top) offset.
"""

import sys
from pathlib import Path

import numpy as np
import pycolmap
import rawpy

SCENE = Path.home() / ".cache/recce/datasets/eth3d/pipes"


def luma(a):
    a = a.astype(np.float64)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def phase_corr(a, b):
    fa, fb = np.fft.fft2(a), np.fft.fft2(b)
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-9
    c = np.real(np.fft.ifft2(r))
    y, x = np.unravel_index(np.argmax(c), c.shape)
    h, w = c.shape
    return (y if y < h // 2 else y - h), (x if x < w // 2 else x - w), float(c.max())


def main(stem):
    raw = rawpy.imread(str(SCENE / f"raw/images/dslr_images/{stem}.NEF"))
    full = raw.postprocess(use_camera_wb=True, output_bps=8, no_auto_bright=True)
    jpg = pycolmap.Bitmap.read(
        str(SCENE / f"images/dslr_images/{stem}.JPG"), as_rgb=True
    ).to_array()
    print("raw developed", full.shape, "jpeg", jpg.shape)
    # window on the JPEG frame, compare against the same window of the RAW at candidate offsets
    for cy, cx in [(1500, 2500), (800, 4000)]:
        size = 512
        j = luma(jpg[cy : cy + size, cx : cx + size])
        j = (j - j.mean()) / j.std()
        # RAW search window is larger by 64 px each side
        pad = 64
        r = luma(full[cy - pad : cy + size + pad, cx - pad : cx + size + pad])
        best = None
        for dy in range(0, 2 * pad + 1):
            for dx in range(0, 2 * pad + 1):
                if abs(dy - pad) > 24 or abs(dx - pad) > 24:
                    continue
                p = r[dy : dy + size, dx : dx + size]
                s = float(np.mean(j * (p - p.mean()) / p.std()))
                if best is None or s > best[0]:
                    best = (s, dy - pad, dx - pad)
        print(
            f"window ({cy},{cx}): corr {best[0]:.3f}  raw_offset_y={best[1]} raw_offset_x={best[2]}"
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "DSC_0634")
