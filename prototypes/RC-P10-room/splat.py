"""RC-P10: is the splat the same metric model as the TSDF mesh?

For each video's splat (run_splat.sh, trained with --no-normalize-world-space, so in ARKit's frame
in metres):
  surface   distance from each confident gaussian's centre (opacity at least OPACITY_MIN) to the
            TSDF mesh, sampled as points
  walls     for each seed, room.py's walls refitted in the confident centres with room.py's
            refit, and the same wall-to-wall distances, splat against the laser reference
  quality   the trainer's held-out PSNR, SSIM and LPIPS (every 8th frame)

Copy each result/ply and result/stats from the DGX to runs/p10/<video>/splat first.
Writes runs/p10/splat_check.json.
"""

import argparse
import json

import numpy as np
import open3d as o3d
import room

OPACITY_MIN = 0.5
SURFACE_BANDS_M = (0.02, 0.05, 0.10)


def read_splat(path):
    """Centres and opacities (after the sigmoid) of a gsplat PLY."""
    raw = path.read_bytes()
    end = raw.index(b"end_header\n") + len(b"end_header\n")
    header = raw[:end].decode().splitlines()
    n = next(int(h.split()[2]) for h in header if h.startswith("element vertex"))
    names = [h.split()[2] for h in header if h.startswith("property float")]
    data = np.frombuffer(raw[end:], dtype="<f4", count=n * len(names)).reshape(n, len(names))
    xyz = data[:, [names.index("x"), names.index("y"), names.index("z")]].astype(np.float64)
    opacity = 1 / (1 + np.exp(-data[:, names.index("opacity")]))
    return xyz, opacity


def check(vid, seeds):
    out_dir = room.RUNS / vid
    plys = sorted((out_dir / "splat/result/ply").glob("point_cloud_*.ply"))
    xyz, opacity = read_splat(plys[-1])
    centres = xyz[opacity >= OPACITY_MIN]
    mesh = o3d.io.read_triangle_mesh(str(out_dir / "tsdf.ply"))
    o3d.utility.random.seed(0)
    surf = mesh.sample_points_uniformly(2_000_000)
    pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(centres))
    d = np.asarray(pc.compute_point_cloud_distance(surf))
    stats = sorted((out_dir / "splat/result/stats").glob("val_step*.json"))
    row = {
        "gaussians": len(xyz),
        "confident": len(centres),
        "surface_median_m": round(float(np.median(d)), 4),
        "surface_within": {f"{b:.2f}": round(float(np.mean(d < b)), 3) for b in SURFACE_BANDS_M},
        "held_out": json.loads(stats[-1].read_text()) if stats else None,
        "walls": {},
    }
    traj = np.loadtxt(room.RAW / vid / "lowres_wide.traj")
    ref = np.asarray(o3d.io.read_point_cloud(str(out_dir / "reference.ply")).points)
    for seed in seeds:
        # The same draw as room.py walls --seed: seed, then the TSDF sample, then the planes.
        o3d.utility.random.seed(seed)
        mesh.sample_points_uniformly(len(ref))
        planes = room.find_planes(ref)
        up, _ = room.gravity_up(planes, traj)
        walls = room.walls_of(planes, up)
        for w in walls:
            w["splat"] = room.refit(w, centres, up)
        pairs = []
        for g in room.axes_of(walls):
            members = g["members"]
            for k, i in enumerate(members):
                for j in members[k + 1 :]:
                    a, b = walls[i], walls[j]
                    ref_m = room.separation(a, b, a, b)
                    if ref_m < room.PAIR_MIN_SEP_M or not (a["splat"] and b["splat"]):
                        continue
                    splat_m = room.separation(a, b, a["splat"], b["splat"])
                    tol = max(room.TOL_FRAC * ref_m, room.TOL_M)
                    pairs.append(
                        {
                            "reference_m": round(ref_m, 4),
                            "splat_m": round(splat_m, 4),
                            "error_pct": round(100 * (splat_m - ref_m) / ref_m, 3),
                            "within": bool(abs(splat_m - ref_m) <= tol),
                        }
                    )
        row["walls"][str(seed)] = pairs
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", nargs="+", default=list(room.VIDEOS))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    args = ap.parse_args()
    rows = {}
    for vid in args.videos:
        rows[vid] = r = check(vid, args.seeds)
        pairs = [p for s in r["walls"].values() for p in s]
        e = [p["error_pct"] for p in pairs]
        ho = r["held_out"] or {}
        print(
            f"{vid}: {r['confident']:,} of {r['gaussians']:,} gaussians confident; to TSDF median "
            f"{100 * r['surface_median_m']:.1f} cm, within 2/5/10 cm "
            f"{list(r['surface_within'].values())}; walls {sum(p['within'] for p in pairs)}/"
            f"{len(pairs)} within, median {np.median(e) if e else float('nan'):+.2f}%; "
            f"PSNR {ho.get('psnr', float('nan')):.2f} SSIM {ho.get('ssim', float('nan')):.3f}"
        )
    (room.RUNS / "splat_check.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
