"""RC-P8 agreement check: keep the learned route (MapAnything + bundle adjustment) only where it
agrees with the classical model, without ground truth.

The owner's decision (2026-11-25): the learned route is an optional second route, run where
COLMAP registers too little, kept only after an agreement check against the classical model.

The check, per run:
  - every COLMAP component (colmap_incremental/<n>) that shares at least MIN_SHARED registered
    frames with the learned model is compared with it on those frames: the median disagreement of
    camera-pair relative rotations (no alignment needed), and the median camera-centre residual
    after a Sim(3) fit, as a fraction of the component's extent;
  - the learned model passes only if it agrees with every component it overlaps, within
    ROT_DEG and POS_FRAC; with no overlapping component there is nothing to check and it fails;
  - frames only the learned model registers are the gain, kept only on a pass.

The ground truth (ETH3D's poses, or ARKit's tracking for ARKitScenes) is then used only to score
the check: the same two thresholds applied to the learned model against the reference say
whether it should have passed. Thresholds were set before any run was checked.

Needs pycolmap: uv run --project ../RC-P1-registration python agreement.py
"""

import argparse
import itertools
import json
import os
from pathlib import Path

import numpy as np
import pycolmap
from run_p8 import pose_metrics, rotation_angle_deg, umeyama, world_from_cam

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
RUNS = RECCE / "runs/p8"
SCENES = (
    "pipes",
    "kicker",
    "courtyard",
    "a42444515",
    "a42444821",
    "a42444793",
    "a42444858",
    "a42444873",
)
VARIANTS = ("none", "prior")
MIN_SHARED = 3
ROT_DEG = 2.0
POS_FRAC = 0.02


def registered_poses(rec):
    """{basename: (R_world_from_cam, centre)} for frames that hold 3-D points (RC-P1's rule)."""
    return {
        Path(img.name).name: world_from_cam(img)
        for img in rec.images.values()
        if img.has_pose and img.num_points3D > 0
    }


def reference_poses(scene):
    """Every posed frame of the reference: ETH3D's calibration in the dataset folder, or the
    ARKit tracking that run_p8.py prep-arkit wrote next to the run."""
    path = RUNS / scene / "reference"
    if not path.exists():
        path = RECCE / "datasets/eth3d" / scene / "dslr_calibration_jpg"
    rec = pycolmap.Reconstruction(str(path))
    return {Path(i.name).name: world_from_cam(i) for i in rec.images.values() if i.has_pose}


def compare(a, b):
    """Disagreement of two pose sets on their shared frames, needing no ground truth."""
    names = sorted(set(a) & set(b))
    if len(names) < MIN_SHARED:
        return {"shared": len(names)}
    rel = [
        rotation_angle_deg((a[i][0].T @ a[j][0]).T @ (b[i][0].T @ b[j][0]))
        for i, j in itertools.combinations(names, 2)
    ]
    ca = np.array([a[n][1] for n in names])
    cb = np.array([b[n][1] for n in names])
    s, rot, t = umeyama(ca, cb)
    pos = np.linalg.norm((s * (rot @ ca.T)).T + t - cb, axis=1)
    extent = float(np.linalg.norm(cb.max(0) - cb.min(0)))
    rel_med = float(np.median(rel))
    pos_frac = float(np.median(pos) / extent) if extent > 0 else float("inf")
    return {
        "shared": len(names),
        "relative_rotation_deg_median": round(rel_med, 3),
        "position_frac_of_extent_median": round(pos_frac, 5),
        "agrees": rel_med <= ROT_DEG and pos_frac <= POS_FRAC,
    }


def check_run(run):
    learned = registered_poses(pycolmap.Reconstruction(str(run / "learned_ba/anchored")))
    components, classical = [], {}
    for d in sorted((run / "colmap_incremental").iterdir(), key=lambda p: int(p.name)):
        poses = registered_poses(pycolmap.Reconstruction(str(d)))
        classical.update(poses)
        components.append(
            {"component": int(d.name), "frames": len(poses), **compare(learned, poses)}
        )
    checked = [c for c in components if c["shared"] >= MIN_SHARED]
    passes = bool(checked) and all(c["agrees"] for c in checked)
    gained = sorted(set(learned) - set(classical))
    return (
        learned,
        classical,
        {
            "learned_frames": len(learned),
            "classical_frames": len(classical),
            "gained_frames": len(gained),
            "components": components,
            "passes": passes,
        },
        gained,
    )


