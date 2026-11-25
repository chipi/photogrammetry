"""RC-P10: a room from inside, from ARKit poses and LiDAR depth, scored against the laser scan.

  align    checks that highres_depth (the Faro laser mesh rendered into each frame) lines up with
           the LiDAR lowres_depth of the same frame, under the lowres_wide intrinsics scaled to
           1920x1440; nothing else is trusted until this passes
  fuse     TSDF of lowres_depth with the ARKit poses (Open3D), mesh written as tsdf.ply
  reference  the laser depth frames back-projected with the same poses, as reference.ply
  walls    tall vertical planes of the reference; the same planes refitted in the TSDF mesh; the
           distance between every two parallel ones at least 1 m apart, laser against TSDF

ARKitScenes' world frame is z-up, not ARKit's native y-up; `walls` takes up from the camera's
image-up direction and snaps it to the floor's normal, and fails if no plane is near it.
Everything is written under $RECCE_DATA_DIR/runs/p10/<video>.
"""

import argparse
import itertools
import json
import os
from pathlib import Path

import numpy as np
import open3d as o3d
import open3d.core as o3c

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
RAW = RECCE / "datasets/arkitscenes/raw/Training"
RUNS = RECCE / "runs/p10"
VIDEOS = ("42444515", "42444793", "42444821", "42444858", "42444873")
HIGHRES = (1920, 1440)
MAX_POSE_GAP_S = 0.15
CONF_MIN = 2
FUSE_EVERY = 2
VOXEL_M = 0.02
TRUNC_M = 0.08
DEPTH_MAX_M = 4.0
REF_STRIDE = 4
REF_VOXEL_M = 0.01
PLANE_DIST_M = 0.02
PLANES_MAX = 40
PLANE_MIN_PTS = 3000
VERTICAL_DEG = 5.0
PARALLEL_DEG = 5.0
WALL_MIN_HEIGHT_M = 1.8
WALL_MIN_WIDTH_M = 0.8
PAIR_MIN_SEP_M = 1.0
REFIT_BAND_M = 0.05
TOL_FRAC = 0.02
TOL_M = 0.02
FLOOR_SEARCH_DEG = 30.0


def rodrigues(v):
    theta = float(np.linalg.norm(v))
    if theta < 1e-12:
        return np.eye(3)
    k = np.asarray(v) / theta
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(theta) * kx + (1 - np.cos(theta)) * kx @ kx


def log_rotation(rot):
    angle = float(np.arccos(np.clip((np.trace(rot) - 1) / 2, -1.0, 1.0)))
    if angle < 1e-12:
        return np.zeros(3)
    w = np.array([rot[2, 1] - rot[1, 2], rot[0, 2] - rot[2, 0], rot[1, 0] - rot[0, 1]])
    return w * angle / (2 * np.sin(angle))


def world_from_cam_at(traj, stamp):
    """4x4 world_from_cam (OpenCV camera axes) at `stamp`, interpolated as in RC-P8, or None.

    Each .traj line holds cam_from_world as axis-angle and translation."""
    i = int(np.searchsorted(traj[:, 0], stamp))
    if i == 0 or i == len(traj):
        return None
    a, b = traj[i - 1], traj[i]
    if b[0] - a[0] > MAX_POSE_GAP_S:
        return None
    u = (stamp - a[0]) / (b[0] - a[0])
    ra, rb = rodrigues(a[1:4]), rodrigues(b[1:4])
    ca, cb = -ra.T @ a[4:7], -rb.T @ b[4:7]
    w = ra.T @ rodrigues(u * log_rotation(ra @ rb.T))
    out = np.eye(4)
    out[:3, :3] = w
    out[:3, 3] = (1 - u) * ca + u * cb
    return out


def stamp_of(path):
    return float(path.stem.split("_")[1])


def frames(vid, sub):
    return sorted((RAW / vid / sub).glob("*.png"), key=stamp_of)


def pincam(vid, sub, stamp):
    w, h, fx, fy, cx, cy = np.loadtxt(RAW / vid / sub / f"{vid}_{stamp:.3f}.pincam")
    return int(w), int(h), fx, fy, cx, cy


def read_png(path):
    return np.asarray(o3d.io.read_image(str(path)))


def highres_k(vid, stamp):
    """lowres_wide intrinsics scaled to the 1920x1440 frame (the 256x192 LiDAR grid is the same
    view at 1/7.5); pixel centres scale about (-0.5, -0.5)."""
    w, _, fx, fy, cx, cy = pincam(vid, "lowres_wide_intrinsics", stamp)
    s = HIGHRES[0] / w
    return fx * s, fy * s, (cx + 0.5) * s - 0.5, (cy + 0.5) * s - 0.5


