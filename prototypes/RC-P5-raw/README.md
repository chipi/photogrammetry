# RC-P5 — RAW to a consistent set

**Status:** proven on one scene (ETH3D `pipes`, 14 images). The `courtyard` scene is not run.

**Proves:** That a develop stage replaces the Lightroom step without hurting reconstruction, and
which develop route to use. See the [brief](../../docs/concept/RC-brief.md), RC-P5.

**Proven when** *(copied from the brief)*: Three routes — the dataset's own JPEGs, a minimal own
pipeline (rawpy, set-wide white balance and exposure), and Chemigram/darktable through its command
line — each reconstruct the same scene; registration rate from RAW is no worse than from JPEG; the
exposure and white-balance spread across the set and the seam contrast in the texture are measured
for each; one route is chosen on those numbers.

## Routes

| Route | What it is |
|---|---|
| `jpeg` | ETH3D's own in-camera JPEGs, unchanged. |
| `own` | `develop_own.py`: rawpy (libraw AHD), one white balance for the set (median of the cameras' as-shot multipliers: 1.875 / 1 / 1.902), one linear gain for the set (+1.13 EV, median-of-medians luminance at 0.18), sRGB curve, JPEG q95. |
| `chemigram` | `develop_chemigram.py --wb camera`: the `chemigram` CLI (an external process) drives darktable 5.6.1. `ingest` per NEF, `exposure` applied to one anchor image, `propagate-state` to the other 13, `export-final`. One EV for the set (+1.42, found by a closed loop to the same 0.18 target). No `temperature` entry, so darktable applies each image's as-shot white balance. |
| `chemigram_greypick` | Same, with a set-wide `temperature` entry (R 3.35, B 2.47) found by a closed loop that neutralises the grey cabinet door in the anchor render. A variant, not a fourth route. |
| `darktable_default` | `develop_darktable.py`: `darktable-cli` with stock settings and no XMP. A reference run that separates darktable from Chemigram's baseline XMP; not a route of the brief. |

All routes are cropped to the JPEG frame so they share one geometry. libraw reports the NEF as
6080 x 4044; ETH3D's JPEGs are 6048 x 4032. `find_crop.py` phase-correlates the two and finds the
JPEG frame at left 15, top 6 (correlation 0.987 and 0.996 on two windows of `DSC_0634`; the
left offset is 15, not the even 16 one would expect from the Bayer grid, and is not resolved
further). ETH3D's RAW calibration files have the same cameras and poses as the JPEG ones.
Registration here self-calibrates intrinsics as in RC-P1 and scores poses only, so the 1 px
uncertainty does not enter the scoring.

## Data

ETH3D DSLR RAW archive (CC BY-NC-SA 4.0, development use), outside git:

```bash
cd ~/.cache/recce/datasets/eth3d/pipes && mkdir -p raw && cd raw
curl -LO https://www.eth3d.net/data/pipes_dslr_raw.7z    # 373 MB
uv run --project <repo>/prototypes/RC-P5-raw python -m py7zr x pipes_dslr_raw.7z .
mv pipes/* . && rmdir pipes                              # leaves raw/images/dslr_images/*.NEF
```

14 NEFs, names 1:1 with the 14 JPEGs (`DSC_0634` to `DSC_0647`). The JPEGs and ground truth
(`images/`, `dslr_calibration_jpg/`) come from RC-P1's download.

## Reproduce

```bash
cd prototypes/RC-P5-raw
uv sync
S=~/.cache/recce/datasets/eth3d/pipes
mkdir -p ~/.cache/recce/runs/p5/pipes/jpeg/images/dslr_images
ln -sf $S/images/dslr_images/*.JPG ~/.cache/recce/runs/p5/pipes/jpeg/images/dslr_images/
uv run python develop_own.py pipes
uv run python develop_chemigram.py pipes --wb camera      # needs chemigram + darktable-cli
uv run python develop_chemigram.py pipes --wb greypick
uv run python develop_darktable.py pipes
uv run python run_p5.py pipes jpeg own chemigram chemigram_greypick darktable_default
```

Chemigram is at `/work/chemigram/main` (override with `CHEMIGRAM_BIN`); its workspace and
darktable configdir live under `~/.cache/recce/runs/p5/`. Outputs, `results.json` per route and the
develop parameters (`develop.json`) are in `~/.cache/recce/runs/p5/pipes/<route>/`.

## Measures

- **Registration:** copied from RC-P1: SIFT, exhaustive matching, COLMAP incremental mapping, the
  largest model scored; poses against ETH3D ground truth after Sim(3) alignment.
- **Exposure spread:** per image, log2 of the median linear luminance (decoded from the route's
  8-bit sRGB JPEG, 1/8 decimation); std and max-min across the set, in EV.
- **White-balance spread:** per image, median of per-pixel linear R/G and B/G (pixels with G > 0.01);
  std across the set, and the two relative stds combined in quadrature, in percent. Scene content
  differs between views, so this includes content variation; it is the same for every route.
- **Seam contrast (proxy; no textured mesh exists before RC-P4):** for each 3D point with a track of
  3 or more images, the std across the track of log2 luminance (EV) and of log2 R/G and B/G, each
  observation a 5 x 5 box mean at the keypoint; median over points. This includes real view
  dependence (specular floor, grazing angles) and keypoint localisation error, which every route
  shares; only differences between routes mean anything.

## Results (`pipes`, 14 images, X3, pycolmap 4.2.1 CPU)

| Measure | jpeg | own | chemigram | chemigram_greypick | darktable_default |
|---|---|---|---|---|---|
| Registered / 14 | 14 | 14 | **7** | **7** | 14 |
| Registration rate | 1.00 | 1.00 | 0.50 | 0.50 | 1.00 |
| Reprojection mean / p95 (px) | 1.08 / 2.26 | 1.18 / 2.26 | 1.10 / 2.13 | 1.06 / 2.03 | 1.13 / 2.21 |
| 3D points | 2526 | 2983 | 2488 | 2312 | 3093 |
| Relative rotation vs GT, median / p95 (deg) | 0.80 / 1.67 | 0.62 / 1.23 | 0.34 / 0.63 * | 0.32 / 0.60 * | 0.46 / 0.96 |
| Position vs GT, median (m, scene 3.1 m) | 0.021 | 0.027 | 0.012 * | 0.009 * | 0.027 |
| Exposure spread, std / range (EV) | 0.208 / 0.735 | 0.204 / 0.747 | 0.364 / 1.300 | 0.376 / 1.356 | 0.255 / 0.931 |
| White-balance spread, R/G std, B/G std | 0.027, 0.068 | 0.036, 0.057 | 0.156, 0.074 | 0.140, 0.279 | 0.035, 0.071 |
| White-balance spread, combined relative (%) | 9.4 | 8.4 | 119.9 | 64.5 | 11.5 |
| Seam proxy, luminance sd median (EV) | 0.216 | 0.199 | 0.226 | 0.229 | 0.224 |
| Seam proxy, luminance sd p90 (EV) | 1.21 | 0.89 | 0.54 * | 0.54 * | 1.11 |
| Seam proxy, R/G sd, B/G sd median (EV) | 0.029, 0.049 | 0.061, 0.068 | 0.258, 0.621 | 0.225, 0.578 | 0.070, 0.091 |
| Seam proxy, points used | 1454 | 2304 | 1591 | 1483 | 2099 |

\* Scored on the 7 registered images only; not comparable with the 14-image columns.

Timings (not comparable, the X3 was shared) are in each `results.json`.

## Chosen route: `own`

The brief's criterion holds for `own`: 14 of 14 images register from RAW, as from the JPEGs, with
the same reprojection p95 (2.26 px) and pose error to ground truth no worse than the JPEG route
(median relative rotation 0.62 against 0.80 degrees). `own` has the smallest exposure spread of the
RAW routes (0.20 EV std, equal to the JPEGs) and the smallest combined white-balance spread of any
route (8.4 percent against 9.4 for the JPEGs), the lowest luminance seam proxy, and the most 3D
points of the three brief routes. The Chemigram route as driven here fails the registration
criterion (7 of 14) and its colour is far from consistent: the renders are strongly yellow-green and
dark, the white-balance spread is 64 to 120 percent, and the colour seam proxy is five to ten times
the others. Stock `darktable-cli` is a close second (14 of 14, the most 3D points, but 0.25 EV and
11.5 percent spread, and a higher colour seam proxy than `own`). The differences among `jpeg`,
`own` and `darktable_default` are small, from one scene and one run, and not tested for
significance; the decision between them rests on RAW giving full control of the set-wide
parameters, not on a measured gap in reconstruction.

## Not covered

- **Only `pipes`.** `courtyard` (38 images, 1.1 GB) is not downloaded or run; one scene and 14
  images cannot show a registration difference of a few images.
- **Chemigram's failure is observed, not explained.** Its baseline render of the NEFs
  (no `temperature` entry, as-shot white balance) is dark and yellow-green, while `darktable-cli`
  with no XMP on the same files is neutral (`darktable_default`, 14 of 14). The cause (the baseline
  XMP, the vocabulary pack, the colour pipeline for the D3X) is not investigated. The Chemigram
  numbers describe Chemigram's `starter` + `expressive-baseline` packs at v1.11.0 driven as above,
  not darktable, and a different recipe may register fully. Chemigram's `wb-from-gray-card` verb is
  not used (it refused the unity-coefficient render as too dark); the grey patch is iterated by
  `develop_chemigram.py` instead. The grey cabinet door is assumed neutral.
- **No ground-truth scale or dense scoring.** Poses only; no dense cloud, mesh or texture.
- **Seam contrast is a proxy** (see Measures); no textured mesh, no RC-P4 seam measurement.
- **Exposure and white-balance numbers** come from 8-bit sRGB JPEGs after each route's tone curve,
  not from the sensor, and the white-balance spread includes scene-content variation.
- **Own route's exposure** is one set-wide gain by design, so it keeps the camera's auto-exposure
  variation between frames; a per-image normalisation route is not tested.
- **The JPEG frame offset** is measured to about 1 px (left 15 vs an expected 16).
- **Timings** are recorded and not compared.
- No second sensor or lens; no scene with mixed lighting; one run per route, no repeat for noise
  (COLMAP's incremental mapping is not seeded in this script).
