"""RC-P10: the README's tables from runs/p10/{align,walls_seed<n>,components}.json."""

import json
import os
from pathlib import Path

import numpy as np

RUNS = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce")) / "runs/p10"


def scored(w):
    return [p for p in w["lengths"] if "error_pct" in p]


def main():
    align = json.loads((RUNS / "align.json").read_text())
    seeds = {
        int(p.stem.removeprefix("walls_seed")): json.loads(p.read_text())
        for p in sorted(RUNS.glob("walls_seed*.json"))
    }
    comps = json.loads((RUNS / "components.json").read_text())
    videos = list(seeds[min(seeds)])

    print("| Video | Laser frames | LiDAR minus laser depth, median abs / signed |")
    print("|---|---|---|")
    for vid in videos:
        a = align[vid]
        print(
            f"| {vid} | {a['frames']} | {100 * a['median_abs_m']:.1f} cm / "
            f"{a['median_signed_rel_pct']:+.2f}% |"
        )
    print()

    head = " | ".join(f"Seed {s}" for s in seeds)
    print(f"| Video | {head} |")
    print("|---|" + "---|" * len(seeds))
    for vid in videos:
        cells = []
        for rows in seeds.values():
            p = scored(rows[vid])
            cells.append(f"{sum(x['within'] for x in p)}/{len(p)}")
        print(f"| {vid} | " + " | ".join(cells) + " |")
    print()

    print(
        "| Seed | Within / scored | Failed pairs | Error, min / median / max "
        "| Median abs error | Wall RMS, laser / TSDF (mm) |"
    )
    print("|---|---|---|---|---|---|")
    for s, rows in seeds.items():
        p = [(vid, x) for vid in videos for x in scored(rows[vid])]
        e = np.array([x["error_pct"] for _, x in p])
        em = np.array([x["error_m"] for _, x in p])
        fails = "; ".join(
            f"{vid} {x['reference_m']:.2f} m, {x['error_pct']:+.2f}%"
            for vid, x in p
            if not x["within"]
        )
        walls = [w for vid in videos for w in rows[vid]["walls"]]
        ref_rms = np.median([w["reference_rms_m"] for w in walls]) * 1000
        tsdf_rms = np.median([w["tsdf_rms_m"] for w in walls if w["tsdf_rms_m"]]) * 1000
        print(
            f"| {s} | {sum(x['within'] for _, x in p)}/{len(p)} | {fails or 'none'} | "
            f"{e.min():+.2f} / {np.median(e):+.2f} / {e.max():+.2f}% | "
            f"{100 * np.median(np.abs(em)):.1f} cm | {ref_rms:.1f} / {tsdf_rms:.1f} |"
        )
    allp = [x for rows in seeds.values() for vid in videos for x in scored(rows[vid])]
    e = np.array([x["error_pct"] for x in allp])
    print(
        f"\nall seeds: {sum(x['within'] for x in allp)}/{len(allp)} within; "
        f"median {np.median(e):+.2f}%; negative {100 * np.mean(e < 0):.0f}%; "
        f"|error| p90 {np.percentile(np.abs([x['error_m'] for x in allp]), 90) * 100:.1f} cm"
    )
    print()

    print(
        "| Video | Frames | Registered | Components (frames) | Component changes "
        "| Shared frames | One model |"
    )
    print("|---|---|---|---|---|---|---|")
    for vid, c in comps.items():
        sizes = ", ".join(str(x["frames"]) for x in c["components"])
        shared = ", ".join(f"{k}: {v}" for k, v in c["shared_frames"].items()) or "none"
        print(
            f"| {vid} | {c['frames']} | {c['registered']} | {sizes} | {len(c['breaks'])} | "
            f"{shared} | {'yes' if c['one_model'] else 'no'} |"
        )


if __name__ == "__main__":
    main()
