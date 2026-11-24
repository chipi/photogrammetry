"""Export a PG-P1 run (both strategies) and its photos as the mock-up's data, outside git.

Usage, from prototypes/PG-P1-registration (its uv project has pycolmap):
    uv run python ../../mockups/PG-M1-run/export_run.py <scene_dir> <run_dir> <mockup_data_dir>
"""

import json
import sys
from pathlib import Path

import numpy as np
import pycolmap


def pose(image):
    cfw = image.cam_from_world() if callable(image.cam_from_world) else image.cam_from_world
    wfc = cfw.inverse()
    return wfc.rotation.matrix(), np.asarray(wfc.translation)


def up_rotation(rotations):
    """Rotate the world so the cameras' mean up (-y in camera) points along +Y."""
    up = -np.mean([r[:, 1] for r in rotations], axis=0)
    up /= np.linalg.norm(up)
    target = np.array([0.0, 1.0, 0.0])
    v, c = np.cross(up, target), float(up @ target)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


def derived_order(images, tracks):
    """Order images the way an incremental mapper would plausibly add them: the best pair
    first, then the image sharing most points with those already in. Not the logged order."""
    seen = {i: set() for i in images}
    for pid, ids in tracks.items():
        for i in ids:
            seen[i].add(pid)
    ids = list(images)
    best = max(
        ((a, b) for a in ids for b in ids if a < b), key=lambda p: len(seen[p[0]] & seen[p[1]])
    )
    order, covered = list(best), seen[best[0]] | seen[best[1]]
    while len(order) < len(ids):
        nxt = max((i for i in ids if i not in order), key=lambda i: len(seen[i] & covered))
        order.append(nxt)
        covered |= seen[nxt]
    return order


def export(recon, gt):
    images = {i: img for i, img in recon.images.items() if img.has_pose}
    poses = {i: pose(img) for i, img in images.items()}
    rot_up = up_rotation([r for r, _ in poses.values()])
    pts = {pid: p for pid, p in recon.points3D.items()}
    xyz = np.array([p.xyz for p in pts.values()]) @ rot_up.T
    centre = np.median(xyz, axis=0)
    spread = np.percentile(np.linalg.norm(xyz - centre, axis=1), 90)
    scale = 4.0 / spread

    def place(x):
        return ((rot_up @ x - centre) * scale).round(4).tolist()

    tracks = {pid: sorted({el.image_id for el in p.track.elements}) for pid, p in pts.items()}
    order = derived_order(images, tracks)
    index = {img_id: k for k, img_id in enumerate(order)}

    cams = []
    for img_id in order:
        img = images[img_id]
        r, c = poses[img_id]
        cam = img.camera
        cams.append(
            {
                "name": Path(img.name).name,
                "center": place(c),
                "rotation": (rot_up @ r).round(6).tolist(),
                "focal": float(cam.params[0]),
                "width": cam.width,
                "height": cam.height,
                "points": img.num_points3D,
            }
        )
    points = [
        {
            "p": place(p.xyz),
            "c": [int(v) for v in p.color],
            "e": round(float(p.error), 3),
            "t": sorted(index[i] for i in tracks[pid] if i in index),
        }
        for pid, p in pts.items()
    ]

    gt_by_name = {Path(img.name).name: img for img in gt.images.values()}
    est_c, gt_c = [], []
    for cam in cams:
        ref = gt_by_name.get(cam["name"])
        if ref is not None and cam["points"] > 0:
            est_c.append(cam["center"])
            gt_c.append(pose(ref)[1])
    est_c, gt_c = np.array(est_c), np.array(gt_c)
    # Ground truth into the estimate's display frame: similarity from gt to estimate.
    mu_g, mu_e = gt_c.mean(0), est_c.mean(0)
    u, d, vt = np.linalg.svd((est_c - mu_e).T @ (gt_c - mu_g) / len(gt_c))
    sign = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[2, 2] = -1
    rot = u @ sign @ vt
    s = np.trace(np.diag(d) @ sign) / (gt_c - mu_g).var(0).sum()
    # Cameras without points are left out of the alignment but still drawn against the truth.
    names = [c["name"] for c in cams if c["name"] in gt_by_name]
    all_gt = np.array([pose(gt_by_name[n])[1] for n in names])
    gt_display = (s * (rot @ (all_gt - mu_g).T)).T + mu_e
    return {
        "metres_per_unit": round(float(1 / s), 5),
        "cameras": cams,
        "points": points,
        "truth": {n: g.round(4).tolist() for n, g in zip(names, gt_display, strict=True)},
    }


def main():
    scene, run, out = (Path(a).expanduser() for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    gt = pycolmap.Reconstruction(str(scene / "dslr_calibration_jpg"))
    results = json.loads((run / "results.json").read_text())
    data = {"scene": scene.name, "results": results, "strategies": {}}
    for name in results["strategies"]:
        recon = pycolmap.Reconstruction(str(run / name / "0"))
        data["strategies"][name] = export(recon, gt)
    (out / "run.json").write_text(json.dumps(data, separators=(",", ":")))
    thumbs = out / "thumbs"
    thumbs.mkdir(exist_ok=True)
    for img in sorted((scene / "images").rglob("*.JPG")):
        bitmap = pycolmap.Bitmap.read(str(img), as_rgb=True)
        bitmap.rescale(480, round(480 * bitmap.height / bitmap.width))
        bitmap.write(str(thumbs / f"{img.stem}.jpg"))
    print(f"wrote {out / 'run.json'} and {len(list(thumbs.iterdir()))} thumbnails")


if __name__ == "__main__":
    main()
