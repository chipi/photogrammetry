"""RC-P5: register one ETH3D scene from each develop route with COLMAP (SIFT, exhaustive matching,
incremental mapping) and measure, per route, registration, exposure and white-balance spread, and
a seam-contrast proxy. Registration and scoring are copied from RC-P1 (no cross-prototype import).
"""

import argparse
import itertools
import json
import platform
import shutil
import time
from pathlib import Path

import numpy as np
import pycolmap
from common import (
    luminance,
    read_rgb,
    route_dir,
    route_images,
    scene_dir,
    srgb_lut,
    to_linear,
)


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
    supported = [img for img in largest.images.values() if img.has_pose and img.num_points3D > 0]
    result = {
        "components": len(recons),
        "registered": len(supported),
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
        "scene_extent_m": round(extent, 3),
    }
    return result


def exposure_wb_spread(paths):
    """Per-image median luminance (EV) and median R/G, B/G in linear light; spread across the set.

    The values are decoded from the route's 8-bit sRGB JPEGs, so they describe the developed
    set, not the sensor. Scene content differs between views, so the white-balance numbers carry
    that variation too; it is the same for every route.
    """
    ev, rg, bg = [], [], []
    for p in paths:
        lin = to_linear(read_rgb(p)[::8, ::8])
        y = luminance(lin)
        ev.append(float(np.log2(np.median(y) + 1e-6)))
        ok = lin[..., 1] > 0.01
        rg.append(float(np.median(lin[..., 0][ok] / lin[..., 1][ok])))
        bg.append(float(np.median(lin[..., 2][ok] / lin[..., 1][ok])))
    ev, rg, bg = np.array(ev), np.array(rg), np.array(bg)
    return {
        "median_luminance_ev_std": round(float(ev.std()), 4),
        "median_luminance_ev_range": round(float(ev.max() - ev.min()), 4),
        "median_luminance_mean_linear": round(float(np.mean(2**ev)), 4),
        "rg_mean": round(float(rg.mean()), 4),
        "rg_std": round(float(rg.std()), 4),
        "bg_mean": round(float(bg.mean()), 4),
        "bg_std": round(float(bg.std()), 4),
        "rg_bg_std_relative_pct": round(
            float(100 * np.hypot(rg.std() / rg.mean(), bg.std() / bg.mean())), 3
        ),
    }


def track_observations(recon, image_dir, min_track, patch):
    """Per long-enough track: the linear luminance and the R/G, B/G of each observation."""
    obs = {}  # image_id -> list of (track_index, x, y)
    n = 0
    for point in recon.points3D.values():
        elems = point.track.elements
        if len(elems) < min_track:
            continue
        for e in elems:
            xy = recon.images[e.image_id].points2D[e.point2D_idx].xy
            obs.setdefault(e.image_id, []).append((n, xy[0], xy[1]))
        n += 1
    values = [([], [], []) for _ in range(n)]
    lut = srgb_lut()
    for image_id, items in obs.items():
        img = read_rgb(image_dir / recon.images[image_id].name)
        h, w = img.shape[:2]
        xs = np.clip(np.floor([i[1] for i in items]).astype(int), patch, w - patch - 1)
        ys = np.clip(np.floor([i[2] for i in items]).astype(int), patch, h - patch - 1)
        acc = np.zeros((len(items), 3), dtype=np.float64)
        for dy in range(-patch, patch + 1):
            for dx in range(-patch, patch + 1):
                acc += lut[img[ys + dy, xs + dx]]
        acc /= (2 * patch + 1) ** 2
        y = luminance(acc)
        for j, item in enumerate(items):
            lum, rg, bg = values[item[0]]
            lum.append(y[j])
            rg.append(acc[j, 0] / max(acc[j, 1], 1e-6))
            bg.append(acc[j, 2] / max(acc[j, 1], 1e-6))
    return values


def seam_proxy(recon, image_dir, min_track=3, patch=2):
    """Colour and brightness disagreement between the images that see the same 3D point.

    Per 3D point with a track of >= min_track observations: the standard deviation across the
    track of log2 linear luminance (EV) and of log2 R/G and B/G, each observation a (2*patch+1)^2
    box mean at the keypoint. Reported: median and 90th percentile over points. This is a proxy
    for texture seams: a textured mesh does not exist yet (RC-P4).
    """
    sd_ev, sd_rg, sd_bg, rel = [], [], [], []
    for lum, rg, bg in track_observations(recon, image_dir, min_track, patch):
        y = np.array(lum)
        if len(y) < min_track or y.mean() < 0.02:  # near-black points are noise in log space
            continue
        sd_ev.append(np.log2(y + 1e-6).std(ddof=1))
        rel.append(y.std(ddof=1) / y.mean())
        sd_rg.append(np.log2(np.array(rg) + 1e-6).std(ddof=1))
        sd_bg.append(np.log2(np.array(bg) + 1e-6).std(ddof=1))

    def med(a):
        return round(float(np.median(a)), 4)

    return {
        "points_used": len(sd_ev),
        "min_track": min_track,
        "luminance_sd_ev_median": med(sd_ev),
        "luminance_sd_ev_p90": round(float(np.percentile(sd_ev, 90)), 4),
        "luminance_rel_sd_median": med(rel),
        "chroma_rg_sd_ev_median": med(sd_rg),
        "chroma_bg_sd_ev_median": med(sd_bg),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene")
    parser.add_argument("routes", nargs="+")
    parser.add_argument("--stats-only", action="store_true", help="skip registration, reuse models")
    args = parser.parse_args()
    gt = pycolmap.Reconstruction(str(scene_dir(args.scene) / "dslr_calibration_jpg"))

    for route in args.routes:
        base = route_dir(args.scene, route)
        image_dir = base / "images"
        paths = route_images(args.scene, route)
        names = sorted(str(p.relative_to(image_dir)) for p in paths)
        sparse = base / "sparse"
        entry = {
            "scene": args.scene,
            "route": route,
            "images": len(names),
            "machine": {"host": platform.node(), "arch": platform.machine()},
            "pycolmap": pycolmap.__version__,
        }
        if not args.stats_only:
            if sparse.exists():
                shutil.rmtree(sparse)
            sparse.mkdir()
            db = base / "database.db"
            db.unlink(missing_ok=True)
            t0 = time.perf_counter()
            pycolmap.extract_features(db, image_dir, image_names=names)
            t1 = time.perf_counter()
            pycolmap.match_exhaustive(db)
            t2 = time.perf_counter()
            pycolmap.incremental_mapping(db, image_dir, sparse)
            t3 = time.perf_counter()
            entry["timings_s_not_comparable"] = {
                "features": round(t1 - t0, 1),
                "matching": round(t2 - t1, 1),
                "mapping": round(t3 - t2, 1),
            }
        models = sorted(p for p in sparse.iterdir() if p.is_dir())
        recons = {i: pycolmap.Reconstruction(str(m)) for i, m in enumerate(models)}
        entry["registration"] = score(recons, gt, len(names))
        entry["exposure_wb_spread"] = exposure_wb_spread(paths)
        if recons:
            largest = max(recons.values(), key=lambda r: r.num_reg_images())
            entry["seam_proxy"] = seam_proxy(largest, image_dir)
        (base / "results.json").write_text(json.dumps(entry, indent=2))
        print(json.dumps(entry, indent=2), flush=True)


if __name__ == "__main__":
    main()