def backproject(depth_m, fx, fy, cx, cy, stride=1):
    d = depth_m[::stride, ::stride]
    v, u = np.mgrid[0 : depth_m.shape[0] : stride, 0 : depth_m.shape[1] : stride]
    ok = d > 0
    z = d[ok]
    return np.stack([(u[ok] - cx) / fx * z, (v[ok] - cy) / fy * z, z], axis=1)


def cmd_align(args):
    report = {}
    for vid in args.videos:
        diffs, signed = [], []
        for f in frames(vid, "highres_depth"):
            low = read_png(RAW / vid / "lowres_depth" / f.name).astype(np.float64) / 1000
            conf = read_png(RAW / vid / "confidence" / f.name)
            high = read_png(f).astype(np.float64) / 1000
            h, w = low.shape
            scale = HIGHRES[0] / w
            v, u = np.mgrid[0:h, 0:w]
            hu = np.clip(np.round((u + 0.5) * scale - 0.5).astype(int), 0, HIGHRES[0] - 1)
            hv = np.clip(np.round((v + 0.5) * scale - 0.5).astype(int), 0, HIGHRES[1] - 1)
            sampled = high[hv, hu]
            ok = (low > 0) & (sampled > 0) & (conf >= CONF_MIN)
            if ok.sum() > 100:
                diffs.append(float(np.median(np.abs(low[ok] - sampled[ok]))))
                signed.append(float(np.median((low[ok] - sampled[ok]) / sampled[ok])))
        report[vid] = {
            "frames": len(diffs),
            "median_abs_m": round(float(np.median(diffs)), 4),
            "p90_abs_m": round(float(np.percentile(diffs, 90)), 4),
            "median_signed_rel_pct": round(100 * float(np.median(signed)), 2),
        }
    print(json.dumps(report, indent=1))
    (RUNS / "align.json").parent.mkdir(parents=True, exist_ok=True)
    (RUNS / "align.json").write_text(json.dumps(report, indent=1))


def cmd_fuse(args):
    # Open3D 0.20's legacy ScalableTSDFVolume returned no surface here, even for one frame at
    # the identity pose; the tensor VoxelBlockGrid integrates the same frames.
    dev = o3c.Device("CPU:0")
    for vid in args.videos:
        traj = np.loadtxt(RAW / vid / "lowres_wide.traj")
        vga = frames(vid, "vga_wide")
        vga_stamps = np.array([stamp_of(p) for p in vga])
        vbg = o3d.t.geometry.VoxelBlockGrid(
            attr_names=("tsdf", "weight", "color"),
            attr_dtypes=(o3c.float32, o3c.float32, o3c.float32),
            attr_channels=(1, 1, 3),
            voxel_size=VOXEL_M,
            block_resolution=16,
            block_count=100000,
            device=dev,
        )
        used = 0
        for f in frames(vid, "lowres_depth")[::FUSE_EVERY]:
            s = stamp_of(f)
            pose = world_from_cam_at(traj, s)
            if pose is None:
                continue
            w, h, fx, fy, cx, cy = pincam(vid, "lowres_wide_intrinsics", s)
            depth = read_png(f).copy()
            depth[read_png(RAW / vid / "confidence" / f.name) < CONF_MIN] = 0
            if not np.any((depth > 0) & (depth < DEPTH_MAX_M * 1000)):
                continue
            rgb = read_png(vga[int(np.argmin(np.abs(vga_stamps - s)))])
            rows = (np.arange(h) * rgb.shape[0] / h).astype(int)
            cols = (np.arange(w) * rgb.shape[1] / w).astype(int)
            k = o3c.Tensor(np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]), o3c.float64)
            ext = o3c.Tensor(np.linalg.inv(pose), o3c.float64)
            d_img = o3d.t.geometry.Image(o3c.Tensor(depth))
            c_img = o3d.t.geometry.Image(o3c.Tensor(np.ascontiguousarray(rgb[rows][:, cols])))
            blocks = vbg.compute_unique_block_coordinates(
                d_img, k, ext, 1000.0, DEPTH_MAX_M, TRUNC_M / VOXEL_M
            )
            vbg.integrate(blocks, d_img, c_img, k, k, ext, 1000.0, DEPTH_MAX_M, TRUNC_M / VOXEL_M)
            used += 1
        mesh = vbg.extract_triangle_mesh().to_legacy()
        out = RUNS / vid
        out.mkdir(parents=True, exist_ok=True)
        o3d.io.write_triangle_mesh(str(out / "tsdf.ply"), mesh)
        print(vid, "fused", used, "frames;", len(mesh.vertices), "vertices")


