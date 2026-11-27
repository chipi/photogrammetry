"""RC-M2 coach: what the room's coverage says, the actions the engine (or the person with the
phone) can take, the rule's plan without AI, and optionally the person's AI as a coach.

    python3 coach.py data            # facts, menu and the rule's plan: data/coach_facts.json
    python3 coach.py data ai [model] # also the AI coach: data/ai_coach.json (one `claude -p` call)
    python3 coach.py data --recheck  # re-checks the recorded AI answer, no call
"""

import json
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coach_lib

ACTIONS = {
    "ghost_shot": {
        "kind": "capture",
        "text": "Take the shot the engine placed: stand at the ghost camera, face the marked wall.",
    },
    "revisit_weak": {
        "kind": "capture",
        "text": "Walk the weakly seen areas again, closer and from a second side.",
    },
    "floor_ceiling": {
        "kind": "capture",
        "text": "Sweep the floor and ceiling no frame saw: tilt the phone down, then up.",
    },
    "reference_check": {
        "kind": "capture",
        "text": "Check one distance with a tape or laser where accuracy matters.",
    },
    "show_shadow": {"kind": "engine", "text": "Show light and shadow: where frames were few."},
    "show_confidence": {
        "kind": "engine",
        "text": "Show the model's support, hatched below its threshold.",
    },
    "show_structure": {
        "kind": "engine",
        "text": "Show the structured room: walls, floor and ceiling as measured, inferred or "
        "unknown, with each measurement's sigma.",
    },
}


def read(data: Path, meta: dict, key: str, code: str) -> array:
    lay = meta["layout"][key]
    n = 1
    for s in lay["shape"]:
        n *= s
    a = array(code)
    with open(data / "room.bin", "rb") as f:
        f.seek(lay["offset"])
        a.frombytes(f.read(n * a.itemsize))
    return a


def facts(data: Path) -> dict:
    meta = json.loads((data / "room.json").read_text())
    views = read(data, meta, "views", "H")
    sectors = read(data, meta, "sectors", "H")
    err = read(data, meta, "error_mm", "H")
    n = len(views)
    share = lambda pred: round(sum(1 for v in views if pred(v)) / n, 3)  # noqa: E731
    dirs = [bin(s).count("1") for s in sectors]
    one_dir = round(sum(1 for v, k in zip(views, dirs, strict=True) if v >= 4 and k == 1) / n, 3)
    by_dirs = {}
    for v, k, e in zip(views, dirs, err, strict=True):
        if v >= 16 and e < 65535:
            by_dirs.setdefault(min(k, 3), []).append(e)
    by_dirs_mm = {
        ("1", "2", "3_or_more")[k - 1]: sorted(g)[len(g) // 2] for k, g in sorted(by_dirs.items())
    }
    el = meta["scene"]["elements"]
    unknown = {e["id"]: e["attributes"].get("area_m2") for e in el if e["source"] == "unknown"}
    return {
        "room": f"ARKitScenes {meta['video']}, iPhone LiDAR video; a Faro laser scan exists only "
        "because this is a benchmark",
        "frames_counted": meta["frames_used"],
        "vertices": n,
        "share_seen_by_0_frames": share(lambda v: v == 0),
        "share_seen_by_under_4_frames": share(lambda v: v < 4),
        "share_seen_by_32_or_more": share(lambda v: v >= 32),
        "share_seen_from_one_horizontal_direction": one_dir,
        "faro_median_mm_by_directions_where_16_or_more_frames": by_dirs_mm,
        "error_against_faro_by_frames": [
            {
                "frames_from": b["views"][0],
                "frames_to": b["views"][1],
                "vertices": b["vertices"],
                "median_mm": b["error_mm_median"],
                "p90_mm": b["error_mm_p90"],
            }
            for b in meta["error_by_views"]
        ],
        "next_shot": {
            "weak_wall_vertices": meta["ghost"]["weak_vertices"],
            "standoff_m": meta["ghost"]["standoff_m"],
            "rule": meta["ghost"]["rule"],
        },
        "structure": {
            "walls_measured": sum(e["kind"] == "wall" and e["source"] == "measured" for e in el),
            "unknown_area_m2": unknown,
            "wall_sigma_m_max": max(e["sigma_m"] for e in el if e["kind"] == "wall"),
            "room_height_m": next(
                m["value_m"] for m in meta["scene"]["measurements"] if m["id"] == "height"
            ),
            "room_height_sigma_m": next(
                m["sigma_m"] for m in meta["scene"]["measurements"] if m["id"] == "height"
            ),
        },
        "support_threshold": 0.55,
    }


def rule_plan(f: dict) -> dict:
    b = f["error_against_faro_by_frames"]
    plan = [
        (
            "show_shadow",
            f"{f['share_seen_by_under_4_frames'] * 100:.1f}% of the surface was seen by fewer than "
            f"4 frames; there the error runs {b[0]['median_mm']} mm (median, unseen) against "
            f"{b[-1]['median_mm']} mm where 32 or more frames saw it.",
        ),
        (
            "ghost_shot",
            f"The largest weak wall patch has {f['next_shot']['weak_wall_vertices']} vertices "
            "seen by fewer than 4 frames.",
        ),
    ]
    d = f["faro_median_mm_by_directions_where_16_or_more_frames"]
    if f["share_seen_from_one_horizontal_direction"] > 0.3 and d["1"] - d["3_or_more"] >= 3:
        plan.append(
            (
                "revisit_weak",
                f"{f['share_seen_from_one_horizontal_direction'] * 100:.0f}% of the surface was "
                f"seen from one horizontal direction only; even where 16 or more frames saw it, "
                f"that is {d['1']} mm off against {d['3_or_more']} mm from three or more.",
            )
        )
    unk = f["structure"]["unknown_area_m2"]
    if unk:
        plan.append(
            (
                "floor_ceiling",
                "No frame saw "
                + " and ".join(f"{a:.1f} m² of {k.split('-')[0]}" for k, a in unk.items())
                + ".",
            )
        )
    plan += [
        (
            "show_structure",
            f"Each wall is measured to {f['structure']['wall_sigma_m_max'] * 1000:.0f} mm "
            "(sigma) or better; the unseen parts are marked unknown, not guessed.",
        ),
        (
            "reference_check",
            f"Even well-seen surfaces miss by up to {b[-1]['p90_mm']} mm (90th percentile); "
            "the laser check exists only on this benchmark.",
        ),
    ]
    return {
        "headline": "The room is mostly well seen; the weak walls and the unseen floor and "
        "ceiling are where the model is least right.",
        "plan": [{"action": a, "why": w} for a, w in plan],
        "rules": "Rules written for the mock-up: fewer than 4 frames is weak; one direction means "
        "one of the glyph's 12 horizontal sectors; unknown areas from RC-P13.",
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
            "- The operator scanned one room with an iPhone (LiDAR video). The error against "
            "the laser scan is known only because this is a benchmark: in the field the "
            "operator has the frame counts, not the truth. Coach for the next visit."
        )
        doc = coach_lib.run(f, ACTIONS, extra, None, model)
        (data / "ai_coach.json").write_text(json.dumps(doc, indent=1))
        coach_lib.report(doc)
    for step in out["rule"]["plan"]:
        print("rule", step["action"].ljust(16), step["why"])


if __name__ == "__main__":
    main()
