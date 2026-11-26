"""Registration components and where the links are missing.

Reads the sparse models a mapper writes (COLMAP's `images.bin` or `images.txt`, one folder per
connected component) and reports, for the photos in capture order:

- which component registered each photo. A photo counts as registered only when it observes at
  least one 3-D point (RC-P1's rule: a pose without points is not part of the model);
- the components, their size, and photos that two components share (a link the mapper did not
  merge on);
- every break in the sequence: two registered photos, consecutive in capture order, that sit in
  different components, or in the same component with unregistered photos between them;
- with a capture set whose photos carry poses (ARKit, a robot), where each break is: the camera
  positions on either side, the distance between them and the change of viewing direction.

Pure Python (no numpy), like the capture-set reader. Proven on ARKitScenes in RC-P10.
"""

import itertools
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from recon import capture_set as cs


class ModelError(ValueError):
    """A sparse model folder is missing its images file or is malformed."""


@dataclass(frozen=True)
class ModelImage:
    name: str
    cam_from_world_quat_wxyz: tuple[float, float, float, float]
    translation: cs.Vec
    observed_points: int


def _read_images_bin(path: Path) -> list[ModelImage]:
    raw = path.read_bytes()
    try:
        (n,) = struct.unpack_from("<Q", raw, 0)
        off, out = 8, []
        for _ in range(n):
            _image_id, *pose, _cam = struct.unpack_from("<I7di", raw, off)
            off += 4 + 56 + 4
            end = raw.index(b"\0", off)
            name = raw[off:end].decode()
            off = end + 1
            (npts,) = struct.unpack_from("<Q", raw, off)
            off += 8
            # Each 2-D point is x, y (doubles) and a point3D id (int64, -1 when unmatched).
            observed = sum(
                p[2] != -1 for p in struct.iter_unpack("<ddq", raw[off : off + 24 * npts])
            )
            off += 24 * npts
            out.append(ModelImage(name, tuple(pose[:4]), tuple(pose[4:]), observed))
    except (struct.error, ValueError) as exc:
        raise ModelError(f"{path}: malformed images.bin ({exc})") from exc
    return out


def _read_images_txt(path: Path) -> list[ModelImage]:
    lines = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    out = []
    for head, pts in zip(lines[0::2], lines[1::2], strict=False):
        f = head.split()
        if len(f) < 10:
            raise ModelError(f"{path}: malformed image line {head!r}")
        ids = pts.split()[2::3]
        out.append(
            ModelImage(
                name=" ".join(f[9:]),
                cam_from_world_quat_wxyz=tuple(float(x) for x in f[1:5]),
                translation=tuple(float(x) for x in f[5:8]),
                observed_points=sum(i != "-1" for i in ids),
            )
        )
    return out


def read_model(folder: str | Path) -> list[ModelImage]:
    """The images of one sparse model folder, binary preferred over text."""
    folder = Path(folder)
    if (folder / "images.bin").exists():
        return _read_images_bin(folder / "images.bin")
    if (folder / "images.txt").exists():
        return _read_images_txt(folder / "images.txt")
    raise ModelError(f"{folder}: no images.bin or images.txt")


def read_components(root: str | Path) -> dict[str, set[str]]:
    """Registered photo names per component. `root` is one model folder, or a folder of them
    (COLMAP's `sparse/0`, `sparse/1`, ...)."""
    root = Path(root)
    folders = (
        [root]
        if (root / "images.bin").exists() or (root / "images.txt").exists()
        else sorted((p for p in root.iterdir() if p.is_dir()), key=_natural)
    )
    if not folders:
        raise ModelError(f"{root}: no model folders")
    return {f.name: {im.name for im in read_model(f) if im.observed_points > 0} for f in folders}


def _natural(p: Path | str) -> list:
    """Sort key that orders numbers by value: frame_9 before frame_10, 3669.060 before 3700.88."""
    s = p.name if isinstance(p, Path) else p
    return [
        float(t) if re.fullmatch(r"\d+(\.\d+)?", t) else t for t in re.split(r"(\d+(?:\.\d+)?)", s)
    ]


def capture_order(capture: cs.CaptureSet | None, names: set[str]) -> list[str]:
    """Photos in capture order: the set's frame index when a set is given, else natural name
    order (timestamped names sort in time)."""
    if capture is not None:
        return [cs.colmap_name(f) for f in sorted(capture.frames, key=lambda f: f.index)]
    return sorted(names, key=_natural)


def _where(capture: cs.CaptureSet, a: str, b: str) -> dict | None:
    poses = {
        cs.colmap_name(f): f
        for f in capture.frames
        if f.position is not None and f.quaternion_xyzw is not None
    }
    if a not in poses or b not in poses:
        return None
    (ra, ta), (rb, tb) = (
        cs.cam_from_world(poses[n].position, poses[n].quaternion_xyzw, capture.convention)
        for n in (a, b)
    )
    ca, cb = cs.camera_centre(ra, ta), cs.camera_centre(rb, tb)
    # The viewing direction in the world is the camera's +z axis: the third row of cam_from_world.
    cos = sum(x * y for x, y in zip(ra[2], rb[2], strict=True))
    return {
        "pose_source": poses[a].pose_source,
        "from_position": [round(x, 3) for x in ca],
        "to_position": [round(x, 3) for x in cb],
        "moved_m": round(math.dist(ca, cb), 3),
        "turned_deg": round(math.degrees(math.acos(max(-1.0, min(1.0, cos)))), 1),
    }


def report(components: dict[str, set[str]], capture: cs.CaptureSet | None = None) -> dict:
    """The component report for photos in capture order (see the module docstring)."""
    registered = set().union(*components.values()) if components else set()
    order = capture_order(capture, registered)
    missing = registered - set(order)
    if missing:
        raise ModelError(f"{len(missing)} registered photos are not in the capture set")
    label = {n: {c for c, members in components.items() if n in members} for n in order}
    reg = [(i, n) for i, n in enumerate(order) if label[n]]
    breaks, gaps = [], []
    for (i, a), (j, b) in itertools.pairwise(reg):
        same = label[a] & label[b]
        if same and j == i + 1:
            continue
        row = {
            "from_photo": a,
            "to_photo": b,
            "from_components": sorted(label[a], key=_natural),
            "to_components": sorted(label[b], key=_natural),
            "unregistered_between": j - i - 1,
        }
        if capture is not None:
            where = _where(capture, a, b)
            if where:
                row["where"] = where
        (gaps if same else breaks).append(row)
    names = sorted(components, key=_natural)
    shared = {
        f"{a}-{b}": len(components[a] & components[b])
        for k, a in enumerate(names)
        for b in names[k + 1 :]
        if components[a] & components[b]
    }
    sized = [c for c in names if components[c]]
    return {
        "photos": len(order),
        "registered": len(reg),
        "unregistered": len(order) - len(reg),
        "components": [{"component": c, "photos": len(components[c])} for c in names],
        "one_model": len(sized) == 1 and len(reg) == len(order),
        "shared_photos": shared,
        "breaks": breaks,
        "gaps_within_component": gaps,
    }