def cmd_reference(args):
    for vid in args.videos:
        traj = np.loadtxt(RAW / vid / "lowres_wide.traj")
        pts, used = [], 0
        for f in frames(vid, "highres_depth"):
            s = stamp_of(f)
            pose = world_from_cam_at(traj, s)
            if pose is None:
                continue
            depth = read_png(f).astype(np.float64) / 1000
            depth[depth > DEPTH_MAX_M * 2] = 0
            p = backproject(depth, *highres_k(vid, s), stride=REF_STRIDE)
            pts.append(p @ pose[:3, :3].T + pose[:3, 3])
            used += 1
        cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.concatenate(pts)))
        cloud = cloud.voxel_down_sample(REF_VOXEL_M)
        out = RUNS / vid
        out.mkdir(parents=True, exist_ok=True)
        o3d.io.write_point_cloud(str(out / "reference.ply"), cloud)
        print(vid, "reference from", used, "laser frames;", len(cloud.points), "points")


def camera_up(traj):
    """Mean image-up direction (-y of the OpenCV camera) in the world, over the trajectory; the
    videos were picked with sky direction Up, so it points roughly away from gravity."""
    ups = [-(rodrigues(r[1:4]).T @ np.array([0.0, 1.0, 0.0])) for r in traj]
    u = np.mean(ups, axis=0)
    return u / np.linalg.norm(u)


def gravity_up(planes, traj):
    """Up as the normal of the largest plane within FLOOR_SEARCH_DEG of the camera's up,
    signed to agree with it. Fails if no plane is that close: the axis is then unchecked."""
    cam = camera_up(traj)
    near = [p for p in planes if abs(p[0] @ cam) > np.cos(np.radians(FLOOR_SEARCH_DEG))]
    if not near:
        raise ValueError("no horizontal plane near the camera's up direction")
    n = max(near, key=lambda p: len(p[2]))[0]
    up = n if n @ cam > 0 else -n
    return up, cam


def horizontal_axis(n, up):
    """Unit in-plane horizontal direction of a vertical plane with normal n."""
    t = np.cross(up, n)
    return t / np.linalg.norm(t)


def fit_plane(p):
    c = p.mean(0)
    _, _, vt = np.linalg.svd(p - c, full_matrices=False)
    n = vt[2]
    return n, -float(n @ c)


def find_planes(points):
    """Iterative RANSAC planes, largest first: [(normal, offset, inlier points)]."""
    rest = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    planes = []
    for _ in range(PLANES_MAX):
        if len(rest.points) < PLANE_MIN_PTS:
            break
        _, idx = rest.segment_plane(PLANE_DIST_M, 3, 2000)
        if len(idx) < PLANE_MIN_PTS:
            break
        inl = np.asarray(rest.points)[idx]
        n, d = fit_plane(inl)
        planes.append((n, d, inl))
        rest = rest.select_by_index(idx, invert=True)
    return planes


def walls_of(planes, up):
    """Tall vertical planes: candidates for the room's walls."""
    walls = []
    for n, d, inl in planes:
        if abs(n @ up) > np.sin(np.radians(VERTICAL_DEG)):
            continue
        t = horizontal_axis(n, up)
        height = float(np.percentile(inl @ up, 99) - np.percentile(inl @ up, 1))
        width = float(np.percentile(inl @ t, 99) - np.percentile(inl @ t, 1))
        if height < WALL_MIN_HEIGHT_M or width < WALL_MIN_WIDTH_M:
            continue
        rms = float(np.sqrt(np.mean((inl @ n + d) ** 2)))
        walls.append({"n": n, "d": d, "inl": inl, "height": height, "width": width, "rms": rms})
    return walls


def refit(wall, cloud_pts, up):
    """The same wall in another cloud: points within REFIT_BAND_M of the plane and inside its
    footprint, plane refitted by least squares, then once more on a PLANE_DIST_M band."""
    n, d, inl = wall["n"], wall["d"], wall["inl"]
    t = horizontal_axis(n, up)
    lo_t, hi_t = np.percentile(inl @ t, [1, 99])
    lo_u, hi_u = np.percentile(inl @ up, [1, 99])
    along, high = cloud_pts @ t, cloud_pts @ up
    box = (along > lo_t) & (along < hi_t) & (high > lo_u) & (high < hi_u)
    sel = cloud_pts[box & (np.abs(cloud_pts @ n + d) < REFIT_BAND_M)]
    if len(sel) < 100:
        return None
    n2, d2 = fit_plane(sel)
    sel = sel[np.abs(sel @ n2 + d2) < PLANE_DIST_M]
    if len(sel) < 100:
        return None
    n2, d2 = fit_plane(sel)
    if n2 @ n < 0:
        n2, d2 = -n2, -d2
    return {
        "n": n2,
        "d": d2,
        "points": len(sel),
        "rms": float(np.sqrt(np.mean((sel @ n2 + d2) ** 2))),
    }


