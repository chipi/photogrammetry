"""RC-P9: measure a model built by run_p9.py against the fixture's known geometry.

    uv run python measure_p9.py <capture set> <out> <fixture dir>

Reads `<fixture dir>/ground_truth.json` and `<set name>.marker_pixels.json` (written by
make_fixture.py) and writes `<out>/results.json`.

Scale: distances between fitted opposite room planes against the true room dimensions.
Placement: eight room corners (intersections of fitted planes), a sphere centre and a cylinder axis
against their true positions in the map frame, as a fraction of the scene extent.
Frames: the floor normal, the corner and object positions, and the pixel positions of rendered
markers against the converted poses; two deliberately wrong conversions as negative controls.
"""

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pycolmap

from recon import capture_set as cs_mod

SCALE_LIMIT, PLACEMENT_LIMIT = 0.005, 0.01
AXES = {"x": 0, "y": 1, "z": 2}


def good_points(rec, min_track=3, max_error=1.0):
    pts = [
        p for p in rec.points3D.values() if p.track.length() >= min_track and p.error < max_error
    ]
    return np.array([p.xyz for p in pts])


def inside_object(pts, objects, margin=0.05):
    """Mask of points inside an object's bounding box grown by `margin`."""
    mask = np.zeros(len(pts), bool)
    for o in objects.values():
        c = np.array(o["centre"])
        if o["kind"] == "sphere":
            half = np.full(3, o["radius"])
        elif o["kind"] == "cylinder":
            half = np.array([o["radius"], o["radius"], o["height"] / 2])
        else:
            half = np.array(o["size"]) / 2
        mask |= np.all(np.abs(pts - c) < half + margin, axis=1)
    return mask


def fit_plane(pts):
    c = pts.mean(0)
    n = np.linalg.svd(pts - c)[2][-1]
    return n, float(n @ c)


def wall_plane(pts, axis, truth, room, objects):
    """Plane near the true wall `axis=truth`: densest 2 cm slab within 30 cm, then a least-squares
    fit to the points within 3 cm of that slab. Points on objects and outside the room are out."""
    a = AXES[axis]
    keep = ~inside_object(pts, objects)
    for k, ax in enumerate("xyz"):
        if k != a:
            lo, hi = room[ax]
            keep &= (pts[:, k] > lo + 0.05) & (pts[:, k] < hi - 0.05)
    cand = pts[keep & (np.abs(pts[:, a] - truth) < 0.3)]
    hist, edges = np.histogram(cand[:, a], bins=np.arange(truth - 0.3, truth + 0.3001, 0.02))
    mode = edges[hist.argmax()] + 0.01
    inl = cand[np.abs(cand[:, a] - mode) < 0.03]
    n, c = fit_plane(inl)
    if n[a] < 0:
        n, c = -n, -c
    return {"n": n, "c": c, "inliers": len(inl)}


def plane_corner(px, py, pz):
    a = np.array([px["n"], py["n"], pz["n"]])
    return np.linalg.solve(a, np.array([px["c"], py["c"], pz["c"]]))


def sphere_fit(pts, centre, radius):
    d = np.linalg.norm(pts - centre, axis=1)
    p = pts[(d > radius * 0.75) & (d < radius * 1.35)]
    for _ in range(3):
        a = np.c_[2 * p, np.ones(len(p))]
        sol = np.linalg.lstsq(a, (p**2).sum(1), rcond=None)[0]
        c = sol[:3]
        r = math.sqrt(sol[3] + c @ c)
        d = np.abs(np.linalg.norm(pts - c, axis=1) - r)
        p = pts[d < 0.02]
    return c, r, len(p)


def cylinder_fit(pts, centre, radius, height):
    z0, z1 = centre[2] - height / 2 + 0.1, centre[2] + height / 2 - 0.1
    p = pts[(pts[:, 2] > z0) & (pts[:, 2] < z1)]
    r = np.linalg.norm(p[:, :2] - centre[:2], axis=1)
    p = p[np.abs(r - radius) < 0.1][:, :2]
    for _ in range(3):
        a = np.c_[2 * p, np.ones(len(p))]
        sol = np.linalg.lstsq(a, (p**2).sum(1), rcond=None)[0]
        c = sol[:2]
        rr = math.sqrt(sol[2] + c @ c)
        p = p[np.abs(np.linalg.norm(p - c, axis=1) - rr) < 0.02] if len(p) > 50 else p
    return c, rr, len(p)


def top_plane_height(pts, box):
    cx, cy, cz = box["centre"]
    sx, sy, sz = box["size"]
    top = cz + sz / 2
    m = (
        (np.abs(pts[:, 0] - cx) < sx / 2 - 0.08)
        & (np.abs(pts[:, 1] - cy) < sy / 2 - 0.08)
        & (np.abs(pts[:, 2] - top) < 0.05)
    )
    return float(np.median(pts[m, 2])), int(m.sum())


