"""RC-P13 buildings segment, step 2: a reconstruction of UseGeo Dataset-1 to terrain and building
footprints, then the same footprints derived from the dataset's LiDAR, compared building by
building.

The structure is a city model's at its simplest level (CityGML LOD1): terrain cells, and each
building as a footprint extruded to one roof height. A building is a connected group of cells
standing more than 2.5 m above the estimated ground, not green (the photos' colour) and covering at
least 20 m2. The LiDAR goes through the same rule, with its vegetation class in place of colour.

Runs in RC-P1's environment (pycolmap):

    uv run --project ../../RC-P1-registration python build_buildings.py

Inputs: `reconstruct.py`'s model (`given/` by default); the LiDAR as `lidar_xyz.npy` /
`lidar_class.npy` in the same local frame (converted from the LAS with laspy in a throwaway
container).
"""

import argparse
import itertools
import json
import os
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pycolmap

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "RC-P6-viewer"))
import scene as sc  # noqa: E402
from p6_io import read_ply  # noqa: E402

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
RUN = RECCE / "runs/p13/buildings/usegeo1"
DATA = RECCE / "datasets/usegeo/Dataset-1"
CELL_M = 1.0
MIN_POINTS = 2
GROUND_WINDOW_M = 30.0  # wider than any building here, so its minimum is ground
MIN_HEIGHT_M = 2.5
MIN_AREA_M2 = 20.0
EXG_GREEN = 0.06  # excess green (2g - r - b, colours in 0..1) above this is vegetation
VEG_CLASS = 4
VEG_SHARE = 0.3  # a LiDAR cell with more vegetation-class points than this is vegetation
# The LiDAR's vegetation class leaves many trees out. A tree canopy spreads the LiDAR heights within
# a cell (median 3.5 m here), a roof does not (0.25 m) except at its edge, where the wall falls
# inside the cell. A cell is vegetation when it and all eight neighbours spread more than this.
ROUGH_M = 1.0
FOOTPRINT_M = 40.0
IOU_MATCH = 0.3
# Neighbouring roof cells further apart in height than this belong to different buildings, so a
# terrace of houses at different heights splits. Set on this site (1.5 m of 0.6, 1.0, 1.5 tried).
ROOF_STEP_M = 1.5
# The tolerance, fixed in the README before the OpenStreetMap check ran.
TOL_MIN_AREA_M2 = 100.0
TOL_IOU = 0.5
TOL_DETECTED = 0.8
OSM_IN_VIEW = 0.9  # an OSM building is compared when this share of it lies where the photos see


def grid_stats(xy, z, lo, shape, extra=None, spread=False):
    """Per cell: point count, the 90th-percentile height (the surface) and, if given, the mean of
    `extra` per point. With `spread`, also the 90th minus the 10th percentile height."""
    nx, ny = shape
    ij = np.floor((xy - lo) / CELL_M).astype(np.int64)
    ok = (ij >= 0).all(1) & (ij[:, 0] < nx) & (ij[:, 1] < ny)
    flat = ij[ok, 0] * ny + ij[ok, 1]
    z = z[ok]
    order = np.lexsort((z, flat))
    flat, z = flat[order], z[order]
    counts = np.bincount(flat, minlength=nx * ny)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    top = np.full(nx * ny, np.nan)
    has = counts >= MIN_POINTS
    idx = starts[has] + np.floor(0.9 * (counts[has] - 1)).astype(np.int64)
    top[has] = z[idx]
    if spread:
        low = np.full(nx * ny, np.nan)
        low[has] = z[starts[has] + np.floor(0.1 * (counts[has] - 1)).astype(np.int64)]
        spread_out = (top - low).reshape(shape)
    mean_extra = None
    if extra is not None:
        e = extra[ok][order]
        sums = np.bincount(flat, weights=e, minlength=nx * ny)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_extra = (sums / counts).reshape(shape)
    if spread:
        return counts.reshape(shape), top.reshape(shape), mean_extra, spread_out
    return counts.reshape(shape), top.reshape(shape), mean_extra


