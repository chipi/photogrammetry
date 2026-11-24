# Tools overview

The catalogue of every tool, library, model, format and product that bears on the photogrammetry
project, kept open as a lookup while designing and prototyping. It merges the two research notes
([landscape](../wip/research-landscape-2026-11-23.md),
[Metashape and underwater](../wip/research-metashape-underwater-2026-11-23.md)) with a licence and
platform pass done the same day. As of 2026-11-23.

**Verification.** `[V]` = read on a primary page on 2026-11-23 (GitHub repo and LICENSE file, official
docs, PyPI file list); the URL follows. `[U]` = memory, a search snippet or a secondary page; a lead,
not a fact. A `[V]` carried from a research note keeps that note's reading. Where the platform column
cites "wheels", it is the PyPI file list read today, not an install test.

**Licence classes.** *Permissive* (MIT, BSD, Apache-2.0, MPL-2.0 file-level) · *Copyleft* (GPL, LGPL,
AGPL) · *Non-commercial* (CC-BY-NC, research-only, NVIDIA non-commercial) · *Custom* (a bespoke
agreement that is neither OSI-permissive nor non-commercial, read the text) · *Proprietary*.

**Role.** *Default* = in the permissive default stack. *Plug-in* = optional, labelled, never required.
*Reference* = compared against or read, not shipped. *Not used*.

**Policy.** The default stack is permissive so it can be open-sourced. Non-commercial weights and
AGPL/GPL tools are optional plug-ins. Engine is Python first. Machines: M4 Pro (Metal), GB10 (ARM64 +
CUDA 13), X3 (ROCm/HIP or Vulkan, x86_64 Linux), iMac Pro (CPU, macOS x86_64).

## 1. End-to-end pipelines (open source)

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| COLMAP | SfM + MVS; the format hub. GLOMAP merged in. | Permissive, BSD-3 [V]. Dependencies licensed separately; a build may change the effective licence. | CUDA; HIP/ROCm build (`-DHIP_ENABLED=ON`, accelerates `patch_match_stereo` and GPU SIFT) [V]; builds on Linux/Mac/Windows [V]; Metal/Vulkan not in docs read [U]; aarch64 by source build | Default (SfM, BA); dense via CUDA/HIP only | <https://github.com/colmap/colmap> [V]; <https://github.com/colmap/colmap/blob/main/doc/install.rst> [V] |
| GLOMAP | Global SfM | Permissive, BSD-3 [V] | CPU/CUDA per COLMAP; standalone repo, merged into COLMAP | Default option | <https://github.com/colmap/glomap> [V] |
| pycolmap | Python bindings for COLMAP SfM and MVS | Permissive, BSD-3 [V] | PyPI 4.2.1 wheels: Linux x86_64, macOS arm64 (14.0+), Windows; **no Linux aarch64, no macOS x86_64**; CUDA 12 wheels only as `pycolmap-cuda12`, Linux x86_64 [V] | Default (Python API) | <https://pypi.org/project/pycolmap/> [V] |
| WebODM / NodeODM (ODX) | Web UI + API + worker nodes; orthophotos, point clouds, DEMs, meshes, splats | Copyleft, AGPL-3.0 [V, partly] | Docker; aerial-only workflow; NodeODM REST API (task new/upload/status/output/cancel) [U]; one WebODM schedules many nodes [U] | Reference (closest analogue) | <https://github.com/WebODM/WebODM> |
| Meshroom / AliceVision | Node-graph photogrammetry, caching, render farm, plugins | Permissive (file-level), MPL-2.0 [V Meshroom page note]; GitHub reports "NOASSERTION" for both repos, LICENSE not read [U] | CUDA for depth maps [U] | Reference | <https://github.com/alicevision/Meshroom> |
| OpenMVG | SfM library | Permissive (file-level), MPL-2.0 [V] | CPU | Reference | <https://github.com/openMVG/openMVG> [V] |
| OpenMVS | Dense reconstruction, meshing, refinement, texturing | **Copyleft, AGPL-3.0 [V]**; a risk for a hosted service | CPU, CUDA [U] | Plug-in only | <https://github.com/cdcseacave/openMVS> [V] |
| nerfstudio | Radiance-field framework; transforms.json | Permissive, Apache-2.0 [U]; ran at 1.1.5 on a GB10 in one write-up [U] | CUDA | Reference | <https://github.com/nerfstudio-project/nerfstudio> |
| Refractive COLMAP (IROS 2024) | SfM with flat and dome port refraction | Open source, licence not stated [V] | COLMAP-based | Reference (underwater) | <https://arxiv.org/abs/2403.08640> |

## 2. Structure from motion and bundle adjustment

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| COLMAP incremental mapper | Incremental SfM + BA (Ceres) | Permissive, BSD-3 [V] | CPU; optional CUDA Ceres solver "Caspar", off by default [V] | Default | <https://github.com/colmap/colmap/blob/main/doc/install.rst> [V] |
| GLOMAP global mapper | Global rotation/position averaging | Permissive, BSD-3 [V] | CPU | Default (fast path) | <https://github.com/colmap/glomap> [V] |
| COLMAP hierarchical mapper | Clustered reconstruction on one box | Permissive, BSD-3 [V] | CPU | Default (basis for spatial partitioning) | <https://github.com/colmap/colmap> |
| Ceres Solver | Nonlinear least squares under COLMAP | Permissive, Apache-2.0 [U] | CPU, CUDA | Default (transitive) | unverified |

