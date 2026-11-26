"""RC-P13 drone segment: RC-P8's drone reconstruction to a terrain model, then the terrain against
the survey's check points.

The structure is a surveyor's terrain model: ground heights on a regular grid of cells, measured
where the reconstruction has points and unknown where it has none, with the steep faces (quarry
walls, rock outcrops) apart from the open ground. The site is upland pasture with a quarry and
no buildings, so no building footprints are built.

Runs in RC-P1's environment (pycolmap):

    uv run --project ../../RC-P1-registration python build_drone.py [--variant prior_half_opencv]

Data: EuroSDR RPAS benchmark, Phase 2, DJI Phantom 4 RTK, flight 100_0004 (CC BY 4.0); check
points from the benchmark's `GCPsandCPs_coords.xlsx` (ETRS89, GRS80 ellipsoidal heights).
"""

import argparse
import json
import os
import re
import sys
import warnings
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pycolmap

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import scene as sc  # noqa: E402

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
RUN = RECCE / "runs/p8drone/100_0004"
POINTS_XLSX = RECCE / "datasets/eurosdr-rpas/GCPsandCPs_coords.xlsx"
OUT = RECCE / "runs/p13/drone/100_0004"
CELL_M = 2.0
MIN_CELL_POINTS = 4
STEEP_DEG = 45.0
# Each photo sees about 82 x 55 m of ground from 55 m; within 25 m of a camera, the ground is
# in its view.
FOOTPRINT_M = 25.0
# Iteration 2: a gap whose 8 neighbours are mostly seen is a cell short of points, not a hole.
MIN_SEEN_NEIGHBOURS = 6
XLSX = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def survey_points(path):
    """Station id to ETRS89 (lat, lon, h). The sheet's columns E, F, G are the geodetic ones."""
    z = zipfile.ZipFile(path)
    # The benchmark's own sheet, checksummed at download; defusedxml would be a new dependency.
    strings = [
        "".join(t.text or "" for t in si.iter(f"{{{XLSX['m']}}}t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", XLSX)  # noqa: S314
    ]
    out = {}
    for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(f"{{{XLSX['m']}}}row"):  # noqa: S314
        vals = {}
        for c in row.findall("m:c", XLSX):
            v = c.findtext("m:v", namespaces=XLSX)
            if v is not None:
                col = re.match(r"[A-Z]+", c.get("r")).group()
                vals[col] = strings[int(v)] if c.get("t") == "s" else float(v)
        if isinstance(vals.get("A"), str) and isinstance(vals.get("E"), float):
            out[vals["A"]] = (vals["E"], vals["F"], vals["G"])
    return out


def to_enu(points, origin):
    gps = pycolmap.GPSTransform(pycolmap.GPSTransformEllipsoid.WGS84)
    names = sorted(points)
    enu = gps.ellipsoid_to_enu(np.array([points[n] for n in names]), *origin)
    return {n: np.asarray(e) for n, e in zip(names, enu, strict=True)}


def held_out_sigma(rec, rtk):
    """The vertical error of the photos that had no prior, as the model stands: the one check of
    the frame the reconstruction carries without ground information."""
    du = [
        img.projection_center()[2] - rtk[img.name]["centre_enu_m"][2]
        for img in rec.images.values()
        if int(Path(img.name).stem.rsplit("_", 1)[1]) % 2 == 0
    ]
    return float(np.sqrt(np.mean(np.square(du)))), len(du)


def grid(xyz, cams):
    """Median height of the points in each cell, over the cameras' extent."""
    lo = np.floor(cams[:, :2].min(0) / CELL_M) * CELL_M
    hi = np.ceil(cams[:, :2].max(0) / CELL_M) * CELL_M
    nx, ny = ((hi - lo) / CELL_M).astype(int)
    ij = np.floor((xyz[:, :2] - lo) / CELL_M).astype(int)
    keep = (ij >= 0).all(1) & (ij[:, 0] < nx) & (ij[:, 1] < ny)
    ij, z = ij[keep], xyz[keep, 2]
    flat = ij[:, 0] * ny + ij[:, 1]
    order = np.argsort(flat)
    flat, z = flat[order], z[order]
    heights = np.full(nx * ny, np.nan)
    counts = np.zeros(nx * ny, int)
    starts = np.flatnonzero(np.r_[True, flat[1:] != flat[:-1]])
    for s, e in zip(starts, np.r_[starts[1:], len(flat)], strict=True):
        counts[flat[s]] = e - s
        if e - s >= MIN_CELL_POINTS:
            heights[flat[s]] = np.median(z[s:e])
    return lo, nx, ny, heights.reshape(nx, ny), counts.reshape(nx, ny)


def footprint(lo, shape, cams):
    """Cells whose centre is within FOOTPRINT_M of a camera: the ground the flight looked at."""
    ii, jj = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]), indexing="ij")
    centres = lo + (np.stack([ii, jj], -1).reshape(-1, 2) + 0.5) * CELL_M
    near = np.zeros(len(centres), bool)
    for c in cams[:, :2]:
        near |= np.sum((centres - c) ** 2, axis=1) <= FOOTPRINT_M**2
    return near.reshape(shape)


