"""RC-P13 cave segment: a lava tube's photogrammetric cloud to a structured scene, then the scene
against the LiDAR scans of the same tube.

The structure is a cave survey's: stations along the passage centreline, a cross-section at each,
and each section's Left, Right, Up and Down from its station (LRUD). A section's outline is
measured where the cloud has rock and unknown where it has none.

Runs in RC-P10's environment (Open3D):

    uv run --project ../../RC-P10-room python build_cave.py

Data: Grotta di Monte Intraleo (Etna), 4TU.ResearchData doi:10.4121/0cc49d43-8a5c-453e-9370-
8e9088b00b48, CC BY 4.0; clouds exported to PLY with CloudCompare 2.13.2 (Debian 13, in Docker).
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import open3d as o3d

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import scene as sc  # noqa: E402

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
DATA = RECCE / "datasets/cave-intraleo/ply"
OUT = RECCE / "runs/p13/cave/intraleo"
VOXEL_M = 0.05
STATION_STEP_M = 1.0
SLAB_M = 0.10  # half-thickness of the slab of points that makes a section
BINS = 72  # rays per section, every 5 degrees
MIN_BIN_POINTS = 3
TOL_FRAC, TOL_M = 0.02, 0.05  # proposed for the cave; the brief leaves it open
FULL_MAX_UNKNOWN = 6  # a section counts as covered with at most this many rays unknown


def load(name):
    cloud = o3d.io.read_point_cloud(str(DATA / f"{name}_merged.ply"))
    return np.asarray(cloud.voxel_down_sample(VOXEL_M).points)


def centreline(pts):
    """Stations every STATION_STEP_M along the passage: slice along the main horizontal axis,
    take each slice's centroid, then re-slice square to the local direction once."""
    xy = pts[:, :2] - pts[:, :2].mean(0)
    _, _, vt = np.linalg.svd(xy, full_matrices=False)
    axis = vt[0]
    s = xy @ axis
    knots = []
    for a in np.arange(s.min() + 0.5, s.max() - 0.5, STATION_STEP_M):
        sel = pts[np.abs(s - a) < STATION_STEP_M / 2]
        if len(sel) > 200:
            knots.append(np.median(sel, axis=0))
    knots = np.array(knots)
    refined = []
    for i, k in enumerate(knots):
        t = knots[min(i + 1, len(knots) - 1)] - knots[max(i - 1, 0)]
        t[2] = 0
        t /= np.linalg.norm(t)
        sel = pts[np.abs((pts - k) @ t) < STATION_STEP_M / 2]
        c = np.median(sel, axis=0) if len(sel) > 200 else k
        refined.append(c)
    return np.array(refined)


def single_passage(stations, max_step_m=2.0, max_turn_deg=60.0):
    """The one passage the stations follow cleanly. Seed at the station whose neighbours agree
    best, then walk both ways while each next station is close and the passage turns little.
    Iteration 2: the tube forks near one end, where slabs mix the branches and the stations
    scatter; iteration 3: a walk from an end failed at once on the mouth's wobbling station.
    Returns (passage, the rest)."""

    def turn(a, b):
        a2, b2 = a[:2] / np.linalg.norm(a[:2]), b[:2] / np.linalg.norm(b[:2])
        return math.degrees(math.acos(max(-1.0, min(1.0, float(a2 @ b2)))))

    def ok(prev, cur, nxt):
        return (
            np.linalg.norm((nxt - cur)[:2]) <= max_step_m
            and turn(cur - prev, nxt - cur) <= max_turn_deg
        )

    n = len(stations)
    score = [
        turn(stations[i] - stations[i - 1], stations[i + 1] - stations[i])
        + 10 * abs(np.linalg.norm((stations[i + 1] - stations[i])[:2]) - STATION_STEP_M)
        for i in range(1, n - 1)
    ]
    seed = 1 + int(np.argmin(score))
    lo, hi = seed - 1, seed + 1
    while hi + 1 < n and ok(stations[hi - 1], stations[hi], stations[hi + 1]):
        hi += 1
    while lo - 1 >= 0 and ok(stations[lo + 1], stations[lo], stations[lo - 1]):
        lo -= 1
    # Iteration 5: the two ends are separate; joined, they drew a line across the passage.
    return stations[lo : hi + 1], (stations[:lo], stations[hi + 1 :])


