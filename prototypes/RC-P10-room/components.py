"""RC-P10, photos only: does the room register as one model; if not, where are links missing?

Reads RC-P8's photos-only COLMAP runs (runs/p8/a<video>/none/colmap_incremental/<n>), made from
every 12th vga_wide frame with no pose priors. Each frame of the capture, in time order, is labelled
with the component that registered it (with 3-D points, RC-P1's rule) or as unregistered. The
report is what the engine can say without ARKit: the components, their frames, and the frames on
either side of each break in the sequence. ARKit's poses are used only afterwards, to say where in
the room each break is (camera position and heading on either side).

Needs pycolmap: uv run --project ../RC-P1-registration python components.py
"""

import itertools
import json
import os
from pathlib import Path

import numpy as np
import pycolmap

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
P8 = RECCE / "runs/p8"
OUT = RECCE / "runs/p10/components.json"
VIDEOS = ("42444515", "42444793", "42444821", "42444858", "42444873")


def stamp(name):
    return float(Path(name).stem.split("_")[1])


def world_from_cam(img):
    rot = img.cam_from_world().rotation.matrix()
    t = img.cam_from_world().translation
    return rot.T, -rot.T @ t


def segments(labels):
    """Runs of equal labels over the time-ordered frames: [(label, first index, last index)]."""
    out = []
    for i, lab in enumerate(labels):
        if out and out[-1][0] == lab:
            out[-1][2] = i
        else:
            out.append([lab, i, i])
    return out


def report(vid):
    run = P8 / f"a{vid}"
    ref = pycolmap.Reconstruction(str(run / "reference"))
    poses = {Path(i.name).name: world_from_cam(i) for i in ref.images.values()}
    names = sorted(poses, key=stamp)
    label = dict.fromkeys(names, "unregistered")
    comps, members = [], {}
    for d in sorted((run / "none/colmap_incremental").iterdir(), key=lambda p: int(p.name)):
        rec = pycolmap.Reconstruction(str(d))
        regs = sorted(
            (Path(i.name).name for i in rec.images.values() if i.has_pose and i.num_points3D > 0),
            key=stamp,
        )
        members[int(d.name)] = set(regs)
        for n in regs:
            label[n] = int(d.name)
        comps.append(
            {
                "component": int(d.name),
                "frames": len(regs),
                "points": rec.num_points3D(),
                "first": regs[0] if regs else None,
                "last": regs[-1] if regs else None,
            }
        )
    labels = [label[n] for n in names]
    segs = segments(labels)
    breaks = []
    # A break is a change of component, with any unregistered run between them.
    regs = [(i, lab) for i, lab in enumerate(labels) if lab != "unregistered"]
    for (i, la), (j, lb) in itertools.pairwise(regs):
        if la == lb and j == i + 1:
            continue
        ra, ca = poses[names[i]]
        rb, cb = poses[names[j]]
        heading = np.degrees(np.arccos(np.clip(ra[:, 2] @ rb[:, 2], -1, 1)))
        breaks.append(
            {
                "from_frame": names[i],
                "from_component": la,
                "to_frame": names[j],
                "to_component": lb,
                "unregistered_between": j - i - 1,
                "seconds": round(stamp(names[j]) - stamp(names[i]), 2),
                "arkit_from_position_m": [round(float(x), 2) for x in ca],
                "arkit_to_position_m": [round(float(x), 2) for x in cb],
                "arkit_moved_m": round(float(np.linalg.norm(cb - ca)), 2),
                "arkit_heading_change_deg": round(float(heading), 1),
            }
        )
    return {
        "frames": len(names),
        "registered": sum(lab != "unregistered" for lab in labels),
        "components": comps,
        "one_model": len([c for c in comps if c["frames"]]) == 1
        and all(lab != "unregistered" for lab in labels),
        # A frame in two components is a link COLMAP did not merge on; listed per pair.
        "shared_frames": {
            f"{a}-{b}": len(members[a] & members[b])
            for a in members
            for b in members
            if a < b and members[a] & members[b]
        },
        "segments": [[lab, names[a], names[b], b - a + 1] for lab, a, b in segs],
        "breaks": [b for b in breaks if b["from_component"] != b["to_component"]],
        "gaps_within_component": [b for b in breaks if b["from_component"] == b["to_component"]],
    }


def main():
    rows = {vid: report(vid) for vid in VIDEOS}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1))
    for vid, r in rows.items():
        sizes = ", ".join(f"{c['component']}: {c['frames']}" for c in r["components"])
        print(
            f"{vid}: {r['registered']}/{r['frames']} registered; components {sizes}; "
            f"{len(r['segments'])} segments; {len(r['breaks'])} component changes; "
            f"{len(r['gaps_within_component'])} unregistered runs inside a component; "
            f"shared frames {r['shared_frames'] or 'none'}"
        )
        for b in r["breaks"]:
            print(
                f"   {b['from_component']} -> {b['to_component']} at {b['from_frame']} .. "
                f"{b['to_frame']} ({b['seconds']} s, {b['unregistered_between']} unregistered): "
                f"camera moved {b['arkit_moved_m']} m, turned {b['arkit_heading_change_deg']} deg"
            )


if __name__ == "__main__":
    main()
