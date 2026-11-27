"""RC-M3: the debrief without AI. Templates filled from the same tools the agent uses, the
weakest regions picked by rule, the shots placed by plan_shots. Every sentence carries its
handles, so verify.py checks it exactly as it checks the agent's. Writes data/rules.json.

    cd prototypes/RC-P3-quality
    uv run python ../../mockups/RC-M3-debrief/rules_debrief.py <data>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P3-quality"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import debrief_server
import tools
import verify

RUN = "courtyard/full"
WEAK = 3


def h(tool, field, value, **args):
    if tool in ("get_summary", "list_regions", "get_region"):
        args = {"run": RUN, **args}
    return {"tool": tool, "args": args, "field": field, "value": value}


def pct(x):
    return f"{round(x * 100)}%"


def main():
    data = Path(sys.argv[1])
    s = tools.get_summary(RUN)
    p = debrief_server.get_products()
    reg, rp = s["registration"], s["reprojection"]
    regions = tools.list_regions(RUN)["regions"]
    full = {r["id"]: tools.get_region(RUN, r["id"]) for r in regions}

    best = max(regions, key=lambda r: (r["coverage"], r["points"]))
    b = full[best["id"]]
    flagged = [full[r["id"]] for r in regions if r["flags"]]
    weak = sorted(
        flagged,
        key=lambda r: (
            r["coverage"],
            -r["few_photo_fraction"],
            r["median_triangulation_angle_deg"],
        ),
    )[:WEAK]

    holds = [
        {
            "text": f"{reg['registered']} of {reg['images']} photos registered, in "
            f"{reg['components']} model.",
            "handles": [
                h("get_summary", "registration.registered", reg["registered"]),
                h("get_summary", "registration.images", reg["images"]),
                h("get_summary", "registration.components", reg["components"]),
            ],
        },
        {
            "text": f"Reprojection error {rp['mean_px']:.2f} px on average and "
            f"{rp['p95_px']:.2f} px "
            f"at the 95th percentile, over {rp['points']:,} points.",
            "handles": [
                h("get_summary", "reprojection.mean_px", rp["mean_px"]),
                h("get_summary", "reprojection.p95_px", rp["p95_px"]),
                h("get_summary", "reprojection.points", rp["points"]),
            ],
        },
        {
            "text": f"Best covered: {b['id']}, seen by {b['images_any']} photos, {b['points']:,} "
            f"points, median triangulation angle "
            f"{b['median_triangulation_angle_deg']:.1f} degrees.",
            "region": b["id"],
            "photos": [i["name"] for i in b["images_seeing"][:3]],
            "handles": [
                h("get_region", "images_any", b["images_any"], region_id=b["id"]),
                h("get_region", "points", b["points"], region_id=b["id"]),
                h(
                    "get_region",
                    "median_triangulation_angle_deg",
                    b["median_triangulation_angle_deg"],
                    region_id=b["id"],
                ),
            ],
        },
        {
            "text": "Against the laser scan (not available in the field): mesh F1 "
            f"{p['mesh']['at_10cm']['f1']:.2f} at 10 cm and "
            f"{p['mesh']['at_2cm']['f1']:.2f} at 2 cm.",
            "handles": [
                h("get_products", "mesh.at_10cm.f1", p["mesh"]["at_10cm"]["f1"]),
                h("get_products", "mesh.at_2cm.f1", p["mesh"]["at_2cm"]["f1"]),
            ],
        },
    ]
    is_weak = [
        {
            "text": f"Scale is {s['scale']['state']}: {s['scale']['reason']}.",
            "handles": [h("get_summary", "scale.state", s["scale"]["state"])],
        },
        {
            "text": f"{s['regions']['flagged']} of {s['regions']['total']} regions are flagged; "
            f"median coverage {s['regions']['coverage_median']:.2f}.",
            "handles": [
                h("get_summary", "regions.flagged", s["regions"]["flagged"]),
                h("get_summary", "regions.total", s["regions"]["total"]),
                h("get_summary", "regions.coverage_median", s["regions"]["coverage_median"]),
            ],
        },
    ]
    for r in weak:
        is_weak.append(
            {
                "text": f"{r['id']}: {r['images_any']} photos, median angle "
                f"{r['median_triangulation_angle_deg']:.1f} degrees, "
                f"{pct(r['few_photo_fraction'])} of its points on two photos or fewer, "
                f"unseen across {r['azimuth_gap']['length_deg']} degrees "
                f"({', '.join(r['flags'])}).",
                "region": r["id"],
                "photos": [i["name"] for i in r["images_seeing"][:3]],
                "handles": [
                    h("get_region", "images_any", r["images_any"], region_id=r["id"]),
                    h(
                        "get_region",
                        "median_triangulation_angle_deg",
                        r["median_triangulation_angle_deg"],
                        region_id=r["id"],
                    ),
                    h(
                        "get_region",
                        "few_photo_fraction",
                        r["few_photo_fraction"],
                        region_id=r["id"],
                    ),
                    h(
                        "get_region",
                        "azimuth_gap.length_deg",
                        r["azimuth_gap"]["length_deg"],
                        region_id=r["id"],
                    ),
                ],
            }
        )

    shoot, annotations, spots = [], [], {}
    for r in weak:
        annotations.append(
            {
                "id": f"E{len(annotations) + 1:02d}",
                "kind": "label",
                "text": f"{r['id']}: {', '.join(r['flags'])}",
                "position": r["centre"],
                "region": r["id"],
            }
        )
        plan = debrief_server.suggest_shots(r["id"])
        if plan["found"]:
            spots.setdefault(tuple(plan["position"]), []).append((r, plan))
    for regs in spots.values():
        r, plan = regs[0]
        ids = [x["id"] for x, _ in regs]
        near = plan["nearest_photo"].split("/")[-1]
        shoot.append(
            {
                "text": f"Shoot {' and '.join(ids)} from {plan['nearest_photo_m']} m beside "
                f"{near}, at {plan['height_m']} m: a view {plan['new_angle_deg']:.0f} degrees "
                f"from any photo of it, {plan['distance_m']} m away, clear line of sight.",
                "region": r["id"],
                "photos": [plan["nearest_photo"]],
                "handles": [
                    h(
                        "suggest_shots",
                        "nearest_photo_m",
                        plan["nearest_photo_m"],
                        region_id=r["id"],
                    ),
                    h("suggest_shots", "height_m", plan["height_m"], region_id=r["id"]),
                    h("suggest_shots", "new_angle_deg", plan["new_angle_deg"], region_id=r["id"]),
                    h("suggest_shots", "distance_m", plan["distance_m"], region_id=r["id"]),
                ],
            }
        )
        annotations.append(
            {
                "id": f"E{len(annotations) + 1:02d}",
                "kind": "camera",
                "position": plan["position"],
                "look_at": plan["look_at"],
                "reason": f"{' and '.join(ids)}: new angle {plan['new_angle_deg']:.0f} degrees",
            }
        )

    sections = [
        {"heading": "What holds", "claims": holds},
        {"heading": "What is weak", "claims": is_weak},
        {"heading": "What to shoot next", "claims": shoot},
    ]
    sections = [
        {**sec, "claims": [verify.check_claim(c, data) for c in sec["claims"]]} for sec in sections
    ]
    claims = [c for sec in sections for c in sec["claims"]]
    out = {
        "title": f"Courtyard: {reg['registered']} of {reg['images']} photos registered, scale "
        f"{s['scale']['state']}, {s['regions']['flagged']} regions flagged",
        "by": "rules",
        "sections": sections,
        "count": {
            k: sum(c["status"] == k for c in claims)
            for k in ("supported", "unsupported", "judgement")
        },
        "readiness": verify.readiness(data),
        "annotations": annotations,
    }
    (data / "rules.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["count"]), f"{len(annotations)} annotations")
    for c in claims:
        print(" ", c["status"], c["text"])


if __name__ == "__main__":
    main()
