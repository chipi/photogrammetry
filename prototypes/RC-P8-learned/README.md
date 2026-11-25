# RC-P8 — Learned and classical, compared

**Proves:** Whether MapAnything's Apache checkpoint is a useful first pass (fast poses and metric
scale) once bundle adjustment checks it. See the [brief](../../docs/concept/RC-brief.md), RC-P8.

**Proven when:** On ETH3D and on ARKitScenes, with and without pose priors, the learned-then-bundle-adjust
route and the classical routes are compared on registration rate, pose error against the reference,
and scale error; the result decides whether the learned first pass enters a recipe.

## Routes

| Route | What runs |
|---|---|
| `colmap_incremental` | SIFT, exhaustive matching, COLMAP's incremental mapper (as in RC-P1) |
| `glomap_global` | The same matches, GLOMAP's global mapper (as in RC-P1) |
| `mapanything` | MapAnything (`facebook/map-anything-apache`, Apache 2.0) alone: one forward pass over all images |
| `mapanything_ba` | MapAnything's poses and intrinsics start a coarse-to-fine loop over the same SIFT matches: triangulate (poses fixed, intrinsics refined), then a full bundle adjustment, at 64, 32, 16, 8 and 4 px |

Scoring is RC-P1's: a camera counts as registered only when it holds 3D points; pose error is
after a Sim(3) alignment of camera centres. Scale error is the size of the estimate against the
reference, `100 × (1/s − 1)` %, where `s` is the Sim(3) scale; it is reported only for routes that
claim metric scale (MapAnything, MapAnything + BA, COLMAP with position priors).

Why the loop: on pipes (CPU code check), one triangulation at COLMAP's 4 px from MapAnything's
poses kept 129 two-view points, since the lens model starts without distortion and ETH3D's lens
is strongly distorted; the bundle adjustment then overfit them (rotation 7.0° median, worse than
MapAnything alone). COLMAP's incremental mapper started from MapAnything's model refined the poses
well (0.69°, 1.5 cm) but re-normalises the model, so the metric scale is lost (+293%); it is not
used.

**Anchoring.** The bundle adjustment leaves the gauge free and the scale drifts: on the GB10,
kicker without priors went from MapAnything's +4.1% to −39.6%, courtyard with priors from −5.3%
to −75.4%. The adjusted model is therefore mapped onto MapAnything's own camera centres with a
Sim(3) (`anchor_to_learned`): the scale comes from the learned pass, the shape from the adjustment.
The drift before anchoring is kept in each result (`ba_scale_drift_pct`). `run_p8.py rescore-ba`
re-scores a saved adjusted model this way without running anything again.

## Variants and references

| Data | Reference | `none` | `prior` |
|---|---|---|---|
| ETH3D (pipes, kicker, courtyard) | ETH3D ground truth | images only | ground-truth intrinsics (held fixed) and ground-truth poses with noise: position σ = 1% of the scene extent, rotation σ = 1° (seed 0) |
| ARKitScenes raw (videos 42444515, 42444821, 42444793, 42444858, 42444873) | ARKit's own tracking (`lowres_wide.traj`) | images only | ARKit intrinsics (held fixed) |

