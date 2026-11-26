"""RC-P13 room segment: RC-P10's TSDF mesh to a structured scene, then the scene against Faro.

Runs in RC-P10's environment (Open3D):

    uv run --project ../../RC-P10-room python build_room.py [--video 42444793] [--seed 0]

Writes `$RECCE_DATA_DIR/runs/p13/room/<video>/scene.json` and `check.json`.
"""

import argparse
import itertools
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
import open3d as o3d

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "RC-P10-room"))
import room  # noqa: E402
import scene as sc  # noqa: E402

OUT = room.RECCE / "runs/p13/room"
SAMPLES = 400_000
CELL_M = 0.05
HORIZONTAL_COS = 0.95
WALL_THICKNESS_M = 0.10
PARTITION_MAX_M = 0.35
WALL_MIN_DENSITY_FRAC = 0.2
# RC-P10: TSDF wall-to-wall distance minus the ARKit-posed laser reference, seed 0, the 47 pairs in
# the four rooms other than 42444793 (so the Faro check below stays independent).
SEP_SIGMA_M = 0.0108
SEP_BIAS_M = -0.0091
SEP_BASIS = "RC-P10 TSDF minus laser reference, 47 wall pairs in four other rooms"


def levelling(up):
    """Rotation that takes `up` to +z (Rodrigues), so plans are drawn in x, y."""
    z = np.array([0.0, 0.0, 1.0])
    v, c = np.cross(up, z), float(up @ z)
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def cells_of(points_xy, origin):
    return {(int(x), int(y)) for x, y in np.floor((points_xy - origin) / CELL_M).astype(int)}


def footprint(seen, close=3):
    """Cells inside the seen region: dilate by `close` cells, fill holes from outside, erode."""
    pad = close + 2
    xs, ys = zip(*seen, strict=True)
    x0, y0 = min(xs) - pad, min(ys) - pad
    w, h = max(xs) + pad - x0 + 1, max(ys) + pad - y0 + 1
    grid = np.zeros((w, h), bool)
    for x, y in seen:
        grid[x - x0, y - y0] = True

    def shift_or(g, k):
        out = g.copy()
        for dx, dy in itertools.product(range(-k, k + 1), repeat=2):
            out |= np.roll(np.roll(g, dx, 0), dy, 1)
        return out

    grown = shift_or(grid, close)
    outside = np.zeros_like(grown)
    q = deque([(0, 0)])
    outside[0, 0] = True
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not outside[nx, ny] and not grown[nx, ny]:
                outside[nx, ny] = True
                q.append((nx, ny))
    filled = ~outside
    inside = ~shift_or(~filled, close)
    return {(int(x + x0), int(y + y0)) for x, y in zip(*np.nonzero(inside), strict=True)} | seen


def horizontal(planes, up, sign):
    cands = [p for p in planes if sign * (p[0] @ up) > HORIZONTAL_COS]
    return max(cands, key=lambda p: len(p[2])) if cands else None


def dense_walls(walls):
    """Drop planes whose points are far sparser than a typical wall's: RANSAC threads such planes
    through scattered fragments (iteration 2: a diagonal 'wall' at 450 points/m2 against about
    10,000 for real walls)."""
    density = [len(w["inl"]) / (w["width"] * w["height"]) for w in walls]
    floor = WALL_MIN_DENSITY_FRAC * float(np.median(density))
    return [w for w, d in zip(walls, density, strict=True) if d >= floor]


def camera_centres(traj):
    """ARKit .traj rows are cam_from_world (axis-angle, translation); centres are -R^T t."""
    return np.array([-room.rodrigues(r[1:4]).T @ r[4:7] for r in traj])


def room_side(w, up, centres):
    """+1 if the cameras that faced this wall sit on the side its normal points to, else -1."""
    t = room.horizontal_axis(w["n"], up)
    lo, hi = np.percentile(w["inl"] @ t, [1, 99])
    along, dist = centres @ t, centres @ w["n"] + w["d"]
    near = (along > lo) & (along < hi) & (np.abs(dist) < room.DEPTH_MAX_M)
    return 1 if np.sum(dist[near] > 0) >= np.sum(dist[near] < 0) else -1


