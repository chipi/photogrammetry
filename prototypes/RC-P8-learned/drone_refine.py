"""RC-P8 on a drone, the height offset: where the 1 m between the model's ground and the survey
comes from. Runs in RC-P1's environment (pycolmap), on the outputs of `drone_rtk.py`.

    drone_refine.py ppk OUT PPK_DIR      the MRK positions against a PPK solution (drone_ppk.sh)
    drone_refine.py ba OUT [--source V] [--free-focal] [--free-pp]
                                         bundle adjustment tied to all 430 RTK centres

Both score the ground against the survey points (`checkpoints_enu.json`, written by RC-P13's drone
builder's frame: ETRS89 points in the flight's ENU).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pycolmap

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P13-structured/drone"))
from build_drone import POINTS_XLSX, survey_points, to_enu


def ground_error(rec, cps, shift=(0.0, 0.0, 0.0)):
    """Median model height within 1 m of each survey point, minus the survey height."""
    xyz = np.array([p.xyz for p in rec.points3D.values()]) + np.asarray(shift)
    dz = []
    for p in cps.values():
        sel = xyz[np.linalg.norm(xyz[:, :2] - p[:2], axis=1) < 1.0]
        if len(sel) >= 5:
            dz.append(float(np.median(sel[:, 2]) - p[2]))
    return {
        "n": len(dz),
        "mean_m": round(float(np.mean(dz)), 3),
        "std_m": round(float(np.std(dz)), 3),
    }


def mrk_rows(flight):
    (mrk,) = flight.glob("*_Timestamp.MRK")
    rows = []
    for ln in mrk.read_text().splitlines():
        f = ln.split()
        val = {x.split(",")[1]: float(x.split(",")[0]) for x in f if x.count(",") == 1}
        rows.append((float(f[1]), val["Lat"], val["Lon"], val["Ellh"]))
    return np.array(rows)


def cmd_ppk(a):
    meta = json.loads((a.out / "rtk.json").read_text())
    origin = meta["enu_origin_lat_lon_h"]
    pos = np.array(
        [
            [float(x) for x in ln.split()[1:5]]  # week, then time of week, lat, lon, h
            for ln in (a.ppk / "ppk.pos").read_text().splitlines()
            if not ln.startswith("%") and ln.split()[5] == "1"
        ]
    )
    mrk = mrk_rows(Path(meta["flight"]))
    llh = np.stack([np.interp(mrk[:, 0], pos[:, 0], pos[:, k]) for k in (1, 2, 3)], 1)
    gps = pycolmap.GPSTransform(pycolmap.GPSTransformEllipsoid.WGS84)
    d = np.array(gps.ellipsoid_to_enu(llh, *origin)) - np.array(
        gps.ellipsoid_to_enu(mrk[:, 1:4], *origin)
    )
    cps = to_enu(survey_points(POINTS_XLSX), origin)
    rec = pycolmap.Reconstruction(str(a.out / a.source / "sparse/0"))
    out = {
        "fixed_epochs": len(pos),
        "photos": len(mrk),
        "ppk_minus_mrk_mean_enu_m": d.mean(0).round(3).tolist(),
        "ppk_minus_mrk_std_enu_m": d.std(0).round(3).tolist(),
        "ground_as_mapped": ground_error(rec, cps),
        "ground_in_ppk_frame": ground_error(rec, cps, d.mean(0)),
    }
    print(json.dumps(out, indent=1))
    (a.ppk / "compare.json").write_text(json.dumps(out, indent=1))


def cmd_ba(a):
    meta = json.loads((a.out / "rtk.json").read_text())
    rtk = meta["images"]
    cps = to_enu(survey_points(POINTS_XLSX), meta["enu_origin_lat_lon_h"])
    rec = pycolmap.Reconstruction(str(a.out / a.source / "sparse/0"))
    before = {"camera": np.round(next(iter(rec.cameras.values())).params, 4).tolist()}
    before["ground"] = ground_error(rec, cps)
    with pycolmap.Database.open(a.out / "prior/database.db") as db:
        priors = db.read_all_pose_priors()
    opts = pycolmap.BundleAdjustmentOptions()
    opts.refine_focal_length = a.free_focal
    opts.refine_principal_point = a.free_pp
    opts.refine_extra_params = True
    popts = pycolmap.PosePriorBundleAdjustmentOptions()
    # The MRK rows carry RTK sigmas of 1-2 cm; 3 cm stands for all of them.
    popts.prior_position_fallback_stddev = 0.03
    config = pycolmap.BundleAdjustmentConfig()
    for image_id in rec.reg_image_ids():
        config.add_image(image_id)
    summary = pycolmap.create_pose_prior_bundle_adjuster(opts, popts, config, priors, rec).solve()
    du = [im.projection_center()[2] - rtk[im.name]["centre_enu_m"][2] for im in rec.images.values()]
    tag = (
        a.source + "_ba" + ("_freefocal" if a.free_focal else "") + ("_freepp" if a.free_pp else "")
    )
    out = {
        "source": a.source,
        "priors": len(priors),
        "termination": str(summary.termination_type),
        "before": before,
        "after": {
            "camera": np.round(next(iter(rec.cameras.values())).params, 4).tolist(),
            "camera_dU_mean_m": round(float(np.mean(du)), 3),
            "ground": ground_error(rec, cps),
        },
    }
    (a.out / tag / "sparse/0").mkdir(parents=True, exist_ok=True)
    rec.write(str(a.out / tag / "sparse/0"))
    (a.out / tag / "result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ppk")
    p.add_argument("out", type=Path)
    p.add_argument("ppk", type=Path)
    p.add_argument("--source", default="prior_half_opencv")
    p = sub.add_parser("ba")
    p.add_argument("out", type=Path)
    p.add_argument("--source", default="prior_half_opencv")
    p.add_argument("--free-focal", action="store_true")
    p.add_argument("--free-pp", action="store_true")
    a = ap.parse_args()
    {"ppk": cmd_ppk, "ba": cmd_ba}[a.cmd](a)


if __name__ == "__main__":
    main()
