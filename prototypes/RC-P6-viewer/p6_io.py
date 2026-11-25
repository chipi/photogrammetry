"""RC-P6 shared readers: binary PLY, COLMAP binary models, and gsplat's world normalisation."""

import struct
from pathlib import Path

import numpy as np

PLY_TYPES = {
    "char": "i1", "uchar": "u1", "short": "<i2", "ushort": "<u2",
    "int": "<i4", "uint": "<u4", "float": "<f4", "double": "<f8",
}  # fmt: skip


def read_ply(path: Path, mmap: bool = True) -> tuple[np.ndarray, list[str]]:
    """Read the first element of a binary little-endian PLY as a structured array."""
    with open(path, "rb") as f:
        header = []
        while True:
            line = f.readline().decode("ascii").strip()
            header.append(line)
            if line == "end_header":
                break
        offset = f.tell()
    if "format binary_little_endian 1.0" not in header:
        raise ValueError(f"{path}: only binary_little_endian PLY is read")
    count, fields, in_vertex = 0, [], False
    for line in header:
        parts = line.split()
        if parts[:1] == ["element"]:
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                count = int(parts[2])
        elif parts[:1] == ["property"] and in_vertex:
            if parts[1] == "list":
                raise ValueError(f"{path}: list properties in the vertex element")
            fields.append((parts[2], PLY_TYPES[parts[1]]))
    dtype = np.dtype(fields)
    if mmap:
        return np.memmap(path, dtype=dtype, mode="r", offset=offset, shape=(count,)), header
    return np.fromfile(path, dtype=dtype, count=count, offset=offset), header


def write_ply(path: Path, arr: np.ndarray) -> None:
    lines = ["ply", "format binary_little_endian 1.0", f"element vertex {len(arr)}"]
    for name in arr.dtype.names:
        kind = {"<f4": "float", "u1": "uchar", "<u4": "uint", "<i4": "int"}[arr.dtype[name].str]
        lines.append(f"property {kind} {name}")
    lines.append("end_header")
    with open(path, "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("ascii"))
        f.write(np.ascontiguousarray(arr).tobytes())


def read_obj(path: Path) -> dict:
    """Read a texrecon OBJ: positions, uvs and faces grouped by material."""
    v, vt = [], []
    faces: dict[str, list] = {}
    mat = None
    with open(path) as f:
        for line in f:
            t = line.split()
            if not t:
                continue
            if t[0] == "v":
                v.append([float(x) for x in t[1:4]])
            elif t[0] == "vt":
                vt.append([float(x) for x in t[1:3]])
            elif t[0] == "usemtl":
                mat = t[1]
                faces.setdefault(mat, [])
            elif t[0] == "f":
                idx = [[int(i) - 1 for i in p.split("/")[:2]] for p in t[1:4]]
                faces[mat].append(idx)
    return {
        "v": np.array(v, np.float32),
        "vt": np.array(vt, np.float32),
        "faces": {m: np.array(fc, np.int64) for m, fc in faces.items() if fc},
    }


def qvec_to_rot(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * w * z, 2 * x * z + 2 * w * y],
            [2 * x * y + 2 * w * z, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * w * x],
            [2 * x * z - 2 * w * y, 2 * y * z + 2 * w * x, 1 - 2 * x * x - 2 * y * y],
        ]
    )


def read_images_bin(path: Path) -> list[dict]:
    """COLMAP images.bin: name, camera id and the camera-to-world pose of every image."""
    out = []
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            image_id, *q_t, camera_id = struct.unpack("<I4d3dI", f.read(4 + 56 + 4))
            name = b""
            while (c := f.read(1)) != b"\x00":
                name += c
            (n2d,) = struct.unpack("<Q", f.read(8))
            f.seek(n2d * 24, 1)
            w2c = np.eye(4)
            w2c[:3, :3] = qvec_to_rot(np.array(q_t[:4]))
            w2c[:3, 3] = q_t[4:7]
            out.append({"id": image_id, "name": name.decode(), "camera_id": camera_id,
                        "c2w": np.linalg.inv(w2c)})  # fmt: skip
    return out


