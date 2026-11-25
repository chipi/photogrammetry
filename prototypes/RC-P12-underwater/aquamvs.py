"""RC-P12 refraction: board-corner distances on AquaMVS with a pinhole and a refractive model.

Each calibration's own corner detections (2-D pixels on its undistorted images, from AquaMVS's
corner transfer) are triangulated here from the rays of every camera that sees the corner:
straight rays for the pinhole calibration; for the refractive calibration, rays bent by Snell's
law at the flat water surface (z = water_z, normal and refractive indices from the calibration).
The triangulated corners are compared with the board: 12 x 9 squares of 60 mm, inner corner id
= row * 11 + column. Only held-out frames are in the corner files.
"""

import argparse
import itertools
import json
import os
from pathlib import Path

import cv2
import numpy as np

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
DATA = RECCE / "datasets/aquamvs/data"
MIN_VIEWS = 2


def undistorted_k(intr):
    """The camera matrix of AquaMVS's undistorted images (aquamvs/calibration.py,
    compute_undistortion_maps): the corner pixels live on these images, not on K's."""
    k = np.array(intr["K"], dtype=np.float64)
    dist = np.array(intr["dist_coeffs"], dtype=np.float64)
    size = tuple(intr["image_size"])
    if intr.get("is_fisheye"):
        return cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
            k, dist.reshape(4, 1), size, np.eye(3)
        )
    return cv2.getOptimalNewCameraMatrix(k, dist, size, alpha=0, newImgSize=size)[0]


def load_calibration(path):
    cal = json.loads(Path(path).read_text())
    cams = {}
    for name, c in cal["cameras"].items():
        r = np.array(c["extrinsics"]["R"])
        t = np.array(c["extrinsics"]["t"])
        cams[name] = {
            "K_inv": np.linalg.inv(undistorted_k(c["intrinsics"])),
            "R": r,
            "C": -r.T @ t,
            "water_z": c["water_z"],
        }
    return cams, cal["interface"], cal["board"]


def refract(d, normal, n1, n2):
    """Snell's law in vector form; `normal` points against the incoming ray."""
    d = d / np.linalg.norm(d)
    cos_i = -d @ normal
    eta = n1 / n2
    k = 1 - eta**2 * (1 - cos_i**2)
    return eta * d + (eta * cos_i - np.sqrt(k)) * normal


def ray(cam, pixel, interface):
    """Origin and unit direction of the ray that reaches the corner, in the world frame."""
    d = cam["R"].T @ cam["K_inv"] @ np.array([pixel[0], pixel[1], 1.0])
    d /= np.linalg.norm(d)
    n1, n2 = interface["n_air"], interface["n_water"]
    if n1 == n2:
        return cam["C"], d
    s = (cam["water_z"] - cam["C"][2]) / d[2]
    hit = cam["C"] + s * d
    normal = np.array(interface["normal"], dtype=float)
    if d @ normal > 0:
        normal = -normal
    out = refract(d, normal, n1, n2)
    return hit, out / np.linalg.norm(out)


def intersect(origins, dirs):
    """Least-squares point closest to all rays; also the RMS distance of the rays from it."""
    a = np.zeros((3, 3))
    b = np.zeros(3)
    for o, d in zip(origins, dirs, strict=True):
        p = np.eye(3) - np.outer(d, d)
        a += p
        b += p @ o
    x = np.linalg.solve(a, b)
    dist = [
        np.linalg.norm((np.eye(3) - np.outer(d, d)) @ (x - o))
        for o, d in zip(origins, dirs, strict=True)
    ]
    return x, float(np.sqrt(np.mean(np.square(dist))))