def truth(learned, reference, gained):
    """Whether the learned model should pass, from the reference; and how good the gained frames
    are, aligned with the whole learned model."""
    m = pose_metrics(learned, reference)
    should = (
        m.get("relative_rotation_deg_median", np.inf) <= ROT_DEG
        and m.get("position_frac_of_extent_median", np.inf) <= POS_FRAC
    )
    out = {
        "reference_relative_rotation_deg_median": m.get("relative_rotation_deg_median"),
        "reference_position_frac_of_extent_median": m.get("position_frac_of_extent_median"),
        "should_pass": bool(should),
    }
    names = sorted(set(learned) & set(reference))
    shared_gained = [n for n in gained if n in reference]
    if len(names) >= MIN_SHARED and shared_gained:
        e = np.array([learned[n][1] for n in names])
        g = np.array([reference[n][1] for n in names])
        s, rot, t = umeyama(e, g)
        extent = float(np.linalg.norm(g.max(0) - g.min(0)))
        pos = [
            np.linalg.norm(s * rot @ learned[n][1] + t - reference[n][1]) / extent
            for n in shared_gained
        ]
        out["gained_position_frac_of_extent_median"] = round(float(np.median(pos)), 5)
        r_align = rot
        rot_err = [
            rotation_angle_deg(reference[n][0].T @ r_align @ learned[n][0]) for n in shared_gained
        ]
        out["gained_rotation_deg_median"] = round(float(np.median(rot_err)), 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=RUNS / "agreement.json")
    args = ap.parse_args()
    rows = []
    for scene in SCENES:
        for variant in VARIANTS:
            run = RUNS / scene / variant
            if not (run / "learned_ba/anchored").exists():
                continue
            learned, _classical, verdict, gained = check_run(run)
            reference = reference_poses(scene)
            rows.append(
                {"scene": scene, "variant": variant, **verdict, **truth(learned, reference, gained)}
            )
    args.out.write_text(json.dumps(rows, indent=1))
    print(
        "| Scene | Variant | Learned | Classical | Gained | Components checked | Check | "
        "Reference: rel. rot. (°) / pos. (% extent) | Should pass | Verdict |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        checked = [c for c in r["components"] if c["shared"] >= MIN_SHARED]
        comp = (
            "; ".join(
                f"{c['component']}: {c['relative_rotation_deg_median']}° / "
                f"{100 * c['position_frac_of_extent_median']:.2f}%"
                for c in checked
            )
            or "none"
        )
        verdict = {
            (True, True): "right pass",
            (False, False): "right reject",
            (True, False): "WRONG pass",
            (False, True): "missed gain",
        }[(r["passes"], r["should_pass"])]
        rr, rp = (
            r["reference_relative_rotation_deg_median"],
            r["reference_position_frac_of_extent_median"],
        )
        ref = f"{rr} / {100 * rp:.2f}" if rr is not None else "n/a"
        print(
            f"| {r['scene']} | {r['variant']} | {r['learned_frames']} | {r['classical_frames']} | "
            f"{r['gained_frames']} | {comp} | {'pass' if r['passes'] else 'reject'} | {ref} | "
            f"{'yes' if r['should_pass'] else 'no'} | {verdict} |"
        )
    print(
        "gained-frame accuracy:",
        json.dumps(
            {
                f"{r['scene']}/{r['variant']}": {
                    k: r[k]
                    for k in ("gained_position_frac_of_extent_median", "gained_rotation_deg_median")
                    if k in r
                }
                for r in rows
                if r["gained_frames"]
            },
            indent=None,
        ),
    )


if __name__ == "__main__":
    main()
