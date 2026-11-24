"""RC-P4: print every result of the GPU phase as one compact report.

Usage: summarize.py [runs/p4 folder]   (default ~/.cache/recce/runs/p4)
"""

import json
import sys
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".cache/recce/runs/p4"
    for run in sorted(root.glob("courtyard_*")):
        print("==", run.name)
        res = load(run / "results.json")
        if res:
            print(
                " dense:",
                res["stage_seconds"],
                "fused_points",
                res.get("fused_points"),
                "depth_maps",
                res.get("depth_maps"),
            )
        for name in ("eval_dense", "eval_mesh"):
            ev = load(run / f"{name}.json")
            if ev and "f1_scores" in ev:
                print(f" {name} (s={ev['seconds']}, rss={ev['peak_rss_gb']} GB)")
                for key in ("accuracies", "completenesses", "f1_scores"):
                    print(f"   {key:15}", " ".join(f"{v:.3f}" for v in ev[key]))
        sim = load(run / "align" / "sim3.json")
        if sim:
            print(" sim3 scale", sim["sim3_scale_metres_per_model_unit"])
    for run in sorted(root.glob("gsplat_*")):
        print("==", run.name)
        wall = run / "wall.txt"
        print(" ", wall.read_text().strip() if wall.exists() else "no wall.txt")
        for stats in sorted((run / "result" / "stats").glob("val_step*.json")):
            print(" ", stats.name, json.dumps(load(stats)))
        for stats in sorted((run / "result" / "stats").glob("train_step*.json")):
            print(" ", stats.name, json.dumps(load(stats)))


if __name__ == "__main__":
    main()
