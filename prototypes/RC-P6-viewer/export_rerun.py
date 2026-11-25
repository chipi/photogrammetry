"""RC-P6: log the RC-P4 courtyard result to Rerun as the engineering view and save an .rrd.

Usage:
  export_rerun.py [--data ~/.cache/recce/runs/p6/data] [--out ~/.cache/recce/runs/p6/courtyard.rrd]

Logs, all in the COLMAP model frame (z up):
  world/mesh      the textured mesh; Rerun takes one albedo texture per mesh and texrecon writes
                  115 atlases, so each face corner is coloured by the atlas texel at its uv
  world/splat     the centres of the ~1 M gaussians, coloured by their base colour (degree 0)
  world/cameras/  the 38 RC-P1 camera poses and pinholes from the sparse model next to the mesh
"""

import argparse
from pathlib import Path

import numpy as np
import rerun as rr
from PIL import Image  # a dependency of rerun-sdk, not declared here

from p6_io import read_cameras_bin, read_images_bin, read_obj, read_ply

SH0 = 0.28209479177387814


def mtl_maps(mtl: Path) -> dict[str, str]:
    maps, cur = {}, None
    for line in mtl.read_text().splitlines():
        t = line.split()
        if t[:1] == ["newmtl"]:
            cur = t[1]
        elif t[:1] == ["map_Kd"]:
            maps[cur] = t[1]
    return maps


def corner_colours(
    mesh: dict, mesh_dir: Path, maps: dict[str, str]
) -> tuple[np.ndarray, np.ndarray]:
    """Unroll the faces to three vertices each and sample the atlas at every corner's uv."""
    pos, col = [], []
    for name, faces in mesh["faces"].items():
        vi, ti = faces[:, :, 0].reshape(-1), faces[:, :, 1].reshape(-1)
        atlas = np.asarray(Image.open(mesh_dir / maps[name]).convert("RGB"))
        h, w = atlas.shape[:2]
        uv = mesh["vt"][ti]
        x = np.clip(np.rint(uv[:, 0] * (w - 1)), 0, w - 1).astype(int)
        y = np.clip(np.rint((1.0 - uv[:, 1]) * (h - 1)), 0, h - 1).astype(int)
        pos.append(mesh["v"][vi])
        col.append(atlas[y, x])
    return np.concatenate(pos), np.concatenate(col)


def log_mesh(data: Path) -> None:
    mesh_dir = data / "mesh"
    mesh = read_obj(mesh_dir / "textured.obj")
    pos, col = corner_colours(mesh, mesh_dir, mtl_maps(mesh_dir / "textured.mtl"))
    tri = np.arange(len(pos), dtype=np.uint32).reshape(-1, 3)
    rr.log(
        "world/mesh",
        rr.Mesh3D(vertex_positions=pos, triangle_indices=tri, vertex_colors=col),
        static=True,
    )
    print(f"mesh: {len(tri):,} faces, {len(pos):,} unrolled vertices")


def log_splat(path: Path) -> None:
    s, _ = read_ply(path, mmap=False)
    xyz = np.stack([s["x"], s["y"], s["z"]], axis=1)
    rgb = np.stack([s["f_dc_0"], s["f_dc_1"], s["f_dc_2"]], axis=1) * SH0 + 0.5
    rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    rr.log("world/splat", rr.Points3D(xyz, colors=rgb, radii=rr.Radius.ui_points(1.0)), static=True)
    print(f"splat centres: {len(xyz):,} points")


def log_cameras(sparse: Path) -> None:
    cams = read_cameras_bin(sparse / "cameras.bin")
    images = sorted(read_images_bin(sparse / "images.bin"), key=lambda i: i["name"])
    for im in images:
        cam = cams[im["camera_id"]]
        fx, fy, cx, cy = cam["params"][:4]  # PINHOLE
        path = f"world/cameras/{Path(im['name']).stem}"
        rr.log(
            path,
            rr.Transform3D(translation=im["c2w"][:3, 3], mat3x3=im["c2w"][:3, :3]),
            static=True,
        )
        rr.log(
            path,
            rr.Pinhole(
                focal_length=[fx, fy],
                principal_point=[cx, cy],
                resolution=[cam["width"], cam["height"]],
                camera_xyz=rr.ViewCoordinates.RDF,
                image_plane_distance=0.8,
            ),
            static=True,
        )
    print(f"cameras: {len(images)} poses with pinholes")


def main() -> None:
    home = Path.home() / ".cache/recce/runs/p6"
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, default=home / "data")
    ap.add_argument("--out", type=Path, default=home / "courtyard.rrd")
    ap.add_argument("--splat", default="splat/courtyard_1m.ply")
    args = ap.parse_args()

    rr.init("recce_p6_courtyard")
    rr.save(args.out)
    rr.log("world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    log_mesh(args.data)
    log_splat(args.data / args.splat)
    log_cameras(args.data / "sparse")
    rr.disconnect()
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
