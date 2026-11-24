# RC-P4 — Dense, mesh, texture and splat, measured

**Proves:** That the products are measurably good, not just plausible. See the
[brief](../../docs/concept/RC-brief.md) §5.

**Proven when:** Dense cloud and mesh are scored against ETH3D's laser scans for accuracy,
completeness and F-score at ETH3D's evaluation thresholds (1, 2, 5, 10, 20 and 50 cm, with the
BSD-licensed ETH3D multi-view-evaluation tool); the textured mesh and the splat come from the same
poses; the splat's PSNR and SSIM on held-out views of at least two Mip-NeRF 360 scenes are recorded;
the seven complaint measurements of §0 each have a first number.

Status: **not proven yet.** The GPU phase ran on 2026-11-24 on the GB10 in `free` mode. Three clauses
have numbers: the dense cloud and the mesh are scored at all six tolerances (two pose sources), the
splat has held-out PSNR and SSIM on garden and counter at 30,000 steps, and the textured mesh and
the courtyard splat share one pose set. Three things keep it open: measurement 5 (underwater colour)
has no number and no data, the texture-side parts of measurements 1 and 4 are not computed, and the
courtyard splat ran 7,000 steps, not 30,000 (the 4-hour GPU budget ran out). See "Not covered".

## Results (ETH3D `courtyard`, 38 DSLR images, scans in the scan frame)

Two runs, both at `max_image_size` 3000 (3000×1957 undistorted, half of 6048×4032), both cropped to
the scans' bounding box plus 0.5 m before scoring, scored with the ETH3D tool at 1, 2, 5, 10, 20 and
50 cm. The mesh is COLMAP Delaunay meshing; the tool reads only vertices, so the cropped mesh is
sampled to 5 M points by area (about 2.2 cm spacing over its 2,333 m², see "Not covered").

- **`p1`**: poses from RC-P1's GB10 COLMAP incremental model, moved into the scan frame by a Sim(3)
  fit of camera centres. This is what the engine would deliver.
- **`gt`**: control, poses from ETH3D's own ground-truth calibration. It separates registration
  error from dense and meshing error. The `THIN_PRISM_FISHEYE` undistortion worked.

| Product | Poses | Metric | 1 cm | 2 cm | 5 cm | 10 cm | 20 cm | 50 cm |
|---|---|---|---|---|---|---|---|---|
| Dense cloud | p1 | accuracy | 0.138 | 0.266 | 0.662 | 0.864 | 0.963 | 0.987 |
| | | completeness | 0.019 | 0.078 | 0.237 | 0.381 | 0.486 | 0.647 |
| | | F1 | 0.034 | 0.120 | 0.349 | 0.529 | 0.646 | 0.782 |
| Mesh | p1 | accuracy | 0.100 | 0.188 | 0.418 | 0.642 | 0.822 | 0.936 |
| | | completeness | 0.034 | 0.145 | 0.378 | 0.545 | 0.654 | 0.776 |
| | | F1 | 0.051 | 0.164 | 0.397 | 0.590 | 0.729 | 0.848 |
| Dense cloud | gt | accuracy | 0.760 | 0.894 | 0.962 | 0.991 | 0.997 | 0.998 |
| | | completeness | 0.287 | 0.661 | 0.815 | 0.865 | 0.897 | 0.929 |
| | | F1 | 0.417 | 0.760 | 0.882 | 0.924 | 0.944 | 0.962 |
| Mesh | gt | accuracy | 0.557 | 0.743 | 0.880 | 0.954 | 0.983 | 0.993 |
| | | completeness | 0.225 | 0.688 | 0.899 | 0.920 | 0.934 | 0.948 |
| | | F1 | 0.320 | 0.714 | 0.890 | 0.937 | 0.958 | 0.970 |

The finding: **registration error, not dense depth, limits the result.** With RC-P1's poses the
fused cloud has 1.04 M points and an F1 of 0.35 at 5 cm; with ground-truth poses the same dense
stage gives 4.64 M points and 0.88. The Sim(3) fit of RC-P1's camera centres leaves a median
residual of 6.1 cm (95th percentile 16.9 cm), which is above the 1 and 2 cm tolerances. Why RC-P1's
poses degrade the dense stage this much (its camera model, its intrinsics, or the pose error itself)
is not investigated. The same cause probably holds the splat's PSNR down (next section).

The earlier smoke test on RC-P2's 2000-px cloud (uncropped, same RC-P1 poses) scored F1 0.392 at
5 cm, higher than the 3000-px cloud's 0.349; the difference is not explained (the crop removed 686
points, so it is not the crop).

Dense-stage cost, from the scripts' own timers on the GB10:

