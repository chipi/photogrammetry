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

Status: **not proven yet.** Three scenes pass on two machines (X3, M4 Pro); the GB10 is not run.

| Machine | Scene | Strategy | Registered | Posed, no points | Reproj. mean / p95 (px) | Rot. err. median (°) | Pos. err. median (m, % extent) | Mapping (s) |
|---|---|---|---|---|---|---|---|---|
| X3 (CPU) | kicker, 31 images | COLMAP incremental | 30/31 | 0 | 1.23 / 2.30 | 0.447 | 0.023, 0.28% | 57.2 |
| X3 (CPU) | kicker, 31 images | GLOMAP global | 30/31 | 1 | 2.50 / 9.21 | 0.609 | 0.025, 0.30% | 20.7 |
| X3 (CPU) | courtyard, 38 images | COLMAP incremental | 38/38 | 0 | 1.26 / 2.29 | 0.328 | 0.059, 0.39% | 50.4 |
| X3 (CPU) | courtyard, 38 images | GLOMAP global | 38/38 | 0 | 2.59 / 11.23 | 0.332 | 0.056, 0.37% | 13.6 |
| X3 (CPU) | pipes, 14 images | COLMAP incremental | 14/14 | 0 | 1.06 / 2.22 | 0.752 | 0.014, 0.45% | 3.8 |
| X3 (CPU) | pipes, 14 images | GLOMAP global | 14/14 | 0 | 2.07 / 6.46 | 0.961 | 0.017, 0.53% | 1.2 |
| M4 Pro (CPU) | kicker, 31 images | COLMAP incremental | 30/31 | 0 | 1.20 / 2.25 | 0.318 | 0.023, 0.29% | 17.2 |
| M4 Pro (CPU) | kicker, 31 images | GLOMAP global | 31/31 | 0 | 2.45 / 9.26 | 0.590 | 0.022, 0.27% | 5.1 |
| M4 Pro (CPU) | courtyard, 38 images | COLMAP incremental | 38/38 | 0 | 1.27 / 2.30 | 0.338 | 0.063, 0.42% | 38.2 |
| M4 Pro (CPU) | courtyard, 38 images | GLOMAP global | 38/38 | 0 | 2.22 / 3.67 | 0.423 | 0.054, 0.36% | 9.2 |
| M4 Pro (CPU) | pipes, 14 images | COLMAP incremental | 14/14 | 0 | 1.09 / 2.36 | 0.960 | 0.021, 0.66% | 2.2 |
| M4 Pro (CPU) | pipes, 14 images | GLOMAP global | 14/14 | 0 | 2.18 / 8.20 | 0.989 | 0.019, 0.61% | 0.7 |

Shared stages (feature extraction, exhaustive matching), X3 / M4 Pro: kicker 22.4 + 7.4 s /
24.3 + 7.4 s; courtyard 27.9 + 6.7 s / 25.9 + 10.6 s; pipes 8.0 + 0.9 s / 9.2 + 1.8 s. SIFT runs on
the CPU on both: pycolmap 4.2.1 from PyPI has no CUDA, and has no Metal path on the Mac. The X3
runs shared the machine with other workloads, so its timings are an upper bound; the M4 Pro ran
on mains power with no other heavy work.

Each cell, per machine × stage: X3 and M4 Pro, extraction, matching, COLMAP mapping and GLOMAP
mapping all **pass** on CPU; GPU stages are a **CPU fallback** on both. The GB10 has no result.

**What three scenes show (2026-11-24).** On every scene and both machines, GLOMAP maps 3–4× faster
than COLMAP and its poses are as good: rotation and position errors agree within a few tenths of a
degree and under a centimetre. GLOMAP's reprojection error is about twice COLMAP's on every scene
(2.1–2.6 px against 1.1–1.3 px), with a far longer 95th-percentile tail; the cause is not known.
The two machines give the same quality, but not identical models: on the M4 Pro GLOMAP registered
kicker's `DSC_6487.JPG` with points, where on the X3 it posed it with none. Runs are not bit-for-bit
reproducible across machines.

**What the first scene showed (2026-11-24).** The first scoring gave GLOMAP a 13.1° rotation
error and a 1.76 m position error against COLMAP's 0.45° and 0.023 m. The cause was the scoring,
not the solver: GLOMAP posed `DSC_6487.JPG` (the photo COLMAP could not register) with no 3D
point, about 47 m from its true place, and the least-squares alignment of camera centres bent
every other camera to fit it. Relative rotations between camera pairs, which need no alignment,
were close all along (median 0.54° for COLMAP, 0.77° for GLOMAP). Without the unsupported camera,
the two strategies agree to within a few millimetres on position. GLOMAP's higher reprojection
error (2.50 px against 1.23 px) is real and not yet explained. The [M1 mock-up](../../mockups/RC-M1-run/)
shows the unsupported camera and its line to the truth.
