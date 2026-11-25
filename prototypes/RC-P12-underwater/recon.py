"""RC-P12: ranges for SQUID Satil from our own reconstruction instead of SQUID's stereo.

  prep      the 16 resizedUndistort TIFs (8 stereo pairs) as 8-bit PNGs, left and right in
            separate folders so each side gets one shared PINHOLE camera (the TIFs are already
            undistorted); per-image contrast stretch for feature matching only
  register  SIFT, exhaustive matching, incremental mapping. Needs pycolmap, which is not in this
            environment: run it as `uv run --project ../RC-P1-registration python recon.py register`
  dense     the RC-P2 HIP container (COLMAP patch_match_stereo on the X3's GPU): run_dense.sh
  ranges    geometric depth of each right image -> range along its ray in the TIF's pixel grid;
            compared with SQUID's dist_map_r up to one scale factor (the reconstruction has no
            metric scale; the colour fits do not need one, since a scale on range folds into the
            fitted coefficients)

Everything is written under $RECCE_DATA_DIR/runs/p12/recon.
"""

import argparse
import json
import os
import struct
from pathlib import Path

import numpy as np

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
SATIL = RECCE / "datasets/squid/Satil"
WORK = RECCE / "runs/p12/recon"
SIDES = {"LFT": "left", "RGT": "right"}


def image_name(tif):
    set_no = tif.parent.name.rsplit("_", 1)[1]
    return f"s{set_no}_{tif.name[:3]}.png"


def cmd_prep(_args):
    import cv2
    import tifffile

    for tif in sorted(SATIL.glob("image_set_0*/*resizedUndistort.tif")):
        img = tifffile.imread(tif).astype(np.float64)
        lo = np.percentile(img, 1, axis=(0, 1))
        hi = np.percentile(img, 99.5, axis=(0, 1))
        v = np.clip((img - lo) / np.maximum(hi - lo, 1), 0, 1)
        out = WORK / "images" / SIDES[tif.name[:3]] / image_name(tif)
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), (v[..., ::-1] * 255).astype(np.uint8))
        print("wrote", out.relative_to(WORK), v.shape)


# Nikon D810 (35.9 mm sensor, 7360 px active) with a 35 mm lens, read from the NEFs; the
# resizedUndistort images are the RAW scaled by 2737 / 7380. This is the in-air focal length: a
# dome port keeps it, a flat port would multiply it by about 1.33. Bundle adjustment refines it.
FOCAL_PRIOR_PX = 35 / 35.9 * 7360 * 2737 / 7380
MIN_MODEL_SIZE = 2
# A lone stereo pair sees the wreck at 6-20 m over a short baseline; the default 16 degrees
# never starts a model from it.
INIT_MIN_TRI_ANGLE_DEG = 2.0


def cmd_register(_args):
    import pycolmap

    db = WORK / "database.db"
    db.unlink(missing_ok=True)
    reader = pycolmap.ImageReaderOptions()
    reader.camera_model = "SIMPLE_PINHOLE"
    reader.camera_params = f"{FOCAL_PRIOR_PX},1368.5,913.5"
    pycolmap.extract_features(
        db,
        WORK / "images",
        camera_mode=pycolmap.CameraMode.PER_FOLDER,
        reader_options=reader,
        device=pycolmap.Device.cpu,
    )
    pycolmap.match_exhaustive(db, device=pycolmap.Device.cpu)
    sparse = WORK / "sparse"
    sparse.mkdir(exist_ok=True)
    opts = pycolmap.IncrementalPipelineOptions()
    opts.min_model_size = MIN_MODEL_SIZE
    opts.multiple_models = True
    opts.mapper.init_min_tri_angle = INIT_MIN_TRI_ANGLE_DEG
    recons = pycolmap.incremental_mapping(db, WORK / "images", sparse, options=opts)
    summary = {}
    for i, r in recons.items():
        cams = {str(c): [float(v) for v in cam.params] for c, cam in r.cameras.items()}
        summary[str(i)] = {
            "images": sorted(img.name for img in r.images.values()),
            "points": r.num_points3D(),
            "reprojection_px": r.compute_mean_reprojection_error(),
            "cameras": cams,
        }
    (WORK / "register.json").write_text(json.dumps(summary, indent=1))
    print("focal prior", round(FOCAL_PRIOR_PX, 1))
    print(json.dumps(summary, indent=1))


