"""RC-P4: write a texrecon scene folder (.cam files and image links) from a COLMAP workspace.

Usage: make_texrecon_scene.py <dense workspace> <output scene folder>
The workspace is the undistorted one from run_dense.py (PINHOLE cameras, so the .cam distortion
terms are zero). A .cam file holds the world-to-camera translation and rotation, then the focal
length normalised by the larger image side, two zero distortion terms, the pixel aspect ratio and
the principal point in unit coordinates.
"""

import sys
from pathlib import Path

import pycolmap


def main() -> None:
    ws, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rec = pycolmap.Reconstruction(str(ws / "sparse"))
    n = 0
    for img in rec.images.values():
        if not img.has_pose:
            continue
        cam = rec.cameras[img.camera_id]
        pose = img.cam_from_world() if callable(img.cam_from_world) else img.cam_from_world
        rot, t = pose.rotation.matrix(), pose.translation
        size = max(cam.width, cam.height)
        fx, fy = cam.params[0], cam.params[1]
        stem = Path(img.name).stem
        lines = [
            " ".join(f"{v:.9g}" for v in [*t, *rot.reshape(-1)]),
            " ".join(
                f"{v:.9g}"
                for v in [
                    fx / size,
                    0,
                    0,
                    fy / fx,
                    cam.params[2] / cam.width,
                    cam.params[3] / cam.height,
                ]
            ),
        ]
        (out / f"{stem}.cam").write_text("\n".join(lines) + "\n")
        link = out / f"{stem}.jpg"
        link.unlink(missing_ok=True)
        link.symlink_to((ws / "images" / img.name).resolve())
        n += 1
    print(f"wrote {n} cameras to {out}")


if __name__ == "__main__":
    main()
