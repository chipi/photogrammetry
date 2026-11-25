"""RC-P8: one Markdown table from every SCENE/VARIANT/results.json under a runs folder.

python summarize.py ~/.cache/recce/runs/p8 > table.md
"""

import json
import sys
from pathlib import Path

SCENES = [
    "pipes",
    "kicker",
    "courtyard",
    "a42444515",
    "a42444821",
    "a42444793",
    "a42444858",
    "a42444873",
]
ROUTES = ["colmap_incremental", "glomap_global", "mapanything", "mapanything_ba"]


def fmt(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def row(scene, variant, route, r, n):
    if not isinstance(r, dict) or "error" in r:
        err = r.get("error", r) if isinstance(r, dict) else r
        return f"| {scene} | {variant} | {route} | failed: {str(err)[:60]} |" + " |" * 8
    pe = r.get("pose_error") or {}
    if isinstance(pe, str):
        pe = {}
    reg = r.get("registered")
    scale = (r.get("scale") or {}).get("scale_error_pct")
    if route == "mapanything":
        scale = pe.get("scale_error_pct")
        reg = n
    drift = (r.get("anchor_to_learned") or {}).get("ba_scale_drift_pct")
    t = r.get("timings") or {}
    secs = sum(v for k, v in t.items() if k != "model_load_s")
    return (
        f"| {scene} | {variant} | {route} | {reg}/{n} | {fmt(pe.get('rotation_deg_median'))} "
        f"| {fmt(pe.get('relative_rotation_deg_median'))} "
        f"| {fmt(pe.get('position_m_median'), 3)} "
        f"| {fmt(pe.get('position_frac_of_extent_median', 0) * 100 if pe else None)} "
        f"| {fmt(scale, 1)} | {fmt(drift, 1)} | {fmt(r.get('reprojection_error_mean_px'))} "
        f"| {secs:.0f} |"
    )


def main():
    root = Path(sys.argv[1])
    print(
        "| Scene | Priors | Route | Registered | Rot. (°) | Rel. rot. (°) | Pos. (m) "
        "| Pos. (% extent) | Scale err. (%) | BA drift (%) | Reproj. (px) | Time (s) |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for s in SCENES:
        for v in ("none", "prior"):
            p = root / s / v / "results.json"
            if not p.exists():
                print(f"| {s} | {v} | missing |" + " |" * 9)
                continue
            res = json.loads(p.read_text())
            for route in ROUTES:
                print(row(s, v, route, res["routes"].get(route, "absent"), res["images"]))


if __name__ == "__main__":
    main()
