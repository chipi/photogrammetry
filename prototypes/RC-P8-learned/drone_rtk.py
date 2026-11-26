"""RC-P8 on a drone: COLMAP's incremental mapper with and without RTK position priors.

EuroSDR RPAS Phase 2, DJI Phantom 4 RTK (CC BY 4.0). Each flight folder holds the JPGs and a
`*_Timestamp.MRK` with one RTK fix per photo. Runs in RC-P1's environment (PyPI pycolmap, CPU).

    drone_rtk.py prep FLIGHT OUT           RTK camera centres in a local ENU frame
    drone_rtk.py run OUT [--threads N]     features and matches once, then three variants

Variants: `none` (no priors), `prior` (every photo), `prior_half` (odd photos only, so the even
ones are an independent check of the metric frame). `--camera OPENCV` swaps the lens model
(k1 only by default) for k1, k2 and tangential terms; its variants are named `<variant>_opencv`.
"""

import argparse
import json
import platform
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pycolmap

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "RC-P1-registration"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from run_p1 import timed, umeyama

from recon import components

MAX_IMAGE_SIZE = 2000
MAX_FEATURES = 8192


def read_mrk(path):
    """MRK row: index, GPS seconds, [week], dN, dE, dV (mm, camera from antenna), lat, lon,
    ellipsoidal height, std N/E/V (m), quality (50 = RTK fixed)."""
    rows = {}
    for line in path.read_text().splitlines():
        f = line.replace(",", " ").split()
        if not f:
            continue
        rows[int(f[0])] = {
            "gps_s": float(f[1]),
            "offset_nev_mm": [float(f[3]), float(f[5]), float(f[7])],
            "lat_lon_h": [float(f[9]), float(f[11]), float(f[13])],
            "std_nev_m": [float(f[15]), float(f[16]), float(f[17])],
            "quality": int(f[18]),
        }
    return rows


def cmd_prep(args):
    flight, out = args.flight, args.out
    (mrk,) = flight.glob("*_Timestamp.MRK")
    rows = read_mrk(mrk)
    jpgs = sorted(flight.glob("*.JPG"))
    if len(jpgs) != len(rows):
        raise SystemExit(f"{len(jpgs)} photos against {len(rows)} MRK rows")
    gps = pycolmap.GPSTransform(pycolmap.GPSTransformEllipsoid.WGS84)
    lat_lon_h = np.array([rows[k]["lat_lon_h"] for k in sorted(rows)])
    ref = lat_lon_h.mean(0)
    enu = gps.ellipsoid_to_enu(lat_lon_h, *ref)
    images = {}
    for (k, row), jpg, antenna in zip(sorted(rows.items()), jpgs, enu, strict=True):
        if int(jpg.stem.rsplit("_", 1)[1]) != k:
            raise SystemExit(f"{jpg.name} does not match MRK row {k}")
        # The offset is the camera from the antenna in N, E and V (down), in millimetres: on the
        # P4 RTK the camera hangs about 19 cm under the antenna.
        dn, de, dv = row["offset_nev_mm"]
        centre = antenna + np.array([de, dn, -dv]) / 1000
        sn, se, sv = row["std_nev_m"]
        images[jpg.name] = {
            "centre_enu_m": centre.round(4).tolist(),
            "std_enu_m": [se, sn, sv],
            "quality": row["quality"],
        }
    out.mkdir(parents=True, exist_ok=True)
    link = out / "images"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(flight.resolve())
    (out / "rtk.json").write_text(
        json.dumps(
            {
                "flight": str(flight),
                "enu_origin_lat_lon_h": ref.tolist(),
                "ellipsoid": "WGS84",
                "images": images,
            },
            indent=2,
        )
    )
    q = {r["quality"] for r in rows.values()}
    print(f"prep: {len(images)} photos, quality flags {sorted(q)}, origin {ref.round(7).tolist()}")


