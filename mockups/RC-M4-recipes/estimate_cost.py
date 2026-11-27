"""RC-M4: estimate a recipe's time and energy before it runs, from runs already measured on the
same machine. Fitted per stage:
- features: seconds per image;
- matching: seconds per image pair (exhaustive matching);
- mapping: seconds = c * images^k, fitted on the scenes measured (a power law: mapping grows
  faster than the image count);
- energy: the estimated seconds times the stage's mean power above the idle baseline.
With two scenes the fit has no spare data to check itself; the estimate says so.

    python3 estimate_cost.py <images> <measured run dir>... > estimate.json
"""

import json
import math
import sys
import time
from pathlib import Path

PER_IMAGE = {"features"}
PER_PAIR = {"matching"}


def main():
    n = int(sys.argv[1])
    runs = []
    for d in map(Path, sys.argv[2:]):
        cost = json.loads((d / "cost.json").read_text())
        images = json.loads((d / "results.json").read_text())["images"]
        runs.append((d.name, images, cost))
    stages = {}
    for stage in runs[0][2]["stages"]:
        pts = [(img, c["stages"][stage], c["baseline_w"]) for _, img, c in runs]
        watts = sum(s["mean_w"] - b for _, s, b in pts) / len(pts)
        if stage in PER_IMAGE:
            rate = sum(s["seconds"] / img for img, s, _ in pts) / len(pts)
            secs, model = rate * n, f"{rate:.3f} s per image"
        elif stage in PER_PAIR:
            rate = sum(s["seconds"] / (img * (img - 1) / 2) for img, s, _ in pts) / len(pts)
            secs, model = rate * n * (n - 1) / 2, f"{rate * 1000:.2f} ms per image pair"
        else:
            (n0, s0, _), (n1, s1, _) = (
                sorted(pts, key=lambda p: p[0])[:1] + sorted(pts, key=lambda p: p[0])[-1:]
            )
            k = math.log(s1["seconds"] / s0["seconds"]) / math.log(n1 / n0)
            secs = s1["seconds"] * (n / n1) ** k
            model = f"seconds grow as images^{k:.2f}"
        stages[stage] = {
            "seconds": round(secs, 1),
            "above_baseline_wh": round(max(0.0, watts) * secs / 3600, 3),
            "model": model,
        }
    print(
        json.dumps(
            {
                "images": n,
                "fitted_on": [f"{name} ({img} images)" for name, img, _ in runs],
                "made_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "caveat": f"fitted on {len(runs)} scenes of one machine; not checked on a third",
                "stages": stages,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
