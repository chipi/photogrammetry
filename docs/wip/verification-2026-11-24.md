# Verification of open facts (2026-11-24)

This note checks the facts marked "to verify" or "unknown" in `docs/concept/RC-brief.md`, `docs/concept/RC-use-cases.md` and `docs/reference/*.md` against primary sources: Apple Developer and Support pages, GoPro's manual and product pages, GitHub and GitLab repositories, dataset pages, the papers and the conda-forge and PyPI indexes. `[V]` means the page was read on 2026-11-24; `[U]` means it was not (search snippet or memory). Apple's iPhone User Guide pages read today carry the current (iOS 26) text; the iPhone 15 Pro statements rest on the iOS 17-era Apple article 119916 where it matters. Several items need a test on the real device; they are listed at the end. The search/fetch budget of about 30 was exceeded (about 50 calls) because several vendor pages are JavaScript shells and needed a second route.

## Summary

| Item | Answer | V/U | Consequence |
|---|---|---|---|
| 1a iPhone default resolution | Camera app default is 24 MP HEIF (changeable to 12 MP). 48 MP only via Resolution Control: HEIF Max, JPEG Max or RAW Max; ProRAW is 12 or 48 MP. Ultra Wide, Telephoto, Night, flash and macro: 12 MP only | V | Capture protocol must say "HEIF Max or RAW Max, 1x main camera"; default shots are 24 MP |
| 1b Safari HEIC upload | Safari transcodes a file whose type is not in the `accept` list, to the first type listed; `image/*` was treated as a literal string until a fix in Jan 2026. "Most Compatible" changes the capture format to JPEG | V | Set `accept` explicitly and test on the phone; do not assume HEIC arrives or is converted |
| 1c Macro auto-switch | Yes, can be turned off: in-camera Auto Macro button, and Settings > Camera > Macro Control | V | Protocol: turn Auto Macro off, shoot at 1x; ultra-wide macro is 12 MP anyway |
| 1d ProRAW processing | ProRAW is captured together with Smart HDR, Deep Fusion or Night mode, so it is not unprocessed sensor data | V | Do not treat ProRAW as radiometrically linear; per-photo tone mapping can still differ |
| 1e ARKit | `captureHighResolutionFrame` exists, iOS 16+, needs a high-res video format. World frame y-up, right-handed, camera starts looking down -z. `sceneDepth` needs LiDAR (iOS 14+). Resolution on iPhone 15 Pro, default `capturedImage` size, intrinsics drift and 256x192 depth are not on Apple's doc pages | V (API, axes), U (sizes), unsettled (15 Pro size, intrinsics drift) | Log `intrinsics` and image size per frame on the device before relying on a fixed K |
| 2a HERO13 RAW | .gpr (DNG-based) in Photo, Burst, Night, Time Lapse photo and Night Lapse photo, only with SuperPhoto off, digital lens Wide, zoom off, Time Lapse interval 5 s or more, Night Lapse shutter 5 s or more | V (manual copy hosted by Adorama) | P-GoPro runs use Wide + RAW; lens is Wide, which is the most distorted mode |
| 2b HERO13 lens modes | Photo: Wide (16-34 mm) and Linear (19-39 mm) only. Time-lapse video: TimeWarp has HyperView, SuperView, Wide, Linear, Linear + Horizon Lock; Time Lapse and Night Lapse video have Wide and Linear; Star Trails, Light Painting, Vehicle Light Trails have Wide. Video also has Narrow (high-fps presets). No Max SuperView | V | No Narrow, HyperView or SuperView in stills; RAW forces Wide; Linear is the lowest-distortion still mode |
| 2c HB lens mods | Macro: manual focus ring 11-75 cm. Ultra Wide: up to 177 degrees FOV. Anamorphic: 21:9 with in-camera de-squeeze. ND 4-pack: ND4, 8, 16, 32. Camera auto-detects the mod | V | A mod is a different optical system: calibrate it as its own camera; Macro mod is the only close-focus route |
| 2d Lens mode in metadata | GPMF defines `VFOV` (L/S/W/H), `ZFOV`, `PRJT`, `DZOM/DZMX`; GPMF README says header metadata is in all MP4 and JPG files; ExifTool reads GPMF from the JPEG APP6 segment. Whether a HERO13 photo writes `VFOV` is not confirmed | V (spec), unsettled (actual files) | Run `exiftool -G1 -a -u` on a real HERO13 JPG and GPR before the ingest stage depends on it |
| 2e Stock minimum focus | Not published on the pages read (manual, product pages). Only a marketing claim that the Macro mod focuses "4X closer" | V (absence), unsettled | Measure on the camera with a ruler target |
| 3a Mip-NeRF 360 licence | No licence or terms on the project page; the code repo (multinerf) is Apache-2.0; the zip's contents were not inspected | V (page), unsettled | Local development only; ask the authors or inspect the zip before any release |
| 3b COLMAP datasets | South Building 128 images at 3072x2304 (checked in the zip); Gerrard Hall 100, Person Hall 330, Graham Hall 1273 images; resolution of the last three not checked; no licence stated; download from github.com/colmap/colmap releases 3.11.1 | V | Graham Hall stays the only 1,000+ set but is a roughly 11.8 GB multipart download; resolution still to check |
| 3c ETH3D evaluation | Tolerances 1, 2, 5, 10, 20, 50 cm; tool is `ETH3D/multi-view-evaluation`, BSD licence, depends on Boost, Eigen, PCL | V | Evaluation can run locally and be bundled; GitHub shows "NOASSERTION" only because the file is `LICENSE.txt` |
| 3d SQUID targets | Identical waterproof colour charts from DGK Color Tools at several distances, plus a calibration checkerboard; RAW, TIF, calibration files and distance maps; 57 stereo pairs, 4 sites | V | Usable for colour-chart checks (P8); exact DGK chart model not stated |
| 3e AquaMVS licence | MIT (LICENSE file and PyPI metadata) | V | No licence blocker |
| 4 Refractive COLMAP | New BSD (`COPYING.txt`, underwater branch). Not merged upstream: no refractive model in COLMAP main. No pycolmap bindings found in the fork | V (licence, models.h), "not found" (bindings) | Treat as a separate C++ build; refractive SfM is CLI only, no Python path |
| 5 Akkaynak and Treibitz | 2018 paper: backscatter coefficients differ from direct-transmission coefficients. Range and reflectance dependence of the attenuation coefficient was shown earlier and is restated in the 2019 paper. Sea-thru (2019) applies the revised model to RGBD images | V | Cite both; Sea-thru needs a range map, which the pipeline has from MVS |
| 6 COLMAP dense | `patch_match_stereo` needs CUDA or the HIP/ROCm build. No CPU or Metal path in the docs read. Current COLMAP is 4.2.1 (2026-09-29) | V | No COLMAP dense on the M4 Pro MacBook; X3 (gfx1151) HIP support is still untested |
| 7 pycolmap | 4.2.1. PyPI wheels: Linux x86_64, macOS arm64, Windows only; no Linux aarch64, no macOS x86_64. conda-forge has 4.2.1 for linux-aarch64 (CPU and CUDA 12.9 / 13.4 builds) and osx-64 (CPU only). Source build documented for Linux and macOS | V | On the aarch64 CUDA box use conda-forge; PyPI wheel will not install |

