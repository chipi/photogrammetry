"""RC-M4: run RC-P1 on one scene and measure each stage's time and energy on the X3.

Energy comes from the APU's package power (amdgpu hwmon `PPT`: CPU and GPU together, readable
without root), sampled every 0.25 s. The machine is shared, so a 10 s idle reading before the run
and another after it are the baseline (the run is marked unsteady when they differ by more
than 10 W), and a stage's energy is what it drew above that baseline. Writes cost.json
beside RC-P1's results.json.

Usage, from prototypes/RC-P1-registration (pinned to the cores this work may use):
    taskset -c 16-31 uv run python ../../mockups/RC-M4-recipes/measure_cost.py <scene> <out>
"""

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P1-registration"))
import run_p1

PPT = next(
    p.parent / "power1_input"
    for p in Path("/sys/class/hwmon").glob("hwmon*/name")
    if p.read_text().strip() == "amdgpu"
)
STEP_S = 0.25
BASELINE_S = 10
STEADY_W = 10
STAGES = ["features", "matching", "colmap_incremental", "glomap_global"]

samples: list[tuple[float, float]] = []
stop = threading.Event()


def sample():
    while not stop.is_set():
        samples.append((time.time(), int(PPT.read_text()) / 1e6))
        time.sleep(STEP_S)


def main():
    out = Path(sys.argv[2])
    threading.Thread(target=sample, daemon=True).start()
    time.sleep(BASELINE_S)
    baseline = sorted(w for _, w in samples)[len(samples) // 2]

    spans = []
    original = run_p1.timed

    def timed(record, name, fn):
        start = time.time()
        result = original(record, name, fn)
        spans.append((STAGES[len(spans)], start, time.time()))
        return result

    run_p1.timed = timed
    sys.argv = [sys.argv[0], sys.argv[1], str(out)]
    run_p1.main()
    end = time.time()
    time.sleep(BASELINE_S)
    stop.set()
    after = sorted(w for t, w in samples if t > end)
    baseline_after = after[len(after) // 2]
    before = baseline
    # Other work on a shared machine moves the idle draw; the run is trusted only when the idle
    # readings before and after agree.
    baseline = (before + baseline_after) / 2

    stages = {}
    for name, t0, t1 in spans:
        w = [p for t, p in samples if t0 <= t <= t1]
        mean = sum(w) / len(w) if w else baseline
        stages[name] = {
            "seconds": round(t1 - t0, 2),
            "mean_w": round(mean, 1),
            "above_baseline_wh": round(max(0.0, mean - baseline) * (t1 - t0) / 3600, 4),
            "total_wh": round(mean * (t1 - t0) / 3600, 4),
            "samples": len(w),
        }
    cost = {
        "sensor": "amdgpu hwmon PPT (APU package: CPU and GPU)",
        "cores": "taskset -c 16-31",
        "baseline_w": round(baseline, 1),
        "baseline_before_w": round(before, 1),
        "baseline_after_w": round(baseline_after, 1),
        "baseline_steady": abs(before - baseline_after) <= STEADY_W,
        "baseline_s": BASELINE_S,
        "stages": stages,
    }
    (out / "cost.json").write_text(json.dumps(cost, indent=2))
    print(json.dumps(cost, indent=2))


if __name__ == "__main__":
    main()
