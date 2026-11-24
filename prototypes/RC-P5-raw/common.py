"""Shared paths and image helpers for the RC-P5 scripts."""

import os
from pathlib import Path

import numpy as np
import pycolmap

DATA = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
RUNS = Path(os.environ.get("RECCE_RUNS_DIR", DATA / "runs")) / "p5"
ROUTES = ("jpeg", "own", "chemigram")

# Where the JPEG frame (6048x4032, the frame the ETH3D ground truth describes) sits inside the NEF
# frame libraw reports (6080x4044), measured by find_crop.py on the camera-WB develop of DSC_0634.
CROP_LEFT, CROP_TOP, CROP_W, CROP_H = 15, 6, 6048, 4032

# The luminance every route is developed to, as a median linear value over the set; mid-grey.
TARGET_MEDIAN_LINEAR = 0.18


def scene_dir(scene):
    return DATA / "datasets/eth3d" / scene


def raw_files(scene):
    return sorted((scene_dir(scene) / "raw/images/dslr_images").glob("*.NEF"))


def route_dir(scene, route):
    return RUNS / scene / route


def route_images(scene, route):
    return sorted((route_dir(scene, route) / "images/dslr_images").glob("*.JPG"))


def read_rgb(path):
    return pycolmap.Bitmap.read(str(path), as_rgb=True).to_array()


def write_jpeg(path, rgb, quality=95):
    bmp = pycolmap.Bitmap.from_array(np.ascontiguousarray(rgb))
    bmp.set_jpeg_quality(quality)
    bmp.write(str(path))


_SRGB_LUT = None


def srgb_lut():
    global _SRGB_LUT
    if _SRGB_LUT is None:
        v = np.arange(256) / 255.0
        _SRGB_LUT = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4).astype(
            np.float32
        )
    return _SRGB_LUT


def to_linear(rgb8):
    return srgb_lut()[rgb8]


def luminance(lin):
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