def slope_deg(h):
    gx, gy = np.gradient(h, CELL_M)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def fill(h):
    """Heights for unseen cells, from the nearest seen ones; for drawing only, never measured."""
    out = h.copy()
    for _ in range(200):
        miss = np.isnan(out)
        if not miss.any():
            break
        pad = np.pad(out, 1, constant_values=np.nan)
        nb = np.stack([pad[1:-1, :-2], pad[1:-1, 2:], pad[:-2, 1:-1], pad[2:, 1:-1]])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            m = np.nanmean(nb, axis=0)
        out[miss] = m[miss]
    return out


def neighbours(h):
    """For each cell, how many of its 8 neighbours are seen, and their mean height."""
    pad = np.pad(h, 1, constant_values=np.nan)
    nx, ny = h.shape
    stack = np.stack(
        [
            pad[1 + a : 1 + a + nx, 1 + b : 1 + b + ny]
            for a in (-1, 0, 1)
            for b in (-1, 0, 1)
            if a or b
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return (~np.isnan(stack)).sum(0), np.nanmean(stack, axis=0)


def grid_geometry(lo, h, mask):
    return {
        "type": "height_grid",
        "origin": [round(float(lo[0]), 3), round(float(lo[1]), 3)],
        "cell_m": CELL_M,
        "shape": list(h.shape),
        "heights_m": [
            [round(float(v), 3) if m else None for v, m in zip(row, mrow, strict=True)]
            for row, mrow in zip(h, mask, strict=True)
        ],
    }


def build(rec, rtk, cps):
    xyz = np.array([p.xyz for p in rec.points3D.values()])
    cams = np.array([img.projection_center() for img in rec.images.values()])
    lo, nx, ny, h, counts = grid(xyz, cams)
    inside = footprint(lo, h.shape, cams)
    h[~inside] = np.nan
    seen = ~np.isnan(h)
    steep = seen & (slope_deg(fill(h)) > STEEP_DEG)
    sigma, n_held = held_out_sigma(rec, rtk)
    basis = (
        f"RMS vertical error of the {n_held} photos without a prior against their RTK centres; "
        "a camera check, not a ground check"
    )
    evidence = {"points": len(xyz), "cell_m": CELL_M, "min_points_per_cell": MIN_CELL_POINTS}
    n_seen, mean_nb = neighbours(h)
    short = inside & ~seen & (n_seen >= MIN_SEEN_NEIGHBOURS)
    hole = inside & ~seen & ~short
    model = np.where(short, mean_nb, h)
    drawn = fill(model)
    elements = [
        sc.element(
            "terrain",
            "terrain",
            "measured",
            grid_geometry(lo, h, seen & ~steep),
            sigma_m=round(sigma, 3),
            sigma_basis=basis,
            evidence={**evidence, "cells": int((seen & ~steep).sum())},
        ),
        sc.element(
            "steep",
            "steep_face",
            "measured",
            grid_geometry(lo, h, steep),
            sigma_m=round(sigma, 3),
            sigma_basis=basis + "; a cell's height on a steep face also depends on where in the "
            "cell the points fall",
            evidence={**evidence, "cells": int(steep.sum()), "slope_over_deg": STEEP_DEG},
        ),
        sc.element(
            "interpolated",
            "terrain",
            "inferred",
            grid_geometry(lo, model, short),
            rule=f"cells with fewer than {MIN_CELL_POINTS} points but at least "
            f"{MIN_SEEN_NEIGHBOURS} of 8 neighbours seen: the neighbours' mean height",
            cells=int(short.sum()),
        ),
        sc.element(
            "unseen",
            "terrain",
            "unknown",
            grid_geometry(lo, drawn, hole),
            rule=f"cells with fewer than {MIN_CELL_POINTS} points and fewer than "
            f"{MIN_SEEN_NEIGHBOURS} of 8 neighbours seen; drawn at the nearest seen height, which "
            "is not a measurement",
            cells=int(hole.sum()),
        ),
    ]
    measurements = []
    for name, p in sorted(cps.items()):
        i, j = np.floor((p[:2] - lo) / CELL_M).astype(int)
        inside = 0 <= i < nx and 0 <= j < ny
        inside_ij = 0 <= i < nx and 0 <= j < ny
        if inside_ij and seen[i, j]:
            on, src, val = ("steep" if steep[i, j] else "terrain"), "measured", float(h[i, j])
        elif inside_ij and short[i, j]:
            on, src, val = "interpolated", "inferred", float(model[i, j])
        else:
            on, src, val = "unseen", "unknown", None
        measurements.append(
            sc.measurement(
                f"height-{name}",
                [on],
                None if val is None else round(val, 3),
                src,
                sigma_m=round(sigma, 3) if src == "measured" else None,
                sigma_basis=basis if src == "measured" else None,
                evidence={"cell": [int(i), int(j)], "points": int(counts[i, j])}
                if src == "measured"
                else None,
            )
        )
    return elements, measurements, sigma


def check(measurements, cps, sigma):
    """Model heights against the survey: as the model stands (RTK only, no ground information),
    and after one vertical shift fitted on the 8 ground control points, checked on the rest."""
    rows = []
    for m in measurements:
        name = m["id"].removeprefix("height-")
        if m["value_m"] is not None:
            rows.append(
                {
                    "id": name,
                    "source": m["source"],
                    "model_m": m["value_m"],
                    "survey_m": round(float(cps[name][2]), 3),
                }
            )
    for r in rows:
        r["error_m"] = round(r["model_m"] - r["survey_m"], 3)
    meas = [r for r in rows if r["source"] == "measured"]
    gcp = [r for r in meas if r["id"].startswith("G")]
    shift = float(np.median([r["error_m"] for r in gcp]))
    rest = [r for r in meas if not r["id"].startswith("G")]

    def stats(errs):
        e = np.array(errs)
        return {
            "n": len(e),
            "mean_m": round(float(e.mean()), 3),
            "std_m": round(float(e.std()), 3),
            "abs_p95_m": round(float(np.percentile(np.abs(e), 95)), 3),
            "within_2_sigma": int((np.abs(e) <= 2 * sigma).sum()),
        }

    return {
        "reference": "EuroSDR survey points, ETRS89 ellipsoidal heights, in the RTK frame's ENU",
        "sigma_m": round(sigma, 3),
        "as_is_measured": stats([r["error_m"] for r in meas]),
        "gcps_used": len(gcp),
        "inferred": [
            {k: r[k] for k in ("id", "error_m")} for r in rows if r["source"] == "inferred"
        ],
        "gcp_shift_m": round(shift, 3),
        "after_gcp_shift_check_points": stats([r["error_m"] - shift for r in rest]),
        "unknown": sum(m["value_m"] is None for m in measurements),
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", default="prior_half_opencv")
    a = ap.parse_args()
    meta = json.loads((RUN / "rtk.json").read_text())
    rec = pycolmap.Reconstruction(str(RUN / a.variant / "sparse/0"))
    cps = to_enu(survey_points(POINTS_XLSX), meta["enu_origin_lat_lon_h"])
    elements, measurements, sigma = build(rec, meta["images"], cps)
    s = sc.scene(
        "drone",
        {"name": "local ENU at the flight's mean RTK position (WGS84), metres, z up", "units": "m"},
        {
            "reconstruction": f"RC-P8 drone, {a.variant}: {len(rec.images)} photos, "
            f"{len(rec.points3D)} points",
            "reference": "GCPsandCPs_coords.xlsx (58 survey points)",
            "context": "nadir flight at 55 m over pasture and a quarry; no buildings",
        },
        elements,
        measurements,
        notes=[f"Cells of {CELL_M} m; steep where the slope exceeds {STEEP_DEG} degrees."],
    )
    out = OUT / a.variant
    out.mkdir(parents=True, exist_ok=True)
    sc.write(s, out / "scene.json")
    result = check(measurements, cps, sigma)
    (out / "check.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=1))
    cells = {
        e["id"]: e["evidence"]["cells"] if e["evidence"] else e["attributes"]["cells"]
        for e in elements
    }
    print("cells", cells, "area m2", {k: v * CELL_M**2 for k, v in cells.items()})


if __name__ == "__main__":
    main()
