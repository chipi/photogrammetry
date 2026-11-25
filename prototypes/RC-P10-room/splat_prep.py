"""RC-P10: input for a splat in the same metric frame as the TSDF mesh.

For each video: RC-P8's reference model (every 12th vga_wide frame with its interpolated ARKit
pose), written as COLMAP binaries with 3-D points seeded from the TSDF mesh's vertices and their
fused colour, next to links to the frames. gsplat's trainer reads it as a COLMAP scene; run with
`--no-normalize-world-space` so the splat stays in ARKit's frame, in metres (run_splat.sh).

Needs pycolmap: uv run --project ../RC-P1-registration python splat_prep.py
"""

import os
import shutil
from pathlib import Path

import numpy as np
import pycolmap

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
P8 = RECCE / "runs/p8"
RUNS = RECCE / "runs/p10"
VIDEOS = ("42444515", "42444793", "42444821", "42444858", "42444873")
SEED_POINTS = 200_000
SEED = 0


def read_ply_vertices(path):
    """x, y, z and red, green, blue of an Open3D binary little-endian PLY mesh."""
    raw = Path(path).read_bytes()
    end = raw.index(b"end_header\n") + len(b"end_header\n")
    header = raw[:end].decode().splitlines()
    n = next(int(h.split()[2]) for h in header if h.startswith("element vertex"))
    props, in_vertex = [], False
    for h in header:
        if h.startswith("element"):
            in_vertex = h.startswith("element vertex")
        elif h.startswith("property") and in_vertex:
            _, kind, name = h.split()
            props.append((name, {"double": "<f8", "float": "<f4", "uchar": "u1"}[kind]))
    v = np.frombuffer(raw[end:], dtype=np.dtype(props), count=n)
    return np.stack([v["x"], v["y"], v["z"]], 1), np.stack([v["red"], v["green"], v["blue"]], 1)


def main():
    rng = np.random.default_rng(SEED)
    for vid in VIDEOS:
        rec = pycolmap.Reconstruction(str(P8 / f"a{vid}/reference"))
        xyz, rgb = read_ply_vertices(RUNS / vid / "tsdf.ply")
        pick = rng.choice(len(xyz), min(SEED_POINTS, len(xyz)), replace=False)
        for p, c in zip(xyz[pick], rgb[pick], strict=True):
            rec.add_point3D(p.astype(np.float64), pycolmap.Track(), c.astype(np.uint8))
        out = RUNS / vid / "splat_input"
        if out.exists():
            shutil.rmtree(out)
        (out / "sparse/0").mkdir(parents=True)
        rec.write_binary(str(out / "sparse/0"))
        (out / "images").mkdir()
        for img in rec.images.values():
            src = (P8 / f"a{vid}/none/images" / img.name).resolve()
            if not src.exists():
                src = RECCE / "datasets/arkitscenes/raw/Training" / vid / "vga_wide" / img.name
            shutil.copy(src, out / "images" / img.name)
        print(vid, len(rec.images), "images,", len(pick), "seed points")


if __name__ == "__main__":
    main()
