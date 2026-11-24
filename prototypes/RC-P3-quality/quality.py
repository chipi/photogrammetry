"""RC-P3: turn a reconstruction (RC-P1 output) and its database into quality.json v0.

Regions live in a frame that survives re-running the mapper: every model is aligned (Sim(3) on the
camera centres, as RC-P1 does) to the ETH3D ground-truth cameras, and a fixed voxel grid in that
frame defines the regions. The grid comes from the full run once (`regions.json`) and is reused for
every later run of the same scene.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pycolmap

SCHEMA = "recce.quality/v0"
MIN_REGION_POINTS = 30  # a cell with fewer reference points is not a region
SEE_MIN_OBS = 5  # an image "sees" a region when it observes at least this many of its points
THIN_DEG = 8.0  # median triangulation angle below this: thin_angle
FEW_PHOTOS_FRAC = 0.5  # more than this fraction of points seen by <= 2 images: few_photos
AZ_BINS = 36


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


def load_models(model_root: Path):
    return [pycolmap.Reconstruction(str(p)) for p in sorted(model_root.iterdir()) if p.is_dir()]


def gt_cameras(gt):
    """name -> (rotation, centre) of the ground-truth cameras, keyed by full and base name."""
    out = {}
    for img in gt.images.values():
        out[img.name] = out[Path(img.name).name] = world_from_cam(img)
    return out


def align_to_gt(recon, gt_cams):
    """Sim(3) from the model frame to the GT frame, from cameras that hold points."""
    src, dst = [], []
    for img in recon.images.values():
        if img.has_pose and img.num_points3D > 0:
            ref = gt_cams.get(img.name) or gt_cams.get(Path(img.name).name)
            if ref is not None:
                src.append(world_from_cam(img)[1])
                dst.append(ref[1])
    if len(src) < 3:
        return None
    src, dst = np.array(src), np.array(dst)
    s, rot, t = umeyama(src, dst)
    resid = np.linalg.norm((s * (rot @ src.T)).T + t - dst, axis=1)
    return {"scale": s, "rot": rot, "t": t, "residual_median_m": float(np.median(resid))}


def up_axis(gt_cams):
    """World up in the GT frame: COLMAP cameras have +y pointing down."""
    up = -np.mean([r[:, 1] for r, _ in gt_cams.values()], axis=0)
    return up / np.linalg.norm(up)


def extract_points(recon, sim):
    """Per-point arrays in the reference frame: xyz, error, triangulation angle, track."""
    centres = {i: world_from_cam(img)[1] for i, img in recon.images.items() if img.has_pose}
    xyz, err, ang, tracks = [], [], [], []
    for p in recon.points3D.values():
        ids = [e.image_id for e in p.track.elements]
        rays = np.array([centres[i] - p.xyz for i in ids if i in centres])
        if len(rays) < 2:
            continue
        rays /= np.linalg.norm(rays, axis=1, keepdims=True)
        # COLMAP's definition: the largest angle between any two viewing rays of the track.
        widest = np.degrees(np.arccos(np.clip((rays @ rays.T).min(), -1.0, 1.0)))
        xyz.append(p.xyz)
        err.append(p.error)
        ang.append(widest)
        tracks.append(ids)
    xyz = np.array(xyz).reshape(-1, 3)
    if sim is not None:
        xyz = (sim["scale"] * (sim["rot"] @ xyz.T)).T + sim["t"]
    return xyz, np.array(err), np.array(ang), tracks


def build_regions(xyz, up, cell_m=None, divisor=10):
    """Voxel grid over the full run's points; keeps cells with >= MIN_REGION_POINTS points."""
    diag = float(np.linalg.norm(xyz.max(0) - xyz.min(0)))
    cell = cell_m or round(diag / divisor, 2)
    cells = {}
    for k, ijk in enumerate(map(tuple, np.floor(xyz / cell).astype(int))):
        cells.setdefault(ijk, []).append(k)
    regions = []
    for ijk in sorted(cells):
        if len(cells[ijk]) >= MIN_REGION_POINTS:
            regions.append(
                {
                    "id": f"R{len(regions) + 1:03d}",
                    "ijk": [int(v) for v in ijk],
                    "reference_points": len(cells[ijk]),
                }
            )
    return {
        "frame": "eth3d_gt",
        "cell_m": cell,
        "min_points": MIN_REGION_POINTS,
        "up": [round(float(v), 6) for v in up],
        "regions": regions,
    }


def azimuth(bins):
    """Covered fraction of the ring and the longest empty arc (start bin, length)."""
    covered = int((bins > 0).sum())
    gap = (0, 0)
    for s in range(AZ_BINS):
        if bins[s]:
            continue
        n = 0
        while n < AZ_BINS and not bins[(s + n) % AZ_BINS]:
            n += 1
        if n > gap[1]:
            gap = (s, n)
    return covered / AZ_BINS, gap