def partitions(walls, up):
    """Opposite faces of one thin wall: antiparallel, under PARTITION_MAX_M apart, overlapping.
    Returns {face index: (partner index, thickness)} for the face that draws the body."""
    out, used = {}, set()
    for a, b in itertools.combinations(range(len(walls)), 2):
        wa, wb = walls[a], walls[b]
        if a in used or b in used or abs(wa["n"] @ wb["n"]) < np.cos(np.radians(room.PARALLEL_DEG)):
            continue
        sep = room.separation(wa, wb, wa, wb)
        t = room.horizontal_axis(wa["n"], up)
        la, ha = np.percentile(wa["inl"] @ t, [1, 99])
        lb, hb = np.percentile(wb["inl"] @ t, [1, 99])
        if sep < PARTITION_MAX_M and min(ha, hb) - max(la, lb) > 0.3:
            out[a] = (b, sep)
            used |= {a, b}
    return out


def wall_element(i, w, rot, up, side, body):
    """A wall face where the mesh saw it; `body` is (thickness, source, partner, draws): of the
    two faces of one wall, only one draws the body. The normal points into the cameras' room."""
    t = room.horizontal_axis(w["n"], up)
    inl = w["inl"]
    lo, hi = np.percentile(inl @ t, [1, 99])
    c = inl.mean(0)
    c = c - (w["n"] @ c + w["d"]) * w["n"]
    p0, p1 = c + (lo - c @ t) * t, c + (hi - c @ t) * t
    z0, z1 = np.percentile((inl @ rot.T)[:, 2], [1, 99])
    thickness, t_source, partner, draws = body
    return sc.element(
        f"wall-{i}",
        "wall",
        "measured",
        {
            "type": "wall_face",
            "p0": (rot @ p0)[:2].round(4).tolist(),
            "p1": (rot @ p1)[:2].round(4).tolist(),
            "z0": round(float(z0), 4),
            "z1": round(float(z1), 4),
            "normal": (rot @ (side * w["n"])).round(4).tolist(),
        },
        sigma_m=round(w["rms"], 4),
        sigma_basis="plane fit rms over the wall's TSDF points; extent is where the mesh saw it",
        evidence={"tsdf_points": len(inl)},
        thickness_m=round(thickness, 4),
        thickness_source=t_source,
        partner=partner,
        draws_body=draws,
    )


def wall_cells(walls, rot, origin):
    """Cells under each wall's face, so the area walls enclose counts even where no floor was seen
    (iteration 3: a room with walls and no floor showed neither seen nor unknown floor)."""
    out = set()
    for w in walls:
        t = room.horizontal_axis(w["n"], np.array([0.0, 0.0, 1.0]) @ rot)
        lo, hi = np.percentile(w["inl"] @ t, [1, 99])
        c = w["inl"].mean(0)
        steps = np.arange(lo, hi, CELL_M / 2) - c @ t
        out |= cells_of(((c + np.outer(steps, t)) @ rot.T)[:, :2], origin)
    return out


def surface_elements(kind, plane, rot, origin, z, barrier=frozenset()):
    seen = cells_of((plane[2] @ rot.T)[:, :2], origin)
    whole = footprint(seen | barrier) - barrier
    rms = float(np.sqrt(np.mean((plane[2] @ plane[0] + plane[1]) ** 2)))
    geom = {"type": "cells", "cell_m": CELL_M, "origin": origin.round(4).tolist(), "z": z}
    seen_el = sc.element(
        f"{kind}-seen",
        kind,
        "measured",
        {**geom, "cells": sorted(seen)},
        sigma_m=round(rms, 4),
        sigma_basis="plane fit rms over the TSDF points",
        evidence={"tsdf_points": len(plane[2])},
        area_m2=round(len(seen) * CELL_M**2, 3),
    )
    gap = sorted(whole - seen)
    gap_el = sc.element(
        f"{kind}-unseen",
        kind,
        "unknown",
        {**geom, "cells": gap},
        area_m2=round(len(gap) * CELL_M**2, 3),
        rule=f"inside the seen {kind} and the walls, gaps up to 3 cells closed; not observed",
    )
    return seen_el, gap_el, seen, whole


