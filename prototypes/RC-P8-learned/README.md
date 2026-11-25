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

Status: **not proven yet.** Code checked on the CPU only; the GPU runs wait for a `free` window.

## Not covered

- ARKitScenes pose error is agreement with ARKit's tracking, which has its own drift; the laser
  scans that could check it are not downloaded.
- `lowres_depth` (LiDAR) is downloaded but not used, neither as a depth prior nor as a check.
- Pose priors are not tested on ARKitScenes (see above).
- One noise level and one seed for the ETH3D pose priors.