def calibrated_pinhole(jpg):
    """DJI's factory calibration from the photo's XMP: focal and optical centre in pixels."""
    xmp = jpg.read_bytes()[:200_000].decode("latin-1")
    keys = ("CalibratedFocalLength", "CalibratedOpticalCenterX", "CalibratedOpticalCenterY")
    vals = [re.search(rf'drone-dji:{k}="([-+0-9.]+)"', xmp) for k in keys]
    if not all(vals):
        raise SystemExit(f"{jpg.name}: no DJI calibration in the XMP")
    return [float(v.group(1)) for v in vals]


def set_camera(db, f, cx, cy, model="SIMPLE_RADIAL"):
    """Every photo shares one camera; start it at the factory focal and centre, no distortion."""
    with pycolmap.Database.open(db) as d:
        (cam,) = d.read_all_cameras()
        if model == "OPENCV":
            cam.model = pycolmap.CameraModelId.OPENCV
            cam.params = [f, f, cx, cy, 0.0, 0.0, 0.0, 0.0]
        else:
            cam.params = [f, cx, cy, 0.0]
        cam.has_prior_focal_length = True
        d.update_camera(cam)


def set_priors(db, rtk, keep):
    """Replace every pose prior with the RTK centre (ENU) of the photos in `keep`. The extractor
    writes a WGS84 prior from EXIF GPS; cleared first, so none leaks into a held-out photo. A row
    with no position stops the mapper aligning to the priors (smoke test: 123 m off as-is)."""
    with pycolmap.Database.open(db) as d:
        d.clear_pose_priors()
        n = 0
        for img in d.read_all_images():
            if img.name not in keep:
                continue
            r = rtk[img.name]
            prior = pycolmap.PosePrior()
            prior.corr_data_id = img.data_id
            prior.position = np.array(r["centre_enu_m"])
            prior.position_covariance = np.diag(np.square(r["std_enu_m"]))
            prior.coordinate_system = pycolmap.PosePriorCoordinateSystem.CARTESIAN
            d.write_pose_prior(prior)
            n += 1
    return n


def centres(rec):
    return {
        i.name: i.projection_center()
        for i in rec.images.values()
        if i.has_pose and i.num_points3D > 0
    }


def errors(est, ref, names):
    e = np.array([np.linalg.norm(est[n] - ref[n]) for n in names])
    if not len(e):
        return {"images": 0}
    return {
        "images": len(e),
        "median_m": round(float(np.median(e)), 4),
        "p95_m": round(float(np.percentile(e, 95)), 4),
        "max_m": round(float(e.max()), 4),
    }


def score(recons, rtk, prior_names):
    ref = {n: np.array(v["centre_enu_m"]) for n, v in rtk.items()}
    if not recons:
        return {"registered": 0}
    largest = max(recons.values(), key=lambda r: r.num_reg_images())
    est = centres(largest)
    names = sorted(est)
    e = np.array([est[n] for n in names])
    g = np.array([ref[n] for n in names])
    s, rot, t = umeyama(e, g)
    aligned = {n: s * rot @ est[n] + t for n in names}
    out = {
        "largest_component_photos": len(names),
        "sim3_scale": round(float(s), 6),
        "scale_error_pct": round(100 * (1 / s - 1), 4),
        "after_sim3": errors(aligned, ref, names),
    }
    if prior_names:
        # The model claims the priors' frame: compare it as it stands, no alignment.
        out["as_is_with_prior"] = errors(est, ref, [n for n in names if n in prior_names])
        out["as_is_held_out"] = errors(est, ref, [n for n in names if n not in prior_names])
    return out