def tangents(stations):
    out = []
    for i in range(len(stations)):
        t = stations[min(i + 1, len(stations) - 1)] - stations[max(i - 1, 0)]
        t[2] = 0
        out.append(t / np.linalg.norm(t))
    return np.array(out)


def section(pts, centre, t):
    """Rays from the station in the vertical plane square to the passage: the median distance of
    the slab's points in each 5-degree bin, or None where the bin has too few points."""
    left = np.array([-t[1], t[0], 0.0])
    slab = pts[np.abs((pts - centre) @ t) < SLAB_M]
    u, v = (slab - centre) @ left, (slab - centre)[:, 2]
    ang = (np.degrees(np.arctan2(v, u)) + 360) % 360
    r = np.hypot(u, v)
    radii = []
    for b in range(BINS):
        m = (ang >= b * 360 / BINS) & (ang < (b + 1) * 360 / BINS)
        radii.append(float(np.median(r[m])) if m.sum() >= MIN_BIN_POINTS else None)
    return radii, len(slab)


def lrud(radii):
    """Left (0 deg), Up (90), Right (180), Down (270): the bin nearest each direction."""
    pick = {"left": 0, "up": BINS // 4, "right": BINS // 2, "down": 3 * BINS // 4}
    out = {}
    for k, i in pick.items():
        # The bins within +/-10 degrees of the direction, so one empty or stray bin does not
        # decide it (iteration 1).
        near = [radii[(i + d) % BINS] for d in (-2, -1, 0, 1, 2)]
        near = [r for r in near if r is not None]
        out[k] = float(np.median(near)) if len(near) >= 2 else None
    return out


def width_height(radii):
    lr = lrud(radii)
    w = lr["left"] + lr["right"] if lr["left"] is not None and lr["right"] is not None else None
    h = lr["up"] + lr["down"] if lr["up"] is not None and lr["down"] is not None else None
    return w, h


def build(photo, stations, ts, rest):
    elements, measurements = [], []
    for i, (c, t) in enumerate(zip(stations, ts, strict=True)):
        radii, n = section(photo, c, t)
        seen = sum(r is not None for r in radii)
        sid = f"section-{i}"
        elements.append(
            sc.element(
                sid,
                "cross_section",
                "measured" if seen else "unknown",
                {
                    "type": "ray_section",
                    "station": c.round(4).tolist(),
                    "tangent": t.round(5).tolist(),
                    "angles_deg": [b * 360 / BINS + 180 / BINS for b in range(BINS)],
                    "radii_m": [None if r is None else round(r, 4) for r in radii],
                },
                sigma_m=VOXEL_M if seen else None,
                sigma_basis="5 cm voxel of the downsampled cloud; not calibrated on a reference"
                if seen
                else None,
                evidence={"slab_points": n, "rays_with_rock": seen} if seen else None,
                rays_unknown=BINS - seen,
            )
        )
        w, h = width_height(radii)
        for name, val in (("width", w), ("height", h)):
            src = "measured" if val is not None else "unknown"
            measurements.append(
                sc.measurement(
                    f"{name}-{i}",
                    [sid],
                    None if val is None else round(val, 4),
                    src,
                    sigma_m=VOXEL_M * math.sqrt(2) if val is not None else None,
                    sigma_basis="two rays, each to the 5 cm voxel" if val is not None else None,
                    evidence={"rule": "left+right or up+down rays"} if val is not None else None,
                )
            )
    elements.append(
        sc.element(
            "centreline",
            "centreline",
            "inferred",
            {"type": "polyline", "points": stations.round(4).tolist()},
            rule="medians of slabs square to the local passage direction",
        )
    )
    rules = (
        "the stations before the passage starts scatter (the mouth); no sections are drawn",
        "the passage forks here; slabs mix the branches, so no sections are drawn",
    )
    for i, (part, rule) in enumerate(zip(rest, rules, strict=True)):
        if len(part) >= 2:
            elements.append(
                sc.element(
                    f"unstructured-{i}",
                    "junction",
                    "unknown",
                    {"type": "polyline", "points": part.round(4).tolist()},
                    rule=rule,
                )
            )
    return elements, measurements


def check(lidar, stations, ts, measurements, unknown_rays):
    rows = []
    for i, (c, t) in enumerate(zip(stations, ts, strict=True)):
        radii, _ = section(lidar, c, t)
        w, h = width_height(radii)
        for name, ref in (("width", w), ("height", h)):
            m = next(x for x in measurements if x["id"] == f"{name}-{i}")
            row = {"id": m["id"], "model_m": m["value_m"], "unknown_rays": unknown_rays[i]}
            if m["value_m"] is None or ref is None:
                rows.append({**row, "lidar_m": ref})
                continue
            err, tol = m["value_m"] - ref, max(TOL_FRAC * ref, TOL_M)
            rows.append(
                {
                    **row,
                    "lidar_m": round(ref, 4),
                    "error_m": round(err, 4),
                    "within": bool(abs(err) <= tol),
                }
            )
    both = [r for r in rows if r.get("error_m") is not None]
    out = {
        "reference": "LiDAR, five scans merged by the authors (CloudCompare ICP)",
        "tolerance": f"{TOL_FRAC:.0%} or {TOL_M} m, proposed; the brief leaves the cave's open",
        "model_only": sum(r["lidar_m"] is None and r["model_m"] is not None for r in rows),
        "lidar_only": sum(r["model_m"] is None and r["lidar_m"] is not None for r in rows),
        "all": stats(both),
        # Iteration 4: the large errors sit in sections the photos cover in part; split by it.
        f"covered (at most {FULL_MAX_UNKNOWN} of {BINS} rays unknown)": stats(
            [r for r in both if r["unknown_rays"] <= FULL_MAX_UNKNOWN]
        ),
        "partly covered": stats([r for r in both if r["unknown_rays"] > FULL_MAX_UNKNOWN]),
        "rows": rows,
    }
    return out


def stats(rows):
    if not rows:
        return {"compared": 0}
    errs = np.array([r["error_m"] for r in rows])
    by = {k: [r["error_m"] for r in rows if r["id"].startswith(k)] for k in ("width", "height")}
    return {
        "compared": len(rows),
        "within": sum(r["within"] for r in rows),
        "error_median_m": round(float(np.median(errs)), 4),
        "error_abs_p95_m": round(float(np.percentile(np.abs(errs), 95)), 4),
        **{f"{k}_error_median_m": round(float(np.median(v)), 4) for k, v in by.items() if v},
    }


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    photo, lidar = load("photogrammetry"), load("lidar")
    stations, rest = single_passage(centreline(photo))
    ts = tangents(stations)
    elements, measurements = build(photo, stations, ts, rest)
    s = sc.scene(
        "cave",
        {"name": "the clouds' own frame (z up, metres), as published", "units": "m"},
        {
            "reconstruction": "photogrammetry_merged.ply (12.95 M points)",
            "reference": "lidar_merged.ply (2.41 M points)",
            "context": "lava tube; z is up",
        },
        elements,
        measurements,
        notes=[f"Stations every {STATION_STEP_M} m; sections from a {2 * SLAB_M} m slab."],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    sc.write(s, OUT / "scene.json")
    unknown = [e["attributes"]["rays_unknown"] for e in elements if e["kind"] == "cross_section"]
    result = check(lidar, stations, ts, measurements, unknown)
    (OUT / "check.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=1))
    print(
        "stations",
        len(stations),
        "length m",
        round(float(np.sum(np.linalg.norm(np.diff(stations, axis=0), axis=1))), 2),
    )


if __name__ == "__main__":
    main()
