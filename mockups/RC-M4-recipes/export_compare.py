"""Export RC-M4's data, outside git: for each scene, both RC-P1 recipes (COLMAP incremental and
GLOMAP global, from the same matches) in ETH3D's ground-truth frame, so one camera view shows
both; per camera its distance from the truth; the measured cost of each stage and the estimate
made before the run.

Usage, from prototypes/RC-P1-registration (its uv project has pycolmap):
    uv run python ../../mockups/RC-M4-recipes/export_compare.py \\
        ~/.cache/recce/datasets/eth3d ~/.cache/recce/runs/m4/x3 ../../mockups/RC-M4-recipes/data
"""

import json
import sys
from pathlib import Path

import numpy as np
import pycolmap

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P1-registration"))
import run_p1

SCENES = ["kicker", "courtyard"]
RECIPES = ["colmap_incremental", "glomap_global"]


def export_recipe(recon, gt_centre):
    cams = {img.name: run_p1.world_from_cam(img) for img in recon.images.values() if img.has_pose}
    points_of = {img.name: img.num_points3D for img in recon.images.values() if img.has_pose}
    names = [n for n in cams if points_of[n] > 0 and n in gt_centre]
    src = np.array([cams[n][1] for n in names])
    dst = np.array([gt_centre[n] for n in names])
    s, rot, t = run_p1.umeyama(src, dst)

    def place(x):
        return s * (rot @ x) + t

    out = []
    for n, (r, c) in sorted(cams.items()):
        p = place(c)
        out.append(
            {
                "name": n,
                "centre": p.round(3).tolist(),
                "rotation": (rot @ r).round(5).tolist(),
                "points": points_of[n],
                "error_m": round(float(np.linalg.norm(p - gt_centre[n])), 3)
                if n in gt_centre
                else None,
            }
        )
    xyz = np.array([place(p.xyz) for p in recon.points3D.values()])
    return {
        "cameras": out,
        "points": {
            "xyz": xyz.round(3).ravel().tolist(),
            "rgb": np.array([p.color for p in recon.points3D.values()])
            .astype(int)
            .ravel()
            .tolist(),
            "error_px": [round(float(p.error), 2) for p in recon.points3D.values()],
        },
    }


def main():
    datasets, runs, out = (Path(a).expanduser() for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    meta = {"scenes": {}}
    for scene in SCENES:
        gt = pycolmap.Reconstruction(str(datasets / scene / "dslr_calibration_jpg"))
        gt_centre = {img.name: run_p1.world_from_cam(img)[1] for img in gt.images.values()}
        run = runs / scene
        results = json.loads((run / "results.json").read_text())
        data = {"recipes": {}}
        for recipe in RECIPES:
            recon = pycolmap.Reconstruction(str(run / recipe / "0"))
            data["recipes"][recipe] = export_recipe(recon, gt_centre)
        data["truth"] = {n: c.round(3).tolist() for n, c in sorted(gt_centre.items())}
        (out / f"{scene}.json").write_text(json.dumps(data, separators=(",", ":")))
        est = runs / "estimates" / f"{scene}_before.json"
        meta["scenes"][scene] = {
            "images": results["images"],
            "results": results,
            "cost": json.loads((run / "cost.json").read_text()),
            "estimate": json.loads(est.read_text()) if est.is_file() else None,
        }
        thumbs = out / "thumbs" / scene
        thumbs.mkdir(parents=True, exist_ok=True)
        for img in sorted((datasets / scene / "images").rglob("*.JPG")):
            bitmap = pycolmap.Bitmap.read(str(img), as_rgb=True)
            bitmap.rescale(480, round(480 * bitmap.height / bitmap.width))
            bitmap.write(str(thumbs / f"{img.stem}.jpg"))
        print(scene, {r: len(d["cameras"]) for r, d in data["recipes"].items()})
    for machine in ("x3", "m4pro", "gb10"):
        p1 = runs.parents[1] / "p1" / machine
        meta.setdefault("rc_p1", {})[machine] = {
            s: json.loads((p1 / s / "results.json").read_text())
            for s in ("pipes", "kicker", "courtyard")
            if (p1 / s / "results.json").is_file()
        }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
