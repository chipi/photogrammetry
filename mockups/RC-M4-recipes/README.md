# RC-M4 — Recipes and comparison

**Shows:** two recipes for the same photos side by side, what changed between them, and what
each cost, estimated before it ran and measured after.

- **The recipe as a graph, swap in place** (pattern): photos, features, matching, then the node
  that differs, mapping, forked into recipe A and recipe B; the stages they share appear once.
  Clicking a mapping node lists the alternatives for that node only (COLMAP incremental, GLOMAP
  global, and RC-P8's MapAnything route, shown but disabled: not run on these scenes); swapping
  keeps features and matches connected.
- **Compare like a photographer** (idea 6): a wipe across one 3D view, recipe A left of the line
  and recipe B right of it, the same camera on both. Points in their photo colour or by
  reprojection error (an OKLCH ramp, as RC-M2), each recipe's cameras, where ETH3D says the
  cameras were, and each camera's miss drawn as a line, with the worst one labelled.
- **What changed**: the numbers that differ, A against B, the better one marked; then a verdict.
  Without AI the verdict is a stated rule over those numbers. With the person's own AI connected
  (opt-in, as in RC-M3) the AI says which recipe suits which purpose, every number it uses
  checked against the comparison.
- **Frame the cost** (idea 20): per stage, the time and energy estimated before the run (dashed)
  and measured after (solid), and the totals with the miss in percent. Mapping times on the other
  machines come from RC-P1.

The frame follows RC-M1 to RC-M3. Recipe A is the accent colour and recipe B orange in every
panel.

## What the data says

**COLMAP against GLOMAP, from the same matches** (X3, 2026-11-27, pinned to cores 16–31):

| Scene | Recipe | Registered | Reprojection mean / 95th (px) | Worst camera off truth (% of scene) | Mapping (s) | Energy above idle (mWh) |
|---|---|---|---|---|---|---|
| kicker | COLMAP | 30 of 31 | 1.23 / 2.28 | 1.94 | 23.9 | 150 |
| kicker | GLOMAP | 31 of 31 | 2.54 / 9.26 | 10.92 | 6.9 | 61 |
| courtyard | COLMAP | 38 of 38 | 1.27 / 2.30 | 2.20 | 48.8 | 432 |
| courtyard | GLOMAP | 38 of 38 | 2.76 / 12.75 | 3.86 | 13.3 | 108 |

GLOMAP maps 3.4 to 3.7 times faster for a quarter to two fifths of the energy; COLMAP keeps its
worst camera closer to the truth and its points tighter. The engine sees the second without
ground truth: GLOMAP's 95th-percentile reprojection is 4 to 6 times COLMAP's.

**The estimate before the run.** Each scene's estimate is fitted on the other two scenes only
(`estimate_cost.py`: features per image, matching per image pair, mapping as a power law in the
image count; energy as estimated seconds times each stage's measured power above idle):

| Scene | Time estimated → measured | Energy above idle estimated → measured |
|---|---|---|
| kicker (fitted on pipes, courtyard) | 58.1 → 52.9 s (−9%) | 618 → 558 mWh (−10%) |
| courtyard (fitted on pipes, kicker) | 79.2 → 93.0 s (+17%) | 756 → 1,056 mWh (+40%) |

The miss is largest on COLMAP's mapping (40 → 49 s on courtyard): a power law fitted on two
scenes. Energy misses more than time because a stage's power also varies from scene to scene.

**Measuring energy on a shared machine.** The X3 reports its package power (CPU and GPU) through
`amdgpu`'s hwmon `PPT`, readable without root. The idle draw moved with other work on the
machine: one courtyard run read 85 W idle before it (every stage then measured nothing above
idle) and another 30 W before and 60 W after. `measure_cost.py` now reads idle before and after
each run and marks it unsteady when they differ by more than 10 W; the numbers above are from
runs marked steady. The estimate made before courtyard's first run, on pipes and kicker runs whose
idle was not yet checked after, is kept as `courtyard_before_unsteady_fit.json`; the one shown was
refitted on the steady pipes and kicker runs after courtyard had been measured, from their data
only.

**The AI layer.** One call (Claude Sonnet, `claude -p`, no tools) read the comparison and wrote
four sentences per scene: GLOMAP for web viewing, COLMAP for measurement and robot localisation,
and "GLOMAP for a quick first pass, then let COLMAP refine" as the thing to try. All 8 sentences
are backed: every number matches the path it cites. The call cost US$1.75, about twenty times the
US$0.10 expected; the cause was not investigated.

## Data

| Shown | Status |
|---|---|
| Both recipes' cameras, points, colours, reprojection errors | Real: RC-P1's `run_p1.py` re-run on the X3 by `measure_cost.py`, aligned to ETH3D's cameras (Sim(3)) |
| Where the cameras were, each camera's miss | Real: ETH3D's ground truth (known only for the benchmark) |
| Quality numbers | Real: RC-P1's `results.json` of the same runs |
| Time and energy per stage, measured | Real: stage timings and the X3's package power, above idle |
| Time and energy, estimated | **Model** fitted on the other scenes (`estimate_cost.py`) |
| Mapping time on the M4 Pro and GB10 | Real: RC-P1's runs of 2026-11-24 (energy not measured there) |
| The verdict without AI | **Rule written for the mock-up**, stated beside it |
| The verdict with AI | **One recorded run**, checked by `ai_compare.py` |
| Swap-in-place alternatives | COLMAP and GLOMAP real; MapAnything listed, not run on these scenes |

## Run

```bash
R=~/.cache/recce/runs/m4/x3
cd prototypes/RC-P1-registration
for s in pipes kicker courtyard; do
  taskset -c 16-31 uv run python ../../mockups/RC-M4-recipes/measure_cost.py \
    ~/.cache/recce/datasets/eth3d/$s $R/$s
done                                   # repeat a scene whose cost.json says "baseline_steady": false
cd ../../mockups/RC-M4-recipes
mkdir -p $R/estimates
python3 estimate_cost.py 38 $R/pipes $R/kicker > $R/estimates/courtyard_before.json
python3 estimate_cost.py 31 $R/pipes $R/courtyard > $R/estimates/kicker_before.json
cd ../../prototypes/RC-P1-registration
uv run python ../../mockups/RC-M4-recipes/export_compare.py \
  ~/.cache/recce/datasets/eth3d $R ../../mockups/RC-M4-recipes/data
cd ../../mockups/RC-M4-recipes
python3 ai_compare.py data sonnet      # optional: the AI layer
python3 -m http.server 8796 --bind 127.0.0.1
```

Open <http://127.0.0.1:8796/>. A view is a link: `?scene=kicker|courtyard`, `&color=photo|error`,
`&ai=1`, `&swap=1` (B on the left), `&split=0.3` (where the line sits), `&theme=light`.

| File | Does |
|---|---|
| `measure_cost.py` | Runs RC-P1 on one scene with per-stage time and package power; writes `cost.json` |
| `estimate_cost.py` | The estimate before a run, from other measured runs |
| `export_compare.py` | Both recipes in the ground-truth frame, `meta.json` with results and cost |
| `ai_compare.py` | The optional AI layer and its check; writes `ai.json` |
| `index.html` | The page |

## Verdict

Phase 1, built 2026-11-27. The owner's verdict per concept is open:

| Concept | Idea | Verdict |
|---|---|---|
| The recipe graph, the node that differs, swap in place | pattern | Open |
| The wipe across one 3D view | 6 | Open |
| What changed, A against B, and the verdict by rule | 6 | Open |
| The AI layer's verdict per purpose, checked | 6 (owner, 2026-11-27) | Open |
| Cost estimated before and measured after, time and energy | 20 | Open |

## Not covered

- **One node differs.** Only mapping is swapped; a recipe that changes features or matching
  (RAW against JPEG, RC-P5) is not exported, and the dense, mesh and splat stages are not run
  for either recipe.
- **Energy is the package, not the wall,** and on one machine. The M4 Pro and GB10 have no
  energy figures; the X3's GPU is idle in these stages (SIFT and matching run on the CPU here).
- **The estimate is fitted on two scenes** per prediction, with no third to check the fit
  beyond the one it predicts. A real estimator needs many runs.
- **One run per scene and recipe.** Run-to-run variation of the mappers (RC-P3 saw it) is not
  measured; neither is variation in the energy reading.
- **Truth columns.** The camera miss and the "worst camera" are known only for benchmarks; the
  page says so, and the rule falls back on the reprojection tail.
- **The AI call's cost** (US$1.75) is not explained or reduced; no other model or provider tried.
- **Swap in place** swaps between existing runs; it does not start a new run.
