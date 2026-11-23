# Research: the photogrammetry landscape (2026-11-23)

> **Corrections (2026-11-23, from the tools overview pass):** `KHR_gaussian_splatting` is
> ratified, not a release candidate — the spec README on Khronos `main` reads "Complete, Ratified
> by the Khronos Group". LightGlue's README states its weights are Apache-2.0; only SuperPoint and
> its weights are restrictive, so "LightGlue weights inherit SuperPoint's restriction" below is
> wrong. Current figures live in [tools overview](../reference/tools-overview.md).

Input to the brief and the prototype plan. Gathered by a research agent from web sources on
2026-11-23. `[V]` means confirmed on a primary page that day, with the URL. `[U]` means from
memory or a search snippet only, not checked. Treat every `[U]` as a lead, not a fact.

## Open-source pipelines

- **COLMAP** [V] — BSD-3. GLOMAP (global SfM) is merged in. CUDA wheels on PyPI; AMD via HIP/ROCm
  builds. The format hub: nearly every other tool imports or exports COLMAP.
  <https://github.com/colmap/colmap>
- **WebODM** [V, partly] — AGPL-3.0. Django 5.2 + Celery + PostgreSQL + Valkey, processing on
  NodeODM workers (engine now named "ODX"). Outputs orthophotos, point clouds, DEMs, textured
  meshes, and now gaussian splats. NodeODM has its own small REST API (task new / upload / status /
  output / cancel) [U]; one WebODM schedules onto many nodes [U]. The closest analogue to
  "web UI + API + workers", but aerial-only: no object, fisheye, RAW or known-pose workflow.
  <https://github.com/WebODM/WebODM>
- **gsplat** [V] — Apache-2.0. Pinhole and fisheye, 3DGUT, MCMC. No prebuilt aarch64 wheels;
  JIT build. <https://github.com/nerfstudio-project/gsplat>
- **Brush** [V] — Apache-2.0. Splat training on wgpu (no CUDA): Mac, Windows, Linux, Android,
  web. Trains from COLMAP or nerfstudio data; supports masks. <https://github.com/ArthurBrussee/brush>
- **nerfstudio** [U] — Apache-2.0; ran at 1.1.5 on a GB10 in one write-up.
- **OpenMVG** (MPL2), **OpenMVS** (AGPL3 — a risk for a hosted service), **AliceVision/Meshroom**
  (MPL2), **OpenSplat** (AGPL3), **Instant-NGP** (NVIDIA non-commercial), **2DGS / PGSR** (research
  code, licences unchecked) [all U].

## Learned feed-forward SfM

| Model | Code | Weights | Notes |
|---|---|---|---|
| VGGT (Meta/Oxford) | not captured [U] | VGGT-1B non-commercial; VGGT-1B-Commercial gated by form [V] | CVPR 2025 best paper; COLMAP export; "VGGT-Omega" May 2026, licence unread. <https://github.com/facebookresearch/vggt> |
| MapAnything (Meta) | Apache-2.0 [V] | `map-anything` CC-BY-NC; `map-anything-apache` Apache-2.0 [V] | Takes optional intrinsics, poses, depth; metric output; up to ~2,000 views on 140 GB. <https://github.com/facebookresearch/map-anything> |
| Pi3 / Pi3X | BSD-3 [V] | CC-BY-NC 4.0 [V] | Pi3X accepts optional pose/intrinsics/depth; approximate metric scale. <https://github.com/yyfz/Pi3> |
| DUSt3R / MASt3R / MASt3R-SfM (Naver) | CC BY-NC-SA 4.0 [V] | same [V] | Non-commercial. <https://github.com/naver/mast3r> |

Feed-forward models run at low resolution (~518 px for VGGT [U]). Use them for initialisation,
pose priors, metric scale and sparse-view cases; COLMAP/GLOMAP bundle adjustment stays the
accuracy engine. No head-to-head numbers were checked.

## Feature matching [all U]

SuperPoint weights: restrictive (Magic Leap); LightGlue weights trained on SuperPoint inherit it.
ALIKED BSD-3, RoMa MIT, hloc Apache-2.0. A clean stack: ALIKED+LightGlue or RoMa, weights checked.

## Commercial tools

- **RealityScan** (Epic, ex-RealityCapture) [V via news]: free under $1M revenue, $1,250/seat/year
  above. 2.1 (Nov 2025) added CLI `importColmap` and a Remote Command plugin (REST/gRPC); 2.2
  (Jun 2026) added AMD GPUs. Windows-only [U].
- **Agisoft Metashape** [partly V]: Python API, scripting in Professional only. A `metashape-mcp`
  package exists on PyPI (106 tools reported; author and licence unverified).
- **Polycam** (API mentioned), **KIRI Engine** (pay-per-credit API incl. 3DGS-to-mesh) [V];
  **Luma** ($1/capture API, possibly stale), **Pix4D**, **Scaniverse**, **Apple Object Capture**
  (macOS/iOS only, USDZ out) [U].

## MCP and agents

`metashape-mcp` (above) and the paper "SceneAgent" (arXiv 2610.34745, unread). Two searches found
no MCP server for COLMAP or splat training — a fact about two searches, not proof of a gap.

## Formats and viewers

- `KHR_gaussian_splatting` reached release candidate 2026-02-04, with
  `KHR_gaussian_splatting_compression_spz` [V].
  <https://digitalproduction.com/2026/02/04/gltf-learns-to-splat-without-losing-the-plot/>
- PlayCanvas reads PLY, SOG, SPZ and splat-GLB; `splat-transform` converts between them [V].
- Cesium 3D Tiles added LOD splats in April 2026 [V].
- GLB for web meshes, USDZ for Apple/AR, PLY/OBJ for interchange; three.js, Babylon, SuperSplat,
  Spark, potree as viewers [U].

## ARM64 / GB10

One blog (not NVIDIA) ran COLMAP, gsplat and nerfstudio on a GB10: DGX OS on Ubuntu 24.04,
CUDA 13.0, compute capability 12.1, PyTorch 2.9.0+cu130. It needed `TORCH_CUDA_ARCH_LIST=12.0`,
and apt COLMAP fell back to CPU SIFT headless.
<https://dev.classmethod.jp/en/articles/dgx-spark-3dgs-digital-twin/>

## Gaps the research agent named (its judgement, unsourced)

1. Agent-readable quality state: coverage, reprojection error, unregistered images, "capture more
   here".
2. Hybrid: feed-forward poses and scale, verified by COLMAP bundle adjustment, with fallback.
3. Robot-supplied poses and intrinsics as first-class input.
4. Mixed sensors in one scene (iPhone LiDAR, GoPro fisheye, DSLR RAW).
5. Production-quality textured mesh from splats.
6. A licence-clean, commercial-safe stack.
7. Tested ARM64 containers for the whole stack.

## Not verified

Pix4D, Scaniverse, Object Capture details; OpenMVS, AliceVision, OpenSplat, Instant-NGP status;
DUSt3R, VGGT-Omega and SAM 3 licences; web viewer status; Luma pricing; `metashape-mcp`
provenance; most release dates.
