"""RC-P4: crop a cloud or mesh to the laser scans' bounding box, so the score covers the scene only.

Usage:
  crop.py bbox <scan_alignment.mlp> <out.json> [--pad-m 0.5]
  crop.py apply <bbox.json> <input.ply> <output.ply>
`bbox` loads every scan listed in the MeshLab project, applies its transform and writes the padded
axis-aligned box. `apply` keeps the points, or the faces whose three vertices all lie inside it,
and prints how much was removed. Run it in the gsplat environment (trimesh).
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import trimesh


def read_mlp(path: Path) -> list[tuple[Path, np.ndarray]]:
    text = path.read_text()
    out = []
    for m in re.finditer(r'filename="([^"]+)".*?<MLMatrix44>(.*?)</MLMatrix44>', text, re.S):
        mat = np.array(m.group(2).split(), dtype=float).reshape(4, 4)
        out.append((path.parent / m.group(1), mat))
    return out


def inside(pts: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    return np.all((pts >= lo) & (pts <= hi), axis=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bbox")
    b.add_argument("mlp", type=Path)
    b.add_argument("out", type=Path)
    b.add_argument("--pad-m", type=float, default=0.5)
    a = sub.add_parser("apply")
    a.add_argument("bbox", type=Path)
    a.add_argument("src", type=Path)
    a.add_argument("dst", type=Path)
    args = ap.parse_args()

    if args.cmd == "bbox":
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for ply, mat in read_mlp(args.mlp):
            v = np.asarray(trimesh.load(ply, process=False).vertices)
            v = v @ mat[:3, :3].T + mat[:3, 3]
            lo, hi = np.minimum(lo, v.min(0)), np.maximum(hi, v.max(0))
        lo, hi = lo - args.pad_m, hi + args.pad_m
        args.out.write_text(json.dumps({"lo": lo.tolist(), "hi": hi.tolist(), "pad_m": args.pad_m}))
        print("BBOX", lo, hi)
        return

    box = json.loads(args.bbox.read_text())
    lo, hi = np.array(box["lo"]), np.array(box["hi"])
    geom = trimesh.load(args.src, process=False)
    if isinstance(geom, trimesh.Trimesh):
        keep = inside(np.asarray(geom.vertices), lo, hi)[geom.faces].all(axis=1)
        before = len(geom.faces)
        area_before = geom.area
        geom.update_faces(keep)
        geom.remove_unreferenced_vertices()
        print(f"faces {before} -> {len(geom.faces)}, area_m2 {area_before:.1f} -> {geom.area:.1f}")
    else:
        pts = np.asarray(geom.vertices)
        keep = inside(pts, lo, hi)
        print(f"points {len(pts)} -> {int(keep.sum())}")
        geom = trimesh.PointCloud(pts[keep])
    geom.export(args.dst)


if __name__ == "__main__":
    main()
