"""RC-P9: read a capture set, triangulate a model from its exact poses, write the model and
provenance.json.

    uv run python run_p9.py <capture set> <out> [--free]

`recon.capture_set` does the reading and the pose conversion; pycolmap matches features and
triangulates with the poses held fixed. `--free` also runs a pose-free incremental model, so the
Sim(3) from its cameras to the given ones gives an independent scale.
"""

import argparse
import json
import platform
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import pycolmap

from recon import __version__ as recon_version
from recon import capture_set


def timed(record, name, fn):
    start = time.perf_counter()
    out = fn()
    record[name] = round(time.perf_counter() - start, 2)
    return out


def scale_state(cs):
    """The scale statement the result carries (RFC-0025 calls it 'the main trap')."""
    posed = [f for f in cs.frames if f.position is not None]
    if not posed:
        return {"state": "arbitrary", "reason": "no poses in the capture set"}
    sources = sorted({f.pose_source or "unstated" for f in posed})
    return {
        "state": "metric from given poses",
        "units": cs.manifest.get("units", "m"),
        "pose_sources": sources,
        "exact": sources == ["truth"],
        "poses_refined": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_set", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--free", action="store_true", help="also run a pose-free incremental map")
    args = parser.parse_args()

    started = datetime.now(UTC)
    cs = capture_set.load(args.capture_set)
    stale = capture_set.stale_image_checksums(cs)
    if stale:
        raise SystemExit(
            f"recorded sha256 differs from the file for {len(stale)} images: {stale[:3]}"
        )
    if any(f.position is None for f in cs.frames):
        raise SystemExit("this prototype needs a pose for every image")
    sensors = sorted({f.sensor for f in cs.frames})
    if len(sensors) != 1:
        raise SystemExit("this prototype handles one sensor")
    cam = cs.cameras[sensors[0]]

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    image_dir = cs.root / "images"
    names = [capture_set.colmap_name(f) for f in cs.frames]
    given = args.out / "given"

    timings = {}
    db = args.out / "database.db"
    reader = pycolmap.ImageReaderOptions()
    reader.camera_model = "PINHOLE"
    reader.camera_params = f"{cam.fx},{cam.fy},{cam.cx},{cam.cy}"
    timed(
        timings,
        "features_s",
        lambda: pycolmap.extract_features(
            db,
            image_dir,
            image_names=names,
            camera_mode=pycolmap.CameraMode.SINGLE,
            reader_options=reader,
        ),
    )
    timed(timings, "matching_s", lambda: pycolmap.match_exhaustive(db))

    # The extractor numbers images in thread order, so the given model takes the database's ids.
    with pycolmap.Database.open(db) as database:
        db_ids = {i.name: i.image_id for i in database.read_all_images()}
    n_posed = capture_set.write_colmap_text(cs, given, image_ids=db_ids)
    rec = pycolmap.Reconstruction(str(given))
    if {i.name: i.image_id for i in rec.images.values()} != db_ids:
        raise SystemExit("database image ids differ from the given model's; cannot triangulate")

    model_dir = args.out / "model"
    model_dir.mkdir()
    options = pycolmap.IncrementalPipelineOptions()
    tri = timed(
        timings,
        "triangulation_s",
        lambda: pycolmap.triangulate_points(rec, db, image_dir, model_dir, options=options),
    )
    tri.write(str(model_dir))
    tri.export_PLY(str(args.out / "cloud.ply"))

    free = None
    if args.free:
        (args.out / "free").mkdir()
        free = timed(
            timings,
            "free_mapping_s",
            lambda: pycolmap.incremental_mapping(db, image_dir, args.out / "free"),
        )

    errors = [p.error for p in tri.points3D.values()]
    finished = datetime.now(UTC)
    provenance = {
        "tool": {
            "name": "recon",
            "version": recon_version,
            "backend": {"name": "pycolmap", "version": pycolmap.__version__},
            "entry": "prototypes/RC-P9-robot-capture/run_p9.py",
        },
        "input": {
            "capture_set": str(cs.root),
            "manifest": cs.manifest["manifest"],
            "run_id": cs.manifest.get("run_id"),
            "images": len(cs.frames),
            "posed": n_posed,
            "sha256": capture_set.input_checksums(cs),
        },
        "frame": {
            "name": cs.frame_name,
            "axes": (cs.manifest.get("frame") or {}).get("axes"),
            "units": cs.manifest.get("units", "m"),
            "model_in_frame": "the given poses frame; poses fixed during triangulation",
        },
        "pose_conversion": {
            "from": vars(cs.convention),
            "to": {
                "direction": "world_to_camera",
                "camera_axes": "opencv",
                "world_up": "+z",
                "handedness": "right",
            },
            "steps": [
                "camera axes opengl->opencv (diag(1,-1,-1))",
                "camera_to_world->world_to_camera",
            ],
        },
        "scale": scale_state(cs),
        "poses": {"refined": False, "refined_poses_file": None},
        "parameters": {
            "camera_model": "PINHOLE (from cameras.json, held fixed)",
            "features": "SIFT, pycolmap defaults",
            "matching": "exhaustive with geometric verification, pycolmap defaults",
            "triangulation": "pycolmap.triangulate_points, IncrementalPipelineOptions defaults",
            "refine_intrinsics": False,
        },
        "result": {
            "model": "model/ (COLMAP binary)",
            "cloud": "cloud.ply",
            "points3D": len(errors),
            "reprojection_error_mean_px": round(sum(errors) / len(errors), 4) if errors else None,
        },
        "time": {
            "started": started.isoformat(timespec="seconds"),
            "finished": finished.isoformat(timespec="seconds"),
            "stage_s": timings,
        },
        "machine": {
            "host": platform.node(),
            "system": platform.system(),
            "arch": platform.machine(),
        },
    }
    (args.out / "provenance.json").write_text(json.dumps(provenance, indent=2))
    print(json.dumps({k: provenance[k] for k in ("scale", "result", "time")}, indent=2))
    if free is not None:
        print("free models:", {k: v.num_reg_images() for k, v in free.items()})


if __name__ == "__main__":
    main()