def build(vid, seed):
    o3d.utility.random.seed(seed)
    mesh = o3d.io.read_triangle_mesh(str(room.RUNS / vid / "tsdf.ply"))
    pts = np.asarray(mesh.sample_points_uniformly(SAMPLES).points)
    planes = room.find_planes(pts)
    traj = np.loadtxt(room.RAW / vid / "lowres_wide.traj")
    up, _ = room.gravity_up(planes, traj)
    rot = levelling(up)
    floor, ceil = horizontal(planes, up, +1), horizontal(planes, up, -1)
    z_floor = float(np.median((floor[2] @ rot.T)[:, 2]))
    origin = np.floor((pts @ rot.T)[:, :2].min(0) / CELL_M) * CELL_M
    elements, measurements = [], []
    walls = dense_walls(room.walls_of(planes, up))
    barrier = frozenset(wall_cells(walls, rot, origin))
    f_seen, f_gap, floor_seen, floor_all = surface_elements(
        "floor", floor, rot, origin, round(z_floor, 4), barrier
    )
    elements += [f_seen, f_gap]
    if ceil is not None:
        z_ceil = float(np.median((ceil[2] @ rot.T)[:, 2]))
        c_seen, c_gap, _, _ = surface_elements(
            "ceiling", ceil, rot, origin, round(z_ceil, 4), barrier
        )
        elements += [c_seen, c_gap]
        measurements.append(
            sc.measurement(
                "height",
                ["floor-seen", "ceiling-seen"],
                round(z_ceil - z_floor, 4),
                "measured",
                sigma_m=round(float(np.hypot(f_seen["sigma_m"], c_seen["sigma_m"])), 4),
                sigma_basis="floor and ceiling plane rms combined; not calibrated on a reference",
                evidence={"floor_points": len(floor[2]), "ceiling_points": len(ceil[2])},
            )
        )
    else:
        elements.append(
            sc.element("ceiling", "ceiling", "unknown", {"type": "none"}, rule="no ceiling plane")
        )
    centres = camera_centres(traj)
    pairs = partitions(walls, up)
    partnered = {b: (a, sep) for a, (b, sep) in pairs.items()}
    for i, w in enumerate(walls):
        if i in pairs:
            b, sep = pairs[i]
            body = (sep, "measured", f"wall-{b}", True)
        elif i in partnered:
            a, sep = partnered[i]
            body = (sep, "measured", f"wall-{a}", False)
        else:
            body = (WALL_THICKNESS_M, "inferred", None, True)
        elements.append(wall_element(i, w, rot, up, room_side(w, up, centres), body))
    for a, (b, sep) in pairs.items():
        measurements.append(
            sc.measurement(
                f"thickness-wall-{a}-wall-{b}",
                [f"wall-{a}", f"wall-{b}"],
                round(sep, 4),
                "measured",
                sigma_m=SEP_SIGMA_M,
                bias_m=SEP_BIAS_M,
                sigma_basis=SEP_BASIS
                + "; thin walls are outside that calibration (pairs were 1 m or more)",
                evidence={"rule": "both faces of one wall, antiparallel, under 0.35 m apart"},
            )
        )
    for g in room.axes_of(walls):
        for a, b in itertools.combinations(g["members"], 2):
            wa, wb = walls[a], walls[b]
            sep = room.separation(wa, wb, wa, wb)
            if sep < room.PAIR_MIN_SEP_M:
                continue
            measurements.append(
                sc.measurement(
                    f"distance-wall-{a}-wall-{b}",
                    [f"wall-{a}", f"wall-{b}"],
                    round(sep, 4),
                    "measured",
                    sigma_m=SEP_SIGMA_M,
                    bias_m=SEP_BIAS_M,
                    sigma_basis=SEP_BASIS,
                    evidence={"rule": "RC-P10 separation: centroids to the other plane, averaged"},
                )
            )
    s = sc.scene(
        "room",
        {
            "name": f"ARKitScenes {vid}, ARKit world levelled so up is +z",
            "units": "m",
            "up_in_arkit": up.round(5).tolist(),
            "levelling": rot.round(6).tolist(),
        },
        {
            "reconstruction": f"runs/p10/{vid}/tsdf.ply",
            "context": "ARKitScenes video; up from the camera and the floor plane",
            "ransac_seed": seed,
        },
        elements,
        measurements,
        notes=[
            "Walls are drawn where the mesh saw them; a wall's thickness is inferred.",
            "Unknown cells sit inside the seen floor or ceiling and were not observed.",
        ],
    )
    return s, {
        "walls": walls,
        "planes": planes,
        "up": up,
        "rot": rot,
        "floor": floor,
        "ceil": ceil,
        "origin": origin,
        "floor_seen": floor_seen,
        "floor_all": floor_all,
    }