def min_filter(h, radius):
    """Grey erosion with a square window of half-width `radius` cells, NaN ignored."""
    out = np.where(np.isnan(h), np.inf, h)
    for axis in (0, 1):
        pad = np.pad(out, [(radius, radius) if a == axis else (0, 0) for a in (0, 1)],
                     constant_values=np.inf)  # fmt: skip
        acc = np.full_like(out, np.inf)
        for k in range(2 * radius + 1):
            sl = [slice(None), slice(None)]
            sl[axis] = slice(k, k + out.shape[axis])
            acc = np.minimum(acc, pad[tuple(sl)])
        out = acc
    return np.where(np.isinf(out), np.nan, out)


def max_filter(h, radius):
    return -min_filter(-h, radius)


def median3(h):
    """3 x 3 median, NaN ignored: single cells far off their neighbours (stray points under the
    surface in the photo model) would otherwise become the window minimum in `ground`."""
    pad = np.pad(h, 1, constant_values=np.nan)
    stack = [pad[1 + di : 1 + di + h.shape[0], 1 + dj : 1 + dj + h.shape[1]]
             for di in (-1, 0, 1) for dj in (-1, 0, 1)]  # fmt: skip
    with np.errstate(all="ignore"):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            out = np.nanmedian(np.stack(stack), axis=0)
    return np.where(np.isnan(h), np.nan, out)


def ground(top):
    """Morphological opening of the surface: erosion then dilation over a window wider than any
    building leaves the ground under it."""
    r = int(GROUND_WINDOW_M / CELL_M / 2)
    return max_filter(min_filter(median3(top), r), r)


def tidy(mask, close=1):
    """Close gaps of up to 2 x `close` cells (roof cells without a point), then open away
    one-cell specks."""
    f = mask.astype(float)
    f = min_filter(max_filter(f, close), close)
    f = max_filter(min_filter(f, 1), 1)
    return np.nan_to_num(f) > 0.5


def components(mask, h=None, step=None):
    """4-connected components of a boolean grid, as lists of (i, j). With heights `h`, neighbours
    more than `step` apart in height are not connected."""
    seen = np.zeros_like(mask)
    out = []
    for i0, j0 in zip(*np.nonzero(mask), strict=True):
        if seen[i0, j0]:
            continue
        q, cells = deque([(i0, j0)]), []
        seen[i0, j0] = True
        while q:
            i, j = q.popleft()
            cells.append((int(i), int(j)))
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if (
                    0 <= a < mask.shape[0]
                    and 0 <= b < mask.shape[1]
                    and mask[a, b]
                    and not seen[a, b]
                    and (h is None or not abs(h[a, b] - h[i, j]) > step)
                ):
                    seen[a, b] = True
                    q.append((a, b))
        out.append(cells)
    return out


def buildings(top, gnd, not_veg, inside=None):
    ndsm = median3(top) - gnd
    mask = tidy((ndsm > MIN_HEIGHT_M) & not_veg)
    if inside is not None:
        mask &= inside
    found = []
    for cells in components(mask, ndsm + gnd, ROOF_STEP_M):
        if len(cells) * CELL_M**2 < MIN_AREA_M2:
            continue
        found.append(prism(cells, top, gnd))
    return found, ndsm


def prism(cells, top, gnd):
    """One LOD1 building. Its roof is the median cell height; the roof's sigma is how far a single
    height stands for the cells (1.4826 x their median absolute deviation)."""
    ii, jj = np.array(cells).T
    z = top[ii, jj]
    roof = float(np.nanmedian(z))
    return {
        "cells": cells,
        "area_m2": len(cells) * CELL_M**2,
        "roof_m": roof,
        "roof_sigma_m": float(1.4826 * np.nanmedian(np.abs(z - roof))),
        "ground_m": float(np.nanmedian(gnd[ii, jj])),
    }