def geometry(pts, truth):
    room, objects, extent = truth["room"], truth["objects"], truth["extent_m"]
    planes = {}
    for axis, i in (("x", 0), ("y", 0), ("z", 0), ("x", 1), ("y", 1), ("z", 1)):
        planes[f"{axis}{i}"] = wall_plane(pts, axis, room[axis][i], room, objects)
    centre = np.array([sum(room[a]) / 2 for a in "xyz"])

    def position(name):
        # Where the fitted plane crosses the axis through the room centre.
        pl, a = planes[name], AXES[name[0]]
        other = [k for k in range(3) if k != a]
        return float((pl["c"] - pl["n"][other] @ centre[other]) / pl["n"][a])

    res = {"planes": {}, "scale": {}, "placement": {}}
    for name, pl in planes.items():
        a = AXES[name[0]]
        truth_pos = room[name[0]][int(name[1])]
        tilt = float(np.degrees(np.arccos(np.clip(abs(pl["n"][a]), 0, 1))))
        res["planes"][name] = {
            "inliers": pl["inliers"],
            "position_m": round(position(name), 4),
            "truth_m": truth_pos,
            "error_m": round(position(name) - truth_pos, 4),
            "normal": [round(float(v), 5) for v in pl["n"]],
            "tilt_from_axis_deg": round(tilt, 3),
        }
    for axis in "xyz":
        true_len = room[axis][1] - room[axis][0]
        length = position(axis + "1") - position(axis + "0")
        res["scale"][f"{axis}_span"] = {
            "measured_m": round(length, 4),
            "truth_m": true_len,
            "relative_error": round(length / true_len - 1, 5),
        }
    res["scale"]["max_abs_relative_error"] = max(
        abs(v["relative_error"]) for v in res["scale"].values() if isinstance(v, dict)
    )
    corner_err = []
    for xi, yi, zi in itertools.product((0, 1), repeat=3):
        got = plane_corner(planes[f"x{xi}"], planes[f"y{yi}"], planes[f"z{zi}"])
        want = np.array([room["x"][xi], room["y"][yi], room["z"][zi]])
        corner_err.append(float(np.linalg.norm(got - want)))
    res["placement"]["room_corners_error_m"] = [round(e, 4) for e in corner_err]
    sph = objects["sphere"]
    c, r, n = sphere_fit(pts, np.array(sph["centre"]), sph["radius"])
    sphere_err = float(np.linalg.norm(c - sph["centre"]))
    res["placement"]["sphere"] = {
        "centre": [round(float(v), 4) for v in c],
        "truth_centre": sph["centre"],
        "centre_error_m": round(sphere_err, 4),
        "radius_m": round(r, 4),
        "truth_radius_m": sph["radius"],
        "inliers": n,
    }
    cyl = objects["cylinder"]
    cc, cr, n = cylinder_fit(pts, np.array(cyl["centre"]), cyl["radius"], cyl["height"])
    cyl_err = float(np.linalg.norm(cc - cyl["centre"][:2]))
    res["placement"]["cylinder"] = {
        "axis_xy": [round(float(v), 4) for v in cc],
        "truth_axis_xy": cyl["centre"][:2],
        "axis_error_m": round(cyl_err, 4),
        "radius_m": round(cr, 4),
        "truth_radius_m": cyl["radius"],
        "inliers": n,
    }
    top, n = top_plane_height(pts, objects["box_low"])
    res["placement"]["box_low_top"] = {
        "z_m": round(top, 4),
        "truth_z_m": objects["box_low"]["centre"][2] + objects["box_low"]["size"][2] / 2,
        "inliers": n,
    }
    errs = [
        *corner_err,
        sphere_err,
        cyl_err,
        abs(top - res["placement"]["box_low_top"]["truth_z_m"]),
    ]
    res["placement"]["max_error_m"] = round(max(errs), 4)
    res["placement"]["max_fraction_of_extent"] = round(max(errs) / extent, 5)
    res["placement"]["median_fraction_of_extent"] = round(float(np.median(errs)) / extent, 5)
    res["scene_extent_m"] = round(extent, 3)
    res["frame_checks"] = {
        "floor_normal_angle_to_plus_z_deg": res["planes"]["z0"]["tilt_from_axis_deg"],
        "ceiling_above_floor": res["planes"]["z1"]["position_m"]
        > res["planes"]["z0"]["position_m"],
        "x1_east_of_x0": res["planes"]["x1"]["position_m"] > res["planes"]["x0"]["position_m"],
        "y1_north_of_y0": res["planes"]["y1"]["position_m"] > res["planes"]["y0"]["position_m"],
    }
    return res


