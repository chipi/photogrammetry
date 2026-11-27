# RC-M1 — The run (with the M0 frame, and first passes at M2 and M3)

**Shows:** one page with three modes over the same real data.

- **Run** (M1): a reconstruction replayed: cameras finding their place one by one with their
  photos on the frustums, points glowing as they join, threads from the newest photo to what it
  sees, plural timelines, the ground truth beside the estimate. Ideas 1, 2, 9, 19.
- **Coverage** (first pass at M2): light and shadow by how many photos agree on a point; crisp or
  soft by the angle between the rays that placed it. Then the **gap list for the next session**
  (idea 21): every gap found, ranked for a purpose (web viewing, measurement, robot), each as a
  card (where to stand from the nearest photo already taken, what to shoot, why, what it gains,
  its coverage ring), a **site map** from above with the gaps numbered, where to stand and the
  order to walk them, and the same list as a **robot brief** (draft JSON). Ideas 3, 4, 13, 14, 21.
- **Debrief** (first pass at M3): a written debrief whose every claim carries an evidence handle
  that flies the scene to its evidence, a claim without evidence flagged as such, readiness stamps
  with their stated requirements, and labels placed in the scene. Ideas 5, 10, 16, 18.

The frame around them (M0): outliner, inspector, timeline with a filmstrip, command palette with
each command's CLI line (idea 15), light and dark. Ideas are numbered as in the
[catalogue](../../docs/wip/visual-ideas.md).

**Phase:** 2 — polish of the direction chosen in phase 1 (see "Phase 2" below). Concepts, modes,
URL parameters and the gap-list brief JSON are unchanged.

## Data

Real output from [RC-P1](../../prototypes/RC-P1-registration/) on ETH3D *kicker* (CC BY-NC-SA 4.0,
development use), both strategies. Nothing from the dataset is committed: `export_run.py` writes
`data/run.json` and `data/thumbs/` (ignored by git) from the local run.

| Shown | Status |
|---|---|
| Cameras, poses, focal lengths, points, point colours, tracks | Real (RC-P1) |
| Ground truth positions | Real (ETH3D), aligned on the cameras that hold points |
| Registration order | **Derived** from the final model (best pair, then most shared points); RC-P1 does not log the mapper's real order yet |
| Biggest additions on the timeline | Derived from the order above |
| What the solver believed at each step (idea 11) | Not shown; needs RC-P1 to log iterations |
| Light and shadow, crisp and soft | Real: track length and the widest angle between a point's rays, computed by `export_run.py` |
| Gaps and their coverage rings | Computed in the page from the real points: 0.9-unit cells; thin angle where the median ray angle is under 8°, few photos where over half the points have two views; at most two of each, 2 units apart |
| Photo that did not join, missing scale | Real (from the registration and the absence of priors or markers) |
| Where to stand | **Heuristic**: the middle of the widest gap in viewing directions, kept inside the footprint of the cameras tied to points |
| Directions from the landmark photo | Computed from its pose; metres come from the ground-truth alignment, which a real capture has only with scale |
| Priorities per purpose | Rules written for the mock-up |
| Robot brief | The shape of the gap-list interface draft (`gap_list` 1, docs/wip/gap-list-interface.md), filled from the page's gaps; rankings follow the mock-up's rules |
| Debrief text | **Template** filled from the run's numbers; an agent writes it in the product |
| Readiness stamps | Rules written for the mock-up; their requirements are stated next to each stamp |

## Run

```bash
cd prototypes/RC-P1-registration
uv run python ../../mockups/RC-M1-run/export_run.py \
  ~/.cache/recce/datasets/eth3d/kicker ~/.cache/recce/runs/p1/x3/kicker \
  ../../mockups/RC-M1-run/data
cd ../../mockups/RC-M1-run && python3 -m http.server 8793 --bind 127.0.0.1
```

