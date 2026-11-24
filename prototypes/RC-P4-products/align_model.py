"""RC-P4: align an RC-P1 sparse model to ETH3D's ground-truth frame with a Sim(3).

ETH3D's scan_alignment.mlp places the laser scans in the frame of the ground-truth camera poses, so
a reconstruction is scored there. The alignment uses camera centres matched by file name. The same
fit gives the first "untrustworthy scale" numbers: the Sim(3) scale (model units per metre) and the
error of pairwise camera distances, which is what a scale bar between two cameras would show.

Usage: align_model.py <p1 model folder> <ground-truth calibration folder> <output folder>
Writes <output>/aligned/ (COLMAP binary model in the ground-truth frame) and <output>/sim3.json.
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pycolmap


def world_from_cam(image):
    cam_from_world = (
        image.cam_from_world() if callable(image.cam_from_world) else image.cam_from_world
    )
    inv = cam_from_world.inverse()
    return inv.rotation.matrix(), np.asarray(inv.translation)


def umeyama(src, dst):
    """Similarity (s, R, t) minimising |dst - (s R src + t)|^2; points as rows."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    u, d, vt = np.linalg.svd(xd.T @ xs / len(src))
    sign = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[2, 2] = -1
    rot = u @ sign @ vt
    scale = np.trace(np.diag(d) @ sign) / xs.var(0).sum()
    return scale, rot, mu_d - scale * rot @ mu_s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model", type=Path)
    ap.add_argument("gt", type=Path)
    ap.add_argument("out", type=Path)
    args = ap.parse_args()

    rec = pycolmap.Reconstruction(str(args.model))
    gt = pycolmap.Reconstruction(str(args.gt))
    gt_by_name = {Path(i.name).name: i for i in gt.images.values()}
    # A posed image without 3D points is not tied to the model (see RC-P1); keep it out of the fit.
    est, ref, names = [], [], []
    for img in rec.images.values():
        match = gt_by_name.get(Path(img.name).name)
        if img.has_pose and img.num_points3D > 0 and match is not None:
            est.append(world_from_cam(img)[1])
            ref.append(world_from_cam(match)[1])
            names.append(Path(img.name).name)
    est, ref = np.array(est), np.array(ref)
    if len(est) < 3:
        raise SystemExit(f"only {len(est)} images match the ground truth")

    s, rot, t = umeyama(est, ref)
    aligned = (s * (rot @ est.T)).T + t
    resid = np.linalg.norm(aligned - ref, axis=1)

    # What a scale bar between two cameras reads: relative error of every pairwise distance.
    pair_err = []
    for i, j in itertools.combinations(range(len(est)), 2):
        d_gt = np.linalg.norm(ref[i] - ref[j])
        if d_gt > 0:
            pair_err.append(abs(s * np.linalg.norm(est[i] - est[j]) - d_gt) / d_gt)
    pair_err = np.array(pair_err)

    rec.transform(pycolmap.Sim3d(s, pycolmap.Rotation3d(rot), t))
    (args.out / "aligned").mkdir(parents=True, exist_ok=True)
    rec.write(str(args.out / "aligned"))

    result = {
        "images_in_fit": len(est),
        "sim3_scale_metres_per_model_unit": float(s),
        "camera_centre_residual_m": {
            "median": float(np.median(resid)),
            "p95": float(np.percentile(resid, 95)),
            "max": float(resid.max()),
        },
        "pairwise_distance_rel_error": {
            "median": float(np.median(pair_err)),
            "p95": float(np.percentile(pair_err, 95)),
            "max": float(pair_err.max()),
        },
        "rotation": rot.tolist(),
        "translation": t.tolist(),
        "images": names,
    }
    (args.out / "sim3.json").write_text(json.dumps(result, indent=2))
    print("RESULT", json.dumps({k: v for k, v in result.items() if k != "images"}))


if __name__ == "__main__":
    main()