def polygon_cells(xy, lo, shape):
    """Grid cells whose centre lies inside a closed outline (even-odd rule)."""
    xy = np.asarray(xy, float)
    i0, j0 = np.floor((xy.min(0) - lo) / CELL_M).astype(int)
    i1, j1 = np.ceil((xy.max(0) - lo) / CELL_M).astype(int)
    a0, a1, b0, b1 = max(i0, 0), min(i1, shape[0]), max(j0, 0), min(j1, shape[1])
    if a1 <= a0 or b1 <= b0:
        return []
    ii, jj = np.mgrid[a0:a1, b0:b1]
    px, py = lo[0] + (ii + 0.5) * CELL_M, lo[1] + (jj + 0.5) * CELL_M
    inside = np.zeros(ii.shape, bool)
    for (xa, ya), (xb, yb) in itertools.pairwise(xy):
        if ya == yb:
            continue
        inside ^= ((ya > py) != (yb > py)) & (px < (xb - xa) * (py - ya) / (yb - ya) + xa)
    return [(int(i), int(j)) for i, j in zip(ii[inside], jj[inside], strict=True)]


def osm_reference(lo, shape, covered, ltop, lgnd):
    """OpenStreetMap's footprints (fetch_osm.py) as reference buildings, heights from the LiDAR.
    Only buildings almost wholly inside the photos' view are compared."""
    path = RUN / "osm_buildings.json"
    if not path.exists():
        return None, 0
    found, skipped = [], 0
    for b in json.loads(path.read_text()):
        cells = polygon_cells(b["xy"], lo, shape)
        seen = [c for c in cells if covered[c]]
        if not cells or len(seen) < OSM_IN_VIEW * len(cells):
            skipped += 1
            continue
        found.append(prism(seen, ltop, lgnd) | {"osm_id": b["id"]})
    return found, skipped


def verdict(rows, model):
    """The README's tolerance on reference buildings of 100 m2 or more."""
    big = [r for r in rows if r["ref_area_m2"] >= TOL_MIN_AREA_M2]
    passed = [r for r in big if r.get("iou", 0) >= TOL_IOU]
    area_ok = height_ok = 0
    for r in passed:
        b = model[r["model"]]
        sigma_area = boundary_cells(b["cells"]) * CELL_M * CELL_M / 2
        area_ok += abs(r["model_area_m2"] - r["ref_area_m2"]) <= 2 * sigma_area
        height_ok += abs(r["model_height_m"] - r["ref_height_m"]) <= 2 * b["roof_sigma_m"]
    detected = len(passed) / len(big) if big else 0.0
    return {
        "reference_buildings": len(big),
        "passed_iou": len(passed),
        "detected_share": round(detected, 3),
        "area_within_2sigma": area_ok,
        "height_within_2sigma": height_ok,
        "met": bool(
            big and detected >= TOL_DETECTED and area_ok == len(passed) and height_ok == len(passed)
        ),
    }


def label(found, shape):
    """Building number per cell, -1 elsewhere."""
    out = np.full(shape, -1, np.int32)
    for k, b in enumerate(found):
        out[tuple(np.array(b["cells"]).T)] = k
    return out