## 3. Features and matching

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| COLMAP SIFT | Classical features, GPU and CPU | Permissive, BSD-3 [V] | CUDA, HIP [V]; CPU fallback (apt COLMAP fell back to CPU SIFT headless on GB10 [V blog]) | Default | <https://dev.classmethod.jp/en/articles/dgx-spark-3dgs-digital-twin/> |
| hloc | Feature + match pipeline over COLMAP | Permissive, Apache-2.0 [V] | PyTorch; not on PyPI under that name [U] | Default (driver option) | <https://github.com/cvg/Hierarchical-Localization> [V] |
| LightGlue | Learned matcher | Code **and** released weights Apache-2.0 per its README [V]; the **SuperPoint** extractor and its weights follow a different, restrictive Magic Leap licence [V] | PyTorch (CUDA/MPS/ROCm via torch) | Default with ALIKED or DISK; SuperPoint = plug-in | <https://github.com/cvg/LightGlue> [V] |
| ALIKED | Learned keypoints + descriptors | Permissive, BSD-3 [V] | PyTorch | Default | <https://github.com/Shiaoming/ALIKED> [V] |
| DISK | Learned keypoints (EPFL) | Permissive, Apache-2.0 [V repo `cvlab-epfl/disk`]; its weights' terms not read separately [U] | PyTorch | Default candidate | <https://github.com/cvlab-epfl/disk> [V] |
| RoMa | Dense matcher | Code MIT [V]; weights licence not read [U] | PyTorch | Default candidate (weights unchecked) | <https://github.com/Parskatt/RoMa> [V] |
| SuperPoint (Magic Leap) | Keypoints | Restrictive (not OSI) [V via LightGlue README] | PyTorch | Plug-in only | <https://github.com/magicleap/SuperPointPretrainedNetwork/blob/master/LICENSE> [U, not opened] |
| Kornia | Differentiable CV, LoFTR, DISK ports | Permissive, Apache-2.0 [V PyPI 0.9.2] | PyTorch | Optional | <https://pypi.org/project/kornia/> [V] |

## 4. Learned feed-forward reconstruction

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| MapAnything (Meta) | Metric multi-view reconstruction; optional intrinsics, poses, depth; to ~2,000 views on 140 GB | Code Apache-2.0 [V]; `map-anything-apache` weights Apache-2.0 [V]; `map-anything` weights CC-BY-NC [V] | PyTorch, CUDA | Default (Apache checkpoint, RC-P4); NC checkpoint = plug-in | <https://github.com/facebookresearch/map-anything> |
| VGGT (Meta/Oxford) | Feed-forward poses + depth, COLMAP export | Code relicensed commercial-friendly (excluding military) 2025-07-29 [V README]; `VGGT-1B` weights non-commercial; `VGGT-1B-Commercial` gated by application form [V]; code licence not captured separately in the landscape note [U]; "VGGT-Omega" (May 2026) unread [U] | PyTorch, CUDA | Plug-in (commercial checkpoint is gated) | <https://github.com/facebookresearch/vggt> [V] |
| Pi3 / Pi3X | Permutation-equivariant reconstruction; Pi3X takes optional pose/intrinsics/depth | Code BSD-3 [V]; weights CC-BY-NC 4.0 [V] | PyTorch | Plug-in (NC) | <https://github.com/yyfz/Pi3> |
| DUSt3R / MASt3R / MASt3R-SfM (Naver) | Pairwise pointmaps, matching | CC BY-NC-SA 4.0 [V] | PyTorch | Plug-in (NC) | <https://github.com/naver/mast3r> |

Feed-forward models run at low resolution (about 518 px for VGGT [U]); use them for initialisation,
pose priors, metric scale and sparse views, with COLMAP/GLOMAP bundle adjustment as the accuracy
engine. No head-to-head numbers were checked.

## 5. Dense reconstruction (MVS)

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| COLMAP PatchMatch stereo + fusion | Dense depth maps, fused point cloud, Poisson/Delaunay meshing | Permissive, BSD-3 [V] | CUDA or HIP build required for `patch_match_stereo`; the docs read describe no CPU or Metal dense path [V, absence only] | Default on GB10 (CUDA) and X3 (HIP) | <https://github.com/colmap/colmap/blob/main/doc/install.rst> [V] |
| OpenMVS | Dense point cloud, mesh, refine, texture | Copyleft, AGPL-3.0 [V] | CPU/CUDA [U] | Plug-in | <https://github.com/cdcseacave/openMVS> [V] |
| Metashape depth maps | Depth-map MVS | Proprietary | CUDA, OpenCL 1.2; Vulkan for texture blending; **Metal not mentioned** [V manual] | Reference | <https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf> |
| MapAnything / VGGT depth | Learned depth as dense prior | see section 4 | | Optional | |
| Own depth fusion (Metal, wgpu) | To fill the M4 Pro and iMac Pro gap | n/a | Metal/wgpu | Open question for RC-P2/P3 | n/a |

