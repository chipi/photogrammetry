"""RC-P4 measurements 1 and 4 on the textured mesh: texture resolution per surface area, texel
source count, and seam contrast.

Reads texrecon's output for a run (textured.obj, its atlases, textured_labeling.vec) and the input
mesh_crop.ply. The OBJ keeps the input mesh's vertex numbering, so each OBJ face is matched to its
input face, and so to its label: 0 is unseen, k is source view k - 1.

  resolution  per face: atlas texels over the face's area, as texels per square metre and as the
              side of one texel in millimetres (area-weighted percentiles)
  sources     texrecon picks one view per face (MRF labelling), so a seen face's texels come from
              exactly one photo; faces texrecon kept although unseen are filled by interpolation
              and come from none. Reported as shares of faces and of area
  seams       for an edge shared by two faces, the colour just inside each face (2 texels from the
              edge midpoint, toward the face's own centroid in the atlas), as CIELAB; the CIE76
              colour difference across the edge. Seam edges join faces with different labels;
              interior edges join faces with the same label and the same texture coordinates at
              both ends, and give the baseline

Needs numpy and OpenCV (RC-P12's environment):
uv run --project ../RC-P12-underwater python measure_texture.py [run]
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
INSET_TEXELS = 2.0
MAX_EDGES = 60_000
SEED = 0


def read_obj(path):
    v, vt, faces, fvt, fmat = [], [], [], [], []
    mats, cur = {}, -1
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                v.append(line.split()[1:4])
            elif line.startswith("vt "):
                vt.append(line.split()[1:3])
            elif line.startswith("usemtl"):
                cur = mats.setdefault(line.split()[1], len(mats))
            elif line.startswith("f "):
                parts = [p.split("/") for p in line.split()[1:4]]
                faces.append([int(p[0]) - 1 for p in parts])
                fvt.append([int(p[1]) - 1 for p in parts])
                fmat.append(cur)
    names = {i: n for n, i in mats.items()}
    return (
        np.array(v, dtype=np.float64),
        np.array(vt, dtype=np.float64),
        np.array(faces),
        np.array(fvt),
        np.array(fmat),
        names,
    )


def read_ply_faces(path):
    """Faces of a binary little-endian PLY with float xyz vertices and uchar-count int faces."""
    raw = Path(path).read_bytes()
    end = raw.index(b"end_header\n") + len(b"end_header\n")
    header = raw[:end].decode().splitlines()
    nv = next(int(h.split()[2]) for h in header if h.startswith("element vertex"))
    nf = next(int(h.split()[2]) for h in header if h.startswith("element face"))
    start = end + nv * 12
    rec = np.frombuffer(
        raw[start : start + nf * 13], dtype=np.dtype([("n", "u1"), ("i", "<i4", 3)])
    )
    if not np.all(rec["n"] == 3):
        raise ValueError("expected triangles")
    return rec["i"]


def key(tri):
    s = np.sort(tri, axis=1).astype(np.int64)
    return (s[:, 0] * 1_000_000 + s[:, 1]) * 1_000_000 + s[:, 2]


def srgb_to_lab(rgb):
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack(
        [116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1
    )


def weighted_pct(x, w, q):
    o = np.argsort(x)
    c = np.cumsum(w[o]) / w.sum()
    return [float(x[o][np.searchsorted(c, p / 100)]) for p in q]


def face_labels(mesh, faces):
    labels_in = np.fromfile(mesh / "textured_labeling.vec", dtype="<u8")
    faces_in = read_ply_faces(mesh / "mesh_crop.ply")
    if len(labels_in) != len(faces_in):
        raise ValueError("labeling does not match the input mesh")
    lookup = dict(zip(key(faces_in).tolist(), labels_in.tolist(), strict=True))
    labels = np.array([lookup.get(k, -1) for k in key(faces).tolist()])
    if np.any(labels < 0):
        raise ValueError(f"{int(np.sum(labels < 0))} OBJ faces not found in the input mesh")
    return labels, labels_in


def resolution(area, uv, seen):
    duv1, duv2 = uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]
    texels = 0.5 * np.abs(duv1[:, 0] * duv2[:, 1] - duv1[:, 1] * duv2[:, 0])
    ok = (area > 0) & (texels > 0)
    side_mm = np.full(len(area), np.nan)
    side_mm[ok] = 1000 * np.sqrt(area[ok] / texels[ok])
    res = {}
    for name, m in (("seen", seen & ok), ("filled", ~seen & ok)):
        q = weighted_pct(side_mm[m], area[m], [10, 50, 90])
        res[name] = {
            "faces": int(m.sum()),
            "area_m2": round(float(area[m].sum()), 2),
            "texel_side_mm_p10_p50_p90": [round(x, 2) for x in q],
            "texels_per_m2_median": round(1e6 / q[1] ** 2),
        }
    return res


def classify_edges(faces, fvt, fmat, labels):
    """Edges shared by exactly two faces, as seam, interior or hole border."""
    edge_faces = defaultdict(list)
    for f, tri in enumerate(faces):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_faces[(min(tri[a], tri[b]), max(tri[a], tri[b]))].append((f, a, b))
    kinds = {"seam": [], "interior": [], "hole_border": []}
    for fs in edge_faces.values():
        if len(fs) != 2:
            continue
        (f1, a1, b1), (f2, a2, b2) = fs
        l1, l2 = labels[f1], labels[f2]
        if (l1 == 0) != (l2 == 0):
            kinds["hole_border"].append(fs)
        elif l1 > 0 and l1 != l2:
            kinds["seam"].append(fs)
        elif l1 > 0 and fmat[f1] == fmat[f2]:
            t1 = {faces[f1][a1]: fvt[f1][a1], faces[f1][b1]: fvt[f1][b1]}
            t2 = {faces[f2][a2]: fvt[f2][a2], faces[f2][b2]: fvt[f2][b2]}
            if t1 == t2:
                kinds["interior"].append(fs)
    return kinds


def sample_points(kinds, uv, fmat):
    """(kind, edge, side, material, x, y) just inside each face of each sampled edge."""
    rng = np.random.default_rng(SEED)
    samples = []
    for k, edges in enumerate(kinds.values()):
        for e in rng.choice(len(edges), min(MAX_EDGES, len(edges)), replace=False):
            for side, (f, a, b) in enumerate(edges[e]):
                mid = 0.5 * (uv[f][a] + uv[f][b])
                d = uv[f].mean(0) - mid
                n = np.linalg.norm(d)
                if n > 1e-9:
                    pt = mid + d / n * min(INSET_TEXELS, 0.5 * n)
                    samples.append((k, e, side, fmat[f], pt[0], pt[1]))
    return np.array(samples)


def sample_colours(mesh, names, sizes, s):
    colour = np.zeros((len(s), 3))
    for m in np.unique(s[:, 3]).astype(int):
        img = cv2.imread(str(mesh / f"textured_{names[m]}_map_Kd.png"))[:, :, ::-1]
        idx = np.where(s[:, 3] == m)[0]
        w, h = sizes[m]
        x = np.clip(np.round(s[idx, 4] - 0.5).astype(int), 0, w - 1)
        y = np.clip(np.round((1 - s[idx, 5] / h) * h - 0.5).astype(int), 0, h - 1)
        colour[idx] = img[y, x]
    return colour


def seam_stats(kinds, s, colour):
    lab = srgb_to_lab(colour)
    seams = {}
    for k, name in enumerate(kinds):
        sel = s[:, 0] == k
        by_edge = defaultdict(dict)
        for row, val in zip(s[sel], lab[sel], strict=True):
            by_edge[int(row[1])][int(row[2])] = val
        pairs = [d for d in by_edge.values() if len(d) == 2]
        de = np.array([np.linalg.norm(d[0] - d[1]) for d in pairs])
        dl = np.array([abs(d[0][0] - d[1][0]) for d in pairs])
        seams[name] = {
            # A sample in the atlas padding reads black; a high share means the lookup misses.
            "black_sample_share": round(float(np.mean(colour[sel].sum(1) == 0)), 4),
            "edges": len(kinds[name]),
            "sampled": len(de),
            "delta_e76_p50_p90": [round(float(x), 2) for x in np.percentile(de, [50, 90])],
            "share_delta_e_over_5": round(float(np.mean(de > 5)), 3),
            "delta_lightness_p50_p90": [round(float(x), 2) for x in np.percentile(dl, [50, 90])],
        }
    return seams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", default="courtyard_3000_p1")
    args = ap.parse_args()
    mesh = RECCE / "runs/p4" / args.run / "mesh"
    v, vt, faces, fvt, fmat, names = read_obj(mesh / "textured.obj")
    labels, labels_in = face_labels(mesh, faces)
    sizes = {}
    for i, n in names.items():
        img = cv2.imread(str(mesh / f"textured_{n}_map_Kd.png"), cv2.IMREAD_UNCHANGED)
        sizes[i] = img.shape[1], img.shape[0]
    wh = np.array([sizes[m] for m in fmat], dtype=np.float64)
    p = v[faces]
    area = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    uv = vt[fvt] * wh[:, None, :]
    seen = labels > 0
    kinds = classify_edges(faces, fvt, fmat, labels)
    s = sample_points(kinds, uv, fmat)
    out = {
        "run": args.run,
        "faces_obj": len(faces),
        "faces_input": len(labels_in),
        "faces_unseen_dropped": int(np.sum(labels_in == 0)) - int(np.sum(~seen)),
        "extent_m": (v.max(0) - v.min(0)).round(2).tolist(),
        "views_used": len(np.unique(labels[seen])),
        "resolution": resolution(area, uv, seen),
        "sources": {
            "one_photo_faces_share": round(float(seen.mean()), 4),
            "one_photo_area_share": round(float(area[seen].sum() / area.sum()), 4),
            "interpolated_faces_share": round(float((~seen).mean()), 4),
            "interpolated_area_share": round(float(area[~seen].sum() / area.sum()), 4),
        },
        "seams": seam_stats(kinds, s, sample_colours(mesh, names, sizes, s)),
    }
    path = RECCE / "runs/p4" / f"measure_texture_{args.run}.json"
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
