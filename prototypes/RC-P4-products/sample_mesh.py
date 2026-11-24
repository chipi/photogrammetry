"""RC-P4: sample a mesh into a point cloud for the ETH3D evaluation tool.

The tool reads only the PLY's vertices and ignores faces, so a mesh is scored through points
sampled on its surface, uniformly by area. Run it in the gsplat environment (trimesh).

Usage: sample_mesh.py <mesh.ply> <output points.ply> [--spacing-m 0.005]
"""

import argparse
from pathlib import Path

import numpy as np
import trimesh


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--spacing-m", type=float, default=0.005)
    ap.add_argument("--max-points", type=int, default=5_000_000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    mesh = trimesh.load(args.mesh, process=False)
    # An untrimmed Delaunay mesh reaches far past the scene (RC-P2's courtyard mesh covers
    # 2,486 m2, which is 99 M points at 5 mm). The evaluator holds the scans (about 5 GB) plus
    # about 0.2 GB per million points, so the cap keeps it near 6 GB.
    n = min(int(mesh.area / args.spacing_m**2), args.max_points)
    pts, _ = trimesh.sample.sample_surface(mesh, n, seed=args.seed)
    trimesh.PointCloud(np.asarray(pts)).export(args.out)
    print(
        f"area_m2={mesh.area:.2f} faces={len(mesh.faces)} sampled={n} "
        f"spacing_m={(mesh.area / n) ** 0.5:.4f} -> {args.out}"
    )


if __name__ == "__main__":
    main()