def region_metrics(region, idx, xyz, ang, tracks, centres, up, cell_m):
    n = len(idx)
    entry = {
        "id": region["id"],
        "cell_centre": [round((v + 0.5) * cell_m, 3) for v in region["ijk"]],
        "points": n,
        "reference_points": region["reference_points"],
    }
    if n == 0:
        entry |= {
            "centre": None,
            "images_seeing": [],
            "images_any": 0,
            "median_triangulation_angle_deg": None,
            "few_photo_fraction": None,
            "azimuth_coverage": 0.0,
            "azimuth_gap": None,
            "coverage": 0.0,
            "flags": ["no_points"],
        }
        return entry
    centre = xyz[idx].mean(0)
    obs = {}
    for k in idx:
        for i in tracks[k]:
            obs[i] = obs.get(i, 0) + 1
    ref_u = np.cross(up, [1.0, 0.0, 0.0] if abs(up[0]) < 0.9 else [0.0, 1.0, 0.0])
    ref_u /= np.linalg.norm(ref_u)
    ref_v = np.cross(up, ref_u)
    bins = np.zeros(AZ_BINS)
    for i, w in obs.items():
        if i in centres:
            d = centres[i] - centre
            a = np.arctan2(d @ ref_v, d @ ref_u)
            bins[int((a + np.pi) / (2 * np.pi) * AZ_BINS) % AZ_BINS] += w
    az, (g0, glen) = azimuth(bins)
    few = float(np.mean([len(tracks[k]) <= 2 for k in idx]))
    med_ang = float(np.median(ang[idx]))
    flags = []
    if med_ang < THIN_DEG:
        flags.append("thin_angle")
    if few > FEW_PHOTOS_FRAC:
        flags.append("few_photos")
    # coverage = azimuth_coverage * min(1, points / reference_points); see README.
    coverage = az * min(1.0, n / region["reference_points"])
    entry |= {
        "centre": [round(float(v), 3) for v in centre],
        "images_seeing": sorted(i for i, w in obs.items() if w >= SEE_MIN_OBS),
        "images_any": len(obs),
        "median_triangulation_angle_deg": round(med_ang, 2),
        "few_photo_fraction": round(few, 3),
        "azimuth_coverage": round(az, 3),
        "azimuth_gap": {"start_deg": g0 * 360 // AZ_BINS, "length_deg": glen * 360 // AZ_BINS}
        if glen
        else None,
        "coverage": round(coverage, 4),
        "flags": flags,
    }
    return entry


def pair_inliers(db_path: Path):
    """image name -> total verified (two-view geometry) inlier matches with other images."""
    db = pycolmap.Database.open(str(db_path))
    names = {im.image_id: im.name for im in db.read_all_images()}
    pairs, counts = db.read_two_view_geometry_num_inliers()
    total = dict.fromkeys(names.values(), 0)
    for pid, n in zip(pairs, counts, strict=True):
        for i in divmod(int(pid), 0x7FFFFFFF):
            total[names[i]] += int(n)
    db.close()
    return total


def image_verdicts(models, names, inliers):
    main = max(models, key=lambda r: r.num_reg_images()) if models else None
    other = {}
    for ci, r in enumerate(models):
        if r is not main:
            for img in r.images.values():
                other[img.name] = ci
    in_main = {img.name: img for img in main.images.values() if img.has_pose} if main else {}
    out = []
    for name in names:
        img = in_main.get(name)
        if img is not None and img.num_points3D > 0:
            errs = [main.points3D[p.point3D_id].error for p in img.points2D if p.has_point3D()]
            out.append(
                {
                    "name": name,
                    "verdict": "registered",
                    "reason": "pose and triangulated points in the main model",
                    "points": img.num_points3D,
                    "mean_reproj_px": round(float(np.mean(errs)), 3),
                }
            )
        elif img is not None:
            out.append(
                {
                    "name": name,
                    "verdict": "posed_without_points",
                    "reason": "pose set, but no 3D point observes it: not tied to the model",
                    "points": 0,
                    "mean_reproj_px": None,
                }
            )
        else:
            if name in other:
                why = (
                    f"posed only in secondary component {other[name]}, not joined to the main model"
                )
            elif inliers.get(name, 0) == 0:
                why = "no verified matches with any other image"
            else:
                why = (
                    f"{inliers[name]} verified matches with other images, but the mapper did "
                    "not register it; the mapper does not record why"
                )
            out.append(
                {
                    "name": name,
                    "verdict": "not_registered",
                    "reason": why,
                    "points": 0,
                    "mean_reproj_px": None,
                }
            )
    return out


def compute_quality(models, names, db_path, gt_cams, regions, label):
    """quality.json v0 as a dict. `names` are the images this run was given."""
    inliers = pair_inliers(db_path)
    verdicts = image_verdicts(models, names, inliers)
    registered = sum(v["verdict"] == "registered" for v in verdicts)
    doc = {
        "schema": SCHEMA,
        "run": label,
        "scale": {
            "state": "arbitrary",
            "reason": "photos only; no scale reference, so distances are model units",
        },
        "registration": {
            "images": len(names),
            "registered": registered,
            "rate": round(registered / len(names), 4) if names else 0.0,
            "components": len(models),
            "component_sizes": sorted((r.num_reg_images() for r in models), reverse=True),
        },
        "images": verdicts,
    }
    if not models:
        doc["reprojection"] = None
        doc["frame"] = None
        doc["regions"] = [
            region_metrics(r, [], None, None, None, {}, None, regions["cell_m"])
            for r in regions["regions"]
        ]
        return doc
    main = max(models, key=lambda r: r.num_reg_images())
    sim = align_to_gt(main, gt_cams) if gt_cams else None
    if gt_cams and sim is None:
        raise RuntimeError("fewer than 3 cameras matched to the reference; cannot align")
    xyz, err, ang, tracks = extract_points(main, sim)
    up = np.array(regions["up"])
    centres = {i: world_from_cam(img)[1] for i, img in main.images.items() if img.has_pose}
    if sim is not None:
        centres = {i: (sim["scale"] * (sim["rot"] @ c)) + sim["t"] for i, c in centres.items()}
    keys = np.floor(xyz / regions["cell_m"]).astype(int)
    by_cell = {}
    for k, ijk in enumerate(map(tuple, keys)):
        by_cell.setdefault(ijk, []).append(k)
    id_to_name = {i: img.name for i, img in main.images.items()}
    out_regions = []
    for r in regions["regions"]:
        idx = by_cell.get(tuple(r["ijk"]), [])
        m = region_metrics(r, idx, xyz, ang, tracks, centres, up, regions["cell_m"])
        m["images_seeing"] = [id_to_name[i] for i in m["images_seeing"]]
        out_regions.append(m)
    doc["reprojection"] = {
        "points": len(err),
        "mean_px": round(float(err.mean()), 4),
        "p95_px": round(float(np.percentile(err, 95)), 4),
        "p99_px": round(float(np.percentile(err, 99)), 4),
        "max_px": round(float(err.max()), 4),
        "mean_track_length": round(float(np.mean([len(t) for t in tracks])), 3),
    }
    doc["frame"] = {
        "id": regions["frame"],
        "aligned_by": "sim3_on_reference_camera_centres" if sim else "none",
        "residual_median_m": round(sim["residual_median_m"], 4) if sim else None,
        "cell_m": regions["cell_m"],
        "up": regions["up"],
    }
    doc["regions"] = out_regions
    return doc


def scene_names(scene: Path):
    image_dir = scene / "images"
    return sorted(
        str(p.relative_to(image_dir))
        for p in image_dir.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def make_regions(models, gt_cams, cell_m=None, divisor=10):
    main = max(models, key=lambda r: r.num_reg_images())
    sim = align_to_gt(main, gt_cams) if gt_cams else None
    xyz, _, _, _ = extract_points(main, sim)
    return build_regions(
        xyz, up_axis(gt_cams) if gt_cams else np.array([0.0, 0.0, 1.0]), cell_m, divisor
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scene", type=Path, help="ETH3D scene folder")
    ap.add_argument("models", type=Path, help="folder holding model folders 0, 1, ...")
    ap.add_argument("database", type=Path)
    ap.add_argument("out", type=Path, help="run folder; writes quality.json (and regions.json)")
    ap.add_argument("--regions", type=Path, help="regions.json to reuse; built here if absent")
    ap.add_argument("--cell-m", type=float, help="grid cell size when building regions")
    ap.add_argument("--no-gt", action="store_true", help="skip the ground-truth alignment")
    args = ap.parse_args()

    gt_cams = (
        None
        if args.no_gt
        else gt_cameras(pycolmap.Reconstruction(str(args.scene / "dslr_calibration_jpg")))
    )
    models = load_models(args.models)
    args.out.mkdir(parents=True, exist_ok=True)
    reg_path = args.regions or args.out / "regions.json"
    if reg_path.exists():
        regions = json.loads(reg_path.read_text())
    else:
        regions = make_regions(models, gt_cams, args.cell_m)
        reg_path.write_text(json.dumps(regions, indent=2))
    doc = compute_quality(
        models, scene_names(args.scene), args.database, gt_cams, regions, args.out.name
    )
    (args.out / "quality.json").write_text(json.dumps(doc, indent=2))
    print(f"wrote {args.out / 'quality.json'}: {len(doc['regions'])} regions")


if __name__ == "__main__":
    main()