- **ARKit is a reference, not ground truth.** ARKitScenes raw has no other poses. So that the
  comparison is not circular, the ARKitScenes `prior` run gives intrinsics only, never ARKit poses;
  pose priors are tested on ETH3D, with noised ground truth (owner's choice, 2026-11-25).
- The noise size is a choice, not a measurement: about what a phone tracker drifts over a
  room-sized walk.
- MapAnything takes pinhole intrinsics. ETH3D's cameras are `THIN_PRISM_FISHEYE`; MapAnything gets
  their pinhole part (distortion dropped), COLMAP and the bundle adjustment get the full model.
- In the `prior` run COLMAP's incremental mapper uses the noised positions as position priors;
  GLOMAP gets the intrinsics only.
- **Axis control.** ARKitScenes' loader inverts each `.traj` line to get camera-to-world, so a line
  is cam_from_world with OpenCV axes. A second reference with OpenGL axes (`reference_glflip`) is
  scored too; it must fail.
- ARKitScenes frames: every 12th `vga_wide` frame (30 Hz, so 2.5 Hz), each with the ARKit pose
  interpolated at its own timestamp (rotation by slerp, camera centre linearly) between the two
  10 Hz poses around it. Nearest-pose pairing was dropped: on 42444858 half the poses sit 16 ms
  from any frame. Checked: at a pose timestamp the interpolation returns that pose exactly; on
  42444515, where frames and poses align within 0.5 ms, it differs from nearest pairing by at most
  0.014° and 0.21 mm.

## Environments (DGX `dgx-llm-1`, user `claude`, user-level only)

pycolmap has no PyPI wheel for Linux ARM, and MapAnything's environment comes from PyPI, so the two
stages run in two environments and pass JSON between them.

- `~/.cache/recce/p1env` (micromamba, conda-forge pycolmap 4.2.1 with CUDA): `run_p8.py`.
- `~/.cache/recce/mapanyenv` (uv venv, Python 3.12.3): torch 2.14.1+cu130, torchvision
  0.29.1+cu130, MapAnything 1.1.4 installed editable from `~/.cache/recce/map-anything-src`
  (commit `3d10cf7a3016fc0f9bb13a071ee66c47b10be0d9`, Apache 2.0), scipy. Built by
  `setup_env.sh` (below). Loading the checkpoint also fetches DINOv2's code from GitHub through
  torch hub (`facebookresearch/dinov2`, Apache 2.0).
- Checkpoint: `facebook/map-anything-apache`, 1,228,491,222 parameters, loads on the CPU in 107 s.
  The CC-BY-NC checkpoint `facebook/map-anything` is not used.

```bash
uv venv --python 3.12 ~/.cache/recce/mapanyenv
uv pip install --python ~/.cache/recce/mapanyenv/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cu130
uv pip install --python ~/.cache/recce/mapanyenv/bin/python -e ~/.cache/recce/map-anything-src
uv pip install --python ~/.cache/recce/mapanyenv/bin/python scipy
```

## Data

- ETH3D pipes, kicker, courtyard: the RC-P1 downloads (CC BY-NC-SA 4.0, development use).
- ARKitScenes raw, five Training videos (Apple's non-commercial licence, development use only,
  never redistributed), fetched with the official `download_data.py` (commit `474aaa8`) into
  `~/.cache/recce/datasets/arkitscenes`, assets `lowres_wide.traj vga_wide vga_wide_intrinsics
  lowres_depth lowres_wide_intrinsics`: 3.4 GB for the five.
- Which videos. The first three (42444515, 42444821, 42444793) came from the first rows of
  `metadata.csv` that have a laser scan, are in the upsampling subset and have sky direction Up.
  All three are small, low-texture spaces (a dim corridor with a poster on the floor, blank
  walls, a white bathroom). They stay as the hard cases, and two textured rooms are added by a
  stated rule (owner's choice, 2026-11-25), `select_arkit.py`: the first eight rows under the same
  filter, one per visit and none from the first three's visits, ranked by median SIFT keypoint
  count over 10 evenly spaced frames. The two highest, 42444858 and 42444873, are used; the other
  six downloads are deleted.

| Video | Median SIFT keypoints | Frames (30 Hz) | Used |
|---|---|---|---|
| 42444858 | 1,502 | 1,619 | yes |
| 42444873 | 1,250 | 2,637 | yes |
| 42444866 | 1,023 | 1,459 | |
| 42444574 | 904 | 2,376 | |
| 42444503 | 839 | 2,468 | |
| 42444883 | 539 | 1,587 | |
| 42444891 | 490 | 3,251 | |
| 42444511 | 327 | 1,583 | |
| 42444515 | 269 | 1,093 | yes (hard) |
| 42444821 | 268 | 1,289 | yes (hard) |
| 42444793 | 248 | 1,524 | yes (hard) |

## Run

```bash
P=~/.cache/recce/p1env/bin/python; M=~/.cache/recce/mapanyenv/bin/python; R=~/.cache/recce/runs/p8
$P run_p8.py prep-eth3d ~/.cache/recce/datasets/eth3d/courtyard $R/courtyard
$P run_p8.py prep-arkit ~/.cache/recce/datasets/arkitscenes/raw/Training/42444515 $R/a42444515
$M infer_mapanything.py $R/courtyard --variant none     # GPU; --cpu for a code check
$P run_p8.py colmap $R/courtyard --variant none         # writes $R/courtyard/none/results.json
```

`infer_mapanything.py` maps MapAnything's intrinsics back to the original image's pixels through
MapAnything's own resize-and-crop functions; in the `prior` run it checks that map against the
processed intrinsics MapAnything made from the prior (`pixel_map_check_max_px`).

## Results

Status: **proven (2026-11-25, GB10 in a `free` window).** The comparison is done on both sets,
with and without priors, and the owner has decided: MapAnything + BA enters as an optional second
route (decision at the end of this section).

All runs on the GB10: MapAnything in bf16 on CUDA, SIFT and matching on CUDA (conda-forge
pycolmap). Small results (JSON, logs, `table.md`; 127 files, 5.6 MB) are copied to
`~/.cache/recce/runs/p8/` on the workstation; databases, models and frames stay on the DGX.

How to read the table:

- **Rot.** is the rotation error after the Sim(3) alignment of camera centres (RC-P1's number).
  On a short or nearly straight camera path that alignment cannot fix the rotation about the path,
  so this number can be large for a model that is right (GLOMAP on 42444858 with priors: 54.8°
  against 1.7° relative). **Rel. rot.** (every camera pair's relative rotation against the
  reference's) does not depend on the alignment and is the number to compare.
- **Registered** counts cameras that hold 3D points in the largest model; pose errors are over
  those cameras only. COLMAP's 15/90 on 42444515 is accurate on 15 frames, not on the video.
- **Scale err.** is shown only where the route claims metric scale. For MapAnything + BA it is
  after anchoring (above); **BA drift** is how far the adjustment had moved the scale before.
- **Time** is the route's own time: mapping for COLMAP and GLOMAP (the shared SIFT and matching,
  1–8 s, not included); preprocessing, inference, triangulation and adjustment for the learned
  routes (model load, about 11 s, not included).
- On ARKitScenes the reference is ARKit's tracking, not ground truth.

| Scene | Priors | Route | Registered | Rot. (°) | Rel. rot. (°) | Pos. (m) | Pos. (% extent) | Scale err. (%) | BA drift (%) | Reproj. (px) | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pipes | none | colmap_incremental | 14/14 | 0.81 | 0.69 | 0.019 | 0.60 | - | - | 1.02 | 3 |
| pipes | none | glomap_global | 14/14 | 0.88 | 0.69 | 0.018 | 0.57 | - | - | 2.01 | 1 |
| pipes | none | mapanything | 14/14 | 1.21 | 1.55 | 0.129 | 4.12 | 15.3 | - | - | 6 |
| pipes | none | mapanything_ba | 14/14 | 0.56 | 0.48 | 0.016 | 0.53 | 2.2 | 3.1 | 1.23 | 8 |
| pipes | prior | colmap_incremental | 14/14 | 0.02 | 0.07 | 0.001 | 0.04 | -0.1 | - | 0.48 | 3 |
| pipes | prior | glomap_global | 14/14 | 0.10 | 0.11 | 0.002 | 0.05 | - | - | 0.50 | 1 |
| pipes | prior | mapanything | 14/14 | 2.46 | 0.66 | 0.043 | 1.38 | 0.9 | - | - | 6 |
| pipes | prior | mapanything_ba | 14/14 | 0.02 | 0.08 | 0.001 | 0.04 | 0.7 | -2.1 | 0.50 | 8 |
| kicker | none | colmap_incremental | 30/31 | 0.38 | 0.53 | 0.024 | 0.29 | - | - | 1.21 | 22 |
| kicker | none | glomap_global | 31/31 | 0.54 | 0.77 | 0.024 | 0.29 | - | - | 2.60 | 7 |
| kicker | none | mapanything | 31/31 | 0.70 | 0.86 | 0.121 | 1.49 | 4.1 | - | - | 14 |
| kicker | none | mapanything_ba | 31/31 | 0.57 | 0.82 | 0.022 | 0.27 | 2.3 | -41.0 | 1.39 | 38 |
| kicker | prior | colmap_incremental | 30/31 | 0.03 | 0.02 | 0.001 | 0.01 | -1.1 | - | 0.72 | 17 |
| kicker | prior | glomap_global | 29/31 | 0.08 | 0.08 | 0.003 | 0.04 | - | - | 1.07 | 9 |
| kicker | prior | mapanything | 31/31 | 1.84 | 1.01 | 0.121 | 1.49 | -0.7 | - | - | 14 |
| kicker | prior | mapanything_ba | 31/31 | 0.05 | 0.03 | 0.002 | 0.02 | -1.1 | -7.0 | 0.76 | 25 |
| courtyard | none | colmap_incremental | 38/38 | 0.37 | 0.40 | 0.053 | 0.35 | - | - | 1.28 | 46 |
| courtyard | none | glomap_global | 38/38 | 0.39 | 0.46 | 0.053 | 0.35 | - | - | 2.84 | 13 |
| courtyard | none | mapanything | 38/38 | 1.47 | 1.70 | 0.373 | 2.49 | -28.3 | - | - | 17 |
| courtyard | none | mapanything_ba | 38/38 | 0.26 | 0.36 | 0.060 | 0.40 | -29.0 | 6.6 | 1.41 | 45 |
| courtyard | prior | colmap_incremental | 38/38 | 0.04 | 0.04 | 0.003 | 0.02 | 0.3 | - | 0.63 | 21 |
| courtyard | prior | glomap_global | 37/38 | 0.05 | 0.06 | 0.008 | 0.06 | - | - | 0.64 | 16 |
| courtyard | prior | mapanything | 38/38 | 0.90 | 0.94 | 0.246 | 1.64 | -5.3 | - | - | 16 |
| courtyard | prior | mapanything_ba | 38/38 | 0.04 | 0.05 | 0.005 | 0.04 | -5.5 | -74.0 | 0.65 | 32 |
| a42444515 | none | colmap_incremental | 15/90 | 4.25 | 1.61 | 0.019 | 1.84 | - | - | 0.38 | 1 |
| a42444515 | none | glomap_global | 67/90 | 28.79 | 28.02 | 0.364 | 13.38 | - | - | 0.59 | 2 |
| a42444515 | none | mapanything | 90/90 | 56.24 | 82.02 | 0.752 | 27.62 | 195.5 | - | - | 22 |
| a42444515 | none | mapanything_ba | 78/90 | 100.73 | 77.70 | 0.715 | 26.27 | 74.7 | 250.0 | 0.69 | 24 |
| a42444515 | prior | colmap_incremental | 16/90 | 7.63 | 1.52 | 0.026 | 2.15 | - | - | 0.42 | 1 |
| a42444515 | prior | glomap_global | 86/90 | 165.01 | 37.81 | 0.496 | 18.22 | - | - | 0.56 | 3 |
| a42444515 | prior | mapanything | 90/90 | 57.34 | 80.91 | 0.770 | 28.29 | 222.8 | - | - | 22 |
| a42444515 | prior | mapanything_ba | 81/90 | 47.88 | 82.80 | 0.779 | 28.62 | 224.8 | 25.1 | 0.71 | 24 |
| a42444821 | none | colmap_incremental | 11/106 | 6.22 | 3.82 | 0.025 | 1.48 | - | - | 0.38 | 1 |
| a42444821 | none | glomap_global | 36/106 | 67.00 | 8.57 | 0.431 | 17.59 | - | - | 0.63 | 1 |
| a42444821 | none | mapanything | 106/106 | 9.64 | 13.06 | 0.297 | 6.37 | 26.4 | - | - | 29 |
| a42444821 | none | mapanything_ba | 60/106 | 13.86 | 8.73 | 0.286 | 6.25 | 20.6 | 13.1 | 0.53 | 30 |
| a42444821 | prior | colmap_incremental | 14/106 | 3.52 | 1.15 | 0.021 | 1.53 | - | - | 0.65 | 1 |
| a42444821 | prior | glomap_global | 34/106 | 13.22 | 4.43 | 0.399 | 16.28 | - | - | 0.56 | 2 |
| a42444821 | prior | mapanything | 106/106 | 8.36 | 13.18 | 0.297 | 6.37 | 22.9 | - | - | 26 |
| a42444821 | prior | mapanything_ba | 64/106 | 12.31 | 17.73 | 0.347 | 7.57 | 14.5 | 10.1 | 0.65 | 28 |
| a42444793 | none | colmap_incremental | 21/125 | 2.95 | 1.32 | 0.016 | 0.95 | - | - | 0.41 | 2 |
| a42444793 | none | glomap_global | 116/125 | 69.26 | 49.73 | 0.465 | 21.67 | - | - | 0.85 | 5 |
| a42444793 | none | mapanything | 125/125 | 6.84 | 6.13 | 0.186 | 8.61 | 40.9 | - | - | 38 |
| a42444793 | none | mapanything_ba | 121/125 | 1.29 | 1.80 | 0.052 | 2.39 | 11.9 | 201.7 | 0.51 | 50 |
| a42444793 | prior | colmap_incremental | 21/125 | 163.07 | 26.09 | 0.197 | 11.56 | - | - | 0.82 | 3 |
| a42444793 | prior | glomap_global | 119/125 | 61.35 | 12.23 | 0.487 | 22.53 | - | - | 0.47 | 11 |
| a42444793 | prior | mapanything | 125/125 | 6.92 | 5.66 | 0.155 | 7.17 | 26.8 | - | - | 37 |
| a42444793 | prior | mapanything_ba | 121/125 | 1.52 | 1.98 | 0.051 | 2.37 | 11.7 | 164.6 | 0.54 | 45 |
| a42444858 | none | colmap_incremental | 68/133 | 1.28 | 1.52 | 0.018 | 0.66 | - | - | 0.55 | 6 |
| a42444858 | none | glomap_global | 110/133 | 5.80 | 1.64 | 0.062 | 1.19 | - | - | 0.54 | 11 |
| a42444858 | none | mapanything | 133/133 | 5.73 | 5.49 | 0.283 | 5.44 | 1.2 | - | - | 38 |
| a42444858 | none | mapanything_ba | 108/133 | 1.82 | 1.48 | 0.030 | 0.57 | -4.7 | 24.5 | 0.56 | 58 |
| a42444858 | prior | colmap_incremental | 86/133 | 4.71 | 1.49 | 0.062 | 1.21 | - | - | 0.56 | 11 |
| a42444858 | prior | glomap_global | 109/133 | 54.77 | 1.69 | 0.463 | 8.90 | - | - | 0.54 | 11 |
| a42444858 | prior | mapanything | 133/133 | 3.61 | 4.89 | 0.213 | 4.10 | -1.7 | - | - | 39 |
| a42444858 | prior | mapanything_ba | 108/133 | 4.11 | 1.48 | 0.034 | 0.66 | -4.3 | 25.9 | 0.56 | 52 |
| a42444873 | none | colmap_incremental | 179/218 | 1.59 | 1.04 | 0.048 | 0.70 | - | - | 0.57 | 11 |
| a42444873 | none | glomap_global | 204/218 | 1.92 | 1.16 | 0.064 | 0.92 | - | - | 0.58 | 9 |
| a42444873 | none | mapanything | 218/218 | 12.05 | 9.82 | 0.815 | 11.66 | 39.3 | - | - | 68 |
| a42444873 | none | mapanything_ba | 202/218 | 5.74 | 6.29 | 0.831 | 11.91 | 17.3 | 38.0 | 0.64 | 93 |
| a42444873 | prior | colmap_incremental | 181/218 | 1.66 | 1.17 | 0.052 | 0.76 | - | - | 0.58 | 9 |
| a42444873 | prior | glomap_global | 202/218 | 32.72 | 1.36 | 1.581 | 22.62 | - | - | 0.60 | 10 |
| a42444873 | prior | mapanything | 218/218 | 10.36 | 10.46 | 0.800 | 11.44 | 39.3 | - | - | 73 |
| a42444873 | prior | mapanything_ba | 200/218 | 6.81 | 9.16 | 0.941 | 13.50 | 22.5 | 37.2 | 0.78 | 87 |

**ETH3D.** The coarse-to-fine adjustment from MapAnything's poses comes close to the classical
routes: relative rotation 0.48° against COLMAP's 0.69° on pipes and 0.36° against 0.40° on
courtyard, but 0.82° against 0.53° on kicker; median positions within 7 mm of COLMAP's on all
three. MapAnything alone is 0.9–1.7° relative and 12–37 cm off. Its metric scale is +15.3%, +4.1%
and −28.3% on the three scenes. With priors (ground-truth intrinsics, noised poses) COLMAP with
position priors and MapAnything + BA are equally close to the truth (0.02–0.08° relative, 1–5 mm),
and the scale is within 1.1% for COLMAP (from the priors) and within 5.5% for MapAnything + BA
(from MapAnything, which follows the pose priors).

**ARKitScenes, low texture (42444515, 42444821, 42444793).** No route covers 42444515 or 42444821
well. COLMAP's incremental mapper registers 10–18% of the frames, at 1.1–3.8° relative, except 26° on
42444793 with intrinsics. GLOMAP registers more (32–96%) at 4.4–50° relative. MapAnything fails
outright on 42444515 (82° relative; the same through its own demo code on 16 frames, so not this
wrapper) and is poor on 42444821 (13°). On 42444793, the bathroom, MapAnything + BA covers the most
frames well: 121 of 125 at 1.8° relative, 5 cm, scale +11.9%.

**ARKitScenes, textured (42444858, 42444873).** COLMAP registers 51–65% and 82–83% of the frames at
1.0–1.5° relative; GLOMAP registers 82–83% and 93–94% at 1.2–1.7°. MapAnything + BA registers 81%
and 92–93%: on 42444858 at 1.5° relative, 3 cm and scale −4.7% (−4.3% with intrinsics); on
42444873 MapAnything is wrong in parts (9.8° relative, 0.8 m) and the adjustment does not repair it
(6.3°).

Each route's errors are over the frames it registers, against ARKit; no comparison is made on the
frames two routes share.

**Priors.** On ETH3D, intrinsics and noised poses take COLMAP, GLOMAP and MapAnything + BA from
tenths of a degree to hundredths (GLOMAP 0.06–0.11°); MapAnything alone stays at 0.7–1.0° relative,
but its scale comes within 5.3%. On ARKitScenes, ARKit's intrinsics move the results in both
directions without a pattern: COLMAP registers 86 frames of 42444858 instead of 68, but its
42444793 model goes from 1.3° to 26° relative; MapAnything's errors stay where they were.

**BA drift does not flag a failed learned pass.** Before anchoring, the adjustment moved the scale
by 10–250% where MapAnything was wrong (42444515, 42444821, 42444873), by 25–26% on 42444858 where
it was right, and also by 41% (kicker), 74% (courtyard with priors) and 165–202% (42444793) on runs
that ended close to the truth.

**Cost.** MapAnything's inference takes 3–7 s for 14–38 ETH3D images and 21–71 s for 90–218 ARKit
frames on the GB10. Peak GPU memory grows with the view count: 9.7 GiB (14 views), 15.9 (31), 18.4
(38), 42.6–58.9 GiB (90–218); above about 30 views it does not fit in what gpu-mode `prod` leaves
free.

**Proposed decision (for the owner).** The learned first pass does not replace the classical
routes. It enters a recipe as a second route beside COLMAP, used where COLMAP registers too little:
on 42444793 it is the only route that registers most frames at under 2°, and on 42444858 it
registers 81% of the frames against COLMAP's 51% at the same relative rotation. It fails without
warning on some scenes (42444515, 42444873), and BA drift does not show it, so a check against the
classical model is needed before its poses are kept; that check is not built or tested here. Its
metric scale is off by up to 29% on ETH3D (courtyard) and up to 41% on the usable ARKit runs
(MapAnything alone on 42444793), so it is not a source of scale on its own.

**Decision (owner, 2026-11-25).** Yes, as an optional second route beside COLMAP. It runs where
COLMAP registers too little, its poses are kept only after the agreement check against the
classical model on the frames both register, and it is never the source of metric scale. Above
about 30 views it needs a `free` GPU window on the GB10. Only the Apache checkpoint is used. Next
for this route: build and test the agreement check.

## Not covered

- ARKitScenes pose error is agreement with ARKit's tracking, which has its own drift; the laser
  scans that could check it are not downloaded.
- `lowres_depth` (LiDAR) is downloaded but not used, neither as a depth prior nor as a check.
- Pose priors are not tested on ARKitScenes (see above).
- One noise level and one seed for the ETH3D pose priors.