def faro_points(vid):
    cloud = o3d.io.read_point_cloud(str(room.RUNS / vid / "faro.ply"))
    t = np.array(json.loads((room.RUNS / vid / "faro_to_arkit.json").read_text())["transform"])
    cloud.transform(t)
    return np.asarray(cloud.voxel_down_sample(0.01).points)


def band_plane(pts, plane, rot, cells, origin):
    """The same horizontal surface in another cloud: points near the plane over the given cells."""
    n, d = plane[0], plane[1]
    near = pts[np.abs(pts @ n + d) < room.REFIT_BAND_M]
    keep = [
        tuple(c) in cells for c in np.floor(((near @ rot.T)[:, :2] - origin) / CELL_M).astype(int)
    ]
    sel = near[np.array(keep, bool)]
    if len(sel) < 100:
        return None, set()
    n2, d2 = room.fit_plane(sel)
    sel = sel[np.abs(sel @ n2 + d2) < room.PLANE_DIST_M]
    return sel, cells_of((sel @ rot.T)[:, :2], origin)


def check(vid, s, ctx):
    faro = faro_points(vid)
    out = {"video": vid, "reference": "Faro scans, registered to ARKit (RC-P10)", "distances": []}
    for m in s["measurements"]:
        if not m["id"].startswith(("distance-", "thickness-")):
            continue
        a, b = (int(x.split("-")[1]) for x in m["of"])
        wa, wb = ctx["walls"][a], ctx["walls"][b]
        ra, rb = room.refit(wa, faro, ctx["up"]), room.refit(wb, faro, ctx["up"])
        if not (ra and rb):
            out["distances"].append({"id": m["id"], "faro_m": None})
            continue
        ref = room.separation(wa, wb, ra, rb)
        err, tol = m["value_m"] - ref, max(room.TOL_FRAC * ref, room.TOL_M)
        out["distances"].append(
            {
                "id": m["id"],
                "model_m": m["value_m"],
                "faro_m": round(ref, 4),
                "error_m": round(err, 4),
                "tolerance_m": round(tol, 4),
                "within": bool(abs(err) <= tol),
                "within_stated_2sigma": bool(abs(err - m["bias_m"]) <= 2 * m["sigma_m"]),
            }
        )
    rot, origin = ctx["rot"], ctx["origin"]
    fsel, fcells = band_plane(faro, ctx["floor"], rot, ctx["floor_all"], origin)
    seen, gap = ctx["floor_seen"], ctx["floor_all"] - ctx["floor_seen"]
    out["floor"] = {
        "model_seen_m2": round(len(seen) * CELL_M**2, 3),
        "model_unseen_m2": round(len(gap) * CELL_M**2, 3),
        "faro_seen_in_footprint_m2": round(len(fcells) * CELL_M**2, 3),
        "both_m2": round(len(seen & fcells) * CELL_M**2, 3),
        "model_unseen_that_faro_saw_m2": round(len(gap & fcells) * CELL_M**2, 3),
    }
    h = next((m for m in s["measurements"] if m["id"] == "height"), None)
    if h and ctx["ceil"] is not None and fsel is not None:
        csel, _ = band_plane(faro, ctx["ceil"], rot, ctx["floor_all"], origin)
        if csel is not None:
            ref_h = float(np.median((csel @ rot.T)[:, 2]) - np.median((fsel @ rot.T)[:, 2]))
            err = h["value_m"] - ref_h
            out["height"] = {
                "model_m": h["value_m"],
                "faro_m": round(ref_h, 4),
                "error_m": round(err, 4),
                "tolerance_m": round(max(room.TOL_FRAC * ref_h, room.TOL_M), 4),
                "within": bool(abs(err) <= max(room.TOL_FRAC * ref_h, room.TOL_M)),
            }
    d = [x for x in out["distances"] if x.get("faro_m") is not None]
    out["summary"] = {
        "distances_checked": len(d),
        "distances_within_limit": sum(x["within"] for x in d),
        "distances_within_stated_2sigma": sum(x["within_stated_2sigma"] for x in d),
        "distances_without_faro": len(out["distances"]) - len(d),
        "elements": {k: sum(e["source"] == k for e in s["elements"]) for k in sc.SOURCES},
    }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", default="42444793")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    s, ctx = build(args.video, args.seed)
    out = OUT / args.video
    sc.write(s, out / "scene.json")
    result = check(args.video, s, ctx)
    (out / "check.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "distances"}, indent=1))


if __name__ == "__main__":
    main()
