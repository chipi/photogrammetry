# Product feature analysis: what a complete photogrammetry product offers

Date: 2026-11-23. Scope: features, workflows and user experience. Libraries, licences and platforms of
the building blocks live in `tools-overview.md` and are not repeated here. Inputs:
[brief](../concept/RC-brief.md), [Metashape and underwater research](../wip/research-metashape-underwater-2026-11-23.md),
[landscape research](../wip/research-landscape-2026-11-23.md).

## Conventions

- `[V]` = read on a primary page on 2026-11-23, URL in the tag or in the source key below. `[U]` = memory,
  search snippet, an aggregator, or a page the fetch tool summarised without showing its text. `unknown` = not found.
- Source keys. **MAN** = <https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf> (Metashape Professional 2.3 manual, PDF downloaded and searched as text).
  **API** = <https://www.agisoft.com/pdf/metashape_python_api_2_3_0.pdf> (Python reference 2.3.0, dated 2025-12-31).
  **PYPI** = <https://pypi.org/pypi/metashape-mcp/json>. **GH** = <https://github.com/jenkinsm13/metashape-mcp> (raw files and the GitHub API).
- Sections 6 and the "why" lines in sections 4 and 5 are judgement, labelled as such. Everything else is reporting.
- Web fetches of two Polycam pages, Sketchfab help and the AIMS reef SOP failed (403, 404, timeout). Claims from those sources are `[U]` or absent.

---

## 1. Agisoft Metashape Professional 2.3, feature by feature

Metashape is a desktop application, perpetual node-locked licences (Standard $179, Professional $3,499 per the earlier research note, store page not re-read today). Python scripting, network processing, 4D, DEM and orthomosaic are Professional-only [V API overview; MAN].

### 1.1 Project and chunk management

- A project holds chunks; a chunk holds one set of cameras, tie points, depth maps, point cloud, model, tiled model, DEM, orthomosaic and shapes [V MAN ch. 7 "Using chunks"].
- Chunks align to each other (`alignChunks`, methods by points, markers or cameras, with `fit_scale`) and merge (`Merge Chunks`) [V API `alignChunks`; MAN batch list].
- Batch Process runs an ordered job list over chunks. Job types include Align, Detect Markers, Generate Masks, Filter Point Cloud, Smooth/Decimate/Refine Model, Remove Lighting, Reset Region, Run Script, Save/Load Project, Export Texture, Export Tiled Model, Generate Report [V MAN "Batch process" list].
- Preferences expose GPU selection and "fine-level task subdivision", which splits some tasks into sub-jobs to cut memory use on large sets [V MAN ch. 3 and App. C].
- Reduce Overlap marks redundant images in an over-captured set [V MAN ch. 2 "Excessive image elimination"].

### 1.2 Import

- Image formats: JPEG, JPEG 2000, JPEG XL, TIFF, DNG, PNG, OpenEXR, BMP, TGA, PGM/PPM, Norpix SEQ, AscTec ARA, MPO [V MAN "Loading source data"]. NEF and ARW are absent from the list; the manual says other formats must be converted first. It recommends lossless RAW-to-TIFF over JPEG [V MAN ch. 2].
- Video: Import Video extracts frames at a step or rate, with start and end times; it is frame extraction, not a video-native pipeline [V MAN; API `importVideo(frame_step, time_start, ...)`].
- Depth: Import Depth Images reads Dynamic Depth JPEG. The manual names iPhone and iPad TrueDepth (front camera) as the source; images with depth from other cameras load without depth. Rear LiDAR is not mentioned [V MAN].
- Laser scans: structured terrestrial and unstructured aerial scans align with photos (`align_laser_scans`, `match_laser_scans`) [V MAN overview; API `matchPhotos`, `alignCameras`].
- Satellite RPC, multispectral, thermal and multi-camera rigs are supported [V MAN overview, ch. 3].
- Trajectory, camera flight log, GCP, camera calibration and reference files import in many layouts [V MAN App. B].

### 1.3 Camera calibration and lens models

- Models: frame, fisheye, spherical (equirectangular), cylindrical, RPC [V MAN App. D; ch. 3]. 2.3 adds equidistant and equisolid fisheye variants [U, from the earlier research note].
- Per-sensor calibration is estimated in alignment and refined in Optimize Cameras (focal, principal point, skew, K1-K4, P1-P2, B1-B2; `optimizeCameras(fit_f, fit_cx, fit_k1, fit_b1, ...)`) [V API].
- Adaptive camera model fitting turns on distortion terms progressively (`adaptive_fitting`) [V API `alignCameras`].
- Rolling-shutter compensation is a calibration option, with a visualisation of the effect per camera [V MAN ch. 4].
- Lens calibration from a printed chessboard pattern, and a calibration import/export, exist [V MAN ch. 2 and 4 headings].
- No water, port or refraction model appears in the manual's camera models [V MAN App. D; absence in a text search is a fact about the search, not proof].

### 1.4 Alignment

`matchPhotos` and `alignCameras` [V API]:

- Downscale (accuracy Highest = 4x upscale down to Lowest), key point limit (default 40,000), tie point limit (default 4,000; the manual recommends 10,000 elsewhere, earlier note), per-megapixel key point limit.
- Pair preselection: generic (low-resolution matching), reference (from GNSS or camera positions), estimated and sequential [V MAN ch. 3].
- Filter by mask; mask applies to key points or tie points; `filter_stationary_points` drops static features (turntable without masks); `guided_matching`; `keep_keypoints`; `reset_matches`.
- `match_depth_maps` matches against imported depth; `match_laser_scans` includes scans.
- `alignCamerasByReference` aligns from reference positions without matching (added 2.2.1) [V API change log].
- Task splitting (`subdivide_task`, work item sizes for cameras and pairs) is exposed in the API [V API].

### 1.5 Tie point cleanup

