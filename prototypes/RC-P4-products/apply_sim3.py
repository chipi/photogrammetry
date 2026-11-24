"""RC-P4: move a PLY (points or mesh) into the ground-truth frame with the Sim(3) of align_model.py.

Used to score a product made from an unaligned model, such as RC-P2's dense run. Run it in the
gsplat environment (trimesh). Point normals are not carried over, so the output is for scoring only.

Usage: apply_sim3.py <sim3.json> <input.ply> <output.ply>
"""

import json
import sys
from pathlib import Path

import numpy as np
import trimesh


def main() -> None:
    sim, src, dst = (Path(a) for a in sys.argv[1:4])
    p = json.loads(sim.read_text())
    s = p["sim3_scale_metres_per_model_unit"]
    rot, t = np.array(p["rotation"]), np.array(p["translation"])
    mat = np.eye(4)
    mat[:3, :3] = s * rot
    mat[:3, 3] = t
    geom = trimesh.load(src, process=False)
    geom.apply_transform(mat)
    geom.export(dst)
    print("WROTE", dst, "vertices", len(geom.vertices))


if __name__ == "__main__":
    main()
