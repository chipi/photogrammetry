"""RC-P2, GB10 half: COLMAP dense depth through CUDA, from an RC-P1 sparse model.

Usage: run_dense.py <scene folder> <p1 run folder> <output folder> [--max-image-size N]
"""

import argparse
import json
import time
from pathlib import Path

import pycolmap


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", type=Path)
    ap.add_argument("p1_run", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-image-size", type=int, default=2000)
    args = ap.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    ws = out / "dense"
    res: dict = {
        "scene": args.scene.name,
        "pycolmap": pycolmap.__version__,
        "has_cuda": pycolmap.has_cuda,
        "max_image_size": args.max_image_size,
        "stage_seconds": {},
    }

    def stage(name: str, fn):
        t = time.time()
        r = fn()
        res["stage_seconds"][name] = round(time.time() - t, 1)
        print(f"STAGE {name} {res['stage_seconds'][name]} s", flush=True)
        (out / "results.json").write_text(json.dumps(res, indent=2))
        return r

    stage(
        "undistort",
        lambda: pycolmap.undistort_images(
            ws,
            args.p1_run / "colmap_incremental" / "0",
            args.scene / "images",
            undistort_options=pycolmap.UndistortCameraOptions(max_image_size=args.max_image_size),
        ),
    )
    res["undistorted_images"] = len([p for p in (ws / "images").rglob("*") if p.is_file()])

    opts = pycolmap.PatchMatchOptions()
    opts.max_image_size = args.max_image_size
    res["patch_match_options"] = {
        "max_image_size": opts.max_image_size,
        "num_iterations": opts.num_iterations,
        "window_radius": opts.window_radius,
        "geom_consistency": opts.geom_consistency,
        "gpu_index": opts.gpu_index,
    }
    # With geom_consistency on (the default) COLMAP runs a photometric pass, then a geometric one.
    stage("patch_match_stereo", lambda: pycolmap.patch_match_stereo(ws, options=opts))
    res["depth_maps"] = {
        k: len(list((ws / "stereo" / "depth_maps").glob(f"*.{k}.bin")))
        for k in ("photometric", "geometric")
    }

    rec = stage(
        "stereo_fusion",
        lambda: pycolmap.stereo_fusion(ws / "fused.ply", ws, output_type="PLY"),
    )
    res["fused_points"] = rec.num_points3D() if hasattr(rec, "num_points3D") else None
    ply = ws / "fused.ply"
    if ply.exists():
        with ply.open("rb") as f:
            for line in f:
                if line.startswith(b"element vertex"):
                    res["fused_points"] = int(line.split()[-1])
                    break
                if line.startswith(b"end_header"):
                    break
        res["fused_ply_mb"] = round(ply.stat().st_size / 1e6, 1)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    print("RESULT", json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