## 1. iPhone 15 Pro

### 1a. Default photo resolution

- "On supported models, you can change the default resolution of the Main or Fusion cameras from 24 MP to 12 MP... To capture resolution at 48 MP, go to Settings > Camera > Formats, then turn on Resolution Control or ProRAW & Resolution Control." [V <https://support.apple.com/guide/iphone/change-advanced-camera-settings-iphb362b394e/ios>]
- iPhone 14 Pro and later with iOS 17: formats HEIF Max and RAW Max give up to 48 MP; RAW 12 gives 12 MP; standard HEIF gives up to 24 MP. ProRAW files are about 25 MB at 12 MP and about 75 MB at 48 MP. "Only photos that you take with the main camera at 1x can be saved 48 MP. Ultra Wide, Telephoto, Night mode, flash, and macro photos can only be saved at 12 MP." [V <https://support.apple.com/en-us/119916>]
- The 24 MP default is a Camera-app mode. AVFoundation on iPhone 15 Pro lists only 12 MP and 48 MP in `supportedMaxPhotoDimensions` (Apple forum answer, Nov 2023) [V <https://developer.apple.com/forums/thread/738418>, a user post, not Apple documentation; may be outdated].

### 1b. Safari upload and HEIC

- WebKit bug 303803: Safari 17+ transcodes an uploaded file to the first MIME type in the `accept` list when the file's own type is not in the list. Because `image/*` was matched as a literal string, `accept="image/*,image/heic"` turned PNG and JPEG into HEIC. The wildcard fix was committed in January 2026. [V <https://bugs.webkit.org/show_bug.cgi?id=303803>; page read through the fetch tool's summary]
- Apple developer forum report of the same behaviour (a `.jpeg` arrives as `tempImage....heic`). [V <https://developer.apple.com/forums/thread/743049>]
- "Most Compatible" (JPEG) versus "High Efficiency" (HEIF) is the capture format under Settings > Camera > Formats; it applies when RAW is off. [V <https://support.apple.com/en-us/119916>]
- Not settled: what the photo picker hands Safari for a HEIC original with a plain `accept="image/jpeg"`, and whether a ProRAW DNG passes through unchanged. Needs a test page on the phone with each `accept` variant and a log of `File.type`, name and size.

### 1c. Macro control

- "Get close to the subject, as close as 2 centimeters. Camera will automatically switch to the Ultra Wide camera." An on-screen button turns automatic macro switching off. "To turn off the manual Macro Control... go to Settings > Camera, then turn off Macro Control"; Settings > Camera > Preserve Settings keeps the choice between sessions. [V <https://support.apple.com/guide/iphone/take-macro-photos-and-videos-iphfaacf2eb0/ios>]
- The page does not say which setting state is the default on an iPhone 15 Pro. Check on the phone.

### 1d. ProRAW and computational processing

- "Apple ProRAW combines the information of a standard RAW format along with iPhone image processing"; capture works "including when also using the Smart HDR, Deep Fusion, or Night mode features." [V <https://support.apple.com/en-us/119916>]
- ProRAW is not available with Live Photos, Portrait mode or video. [V same page]

### 1e. ARKit

- `ARSession.captureHighResolutionFrame(completion:)`: iOS 16.0+, iPadOS 16.0+. Delivers a frame out-of-band with pose, anchors and semantics filled in; fails if a previous request is pending. For the highest resolution choose a non-binned `ARConfiguration.VideoFormat`, e.g. `recommendedVideoFormatForHighResolutionFrameCapturing`. [V <https://developer.apple.com/documentation/arkit/arsession/capturehighresolutionframe(completion:)>, read via Apple's documentation JSON feed]
- Resolution: the WWDC22 session says "on my iPhone 13 that means the full 12 megapixels of the wide camera"; 4K video mode is 3840x2160 at 30 fps (iPhone 11 and later). [V <https://developer.apple.com/videos/play/wwdc2022/10126/>] The iPhone 15 Pro value is not stated by Apple: unsettled. A DTS reply on an iPhone 16 Pro thread says 48 MP ultra-wide capture during an AR session has "no supported way". [V <https://developer.apple.com/forums/thread/769604>]
- `ARFrame.capturedImage`: full-range planar YCbCr (BT.601) pixel buffer. The doc page gives no size. 1920x1440 is the commonly quoted default [U, forum snippet].
- `ARCamera.intrinsics`: 3x3 matrix in pixels (fx, fy, px, py, origin at the centre of the upper-left pixel), "based on physical characteristics of the device camera and a pinhole camera model." [V <https://developer.apple.com/documentation/arkit/arcamera/intrinsics>] The page does not say whether it changes per frame: unsettled.
- World frame: with `.gravity` alignment "the y-axis is parallel to gravity", z-axis basis (0,0,-1) points where the device camera faces at session start, x-axis by the right-hand rule; "World coordinate space in ARKit always follows a right-handed convention." [V <https://developer.apple.com/documentation/arkit/arconfiguration/worldalignment-swift.enum/gravity>; <https://developer.apple.com/documentation/arkit/arcamera/transform>] Camera space: z points away from the screen side, so the camera looks along its own -z (consistent with the doc's wording, not stated in one sentence).
- `sceneDepth`: needs LiDAR, iOS 14.0+, `nil` unless the frame semantic is enabled; `depthMap` is metres. [V <https://developer.apple.com/documentation/arkit/arconfiguration/framesemantics-swift.struct/scenedepth>; <https://developer.apple.com/documentation/arkit/ardepthdata/depthmap>] 256x192 is stated by forum answers and the search snippet, not by an Apple doc page I read [U].

## 2. GoPro HERO13 Black

Source for 2a, 2b: the HERO13 Black user manual, a copy hosted at <https://www.adorama.com/col/productManuals/GPHERO13A.pdf> (GoPro's own document, retailer host; gopro.com help pages are JavaScript shells and did not render) [V].

### 2a. RAW

"All photos are saved as a .jpg image... and a .gpr file", DNG-based. Available for Photo, Burst, Night, Time Lapse photo and Night Lapse photo with: SuperPhoto off, digital lens Wide, zoom off, not for continuous photos, Time Lapse interval at least 5 s, Night Lapse shutter at least 5 s. HDR also does not work with RAW. Photo resolution 27 MP at 8:7.

### 2b. Lens modes

- Photo: manual says "3 lens options" but its table lists Wide (16-34 mm) and Linear (19-39 mm). The third is not shown; treat the photo list as Wide and Linear until a device check.
- Video: HyperView (16 mm), SuperView (16 mm), Wide (16-34 mm), Linear + Horizon Lock/Leveling (19-33 mm), Linear (19-39 mm); Narrow appears in high-frame-rate presets. No "Max SuperView" on this camera.
- Time lapse table: TimeWarp (5.3K, 4K, 1080p): HyperView, SuperView, Wide, Linear, Linear + Horizon Lock. Star Trails, Light Painting, Vehicle Light Trails: Wide. Time Lapse Video and Night Lapse Video: Wide, Linear.
- GoPro's product page spec list: 27 MP photos [V <https://gopro.com/en/us/shop/cameras/learn/hero13black/CHDHX-131-master.html>].

### 2c. HB-series lens mods (HERO13 Black only)

- Macro Lens Mod: rotating focus ring, 4.33 in (11 cm) to 2.46 ft (75 cm), focus peaking, "4x closer" than the stock lens. [V <https://gopro.com/en/us/shop/mounts-accessories/macro-lens-mod/AEWAL-021.html>]
- Ultra Wide Lens Mod: FOV up to 177 degrees (36% wider, 48% taller), 1:1 aspect, Horizon Lock on all lenses, vertical capture. [V <https://gopro.com/en/us/shop/mounts-accessories/ultra-wide-lens-mod/AEWAL-001.html>]
- Anamorphic Lens Mod: 21:9 ultra-wide cinematic look, horizontal flares, in-camera de-squeeze. [V <https://gopro.com/en/us/shop/mounts-accessories/anamorphic-lens-mod/AEWAL-011.html>]
- ND Filter 4-Pack: ND4, ND8, ND16, ND32; camera detects the filter and enters Auto Cinematic video mode. [V <https://gopro.com/en/us/shop/mounts-accessories/smart-motion-blur-nd-filter/AENDF-001.html>]
- All mods are auto-detected. The manual's settings list includes "Lens Mod Mode". Which of the mods apply to stills (as opposed to video presets) is not stated in the pages read: unsettled, test.

### 2d. Lens mode in metadata

- GPMF spec: "there is a lot of metadata in the header for all MP4 and JPG files"; `VFOV` = "L - Linear, W - wide, S - Superview, H - Hyperview"; `ZFOV` = diagonal FOV in degrees; `PRJT` = lens projection; `DZOM`/`DZMX` = digital zoom. [V <https://github.com/gopro/gpmf-parser/blob/main/README.md>]
- ExifTool: GPMF tags are extracted from "the APP6 'GoPro' segment of JPEG files"; table includes `VFOV`, `ZFOV`, `LensProjection`. [V <https://exiftool.org/TagNames/GoPro.html>]
- Not confirmed: that a HERO13 still (JPG or GPR) carries `VFOV` and `ZFOV`. Unsettled.

### 2e. Stock minimum focus

Not given in the manual text searched (no focus-distance entry) nor on the product pages. Unsettled; measure.

## 3. Datasets

### 3a. Mip-NeRF 360

The project page lists `360_v2.zip` (12.5 GB) and `360_extra_scenes.zip` and states no licence or terms. [V <https://jonbarron.info/mipnerf360/>] The code repository `google-research/multinerf` is Apache-2.0 [V GitHub API]. The zip's contents (any LICENSE or README inside) were not inspected: a partial download was started and cancelled. Unsettled.

### 3b. COLMAP datasets

- Counts from the COLMAP docs: Gerrard Hall 100, Graham Hall 1273, Person Hall 330, South Building 128 (UNC Chapel Hill; "same camera", wide-angle lens). [V <https://github.com/colmap/colmap/blob/main/doc/datasets.rst>; <https://demuc.de/colmap/datasets/>]
- South Building: downloaded and counted, 128 images, 3072x2304, Panasonic DMC-TZ3 (EXIF). [V]
- Licence: none stated on either page. Resolution of Gerrard, Person and Graham not checked (an attempt to read the first JPEG from the multipart zips returned nothing).
- Downloads (all `https://github.com/colmap/colmap/releases/download/3.11.1/`): `south-building.zip` (419 MB), `gerrard-hall.zip` (1.0 GB), `person-hall.z01` + `person-hall.zip`, `graham-hall.z01`-`z05` + `graham-hall.zip` (zip 1.29 GB; `z01` 2.10 GB; if each part is that size, about 11.8 GB in total, only `z01` measured). The page tells to recombine multipart archives with `zip -FF`. [V]

### 3c. ETH3D

- README of the tool: `ETH3DMultiViewEvaluation --reconstruction_ply_path ... --ground_truth_mlp_path ... --tolerances 0.01,0.02,0.05,0.1,0.2,0.5` (metres), i.e. 1, 2, 5, 10, 20, 50 cm. [V <https://github.com/ETH3D/multi-view-evaluation>] The CVPR 2017 paper evaluates "distance thresholds from 1cm to 50cm" and reports category tables at 2 cm [V <https://www.eth3d.net/data/schoeps2017cvpr.pdf>]. The benchmark page shows F1 at 1 and 2 cm and accuracy and completeness at 1, 2, 5, 10, 20, 50 cm [V <https://www.eth3d.net/high_res_multi_view>].
- Licence: `LICENSE.txt` reads "This program is released under the BSD license", copyright 2017 Thomas Schoeps, Johannes L. Schoenberger. [V raw file] Dependencies: Boost.Filesystem, Eigen, PCL [V <https://www.eth3d.net/documentation>]. Last push 2023-04-11.

### 3d. SQUID

Berman, Levy, Avidan, Treibitz: 57 stereo pairs from four sites (Katzaa 15, Satil 8, Nachsholim 13, Mikhmoret 21). The page lists RAW images, TIF files, camera calibration files and distance maps. [V <https://csms.haifa.ac.il/profiles/tTreibitz/datasets/ambient_forwardlooking/index.html>] The TPAMI paper: "identical waterproof color charts (from DGK Color Tools)" at different distances, a calibration checkerboard on the rig, Nikon D810 with 35 mm lens in a dome port, natural light only. [V <https://arxiv.org/abs/1811.01343>, full text read] Licence: the page asks for citation; no licence text. Chart model and patch count: unsettled.

### 3e. AquaMVS

`McGrathLab/AquaMVS`: MIT, copyright 2026 tlancaster6. [V <https://github.com/McGrathLab/AquaMVS>; PyPI metadata `license_expression: MIT`]

## 4. Refractive COLMAP

- Fork of COLMAP on GitLab (branch `underwater`), mirrored at <https://github.com/MDSKiel/colmap_underwater> (default branch `underwater`, last push 2024-10-29). Licence: `COPYING.txt` is COLMAP's new BSD text ("Copyright (c) 2023, ETH Zurich and UNC Chapel Hill") [V <https://cau-git.rz.uni-kiel.de/inf-ag-koeser/colmap_underwater/-/raw/underwater/COPYING.txt>]. GitHub reports NOASSERTION because of the file name.
- README: features are flat-port and dome-port refractive camera models, refractive SfM, bundle adjustment with pose priors; "Building COLMAP Underwater from source is exactly the same as building the original COLMAP"; cite She, Seegraeber, Nakath, Koeser, "Refractive COLMAP: Refractive Structure-from-Motion Revisited", IROS 2024. Mentions a calibration toolbox `calibmar`. [V <https://cau-git.rz.uni-kiel.de/inf-ag-koeser/colmap_underwater/-/raw/underwater/README.md>]
- Upstream: `src/colmap/sensor/models.h` on COLMAP main has no refractive or flat-port model, and the camera-model doc page has no match for "refract" or "flat port". [V raw files today] I did not check upstream pull requests (GitHub code search needs authentication).
- pycolmap: the mirror's top-level tree has no python or pycolmap directory and the README does not mention pycolmap. I did not find bindings. arXiv 2403.08640 not re-read today.

## 5. Akkaynak and Treibitz

- "A Revised Underwater Image Formation Model", Derya Akkaynak and Tali Treibitz, CVPR 2018, pp. 6723-6732. Abstract: "the wideband coefficients that govern backscatter are different than those that govern direct transmission". [V <https://openaccess.thecvf.com/content_cvpr_2018/html/Akkaynak_A_Revised_Underwater_CVPR_2018_paper.html>]
- "Sea-Thru: A Method for Removing Water From Underwater Images", CVPR 2019, pp. 1682-1691. Abstract states both findings: the signal attenuation coefficient "depends on object range and reflectance", and the backscatter coefficient "differs from the signal attenuation coefficient"; the method uses RGBD images. [V <https://openaccess.thecvf.com/content_CVPR_2019/html/Akkaynak_Sea-Thru_A_Method_for_Removing_Water_From_Underwater_Images_CVPR_2019_paper.html>]
- Correction to the working claim: the 2018 abstract attributes the earlier range-dependence finding to prior work ("we recently showed"); the 2018 paper's own new result is the backscatter finding. The earlier work is likely the CVPR 2017 attenuation-coefficient paper [U, not read].

## 6. COLMAP dense

- Current release: COLMAP 4.2.1 (09/29/2026). [V <https://github.com/colmap/colmap/blob/main/CHANGELOG.rst>; GitHub releases API]
- FAQ: "If you do not have a CUDA-enabled GPU but some other GPU, you can use all COLMAP functionality except the dense reconstruction part." [V <https://github.com/colmap/colmap/blob/main/doc/faq.rst>]
- Install doc: CUDA build, or HIP/ROCm build (`-DCUDA_ENABLED=OFF -DHIP_ENABLED=ON`); "The HIP backend accelerates dense reconstruction (`patch_match_stereo`) and GPU SIFT". Changelog: "Added ROCm/HIP acceleration for `patch_match_stereo`... CUDA and HIP builds are mutually exclusive." [V <https://github.com/colmap/colmap/blob/main/doc/install.rst>; CHANGELOG.rst]
- No CPU or Metal path for `patch_match_stereo` in install, FAQ, tutorial, CLI docs or changelog (grep for "metal" returns nothing). `colmap.github.io/dense.html` is a script shell and did not render; the repository `doc/*.rst` sources were read instead.

## 7. pycolmap

- Current: 4.2.1 on PyPI, Python 3.10+. Wheels: `manylinux_2_28_x86_64`, `macosx_14_0_arm64`, `win_amd64` for cp310-cp314. `pycolmap-cuda12` 4.2.1: `manylinux_2_28_x86_64` only. [V <https://pypi.org/project/pycolmap/>, PyPI JSON]
- Docs: wheels via pip; CUDA wheels only for Linux x86_64 ("for now"); source build = install COLMAP from source, then `python -m pip install .` on Linux and macOS. [V <https://github.com/colmap/colmap/blob/main/doc/pycolmap/index.rst>] The docs do not mention aarch64 or CUDA on aarch64 specifically; the generic COLMAP CUDA build applies. Unsettled for an aarch64 source build until tried.
- conda-forge `pycolmap` 4.2.1: linux-aarch64 has cpu, cuda_129 and cuda_134 builds (GPL and LGPL variants); osx-64 has CPU builds only; osx-arm64, linux-64, win-64 also present. [V <https://anaconda.org/conda-forge/pycolmap>, anaconda API listing]

## Still unsettled

1. Safari upload of HEIC and ProRAW DNG from the photo picker for each `accept` variant: test page on the iPhone 15 Pro.
2. iPhone 15 Pro `captureHighResolutionFrame` pixel size (expected 12 MP, not documented), default `capturedImage` size, and whether `ARCamera.intrinsics` varies frame to frame: log on the device.
3. Whether Macro Control is on by default in Settings on the owner's phone.
4. HERO13 stills: third photo digital lens in the manual's "3 options"; whether `VFOV`, `ZFOV` and `PRJT` are written into HERO13 JPG and GPR; whether lens mods work for stills; stock minimum focus distance: shoot and run `exiftool -G1 -a -u -ee`.
5. Mip-NeRF 360 data licence: inspect the zip contents or ask the authors.
6. Resolution and licence of Gerrard Hall, Person Hall, Graham Hall: unpack one image from each.
7. SQUID chart model and licence terms.
8. Refractive COLMAP: upstream PRs, and any Python bindings beyond the mirror's top-level tree; arXiv 2403.08640 not re-read.
9. pycolmap source build with CUDA on Linux aarch64: documented only generically; conda-forge builds exist and are the lower-risk route. COLMAP HIP on gfx1151 untested.
10. Akkaynak 2017 attenuation-coefficient paper (title and venue) was not read.