def boundary_cells(cells):
    s = set(cells)
    return sum(any((i + di, j + dj) not in s for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
               for i, j in cells)  # fmt: skip


def match(model, ref):
    """Each reference building to the model building it overlaps most; IoU of the cell sets."""
    owner = {}
    for k, b in enumerate(model):
        for c in b["cells"]:
            owner[c] = k
    rows, used = [], set()
    for r_id, r in enumerate(ref):
        hits = {}
        for c in r["cells"]:
            if c in owner:
                hits[owner[c]] = hits.get(owner[c], 0) + 1
        if not hits:
            rows.append({"ref": r_id, "model": None, "ref_area_m2": r["area_m2"]})
            continue
        k, inter = max(hits.items(), key=lambda kv: kv[1])
        union = len(r["cells"]) + len(model[k]["cells"]) - inter
        iou = inter / union
        used.add(k)
        rows.append(
            {
                "ref": r_id,
                "model": k,
                "iou": round(iou, 3),
                "matched": iou >= IOU_MATCH,
                "ref_area_m2": r["area_m2"],
                "model_area_m2": model[k]["area_m2"],
                "area_error_pct": round(
                    100 * (model[k]["area_m2"] - r["area_m2"]) / r["area_m2"], 1
                ),
                "ref_height_m": round(r["roof_m"] - r["ground_m"], 2),
                "model_height_m": round(model[k]["roof_m"] - model[k]["ground_m"], 2),
            }
        )
    extra = [k for k in range(len(model)) if k not in used]
    return rows, extra


def summary(model, ref):
    rows, extra = match(model, ref)
    matched = [r for r in rows if r.get("matched")]

    def med(values, nd):
        return round(float(np.median(values)), nd) if values else None

    return {
        "reference_buildings": len(ref),
        "matched": len(matched),
        "missed": sum(1 for r in rows if not r.get("matched")),
        "extra": len(extra),
        "iou_median": med([r["iou"] for r in matched], 3),
        "area_error_pct_median": med([r["area_error_pct"] for r in matched], 1),
        "height_error_m_median": med([r["model_height_m"] - r["ref_height_m"] for r in matched], 2),
        "tolerance": verdict(rows, model),
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="given", help="a model folder in the run: given, sparse/0")
    ap.add_argument(
        "--points", choices=["dense", "sparse"], default="dense",
        help="dense: run_dense.sh's fused cloud from that model; sparse: the model's own points",
    )  # fmt: skip
    a = ap.parse_args()
    rec = pycolmap.Reconstruction(str(RUN / a.model))
    if a.points == "dense":
        v, _ = read_ply(RUN / "dense/dense/fused.ply", mmap=False)
        xyz = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float64)
        rgb = np.stack([v["red"], v["green"], v["blue"]], 1).astype(float) / 255.0
    else:
        pts = list(rec.points3D.values())
        xyz = np.array([p.xyz for p in pts])
        rgb = np.array([p.color for p in pts], float) / 255.0
    n_points = len(xyz)
    exg = 2 * rgb[:, 1] - rgb[:, 0] - rgb[:, 2]
    cams = np.array([im.projection_center() for im in rec.images.values()])
    lo = np.floor(cams[:, :2].min(0) - FOOTPRINT_M)
    hi = np.ceil(cams[:, :2].max(0) + FOOTPRINT_M)
    shape = tuple(((hi - lo) / CELL_M).astype(int))
    counts, top, green = grid_stats(xyz[:, :2], xyz[:, 2], lo, shape, exg)
    gnd = ground(top)
    # Compare only where the photos give a surface: cells with points, gaps up to 5 m closed.
    covered = (
        np.nan_to_num(min_filter(max_filter((counts >= MIN_POINTS).astype(float), 5), 5)) > 0.5
    )
    model, _ = buildings(top, gnd, ~(green > EXG_GREEN), covered)

    lx = np.load(DATA / "lidar_xyz.npy", mmap_mode="r")
    lc = np.load(DATA / "lidar_class.npy", mmap_mode="r")
    sel = (lx[:, 0] >= lo[0]) & (lx[:, 0] < hi[0]) & (lx[:, 1] >= lo[1]) & (lx[:, 1] < hi[1])
    lxy, lz, lveg = (
        np.asarray(lx[sel, :2]),
        np.asarray(lx[sel, 2]),
        (np.asarray(lc[sel]) == VEG_CLASS),
    )
    # Outliers in the LAS reach -225 m and +215 m around a site near 190 m.
    keep = np.abs(lz - np.median(lz)) < 80
    lcounts, ltop, lvegshare, lspread = grid_stats(
        lxy[keep], lz[keep], lo, shape, lveg[keep].astype(float), spread=True
    )
    lgnd = ground(ltop)
    canopy = min_filter(lspread, 1) > ROUGH_M
    ref, _ = buildings(ltop, lgnd, ~(lvegshare > VEG_SHARE) & ~canopy, covered)

    seen = counts >= MIN_POINTS
    n_lidar = int(np.sum(lcounts >= MIN_POINTS))
    print(f"grid {shape} at {CELL_M} m; model cells seen {seen.sum()}, LiDAR cells {n_lidar}, "
          f"compared {covered.sum()}")  # fmt: skip
    print(f"ground, model - LiDAR: median {np.nanmedian(gnd - lgnd):+.2f} m")
    print(f"buildings: model {len(model)}, LiDAR {len(ref)}")
    out = {"cell_m": CELL_M, "model_buildings": len(model), "lidar": summary(model, ref)}
    osm, skipped = osm_reference(lo, shape, covered, ltop, lgnd)
    if osm is not None:
        out["osm"] = summary(model, osm) | {"partly_out_of_view": skipped}
    for k in ("lidar", "osm"):
        if k in out:
            print(k, json.dumps({x: v for x, v in out[k].items() if x != "rows"}))
    (RUN / "check.json").write_text(json.dumps(out, indent=1))
    np.savez_compressed(
        RUN / "grids.npz", top=top, gnd=gnd, ltop=ltop, lgnd=lgnd, lo=lo, counts=counts,
        model_id=label(model, shape), lidar_id=label(ref, shape), covered=covered,
    )  # fmt: skip
    write_scene(model, top, gnd, seen, lo, f"{a.model}, {a.points} points", rec, n_points)


