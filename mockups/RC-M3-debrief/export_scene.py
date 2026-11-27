"""Export ETH3D courtyard as RC-M3's data, outside git: RC-P1's COLMAP model in RC-P3's frame
(aligned to the ETH3D cameras, so metres), the regions of RC-P3's full run, photo thumbnails and
the measured products of RC-P4 and RC-P6 for the debrief agent's `get_products` tool.

Usage, from prototypes/RC-P3-quality (its uv project has pycolmap and RC-P3's alignment):
    uv run python ../../mockups/RC-M3-debrief/export_scene.py \\
        ~/.cache/recce/datasets/eth3d/courtyard ~/.cache/recce/runs ../../mockups/RC-M3-debrief/data
"""

import json
import sys
from pathlib import Path

import numpy as np
import pycolmap

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P3-quality"))
import quality

RUN = "courtyard/full"

# RC-P6's frame rates were read by the owner off the viewer's own counter (RC-P6 README); no
# file holds them, so they are copied here with their source.
VIEWER_FPS = {
    "source": "prototypes/RC-P6-viewer/README.md, owner's readings 2026-11-26",
    "scene": "courtyard: 463,017-face textured mesh and a 1,000,000-gaussian splat in one page",
    "m4_pro_chrome_fps": 59.9,
    "m4_pro_safari_fps": 58.8,
    "iphone_15_pro_fps": 50.0,
}


def products(runs: Path) -> dict:
    p4 = runs / "p4"
    mesh = json.loads((p4 / "courtyard_3000_p1/eval_mesh.json").read_text())
    dense = json.loads((p4 / "courtyard_3000_p1/eval_dense.json").read_text())
    measure = json.loads((p4 / "measure_p1.json").read_text())
    tex = json.loads((p4 / "measure_texture_courtyard_3000_p1.json").read_text())

    def at(doc, tol):
        k = doc["tolerances"].index(tol)
        return {
            "f1": round(doc["f1_scores"][k], 3),
            "accuracy": round(doc["accuracies"][k], 3),
            "completeness": round(doc["completenesses"][k], 3),
        }

    return {
        "checked_against": "ETH3D laser scan; the field has no such scan, so these numbers "
        "describe this run, not what the product can know on site",
        "dense_cloud": {
            "points": measure["cloud"]["points"],
            "at_2cm": at(dense, 0.02),
            "at_5cm": at(dense, 0.05),
            "at_10cm": at(dense, 0.1),
        },
        "mesh": {
            "faces": tex["faces_obj"],
            "at_2cm": at(mesh, 0.02),
            "at_5cm": at(mesh, 0.05),
            "at_10cm": at(mesh, 0.1),
            "closed": None,
            "closed_note": "not checked by any prototype",
        },
        "texture": {
            "texel_side_mm_median": tex["resolution"]["seen"]["texel_side_mm_p10_p50_p90"][1],
            "one_photo_area_share": tex["sources"]["one_photo_area_share"],
            "seam_delta_e_median": tex["seams"]["seam"]["delta_e76_p50_p90"][0],
            "interior_delta_e_median": tex["seams"]["interior"]["delta_e76_p50_p90"][0],
        },
        "photos": {
            "images": measure["photos"]["images"],
            "sharpness_laplacian_var_min": round(
                measure["photos"]["sharpness_laplacian_var"]["min"]
            ),
            "exposure_std_log2": round(measure["photos"]["exposure_std_log2_luminance"], 3),
        },
        "viewer": VIEWER_FPS,
    }


def main():
    scene, runs, out = (Path(a).expanduser() for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads((runs / "p3" / RUN / "quality.json").read_text())
    regions = json.loads((runs / "p3/courtyard/regions.json").read_text())
    cell = regions["cell_m"]
    by_ijk = {tuple(r["ijk"]): r["id"] for r in regions["regions"]}

    gt = pycolmap.Reconstruction(str(scene / "dslr_calibration_jpg"))
    recon = pycolmap.Reconstruction(str(runs / "p1/x3/courtyard/colmap_incremental/0"))
    sim = quality.align_to_gt(recon, quality.gt_cameras(gt))

    def place(x):
        return sim["scale"] * (sim["rot"] @ x) + sim["t"]

    cams = []
    names = {}
    for i, img in sorted(recon.images.items(), key=lambda kv: kv[1].name):
        if not img.has_pose:
            continue
        r, c = quality.world_from_cam(img)
        names[i] = Path(img.name).name
        cams.append(
            {
                "name": img.name,
                "thumb": f"thumbs/{Path(img.name).stem}.jpg",
                "centre": place(c).round(3).tolist(),
                "rotation": (sim["rot"] @ r).round(6).tolist(),
                "focal": float(img.camera.params[0]),
                "width": img.camera.width,
                "height": img.camera.height,
                "points": img.num_points3D,
            }
        )
    xyz, col, reg = [], [], []
    for p in recon.points3D.values():
        x = place(p.xyz)
        xyz.append(x)
        col.append(p.color)
        reg.append(by_ijk.get(tuple(np.floor(x / cell).astype(int)), ""))
    data = {
        "scene": "courtyard",
        "run": RUN,
        "frame": doc["frame"],
        "up": regions["up"],
        "cameras": cams,
        "points": {
            "xyz": np.array(xyz).round(3).ravel().tolist(),
            "rgb": np.array(col).astype(int).ravel().tolist(),
            "region": reg,
        },
        "regions": [
            {k: r[k] for k in ("id", "cell_centre", "centre", "coverage", "flags", "points")}
            for r in doc["regions"]
        ],
    }
    (out / "scene.json").write_text(json.dumps(data, separators=(",", ":")))
    (out / "products.json").write_text(json.dumps(products(runs), indent=1))
    thumbs = out / "thumbs"
    thumbs.mkdir(exist_ok=True)
    for img in sorted((scene / "images").rglob("*.JPG")):
        bitmap = pycolmap.Bitmap.read(str(img), as_rgb=True)
        bitmap.rescale(480, round(480 * bitmap.height / bitmap.width))
        bitmap.write(str(thumbs / f"{img.stem}.jpg"))
    print(f"{len(cams)} cameras, {len(xyz)} points, {len(data['regions'])} regions, cell {cell} m")


if __name__ == "__main__":
    main()