def board_xy(corner_id, board):
    per_row = board["squares_x"] - 1
    return np.array([corner_id % per_row, corner_id // per_row], dtype=float) * board["square_size"]


def umeyama_rigid(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((dst - mu_d).T @ (src - mu_s))
    s = np.diag([1, 1, np.sign(np.linalg.det(u @ vt))])
    r = u @ s @ vt
    return r, mu_d - r @ mu_s


def measure(name, calibration, corners):
    cams, interface, board = load_calibration(calibration)
    z = np.load(corners, allow_pickle=True)
    frames, cam_ids, ids, pixels = z["frame_idx"], z["camera_id"], z["corner_id"], z["pixels"]
    per_frame = []
    for f in np.unique(frames):
        pts, model, ray_rms = [], [], []
        for cid in np.unique(ids[frames == f]):
            sel = (frames == f) & (ids == cid)
            if sel.sum() < MIN_VIEWS:
                continue
            rays = [
                ray(cams[c], p, interface) for c, p in zip(cam_ids[sel], pixels[sel], strict=True)
            ]
            x, rms = intersect([o for o, _ in rays], [d for _, d in rays])
            pts.append(x)
            ray_rms.append(rms)
            model.append(np.append(board_xy(int(cid), board), 0.0))
        pts, model = np.array(pts), np.array(model)
        pairs = list(itertools.combinations(range(len(pts)), 2))
        est = np.array([np.linalg.norm(pts[i] - pts[j]) for i, j in pairs])
        true = np.array([np.linalg.norm(model[i] - model[j]) for i, j in pairs])
        adjacent = np.isclose(true, board["square_size"])
        r, t = umeyama_rigid(model, pts)
        rigid = np.linalg.norm(pts - (model @ r.T + t), axis=1)
        per_frame.append(
            {
                "frame": int(f),
                "corners": len(pts),
                "ray_rms_mm": 1000 * float(np.mean(ray_rms)),
                "scale_error_pct": 100 * float(np.median(est / true) - 1),
                "adjacent_error_mm": 1000 * float(np.mean(est[adjacent] - true[adjacent])),
                "adjacent_rms_mm": 1000
                * float(np.sqrt(np.mean((est[adjacent] - true[adjacent]) ** 2))),
                "rigid_rmse_mm": 1000 * float(np.sqrt(np.mean(rigid**2))),
            }
        )
    keys = (
        "scale_error_pct",
        "adjacent_error_mm",
        "adjacent_rms_mm",
        "rigid_rmse_mm",
        "ray_rms_mm",
    )
    summary = {k: float(np.mean([p[k] for p in per_frame])) for k in keys}
    summary["corners"] = int(sum(p["corners"] for p in per_frame))
    return {"model": name, "n_water": interface["n_water"], "summary": summary, "frames": per_frame}


# Each calibration with the corner file that was transferred through it: AquaMVS's own 3-D
# corners lie on these rays (0.0 mm median per camera); the ground-truth core's
# analysis_output.modern_refractive belongs to another refractive calibration (2-8 mm off).
RUNS = (
    (
        "pinhole",
        DATA / "runs/modern_pinhole_A/calibration.json",
        DATA / "analysis_output.modern_pinhole_A/corner_transfer/corners.npz",
    ),
    (
        "refractive",
        RECCE / "datasets/aquamvs/full/data/aquamvs_ground_truth_analysis/calibration.json",
        RECCE / "datasets/aquamvs/full/data/analysis_output/corner_transfer/corners.npz",
    ),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=RECCE / "runs/p12/aquamvs.json")
    args = ap.parse_args()
    results = [measure(*r) for r in RUNS]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=1))
    print(
        "| Model | n_water | Corners | Scale error (%) | Adjacent error (mm) | "
        "Adjacent RMS (mm) | Rigid RMSE (mm) | Ray spread (mm) |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for res in results:
        s = res["summary"]
        print(
            f"| {res['model']} | {res['n_water']} | {s['corners']} | "
            f"{s['scale_error_pct']:+.3f} | {s['adjacent_error_mm']:+.3f} | "
            f"{s['adjacent_rms_mm']:.3f} | {s['rigid_rmse_mm']:.2f} | {s['ray_rms_mm']:.2f} |"
        )
    print("\nPer frame: scale error (%) / rigid RMSE (mm)")
    print("| Frame | " + " | ".join(r["model"] for r in results) + " |")
    print("|---|" + "---|" * len(results))
    for i, f in enumerate(results[0]["frames"]):
        cells = [
            f"{r['frames'][i]['scale_error_pct']:+.2f} / {r['frames'][i]['rigid_rmse_mm']:.2f}"
            for r in results
        ]
        print(f"| {f['frame']} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