- Gradual selection by criteria: reprojection error, reconstruction uncertainty, image count, projection accuracy; `cleanTiePoints` and `cleanModel` exist since 2.2.1 [V API change log; MAN ch. 4].
- Optimize Cameras re-runs bundle adjustment after removal [V MAN].
- Reference pane reports per-camera, per-marker and per-scale-bar errors, with tie point accuracy as a weighting parameter [V MAN ch. 4 "What do the errors mean"].

### 1.6 Markers, GCPs, scale bars, coded targets

- Coded targets: circular (12 to 20 bit) and AprilTag families 16h5, 25h9, 36h10, 36h11, Circle 21h7, Standard 41h12, Standard 52h13. Detect Markers is a batch job; targets can be generated and printed by the program. The manual notes coded targets need many pixels per target and fit close range, not aerial work [V MAN ch. 4 "Coded targets"].
- Scale bars take a known distance between two markers, with accuracy; the report lists estimated distance and error [V MAN].
- Check points and control points are labelled in the Reference pane; accuracy per marker is set [V MAN].
- Fiducial detection exists (`detectFiducials`) [V API].

### 1.7 Coordinate systems

- Local, projected and geographic systems, EPSG lookup, custom definitions, geoid models (`Geoid` class), reference import with rotation and accuracy columns, GNSS antenna offsets and bias [V MAN ch. 4; API change log 2.2.2 and class `Antenna`].
- Chunk region (bounding box) and transform are scriptable [V API].
- LiDAR and GNSS bias tools are listed in 2.3 [U, earlier note].

### 1.8 Masks

- Sources: image alpha, file, background image, from reconstructed model, and automatic AI (`MaskingModeAI`, added 2.2) [V MAN ch. 6 "Using masks"; API change log].
- Masks apply to alignment key points or tie points, depth maps and texture [V MAN].

### 1.9 Depth maps

- `buildDepthMaps(downscale=4, filter_mode, reuse_depth, ...)`; quality Ultra High down to Lowest; filtering Mild, Moderate, Aggressive, Disabled [V API; MAN ch. 3].
- Depth maps drive point cloud, model, DEM and tiled model reconstruction; GPU accelerated [V MAN GPU section].

### 1.10 Point clouds

- `buildPointCloud(source_data=DepthMapsData, point_colors, point_confidence, ...)`; point confidence and normals; colourise from images [V API].
- Editing: selection tools, Filter Point Cloud by confidence, smooth, compact, calculate normals [V MAN ch. 6; API].
- Classification: ground points (`classifyGroundPoints`), general `classifyPoints` with a trained model, overlap point classification (2.2) [V API].
- Import and export LAS, LAZ, PLY, E57, PTS and others [V MAN App. B].

### 1.11 Mesh

- `buildModel(source_data, surface_type=Arbitrary | HeightField, interpolation, face_count, ...)` from depth maps, point cloud, tie points, or laser scans [V API].
- Decimate, smooth, close holes (by size), remove components, clean model by criteria, refine model (photoconsistent refinement on GPU, `refineModel(downscale, iterations, smoothness)`) [V API; MAN ch. 6 "Editing model geometry"].
- Manual editing: select by tools, delete, fill, cut cross-sections [V MAN].
- Export: OBJ, 3DS, DAE, PLY, Alembic, STL, WRL, U3D, FBX, DXF, GLB, OSGB/OSGT, X3D, KMZ, LandXML, PDF [V MAN App. B]. USD and USDZ are not in the list.

### 1.12 Texture and materials

- `buildUV(mapping_mode = Generic | Orthophoto | Adaptive orthophoto | Spherical | Camera | ..., page_count, texture_size)` [V API].
- `buildTexture(blending_mode = Mosaic | Average | Max | Min | Disabled | NaturalBlending, texture_size=8192, downscale, sharpening, use_assigned_images, out_of_focus_filter)`. NaturalBlending is the 2.3 default [V API change log].
- Map types: diffuse, normal, occlusion, displacement. A high-detail model transfers its relief into the normal, occlusion and displacement maps of a low-polygon model ("Transfer Texture"); anti-aliasing casts several rays per texel when baking [V MAN ch. 3 "Building model texture"].
- Remove Lighting (delighting): single-colour or multi-colour mode, presets including one for rocks, internal blur, mesh noise suppression, optional external ambient-occlusion map and multiplier. The manual states removing shadows while keeping colour is ambiguous in general and the tool is heuristic [V MAN ch. 6 "Editing textures"; API `removeLighting`].
- Calibrate Colors (set-wide colour and optional white balance from the model) and Calibrate Reflectance (panels, sun sensor) [V API `calibrateColors`; MAN].
- Resize texture; texture editing tools (2.3) [V MAN heading "Editing textures"; details U].
- GPU texture blending uses Vulkan on Linux and Windows, for frame and fisheye cameras on NVIDIA [V MAN GPU section].
- PBR material export as a glTF with metal-rough maps: not found in the manual text [unknown].

### 1.13 Tiled models

- `buildTiledModel(pixel_size, tile_size=256, source_data, face_count=20000, ...)` for large scenes; export to Cesium 3D Tiles 1.0 and 1.1, SLPK, 3MX, PhotoMesh, OSGB, TLS, ZIP archive [V API; MAN App. B].

### 1.14 DEM and orthomosaic

- DEM from point cloud or tiled model, DSM or DTM after ground classification; export GeoTIFF, ASC, BIL, XYZ, tile pyramids, KMZ, GPKG, MBTiles [V MAN App. B].
- Orthomosaic projected on DEM or mesh: geographic, planar, cylindrical projections; mosaic and average blending; seamline editing (`buildSeamlines`); hole filling; pansharpening; export GeoTIFF with tiling, tile pyramids [V MAN; API].
- Panorama stitching from rotation-only captures (`buildPanorama`) [V API].
- Contours from DEM (`buildContours`) [V API].

