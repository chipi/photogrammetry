"""RC-P8: pick textured ARKitScenes videos by a stated rule.

Candidates: the first N Training rows with a laser scan, in the upsampling subset and sky
direction Up (the filter the first three videos came from), one per visit, skipping visits
already used. Score: median SIFT keypoint count over 10 evenly spaced vga_wide frames. Needs
each candidate's vga_wide folder downloaded; prints the ranking as JSON.

    python select_arkit.py METADATA RAW_TRAINING_DIR OUT_JSON --exclude 42444515,... [--n 8]
"""

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pycolmap


def candidates(metadata, exclude, n):
    rows = list(csv.DictReader(open(metadata)))
    used_visits = {r["visit_id"] for r in rows if r["video_id"] in exclude}
    out = []
    for r in rows:
        ok = (
            r["fold"] == "Training"
            and r["has_laser_scanner_point_clouds"] == "True"
            and r["is_in_upsampling"] == "True"
            and r["sky_direction"] == "Up"
        )
        if ok and r["video_id"] not in exclude and r["visit_id"] not in used_visits:
            out.append(r["video_id"])
            used_visits.add(r["visit_id"])
        if len(out) == n:
            break
    return out


def sift_median(frames_dir, k=10):
    frames = sorted(frames_dir.glob("*.png"))
    pick = [frames[i] for i in np.linspace(0, len(frames) - 1, k).astype(int)]
    with tempfile.TemporaryDirectory() as tmp:
        img = Path(tmp) / "images"
        img.mkdir()
        for f in pick:
            shutil.copy(f, img / f.name)
        db = Path(tmp) / "db.db"
        pycolmap.extract_features(db, img, device=pycolmap.Device.cpu)
        with pycolmap.Database.open(db) as d:
            counts = [d.num_keypoints_for_image(i.image_id) for i in d.read_all_images()]
    return int(np.median(counts)), len(frames)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metadata", type=Path)
    ap.add_argument("raw", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--list", action="store_true", help="print the candidates and stop")
    args = ap.parse_args()
    cands = candidates(args.metadata, set(args.exclude.split(",")), args.n)
    if args.list:
        print(" ".join(cands))
        return
    scores = {}
    for v in cands:
        d = args.raw / v / "vga_wide"
        scores[v] = dict(zip(("sift_median", "frames"), sift_median(d), strict=True))
        print(v, scores[v], flush=True)
    ranked = sorted(scores, key=lambda v: -scores[v]["sift_median"])
    args.out.write_text(
        json.dumps({"candidates": cands, "scores": scores, "ranked": ranked}, indent=1)
    )
    print("ranked", ranked)


if __name__ == "__main__":
    main()
