# PG-M1 — The run (with the M0 frame, and first passes at M2 and M3)

**Shows:** one page with three modes over the same real data.

- **Run** (M1): a reconstruction replayed: cameras finding their place one by one with their
  photos on the frustums, points glowing as they join, threads from the newest photo to what it
  sees, plural timelines, the ground truth beside the estimate. Ideas 1, 2, 9, 19.
- **Coverage** (first pass at M2): light and shadow by how many photos agree on a point; crisp or
  soft by the angle between the rays that placed it; the weakest region pulsing; its coverage ring
  (which directions saw it); a suggested next shot as a dashed ghost camera. Ideas 3, 4, 13, 14.
- **Debrief** (first pass at M3): a written debrief whose every claim carries an evidence handle
  that flies the scene to its evidence, a claim without evidence flagged as such, readiness stamps
  with their stated requirements, and labels placed in the scene. Ideas 5, 10, 16, 18.

The frame around them (M0): outliner, inspector, timeline with a filmstrip, command palette with
each command's CLI line (idea 15), light and dark. Ideas are numbered as in the
[catalogue](../../docs/wip/visual-ideas.md).

**Phase:** 1 — rough but good-looking, to settle the concepts. Phase 2 polishes the chosen
direction.

## Data

Real output from [PG-P1](../../prototypes/PG-P1-registration/) on ETH3D *kicker* (CC BY-NC-SA 4.0,
development use), both strategies. Nothing from the dataset is committed: `export_run.py` writes
`data/run.json` and `data/thumbs/` (ignored by git) from the local run.

| Shown | Status |
|---|---|
| Cameras, poses, focal lengths, points, point colours, tracks | Real (PG-P1) |
| Ground truth positions | Real (ETH3D), aligned on the cameras that hold points |
| Registration order | **Derived** from the final model (best pair, then most shared points); PG-P1 does not log the mapper's real order yet |
| Biggest additions on the timeline | Derived from the order above |
| What the solver believed at each step (idea 11) | Not shown; needs PG-P1 to log iterations |
| Light and shadow, crisp and soft | Real: track length and the widest angle between a point's rays, computed by `export_run.py` |
| Weakest region and its coverage ring | Computed in the page from the real points (0.9-unit cells, ranked by median angle and support) |
| Suggested next shot | **Heuristic**: the middle of the widest gap in viewing directions, kept inside the cameras' area |
| Debrief text | **Template** filled from the run's numbers; an agent writes it in the product |
| Readiness stamps | Rules written for the mock-up; their requirements are stated next to each stamp |

## Run

```bash
cd prototypes/PG-P1-registration
uv run python ../../mockups/PG-M1-run/export_run.py \
  ~/.cache/photogrammetry/datasets/eth3d/kicker ~/.cache/photogrammetry/runs/p1/x3/kicker \
  ../../mockups/PG-M1-run/data
cd ../../mockups/PG-M1-run && python3 -m http.server 8793 --bind 127.0.0.1
```

Open <http://127.0.0.1:8793/>. three.js loads from jsDelivr. A view is a link:
`?strategy=glomap_global&timeline=name&at=12&truth=1&select=DSC_6487.JPG`, plus `mode=coverage|debrief`, `theme=light`, `palette=1`, `fly=weak|ghost`.

Keys: space play, ← → step, G ground truth, T threads, ⌘K or Ctrl+K commands.

## What it already showed

Switching to GLOMAP with the ground truth on revealed a camera posed with no 3D point, about 47 m
from its true place; that camera had distorted PG-P1's first scoring
([PG-P1 results](../../prototypes/PG-P1-registration/README.md#results)). The mock-up flags such
a camera in the top bar and the inspector.

## Verdict

*Pending the owner's review:* per concept, kept, changed or dropped, with the reason.