Open <http://127.0.0.1:8793/>. three.js loads from jsDelivr. A view is a link:
`?strategy=glomap_global&timeline=name&at=12&truth=1&select=DSC_6487.JPG`, plus `mode=coverage|debrief`, `view=map`, `gap=N`, `purpose=web|measure|robot`, `brief=1`, `theme=light`, `palette=1`, `fly=weak|ghost`.

Keys: space play, ← → step, G ground truth, T threads, ⌘K or Ctrl+K commands.

## What it already showed

Switching to GLOMAP with the ground truth on revealed a camera posed with no 3D point, about 47 m
from its true place; that camera had distorted RC-P1's first scoring
([RC-P1 results](../../prototypes/RC-P1-registration/README.md#results)). The mock-up flags such
a camera in the top bar and the inspector.

## Verdict

**Kept, all concepts shown (owner, 2026-11-24):** the style ("I really like the style"), every concept in the three modes ("we really love everything"), and the gap list with site map and cards ("exactly what I wanted"). Phase 2 polishes the direction; the typeface (Inter, flagged as overused) is decided there.

## Phase 2 (2026-11-24)

- **Typeface:** IBM Plex Sans (UI) and IBM Plex Mono (values, numbers, kinds), both from Google Fonts only. Plex is built for instruments and engineering tools, the two cuts share proportions, and Plex Mono has a slashed zero and distinct 1/l/I, which suits label-left, value-right inspector rows.
- **Spacing:** 4 px scale as tokens (`--sp-1` to `--sp-8`); panels, cards, top bar and chips re-padded to it; every bordered or filled element with text has at least 8 px horizontal inset; every side-panel section has the same 16 px frame and header (title left, optional mono meta right); `.kv` rows align on the text baseline. Bars: top 48 px, status 28 px, left panel 264 px.
- **Type scale:** six size tokens (11, 12, 13, 14, 16, 20 px); nothing below 11 px, including the canvas map text and the ring percentages; numbers in mono or tabular figures.
- **Colour:** ad-hoc colours collapsed into tokens (surfaces, on-fill, scrims, grid, coverage ramp, swatches, label background). Fill colours stay as in phase 1 so the scene is unchanged; new `-ink` twins (accent, new, truth, warn, error) carry text and pass WCAG AA (4.5:1) on every panel surface in both themes (lowest computed 4.66:1, faint text on a hovered row in the light theme; most are above 5). Dim and faint text in the dark theme lifted slightly (now 7.3:1 and 6.0:1 on the panel).
- **Gap cards and site map:** a card reads as a field shot card: large number, kind and priority tag, then labelled rows Stand (nearest photo with thumbnail and directions), Shoot, Why, Gain, Seen (the coverage ring with a plain sentence), then actions. The map repeats the card number at the badge and at the spot to stand ("Stand N" on the selected gap), and names gaps with the same kind text as the card.
- **Motion:** transitions 120 ms (hover, press) and 180 ms (opacity, strip); no glow added. Reduce motion now also zeroes the CSS transitions (and follows the system setting); the scene behaviour it already controlled is unchanged.
- **Photos hang in the air (owner feedback):** a camera is its photo, a crisp textured plane with no outline, a tiny dot at the camera centre, and four hairline rays from the photo corners that fade toward the centre (about 0.15 opacity; stronger on the selected and joining-now camera, which also get a thin accent edge). No pyramid edges and no back fill. With "Photos on cameras" off, a faint rectangle outline marks the image plane; ghost viewpoints in Coverage are a dotted faint outline and faint rays. Same in both themes.
- **Later (owner, 2026-11-27):** a setting that draws each photo as a solid fill instead of its image, to save texture memory and frame rate on large sets or slow devices; the dot and fading rays stay. Recorded in the "A camera is its photo" pattern ([visual ideas](../../docs/wip/visual-ideas.md)); not built, its saving not measured.
- Also: visible keyboard focus ring, a dead style block removed, status line says phase 2.
- **Not done:** the top bar clips crumbs below about 1,400 px wide (no responsive layout); contrast was computed from the token values, not measured on pixels of the 3D scene or the point-cloud shader colours; the theme button glyph (◐) comes from a fallback font.
