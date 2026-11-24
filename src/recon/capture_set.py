"""Capture-set reader and pose conversion.

A capture set is a folder: `manifest.json`, `images.json`, `cameras.json` and `images/`. See
`docs/wip/robotics-lab-contract.md` and `docs/wip/capture-set-amendments.md`. Pure Python (no
numpy): matrices are 3x3 tuples of tuples, vectors are 3-tuples.

Conventions, stated once:

- The set's poses are camera pose records: position `{x, y, z}` and orientation as a quaternion
  named `{x, y, z, w}` (the wire form; robotics-lab runfiles store `[w, x, y, z]`, which a
  runfile adapter reorders before it writes a set).
- `manifest.pose_convention` says what a pose means: `direction` (`camera_to_world` or
  `world_to_camera`), `camera_axes` (`opengl`: looks down -Z, +Y up, as Blender and ARKit;
  `opencv`: looks down +Z, +Y down, as COLMAP), `world_up` (`+z` or `+y`) and `handedness`.
- The engine's working form is COLMAP's: a world-to-camera rigid transform with OpenCV camera
  axes, in a z-up right-handed world. A `+y` world is rotated into z-up on ingest; a left-handed
  world is refused, never mirrored silently.
"""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_MANIFEST = 1

Vec = tuple[float, float, float]
Mat = tuple[Vec, Vec, Vec]

IDENTITY: Mat = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
# OpenGL camera axes to OpenCV: keep x, flip y and z (det +1, a rotation of 180 deg about x).
GL_TO_CV: Mat = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
# World y-up to z-up: rotate +90 deg about x, so (x, y, z) -> (x, -z, y); y maps to z.
YUP_TO_ZUP: Mat = ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0))


class CaptureSetError(ValueError):
    """The set is malformed, newer than this reader, or uses a convention it will not guess."""


def matmul(a: Mat, b: Mat) -> Mat:
    return tuple(  # type: ignore[return-value]
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3)
    )


def transpose(a: Mat) -> Mat:
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def matvec(a: Mat, v: Vec) -> Vec:
    return tuple(sum(a[i][k] * v[k] for k in range(3)) for i in range(3))  # type: ignore[return-value]


def det(a: Mat) -> float:
    return (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )


def quat_to_matrix(x: float, y: float, z: float, w: float) -> Mat:
    """Rotation matrix of the unit quaternion; the input is normalised, a zero one is refused."""
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        raise CaptureSetError("zero-length quaternion")
    x, y, z, w = x / n, y / n, z / n, w / n
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def matrix_to_quat(m: Mat) -> tuple[float, float, float, float]:
    """Unit quaternion (x, y, z, w) of a rotation matrix, with w >= 0."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w, x, y, z = (
            s / 4,
            (m[2][1] - m[1][2]) / s,
            (m[0][2] - m[2][0]) / s,
            (m[1][0] - m[0][1]) / s,
        )
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        w, x, y, z = (
            (m[2][1] - m[1][2]) / s,
            s / 4,
            (m[0][1] + m[1][0]) / s,
            (m[0][2] + m[2][0]) / s,
        )
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        w, x, y, z = (
            (m[0][2] - m[2][0]) / s,
            (m[0][1] + m[1][0]) / s,
            s / 4,
            (m[1][2] + m[2][1]) / s,
        )
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        w, x, y, z = (
            (m[1][0] - m[0][1]) / s,
            (m[0][2] + m[2][0]) / s,
            (m[1][2] + m[2][1]) / s,
            s / 4,
        )
    if w < 0:
        w, x, y, z = -w, -x, -y, -z
    return (x, y, z, w)


@dataclass(frozen=True)
class PoseConvention:
    direction: str = "camera_to_world"
    camera_axes: str = "opencv"
    world_up: str = "+z"
    handedness: str = "right"

    def validate(self) -> None:
        for field, allowed in (
            ("direction", ("camera_to_world", "world_to_camera")),
            ("camera_axes", ("opencv", "opengl")),
            ("world_up", ("+z", "+y")),
        ):
            if getattr(self, field) not in allowed:
                raise CaptureSetError(f"pose_convention.{field} {getattr(self, field)!r} unknown")
        if self.handedness != "right":
            raise CaptureSetError("left-handed worlds are refused, not mirrored")


@dataclass(frozen=True)
class Camera:
    sensor: str
    model: str
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float


@dataclass(frozen=True)
class Frame:
    index: int
    file: str
    sensor: str
    sha256: str | None
    position: Vec | None
    quaternion_xyzw: tuple[float, float, float, float] | None
    pose_frame: str | None
    pose_source: str | None


@dataclass(frozen=True)
class CaptureSet:
    root: Path
    manifest: dict
    cameras: dict[str, Camera]
    frames: list[Frame]
    convention: PoseConvention

    @property
    def frame_name(self) -> str | None:
        return (self.manifest.get("frame") or {}).get("name")


def cam_from_world(
    position: Vec, quaternion_xyzw: tuple[float, float, float, float], conv: PoseConvention
) -> tuple[Mat, Vec]:
    """The pose record as COLMAP wants it: world-to-camera, OpenCV axes, z-up world.

    Returns `(rot, trans)` with `x_cam = rot @ x_world + trans`.
    """
    conv.validate()
    rot = quat_to_matrix(*quaternion_xyzw)
    if conv.direction == "world_to_camera":
        # The record is world-to-camera: rot maps world to camera; recover camera-to-world.
        cam_pos = matvec(transpose(rot), tuple(-c for c in position))  # type: ignore[arg-type]
        rot = transpose(rot)
        position = cam_pos
    # Here: rot is camera-to-world, position the camera centre, both in the set's world.
    if conv.camera_axes == "opengl":
        rot = matmul(rot, GL_TO_CV)
    if conv.world_up == "+y":
        rot = matmul(YUP_TO_ZUP, rot)
        position = matvec(YUP_TO_ZUP, position)
    world_to_cam = transpose(rot)
    trans = matvec(world_to_cam, tuple(-c for c in position))  # type: ignore[arg-type]
    return world_to_cam, trans


def camera_centre(rot: Mat, trans: Vec) -> Vec:
    """Camera centre in the world of a world-to-camera `(rot, trans)`."""
    return matvec(transpose(rot), tuple(-t for t in trans))  # type: ignore[arg-type]


def project(rot: Mat, trans: Vec, cam: Camera, point: Vec) -> tuple[float, float, float]:
    """Pixel `(u, v)` (top-left origin, pixel centres at +0.5) and depth of a world point."""
    x, y, z = (a + b for a, b in zip(matvec(rot, point), trans, strict=True))
    if z <= 0:
        return (math.nan, math.nan, z)
    return (cam.fx * x / z + cam.cx, cam.fy * y / z + cam.cy, z)


def _vec(d: dict) -> Vec:
    return (float(d["x"]), float(d["y"]), float(d["z"]))


def _frame(rec: dict) -> Frame:
    pose = rec.get("pose")
    pos = quat = None
    if pose:
        pos = _vec(pose["position"])
        o = pose["orientation"]
        quat = (float(o["x"]), float(o["y"]), float(o["z"]), float(o["w"]))
    return Frame(
        index=int(rec["index"]),
        file=rec["file"],
        sensor=rec.get("sensor", "cam0"),
        sha256=rec.get("sha256"),
        position=pos,
        quaternion_xyzw=quat,
        pose_frame=(pose or {}).get("frame"),
        pose_source=(pose or {}).get("source"),
    )


def load(root: str | Path) -> CaptureSet:
    """Read a capture set. Refuses a manifest newer than this reader and a missing image."""
    root = Path(root)
    try:
        manifest = json.loads((root / "manifest.json").read_text())
        images = json.loads((root / "images.json").read_text())["images"]
        cams = json.loads((root / "cameras.json").read_text())
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise CaptureSetError(f"not a capture set: {root}: {exc}") from exc
    version = manifest.get("manifest")
    if not isinstance(version, int) or version < 1:
        raise CaptureSetError("manifest.manifest must be an integer version >= 1")
    if version > SUPPORTED_MANIFEST:
        raise CaptureSetError(f"manifest version {version} is newer than {SUPPORTED_MANIFEST}")
    try:
        conv = PoseConvention(**manifest.get("pose_convention", {}))
    except TypeError as exc:
        raise CaptureSetError(f"pose_convention has an unknown field: {exc}") from exc
    conv.validate()
    cameras = {
        sensor: Camera(
            sensor,
            c["model"],
            int(c["width"]),
            int(c["height"]),
            float(c["fx"]),
            float(c["fy"]),
            float(c["cx"]),
            float(c["cy"]),
        )
        for sensor, c in cams.items()
    }
    frames = sorted((_frame(r) for r in images), key=lambda f: f.index)
    for f in frames:
        if f.sensor not in cameras:
            raise CaptureSetError(f"image {f.file}: no intrinsics for sensor {f.sensor!r}")
        if not (root / f.file).is_file():
            raise CaptureSetError(f"image missing: {f.file}")
    return CaptureSet(root, manifest, cameras, frames, conv)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_checksums(cs: CaptureSet) -> dict[str, str]:
    """sha256 of the three description files and every image, computed now (provenance)."""
    names = ["manifest.json", "images.json", "cameras.json", *(f.file for f in cs.frames)]
    return {n: sha256_file(cs.root / n) for n in names}


def stale_image_checksums(cs: CaptureSet) -> list[str]:
    """Images whose recorded sha256 differs from the file on disk."""
    return [
        f.file
        for f in cs.frames
        if f.sha256 is not None and f.sha256 != sha256_file(cs.root / f.file)
    ]


def colmap_name(frame: Frame) -> str:
    """Image name relative to `images/`, as COLMAP expects with `--image_path <set>/images`."""
    return frame.file.removeprefix("images/")


def write_colmap_text(
    cs: CaptureSet, out: str | Path, image_ids: dict[str, int] | None = None
) -> int:
    """Write a COLMAP text model (cameras.txt, images.txt, empty points3D.txt) from the set's
    poses, converted to world-to-camera OpenCV in a z-up world. Image id is the frame index, or
    `image_ids[name]` when a database already numbered the images.
    Returns the number of posed images written; frames without a pose are left out."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sensors = sorted(cs.cameras)
    cam_id = {s: i for i, s in enumerate(sensors, start=1)}
    lines = ["# Camera list: CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]"]
    for s in sensors:
        c = cs.cameras[s]
        if c.model != "pinhole":
            raise CaptureSetError(f"camera model {c.model!r} not supported yet")
        lines.append(
            f"{cam_id[s]} PINHOLE {c.width} {c.height} {c.fx!r} {c.fy!r} {c.cx!r} {c.cy!r}"
        )
    (out / "cameras.txt").write_text("\n".join(lines) + "\n")
    img_lines = ["# Image list: IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME", "#"]
    n = 0
    for f in cs.frames:
        if f.position is None or f.quaternion_xyzw is None:
            continue
        rot, trans = cam_from_world(f.position, f.quaternion_xyzw, cs.convention)
        qx, qy, qz, qw = matrix_to_quat(rot)
        vals = " ".join(repr(v) for v in (qw, qx, qy, qz, *trans))
        image_id = image_ids[colmap_name(f)] if image_ids else f.index
        img_lines += [f"{image_id} {vals} {cam_id[f.sensor]} {colmap_name(f)}", ""]
        n += 1
    (out / "images.txt").write_text("\n".join(img_lines) + "\n")
    (out / "points3D.txt").write_text("# 3D point list\n")
    return n