## 6. Meshing, mesh processing, texturing, UV, decimation

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| mvs-texturing | Texture a mesh from posed images (view selection, seam levelling) | Permissive, BSD-3 [V LICENSE.txt]; GitHub shows "NOASSERTION"; last push 2026-03-11 | CPU (C++) [U] | Default candidate | <https://github.com/nmoehrle/mvs-texturing> [V] |
| Open3D | Point clouds, meshes, Poisson, ICP, visualisation | Permissive, MIT [V LICENSE]; 0.20.0 wheels: macOS arm64, Linux x86_64 and aarch64, Windows; **no macOS x86_64** [V PyPI] | CPU; CUDA in some builds [U] | Default | <https://github.com/isl-org/Open3D> [V]; <https://pypi.org/project/open3d/> [V] |
| trimesh | Pure-Python mesh I/O and ops | Permissive, MIT [V]; 5.2.2 pure Python wheel [V PyPI] | CPU, any platform | Default | <https://github.com/mikedh/trimesh> [V] |
| PyMeshLab | MeshLab filters from Python | **Copyleft, GPL-3.0 [V]**; wheels for macOS arm64+x86_64, Linux x86_64+aarch64, Windows [V PyPI 2025.7.post1] | CPU | Plug-in only (not in default stack) | <https://github.com/cnr-isti-vclab/pymeshlab> [V] |
| meshoptimizer | Simplification, vertex cache, meshopt/quantisation compression for glTF | Permissive, MIT [V]; Python package name unknown [U] | CPU | Default (decimation, glTF compression) | <https://github.com/zeux/meshoptimizer> [V] |
| fast-simplification | Quadric decimation, Python | Permissive, MIT [V]; wheels incl. Linux aarch64, macOS arm64 and x86_64 [V PyPI 0.2.0] | CPU | Default | <https://github.com/pyvista/fast-simplification> [V] |
| xatlas | UV atlas generation | Permissive, MIT [V]; `xatlas` PyPI wheels macOS arm64+x86_64, Linux x86_64 [V]; Linux aarch64 not in the visible list [U] | CPU | Default | <https://github.com/jpcy/xatlas> [V] |
| Poisson / screened Poisson (Kazhdan) | Surface reconstruction | licence not checked [U] | CPU | Via COLMAP/Open3D | unverified |
| MeshLab | Desktop mesh tool | GPL-3.0 [U] | desktop | Reference | <https://github.com/cnr-isti-vclab/meshlab> |
| darktable | RAW development, CLI driven (RC-P7b) | GPL-3.0 [U] | macOS, Linux | Plug-in (compared in RC-P7b) | unverified |

## 7. Radiance fields and gaussian splatting (incl. underwater)

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| gsplat | Splat training library: pinhole and fisheye, 3DGUT, MCMC | Permissive, Apache-2.0 [V] | CUDA; no prebuilt aarch64 wheels, JIT build [V]; needed `TORCH_CUDA_ARCH_LIST=12.0` on GB10 [V blog] | Default (GB10, CUDA) | <https://github.com/nerfstudio-project/gsplat> |
| Brush | Splat training on wgpu | Permissive, Apache-2.0 [V]; README: macOS/Windows/Linux, AMD/Nvidia/Intel, Android, browser (Chrome 134+ for WebGPU) [V] | wgpu (Metal, Vulkan), no CUDA | Default (M4 Pro, X3, iMac Pro) | <https://github.com/ArthurBrussee/brush> |
| OpenSplat | Splat training, CPU/CUDA/Metal/HIP | **Copyleft, AGPL-3.0 [U]**; GitHub licence call returned "moved permanently" and was not followed | CUDA, Metal, HIP [U] | Plug-in | <https://github.com/pierotofy/OpenSplat> |
| 3DGS original (Inria) | Reference splat training | Non-commercial research licence [U] | CUDA | Not used | <https://github.com/graphdeco-inria/gaussian-splatting> |
| Instant-NGP | NeRF/hash grid | NVIDIA non-commercial [U]; GitHub reports NOASSERTION, file not read | CUDA | Not used | <https://github.com/NVlabs/instant-ngp> |
| 2DGS / PGSR | Surface-accurate splats | research code, licences unchecked [U] | CUDA | Reference (splat-to-mesh) | unverified |
| WaterSplatting | Underwater splats, nerfstudio 1.1.4, CUDA 11.8 | Permissive, Apache-2.0 [V] | CUDA | Plug-in candidate | <https://github.com/water-splatting/water-splatting> |
| SeaThru-NeRF | Underwater NeRF | Permissive, Apache-2.0 [V] | CUDA | Reference | <https://github.com/deborahLevy130/seathru_NeRF> |
| RUSplatting | Underwater splats | Research-only [V] | CUDA | Not used | unverified |
| SeaSplat | Underwater splats | unknown [U] | CUDA | Reference | unverified |
| KIRI 3DGS-to-mesh | Splat to mesh API | Proprietary [V] | cloud | Reference | see section 16 |

## 8. Masking and segmentation

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| SAM 2 | Promptable image/video segmentation | Permissive, Apache-2.0 for checkpoints, demo and training code [V README]; `sam2` PyPI 1.1.0 is sdist only [V] | PyTorch; CUDA expected, MPS/ROCm unverified [U] | Default | <https://github.com/facebookresearch/sam2> [V] |
| SAM 3 / SAM 3.1 | Concept (text) segmentation; **exists**, SAM 3.1 checkpoints released | **Custom, "SAM License", last updated 2025-11-19 [V]**: royalty-free grant to use, modify, distribute; terms include trade-control and military/ITAR end-use bans and a copy-of-agreement duty on redistribution; checkpoints gated on Hugging Face [V]; full text not read past section 3 [U] | README states CUDA 12.6+ GPU [V]; no CPU/Metal claim | Plug-in | <https://github.com/facebookresearch/sam3> [V] |
| rembg | Background removal CLI/lib | Permissive, MIT [V]; PyPI 2.0.87; extras `[gpu]` (onnxruntime-gpu) and `[rocm]` (onnxruntime-rocm) [V README]; **model weight licences (u2net, etc.) unread** [U] | ONNX Runtime: CPU, CUDA, ROCm; onnxruntime 1.32.0 wheels macOS arm64, Linux x86_64 and aarch64 (no macOS x86_64) [V PyPI] | Default (weights to check) | <https://github.com/danielgatis/rembg> [V] |
| ONNX Runtime | Inference runtime | Permissive, MIT [V PyPI] | see above | Default | <https://pypi.org/project/onnxruntime/> [V] |
| TagLab | AI-assisted segmentation and annotation (with SAM) | Copyleft, GPL-3.0 [V] | desktop | Reference (reef) | <https://github.com/cnr-isti-vclab/TagLab> |
| Metashape AI masks | Automatic masking (2.2) | Proprietary [U] | n/a | Reference | n/a |

