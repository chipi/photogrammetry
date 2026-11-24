"""RC-P1: register one ETH3D scene with COLMAP (incremental) and GLOMAP (global) from the
same verified matches, and measure both against ETH3D's ground-truth poses."""

import argparse
import itertools
import json
import platform
import shutil
import time
from pathlib import Path

import numpy as np
import pycolmap


def timed(record, name, fn):
    start = time.perf_counter()
    out = fn()
    record[name] = round(time.perf_counter() - start, 2)
    return out


def world_from_cam(image):
    cam_from_world = (
        image.cam_from_world() if callable(image.cam_from_world) else image.cam_from_world
    )
    world_from_cam = cam_from_world.inverse()
    return world_from_cam.rotation.matrix(), np.asarray(world_from_cam.translation)


def umeyama(src, dst):
    """Similarity (s, R, t) minimising |dst - (s R src + t)|^2; points as rows."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    u, d, vt = np.linalg.svd(cov)
    sign = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[2, 2] = -1
    rot = u @ sign @ vt
    scale = np.trace(np.diag(d) @ sign) / xs.var(0).sum()
    return scale, rot, mu_d - scale * rot @ mu_s


def rotation_angle_deg(rot):
    return float(np.degrees(np.arccos(np.clip((np.trace(rot) - 1) / 2, -1.0, 1.0))))


def score(recons, gt, n_images):
    if not recons:
        return {"components": 0, "registered": 0, "registration_rate": 0.0}
    largest = max(recons.values(), key=lambda r: r.num_reg_images())
    errors = np.array([p.error for p in largest.points3D.values()])
    # A posed image that holds no 3D point is not tied to the model: GLOMAP posed one on kicker
    # about 47 m from the truth, and including it in the alignment distorted every other error.
    supported = [img for img in largest.images.values() if img.has_pose and img.num_points3D > 0]
    result = {
        "components": len(recons),
        "registered": len(supported),
        "posed_without_points": largest.num_reg_images() - len(supported),
        "registration_rate": round(len(supported) / n_images, 4),
        "points3D": largest.num_points3D(),
        "reprojection_error_mean_px": round(float(errors.mean()), 4),
        "reprojection_error_p95_px": round(float(np.percentile(errors, 95)), 4),
        "mean_track_length": round(largest.compute_mean_track_length(), 3),
    }
    gt_by_name = {img.name: img for img in gt.images.values()}
    pairs = []
    for img in supported:
        ref = gt_by_name.get(img.name) or gt_by_name.get(Path(img.name).name)
        if ref is not None:
            pairs.append((world_from_cam(img), world_from_cam(ref)))
    if len(pairs) < 3:
        result["pose_error"] = "fewer than 3 images matched to ground truth"
        return result
    # Alignment-free: rotation between every camera pair, estimated against ground truth. A wrong
    # camera layout skews the centre-based Sim(3) below; this number does not depend on it.
    rel = [
        rotation_angle_deg((g1[0].T @ g2[0]).T @ (e1[0].T @ e2[0]))
        for (e1, g1), (e2, g2) in itertools.combinations(pairs, 2)
    ]
    est_c = np.array([p[0][1] for p in pairs])
    gt_c = np.array([p[1][1] for p in pairs])
    s, rot, t = umeyama(est_c, gt_c)
    aligned = (s * (rot @ est_c.T)).T + t
    extent = float(np.linalg.norm(gt_c.max(0) - gt_c.min(0)))
    pos_err = np.linalg.norm(aligned - gt_c, axis=1)
    rot_err = np.array([rotation_angle_deg(g[0].T @ rot @ e[0]) for e, g in pairs])
    result["pose_error"] = {
        "images_compared": len(pairs),
        "relative_rotation_deg_median": round(float(np.median(rel)), 4),
        "relative_rotation_deg_p95": round(float(np.percentile(rel, 95)), 4),
        "position_m_median": round(float(np.median(pos_err)), 4),
        "rotation_deg_median": round(float(np.median(rot_err)), 4),
        "rotation_deg_max": round(float(rot_err.max()), 4),
        "position_frac_of_extent_median": round(float(np.median(pos_err) / extent), 6),
        "position_frac_of_extent_max": round(float(pos_err.max() / extent), 6),
        "scene_extent_m": round(extent, 3),
        "sim3_scale": round(float(s), 6),
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "scene", type=Path, help="ETH3D scene folder (images/ and dslr_calibration_jpg/)"
    )
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--score-only", action="store_true", help="re-score the models already in OUT"
    )
    args = parser.parse_args()

    image_dir = args.scene / "images"
    gt = pycolmap.Reconstruction(str(args.scene / "dslr_calibration_jpg"))
    names = sorted(
        str(p.relative_to(image_dir))
        for p in image_dir.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if args.score_only:
        path = args.out / "results.json"
        results = json.loads(path.read_text())
        for name, entry in results["strategies"].items():
            models = sorted((args.out / name).iterdir())
            recons = {i: pycolmap.Reconstruction(str(m)) for i, m in enumerate(models)}
            results["strategies"][name] = {
                "timings": entry["timings"],
                **score(recons, gt, len(names)),
            }
        path.write_text(json.dumps(results, indent=2))
        print(json.dumps(results, indent=2))
        return
    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    db = args.out / "database.db"

    timings = {}
    timed(
        timings, "features_s", lambda: pycolmap.extract_features(db, image_dir, image_names=names)
    )
    timed(timings, "matching_s", lambda: pycolmap.match_exhaustive(db))

    results = {
        "scene": args.scene.name,
        "machine": {
            "host": platform.node(),
            "system": platform.system(),
            "arch": platform.machine(),
        },
        "pycolmap": pycolmap.__version__,
        "cuda": bool(getattr(pycolmap, "has_cuda", False)),
        "images": len(names),
        "shared_timings": timings,
        "strategies": {},
    }
    strategies = [
        ("colmap_incremental", pycolmap.incremental_mapping),
        ("glomap_global", pycolmap.global_mapping),
    ]
    for name, mapper in strategies:
        out = args.out / name
        out.mkdir()
        t = {}
        recons = timed(t, "mapping_s", lambda m=mapper, o=out: m(db, image_dir, o))
        results["strategies"][name] = {"timings": t, **score(recons, gt, len(names))}

    (args.out / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
