"""RC-P4: COLMAP dense depth and fusion from an aligned sparse model (GPU: patch_match_stereo).

Usage: run_dense.py <scene folder> <aligned model folder> <output folder> [--max-image-size N]
The undistorted workspace in <output>/dense/ is also the gsplat trainer's input, so the mesh and the
splat come from the same poses.
"""

import argparse
import json
import time
from pathlib import Path

import pycolmap


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", type=Path)
    ap.add_argument("model", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-image-size", type=int, default=3000)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    ws = args.out / "dense"
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
        (args.out / "results.json").write_text(json.dumps(res, indent=2))
        return r

    stage(
        "undistort",
        lambda: pycolmap.undistort_images(
            ws,
            args.model,
            args.scene / "images",
            undistort_options=pycolmap.UndistortCameraOptions(max_image_size=args.max_image_size),
        ),
    )
    opts = pycolmap.PatchMatchOptions()
    opts.max_image_size = args.max_image_size
    stage("patch_match_stereo", lambda: pycolmap.patch_match_stereo(ws, options=opts))
    res["depth_maps"] = {
        k: len(list((ws / "stereo" / "depth_maps").rglob(f"*.{k}.bin")))
        for k in ("photometric", "geometric")
    }
    # PLY output carries normals, which Poisson meshing needs.
    stage("stereo_fusion", lambda: pycolmap.stereo_fusion(ws / "fused.ply", ws, output_type="PLY"))
    with (ws / "fused.ply").open("rb") as f:
        for line in f:
            if line.startswith(b"element vertex"):
                res["fused_points"] = int(line.split()[-1])
            if line.startswith(b"end_header"):
                break
    (args.out / "results.json").write_text(json.dumps(res, indent=2))
    print("RESULT", json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