## 9. Image decoding, RAW, metadata, video

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| rawpy | Python wrapper for LibRaw | Permissive, MIT [V]; 0.28.0 wheels: macOS arm64, Linux x86_64 and aarch64, Windows incl. arm64; **no macOS x86_64 wheel**, so the iMac Pro builds from sdist [V PyPI]; bundled LibRaw version unchecked [U] | CPU | Default | <https://github.com/letmaik/rawpy> [V]; <https://pypi.org/project/rawpy/> [V] |
| LibRaw | RAW decoder | **Dual-licensed: LGPL-2.1 or CDDL-1.0, user's choice [V COPYRIGHT]**; 0.22 lists D850 and Sony ILCE-1 [V]; compressed ARW support not stated [U] | CPU | Default | <https://github.com/LibRaw/LibRaw> [V]; <https://www.libraw.org/supported-cameras> [V] |
| pillow-heif | HEIC/HEIF for Pillow | Permissive, BSD-3 [V]; 1.8.1 wheels for macOS x86_64 and arm64, Linux x86_64 and aarch64, musl, Windows [V PyPI] | CPU | Default | <https://github.com/bigcat88/pillow_heif> [V] |
| libheif | HEIF codec library | **Copyleft, LGPL (library); samples MIT [V COPYING]**; version not stated | CPU | Default (dynamic link, via wheel) | <https://github.com/strukturag/libheif> [V] |
| ExifTool | Metadata read/write (Perl) | Artistic/GPL dual [U] | CLI, all | Default (external process) | <https://exiftool.org> [U] |
| PyExifTool | Python wrapper for ExifTool | PyPI metadata: "GPLv3+/BSD" [V PyPI 0.5.6] | CPU | Optional; check which half applies [U] | <https://pypi.org/project/pyexiftool/> [V] |
| PyAV | FFmpeg bindings | Permissive, BSD-3 [V]; 19.0.2 needs Python >=3.12; wheels macOS arm64 and x86_64, Linux x86_64 and aarch64 [V PyPI] | CPU; FFmpeg GPU codecs per build [U] | Default | <https://github.com/PyAV-Org/PyAV> [V] |
| FFmpeg | Video decode | LGPL/GPL depending on build [U] | all | Default (LGPL build) | <https://ffmpeg.org> [U] |
| gpmf-parser | GoPro GPMF telemetry: accel (~200 Hz), gyro, GPS, magnetometer, shutter, ISO, orientation quaternions, gravity; HERO5-HERO13, MAX | Permissive, Apache-2.0 [V]; Apache/MIT per note [V] | C, portable | Default | <https://github.com/gopro/gpmf-parser> |
| `gpmf` (PyPI) | Python GPMF | version 0.1, licence blank in metadata [V PyPI] | CPU | Not used (unvetted) | <https://pypi.org/project/gpmf/> |
| Pillow, numpy, OpenCV | Core imaging | Permissive [U] | all | Default | unverified |

No evidence was found that GPMF has been used as an SfM prior.

## 10. Colour and underwater correction

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| Sea-Thru (Akkaynak and Treibitz, CVPR 2019) | Physically based underwater colour recovery; needs per-pixel range | No official code [V] | n/a | Reference | n/a |
| Sea-Thru-Impl (Teragion) | Small reimplementation | GPL-3.0 and MIT, as the note reads [V] | Python | Reference only | <https://github.com/Teragion/Sea-Thru-Impl> |
| Own set-wide white balance, exposure, tone | Minimal pipeline on rawpy | n/a | CPU | Default (RC-P7b) | n/a |
| Refraction-aware camera models | Flat/dome port | see Refractive COLMAP, section 1 | | Differentiator | <https://isprs-archives.copernicus.org/articles/XLIII-B2-2020/977/2020/> [V] |

