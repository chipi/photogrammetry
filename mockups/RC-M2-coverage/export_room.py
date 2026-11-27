"""Export one RC-P10 room as RC-M2's data, outside git.

Per mesh vertex: how many LiDAR frames saw it (projected inside the frame, facing the camera and
within 5 cm of that frame's own depth), how widely their viewing directions spread, and its
distance to the Faro scan (the truth the model never saw). Also the camera path, RC-P13's
structured elements for the same room and a ghost camera aimed at the largest weakly seen patch.

Usage, from prototypes/RC-P10-room (its uv project has Open3D):
    uv run python ../../mockups/RC-M2-coverage/export_room.py 42444793 \
        ../../mockups/RC-M2-coverage/data
"""

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import open3d as o3d

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P10-room"))
import room

FRAME_STEP = 4
DEPTH_AGREE_M = 0.05
FACING_COS = 0.1
WEAK_VIEWS = 4
SECTORS = 12  # the coverage glyph: which horizontal directions a vertex was seen from
GHOST_STANDOFF_M = 1.4


def main():
    vid, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    mesh = o3d.io.read_triangle_mesh(str(room.RUNS / vid / "tsdf.ply"))
    mesh.compute_vertex_normals()
    v = np.asarray(mesh.vertices)
    nrm = np.asarray(mesh.vertex_normals)
    traj = np.loadtxt(room.RAW / vid / "lowres_wide.traj")

    scene = json.loads((room.RECCE / f"runs/p13/room/{vid}/scene.json").read_text())
    level = np.array(scene["frame"]["levelling"])
    views = np.zeros(len(v), np.int32)
    sectors = np.zeros(len(v), np.uint16)
    dir_sum = np.zeros_like(v)
    cams = []
    for f in room.frames(vid, "lowres_depth")[::FRAME_STEP]:
        s = room.stamp_of(f)
        pose = room.world_from_cam_at(traj, s)
        if pose is None:
            continue
        w, h, fx, fy, cx, cy = room.pincam(vid, "lowres_wide_intrinsics", s)
        depth = room.read_png(f).astype(np.float64) / 1000
        c = pose[:3, 3]
        cams.append(c)
        pc = (v - c) @ pose[:3, :3]
        z = pc[:, 2]
        ok = z > 0.1
        u = np.full(len(v), -1)
        r = np.full(len(v), -1)
        u[ok] = np.round(fx * pc[ok, 0] / z[ok] + cx).astype(int)
        r[ok] = np.round(fy * pc[ok, 1] / z[ok] + cy).astype(int)
        ok &= (u >= 0) & (u < w) & (r >= 0) & (r < h)
        d = np.zeros(len(v))
        d[ok] = depth[r[ok], u[ok]]
        ok &= (d > 0) & (np.abs(d - z) < DEPTH_AGREE_M)
        ray = c - v
        ray /= np.linalg.norm(ray, axis=1, keepdims=True)
        ok &= (ray * nrm).sum(1) > FACING_COS
        views[ok] += 1
        dir_sum[ok] += ray[ok]
        rl = ray[ok] @ level.T
        azimuth = np.arctan2(rl[:, 1], rl[:, 0]) + np.pi
        sec = (azimuth / (2 * np.pi) * SECTORS).astype(int) % SECTORS
        sectors[ok] |= (1 << sec).astype(np.uint16)
    # 0 when every view came from one direction, towards 1 as directions spread.
    with np.errstate(invalid="ignore", divide="ignore"):
        spread = np.where(views > 0, 1 - np.linalg.norm(dir_sum, axis=1) / views, 0.0)

    t = np.array(json.loads((room.RUNS / vid / "faro_to_arkit.json").read_text())["transform"])
    faro = o3d.io.read_point_cloud(str(room.RUNS / vid / "faro.ply"))
    faro.transform(t)
    pv = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(v))
    err = np.asarray(pv.compute_point_cloud_distance(faro))

    lv = v @ level.T
    ln = nrm @ level.T
    lc = np.array(cams) @ level.T

    # Ghost camera: the 0.5 m voxel holding most weakly seen vertices on near-vertical surfaces.
    weak = (views < WEAK_VIEWS) & (np.abs(ln[:, 2]) < 0.5)
    keys = np.floor(lv[weak] / 0.5).astype(int)
    _, inv, cnt = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    k = int(np.argmax(cnt))
    patch = lv[weak][inv.ravel() == k]
    pn = ln[weak][inv.ravel() == k].mean(0)
    pn[2] = 0
    pn /= np.linalg.norm(pn)
    target = patch.mean(0)
    # A mesh normal may point either way; the shot is taken from the side the phone was on.
    near = lc[np.argsort(np.linalg.norm(lc[:, :2] - target[:2], axis=1))[:50]].mean(0)
    if (near - target)[:2] @ pn[:2] < 0:
        pn = -pn
    lo_xy, hi_xy = lc[:, :2].min(0), lc[:, :2].max(0)
    standoff = GHOST_STANDOFF_M
    while standoff > 0.4:
        ghost = target + pn * standoff
        if np.all(ghost[:2] >= lo_xy) and np.all(ghost[:2] <= hi_xy):
            break
        standoff -= 0.1
    ghost[2] = float(np.median(lc[:, 2]))

    faces = np.asarray(mesh.triangles).astype(np.uint32)
    col = (np.asarray(mesh.vertex_colors) * 255).astype(np.uint8)
    blobs = [
        ("position", lv.astype(np.float32)),
        ("normal", ln.astype(np.float32)),
        ("color", col),
        ("views", np.minimum(views, 65535).astype(np.uint16)),
        ("spread", np.round(spread * 255).astype(np.uint8)),
        ("sectors", sectors),
        ("error_mm", np.minimum(err * 1000, 65535).astype(np.uint16)),
        ("index", faces),
    ]
    layout, off = {}, 0
    with open(out / "room.bin", "wb") as fh:
        for name, a in blobs:
            pad = (-off) % 4
            fh.write(b"\0" * pad)
            off += pad
            b = np.ascontiguousarray(a).tobytes()
            layout[name] = {"offset": off, "dtype": a.dtype.name, "shape": list(a.shape)}
            fh.write(b)
            off += len(b)
    bins = [0, 1, 2, 4, 8, 16, 32, 10**9]
    by_views = []
    for lo, hi in itertools.pairwise(bins):
        m = (views >= lo) & (views < hi)
        if m.any():
            by_views.append(
                {
                    "views": [lo, hi if hi < 10**9 else None],
                    "vertices": int(m.sum()),
                    "error_mm_median": round(float(np.median(err[m]) * 1000), 1),
                    "error_mm_p90": round(float(np.percentile(err[m], 90) * 1000), 1),
                }
            )
    meta = {
        "video": vid,
        "frames_used": len(cams),
        "frame_step": FRAME_STEP,
        "sectors": SECTORS,
        "layout": layout,
        "cameras": lc[::3].round(3).tolist(),
        "ghost": {
            "position": ghost.round(3).tolist(),
            "target": target.round(3).tolist(),
            "weak_vertices": len(patch),
            "standoff_m": round(float(standoff), 2),
            "rule": f"the 0.5 m cell with most wall vertices seen by fewer than {WEAK_VIEWS} "
            f"frames; up to {GHOST_STANDOFF_M} m out on the side the phone was, inside the area "
            "it walked, at the capture's median height",
        },
        "error_by_views": by_views,
        "scene": scene,
    }
    (out / "room.json").write_text(json.dumps(meta))
    print(json.dumps({k: meta[k] for k in ("frames_used", "ghost", "error_by_views")}, indent=1))


if __name__ == "__main__":
    main()
