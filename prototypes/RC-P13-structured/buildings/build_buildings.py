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


def components(mask):
    """4-connected components of a boolean grid, as lists of (i, j)."""
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
    for cells in components(mask):
        if len(cells) * CELL_M**2 < MIN_AREA_M2:
            continue
        ii, jj = np.array(cells).T
        found.append(
            {
                "cells": cells,
                "area_m2": len(cells) * CELL_M**2,
                "roof_m": float(np.nanmedian(top[ii, jj])),
                "ground_m": float(np.nanmedian(gnd[ii, jj])),
            }
        )
    return found, ndsm


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
    """Each LiDAR building to the model building it overlaps most; IoU of the cell sets."""
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
            rows.append({"lidar": r_id, "model": None, "lidar_area_m2": r["area_m2"]})
            continue
        k, inter = max(hits.items(), key=lambda kv: kv[1])
        union = len(r["cells"]) + len(model[k]["cells"]) - inter
        iou = inter / union
        used.add(k)
        rows.append(
            {
                "lidar": r_id,
                "model": k,
                "iou": round(iou, 3),
                "matched": iou >= IOU_MATCH,
                "lidar_area_m2": r["area_m2"],
                "model_area_m2": model[k]["area_m2"],
                "area_error_pct": round(
                    100 * (model[k]["area_m2"] - r["area_m2"]) / r["area_m2"], 1
                ),
                "lidar_height_m": round(r["roof_m"] - r["ground_m"], 2),
                "model_height_m": round(model[k]["roof_m"] - model[k]["ground_m"], 2),
            }
        )
    extra = [k for k in range(len(model)) if k not in used]
    return rows, extra


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
    rows, extra = match(model, ref)
    matched = [r for r in rows if r.get("matched")]

    def med(values, nd):
        return round(float(np.median(values)), nd) if values else None

    out = {
        "cell_m": CELL_M,
        "model_buildings": len(model),
        "lidar_buildings": len(ref),
        "matched": len(matched),
        "missed": sum(1 for r in rows if not r.get("matched")),
        "extra": len(extra),
        "iou_median": med([r["iou"] for r in matched], 3),
        "area_error_pct_median": med([r["area_error_pct"] for r in matched], 1),
        "height_error_m_median": med(
            [r["model_height_m"] - r["lidar_height_m"] for r in matched], 2
        ),
        "rows": rows,
    }
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
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
                sigma_basis="half a cell on the footprint's edge; roof height not calibrated",
                evidence={"cells": len(b["cells"]), "boundary_cells": nb},
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
