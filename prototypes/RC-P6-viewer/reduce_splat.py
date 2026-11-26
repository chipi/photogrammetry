"""RC-P6: reduce a trained 3DGS PLY to about one million gaussians and put it in the mesh's frame.

Usage:
  reduce_splat.py <full.ply> <sparse_dir> <out.ply> [--count 1000000] [--rule contribution|volume]
                  [--min-views 2]

Rules:
- `contribution` (default): keep the `count` gaussians that cover the most of the training images,
  summed over the views: sigmoid(opacity) x the projected area of the two largest axes
  (pi s1 s2 f^2 / z^2) in each view whose image holds the centre. Occlusion is not modelled.
- `volume` (the first rule, 2026-11-24): the largest sigmoid(opacity) x exp(sum of log scales). It
  kept large blobs and needles: the kept set's median largest axis was 1.5 times the trained set's.

Crop: before ranking, a gaussian must sit inside at least `min-views` training images (in front of
the camera, inside the frame). From outside the capture area the trained splat is unconstrained,
and its floaters and sky blobs were what the default orbit showed.

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

from p6_io import gsplat_world_transform, read_cameras_bin, read_images_bin, read_ply, write_ply


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


def view_coverage(xyz: np.ndarray, scales: np.ndarray, opacity: np.ndarray, sparse: Path):
    """Per gaussian (model frame): the number of training images holding its centre, and its
    summed opacity x projected area over them, in pixels."""
    cams = read_cameras_bin(sparse / "cameras.bin")
    views = np.zeros(len(xyz), np.int32)
    contrib = np.zeros(len(xyz))
    s2 = np.sort(scales, axis=1)
    area_m2 = np.pi * s2[:, 2] * s2[:, 1]
    for im in read_images_bin(sparse / "images.bin"):
        cam = cams[im["camera_id"]]
        f, cx, cy = cam["params"][0], cam["params"][-2], cam["params"][-1]
        if cam["model"] != 0:  # PINHOLE: fx, fy, cx, cy
            f, cx, cy = cam["params"][0], cam["params"][2], cam["params"][3]
        w2c = np.linalg.inv(im["c2w"])
        pc = xyz @ w2c[:3, :3].T + w2c[:3, 3]
        z = pc[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u, v = f * pc[:, 0] / z + cx, f * pc[:, 1] / z + cy
            inside = (z > 0.05) & (u >= 0) & (u < cam["width"]) & (v >= 0) & (v < cam["height"])
            px = np.minimum(area_m2 * f * f / (z * z), cam["width"] * cam["height"])
        views += inside
        contrib += np.where(inside, opacity * px, 0.0)
    return views, contrib


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("full", type=Path)
    ap.add_argument("sparse_dir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--count", type=int, default=1_000_000)
    ap.add_argument("--rule", choices=["contribution", "volume"], default="contribution")
    ap.add_argument("--min-views", type=int, default=2)
    args = ap.parse_args()

    src, _ = read_ply(args.full)
    n = len(src)
    m = gsplat_world_transform(args.sparse_dir)
    s = np.cbrt(np.linalg.det(m[:3, :3]))
    r = m[:3, :3] / s
    inv_r = r.T
    q_inv = rot_to_quat(inv_r)
    print(f"gsplat frame: scale {s:.6f}, model->gsplat; inverse applied to the splat")

    opacity = 1.0 / (1.0 + np.exp(-np.asarray(src["opacity"], np.float64)))
    log_s = np.stack([np.asarray(src[f"scale_{i}"], np.float64) for i in range(3)], axis=1)
    all_xyz = np.stack([src["x"], src["y"], src["z"]], axis=1).astype(np.float64)
    all_xyz = (all_xyz - m[:3, 3]) @ inv_r.T / s
    views, contrib = view_coverage(all_xyz, np.exp(log_s) / s, opacity, args.sparse_dir)
    seen = views >= args.min_views
    print(f"{n:,} gaussians; {seen.sum():,} inside at least {args.min_views} training images")
    if args.rule == "contribution":
        score = np.where(seen, contrib, -1.0)
    else:
        score = np.where(seen, opacity * np.exp(log_s.sum(1)), -1.0)
    count = min(args.count, int(seen.sum()))
    keep = np.sort(np.argpartition(score, n - count)[n - count :])
    print(f"rule {args.rule}: keeping {len(keep):,}; score cut {score[keep].min():.3e}")
    print(f"kept share of the cropped set's score: {score[keep].sum() / score[seen].sum():.3f}")

    sel = np.asarray(src[keep])
    xyz = all_xyz[keep]
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