def axes_of(walls):
    """Group walls by direction (normals parallel within PARALLEL_DEG, either sign)."""
    groups = []
    for i, w in enumerate(walls):
        for g in groups:
            if abs(w["n"] @ g["axis"]) > np.cos(np.radians(PARALLEL_DEG)):
                g["members"].append(i)
                break
        else:
            groups.append({"axis": w["n"].copy(), "members": [i]})
    return groups


def separation(a, b, plane_a, plane_b):
    """Distance between two near-parallel planes, from each wall's reference inlier centroid to
    the other plane along its normal, averaged. Using the same centroids for the laser and the
    TSDF planes measures both at the same place on the wall."""
    ca, cb = a["inl"].mean(0), b["inl"].mean(0)
    return 0.5 * (abs(ca @ plane_b["n"] + plane_b["d"]) + abs(cb @ plane_a["n"] + plane_a["d"]))


def cmd_walls(args):
    # segment_plane draws at random; the seed makes a run repeatable, and several seeds show
    # how much the plane set (and so the pairs) depends on the draw.
    o3d.utility.random.seed(args.seed)
    rows = {}
    for vid in args.videos:
        traj = np.loadtxt(RAW / vid / "lowres_wide.traj")
        ref = np.asarray(o3d.io.read_point_cloud(str(RUNS / vid / "reference.ply")).points)
        mesh = o3d.io.read_triangle_mesh(str(RUNS / vid / "tsdf.ply"))
        tsdf = np.asarray(mesh.sample_points_uniformly(len(ref)).points)
        planes = find_planes(ref)
        up, cam = gravity_up(planes, traj)
        walls = walls_of(planes, up)
        for w in walls:
            w["tsdf"] = refit(w, tsdf, up)
        lengths = []
        # ARKitScenes videos often cross a doorway, so a scene is not one box room: every pair of
        # parallel tall planes at least PAIR_MIN_SEP_M apart is a wall-to-wall distance.
        pairs = [
            (g, i, j) for g in axes_of(walls) for i, j in itertools.combinations(g["members"], 2)
        ]
        for g, i, j in pairs:
            a, b = walls[i], walls[j]
            ref_m = separation(a, b, a, b)
            if ref_m < PAIR_MIN_SEP_M:
                continue
            row = {
                "axis": [round(float(x), 3) for x in g["axis"]],
                "walls": [i, j],
                "reference_m": round(ref_m, 4),
            }
            if a["tsdf"] and b["tsdf"]:
                tsdf_m = separation(a, b, a["tsdf"], b["tsdf"])
                err, tol = tsdf_m - ref_m, max(TOL_FRAC * ref_m, TOL_M)
                row |= {
                    "tsdf_m": round(tsdf_m, 4),
                    "error_m": round(err, 4),
                    "error_pct": round(100 * err / ref_m, 2),
                    "tolerance_m": round(tol, 4),
                    "within": bool(abs(err) <= tol),
                }
            lengths.append(row)
        rows[vid] = {
            "up": [round(float(x), 4) for x in up],
            "camera_up_angle_deg": round(float(np.degrees(np.arccos(up @ cam))), 1),
            "planes": len(planes),
            "walls": [
                {
                    "normal": [round(float(x), 3) for x in w["n"]],
                    "height_m": round(w["height"], 2),
                    "width_m": round(w["width"], 2),
                    "reference_rms_m": round(w["rms"], 4),
                    "tsdf_points": w["tsdf"]["points"] if w["tsdf"] else 0,
                    "tsdf_rms_m": round(w["tsdf"]["rms"], 4) if w["tsdf"] else None,
                    "tsdf_tilt_deg": round(
                        float(np.degrees(np.arccos(min(1.0, w["tsdf"]["n"] @ w["n"])))), 3
                    )
                    if w["tsdf"]
                    else None,
                }
                for w in walls
            ],
            "lengths": lengths,
        }
        print(vid, json.dumps({k: rows[vid][k] for k in ("up", "camera_up_angle_deg")}))
        for r in lengths:
            print("  ", json.dumps(r))
    (RUNS / f"walls_seed{args.seed}.json").write_text(json.dumps(rows, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["align", "fuse", "reference", "walls"])
    ap.add_argument("--videos", nargs="+", default=list(VIDEOS))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    RUNS.mkdir(parents=True, exist_ok=True)
    {"align": cmd_align, "fuse": cmd_fuse, "reference": cmd_reference, "walls": cmd_walls}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
