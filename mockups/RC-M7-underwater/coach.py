"""RC-M7 coach: the facts of both halves, the actions the engine (or the diver) can take, the
rule's plan without AI, and optionally the person's AI as a coach over the same facts.

    python3 coach.py data            # facts, menu and the rule's plan: data/coach_facts.json
    python3 coach.py data ai [model] # also the AI coach: data/ai_coach.json (one `claude -p` call)
    python3 coach.py data --recheck  # re-checks the recorded AI answer, no call
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coach_lib

METHOD = {"camera_wb": "as_seen", "grey_world": "one_wb", "backscatter": "haze_removed"}

ACTIONS = {
    "raw": {"kind": "capture", "text": "Shoot RAW: the published TIFs clipped red to zero."},
    "one_wb": {"kind": "engine", "text": "Apply one white balance from the RAW (grey world)."},
    "haze_removed": {
        "kind": "engine",
        "text": "Remove backscatter fitted by range (needs a range per pixel).",
    },
    "dark_targets": {
        "kind": "capture",
        "text": "Place black targets at three or more ranges, so the haze fit has a known dark.",
    },
    "closer": {"kind": "capture", "text": "Shoot closer: chart contrast falls with range."},
    "overlap": {
        "kind": "capture",
        "text": "Capture many overlapping views, or use a calibrated stereo rig, so the engine "
        "computes ranges itself.",
    },
    "refractive": {
        "kind": "engine",
        "text": "Use the refractive camera model (flat surface, n = 1.333).",
    },
    "calibrate_wet": {
        "kind": "capture",
        "text": "Calibrate in the water, through the same surface or port, before the survey.",
    },
    "board_positions": {
        "kind": "capture",
        "text": "Check scale on a known board at several positions in the volume.",
    },
}


def facts(data: Path) -> dict:
    sq = json.loads((data / "squid.json").read_text())
    aq = json.loads((data / "aquamvs.json").read_text())
    images = {}
    for im in sq["images"]:
        images[im["name"]] = {
            "charts": [
                {
                    "range_m": c["range_m"],
                    "angle_to_grey_deg": {v: c["angle"][k] for k, v in METHOD.items()},
                    "contrast": {v: c["contrast"][k] for k, v in METHOD.items()},
                    "backscatter_over_black_patch": c["b_over_black"],
                }
                for c in im["charts"]
            ],
            "attenuation_beta_per_m": [round(b, 4) for b in im["fit"]["beta"]],
        }
    frames = {
        str(f): {
            m: {
                "scale_error_pct": round(aq[m]["frames"][str(f)]["metrics"]["scale_error_pct"], 2),
                "shape_rmse_mm": round(aq[m]["frames"][str(f)]["metrics"]["rigid_rmse_mm"], 2),
            }
            for m in ("pinhole", "refractive")
        }
        for f in aq["frames"]
    }
    summ = {
        m: {k: round(v, 3) for k, v in aq[m]["summary"].items() if k != "corners"}
        for m in ("pinhole", "refractive")
    }
    return {
        "colour": {
            "site": "SQUID Satil, five images, 15 charts at 5.8 to 18.9 m",
            "tif_red_zero_share_min": 0.78,
            "images": images,
            "all_charts_median_angle_deg": {
                "as_seen": 31.09,
                "one_wb": 1.37,
                "haze_removed": 4.38,
            },
            "all_charts_mean_contrast": {"one_wb": 0.207, "haze_removed": 0.474},
            "ranges_from_our_reconstruction": {
                "geometric_depth_pixels_kept_pct_max": 1.1,
                "fused_points": 0,
                "photos": 16,
                "stereo_pairs": 8,
                "note": "the pairs barely overlap; the ranges shown are SQUID's own stereo",
            },
        },
        "lens": {
            "rig": "AquaMVS, 13 cameras over a flat water surface, a submerged board",
            "summary": summ,
            "frames": frames,
        },
    }


def rule_plan(f: dict) -> dict:
    """The coach without AI: fixed rules over the facts, each with the fact it rests on."""
    charts = [c for im in f["colour"]["images"].values() for c in im["charts"]]
    far = [c for c in charts if c["range_m"] > 15]
    far_contrast = min(c["contrast"]["one_wb"] for c in far if c["contrast"]["one_wb"] is not None)
    over = [c for c in charts if (c["backscatter_over_black_patch"] or 0) > 1]
    max_over = max((c["backscatter_over_black_patch"] for c in over), default=0)
    worst = max(f["lens"]["frames"].values(), key=lambda v: abs(v["pinhole"]["scale_error_pct"]))
    plan = [
        ("raw", "The published TIFs clip red to zero on at least 78% of pixels; the RAW keeps it."),
        (
            "one_wb",
            f"One white balance takes the grey patches from "
            f"{f['colour']['all_charts_median_angle_deg']['as_seen']}° to "
            f"{f['colour']['all_charts_median_angle_deg']['one_wb']}° (median of 15 charts).",
        ),
    ]
    if far_contrast < 0.15:
        plan.append(
            ("closer", f"Beyond 15 m chart contrast falls to {far_contrast:.2f} under any balance.")
        )
    if over:
        plan.append(
            (
                "dark_targets",
                f"On {len(over)} charts the haze fit removes more light than the black patch "
                f"reflects (up to {max_over:.2f} times).",
            )
        )
    plan.append(
        (
            "overlap",
            "Our reconstruction kept at most 1.1% of pixels with depth on these pairs; "
            "haze removal needs ranges.",
        )
    )
    if abs(worst["pinhole"]["scale_error_pct"]) > 1:
        plan += [
            (
                "refractive",
                f"Without it the board measures up to {abs(worst['pinhole']['scale_error_pct'])}% "
                f"too small; with it {worst['refractive']['scale_error_pct']:+}% on that frame.",
            ),
            ("calibrate_wet", "The refractive model is only as good as its calibration."),
            (
                "board_positions",
                "The pinhole error depends on where the board is, so one check is not enough.",
            ),
        ]
    return {
        "headline": "Colour holds with one white balance; haze and refraction need more than "
        "the image.",
        "plan": [{"action": a, "why": w} for a, w in plan],
        "rules": "Rules written for the mock-up: contrast under 0.15 beyond 15 m, a haze fit "
        "over the black patch, pinhole scale error over 1%.",
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
        imgs = [(data / "squid" / f"RGT_4318_{k}.jpg").resolve() for k in METHOD]
        extra = (
            "- The operator surveys underwater sites. Cover colour (SQUID) and measurement "
            "(AquaMVS). Three photos of RGT_4318 (as seen, one white balance, haze removed) are "
            "listed below; what you see in them is your judgement, say so."
        )
        doc = coach_lib.run(f, ACTIONS, extra, imgs, model)
        (data / "ai_coach.json").write_text(json.dumps(doc, indent=1))
        coach_lib.report(doc)
    for step in out["rule"]["plan"]:
        print("rule", step["action"].ljust(16), step["why"])


if __name__ == "__main__":
    main()
