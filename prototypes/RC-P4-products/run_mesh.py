"""RC-P4: mesh a dense workspace with COLMAP's Delaunay meshing (CPU), optionally Poisson as well.

Usage: run_mesh.py <dense workspace> <output folder> [--poisson [--poisson-depth N --trim T]]
Delaunay reads the workspace's fused.ply and fused.ply.vis (point visibility). Poisson is off by
default: in the conda-forge pycolmap 4.2.1 aarch64 build it aborts the process ("Failed to close
loop", FEMTree.LevelSet.3D.inl line 1645) at every depth and trim tried, even on a clean synthetic
sphere, so it runs in a child process and the failure is recorded instead of ending the run.
"""

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import pycolmap


def _poisson(workspace: Path, out: Path, depth: int, trim: float) -> None:
    opts = pycolmap.PoissonMeshingOptions()
    opts.depth = depth
    opts.trim = trim
    pycolmap.poisson_meshing(workspace / "fused.ply", out / "mesh_poisson.ply", opts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--poisson", action="store_true")
    ap.add_argument("--poisson-depth", type=int, default=11)
    ap.add_argument("--trim", type=float, default=7.0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    res: dict = {"workspace": str(args.workspace), "stages": {}}

    t = time.time()
    pycolmap.dense_delaunay_meshing(args.workspace, args.out / "mesh_delaunay.ply")
    res["stages"]["delaunay"] = {"seconds": round(time.time() - t, 1)}
    print("STAGE delaunay", res["stages"]["delaunay"], flush=True)

    if args.poisson:
        t = time.time()
        child = mp.Process(
            target=_poisson, args=(args.workspace, args.out, args.poisson_depth, args.trim)
        )
        child.start()
        child.join()
        res["stages"]["poisson"] = {
            "seconds": round(time.time() - t, 1),
            "depth": args.poisson_depth,
            "trim": args.trim,
            "exit_code": child.exitcode,
        }
        print("STAGE poisson", res["stages"]["poisson"], flush=True)

    (args.out / "mesh_results.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
