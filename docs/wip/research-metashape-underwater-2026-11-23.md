# Research: Metashape, other tools, underwater, cameras (2026-11-23)

Second research pass, by a research agent on 2026-11-23. `[V]` = read on a primary page that day
(URL given). `[U]` = memory, search snippet or not confirmed. The Metashape manual cited is the 2.3
Professional PDF (<https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf>).

## Agisoft Metashape — the industry reference

- **Editions:** Standard $179, Professional $3,499, both perpetual node-locked [V
  <https://www.agisoft.com/buy/online-store/>]. Professional adds Python scripting, network and
  cloud processing, 4D, DEM and orthomosaic [V compare page + manual]. Version 2.3.x [V]; release
  date unclear [U].
- **Workflow [V manual]:**
  - Align photos: accuracy Highest (4× upscale) … Lowest (1/16 px); preselection Generic /
    Reference / Estimated / Sequential; tie point limit (10,000 recommended); guided matching;
    adaptive camera model fitting; *exclude stationary tie points* (turntable without masks);
    masks applied to key or tie points.
  - Clean tie points by reprojection error, reconstruction uncertainty, image count, projection
    accuracy; Optimize Cameras re-runs bundle adjustment.
  - Depth maps (quality Ultra High down; filtering Mild / Moderate / Aggressive / Disabled) →
    point cloud → mesh (face count, interpolation) → texture (diffuse, occlusion, normal; Mosaic /
    Average / NaturalBlending in 2.3).
  - DEM and orthomosaic (geographic, planar, cylindrical projections; seamline editing; GeoTIFF).
  - Camera models: frame, fisheye, spherical, cylindrical, RPC; 2.3 adds equidistant and
    equisolid fisheye. The manual advises avoiding fisheye and ultra-wide lenses.
  - iPhone/iPad TrueDepth images load with depth; rear LiDAR not mentioned.
  - 2.2: COLMAP export, AI masks, AprilTag [U]. 2.3: NaturalBlending, texture editing, automatic
    colour enhancement, LiDAR and GNSS bias tools [V]. **No gaussian splats** in 2.3 notes [V].
- **Network processing [V manual]:** a server holding the task queue (does no processing, not
  fault tolerant), workers computing onto shared storage at the same absolute path, clients plus a
  Network Monitor. Work is split per task (batch step); 2.3 adds concurrent independent tasks.
  Task-level parallelism, not one alignment spread across nodes (finer splitting unverified).
- **GPU [V manual]:** CUDA and OpenCL 1.2; Vulkan for texture blending. **Metal not mentioned.**
- **Sentiment [U, aggregator snippets]:** praised for accuracy, maturity, Python API; criticised
  for Professional's price, node-locking, slowness on large jobs.

## Other tools, one line each

- **3DF Zephyr** — free tier (50 photos), Lite €199, Pro €4,200 or €250/month; photogrammetry plus
  laser scans with GIS/CAD tools [V <https://www.3dflow.net/3df-zephyr-photogrammetry-software/>].
- **Pix4Dmatic** — large-scale, survey and CAD vectors, linked to PIX4Dcatch mobile capture and
  PIX4Dcloud [V <https://www.pix4d.com/product/pix4dmatic/>].
- **DJI Terra** — photogrammetry, 3D gaussian splatting, multispectral, LiDAR, cluster
  reconstruction; DJI-tied; trial capped at 500 photos [V <https://enterprise.dji.com/dji-terra>].
- **Meshroom** — MPL-2.0 node graph with caching, local or render farm, plugins for depth and
  splatting [V <https://github.com/alicevision/Meshroom>].
- **RealityScan**, **iTwin Capture** — features not verified [U].

## Underwater

- **Refraction:** flat ports cause depth-dependent systematic error; dome ports mostly remove it
  only when the lens entrance pupil sits at the dome centre. Brown models absorb refraction only
  implicitly; radial weighting improved flat-port accuracy up to 50% [V
  <https://isprs-archives.copernicus.org/articles/XLIII-B2-2020/977/2020/>]. Commercial tools
  reportedly have no explicit refraction model [U].
- **Refractive COLMAP** (IROS 2024) supports flat and dome ports; open source; licence not stated
  [V <https://arxiv.org/abs/2403.08640>].
- **Colour:** Sea-thru (Akkaynak & Treibitz, CVPR 2019) needs per-pixel range; no official code.
  Teragion/Sea-Thru-Impl is GPL-3.0/MIT, small [V <https://github.com/Teragion/Sea-Thru-Impl>].
  A reconstruction supplies the range Sea-thru needs — so colour correction after geometry, with an
  uncorrected copy kept for features, is a natural fit (agent's reasoning, unsourced).
- **Splats/NeRF underwater:** WaterSplatting Apache-2.0 (nerfstudio 1.1.4, CUDA 11.8) [V
  <https://github.com/water-splatting/water-splatting>]; SeaThru-NeRF Apache-2.0 [V
  <https://github.com/deborahLevy130/seathru_NeRF>]; RUSplatting research-only [V]; SeaSplat
  licence unknown [U].
- **Reef monitoring:** 100 Island Challenge uses Viscore for viewing large SfM models [V
  <https://chei.ucsd.edu/?p=2805>]. TagLab is GPL-3.0 AI-assisted segmentation and annotation with
  SAM [V <https://github.com/cnr-isti-vclab/TagLab>]. Which reconstruction software reef groups use
  was **not** established.
- **Not covered:** backscatter, caustics, moving subjects, scale methods (bars, lasers, stereo),
  swim patterns and image counts.

## Cameras

- **RAW:** LibRaw 0.22 lists the D850 and the Sony ILCE-1 (A1) [V
  <https://www.libraw.org/supported-cameras>]; compressed ARW not stated. rawpy is MIT with LGPL
  LibRaw [V <https://github.com/letmaik/rawpy>]; its bundled LibRaw version unchecked.
- **GoPro GPMF:** accelerometer (~200 Hz), gyro, GPS, magnetometer, shutter, ISO, orientation
  quaternions, gravity; HERO5–HERO13 and MAX; parser Apache-2.0/MIT [V
  <https://github.com/gopro/gpmf-parser>]. No evidence found of GPMF used as an SfM prior.
- **iPhone:** Record3D streams RGB-D with LiDAR, camera poses and confidence maps over USB; library
  LGPL-2.1 [V <https://github.com/marek-simonik/record3d>]. ProRAW, HEIC depth, Polycam /
  Scaniverse / NeRFCapture exports not verified.
- **DJI Mini 4 Pro:** MSDK v5 supports it only with the RC-N2 controller, not the RC 2 [V
  <https://dronedj.com/2025/03/21/dji-mini-4-pro-msdk/>]; Litchi, Maven, Drone Harmony named.
  EXIF/XMP fields unverified.

## Feature set (agent's synthesis — design judgement, not sourced)

**Table stakes:** JPEG + NEF/ARW ingest; EXIF focal, GPS and gimbal priors; COLMAP-class SfM with
preselection; dense mesh + point cloud + texture, exported PLY/OBJ/glTF; scale (markers or scale
bars) and coordinate transform; masks incl. automatic background; a distributed job queue with
per-task status; HTTP API and MCP over the same job model.

**Differentiators:** refraction-aware camera option (flat/dome port); depth-aware colour correction
after reconstruction; gaussian splats from the same poses (Metashape 2.3 has none); GoPro GPMF and
ARKit/Record3D priors; per-machine backends incl. Apple silicon (Metashape documents no Metal);
drone missions later (Mini 4 Pro needs the RC-N2).

## Not verified

Metashape education prices, full edition table, marker/target and chunk details, 2.3 release date,
real forum sentiment; RealityScan and iTwin features; reef groups' software, NOAA workflow, Sandin
Lab SOP, CoralNet; backscatter/caustics/scale research; GoPro lens modes; iPhone ProRAW and capture
app exports; Mini 4 Pro XMP; Refractive COLMAP and SeaSplat licences; A1 compressed ARW in rawpy.
