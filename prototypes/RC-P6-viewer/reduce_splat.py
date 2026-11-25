"""RC-P6: reduce a trained 3DGS PLY to about one million gaussians and put it in the mesh's frame.

Usage:
  reduce_splat.py <full.ply> <sparse_dir> <out.ply> [--count 1000000]

Rule: keep the `count` gaussians with the largest sigmoid(opacity) x exp(sum of log scales), the
opacity-weighted volume. Large, opaque gaussians carry the visible surface; small or transparent
ones are the first to go.

Frame: gsplat trains in a normalised world (it recentres, rescales and rotates the scene from the
camera poses and sparse points) while the textured mesh stays in the COLMAP model frame. The
script recomputes gsplat's transform from `sparse_dir` (the workspace the trainer read) and writes
the splat in the model frame: positions by the inverse similarity, orientations rotated, log
scales shifted by the inverse scale. Higher spherical-harmonic bands are dropped (they would need
rotating too), so the output has colour only: 14 float properties, 56 bytes per gaussian.
"""

import argparse
from pathlib import Path

import numpy as np

from p6_io import gsplat_world_transform, read_ply, write_ply


def quat_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Hamilton product of quaternions stored as (w, x, y, z); b may be (N, 4) or (4,)."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        axis=-1,
    )


def rot_to_quat(r: np.ndarray) -> np.ndarray:
    """Rotation matrix to (w, x, y, z), Shepperd's method."""
    t = np.trace(r)
    if t > 0:
        s = 2 * np.sqrt(t + 1)
        q = [s / 4, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s]
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2 * np.sqrt(1 + r[i, i] - r[j, j] - r[k, k])
        q = [0.0] * 4
        q[0] = (r[k, j] - r[j, k]) / s
        q[1 + i] = s / 4
        q[1 + j] = (r[j, i] + r[i, j]) / s
        q[1 + k] = (r[k, i] + r[i, k]) / s
    q = np.array(q)
    return q / np.linalg.norm(q)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("full", type=Path)
    ap.add_argument("sparse_dir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--count", type=int, default=1_000_000)
    args = ap.parse_args()

    src, _ = read_ply(args.full)
    n = len(src)
    opacity = 1.0 / (1.0 + np.exp(-np.asarray(src["opacity"], np.float64)))
    log_vol = sum(np.asarray(src[f"scale_{i}"], np.float64) for i in range(3))
    score = opacity * np.exp(log_vol)
    keep = np.sort(np.argpartition(score, n - args.count)[n - args.count :])
    print(f"{n:,} gaussians, keeping {len(keep):,}; score cut {score[keep].min():.3e}")
    kept_volume = score[keep].sum() / score.sum()
    print(f"kept share of total opacity-weighted volume: {kept_volume:.3f}")

    m = gsplat_world_transform(args.sparse_dir)
    s = np.cbrt(np.linalg.det(m[:3, :3]))
    r = m[:3, :3] / s
    inv_r = r.T
    q_inv = rot_to_quat(inv_r)
    print(f"gsplat frame: scale {s:.6f}, model->gsplat; inverse applied to the splat")

    sel = np.asarray(src[keep])
    xyz = np.stack([sel["x"], sel["y"], sel["z"]], axis=1).astype(np.float64)
    xyz = (xyz - m[:3, 3]) @ inv_r.T / s
    rot = np.stack([sel[f"rot_{i}"] for i in range(4)], axis=1).astype(np.float64)
    rot /= np.linalg.norm(rot, axis=1, keepdims=True)
    rot = quat_mul(q_inv, rot)
    rot /= np.linalg.norm(rot, axis=1, keepdims=True)

    names = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity"]
    names += [f"scale_{i}" for i in range(3)] + [f"rot_{i}" for i in range(4)]
    out = np.empty(len(keep), dtype=[(k, "<f4") for k in names])
    for i, k in enumerate("xyz"):
        out[k] = xyz[:, i]
    for k in ("f_dc_0", "f_dc_1", "f_dc_2", "opacity"):
        out[k] = sel[k]
    for i in range(3):
        out[f"scale_{i}"] = sel[f"scale_{i}"] - np.log(s)
    for i in range(4):
        out[f"rot_{i}"] = rot[:, i]
    write_ply(args.out, out)
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    print("bounds (model frame) 1st/99th percentile:")
    print(np.percentile(xyz, [1, 99], axis=0).round(2))


if __name__ == "__main__":
    main()
