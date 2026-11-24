"""RC-P3 hold-out test: withhold every image that sees one region, re-run the COLMAP incremental
mapper from the existing RC-P1 database on the remaining images, then again on all images, and
compare the region's coverage metric across the three quality.json files.

Withholding is done with the mapper's `image_names` option: the database is read, never modified.
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pycolmap
import quality as q

MIN_TARGET_POINTS = 100  # the region needs enough points for the metric to mean something
MAX_SEEING_FRACTION = 0.35  # "seen by a minority": at most this share of the images
MIN_SEEING_IMAGES = 3
DROP_REQUIRED = 0.5  # agreed 2026-11-24: coverage drops by at least half
DIVISORS = (
    10,
    15,
    20,
)  # grid cell = bbox diagonal / divisor; finer grids can make a hold-out local
RECOVERY_REQUIRED = 0.8  # "recovers": returned coverage is at least this share of the full run


def plan_target(models, gt_cams, names):
    """Pick the target from the full model alone, without remapping.

    For each grid (cell = bbox diagonal / divisor) and each candidate region, W is the set of
    images that see it. The predicted effect of withholding W: a region keeps the points that
    still have at least 2 observing images outside W. Collateral is the number of OTHER regions
    predicted to keep under half of their points. Lowest collateral wins; ties go to the smaller W,
    then to the region with more points.
    """
    main = max(models, key=lambda r: r.num_reg_images())
    sim = q.align_to_gt(main, gt_cams)
    xyz, _, _, tracks = q.extract_points(main, sim)
    up = q.up_axis(gt_cams)
    id_to_name = {i: img.name for i, img in main.images.items()}
    best, table = None, []
    for div in DIVISORS:
        regions = q.build_regions(xyz, up, divisor=div)
        cell = regions["cell_m"]
        by_cell = {}
        for k, ijk in enumerate(map(tuple, np.floor(xyz / cell).astype(int))):
            by_cell.setdefault(ijk, []).append(k)
        idx = {r["id"]: by_cell[tuple(r["ijk"])] for r in regions["regions"]}
        for r in regions["regions"]:
            obs = {}
            for k in idx[r["id"]]:
                for i in tracks[k]:
                    obs[i] = obs.get(i, 0) + 1
            w = {i for i, n in obs.items() if n >= q.SEE_MIN_OBS}
            if len(idx[r["id"]]) < MIN_TARGET_POINTS or not MIN_SEEING_IMAGES <= len(
                w
            ) <= MAX_SEEING_FRACTION * len(names):
                continue
            collateral = [
                s["id"]
                for s in regions["regions"]
                if s["id"] != r["id"]
                and np.mean([sum(i not in w for i in tracks[k]) >= 2 for k in idx[s["id"]]])
                < 1 - DROP_REQUIRED
            ]
            row = {
                "divisor": div,
                "cell_m": cell,
                "region": r["id"],
                "points": len(idx[r["id"]]),
                "withheld_images": len(w),
                "predicted_collateral": collateral,
            }
            table.append(row)
            key = (len(collateral), len(w), -len(idx[r["id"]]))
            if best is None or key < best[0]:
                best = (key, row, sorted(id_to_name[i] for i in w))
    if best is None:
        raise SystemExit("no region qualifies as a hold-out target")
    return best[1], table


def run_mapper(db, image_dir, out, names):
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    opts = pycolmap.IncrementalPipelineOptions()
    opts.image_names = list(names)
    return pycolmap.incremental_mapping(db, image_dir, out, opts)


def phase(label, scene, db, names, gt_cams, regions, out):
    models = run_mapper(db, scene / "images", out / label / "models", names)
    recons = list(models.values())
    doc = q.compute_quality(recons, names, db, gt_cams, regions, label)
    (out / label / "quality.json").write_text(json.dumps(doc, indent=2))
    return doc


def region_of(doc, rid):
    return next(r for r in doc["regions"] if r["id"] == rid)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scene", type=Path, help="ETH3D scene folder")
    ap.add_argument("p1", type=Path, help="RC-P1 output folder (database.db, colmap_incremental/)")
    ap.add_argument("out", type=Path, help="RC-P3 output folder for this scene")
    ap.add_argument("--region", help="region id to withhold (grid 1/10); default: plan_target")
    args = ap.parse_args()

    db = args.p1 / "database.db"
    names = q.scene_names(args.scene)
    gt_cams = q.gt_cameras(pycolmap.Reconstruction(str(args.scene / "dslr_calibration_jpg")))
    args.out.mkdir(parents=True, exist_ok=True)

    # Reference: RC-P1's own model gives the regions and the "full" quality.json.
    ref_dir = args.out / "full"
    ref_dir.mkdir(exist_ok=True)
    models = q.load_models(args.p1 / "colmap_incremental")
    if args.region:
        plan, table = {"divisor": 10, "region": args.region, "predicted_collateral": []}, []
    else:
        plan, table = plan_target(models, gt_cams, names)
    regions = q.make_regions(models, gt_cams, divisor=plan["divisor"])
    (args.out / "regions.json").write_text(json.dumps(regions, indent=2))
    full = q.compute_quality(models, names, db, gt_cams, regions, "full")
    (ref_dir / "quality.json").write_text(json.dumps(full, indent=2))

    target = region_of(full, plan["region"])
    rid = target["id"]
    withheld = sorted(target["images_seeing"])
    kept = [n for n in names if n not in withheld]
    print(f"{args.scene.name}: region {rid} ({target['points']} points) seen by {len(withheld)}:")
    print("  withholding", ", ".join(Path(n).name for n in withheld))

    held = phase("heldout", args.scene, db, kept, gt_cams, regions, args.out)
    back = phase("returned", args.scene, db, names, gt_cams, regions, args.out)

    c_full = region_of(full, rid)["coverage"]
    c_held = region_of(held, rid)["coverage"]
    c_back = region_of(back, rid)["coverage"]
    drop = 1 - c_held / c_full if c_full else None
    ranked = sorted(held["regions"], key=lambda r: r["coverage"])
    actual_points = [
        r["id"]
        for r in held["regions"]
        if r["id"] != rid and r["points"] < (1 - DROP_REQUIRED) * r["reference_points"]
    ]
    tied = [r["id"] for r in ranked if r["coverage"] == c_held and r["id"] != rid]
    was_registered = {i["name"] for i in full["images"] if i["verdict"] == "registered"}
    now_registered = {i["name"] for i in held["images"] if i["verdict"] == "registered"}
    extra_lost = sorted(set(kept) & was_registered - now_registered)
    weakened = [
        r["id"]
        for r in held["regions"]
        if region_of(full, r["id"])["coverage"] > 0
        and r["coverage"] <= (1 - DROP_REQUIRED) * region_of(full, r["id"])["coverage"]
    ]
    result = {
        "scene": args.scene.name,
        "region": rid,
        "region_points_full": target["points"],
        "see_min_obs": q.SEE_MIN_OBS,
        "images": len(names),
        "withheld": withheld,
        "coverage": {"full": c_full, "heldout": c_held, "returned": c_back},
        "points": {
            "full": target["points"],
            "heldout": region_of(held, rid)["points"],
            "returned": region_of(back, rid)["points"],
        },
        "drop": round(drop, 4) if drop is not None else None,
        "recovery_ratio": round(c_back / c_full, 4) if c_full else None,
        "drop_at_least_half": drop is not None and drop >= DROP_REQUIRED,
        "recovered": bool(c_full) and c_back / c_full >= RECOVERY_REQUIRED,
        "heldout_rank_by_weakest": 1 + [r["id"] for r in ranked].index(rid),
        "heldout_regions_tied_at_target_coverage": sum(r["coverage"] == c_held for r in ranked),
        "regions_total": len(ranked),
        "plan": {**plan, "candidates_considered": len(table)},
        "predicted_collateral": plan["predicted_collateral"],
        "actual_collateral_points": actual_points,
        "actual_collateral_coverage": [i for i in weakened if i != rid],
        "tied_with_target": tied,
        "tied_only_with_predicted": set(tied) <= set(plan["predicted_collateral"]),
        "unique_weakest": tied == [],
        "extra_images_lost": extra_lost,
        "heldout_registration": held["registration"],
        "returned_registration": back["registration"],
    }
    (args.out / "holdout.json").write_text(json.dumps({**result, "plan_table": table}, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "withheld"}, indent=2))


if __name__ == "__main__":
    main()