def pixel_check(cs, truth, markers):
    """Rendered marker centroids against the converted poses' projection of the true positions."""
    cam = next(iter(cs.cameras.values()))
    by_index = {f"{f.index:06d}": f for f in cs.frames}
    variants = {
        "given_convention": cs.convention,
        "control_axes_treated_as_opencv": cs_mod.PoseConvention(
            cs.convention.direction, "opencv", cs.convention.world_up
        ),
        "control_world_treated_as_y_up": cs_mod.PoseConvention(
            cs.convention.direction, cs.convention.camera_axes, "+y"
        ),
    }
    out = {}
    for name, conv in variants.items():
        errs, missing = [], 0
        for idx, dets in markers["detections"].items():
            f = by_index[idx]
            rot, trans = cs_mod.cam_from_world(f.position, f.quaternion_xyzw, conv)
            for mname, det in dets.items():
                u, v, depth = cs_mod.project(rot, trans, cam, tuple(truth["markers"][mname]))
                if depth <= 0:
                    missing += 1
                    continue
                errs.append(math.hypot(u - det["u"], v - det["v"]))
        e = np.array(errs)
        n_det = sum(len(d) for d in markers["detections"].values())
        out[name] = {
            "detections": n_det,
            "projected_in_front": len(e),
            "behind_camera": missing,
            "within_2px": int((e < 2).sum()),
            "median_px": round(float(np.median(e)), 3) if len(e) else None,
            "max_px": round(float(e.max()), 3) if len(e) else None,
        }
    return out


def umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    u, d, vt = np.linalg.svd(xd.T @ xs / len(src))
    sign = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[2, 2] = -1
    rot = u @ sign @ vt
    scale = np.trace(np.diag(d) @ sign) / xs.var(0).sum()
    return scale, rot, mu_d - scale * rot @ mu_s


def free_run_check(out, cs, extent):
    """Pose-free incremental map, Sim(3)-aligned onto the given camera centres."""
    models = sorted((out / "free").glob("*"))
    if not models:
        return None
    rec = pycolmap.Reconstruction(str(models[0]))
    given = {}
    for f in cs.frames:
        rot, trans = cs_mod.cam_from_world(f.position, f.quaternion_xyzw, cs.convention)
        given[cs_mod.colmap_name(f)] = cs_mod.camera_centre(rot, trans)
    est, ref = [], []
    for img in rec.images.values():
        if img.has_pose and img.name in given:
            est.append(np.asarray(img.cam_from_world().inverse().translation))
            ref.append(given[img.name])
    est, ref = np.array(est), np.array(ref)
    s, rot, t = umeyama(est, ref)
    resid = np.linalg.norm((s * (rot @ est.T)).T + t - ref, axis=1)
    return {
        "registered": len(est),
        "of": len(cs.frames),
        "sim3_scale_given_per_free_unit": round(float(s), 5),
        "camera_centre_residual_m_median": round(float(np.median(resid)), 4),
        "camera_centre_residual_m_max": round(float(resid.max()), 4),
        "residual_fraction_of_extent_max": round(float(resid.max()) / extent, 5),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_set", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    cs = cs_mod.load(args.capture_set)
    truth = json.loads((args.fixture / "ground_truth.json").read_text())
    markers = json.loads((args.fixture / f"{args.capture_set.name}.marker_pixels.json").read_text())
    rec = pycolmap.Reconstruction(str(args.out / "model"))
    pts = good_points(rec)

    res = {
        "model": {
            "images_in_model": rec.num_reg_images(),
            "points3D": rec.num_points3D(),
            "points_used (track>=3, error<1px)": len(pts),
            "reprojection_error_mean_px": round(
                float(np.mean([p.error for p in rec.points3D.values()])), 4
            ),
        },
        **geometry(pts, truth),
        "pixel_check": pixel_check(cs, truth, markers),
    }
    free = free_run_check(args.out, cs, truth["extent_m"])
    if free:
        res["free_run_vs_given_poses"] = free
    scale_ok = res["scale"]["max_abs_relative_error"] < SCALE_LIMIT
    place_ok = res["placement"]["max_fraction_of_extent"] < PLACEMENT_LIMIT
    pix = res["pixel_check"]["given_convention"]
    frame_ok = (
        pix["within_2px"] == pix["detections"]
        and res["frame_checks"]["floor_normal_angle_to_plus_z_deg"] < 2.0
        and all(v for k, v in res["frame_checks"].items() if isinstance(v, bool))
    )
    res["verdict"] = {
        "scale_error_below_0.5pct": scale_ok,
        "placement_error_below_1pct_of_extent": place_ok,
        "frame_conversions_match_render": frame_ok,
    }
    (args.out / "results.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print("PASS" if scale_ok and place_ok and frame_ok else "FAIL")


if __name__ == "__main__":
    main()