### 1.15 Measurements

- Ruler distance along a polyline, area and perimeter of shapes, volume above a reference plane (best-fit, mean level or custom) on mesh and DEM, profile and cross-section cuts, point coordinates; stereoscopic measurement with a 3D display; vegetation indices (NDVI and others), powerline detection [V MAN ch. 5 headings and contents; the volume-plane options are U].

### 1.16 4D and multi-frame

- Multiframe chunks hold images from synchronised, statically mounted cameras at several time moments. Frame coordinate systems match by construction. A timeline pane steps through frames [V MAN ch. 7 "4D processing"].

### 1.17 Reports

The PDF or HTML processing report [V MAN ch. 3 "Generate Report"] lists: orthomosaic sketch; survey data (coverage area, altitude, GSD, camera info, overlap statistics); camera calibration per sensor with a distortion illustration; camera position and orientation error estimates; ground control and check point errors; scale bar errors; DEM sketch with resolution and density; LiDAR swath separation; plus system information and processing parameters (`exportReport(save_system_info, ...)` [V API]).

### 1.18 Export formats (summary)

Meshes (section 1.11), tiled models (1.13), point clouds (LAS, LAZ, PLY, E57, OBJ and others), DEM and ortho (1.14), cameras (many layouts; the earlier note says COLMAP export arrived in 2.2, not re-read), shapes (SHP, DXF, KML, KMZ), tie points, reports [V MAN App. B]. Gaussian splats are not an import or export type; a text search of the manual finds "Gaussian" only in the blur-filter sentence and the key-point scale sentence [V MAN].

### 1.19 Network and cloud processing

- Network: a server holds the task queue and does no processing; workers compute onto shared storage at one absolute path; clients submit; a Network Monitor shows queue and workers. Fine-level subdivision splits eligible tasks across workers; with it off, each chunk or frame goes to one worker [V MAN ch. 8].
- Cloud: Agisoft Cloud account with subscription, storage and processing hours; each operation asks "local or cloud"; mutually exclusive with network processing [V MAN ch. 8 "Cloud processing"].
- Claims in the overview: 50,000+ photos across a local cluster [V MAN overview].

### 1.20 Scripting and batch

- Python scripting, Professional only. The 2.3.0 API reference says the engine is Python 3.8 [V API overview]; metashape-mcp says "embedded Python 3.12" [V PYPI]. The two disagree; unresolved.
- Entry points: GUI console, Tools > Run Script, `-r script.py` on the command line, a stand-alone Python module (the change log mentions its `.pyi` stub) [V API].
- Every processing step is a `Chunk` method with a matching task class (`NetworkTask`, `ExportReport`, ...) that serialises for network submission [V API].
- Java API exists [V MAN ch. 7 heading].
- GPU: CUDA, OpenCL 1.2 and Vulkan for blending are named. Metal is not named. Supported-device table is Windows only [V MAN ch. 1].

---

## 1A. metashape-mcp

- **Source:** repo `jenkinsm13/metashape-mcp` on GitHub, author Michael Jenkins ("Copyright (c) 2026 Michael Jenkins" in LICENSE) [V GH]. Licence MIT [V GH LICENSE; PyPI metadata fields author and licence are null, the README badge says MIT]. Repo created 2026-02-21, last push 2026-05-07, 37 stars, default branch `master` [V GitHub API]. PyPI releases 0.1.0, 0.2.0, 0.3.0; 0.3.0 uploaded 2026-02-27; requires Python 3.12 or newer [V PYPI]. Third-party, not Agisoft.
- **Architecture:** a FastMCP server that runs inside Metashape Professional 2.3+ (GUI, or headless with `metashape -platform offscreen -r start_mcp_headless.py`) and serves Streamable HTTP on `127.0.0.1:8765/mcp`. A stdio proxy with a 24-hour timeout exists because Claude Code's HTTP transport drops calls after about 60 seconds; the README says dense cloud, mesh and texture calls run minutes to hours [V PYPI README]. There is no job handle: a tool call blocks until the step ends, with progress reported.
- **Counts:** README and PyPI say 106 tools, 10 resources, 6 prompts in 15 modules. The master branch source has a 16th module, `diagnostics.py`, and a grep of `@mcp.tool` decorators finds 112 tool functions; PyPI 0.3.0 predates it or the README count is stale [V GH; my count, not a vendor figure].

### Tool inventory (master branch names, grouped by module) [V GH src/metashape_mcp/tools/]