def write_scene(model, top, gnd, seen, lo, model_dir, rec, n_points):
    sigma_cell = CELL_M / 2
    elements = []
    terrain = seen.copy()
    for b in model:
        for i, j in b["cells"]:
            terrain[i, j] = False
    h = np.where(terrain, gnd, np.nan)
    elements.append(
        sc.element(
            "terrain",
            "terrain",
            "inferred",
            {
                "type": "height_grid",
                "origin": lo.tolist(),
                "cell_m": CELL_M,
                "shape": list(h.shape),
                "heights_m": [
                    [None if np.isnan(v) else round(float(v), 2) for v in row] for row in h
                ],
            },
            rule=f"ground by a {GROUND_WINDOW_M:.0f} m morphological opening of the surface",
        )
    )
    measurements = []
    for k, b in enumerate(model):
        bid = f"building-{k}"
        nb = boundary_cells(b["cells"])
        elements.append(
            sc.element(
                bid,
                "building",
                "measured",
                {
                    "type": "prism",
                    "origin": lo.tolist(),
                    "cell_m": CELL_M,
                    "cells": b["cells"],
                    "z0": round(b["ground_m"], 2),
                    "z1": round(b["roof_m"], 2),
                },
                sigma_m=sigma_cell,
                sigma_basis="half a cell on the footprint edge; the roof spread is in evidence",
                evidence={
                    "cells": len(b["cells"]),
                    "boundary_cells": nb,
                    "roof_sigma_m": round(b["roof_sigma_m"], 2),
                },
            )
        )
        measurements.append(
            sc.measurement(
                f"area-{k}",
                [bid],
                b["area_m2"],
                "measured",
                sigma_m=round(nb * CELL_M * sigma_cell, 1),
                sigma_basis="boundary cells x cell edge x half a cell, in m2",
                evidence={"cells": len(b["cells"])},
            )
        )
    s = sc.scene(
        "buildings",
        {"name": "UTM minus the mean camera position (frame.json), metres, z up", "units": "m"},
        {
            "reconstruction": f"UseGeo Dataset-1, model {model_dir}: {len(rec.images)} photos, "
            f"{n_points} points",
            "reference": "LiDAR_dataset1.las, through the same footprint rule",
            "context": "nadir flight over the edge of a town: houses, roads, fields",
        },
        elements,
        measurements,
    )
    sc.write(s, RUN / "scene.json")


if __name__ == "__main__":
    main()