def read_colmap_array(path):
    """COLMAP dense map: header "width&height&channels&", then float32 by channel, row, column."""
    raw = Path(path).read_bytes()
    w, h, c, rest = raw.split(b"&", 3)
    w, h, c = int(w), int(h), int(c)
    data = np.frombuffer(rest[: 4 * w * h * c], dtype=np.float32)
    return data.reshape(c, h, w).transpose(1, 2, 0).squeeze()


def read_cameras_bin(path):
    """Minimal cameras.bin reader for the PINHOLE cameras of the undistorted workspace."""
    cams = {}
    raw = Path(path).read_bytes()
    (n,) = struct.unpack_from("<Q", raw, 0)
    off = 8
    for _ in range(n):
        cam_id, model, w, h = struct.unpack_from("<iiQQ", raw, off)
        off += 24
        if model != 1:
            raise ValueError(f"camera {cam_id}: model {model}, expected PINHOLE (1)")
        params = struct.unpack_from("<4d", raw, off)
        off += 32
        cams[cam_id] = {"w": w, "h": h, "params": params}
    return cams


def read_images_bin(path):
    """name -> camera id, from images.bin (pose and 2-D points skipped)."""
    out = {}
    raw = Path(path).read_bytes()
    (n,) = struct.unpack_from("<Q", raw, 0)
    off = 8
    for _ in range(n):
        off += 4 + 7 * 8
        (cam_id,) = struct.unpack_from("<i", raw, off)
        off += 4
        end = raw.index(b"\0", off)
        name = raw[off:end].decode()
        off = end + 1
        (npts,) = struct.unpack_from("<Q", raw, off)
        off += 8 + npts * 24
        out[name] = cam_id
    return out


def cmd_ranges(_args):
    import scipy.io
    import scipy.ndimage as ndi

    found = {}
    for ws in sorted(WORK.glob("dense_*/dense")):
        cams = read_cameras_bin(ws / "sparse/cameras.bin")
        for name, cam_id in read_images_bin(ws / "sparse/images.bin").items():
            found[name] = (ws, cams[cam_id])
    out_dir = WORK / "ranges"
    out_dir.mkdir(exist_ok=True)
    report = {}
    for set_dir in sorted(SATIL.glob("image_set_0*")):
        name = f"right/s{set_dir.name.rsplit('_', 1)[1]}_RGT.png"
        if name not in found:
            report[set_dir.name] = {"registered": False}
            continue
        ws, cam = found[name]
        dm_path = ws / "stereo/depth_maps" / f"{name}.geometric.bin"
        if not dm_path.exists():
            report[set_dir.name] = {"registered": True, "depth_map": False}
            continue
        depth = read_colmap_array(dm_path)
        fx, fy, cx, cy = cam["params"]
        h, w = depth.shape
        yy, xx = np.mgrid[0:h, 0:w]
        ray_len = np.sqrt(((xx - cx) / fx) ** 2 + ((yy - cy) / fy) ** 2 + 1)
        rng = np.where(depth > 0, depth * ray_len, np.nan)
        squid = scipy.io.loadmat(set_dir / "distanceFromCamera.mat")["dist_map_r"]
        if rng.shape != squid.shape:
            rng = ndi.zoom(rng, (squid.shape[0] / h, squid.shape[1] / w), order=0)
        both = np.isfinite(rng) & np.isfinite(squid) & (squid > 0)
        scale = float(np.median(squid[both] / rng[both]))
        rel = np.abs(rng[both] * scale - squid[both]) / squid[both]
        np.save(out_dir / f"{set_dir.name}_range_r.npy", (rng * scale).astype(np.float32))
        report[set_dir.name] = {
            "registered": True,
            "model": ws.parent.name,
            "depth_px": int(np.isfinite(rng).sum()),
            "overlap_px": int(both.sum()),
            "scale_to_squid": scale,
            "median_rel_diff_pct": 100 * float(np.median(rel)),
            "p90_rel_diff_pct": 100 * float(np.percentile(rel, 90)),
        }
    (WORK / "ranges.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prep", "register", "ranges"])
    args = ap.parse_args()
    {"prep": cmd_prep, "register": cmd_register, "ranges": cmd_ranges}[args.command](args)


if __name__ == "__main__":
    main()
