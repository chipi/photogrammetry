# RC-P1 — Registration on every machine

**Proves:** The registration core end to end on real photos, which machine runs it, and where the
time goes. See the [brief](../../docs/concept/RC-brief.md) §5.

**Proven when:** GLOMAP and COLMAP each register at least two ETH3D scenes from the same verified
matches on the M4 Pro, the X3 and the GB10; each machine × stage cell is pass, fail or CPU
fallback, backed by a command and its output; per strategy, the record holds registration rate,
reprojection error (mean and 95th percentile), wall-clock time per stage, and pose error against
ETH3D's ground truth after Sim(3) alignment.

## Data

ETH3D high-resolution multi-view training scenes, DSLR JPEGs with ground-truth calibration
(CC BY-NC-SA 4.0, development use). Downloaded and extracted outside git:

```bash
mkdir -p ~/.cache/recce/datasets/eth3d && cd $_
curl -LO https://www.eth3d.net/data/multi_view_training_dslr_jpg.7z
uv run --project <repo>/prototypes/RC-P1-registration python -m py7zr x multi_view_training_dslr_jpg.7z .
```

## Run

```bash
cd prototypes/RC-P1-registration
uv run python run_p1.py ~/.cache/recce/datasets/eth3d/<scene> ~/.cache/recce/runs/p1/<machine>/<scene>
```

The script extracts SIFT features once, matches exhaustively once, then runs COLMAP's incremental
mapper and GLOMAP's global mapper from the same database, and writes `results.json`: timings per
stage, registration rate, components, reprojection error (mean, p95), track length, and pose error
against ground truth after a Sim(3) (Umeyama) alignment of camera centres. A camera the mapper
posed but tied to no 3D point does not count as registered: it is reported as
`posed_without_points` and left out of the alignment. `--score-only` re-scores the models already
in the output folder without running the mappers again.

## Results

Status: **not proven yet.** One scene on one machine; the criterion needs two scenes on three.

| Machine | Scene | Strategy | Registered | Posed, no points | Reproj. mean / p95 (px) | Rot. err. median (°) | Pos. err. median (m, % extent) | Mapping (s) |
|---|---|---|---|---|---|---|---|---|
| X3 (CPU) | kicker, 31 images | COLMAP incremental | 30/31 | 0 | 1.23 / 2.30 | 0.447 | 0.023, 0.28% | 57.2 |
| X3 (CPU) | kicker, 31 images | GLOMAP global | 30/31 | 1 | 2.50 / 9.21 | 0.609 | 0.025, 0.30% | 20.7 |

Shared stages on the X3 for kicker: feature extraction 22.4 s, exhaustive matching 7.4 s (SIFT on
CPU; pycolmap 4.2.1 from PyPI has no CUDA). Timings were taken while other workloads ran on the
X3, so they are an upper bound, not a clean measurement.

**What the first scene showed (2026-11-24).** The first scoring gave GLOMAP a 13.1° rotation
error and a 1.76 m position error against COLMAP's 0.45° and 0.023 m. The cause was the scoring,
not the solver: GLOMAP posed `DSC_6487.JPG` (the photo COLMAP could not register) with no 3D
point, about 47 m from its true place, and the least-squares alignment of camera centres bent
every other camera to fit it. Relative rotations between camera pairs, which need no alignment,
were close all along (median 0.54° for COLMAP, 0.77° for GLOMAP). Without the unsupported camera,
the two strategies agree to within a few millimetres on position. GLOMAP's higher reprojection
error (2.50 px against 1.23 px) is real and not yet explained. The [M1 mock-up](../../mockups/RC-M1-run/)
shows the unsupported camera and its line to the truth.
