"""RC-M3: where to stand for a new photo of a weak region, from geometry alone (no AI).

The engine's rule, which both the rule-written debrief and the AI layer use:
- at hand height: the median height of the cameras that took the set;
- inside the area the photographer walked: the cameras' footprint, 1 m wider;
- on the side the region's surface faces: the side its current photos were taken from, with the
  line of sight within 70 degrees of the surface normal (a plane fitted to the region's points);
- with a clear line of sight: at most 3 points within 0.3 m of the ray to the region;
- at a distance like the current photos' (0.6 to 1.6 times their median, at least 2 m);
- a new direction: at least 15 degrees in azimuth from every photo that sees the region.
Among the spots that pass, the widest new angle wins (capped at 60 degrees), less a penalty for
standing more than 3 m from any photo already taken.
"""

import json
from pathlib import Path

import numpy as np

GRID_M = 0.5
MARGIN_M = 1.0
CLEAR_M = 0.3
MAX_BLOCKING = 3
MAX_VIEW_DEG = 70
MIN_GAIN_DEG = 15
GAIN_CAP_DEG = 60
NEAR_M = 3.0


def load(data: Path):
    scene = json.loads((data / "scene.json").read_text())
    xyz = np.array(scene["points"]["xyz"]).reshape(-1, 3)
    regions = np.array(scene["points"]["region"])
    return scene, xyz, regions


def suggest(region: dict, scene: dict, xyz: np.ndarray, point_region: np.ndarray) -> dict:
    cams = {c["name"]: np.array(c["centre"]) for c in scene["cameras"]}
    allc = np.array(list(cams.values()))
    seeing = np.array([cams[i["name"]] for i in region["images_seeing"] if i["name"] in cams])
    pts = xyz[point_region == region["id"]]
    target = pts.mean(0) if len(pts) else np.array(region["centre"])
    out = {"region": region["id"], "look_at": target.round(2).tolist()}
    if len(seeing) == 0 or len(pts) < 3:
        return {**out, "found": False, "reason": "no photo or too few points to fit the surface"}

    # The surface's normal, turned towards the side its photos were taken from.
    _, _, vt = np.linalg.svd(pts - target)
    normal = vt[2]
    if (seeing.mean(0) - target) @ normal < 0:
        normal = -normal

    height = float(np.median(allc[:, 2]))
    lo, hi = allc[:, :2].min(0) - MARGIN_M, allc[:, :2].max(0) + MARGIN_M
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0], GRID_M), np.arange(lo[1], hi[1], GRID_M))
    cand = np.c_[gx.ravel(), gy.ravel(), np.full(gx.size, height)]

    def azimuth(p):
        d = p[..., :2] - target[:2]
        return np.degrees(np.arctan2(d[..., 1], d[..., 0]))

    seen_az = azimuth(seeing)
    dist = np.linalg.norm(cand[:, :2] - target[:2], axis=1)
    ref = float(np.median(np.linalg.norm(seeing[:, :2] - target[:2], axis=1)))
    ok = (dist >= max(2.0, 0.6 * ref)) & (dist <= 1.6 * ref)
    ray = cand - target
    view = np.degrees(np.arccos(np.clip((ray @ normal) / np.linalg.norm(ray, axis=1), -1, 1)))
    ok &= view <= MAX_VIEW_DEG
    diff = np.abs((azimuth(cand)[:, None] - seen_az[None, :] + 180) % 360 - 180)
    gain = diff.min(1)
    ok &= gain >= MIN_GAIN_DEG
    nearest = np.linalg.norm(cand[:, None, :] - allc[None, :, :], axis=2).min(1)
    score = np.minimum(gain, GAIN_CAP_DEG) - 5 * np.maximum(0, nearest - NEAR_M)
    order = [i for i in np.argsort(-score) if ok[i]]

    names = list(cams)
    for i in order[:400]:
        seg = target - cand[i]
        s = np.clip(((xyz - cand[i]) @ seg) / (seg @ seg), 0, 1)
        off = np.linalg.norm(xyz - (cand[i] + s[:, None] * seg), axis=1)
        blocking = int(((off < CLEAR_M) & (s > 0.05) & (s < 0.85)).sum())
        if blocking > MAX_BLOCKING:
            continue
        k = int(np.linalg.norm(allc - cand[i], axis=1).argmin())
        return {
            **out,
            "found": True,
            "position": cand[i].round(2).tolist(),
            "new_angle_deg": round(float(gain[i]), 1),
            "distance_m": round(float(dist[i]), 1),
            "view_to_surface_deg": round(float(view[i]), 1),
            "height_m": round(height, 2),
            "nearest_photo": names[k],
            "nearest_photo_m": round(float(nearest[i]), 1),
            "blocking_points": blocking,
        }
    return {
        **out,
        "found": False,
        "reason": "no spot passes height, side, distance, angle and line of sight",
    }
