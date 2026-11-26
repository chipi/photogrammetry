"""RC-P10: wall distances from the Faro scans themselves, independent of ARKit's poses.

  merge     the visit's Faro scans, which are stored already registered to each other, on a 1 cm
            grid: faro.ply
  register  a rigid transform (no scale) from faro.ply onto the ARKit-frame laser reference
            (reference.ply): FPFH features and RANSAC, then point-to-plane ICP at 5, 2 and 1 cm.
            A rigid transform leaves distances unchanged, so the Faro distances below depend on
            the scanner alone; the transform only says which Faro surface is which wall
  walls     for each seed, the walls of room.py's reference, refitted in the registered Faro cloud
            with room.py's refit; each pair's distance from the Faro scan against the
            ARKit-posed laser reference and against the TSDF

Writes under $RECCE_DATA_DIR/runs/p10/<video>/ and runs/p10/faro_<video>_seed<n>.json.
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import open3d as o3d
import room

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
LASER = RECCE / "datasets/arkitscenes/laser"
VISITS = {"42444793": "421012", "42444858": "421009", "42444515": "421061"}
MERGE_VOXEL_M = 0.01
GLOBAL_VOXEL_M = 0.05
ICP_STEPS_M = (0.05, 0.02, 0.01)


def cmd_merge(args):
    # The scans are stored already registered to each other: on 421012, 60% of scan 170037's
    # points lie within 2 cm of scan 170033 as stored, and 0-7% after applying either _pose.txt
    # (read as an affine transform) or its inverse. The pose files are not applied.
    visit = VISITS[args.video]
    merged = o3d.geometry.PointCloud()
    for ply in sorted((LASER / visit).glob("*.ply")):
        cloud = o3d.io.read_point_cloud(str(ply)).voxel_down_sample(MERGE_VOXEL_M)
        print(ply.name, len(cloud.points), "points after 1 cm grid")
        merged += cloud
    merged = merged.voxel_down_sample(MERGE_VOXEL_M)
    out = room.RUNS / args.video
    o3d.io.write_point_cloud(str(out / "faro.ply"), merged)
    print("merged", len(merged.points), "points")


def features(cloud, voxel):
    cloud.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=2 * voxel, max_nn=30))
    return o3d.pipelines.registration.compute_fpfh_feature(
        cloud, o3d.geometry.KDTreeSearchParamHybrid(radius=5 * voxel, max_nn=100)
    )


def cmd_register(args):
    out = room.RUNS / args.video
    faro = o3d.io.read_point_cloud(str(out / "faro.ply"))
    ref = o3d.io.read_point_cloud(str(out / "reference.ply"))
    src, dst = faro.voxel_down_sample(GLOBAL_VOXEL_M), ref.voxel_down_sample(GLOBAL_VOXEL_M)
    reg = o3d.pipelines.registration
    glob = reg.registration_ransac_based_on_feature_matching(
        src,
        dst,
        features(src, GLOBAL_VOXEL_M),
        features(dst, GLOBAL_VOXEL_M),
        True,
        1.5 * GLOBAL_VOXEL_M,
        reg.TransformationEstimationPointToPoint(False),
        3,
        [
            reg.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            reg.CorrespondenceCheckerBasedOnDistance(1.5 * GLOBAL_VOXEL_M),
        ],
        reg.RANSACConvergenceCriteria(1_000_000, 0.999),
    )
    print("global: fitness", round(glob.fitness, 3), "rmse", round(glob.inlier_rmse, 4))
    t = glob.transformation
    steps = []
    for v in ICP_STEPS_M:
        s, d = faro.voxel_down_sample(v), ref.voxel_down_sample(v)
        for c in (s, d):
            c.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=3 * v, max_nn=30))
        icp = reg.registration_icp(
            s,
            d,
            2 * v,
            t,
            reg.TransformationEstimationPointToPlane(),
            reg.ICPConvergenceCriteria(max_iteration=100),
        )
        t = icp.transformation
        steps.append({"voxel_m": v, "fitness": icp.fitness, "rmse_m": icp.inlier_rmse})
        print(f"icp {v} m: fitness {icp.fitness:.3f}, rmse {icp.inlier_rmse:.4f} m")
    (out / "faro_to_arkit.json").write_text(
        json.dumps(
            {"transform": t.tolist(), "global_fitness": glob.fitness, "icp": steps}, indent=1
        )
    )


def cmd_walls(args):
    out = room.RUNS / args.video
    t = np.array(json.loads((out / "faro_to_arkit.json").read_text())["transform"])
    faro = np.asarray(o3d.io.read_point_cloud(str(out / "faro.ply")).points)
    faro = faro @ t[:3, :3].T + t[:3, 3]
    traj = np.loadtxt(room.RAW / args.video / "lowres_wide.traj")
    ref = np.asarray(o3d.io.read_point_cloud(str(out / "reference.ply")).points)
    for seed in args.seeds:
        # The same draw as room.py walls --seed: seed, then the TSDF sample, then the planes.
        o3d.utility.random.seed(seed)
        mesh = o3d.io.read_triangle_mesh(str(out / "tsdf.ply"))
        tsdf = np.asarray(mesh.sample_points_uniformly(len(ref)).points)
        planes = room.find_planes(ref)
        up, _ = room.gravity_up(planes, traj)
        walls = room.walls_of(planes, up)
        for w in walls:
            w["tsdf"] = room.refit(w, tsdf, up)
            w["faro"] = room.refit(w, faro, up)
        rows = []
        for g in room.axes_of(walls):
            members = g["members"]
            for k, i in enumerate(members):
                for j in members[k + 1 :]:
                    a, b = walls[i], walls[j]
                    ref_m = room.separation(a, b, a, b)
                    if ref_m < room.PAIR_MIN_SEP_M or not (a["faro"] and b["faro"]):
                        continue
                    faro_m = room.separation(a, b, a["faro"], b["faro"])
                    row = {
                        "walls": [i, j],
                        "faro_m": round(faro_m, 4),
                        "reference_m": round(ref_m, 4),
                        "reference_vs_faro_pct": round(100 * (ref_m - faro_m) / faro_m, 3),
                    }
                    if a["tsdf"] and b["tsdf"]:
                        tsdf_m = room.separation(a, b, a["tsdf"], b["tsdf"])
                        tol = max(room.TOL_FRAC * faro_m, room.TOL_M)
                        row |= {
                            "tsdf_m": round(tsdf_m, 4),
                            "tsdf_vs_faro_pct": round(100 * (tsdf_m - faro_m) / faro_m, 3),
                            "tsdf_vs_faro_m": round(tsdf_m - faro_m, 4),
                            "within": bool(abs(tsdf_m - faro_m) <= tol),
                        }
                    rows.append(row)
        path = room.RUNS / f"faro_{args.video}_seed{seed}.json"
        path.write_text(json.dumps(rows, indent=1))
        rv = [r["reference_vs_faro_pct"] for r in rows]
        tv = [r["tsdf_vs_faro_pct"] for r in rows if "tsdf_vs_faro_pct" in r]
        print(
            f"seed {seed}: {len(rows)} pairs; reference vs Faro median {np.median(rv):+.2f}% "
            f"(min {min(rv):+.2f}, max {max(rv):+.2f}); TSDF vs Faro median {np.median(tv):+.2f}% "
            f"(min {min(tv):+.2f}, max {max(tv):+.2f}); within "
            f"{sum(r.get('within', False) for r in rows)}/{len(tv)}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["merge", "register", "walls"])
    ap.add_argument("--video", default="42444793", choices=list(VISITS))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    args = ap.parse_args()
    {"merge": cmd_merge, "register": cmd_register, "walls": cmd_walls}[args.command](args)


if __name__ == "__main__":
    main()