| Run | Undistort | PatchMatch (photometric + geometric) | Fusion | Fused points | Delaunay mesh | Mesh faces |
|---|---|---|---|---|---|---|
| p1 | 3.5 s | 1,886.1 s | 39.9 s | 1,035,715 (28 MB) | 25.5 s | 502,902 (cropped) |
| gt | 5.8 s | 1,926.9 s | 32.2 s | 4,643,779 (125 MB) | 144 s | not recorded |

Host memory peak 43 to 44 GB used against 34 to 38 GB idle (lowest 76 to 78 GB available); GPU
process memory 3.0 GiB. ETH3D scoring: 72 to 101 s per product, 5.4 to 6.8 GB peak RSS.

## Textured mesh (MVS-Texturing, from the `p1` mesh and poses)

`texrecon` (BSD-3-Clause) is built and ran on the cropped Delaunay mesh with the 38 cameras of the
`p1` undistorted workspace, the same workspace the courtyard splat trains on. 52.5 s on 2 CPU
threads: 26,893 texture patches in 115 atlases (PNG), 81,579 of 502,902 faces (16.2%) seen by no
image. Output `runs/p4/courtyard_3000_p1/mesh/textured.obj` (51.5 MB) plus the atlases, on the DGX.
Dependencies it fetched at build time, with the licence file each ships: MVE (nmoehrle fork, commit
91c0f3f) BSD-3-Clause; mapMAP (fa526e0) BSD-style, Copyright 2016 Daniel Thuerck; rayint (b62c890)
BSD-3-Clause; Eigen 3.3.2 (compiled with `EIGEN_MPL2_ONLY`) MPL-2.0. `setup_texrecon.sh` records the
build: `-mfpmath=sse` and MVE's `-msse2 -msse3 -msse4 -mpopcnt` removed (x86-only), built with 2
jobs against `~/.cache/recce/texenv`. The converter is `make_texrecon_scene.py`; `run_texture.sh`
runs it.

## Splats (gsplat 1.5.3, `simple_trainer.py default`, every 8th image held out)

| Scene | Poses | data_factor | Steps | PSNR (dB) | SSIM | LPIPS | Gaussians | Wall time | Torch memory / GPU process |
|---|---|---|---|---|---|---|---|---|---|
| garden (185 photos) | COLMAP, as shipped | 4 | 30,000 | 27.71 | 0.872 | 0.070 | 6,613,332 | 5,956 s | 9.75 GB / 14.3 GiB |
| garden | | | 7,000 | 26.66 | 0.840 | 0.114 | 4,786,525 | | |
| counter (240 photos) | COLMAP, as shipped | 2 | 30,000 | 29.19 | 0.918 | 0.136 | 1,631,453 | 2,325 s | 2.50 GB / 3.5 GiB |
| counter | | | 7,000 | 27.56 | 0.892 | 0.183 | 1,299,084 | | |
| courtyard (38 images) | `p1`, same as mesh and texture | 2 | 7,000 | 18.39 | 0.638 | 0.348 | 3,203,741 | 556 s | 4.77 GB / 6.7 GiB |
| courtyard | `gt` (diagnostic) | 2 | 7,000 | 20.93 | 0.823 | 0.238 | 2,538,886 | 507 s | not recorded |

Held-out PSNR and SSIM on two Mip-NeRF 360 scenes are recorded (garden, counter), with the trainer's
default densification and no tuning. The garden run reaches 14.3 GiB of GPU process memory, close to
the 15 GB that `prod` mode leaves, so it may not fit beside the production vLLMs. Host memory peaked
at 56 GB used (65 GB lowest available) for garden.

