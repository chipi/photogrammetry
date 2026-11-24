"""RC-P4: first numbers for the complaint measurements that need no texture (CPU, gsplat env).

Usage: measure.py <run folder> <scene folder> <scan_alignment.mlp> <output json>
Measures: per-image sharpness and exposure / white-balance spread of the source photos; depth-map
consistency (geometric against photometric valid pixels); noise, density and per-region
completeness of the cropped fused cloud against the laser scans (a KD-tree on a subsample of the
scans, not ETH3D's occlusion-aware metric).
"""

import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from crop import read_mlp
from PIL import Image
from scipy.spatial import cKDTree

SCAN_SAMPLE = 4_000_000
CELL_M = 1.0
NEAR_M = 0.05


def laplacian_var(gray: np.ndarray) -> float:
    lap = (
        -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    )
    return float(lap.var())


def photo_stats(images: list[Path]) -> dict:
    sharp, rgb = [], []
    for p in images:
        with Image.open(p) as im:
            im = im.convert("RGB")
            im = im.resize((2000, round(im.height * 2000 / im.width)), Image.LANCZOS)
            a = np.asarray(im, dtype=np.float64) / 255.0
        sharp.append(laplacian_var(a.mean(axis=2) * 255.0))
        lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
        rgb.append(lin.reshape(-1, 3).mean(0))
    rgb = np.array(rgb)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    s = np.array(sharp)
    return {
        "images": len(images),
        "sharpness_laplacian_var": {
            "median": float(np.median(s)),
            "min": float(s.min()),
            "p10": float(np.percentile(s, 10)),
        },
        "exposure_std_log2_luminance": float(np.std(np.log2(lum))),
        "white_balance_std_log2_r_over_g": float(np.std(np.log2(rgb[:, 0] / rgb[:, 1]))),
        "white_balance_std_log2_b_over_g": float(np.std(np.log2(rgb[:, 2] / rgb[:, 1]))),
        "grey_world_mean_r_over_g": float(np.mean(rgb[:, 0] / rgb[:, 1])),
        "grey_world_mean_b_over_g": float(np.mean(rgb[:, 2] / rgb[:, 1])),
    }


def valid_pixels(path: Path) -> int:
    """Count positive depths; the byte order of the pixels does not matter for a count."""
    with path.open("rb") as f:
        amp = 0
        while amp < 3:
            amp += f.read(1) == b"&"
        return int((np.fromfile(f, dtype=np.float32) > 0).sum())


def depth_consistency(ws: Path) -> dict:
    ratios = []
    for geo in sorted((ws / "stereo" / "depth_maps").rglob("*.geometric.bin")):
        pho = geo.with_name(geo.name.replace(".geometric.bin", ".photometric.bin"))
        if pho.exists():
            ratios.append(valid_pixels(geo) / max(valid_pixels(pho), 1))
    r = np.array(ratios)
    return {
        "views": len(r),
        "geometric_over_photometric_valid_pixels": {
            "median": float(np.median(r)),
            "min": float(r.min()),
        },
    }


def scan_points(mlp: Path) -> np.ndarray:
    rng = np.random.default_rng(0)
    out = []
    for ply, mat in read_mlp(mlp):
        v = np.asarray(trimesh.load(ply, process=False).vertices)
        v = v[rng.choice(len(v), min(SCAN_SAMPLE // 2, len(v)), replace=False)]
        out.append(v @ mat[:3, :3].T + mat[:3, 3])
    return np.vstack(out)


def cloud_stats(cloud: np.ndarray, scan: np.ndarray) -> dict:
    d_cloud, _ = cKDTree(scan).query(cloud, k=1)
    d_scan, _ = cKDTree(cloud).query(scan, k=1)
    near = d_cloud <= 0.10
    mad = float(np.median(np.abs(d_cloud[near] - np.median(d_cloud[near]))))
    cells = np.floor(scan[:, :2] / CELL_M).astype(np.int64)
    _, inv = np.unique(cells, axis=0, return_inverse=True)
    hit = np.bincount(inv, weights=(d_scan <= NEAR_M).astype(float))
    frac = hit / np.bincount(inv)
    # Cells with fewer than 100 sampled scan points are edges of the scene, left out.
    keep = np.bincount(inv) >= 100
    f = frac[keep]
    return {
        "points": len(cloud),
        "within_10cm_of_scan_fraction": float(near.mean()),
        "nn_distance_to_scan_m_median_within_10cm": float(np.median(d_cloud[near])),
        "nn_distance_to_scan_m_mad_within_10cm": mad,
        "scan_points_with_cloud_within_5cm": float((d_scan <= NEAR_M).mean()),
        "cells_1m": int(keep.sum()),
        "cells_completeness_median": float(np.median(f)),
        "cells_below_half_of_median": int((f < 0.5 * np.median(f)).sum()),
        "cells_below_10_percent": int((f < 0.1).sum()),
    }


def main() -> None:
    run, scene, mlp, out = (Path(a) for a in sys.argv[1:5])
    res: dict = {"run": run.name}
    photos = sorted((scene / "images").rglob("*.JPG"))
    res["photos"] = photo_stats(photos)
    res["depth_maps"] = depth_consistency(run / "dense")
    cloud = np.asarray(trimesh.load(run / "fused_crop.ply", process=False).vertices)
    res["cloud"] = cloud_stats(cloud, scan_points(mlp))
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