| Group | Tools |
|---|---|
| Project and chunks (12) | `open_project`, `save_project`, `create_project`, `add_chunk`, `set_active_chunk`, `list_chunks`, `duplicate_chunk`, `merge_chunks`, `align_chunks`, `set_gpu_config`, `get_processing_status`, `cancel_processing` |
| Photos and import (5) | `add_photos`, `analyze_images`, `import_video`, `remove_cameras`, `rename_cameras` |
| Cameras and sensors (8) | `enable_cameras`, `select_cameras`, `set_sensor`, `list_sensors`, `import_masks`, `clear_masks`, `get_camera_metadata`, `set_camera_reference` |
| Alignment (6) | `match_photos`, `align_cameras`, `optimize_cameras`, `filter_tie_points`, `reset_camera_alignment`, `get_alignment_stats` |
| Dense and point cloud (12) | `build_depth_maps`, `build_point_cloud`, `filter_point_cloud`, `filter_points_by_confidence`, `classify_ground_points`, `assign_point_class`, `remove_points_by_class`, `calculate_point_normals`, `colorize_point_cloud`, `clear_depth_maps`, `clear_point_cloud`, `get_point_cloud_stats` |
| Mesh (8) | `build_model`, `decimate_model`, `smooth_model`, `clean_model`, `close_holes`, `refine_model`, `clear_model`, `get_model_stats` |
| Texture (5) | `build_uv`, `build_texture`, `calibrate_colors`, `calibrate_reflectance`, `remove_texture` |
| Survey products (8) | `build_dem`, `build_orthomosaic`, `build_tiled_model`, `build_contours`, `build_panorama`, `clear_dem`, `clear_orthomosaic`, `clear_tiled_model` |
| Export (10) | `export_model`, `export_point_cloud`, `export_orthomosaic`, `export_dem`, `export_tiled_model`, `export_cameras`, `export_tie_points`, `export_shapes`, `export_reference`, `export_report` |
| Import data (6) | `import_model`, `import_point_cloud`, `import_reference`, `import_cameras`, `import_shapes`, `create_shape` |
| Markers and scale (9) | `detect_markers`, `add_marker`, `refine_markers`, `list_markers`, `remove_marker`, `set_marker_reference`, `export_markers`, `add_scalebar`, `remove_scalebar` |
| Coordinates (8) | `set_crs`, `transform_chunk_crs`, `set_reference_settings`, `set_region`, `set_region_rotation`, `reset_region`, `get_chunk_bounds`, `update_transform` |
| Network (5) | `network_connect`, `network_submit_batch`, `network_list_batches`, `network_batch_status`, `network_abort_batch` |
| Viewport and console (3) | `capture_viewport`, `get_console_output`, `auto_save` |
| Scripting (1) | `execute_python` (arbitrary code inside Metashape with `Metashape`, `app`, `doc`, `chunk` bound) |
| Diagnostics (6, master only) | `get_camera_spatial_stats`, `get_reprojection_error_by_region`, `check_alignment_continuity`, `compare_alignment_to_dem`, `generate_virtual_checkpoints`, `get_corridor_drift_report` |

**Resources (10)** [V PYPI README]: `metashape://project/info`, `metashape://project/chunks`, and per chunk `.../summary`, `.../cameras` (alignment status and error), `.../sensors` (calibration), `.../tie_points` (count, projections, reprojection error), `.../point_cloud`, `.../model`, `.../dem`, `.../orthomosaic`.

**Prompts** [V GH prompts/ and README]: `aerial_survey_pipeline`, `close_range_pipeline`, `batch_export`, `road_corridor_pipeline` (master), `diagnose_alignment`, `optimize_quality_settings`.

**Reading the inventory (judgement):**
- It mirrors Metashape's step list one tool per step, not a job model. The agent-facing shape this project wants differs: jobs with ids, stage results with quality state, variants, and "what to capture next".
- Quality state is thin: resources return counts and error summaries; the six diagnostics tools (regional reprojection error, alignment continuity, virtual checkpoints) are the nearest thing to a coverage verdict, and they target road-corridor and aerial work.
- No tools exist for splats, refraction, RAW, robot priors, per-image exposure, or comparing two reconstructions side by side. `execute_python` is the escape hatch for all of them.
- All state lives in one running Metashape process (one active document and chunk).

---

## 2. The other products

Price lines are as read today or `[U]`.