Courtyard: the `p1` splat trains on the same undistorted workspace as the mesh and the texture, so
"the textured mesh and the splat come from the same poses" holds. Its PSNR is low (18.39 dB, as in
RC-P2's 18.83 dB at 2000 px). The `gt`-pose splat, same 7,000 steps and settings, reaches 20.93 dB
and SSIM 0.823 against 0.638, which ties part of the low quality to the RC-P1 poses. 20.9 dB is
still low for a splat; 38 images of an outdoor scene and 7,000 steps are possible causes, none
tested.

## The seven measurements: first numbers

All on courtyard unless noted; `measure.py` produces rows 2 and 3 from the cropped fused cloud, and
1 and 4 from the 38 source JPEGs. Results are in `runs/p4/measure_p1.json` and `measure_gt.json`.

| # | Complaint | First number | How it was computed | Missing |
|---|---|---|---|---|
| 1 | Blurry, smeared textures | Sharpness: variance of the Laplacian of the grey image at 2000 px width, median 802, minimum 363, 10th percentile 432 (38 images). Texture: 16.2% of faces unseen by any image | Photos resized to 2000 px wide; 3×3 Laplacian variance. Unseen faces from texrecon's log | Texture resolution per surface area (per-face ground sampling distance) and texel blend count: not computed |
| 2 | Noisy or melted geometry | Distance of fused points to the nearest scan point (points within 10 cm of a scan: 87.8% for `p1`, 94.9% for `gt`): median 2.75 cm and MAD 1.13 cm (`p1`); 1.20 cm and 0.56 cm (`gt`). Depth-map consistency, geometric over photometric valid pixels, median across 38 views: 0.32 (`p1`), 0.71 (`gt`) | KD-tree of a 4 M-point subsample of the two scans in the scan frame; depth maps counted from the COLMAP `.bin` files | ETH3D's accuracy (above) is the occlusion-aware version of the distance |
| 3 | Holes | Completeness: the table above (for example 0.24 at 5 cm for `p1`, 0.82 for `gt`). Per 1 m cell, share of scan points with a fused point within 5 cm: median 0.4% for `p1` (325 of 474 cells below 10%), 85.5% for `gt` (87 of 474 below 10%) | Same KD-tree, 474 cells of the scans' footprint with at least 100 sampled points | Cells are in the scan frame, not images; RC-P3's coverage on this model is not joined |
| 4 | Colour seams | Exposure spread: standard deviation of log2 mean linear luminance across the 38 images, 0.276 stops. White balance: standard deviation of log2 R/G 0.060, of log2 B/G 0.039 | Per-image mean of linearised sRGB over the whole image | Seam contrast in the texture: not computed (the textured mesh exists now; the script is not written) |
| 5 | Wrong colour underwater | None. Grey-world cast of the above-water set, as a control only: mean R/G 1.066, B/G 0.983 | Mean of per-image channel ratios | No colour target and no water in ETH3D or Mip-NeRF 360; needs an underwater set with a chart (Sea-thru or SQUID, 38 to 46 GB, not downloaded). A decision for the owner |
| 6 | Untrustworthy scale | Photos alone give no scale: the Sim(3) to ETH3D's frame is 1.3513 m per model unit. Against measured distances (all 703 camera pairs, ground-truth centres): median error 0.90%, 95th percentile 6.1%, maximum 23.1%; camera-centre residual median 6.1 cm | `align_model.py` on RC-P1's model; `runs/p4/courtyard_3000_p1/align/sim3.json` | Distances measured on the final model's surface, not between camera centres |
| 7 | Slow | Wall-clock on the GB10 (table above and below); transfer: the 28 MB fused cloud copied in 3.0 s through the Mac mini hop (about 9 MB/s); cost per run in GPU time, no money figure (owned hardware) | The scripts' timers, `status.txt`, `wall.txt`; one timed `scp` | No second machine (X3, M4 Pro) was timed, no rented-GPU cost |

GPU time used, busy time summed from the timers: p1 dense 1,930 s, gt dense 1,966 s, garden 5,956 s,
counter 2,325 s, courtyard splat 556 s, courtyard `gt` splat 507 s, total about 13,240 s (3.7 h),
against the 4-hour budget. The CPU steps ran beside them or after them and are not counted. A first
attempt at the courtyard splat failed in 30 s (the trainer wants an `images_2` folder, and an
`images_2_png/<subfolder>` for resized copies); `downscale_images.py` and a pre-made folder fixed it.

## Setup (2026-11-24, DGX `dgx-llm-1`, aarch64, user `claude`; user-level only)

### ETH3D multi-view-evaluation tool

`setup_evalenv.sh`. Environment `~/.cache/recce/evalenv` (micromamba, conda-forge, 3.5 GB): PCL 1.15.1,
libboost 1.90.0, Eigen 5.0.1, p7zip 16.02, cmake 4.5.1, make; host `g++` 13.3.0. Source
`~/.cache/recce/mve-src`, commit `0daa4f4de036d47d37a6ba054c51fd66642ef896`, BSD licence
(`LICENSE.txt`). Four edits to `CMakeLists.txt` for aarch64 and current libraries, in the clone only:
x86-only flags and `-std=c++11` removed, `cmake_minimum_required` raised to 3.5, Boost `system`
removed, the `CMAKE_MODULE_PATH` line removed. The tool has no `--help`; it prints its usage:

```
Usage example: ./ETH3DMultiViewEvaluation --tolerances 0.1,0.2 --reconstruction_ply_path path/to/reconstruction.ply --ground_truth_mlp_path path/to/ground-truth.mlp
```

### Data

| Item | Where on the DGX | Size |
|---|---|---|
| ETH3D courtyard `dslr_scan_eval` (CC BY-NC-SA 4.0), `https://www.eth3d.net/data/courtyard_dslr_scan_eval.7z` | `datasets/eth3d/courtyard/courtyard/dslr_scan_eval/` | 182 MB archive, 413 MB unpacked |
| Mip-NeRF 360 `360_v2.zip` (data licence not stated) | `datasets/mipnerf360/360_v2.zip` | 12,535,427,936 B, kept |
| `garden` | `datasets/mipnerf360/360_v2/garden/` | 2.9 GB, 185 photos, `images_4` 1297×840 |
| `counter` | `datasets/mipnerf360/360_v2/counter/` | 1.2 GB, 240 photos, `images_2` 1558×1038 |

Why these scenes: `garden` is the outdoor scene splat papers report, so the number can be compared;
`counter` is the smallest indoor scene (240 photos; `room` has 311).

### Scripts

`fetch_data.sh`, `setup_evalenv.sh`, `setup_texrecon.sh` (setup); `run_courtyard.sh [size] [p1|gt]`
(align, dense, fusion, mesh, crop, score), `run_gpu_rest.sh` (the control run, then the three
splats, with the 4-hour budget), `run_gsplat.sh`, `run_texture.sh`; `align_model.py`,
`run_dense.py`, `run_mesh.py`, `crop.py`, `sample_mesh.py`, `run_eval.py`, `make_texrecon_scene.py`,
`downscale_images.py`, `measure.py`, `summarize.py`, `apply_sim3.py`. Small results (JSON, logs,
GPU samples, trainer stats, 115 files, 2.2 MB) are copied to `~/.cache/recce/runs/p4/` on the
workstation; the clouds, meshes, textures, depth maps and splat PLYs (7 GB per courtyard run, 3.2 GB
for garden) stay on the DGX under `~/.cache/recce/runs/p4/`.

### Findings from the work that change what is known

- **Poisson meshing fails in this build.** `pycolmap.poisson_meshing` (conda-forge pycolmap 4.2.1,
  aarch64) aborts with `Failed to close loop` (`FEMTree.LevelSet.3D.inl`, line 1645) at depth 8, 9,
  10, 11 and 13, trim 0 and 10, on RC-P2's cloud and on a clean synthetic sphere with exact normals.
  Cause not investigated. The mesh uses `dense_delaunay_meshing`.
- **The evaluator is memory-bound by the scans:** about 5 GB for the two courtyard scans plus about
  0.2 GB per million points. A smoke run with 15 M points reached 8.3 GB before I stopped it, briefly
  over the 8 GB limit of the setup phase.
- **A driver bug cost 17 minutes of idle GPU:** the first `run_gpu_rest.sh` waited on a status line
  whose name did not match; I restarted it and set its clock back to count only busy time.
- **`depth_maps` in `p1/results.json` reads 0** because the script globbed one folder too shallow
  (the maps sit in `stereo/depth_maps/dslr_images/`); `run_dense.py` now uses `rglob`, and
  `measure.py` found 38 views for both runs.

## Not covered

- **The courtyard splat at 30,000 steps.** Only 7,000 steps ran, for both `p1` and `gt` poses; the
  4-hour budget (3.7 h spent) left no room. Its PSNR is not comparable with the 30,000-step garden
  and counter numbers.
- **Measurement 5** has no number (no data). **Measurements 1 and 4** lack the texture-side numbers:
  per-face texture resolution, texel blend count, seam contrast. The texture exists; no script
  reads it. Measurements 2 and 3 use a KD-tree on a 4 M-point scan subsample, not ETH3D's
  occlusion-aware metric, and measure 6 only camera centres.
- **Mesh scoring is weak.** The Delaunay mesh is untrimmed beyond the crop box: after the crop it
  still covers 2,333 m², so 5 M area-uniform samples give about 2.2 cm spacing, and most samples sit
  on faces far from the photographed surface. The mesh F1 at 1 and 2 cm is not a clean figure. The
  Delaunay parameters are defaults; no hole filling, smoothing or decimation was tried; Poisson
  fails; no mesh quality figure (watertightness, face count against area) is computed.
- **Only courtyard and only 3000 px.** No full-resolution dense run, no `kicker` or `pipes`, no seed
  repeat. The 2000 against 3000 px difference (F1 0.392 against 0.349 at 5 cm) is unexplained.
- **Why RC-P1's poses give so much less** (1.04 M against 4.64 M fused points) is not investigated:
  intrinsics, distortion model, pose error and the Sim(3) fit are all candidates.
- **gsplat:** default strategy and densification only; no seed repeat; no comparison with published
  numbers (not read here); the 7,000-step courtyard PSNRs are unexplained beyond the pose finding.
  The garden run may not fit the 15 GB `prod` mode leaves; coexistence with the vLLMs is untested.
- **The `gt` splat's GPU process memory** was not extracted. The `gt` mesh face count was not
  recorded.
- **Data licence.** Mip-NeRF 360's data licence is not stated; keep the numbers local until it is
  read (see [public-datasets.md](../../docs/reference/public-datasets.md)). ETH3D results are
  published-number use under CC BY-NC-SA with citation.
