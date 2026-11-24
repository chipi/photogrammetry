"""RC-P4: score a point cloud with the ETH3D multi-view-evaluation tool and parse its output.

Usage: run_eval.py <reconstruction.ply> <scan_alignment.mlp> <output json> [--binary PATH]
The tool prints four lines (Tolerances, Completenesses, Accuracies, F1-scores); this parses them.
The tolerances are ETH3D's own: 1, 2, 5, 10, 20 and 50 cm.
"""

import argparse
import json
import resource
import subprocess
import time
from pathlib import Path

TOLERANCES = "0.01,0.02,0.05,0.1,0.2,0.5"
DEFAULT_BINARY = Path.home() / ".cache/recce/mve-src/build/ETH3DMultiViewEvaluation"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ply", type=Path)
    ap.add_argument("mlp", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    args = ap.parse_args()

    cmd = [
        str(args.binary),
        "--reconstruction_ply_path", str(args.ply),
        "--ground_truth_mlp_path", str(args.mlp),
        "--tolerances", TOLERANCES,
    ]  # fmt: skip
    t = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603 (own binary, argv list)
    res: dict = {
        "command": " ".join(cmd),
        "exit": proc.returncode,
        "seconds": round(time.time() - t, 1),
        "peak_rss_gb": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1e6, 2),
    }
    for line in proc.stdout.splitlines():
        for key in ("Tolerances", "Completenesses", "Accuracies", "F1-scores"):
            if line.startswith(key + ":"):
                res[key.lower().replace("-", "_")] = [float(x) for x in line.split(":")[1].split()]
    if proc.returncode != 0 or "f1_scores" not in res:
        res["stderr_tail"] = proc.stderr[-2000:]
        res["stdout_tail"] = proc.stdout[-2000:]
    args.out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res))
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