Colour correction after geometry (the reconstruction supplies Sea-thru's range), with an uncorrected
copy kept for features, is the agent's reasoning in the note, not sourced.

Not covered: backscatter, caustics, moving subjects, scale methods, swim patterns, image counts.

## 11. Capture-side apps and device APIs

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| Record3D app + `record3d` library | Streams RGB-D with LiDAR, camera poses, confidence maps over USB from iPhone | Library Copyleft, LGPL-2.1 [V]; app proprietary [U] | iOS app; Python lib; Linux needs `libusbmuxd` [V] | Plug-in (pose-bearing iPhone ingest) | <https://github.com/marek-simonik/record3d> [V] |
| Polycam raw data export | Images, camera intrinsics/extrinsics, depth maps | Proprietary app | **Only iOS devices with LiDAR, LiDAR or Room mode, Developer mode on, same device** [U, search snippet; page returned 403]; `polyform` converts to NeRF formats [U] | Plug-in (ingest) | <https://learn.poly.cam/hc/en-us/articles/38276871185044> [U] |
| Scaniverse (Niantic Spatial) | Splats: SPZ, PLY; meshes: GLB, USDZ; web, iOS, Android [V]. Also OBJ/FBX/STL per community info [U]. Pose export not mentioned [V, absence] | Proprietary app | iOS, Android, web | Plug-in (ingest of splats/meshes) | <https://nianticspatial.com/products/scaniverse> [V] |
| Apple Object Capture / `PhotogrammetrySession` | On-device photogrammetry; USDZ out | Proprietary (Apple SDK) | macOS 12+, iOS/iPadOS 17+ [V metadata]; needs a GPU with at least 4 GB RAM and **ray tracing support**; on iOS, select LiDAR devices [V article]; inputs include depth, gravity; Intel support and iMac Pro Vega eligibility unknown [U] | Reference; plug-in on M4 Pro | <https://developer.apple.com/documentation/realitykit/photogrammetrysession> [V]; <https://developer.apple.com/documentation/realitykit/creating-3d-objects-from-photographs> [V] |
| NeRFCapture, iPhone ProRAW, HEIC depth | Pose/depth capture | unverified [U] | iOS | Unverified | n/a |
| Open GoPro (BLE + HTTP/Wi-Fi API, Python SDK `open_gopro`, Kotlin SDK) | Control camera, settings, media, preview stream, capabilities per camera/firmware; demos in several languages | Python SDK MIT [V PyPI 0.22.0]; **repo itself has no licence statement: root LICENSE only refers to third-party licences, GitHub shows "Other"** [V]; Python <3.14 | Python 3.11-3.13 | Optional (capture control is a non-goal) | <https://github.com/gopro/OpenGoPro> [V]; <https://pypi.org/project/open-gopro/> [V] |
| DJI MSDK v5 | Drone app SDK; Mini 4 Pro supported only with RC-N2, not RC 2 | Proprietary [U] | Android/iOS | Not used (capture is a non-goal) | <https://dronedj.com/2025/03/21/dji-mini-4-pro-msdk/> [V] |
| Litchi, Maven, Drone Harmony | Mission planners named for Mini 4 Pro | Proprietary [V named only] | | Not used | |

DJI Mini 4 Pro EXIF/XMP fields are unverified.

## 12. Viewers and rendering (web and desktop)

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| three.js | WebGL/WebGPU 3D library | Permissive, MIT [V] | Browser | Default (viewer base) | <https://github.com/mrdoob/three.js> [V] |
| Spark (sparkjs.dev) | 3DGS renderer for three.js; mixes splats and meshes; WebGL2; reads PLY (also compressed), SPZ, SPLAT, KSPLAT, SOG | Permissive, MIT [V] | Browser, WebGL2 (README targets 98%+) | Default (splat view) | <https://github.com/sparkjsdev/spark> [V] |
| PlayCanvas SuperSplat | Splat editor/viewer | Permissive, MIT [V] | Browser | Optional (editing, clean-up) | <https://github.com/playcanvas/supersplat> [V] |
| splat-transform | CLI/lib: reads PLY, compressed PLY, SOG, streamed SOG, SPZ, SPLAT, KSPLAT, LCC; writes PLY, compressed PLY, SOG, streamed SOG, SPZ, GLB, CSV, HTML viewer, LOD, voxel, WebP | Permissive, MIT [V] | Node (npm); Docker backend with GPU/Vulkan setup documented [V] | Default (conversion) | <https://github.com/playcanvas/splat-transform> [V] |
| PlayCanvas engine | Engine reading PLY, SOG, SPZ, splat-GLB | licence not read [U] | Browser | Reference | per landscape note [V] |
| Babylon.js | Web 3D engine | Permissive, Apache-2.0 [V] | Browser | Optional | <https://github.com/BabylonJS/Babylon.js> [V] |
| potree | Web viewer for large point clouds | Permissive, BSD-style (2-clause text, copyright Markus Schuetz) [V]; GitHub shows NOASSERTION; last push 2026-11-20 | Browser | Optional | <https://github.com/potree/potree> [V] |
| Rerun | Multimodal logging and viewer; Python, Rust, C++ SDKs; `pip install rerun-sdk` bundles viewer | Permissive, MIT or Apache-2.0 [V README]; 0.43.2 wheels: macOS arm64, Linux x86_64 and aarch64, Windows; **no macOS x86_64** [V PyPI] | Rust viewer (wgpu) | Default (dev/debug viewer) | <https://github.com/rerun-io/rerun> [V] |
| Viscore | Large SfM model viewing, 100 Island Challenge | unknown [U] | desktop | Reference (reef) | <https://chei.ucsd.edu/?p=2805> [V named] |
| Cesium / CesiumJS | 3D Tiles viewer | Apache-2.0 [U] | Browser | Optional | unverified |

## 13. Formats

| Format | What it is | Licence / spec status | Used by | Role | Source |
|---|---|---|---|---|---|
| glTF 2.0 / GLB | Web and engine mesh interchange | Khronos open standard | all viewers, engines | Default (mesh) | <https://www.khronos.org/gltf/> [U] |
| `KHR_gaussian_splatting` | Splats in glTF | **Status line reads "Complete, Ratified by the Khronos Group"**, spec CC-BY-4.0 [V]; the landscape note had "release candidate 2026-02-04" | Cesium, Niantic, Esri, Nvidia, Autodesk contributors listed [V] | Default (splat interchange, target) | <https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md> [V]; <https://digitalproduction.com/2026/02/04/gltf-learns-to-splat-without-losing-the-plot/> [V] |
| `KHR_gaussian_splatting_compression_spz` | SPZ compression in glTF | RC at 2026-02-04 [V note]; the directory name checked on main was not found (`..._spz_2` 404) [U] | | Optional | as above |
| SPZ | Niantic compressed splat format (~90% smaller than PLY) | Permissive, MIT [V repo] | Scaniverse, Spark, splat-transform | Default (delivery) | <https://github.com/nianticlabs/spz> [V] |
| SOG | PlayCanvas compressed splat (`meta.json` + WebP textures) | PlayCanvas docs; spec licence not read [U] | PlayCanvas, Spark, splat-transform | Default (web delivery) | <https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/> [V named] |
| PLY (3DGS) | Uncompressed splat/point cloud interchange | de-facto | everything | Default (source) | <https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/ply/> [V named] |
| OBJ | Mesh interchange | de-facto | everything | Default (interchange) | n/a |
| USD / USDZ | Apple/AR and robotics sim scene format | `usd-core` 26.11 on PyPI, licence "TOST-1.0" (Tomorrow Open Source Technology License) [V PyPI]; wheels macOS universal2, Linux x86_64 and aarch64, Windows; Python 3.11-3.14 [V] | Apple Quick Look, Object Capture, Scaniverse export, Omniverse | Default (Apple output) | <https://pypi.org/project/usd-core/> [V] |
| COLMAP text/binary (`cameras`, `images`, `points3D`) | The SfM exchange format | BSD-3 project [V] | nearly every tool | Default (hub) | <https://github.com/colmap/colmap> |
| nerfstudio `transforms.json` | Poses + intrinsics JSON | Apache-2.0 project [U] | Brush, gsplat, nerfstudio | Default (splat input) | <https://github.com/nerfstudio-project/nerfstudio> [U] |
| 3D Tiles | Streaming tiled geometry; LOD splats added Apr 2026 [V note] | OGC standard [U]; `3d-tiles-tools` Apache-2.0 [V] | Cesium | Optional | <https://github.com/CesiumGS/3d-tiles-tools> [V] |
| E57 / LAS / LAZ | Point cloud exchange | ASTM / ASPRS [U] | Polycam exports LAS/LAZ/PLY/PTS/XYZ [U] | Only if survey input arrives | n/a |
| MCAP, rrd | Rerun/robot logs | n/a | Rerun ingests MCAP, rrd, LeRobot [V] | Optional | <https://github.com/rerun-io/rerun> |
| `provenance.json`, world frame | Project's own contract | n/a (see RC-P5) | | Default | n/a |

## 14. Game engines and DCC import paths

| Tool | Import path | Licence | Platforms | Role | Source |
|---|---|---|---|---|---|
| Unity glTFast | glTF/GLB import and export package | Permissive, Apache-2.0 [V] | Unity | Default (Unity path) | <https://github.com/atteneder/glTFast> [V] |
| Unreal Engine | glTF and GLB import through the Interchange framework; Import Into Level works with glTF and MaterialX [U, search snippet]. The Epic page read lists KHR_lights_punctual, KHR_materials_unlit, KHR_materials_clearcoat, KHR_materials_variants, KHR_mesh_quantization, KHR_texture_transform, and does **not** mention KHR_draco or KHR_gaussian_splatting [V, page is the export-support page] | Proprietary engine | Windows, Mac, Linux | Default (mesh path) | <https://dev.epicgames.com/documentation/en-us/unreal-engine/gltf-file-format-support-in-unreal-engine> [V] |
| Godot | Native glTF 2.0 import | Permissive, MIT [V repo]; native glTF support [U] | all | Default | <https://github.com/godotengine/godot> |
| Blender | Native glTF importer/exporter (Khronos glTF-Blender-IO, Apache-2.0 [V]) | GPL (Blender itself) [U] | all | Default (inspection) | <https://github.com/KhronosGroup/glTF-Blender-IO> [V] |
| Apple Quick Look / RealityKit | USDZ | Proprietary | iOS, macOS | Default (AR path) | see section 11 |
| Omniverse gsplat converter | splat to USD | unknown [U] | | Reference | <https://docs.omniverse.nvidia.com/extensions/latest/ext_gsplat-converter/manual.html> [U] |

Splat-in-engine paths (KHR_gaussian_splatting in Unity, Unreal, Godot) are unverified.

## 15. Agent and integration

| Tool | What it does | Licence | Platforms | Role | Source |
|---|---|---|---|---|---|
| MCP Python SDK (`modelcontextprotocol/python-sdk`) | Build MCP servers and clients | Permissive, MIT [V]; PyPI `mcp` 2.3.0, Python >=3.10, pure wheel [V] | any | Default (agent surface, RC-P6) | <https://github.com/modelcontextprotocol/python-sdk> [V]; <https://pypi.org/project/mcp/> [V] |
| `metashape-mcp` | MCP server over the Metashape Python API; 106 tools reported | Author and licence unverified [U] | needs licensed Metashape Professional | Reference | PyPI (name only) |
| SceneAgent | Paper, arXiv 2610.34745 | unread [U] | | Reference | unverified |
| NodeODM REST | Task API | AGPL project [V, partly] | | Reference | <https://github.com/WebODM/WebODM> |

Two searches found no MCP server for COLMAP or splat training; that is a fact about two searches,
not proof of a gap.

## 16. Commercial products

Prices only where the notes hold them.

| Product | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| Agisoft Metashape | Industry reference; Standard $179, Professional $3,499, perpetual node-locked; Professional adds Python, network/cloud processing, 4D, DEM, orthomosaic [V]. 2.3.x; **no gaussian splats** [V]; network processing is task-level (server, workers on shared storage, clients) [V]; frame, fisheye, spherical, cylindrical, RPC cameras [V]; iPhone TrueDepth loads with depth, rear LiDAR not mentioned [V] | Proprietary | CUDA, OpenCL 1.2, Vulkan (texture); Metal not mentioned [V] | Reference | <https://www.agisoft.com/buy/online-store/> [V]; <https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf> [V] |
| RealityScan (Epic, ex-RealityCapture) | Free under $1M revenue, $1,250/seat/year above [V via news]; 2.1 (Nov 2025) CLI `importColmap` + Remote Command plugin (REST/gRPC); 2.2 (Jun 2026) AMD GPUs | Proprietary | Windows-only [U] | Reference | news only |
| Pix4Dmatic / PIX4Dcatch / PIX4Dcloud | Large-scale survey, CAD vectors, mobile capture | Proprietary | | Reference | <https://www.pix4d.com/product/pix4dmatic/> [V] |
| 3DF Zephyr | Free (50 photos), Lite 199 EUR, Pro 4,200 EUR or 250 EUR/month; photogrammetry + laser scans, GIS/CAD | Proprietary | | Reference | <https://www.3dflow.net/3df-zephyr-photogrammetry-software/> [V] |
| DJI Terra | Photogrammetry, 3DGS, multispectral, LiDAR, cluster reconstruction; trial capped at 500 photos | Proprietary | DJI-tied | Reference | <https://enterprise.dji.com/dji-terra> [V] |
| iTwin Capture (Bentley) | Features not verified | Proprietary | | Reference | unverified [U] |
| Polycam | Phone/cloud scanning; API mentioned; exports OBJ, GLB, FBX, DAE, STL, USDZ meshes and DXF, PLY, LAZ, XYZ, PTS points; free tier GLTF only [U, search snippet] | Proprietary | iOS, web | Reference | <https://learn.poly.cam/hc/en-us/articles/27756102599572> [U] |
| KIRI Engine | Pay-per-credit API incl. 3DGS-to-mesh [V] | Proprietary | cloud | Reference | <https://www.kiriengine.app/features/export-formats> [U] |
| Luma | $1/capture API, possibly stale [U] | Proprietary | cloud | Reference | unverified |
| Scaniverse | see section 11 | Proprietary | | Reference | |
| Apple Object Capture | see section 11 | Proprietary | | Reference | |

## 17. Frameworks and runtimes

| Tool | What it does | Licence | Platforms / GPU | Role | Source |
|---|---|---|---|---|---|
| PyTorch | Tensor/NN runtime | Permissive, BSD-style with bundled Apache/MIT parts [V PyPI 2.15.0 expression]; repo LICENSE read | **PyPI 2.15.0: macOS arm64 (14.0), Linux x86_64 and aarch64, Windows; no macOS x86_64 wheel [V]**. CUDA index `cu132` has 2.15.0 for Linux aarch64 and x86_64 [V]; `cu130` lists 2.9.1 aarch64 [V]. ROCm index: `rocm7.2` up to 2.14.1, `rocm7.1` up to 2.13.0, Linux x86_64 [V]. Whether gfx1151 (X3) is supported by those wheels: unknown [U]. MPS on M4 Pro [U] | Default | <https://pypi.org/project/torch/> [V]; <https://download.pytorch.org/whl/rocm7.2/torch/> [V] |
| Hugging Face Transformers | Hosts LightGlue | Apache-2.0 [U] | | Optional | <https://huggingface.co/docs/transformers/main/en/model_doc/lightglue> [V named] |
| Burn / wgpu | Rust ML and GPU layers under Brush | permissive [U] | Metal, Vulkan | Via Brush | <https://github.com/tracel-ai/burn> [U] |

## 18. Platform matrix

Expectation table, not measurement. Prototype RC-P2 confirms or replaces every cell with a command
and its output. "Native GPU" = a vendor GPU path exists for that machine; "CPU only" = runs, no GPU
path; "build needed" = no wheel or binary for that architecture, a source build is required.

| Component | M4 Pro (Metal) | GB10 (ARM64 + CUDA 13) | X3 (x86_64, ROCm/Vulkan) | iMac Pro (x86_64 macOS, CPU) |
|---|---|---|---|---|
| COLMAP SfM (SIFT, mapper) | CPU only; GPU SIFT unknown [U] | native GPU (build needed on aarch64; apt build fell back to CPU SIFT) [V blog] | native GPU via HIP build, RDNA3.5 may need `HSA_OVERRIDE_GFX_VERSION` [V install.rst]; gfx1151 unknown [U] | CPU only [U] |
| COLMAP dense (patch_match) | no (no Metal/CPU path in docs read) [V absence] | native GPU (CUDA) [U] | native GPU (HIP build) [V install.rst] | no [U] |
| pycolmap | wheel (arm64) [V] | build needed (no aarch64 wheel) [V] | wheel (x86_64; CUDA wheel is CUDA-only) [V] | build needed (no macOS x86_64 wheel) [V] |
| GLOMAP | CPU [U] | CPU [U] | CPU [U] | CPU [U] |
| PyTorch | wheel, MPS [U] | wheel, CUDA (cu130/cu132 aarch64) [V] | wheel, ROCm index (gfx1151 unknown) [V/U] | build needed (no wheel on latest; old versions [U]) [V] |
| hloc + LightGlue + ALIKED | MPS/CPU [U] | native GPU [U] | native GPU (ROCm) [U] | CPU [U] |
| MapAnything (Apache ckpt) | MPS or CPU [U] | native GPU [U] | ROCm unknown [U] | CPU, slow [U] |
| gsplat | no (CUDA JIT) [V] | build/JIT needed (no aarch64 wheels) [V] | no (CUDA) [U] | no [U] |
| Brush (wgpu) | native GPU (Metal) [V README] | Vulkan [U] | Vulkan [V README: AMD] | Metal on Vega [U] |
| SAM 2 | MPS/CPU [U] | native GPU [U] | ROCm unknown [U] | CPU [U] |
| rembg (ONNX) | CPU (CoreML unverified) [V wheels] | CPU/CUDA [V extras] | CPU/ROCm [V extras] | CPU, wheels arm64-only: build/sdist [V] |
| rawpy / LibRaw | wheel [V] | wheel (aarch64) [V] | wheel [V] | sdist build (no x86_64 mac wheel) [V] |
| pillow-heif | wheel [V] | wheel [V] | wheel [V] | wheel [V] |
| PyAV | wheel [V] | wheel [V] | wheel [V] | wheel [V] |
| Open3D | wheel [V] | wheel [V] | wheel [V] | build needed (no x86_64 mac wheel) [V] |
| trimesh, xatlas, fast-simplification | wheel [V] | wheel (xatlas aarch64 unknown) [V/U] | wheel [V] | wheel [V] |
| Rerun SDK | wheel [V] | wheel [V] | wheel [V] | build needed (no x86_64 mac wheel) [V] |
| usd-core | wheel [V] | wheel [V] | wheel [V] | wheel (universal2) [V] |
| MCP SDK | pure Python [V] | pure Python [V] | pure Python [V] | pure Python [V] |
| Apple Object Capture | native GPU [V metadata; hardware fit M4 Pro [U]] | no | no | unknown (needs ray-tracing GPU) [V/U] |

## 19. Licence traps

1. **VGGT, Pi3, DUSt3R/MASt3R, original MapAnything weights are non-commercial.** Only
   `map-anything-apache` (Apache-2.0) and the form-gated `VGGT-1B-Commercial` are commercial-safe.
   Code under a permissive licence does not license its weights.
2. **SuperPoint is restrictive and so is its inference file** in LightGlue (`lightglue/superpoint.py`).
   LightGlue's README states its own code and weights are Apache-2.0; the research note's claim that
   SuperPoint-trained LightGlue weights inherit the restriction is not what the README says. Decide
   with a lawyer's eye, or avoid by default: ALIKED/DISK + LightGlue.
3. **AGPL: OpenMVS, OpenSplat [U], WebODM.** A hosted service must offer source. Plug-ins only, run
   as separate processes.
4. **GPL: PyMeshLab (GPL-3.0), TagLab, Sea-Thru-Impl, MeshLab, darktable [U].** Do not link into the
   engine. PyExifTool is listed "GPLv3+/BSD" on PyPI: check which applies, or call `exiftool` directly.
5. **LGPL: LibRaw (also CDDL option), libheif, `record3d`.** Wheels bundle the libraries; dynamic
   linking and shipping notices apply. LibRaw's CDDL option is the way out of LGPL.
6. **SAM 3 is a custom licence**, not Apache. Grant is broad but carries trade-control and military
   end-use terms and a duty to ship the agreement; checkpoints are gated. SAM 2 is Apache-2.0.
7. **Open GoPro repo has no licence statement**; only the Python SDK is MIT. Treat the spec text and
   demos as unlicensed until clarified.
8. **COLMAP "BSD-3" excludes dependencies**: a CUDA, FreeImage or similar build may carry other terms.
9. **Instant-NGP and Inria 3DGS** are non-commercial [U]; RUSplatting is research-only.
10. **rembg model weights** (u2net, etc.) have their own licences, unread.
11. **Proprietary SDKs** (DJI MSDK, Record3D app, Polycam, Apple Object Capture) are interop targets,
    never dependencies.

## 20. Not verified

- Licences read only from search snippets or memory: OpenSplat, Ceres, ExifTool, FFmpeg, darktable,
  MeshLab, Cesium, PlayCanvas engine, SOG spec, nerfstudio, Transformers, Burn, Instant-NGP, Inria 3DGS,
  2DGS/PGSR, SeaSplat, Viscore, Omniverse converter.
- AliceVision/Meshroom LICENSE files (GitHub reports NOASSERTION); the "MPL-2.0" is from the notes.
- RoMa, DISK, rembg, MapAnything and Pi3 weights' terms beyond what is stated above; VGGT-Omega and
  `KHR_gaussian_splatting_compression_spz` ratification state.
- SAM 3 licence past section 3; SAM 2 and SAM 3 on MPS and ROCm.
- Whether PyTorch ROCm wheels support gfx1151 (X3), and whether CUDA 13 wheels cover compute capability
  12.1 without `TORCH_CUDA_ARCH_LIST`.
- Last PyTorch version with a macOS x86_64 wheel (believed 2.2.x).
- A CPU or Metal path for dense MVS; Open3D CUDA build availability; xatlas Linux aarch64 wheel;
  meshoptimizer's Python package; bundled LibRaw version in rawpy; compressed ARW on the A1.
- Apple Object Capture on Intel and on the iMac Pro's Vega GPU; ProRAW, HEIC depth, NeRFCapture;
  Polycam raw-data page content (403) and format details; Scaniverse pose export; Unreal's glTF import
  path (Interchange) beyond a search snippet; Godot glTF behaviour; splat-in-engine support.
- Pix4D, iTwin Capture, RealityScan features; Luma pricing; `metashape-mcp` provenance; DJI Mini 4
  Pro EXIF/XMP; GoPro lens modes; reef groups' software; backscatter, caustics, scale research;
  Metashape education prices, 2.3 release date, forum sentiment.
- Every platform-matrix cell marked `[U]`, and every `[V]` cell is a wheel listing, not an install.