### RealityScan (Epic Games, ex-RealityCapture)
- **User:** game and VFX asset creators, scan studios, small AEC.
- **Capture:** RealityScan Mobile (iOS and Android; version 1.9 listed, August 2026) captures and processes objects from phone photos; desktop takes photos, laser scans and 360 camera footage [V <https://www.realityscan.com/en-US>].
- **Processing:** local on Windows; cloud integration exists; AMD GPUs supported from 2.2 [V same page]. 2.1 added the CLI `importColmap` and a REST/gRPC Remote Command plugin [U, earlier note].
- **Outputs:** meshes, textures, measurements, multiple export formats [V same page]; Unreal Engine integration and Nanite-ready meshes [U].
- **Distinct:** masks, control points, CLI batch, the fastest alignment of the commercial desktop tools in public reputation [U]; the best fit with Unreal.
- **UX:** workflow tabs (Alignment, Reconstruction, Texture) with a 3D scene view that shows registered components; "components" let a failed alignment be inspected and merged with control points [U].
- **Price:** free under $1M revenue and for educators; seat subscription above [V same page].

### Pix4Dmatic, PIX4Dcatch, PIX4Dcloud
- **User:** surveyors, AEC, inspection.
- **Capture:** PIX4Dcatch (iOS) takes photogrammetry plus LiDAR with AR guidance, pause and resume, RTK, automatic GCP detection in Pro [V <https://www.pix4d.com/product/pix4dcatch/>].
- **Processing:** Pix4Dmatic desktop for large datasets; PIX4Dcloud for collaboration [V <https://www.pix4d.com/product/pix4dmatic/>].
- **Outputs:** point clouds, orthomosaics, DSM/DTM, meshes, contours and gaussian splats; LAZ, TIFF, DXF, SHP, OBJ, FBX [V same page].
- **Distinct:** survey accuracy and CAD/GIS deliverables, a phone-to-desktop-to-cloud chain.
- **UX:** guided capture with live coverage feedback on the phone [V Catch page, AR feedback; the coverage detail is U].
- **Price:** Catch Discovery tier free; Matic is licensed, price not read [U].

### 3DF Zephyr
- **User:** surveyors, heritage, forensics, generalists who want a perpetual licence.
- **Capture:** photos, video, drone, laser scans (registration inside the app) [V <https://www.3dflow.net/3df-zephyr-photogrammetry-software/>].
- **Processing:** local; GPU count tied to edition [V same page].
- **Outputs:** meshes, textures, orthophotos, orthomosaics, DEMs [V same page]; masking and measurements in-app.
- **Distinct:** the full tool in one GUI at a lower price than Metashape Professional; free tier capped at 50 photos.
- **Price:** Free (50 photos), Lite 199 EUR, 250 EUR per month, Professional 4,200 EUR perpetual with 12 months of updates, renewals at 20% [V same page].

### DJI Terra
- **User:** DJI drone and enterprise mapping operators.
- **Capture:** DJI flight missions; photogrammetry, LiDAR, multispectral [V <https://enterprise.dji.com/dji-terra>].
- **Processing:** local, with cluster and cloud processing; gaussian splatting reconstruction [V same page].
- **Outputs:** 2D maps, 3D models, quality assessment reports [V same page].
- **Distinct:** tight drone-to-result flow for DJI hardware. The owner's DJI Mini 4 Pro is a consumer drone; support for it in Terra is unknown.
- **Price:** one-month trial with 500 photo cap; Standard and Flagship through dealers [V same page].

### Bentley iTwin Capture Modeler
- **User:** infrastructure and AEC owners.
- **Capture:** photos, point clouds, video [V <https://www.bentley.com/software/itwin-capture-modeler/>].
- **Processing:** on-prem engine or cloud services; hybrid and parallel clustering [V same page].
- **Outputs:** reality meshes, gaussian splats, point clouds, orthophotos [V same page]; GCPs, masking, retouching, surface constraints; AI crack detection and feature extraction in cloud services.
- **Price:** free data preparation, pay on processing (Flex), enterprise licences [V same page].

### Polycam
- **User:** creators, real-estate and construction capture, AR/VR.
- **Capture modes:** LiDAR, Photo, 360 photosphere, Object mode (mesh or gaussian splat), splats; floor plans and measurements from LiDAR only [U, search snippets quoting Polycam help]. Web and app both process photos [U].
- **Processing:** cloud [U]. Limits per plan: 150 images free, 300 Basic, 2,000 Business and Enterprise; video 3, 5, 30 minutes [V <https://poly.cam/pricing>].
- **Outputs:** GLTF on the free plan; OBJ, FBX, DAE, STL, USDZ, PLY and point clouds (LAS, PTS, XYZ, DXF) above it; floor plan exports to CAD formats [V pricing page; U help snippet].
- **Distinct:** one app and web library for LiDAR rooms, photogrammetry and splats; measurements and 2D/3D floor plans; shared team library; Content Management API on Enterprise [V pricing page].
- **UX:** capture, wait, edit in a web viewer with crop and clean tools, share by link [U].
- **Price:** Free; Basic $150/year; Business $300/year per user (Black Friday price, $400 list); Enterprise $1,200/year per user, 3 seats minimum [V pricing page].

### KIRI Engine
- **User:** hobbyists and game asset makers on phones.
- **Capture modes:** Photo Scan, LiDAR Scan with floor plans, Featureless Object Scan inside the 3DGS mode (shiny, transparent, plain objects), 3DGS [V <https://www.kiriengine.app/>].
- **Processing:** cloud; the site names an API with details on a separate page [V same page; pay-per-credit and 3DGS-to-mesh are from the earlier note].
- **Outputs:** quad mesh with PBR textures, high-poly and decimated versions, gaussian splat files, with mesh export from splats [V same page].
- **Distinct:** AI auto-rigging, mesh cleanup and decimation built in, production-oriented exports; iOS, Android and web [V same page].
- **UX:** capture guidance with shutter and EV controls [V same page].
- **Price:** free tier plus Pro subscriptions [V same page; amounts unknown].

### Luma AI
- Luma's home page shows video generation models (Ray 3.2) and a brand model (Uni-1); it does not mention 3D capture, NeRF or splats [V <https://lumalabs.ai/>]. Whether the capture app and API still exist: unknown. Treat as not a photogrammetry product today.

### Scaniverse (Niantic Spatial)
- **User:** phone users, enterprise teams via Niantic Spatial.
- **Capture:** phone, 360 cameras, drones, LiDAR, robots [V <https://www.nianticspatial.com/products/capture>]; "self-service mobile and web app".
- **Processing:** the page names on-demand and bring-your-own-data services; on-device processing is the long-standing claim [U].
- **Outputs:** gaussian splats and meshes in SPZ, PLY, GLB, USDZ [V same page].
- **Distinct:** free, on-device splat capture, SPZ as the compressed splat format [U for free and on-device].
- **Price:** unknown for current tiers.

### Apple Object Capture and Reality Composer
- `PhotogrammetrySession` takes images with optional depth, gravity and masks, and returns USDZ at several detail levels (preview, reduced, medium, full, raw); macOS only for the framework, iOS capture through apps [U; the fetch tool returned a summary from memory, not the page].
- **Distinct:** zero-parameter workflow, best matte-object results per effort on Apple silicon, USDZ for AR Quick Look. **Price:** free with the OS [U].

### Jawset Postshot
- **User:** VFX and 3D artists making splats.
- **Capture:** images (JPG, PNG, TIF, EXR, DNG, RAW), video (MOV, MP4, MKV), poses and points from COLMAP and other tools [V <https://www.jawset.com/>].
- **Processing:** local training, no cloud; Windows with NVIDIA compute capability 7.5 or higher [V same page].
- **Outputs:** PLY and splat formats; Unreal Engine and After Effects integrations; CLI [V same page].
- **Distinct:** artist-friendly training with live preview, edit and clean tools, RAW and video in directly.
- **Price:** free download; paid tiers not stated on the page.

### Nerfstudio viewer
- Web viewer launched by `ns-train` at `localhost:7007`: live training view, camera path editor, video render, crop box, export of mesh, point cloud and splat, remote use by SSH port forward, share URLs [V <https://docs.nerf.studio/quickstart/viewer_quickstart.html>]. The pattern worth copying: the viewer is a client of the training process, so you watch training and steer it.

### WebODM
- **User:** drone mappers, local governments, farmers.
- **UI:** map view, 3D view, measurement tools, plant health analysis; API; plugins [V <https://github.com/OpenDroneMap/WebODM>].
- **Processing:** engines ODX and LGT; processing nodes; AGPL-3.0; outputs maps, point clouds, elevation models, textured models, gaussian splats [V same page].
- **UX:** projects, tasks with live console, a quality of "drop images, press go" with presets, side-by-side tile layers [U for the last two].
- **Price:** free installers; hosted paid service [U].

### Meshroom (AliceVision)
- **UI:** node graph editor, per-node attributes, logs and statistics, 2D/3D viewers, image gallery; smart caching reprocesses only downstream nodes; local or render farm execution [V <https://github.com/alicevision/Meshroom>].
- **Plugins:** AliceVision (reconstruction, camera tracking, HDR, panorama, photometric stereo), AI segmentation from text, MeshroomHub plugins for depth estimation and splatting [V same page].
- **Distinct:** every pipeline stage is inspectable and re-runnable; the graph is the project file.
- **Price:** free, MPL-2.0 [V same page].

### Teleport by Varjo
- Paid iPhone and iPad capture app using gaussian splatting, with a PC VR viewer and export to Unity and Unreal; Teleport 2.0 (April 2025) accepts almost any camera including drone and DSLR [U, search snippets from Road to VR, Varjo news and others]. Current status in late 2026: unknown.

### Sketchfab
- The common web 3D sharing and viewing standard: upload, embed, annotations, AR and VR viewing, PBR materials, optional downloads [U; the help page fetch failed]. Splat support: unknown. Price: free tier with limits, paid plans [U].

---

## 3. Underwater workflows and products

- **Core tool:** reef and wreck groups report Metashape as the reconstruction engine; one search summary says it is chosen for automatic per-dataset distortion calibration [U, search snippets quoting ISPRS and NOAA/AIMS documents; I did not read the documents].
- **Viewing and annotation:** Viscore (viewer for large SfM reef models, used by the 100 Island Challenge) and TagLab (AI-assisted segmentation with SAM, GPL-3.0) are named in reef workflows; the earlier research note read both pages, I did not re-read them today [U]. A reef SOP summary says coral colonies are segmented in TagLab and data exported "in formats for GIS and TagLab" [U].
- **CoralNet:** web service for point-annotation of 2D images by humans and a classifier [U, memory]. Whether it takes 3D inputs: unknown.
- **Scale:** scale bars placed on the seabed at right angles touching at one end, at the wreck's depth when the port is flat [U, SHIPS project snippet]. Lasers and stereo bars: unknown for this project.
- **Ports:** dome ports centred on the entrance pupil largely remove refraction; flat ports violate the pinhole model and change with depth [U, ISPRS snippets]; the earlier note read a 2020 ISPRS paper on radial weighting for flat ports [U here].
- **Colour:** colour correction before processing is standard advice [U]; Sea-thru needs range per pixel [U, earlier note].
- **Product features:** no commercial product in this list has an explicit refraction camera model or a depth-aware colour restoration step that I found. Polycam and KIRI have no underwater mode that I found. For Metashape, the manual shows no refraction model [V MAN App. D, absence]. Open-source: Refractive COLMAP (flat and dome ports, IROS 2024) and WaterSplatting exist [U here, read in the earlier note].
- **Unknown:** what the AIMS and NOAA SOPs specify for alignment settings and marker use (fetch timed out); how much of current wreck practice uses Metashape versus RealityCapture or Pix4D; typical image counts and swim patterns; backscatter handling; moving fish and divers as masking tasks.

---

## 4. Feature matrix

Legend: **Y** yes, **P** partial, **N** no, **?** unknown. Cells are my reading of the sources above; most non-Metashape cells rest on `[U]` evidence. Columns: MS = Metashape, RS = RealityScan, P4D = Pix4D (Matic, Catch, Cloud together), ZEP = Zephyr, POL = Polycam, KIR = KIRI, PS = Postshot, ODM = WebODM, MSH = Meshroom.

| Feature | MS | RS | P4D | ZEP | POL | KIR | PS | ODM | MSH |
|---|---|---|---|---|---|---|---|---|---|
| **Capture and ingest** | | | | | | | | | |
| Photos (JPEG, TIFF) | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Camera RAW decoded in-tool | P (DNG only) | ? | ? | ? | ? | ? | Y (RAW, DNG) | ? | ? |
| Video input | P (frame extraction) | ? | ? | Y | Y | Y | Y | ? | P |
| Phone depth or LiDAR input | P (TrueDepth) | ? | Y (Catch) | ? | Y | Y | N | N | N |
| Laser scan input | Y | Y | ? | Y | N | N | N | N | N |
| Own mobile capture app | N | Y | Y | N | Y | Y | N | N | N |
| **Preprocessing and colour** | | | | | | | | | |
| Set-wide colour calibration | Y (Calibrate Colors) | ? | ? | ? | ? | ? | ? | N | N |
| Masking (manual) | Y | Y | ? | Y | P | ? | P | N | P |
| Masking (AI) | Y | ? | ? | ? | ? | ? | ? | N | Y (plugin) |
| **Alignment** | | | | | | | | | |
| Known poses as priors | Y (reference preselection, `alignCamerasByReference`) | Y | Y (GPS, RTK) | Y | N | N | Y (COLMAP in) | P (GPS) | P |
| Fisheye and spherical models | Y | Y | ? | Y | ? | ? | ? | P | Y |
| Explicit water refraction model | N | ? | ? | ? | N | N | N | N | N |
| **Scale and georeference** | | | | | | | | | |
| Coded targets, scale bars | Y | P | P | Y | N | N | N | P (GCP) | N |
| GCPs and CRS | Y | Y | Y | Y | N | N | N | Y | P |
| **Dense and mesh** | | | | | | | | | |
| Depth maps to dense cloud | Y | Y | Y | Y | Y | Y | N | Y | Y |
| Mesh with hole closing, decimation | Y | Y | Y | Y | Y | Y | N | Y | Y |
| Mesh from splat | N | ? | ? | ? | ? | Y | N | ? | P (plugin) |
| Tiled or LOD models | Y | ? | Y | ? | N | N | N | Y | N |
| **Texture and materials** | | | | | | | | | |
| UV and texture atlas | Y | Y | Y | Y | Y | Y | N | Y | Y |
| Normal, occlusion maps | Y | ? | ? | ? | ? | Y (PBR) | N | N | P |
| De-lighting | Y (Remove Lighting) | P | ? | ? | ? | ? | N | N | N |
| **Splats** | | | | | | | | | |
| Splat training | N | ? | Y | ? | Y | Y | Y | Y | P (plugin) |
| Meshes and splats from one pose set | N | ? | ? | ? | P | P | N | P | P |
| **Asset export and game engines** | | | | | | | | | |
| FBX, OBJ, GLB | Y | Y | Y | Y | Y | Y | N | Y | P |
| USD, USDZ | N | ? | ? | ? | Y | ? | N | ? | ? |
| Engine plugin or direct integration | N | Y (Unreal) | N | N | N | P | Y (Unreal) | N | N |
| **Measurement and analysis** | | | | | | | | | |
| Distance, area, volume | Y | Y | Y | Y | Y (paid) | ? | N | Y | N |
| Floor plans | N | N | N | N | Y | Y | N | N | N |
| **Quality reporting** | | | | | | | | | |
| Processing report (PDF) | Y | ? | Y | Y | N | N | N | Y | N |
| Machine-readable quality state | P (API objects) | ? | ? | ? | N | N | N | P | P |
| **Visualisation and sharing** | | | | | | | | | |
| In-app viewer with editing | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Web share link | P (cloud) | P | Y | ? | Y | Y | N | P | N |
| **Automation, API, agents** | | | | | | | | | |
| Scripting API | Y (Pro) | P (CLI, REST) | ? | ? | P (Enterprise API) | Y (API) | P (CLI) | Y | Y |
| MCP server | P (third party) | N | N | N | N | N | N | N | N |
| **Distributed processing** | | | | | | | | | |
| Multi-machine local pool | Y (task level) | ? | ? | P | N | N | N | Y (nodes) | Y (render farm) |
| Metal, CUDA, ROCm, CPU pool | N (no Metal named) | N (Windows; CUDA, AMD) | ? | ? | N | N | N (NVIDIA) | ? | N (CUDA) |

---

## 5. Use-case mapping

"Best today" is judgement based on the evidence above and on the owner's gear.

| Use case | Features needed | Best today and why |
|---|---|---|
| **Lego and small objects** | Turntable or handheld capture; masks (AI and manual); stationary-point filtering; scale from a known object or targets; fine mesh with sharp edges; clean texture; hole closing; GLB or OBJ export | Apple Object Capture for the zero-effort matte case [U]; Metashape for control (masks, stationary points, calibrate colours). RealityScan is a close rival and is free for the owner. KIRI for plain-coloured bricks (featureless mode). |
| **Bike, motorbike, car** | Thin tubes and spokes; glossy and reflective parts; masking of background; fixed scale; large image counts; decimated engine-ready mesh with normal maps; optional splat for the view-dependent shine | Metashape or RealityScan for geometry; a splat (Postshot, Polycam) for reflective parts. No tool handles chrome well; none verified. |
| **House interior** | Low-texture walls; ARKit and LiDAR priors; robot poses; panorama or 360 capture; floor plan; measurements; scene-scale mesh; sharing | Polycam for LiDAR rooms with floor plans and measurements [U]; RealityScan with 360 footage [V]. Metashape accepts TrueDepth only [V]. |
| **Building from drone** | GPS priors, GCPs, CRS, orthomosaic and DEM, tiled model for large scenes, report | Metashape or Pix4Dmatic for survey outputs; WebODM free and capable [V]. DJI Terra for DJI drones; Mini 4 Pro support unknown. |
| **Underwater wreck and reef** | Fisheye or dome-port calibration; refraction handling; colour restoration; scale bars at depth; moving-fish masks; large image sets; GIS or annotation export | Metashape in practice (section 3); nobody models refraction or restores colour in the loop. Viewing with Viscore, annotation with TagLab [U]. Open gap. |
| **Game-engine asset** | Clean mesh, retopology or decimation, UV atlas, PBR maps (normal, AO, de-lit albedo), correct scale and up axis, FBX or GLB, LODs, engine import notes | RealityScan with Unreal integration; KIRI for quad meshes with PBR and auto-rig [V]; Metashape for texture controls (de-lighting, normal-from-high-poly [V]). Godot, Unity, Blender paths: formats only (GLB, FBX, OBJ). |
| **Robot capture set** | Poses and intrinsics as input with a stated frame and scale; fisheye models; batch CLI and HTTP; reports with registration and reprojection numbers; metric output with provenance | Metashape via reference import and Python [V API]; RealityScan CLI and Remote Command [U]; no product states scale and frame on its outputs as a contract. Open gap. |
| **Agent-steered reconstruction** | Job API with ids and status; machine-readable quality state; ability to change one stage and compare variants; capture advice; cancel and resume | Metashape plus `metashape-mcp` (section 1A) is the only working example; one process, blocking calls, thin quality state. Open gap. |

---

## 6. MVP versus complete feature set (judgement)

This section is a recommendation, not a finding. Differentiator marks (**D**) flag things the leaders do poorly or not at all, per the evidence above.

### Tier 1: MVP (household object, Lego, room)

The smallest set that stops the owner reaching for RealityScan, Polycam or Apple Object Capture on these scans.

| Feature | Why |
|---|---|
| Upload photos, RAW and video frames; EXIF and lens read | Entry point for every use case. |
| **D** RAW decode (NEF, ARW, DNG, HEIC, ProRAW) with set-wide white balance and exposure | Metashape lists DNG only [V MAN]; others need Lightroom. |
| Alignment with a registered-image count and per-image status | The first thing a user checks. |
| Camera calibration estimated per lens, including fisheye, shown to the user | GoPro and drone images need it. |
| Masks: manual brush and an automatic subject mask | Lego and turntable sets fail without them. |
| Scale: set from a known distance or a marker pair; the model states "metric" or "arbitrary" | **D** (scale and frame stated); a table-stakes feature elsewhere. |
| Dense reconstruction and a watertight textured mesh with hole closing and decimation | The deliverable. |
| Texture atlas with seam-free exposure | Follows from the RAW stage. |
| Export GLB, OBJ, PLY with a stated up axis and units | Needed for Blender and Godot. |
| Web viewer for mesh and point cloud, with a quality overlay (registered cameras, error) | Quality is visible, not implied (brief section 3). |
| Job list with live progress and logs; HTTP API mirroring every UI action | One engine, three faces. |
| MCP read tools: project state, per-image registration, reprojection error | **D** agent-native quality state; `metashape-mcp` offers counts, not verdicts. |
| One worker on the laptop, one remote worker, jobs placed by capability | **D** hardware pooling, but at MVP only two machines. |

> **Superseded on splats (2026-11-23):** the owner decided splats are in the MVP, bounded — one
> splat per reconstruction from the same poses, GLB and PLY, held-out-view PSNR/SSIM as a quality
> metric ([architecture sketch](../concept/RC-architecture-sketch.md) §9). The line below is
> this analysis's original recommendation.

Not in the MVP: splats, tiled models, DEM and ortho, GCP and CRS work, de-lighting, normal maps, underwater, floor plans.

### Tier 2: v1 (all use cases adequately)

| Feature | Why |
|---|---|
| **D** Splat training and viewer from the same pose set as the mesh | Metashape has none; Polycam, KIRI and Postshot give a splat or a mesh per capture, not both from one pose set as a stated feature. |
| **D** Pose priors with stated frame and scale: ARKit, robot files, GPS, GoPro GPMF | Robot and phone sets; no tool states frame and scale as an output contract. |
| **D** Hardware pool across Metal, CUDA, ROCm, CPU | No product in this analysis lists Metal or mixed backends. |
| Coded targets (AprilTag) and scale bars | Large objects and wrecks. |
| GCPs, CRS, georeferenced export, DEM and orthomosaic | The drone building. |
| Tiled or LOD model and a splat or mesh LOD path | Whole-building scale. |
| Normal and occlusion maps, de-lighting heuristic, LOD decimation, PBR glTF | Game-engine assets. |
| Measurement: distance, area, volume, floor plan from a mesh | House interior. |
| Processing report as PDF and JSON | Reference-class parity [V MAN report contents]. |
| **D** Variant comparison: two reconstructions of one capture side by side | Meshroom-style inspectability, no commercial tool offers it. |
| MCP write tools: start, cancel, change a stage, compare, "capture here next" | Agent steering. |
| Share link and export for Sketchfab, USDZ, SPZ | Sharing. |

### Tier 3: complete (parity-plus with Metashape on what matters to this owner)

| Feature | Why |
|---|---|
| **D** Underwater: refraction model (flat and dome port), depth-aware colour restoration after geometry, uncorrected copy kept for features | Not offered by Metashape [V MAN absence] or any product in section 2. |
| **D** Splat and mesh joint optimisation; mesh from splat at asset quality | KIRI offers mesh from splat; quality unverified. |
| Laser scan and depth fusion | Metashape parity. |
| 4D multi-frame (synchronised camera rigs) | Parity; low priority for the owner. |
| Network job model with fine-grained subdivision (per image, per pair, per tile) | Metashape splits per task with optional fine subdivision [V MAN]; this project aims lower in the pipeline. |
| Classification, retopology, UV editing tools | Asset polish. |
| Annotation and Viscore/TagLab-style review for reefs | Underwater monitoring. |
| Engine plugins for Unreal, Unity, Godot, Blender | Smooth import. |
| Python SDK and CLI with feature parity to the API | Metashape and RealityScan both offer one. |

---

## 7. Not verified

- Metashape: 2.3 release notes (GNSS bias, texture editing, colour enhancement, fisheye variants) not re-read; volume-plane options; coordinate-system details beyond headings; Java API; whether PBR maps export in glTF; Python version discrepancy (3.8 in the API doc, 3.12 in metashape-mcp).
- metashape-mcp: master-branch counts are from a grep of decorators, not from running the server; resource list beyond the README unchecked; I did not run it or read tool bodies.
- Pricing of Metashape editions and RealityScan seats: from the earlier research note, store pages not re-read.
- RealityScan: mobile capabilities beyond the product page, Nanite output, UX claims (tabs, components) are from memory.
- Pix4D: Matic pricing, splat quality, live coverage feedback in Catch.
- Zephyr: feature depth beyond the product page; its scripting and splat support.
- DJI Terra: Mini 4 Pro support.
- Polycam: capture mode details and web processing rest on search snippets; the Help Center pages returned 403 or DNS failure.
- KIRI: pay-per-credit API and price amounts.
- Luma: whether any 3D capture product or API remains.
- Scaniverse: current tiers, on-device processing today.
- Apple Object Capture: the fetch returned a generic summary; every claim is `[U]`.
- Postshot: paid pricing and licence terms; platforms other than Windows.
- WebODM: UX patterns, hosted service price.
- Meshroom: current release features; CUDA requirement not stated on the page read.
- Teleport by Varjo: current status and pricing.
- Sketchfab: formats, splat support, limits (help page fetch failed).
- Underwater: AIMS and NOAA SOPs not read; usage share of Metashape versus others; Viscore and TagLab pages not re-read today; CoralNet details; laser and stereo scale methods; backscatter; moving subjects.
- The matrix: every non-Metashape cell is a reading of vendor marketing or memory, not a test. `?` cells are unknown, not "no".
