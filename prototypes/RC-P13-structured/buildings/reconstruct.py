"""RC-P13 buildings segment, step 1: reconstruct UseGeo Dataset-1 from its photos with COLMAP.

UseGeo (FBK 3DOM and partners, CC BY-NC-SA 4.0; internal prototypes only): 224 nadir photos,
7952 x 5304, DxO-undistorted, with the dataset's interior orientation (c 4636.912 px, principal
point 3970.288, 2601.560) and an exterior orientation per photo (UTM, from the providers'
adjustment), all in a local frame (UTM minus the mean camera position).

Two ways to the cameras. `--poses given` (the default) keeps the providers' orientations and only
triangulates our matches from them, into `given/`. `--poses mapped` runs the incremental mapper
with the positions as CARTESIAN pose priors, as RC-P8 did with RTK, into `sparse/`; on this flight
it bends (camera heights spread 13.8 m against the given 4.1 m), and the README has the numbers.
Runs in RC-P1's environment (pycolmap, CPU):

    uv run --project ../../RC-P1-registration python reconstruct.py [--poses given] [--threads 16]
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pycolmap

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
DATA = RECCE / "datasets/usegeo/Dataset-1"
IMAGES = DATA / "Camera_Inputs/Metashape_outputs_images"
OUT = RECCE / "runs/p13/buildings/usegeo1"
F_PX, CX, CY = 4636.912, 3970.288, 2601.560
MAX_IMAGE_SIZE = 3200
MAX_FEATURES = 16000


def orientations():
    """Per photo: X0, Y0, Z0 (UTM), omega, phi, kappa (degrees)."""
    rows = {}
    for ln in (DATA / "Image_orientations_dataset1.xyz").read_text().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        f = ln.split()
        rows[f[0]] = [float(x) for x in f[1:7]]
    return rows


def cam_from_world(row, origin):
    """The photogrammetric orientation as COLMAP's pose. R = Rx(omega) Ry(phi) Rz(kappa) turns
    camera axes into world axes, the camera looks down its -z with image y up; COLMAP's camera looks
    down +z with y down, hence the flip of y and z. Checked against the dataset's own tie points:
    no other order or transpose reprojects them within 80 px."""
    om, ph, ka = np.radians(row[3:6])
    rx = np.array([[1, 0, 0], [0, np.cos(om), -np.sin(om)], [0, np.sin(om), np.cos(om)]])
    ry = np.array([[np.cos(ph), 0, np.sin(ph)], [0, 1, 0], [-np.sin(ph), 0, np.cos(ph)]])
    rz = np.array([[np.cos(ka), -np.sin(ka), 0], [np.sin(ka), np.cos(ka), 0], [0, 0, 1]])
    rot = np.diag([1.0, -1.0, -1.0]) @ (rx @ ry @ rz).T
    centre = np.asarray(row[:3]) - origin
    return pycolmap.Rigid3d(pycolmap.Rotation3d(rot), -rot @ centre)


def triangulate_given(db, eo, origin, a):
    """Triangulate the matches from the given poses, held fixed."""
    seed = OUT / "seed"
    if not (seed / "images.bin").exists():
        rec = pycolmap.Reconstruction()
        with pycolmap.Database.open(db) as d:
            (cam,) = d.read_all_cameras()
            rec.add_camera_with_trivial_rig(cam)
            for img in d.read_all_images():
                im = pycolmap.Image(img.name, [], cam.camera_id, img.image_id)
                rec.add_image_with_trivial_frame(im, cam_from_world(eo[img.name], origin))
        seed.mkdir(exist_ok=True)
        rec.write(str(seed))
    rec = pycolmap.Reconstruction(str(seed))
    opts = pycolmap.IncrementalPipelineOptions()
    opts.num_threads = a.threads
    # Tracks of two photos count: the overlap is 60/30 and many points are seen only twice.
    opts.triangulation.ignore_two_view_tracks = False
    # The given orientation reprojects our matches at about 5 px (median), not COLMAP's 4 px
    # default: its interior and our features disagree slightly. 40 px keeps the points; the
    # surface still agrees with the LiDAR to a median of 0.01 m.
    opts.mapper.filter_max_reproj_error = 40.0
    opts.triangulation.create_max_angle_error = 4.0
    opts.triangulation.complete_max_reproj_error = 40.0
    opts.triangulation.merge_max_reproj_error = 40.0
    given = OUT / "given"
    given.mkdir(exist_ok=True)
    rec = pycolmap.triangulate_points(rec, db, IMAGES, given, options=opts)
    rec.extract_colors_for_all_images(str(IMAGES))
    rec.write(str(given))
    return {
        "points": rec.num_points3D(),
        "reproj_px": round(rec.compute_mean_reprojection_error(), 2),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--poses", choices=["given", "mapped"], default="given")
    a = ap.parse_args()
    eo = orientations()
    names = sorted(n for n in eo if (IMAGES / n).exists())
    xyz = np.array([eo[n][:3] for n in names])
    origin = xyz.mean(0)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frame.json").write_text(
        json.dumps(
            {
                "crs": "UTM as in the dataset",
                "origin": origin.round(3).tolist(),
                "photos": len(names),
            },
            indent=1,
        )
    )
    db = OUT / "database.db"
    timings = {}
    if not db.exists():
        tmp = OUT / "database.db.partial"
        tmp.unlink(missing_ok=True)
        ext = pycolmap.FeatureExtractionOptions()
        ext.max_image_size = MAX_IMAGE_SIZE
        ext.num_threads = a.threads
        ext.sift.max_num_features = MAX_FEATURES
        t0 = time.perf_counter()
        pycolmap.extract_features(
            tmp,
            IMAGES,
            image_names=names,
            camera_mode=pycolmap.CameraMode.SINGLE,
            reader_options=pycolmap.ImageReaderOptions(
                camera_model="PINHOLE", camera_params=f"{F_PX},{F_PX},{CX},{CY}"
            ),
            extraction_options=ext,
            device=pycolmap.Device.cpu,
        )
        timings["features_s"] = round(time.perf_counter() - t0, 1)
        mo = pycolmap.FeatureMatchingOptions()
        mo.num_threads = a.threads
        t0 = time.perf_counter()
        pycolmap.match_exhaustive(tmp, matching_options=mo, device=pycolmap.Device.cpu)
        timings["matching_s"] = round(time.perf_counter() - t0, 1)
        with pycolmap.Database.open(tmp) as d:
            d.clear_pose_priors()
            for img in d.read_all_images():
                p = pycolmap.PosePrior()
                p.position = np.asarray(eo[img.name][:3]) - origin
                # The providers' adjusted positions; 5 cm stands for their accuracy.
                p.position_covariance = np.diag([0.05**2] * 3)
                p.coordinate_system = pycolmap.PosePriorCoordinateSystem.CARTESIAN
                p.corr_data_id = img.data_id
                d.write_pose_prior(p)
            (c,) = d.read_all_cameras()
            print("camera", c.model, c.params)
        tmp.rename(db)
    if a.poses == "given":
        t0 = time.perf_counter()
        res = triangulate_given(db, eo, origin, a)
        timings["triangulation_s"] = round(time.perf_counter() - t0, 1)
        print("RECONSTRUCT", json.dumps({"given": res, "timings": timings}))
        return
    inc = pycolmap.IncrementalPipelineOptions()
    inc.num_threads = a.threads
    inc.ba_refine_focal_length = False
    inc.ba_refine_principal_point = False
    inc.ba_refine_extra_params = False
    inc.use_prior_position = True
    sparse = OUT / "sparse"
    sparse.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    recons = pycolmap.incremental_mapping(db, IMAGES, sparse, inc)
    timings["mapping_s"] = round(time.perf_counter() - t0, 1)
    for i, r in recons.items():
        (sparse / str(i)).mkdir(exist_ok=True)
        r.write(str(sparse / str(i)))
    sizes = {i: len(r.images) for i, r in recons.items()}
    print("RECONSTRUCT", json.dumps({"components": sizes, "timings": timings}))


if __name__ == "__main__":
    main()