def cmd_run(args):
    root = args.out
    rtk = json.loads((root / "rtk.json").read_text())["images"]
    image_dir = root / "images"
    names = sorted(rtk)
    if args.limit:
        names = names[: args.limit]
        rtk = {n: rtk[n] for n in names}
    base = root / "features.db"
    shared = {}
    if not base.exists():
        tmp = root / "features.db.partial"
        tmp.unlink(missing_ok=True)
        ext = pycolmap.FeatureExtractionOptions()
        ext.max_image_size = MAX_IMAGE_SIZE
        ext.num_threads = args.threads
        ext.sift.max_num_features = MAX_FEATURES
        timed(
            shared,
            "features_s",
            lambda: pycolmap.extract_features(
                tmp,
                image_dir,
                image_names=names,
                camera_mode=pycolmap.CameraMode.SINGLE,
                extraction_options=ext,
                device=pycolmap.Device.cpu,
            ),
        )
        mo = pycolmap.FeatureMatchingOptions()
        mo.num_threads = args.threads
        timed(
            shared,
            "matching_s",
            lambda: pycolmap.match_exhaustive(tmp, matching_options=mo, device=pycolmap.Device.cpu),
        )
        tmp.rename(base)
        (root / "shared_timings.json").write_text(json.dumps(shared))
    else:
        shared = json.loads((root / "shared_timings.json").read_text())

    odd = {n for n in names if int(Path(n).stem.rsplit("_", 1)[1]) % 2 == 1}
    variants = {"none": set(), "prior": set(names), "prior_half": odd}
    calib = calibrated_pinhole(image_dir / names[0])
    if args.variants:
        variants = {k: variants[k] for k in args.variants.split(",")}
    results = {
        "flight": root.name,
        "machine": {"host": platform.node(), "arch": platform.machine()},
        "pycolmap": pycolmap.__version__,
        "photos": len(names),
        "max_image_size": MAX_IMAGE_SIZE,
        "max_num_features": MAX_FEATURES,
        "camera_start_f_cx_cy_px": calib,
        "camera_fixed": "focal and principal point; distortion refined",
        "shared_timings": shared,
        "variants": {},
    }
    # Runs of a subset of variants add to the file rather than replace it.
    if (root / "results.json").exists():
        results["variants"] = json.loads((root / "results.json").read_text())["variants"]
    suffix = "" if args.camera == "SIMPLE_RADIAL" else "_" + args.camera.lower()
    for name, keep in variants.items():
        variant = name + suffix
        out = root / variant
        if out.exists():
            shutil.rmtree(out)
        out.mkdir()
        db = out / "database.db"
        shutil.copy(base, db)
        n_priors = set_priors(db, rtk, keep)
        set_camera(db, *calib, model=args.camera)
        inc = pycolmap.IncrementalPipelineOptions()
        inc.num_threads = args.threads
        # Straight-down photos of near-flat ground leave focal length and height entangled: with
        # the focal free, the first full run's models grew to about 20 photos and collapsed five
        # times in 13 minutes. The factory focal and centre are held; distortion is refined.
        inc.ba_refine_focal_length = False
        inc.ba_refine_principal_point = False
        inc.use_prior_position = n_priors > 0
        sparse = out / "sparse"
        sparse.mkdir()
        t0 = time.perf_counter()
        recons = pycolmap.incremental_mapping(db, image_dir, sparse, inc)
        for i, r in recons.items():
            (sparse / str(i)).mkdir(exist_ok=True)
            r.write(str(sparse / str(i)))
        rep = components.report(components.read_components(sparse)) if recons else None
        results["variants"][variant] = {
            "camera_model": args.camera,
            "position_priors": n_priors,
            "mapping_s": round(time.perf_counter() - t0, 1),
            "components": rep and rep["components"],
            "registered": rep and rep["registered"],
            "breaks": rep and len(rep["breaks"]),
            **score(recons, rtk, keep),
        }
        print(variant, json.dumps(results["variants"][variant]), flush=True)
    (root / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("flight", type=Path)
    p.add_argument("out", type=Path)
    p.set_defaults(func=cmd_prep)
    p = sub.add_parser("run")
    p.add_argument("out", type=Path)
    p.add_argument("--threads", type=int, default=16)
    p.add_argument("--limit", type=int, default=0, help="first N photos only (a smoke test)")
    p.add_argument("--variants", default="", help="comma-separated subset, e.g. prior_half")
    p.add_argument("--camera", choices=["SIMPLE_RADIAL", "OPENCV"], default="SIMPLE_RADIAL")
    p.set_defaults(func=cmd_run)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
