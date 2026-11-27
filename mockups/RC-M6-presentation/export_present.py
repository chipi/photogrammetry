"""RC-M6 export: the courtyard's 38 photo poses, a tour through them, and each photo undistorted
to the pinhole camera the RC-P6 mesh and splat were built with, so a stop can dissolve into its
photo. The mesh and splat are not copied: data/p6 links to RC-P6's data folder.

Run under RC-P1's environment (numpy, pycolmap):
  cd prototypes/RC-P1-registration
  uv run python ../../mockups/RC-M6-presentation/export_present.py \
    ~/.cache/recce/datasets/eth3d/courtyard ~/.cache/recce/runs/p6/data \
    ../../mockups/RC-M6-presentation/data
"""

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pycolmap

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P6-viewer"))
import p6_io

PHOTO_W = 1200
THUMB_W = 240
STOPS = 8


def eth3d_cameras(calib: Path) -> dict[str, list[float]]:
    """Image name -> ETH3D THIN_PRISM_FISHEYE parameters at full resolution."""
    cams = {}
    for line in (calib / "cameras.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            f = line.split()
            cams[f[0]] = [float(x) for x in f[4:]]
    text = (calib / "images.txt").read_text().splitlines()
    out, lines = {}, [s for s in text if not s.startswith("#")]
    for line in lines[::2]:
        f = line.split()
        if len(f) >= 10:
            out[Path(f[9]).name] = cams[f[8]]
    return out


def fisheye_distort(u: np.ndarray, v: np.ndarray, p: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """COLMAP's THIN_PRISM_FISHEYE on normalised coordinates (u, v) = (x/z, y/z)."""
    k1, k2, p1, p2, k3, k4, sx1, sy1 = p[4:12]
    r = np.hypot(u, v)
    theta = np.arctan(r)
    s = np.where(r > 1e-9, theta / np.maximum(r, 1e-9), 1.0)
    uu, vv = u * s, v * s
    t2 = uu * uu + vv * vv
    radial = k1 * t2 + k2 * t2**2 + k3 * t2**3 + k4 * t2**4
    du = uu * radial + 2 * p1 * uu * vv + p2 * (t2 + 2 * uu * uu) + sx1 * t2
    dv = vv * radial + 2 * p2 * uu * vv + p1 * (t2 + 2 * vv * vv) + sy1 * t2
    return uu + du, vv + dv


def undistort(img: Path, eth: list[float], pin: dict, out_w: int) -> np.ndarray:
    """The photo resampled into RC-P6's pinhole camera at out_w pixels wide (bilinear)."""
    src = pycolmap.Bitmap.read(str(img), as_rgb=True).to_array().astype(np.float32)
    fx, fy, cx, cy = pin["params"]
    s = out_w / pin["width"]
    out_h = round(pin["height"] * s)
    ys, xs = np.mgrid[0:out_h, 0:out_w].astype(np.float64)
    u = ((xs + 0.5) / s - cx) / fx
    v = ((ys + 0.5) / s - cy) / fy
    du, dv = fisheye_distort(u, v, eth)
    sx = eth[0] * du + eth[2] - 0.5
    sy = eth[1] * dv + eth[3] - 0.5
    h, w = src.shape[:2]
    x0 = np.clip(np.floor(sx).astype(int), 0, w - 2)
    y0 = np.clip(np.floor(sy).astype(int), 0, h - 2)
    ax = np.clip(sx - x0, 0, 1)[..., None]
    ay = np.clip(sy - y0, 0, 1)[..., None]
    top = src[y0, x0] * (1 - ax) + src[y0, x0 + 1] * ax
    bot = src[y0 + 1, x0] * (1 - ax) + src[y0 + 1, x0 + 1] * ax
    res = top * (1 - ay) + bot * ay
    outside = (sx < 0) | (sy < 0) | (sx > w - 1) | (sy > h - 1)
    res[outside] = 0
    return np.clip(res, 0, 255).astype(np.uint8)


def tour(centres: np.ndarray) -> list[int]:
    """A short walk through every photo: nearest neighbour from the westmost photo, then 2-opt."""
    n = len(centres)
    d = np.linalg.norm(centres[:, None] - centres[None], axis=2)
    order = [int(np.argmin(centres[:, 0]))]
    left = set(range(n)) - set(order)
    while left:
        nxt = min(left, key=lambda j: d[order[-1], j])
        order.append(nxt)
        left.remove(nxt)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a, b, c, e = order[i - 1], order[i], order[j], order[j + 1]
                if d[a, c] + d[b, e] < d[a, b] + d[c, e] - 1e-9:
                    order[i : j + 1] = order[i : j + 1][::-1]
                    improved = True
    return order


def spread(order: list[int], dirs: np.ndarray, k: int) -> list[int]:
    """k stops along the walk that face apart: farthest-point sampling on view direction."""
    picked = [order[0]]
    while len(picked) < k:
        best = max(
            (i for i in order if i not in picked),
            key=lambda i: min(1 - float(dirs[i] @ dirs[j]) for j in picked),
        )
        picked.append(best)
    return sorted(picked, key=order.index)


def main() -> None:
    scene, p6, out = (Path(a).expanduser() for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    link = out / "p6"
    if not link.exists():
        link.symlink_to(p6.resolve())
    pin = p6_io.read_cameras_bin(p6 / "sparse/cameras.bin")
    images = sorted(p6_io.read_images_bin(p6 / "sparse/images.bin"), key=lambda r: r["name"])
    eth = eth3d_cameras(scene / "dslr_calibration_jpg")
    sim3 = json.loads((p6 / "sim3.json").read_text())
    (out / "photos").mkdir(exist_ok=True)
    (out / "thumbs").mkdir(exist_ok=True)
    cams = []
    for im in images:
        name = Path(im["name"]).name
        cam = pin[im["camera_id"]]
        _, fy, cx, cy = cam["params"]
        c2w = im["c2w"]
        arr = undistort(scene / "images" / im["name"], eth[name], cam, PHOTO_W)
        bm = pycolmap.Bitmap.from_array(arr)
        bm.write(str(out / "photos" / f"{Path(name).stem}.jpg"))
        bm.rescale(THUMB_W, round(THUMB_W * arr.shape[0] / arr.shape[1]))
        bm.write(str(out / "thumbs" / f"{Path(name).stem}.jpg"))
        cams.append(
            {
                "name": Path(name).stem,
                "centre": c2w[:3, 3].round(4).tolist(),
                "rotation": c2w[:3, :3].round(6).tolist(),
                "vfov_deg": round(float(np.degrees(2 * np.arctan(cam["height"] / 2 / fy))), 3),
                "aspect": round(cam["width"] / cam["height"], 5),
                "principal_offset": [
                    round(cx / cam["width"] - 0.5, 5),
                    round(cy / cam["height"] - 0.5, 5),
                ],
            }
        )
        print(name, flush=True)
    centres = np.array([c["centre"] for c in cams])
    dirs = np.array([np.array(c["rotation"])[:, 2] for c in cams])
    order = tour(centres)
    stops = spread(order, dirs, STOPS)
    scale = sim3["sim3_scale_metres_per_model_unit"]
    walk = float(sum(np.linalg.norm(centres[a] - centres[b]) for a, b in itertools.pairwise(order)))
    sizes = {
        "mesh_obj": (p6 / "mesh/textured.obj").stat().st_size,
        "mesh_atlases": sum(f.stat().st_size for f in (p6 / "mesh").glob("*.png")),
        "splat": (p6 / "splat/courtyard_1m_contrib.ply").stat().st_size,
        "photos": sum(f.stat().st_size for f in (out / "photos").glob("*.jpg")),
    }
    meta = {
        "scene": "courtyard",
        "source": "ETH3D courtyard (CC BY-NC-SA 4.0); RC-P1 poses, RC-P4 mesh, RC-P6 splat",
        "mesh": "p6/mesh/textured.obj",
        "mtl": "p6/mesh/textured.mtl",
        "splat": "p6/splat/courtyard_1m_contrib.ply",
        "mesh_faces": 463017,
        "mesh_atlases": 115,
        "splat_gaussians": 1000000,
        "metres_per_unit": scale,
        "scale_source": "Sim(3) to ETH3D's surveyed cameras",
        "camera_centre_residual_m": sim3["camera_centre_residual_m"],
        "bbox": json.loads((p6 / "bbox.json").read_text()),
        "cameras": cams,
        "tour": order,
        "stops": stops,
        "walk_m": round(walk * scale, 2),
        "bytes": sizes,
        "fps_measured": [
            {
                "device": "X3 iGPU",
                "browser": "Chromium, headless",
                "fps": 59.9,
                "note": "display-limited",
                "by": "RC-P6, 2026-11-26",
            },
            {"device": "M4 Pro", "browser": "Chrome", "fps": 60.0, "by": "Owner, 2026-11-26"},
            {"device": "M4 Pro", "browser": "Safari", "fps": 58.8, "by": "Owner, 2026-11-26"},
            {
                "device": "iPhone 15 Pro",
                "browser": "Firefox for iOS (WebKit)",
                "fps": 50.0,
                "note": "atlases at 1024 px",
                "by": "Owner, 2026-11-26",
            },
        ],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(cams)} photos, tour {meta['walk_m']} m, stops {[cams[i]['name'] for i in stops]}")


if __name__ == "__main__":
    main()