def read_cameras_bin(path: Path) -> dict[int, dict]:
    nparams = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8, 5: 8, 6: 12, 7: 5, 8: 4, 9: 5, 10: 12, 11: 12}
    out = {}
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            cid, model, w, h = struct.unpack("<IiQQ", f.read(24))
            params = struct.unpack(f"<{nparams[model]}d", f.read(8 * nparams[model]))
            out[cid] = {"model": model, "width": w, "height": h, "params": params}
    return out


def read_points3d_bin(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xyz, rgb = [], []
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            _id, x, y, z, r, g, b, _err = struct.unpack("<Q3d3Bd", f.read(8 + 24 + 3 + 8))
            (tl,) = struct.unpack("<Q", f.read(8))
            f.seek(tl * 8, 1)
            xyz.append((x, y, z))
            rgb.append((r, g, b))
    return np.array(xyz), np.array(rgb, np.uint8)


# gsplat examples/datasets/normalize.py (Apache-2.0), reimplemented: the trainer runs in a frame
# it derives from the cameras and the sparse points, and the splat PLY is written in that frame.
def _similarity_from_cameras(c2w: np.ndarray) -> np.ndarray:
    t = c2w[:, :3, 3]
    r = c2w[:, :3, :3]
    ups = np.sum(r * np.array([0, -1.0, 0]), axis=-1)
    world_up = ups.mean(axis=0)
    world_up /= np.linalg.norm(world_up)
    up_cam = np.array([0.0, -1.0, 0.0])
    c = (up_cam * world_up).sum()
    cross = np.cross(world_up, up_cam)
    skew = np.array([[0, -cross[2], cross[1]], [cross[2], 0, -cross[0]], [-cross[1], cross[0], 0]])
    if c > -1:
        r_align = np.eye(3) + skew + (skew @ skew) / (1 + c)
    else:
        r_align = np.diag([-1.0, 1.0, 1.0])
    r = r_align @ r
    fwds = np.sum(r * np.array([0, 0.0, 1.0]), axis=-1)
    t = (r_align @ t[..., None])[..., 0]
    nearest = t + (fwds * -t).sum(-1)[:, None] * fwds
    translate = -np.median(nearest, axis=0)
    tf = np.eye(4)
    tf[:3, 3] = translate
    tf[:3, :3] = r_align
    tf[:3, :] *= 1.0 / np.median(np.linalg.norm(t + translate, axis=-1))
    return tf


def _align_principal_axes(pts: np.ndarray) -> np.ndarray:
    centroid = np.median(pts, axis=0)
    vals, vecs = np.linalg.eigh(np.cov(pts - centroid, rowvar=False))
    vecs = vecs[:, vals.argsort()[::-1]]
    if np.linalg.det(vecs) < 0:
        vecs[:, 0] *= -1
    tf = np.eye(4)
    tf[:3, :3] = vecs.T
    tf[:3, 3] = -vecs.T @ centroid
    return tf


def gsplat_world_transform(sparse_dir: Path) -> np.ndarray:
    """4x4 matrix taking COLMAP model coordinates into the frame gsplat trained in.

    Images are sorted by name before use, as the trainer does; the result does not depend on it.
    """
    images = sorted(read_images_bin(sparse_dir / "images.bin"), key=lambda i: i["name"])
    c2w = np.stack([i["c2w"] for i in images])
    pts, _ = read_points3d_bin(sparse_dir / "points3D.bin")
    pts = pts.astype(np.float32).astype(np.float64)

    def apply(m, p):
        return p @ m[:3, :3].T + m[:3, 3]

    t1 = _similarity_from_cameras(c2w)
    pts = apply(t1, pts)
    t2 = _align_principal_axes(pts)
    pts = apply(t2, pts)
    tf = t2 @ t1
    if np.median(pts[:, 2]) > np.mean(pts[:, 2]):
        t3 = np.diag([1.0, -1.0, -1.0, 1.0])
        tf = t3 @ tf
    return tf
