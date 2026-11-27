"""RC-M1 coach: what the run says (both solvers on ETH3D kicker), the actions the engine (or the
photographer) can take, the rule's plan without AI, and optionally the person's AI as a coach.

    python3 coach.py data            # facts, menu and the rule's plan: data/coach_facts.json
    python3 coach.py data ai [model] # also the AI coach: data/ai_coach.json (one `claude -p` call)
    python3 coach.py data --recheck  # re-checks the recorded AI answer, no call
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coach_lib

ACTIONS = {
    "incremental": {
        "kind": "engine",
        "text": "Map with the incremental solver (COLMAP): adds photos one at a time and refines "
        "as it goes.",
    },
    "global": {
        "kind": "engine",
        "text": "Map with the global solver (GLOMAP): poses every photo at once.",
    },
    "show_coverage": {
        "kind": "engine",
        "text": "Show coverage: where few photos agree on a point and where their rays nearly "
        "coincide.",
    },
    "show_unjoined": {"kind": "engine", "text": "Show the photo that did not join the model."},
    "drop_weak_points": {
        "kind": "engine",
        "text": "Drop points seen by only 2 photos or with rays under 5 degrees apart before "
        "meshing or measuring.",
    },
    "ghost_shot": {
        "kind": "capture",
        "text": "Take the next shot the engine placed, from the open side of the weakest region.",
    },
    "reshoot_unjoined": {
        "kind": "capture",
        "text": "Retake the photo that did not join, overlapping its neighbours more.",
    },
    "spread_photos": {
        "kind": "capture",
        "text": "Add photos around the parts that rest on a few photos, so no handful carries "
        "the model.",
    },
    "add_scale": {
        "kind": "capture",
        "text": "Put a scale bar, or two markers at a measured distance, in the scene.",
    },
}

LABEL = {"colmap_incremental": "incremental", "glomap_global": "global"}


def points_facts(pts: list) -> dict:
    n = len(pts)
    angles = sorted(p["a"] for p in pts)
    errs = sorted(p["e"] for p in pts)
    return {
        "share_seen_by_only_2_photos": round(sum(len(p["t"]) == 2 for p in pts) / n, 3),
        "share_rays_under_5_deg": round(sum(p["a"] < 5 for p in pts) / n, 3),
        "median_ray_angle_deg": round(angles[n // 2], 1),
        "share_reprojection_over_4_px": round(sum(e > 4 for e in errs) / n, 3),
    }


def strategy_facts(run: dict, key: str) -> dict:
    r = run["results"]["strategies"][key]
    s = run["strategies"][key]
    cams = s["cameras"]
    obs = sum(c["points"] for c in cams)
    top = sorted(cams, key=lambda c: -c["points"])[:3]
    joined = {c["name"] for c in cams if c["points"] > 0}
    pe = r["pose_error"]
    return {
        "registered": r["registered"],
        "posed_without_points": r["posed_without_points"],  # posed, but tied to no point
        "not_in_model": sorted(n for n in run["images"] if n not in joined),
        "points": r["points3D"],
        "reprojection_mean_px": r["reprojection_error_mean_px"],
        "reprojection_p95_px": r["reprojection_error_p95_px"],
        "mean_track_length": r["mean_track_length"],
        "mapping_s": r["timings"]["mapping_s"],
        **points_facts(s["points"]),
        "top_3_photos_share_of_observations": round(sum(c["points"] for c in top) / obs, 3),
        "top_3_photos": [c["name"] for c in top],
        "camera_position_error_cm_median": round(pe["position_m_median"] * 100, 1),
        "camera_position_error_share_of_scene_max": round(pe["position_frac_of_extent_max"], 4),
        "camera_rotation_error_deg_median": round(pe["rotation_deg_median"], 2),
    }


def facts(data: Path) -> dict:
    run = json.loads((data / "run.json").read_text())
    res = run["results"]
    return {
        "scene": f"ETH3D {res['scene']}, {res['images']} photos of an indoor scene; ETH3D's survey "
        "exists only because this is a benchmark",
        "photos": res["images"],
        "shared_s": {
            "features": res["shared_timings"]["features_s"],
            "matching": res["shared_timings"]["matching_s"],
        },
        "solvers": {LABEL[k]: strategy_facts(run, k) for k in res["strategies"]},
        "scale": "none: no scale bar, markers or pose priors; metres on the page come from "
        "aligning to the survey",
        "scene_extent_m": res["strategies"]["colmap_incremental"]["pose_error"]["scene_extent_m"],
    }


def rule_plan(f: dict) -> dict:
    inc, glo = f["solvers"]["incremental"], f["solvers"]["global"]
    plan = []
    if glo["reprojection_p95_px"] > 2 * inc["reprojection_p95_px"]:
        plan.append(
            (
                "incremental",
                f"The global solver maps {inc['mapping_s'] / glo['mapping_s']:.1f} times faster, "
                f"but its 95th-percentile reprojection is {glo['reprojection_p95_px']:.1f} px "
                f"against {inc['reprojection_p95_px']:.1f} px.",
            )
        )
    if inc["not_in_model"]:
        plan += [
            ("show_unjoined", f"{', '.join(inc['not_in_model'])} is not in the model."),
            ("reshoot_unjoined", "A photo joins when it shares enough points with its neighbours."),
        ]
    if inc["share_seen_by_only_2_photos"] > 0.25 or inc["share_rays_under_5_deg"] > 0.1:
        plan += [
            (
                "show_coverage",
                f"{inc['share_seen_by_only_2_photos'] * 100:.0f}% of points are seen by only 2 "
                f"photos; {inc['share_rays_under_5_deg'] * 100:.0f}% rest on rays under 5° apart.",
            ),
            ("ghost_shot", "The coverage view places the shot that closes the weakest region."),
        ]
    if inc["top_3_photos_share_of_observations"] > 0.2:
        plan.append(
            (
                "spread_photos",
                f"Three photos hold {inc['top_3_photos_share_of_observations'] * 100:.0f}% of the "
                "observations.",
            )
        )
    plan.append(("add_scale", "Nothing in the capture gives metres; the solver cannot know them."))
    return {
        "headline": "The model holds, but its scale is unknown and part of it rests on few photos.",
        "plan": [{"action": a, "why": w} for a, w in plan],
        "rules": "Rules written for the mock-up: the global solver's 95th-percentile reprojection "
        "over twice the incremental one's, over 25% of points on 2 photos or over 10% on rays "
        "under 5°, three photos over 20% of observations.",
    }


def main() -> None:
    data = Path(sys.argv[1])
    f = facts(data)
    out = {"facts": f, "actions": ACTIONS, "rule": rule_plan(f)}
    (data / "coach_facts.json").write_text(json.dumps(out, indent=1))
    mode = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == "--recheck":
        coach_lib.report(coach_lib.recheck(data / "ai_coach.json", f, ACTIONS))
    elif mode == "ai":
        model = sys.argv[3] if len(sys.argv) > 3 else "sonnet"
        extra = (
            "- The operator photographed one scene and ran both solvers. The camera errors are "
            "known only because this is a benchmark; in the field the operator has the run's own "
            "numbers, not the truth. Say which solver to keep and what to shoot next."
        )
        doc = coach_lib.run(f, ACTIONS, extra, None, model)
        (data / "ai_coach.json").write_text(json.dumps(doc, indent=1))
        coach_lib.report(doc)
    for step in out["rule"]["plan"]:
        print("rule", step["action"].ljust(18), step["why"])


if __name__ == "__main__":
    main()
