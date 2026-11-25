# Public datasets

Until the owner shoots their own sets, development and the Step 0 prototypes
([RC-brief §5](../concept/RC-brief.md)) run on public datasets. This page lists which exist, what ground truth
each carries, what the licence lets the project do, and which prototype each fits. The question it answers: which
sets can we reuse easily, and which carry a wall.

As of 2026-11-24.

Legend:

- **[V url]** read today on the dataset's own page, repo, Zenodo record or licence file, or measured today with
  an HTTP HEAD request or the Zenodo API. Page reads went through a summarising fetch tool, so a quoted licence
  name is the tool's reading of the page; re-read the licence text before any redistribution.
- **[U]** not read today; from memory or from a search snippet. Verify before relying on it.
- "unknown" means neither the page nor today's checks gave the value.
- No dataset was downloaded. Sizes come from page text or HEAD requests.

## Summary table

| Dataset | Domain | Images (count x res) | Ground truth | Size | Licence | Commercial OK? | Friction | Fits |
|---|---|---|---|---|---|---|---|---|
| ETH3D high-res multi-view | Indoor/outdoor SfM+MVS | 15 train scenes 420 images, 12 test scenes 445; 6048x4032 DSLR (Nikon D3X), NEF RAW included | Faro Focus X 330 laser scans, GT poses | 4.7 GB JPG, 5.9 GB undistorted, 13.0 GB NEF RAW, 1.9 GB scan eval (training) | CC BY-NC-SA 4.0 | No | None for download; NC and SA | P1, dense/mesh vs laser GT, P7b (RAW) |
| COLMAP samples (South Building, Gerrard Hall, Person Hall, Graham Hall) | Buildings, SfM | 128 / 100 / 330 / 1,273; resolution unknown | None published | unknown | not stated on page | unknown | Links not resolved today | P1, P3 (Graham Hall) |
| Tanks and Temples | Large scenes, SfM+MVS | 4K-video frames, 19 scenes | Laser scans (training scenes only) | unknown | CC BY 4.0 text plus non-commercial grant | No | Google Drive; no registration | P1, splat quality |
| Mip-NeRF 360 | Unbounded scenes, radiance fields | 9 scenes; count and res unknown (read today: no) | None; COLMAP poses | 12.5 GB (360_v2.zip) | unknown | unknown | Direct link | Splat quality |
| DTU MVS | Objects on turntable rig | 49 or 64 images x 1600x1200, 124 scans | Structured-light point clouds, STL | 6.3 GB sample set up to 136 GB | "Freely available for research use", cite paper | unknown | Large | Dense accuracy on objects |
| ScanNet++ | Indoor | 33 MP DSLR, iPhone RGB-D, 1000+ scenes | Sub-millimetre laser scans, registered poses | unknown | ScanNet++ Terms of Use (PDF after signup) | unknown | Account plus approval, token | P9 room |
| ARKitScenes | Indoor, iPhone/iPad LiDAR | 5,047 captures, 1,661 scenes | ARKit poses, LiDAR mesh | unknown | Apple custom licence, non-commercial | No | Script download; custom licence | P4, P9, P10 pose priors |
| TUM RGB-D | Indoor RGB-D SLAM | 640x480 Kinect, 30 Hz | Motion-capture trajectories | per sequence | CC BY 4.0 | Yes | None | Pose-prior plumbing only |
| CO3Dv2 | Objects, video | many sequences; res unknown | COLMAP-derived poses | 5.5 TB full, 8.9 GB single-sequence subset | CC BY-NC 4.0 (codebase; data terms unknown) | No | Huge | Not a fit |
| ODM sample sets (odm_data_*) | Aerial drone | e.g. aukerman 77 entries in images/, seneca 167, langley 200, benchmark 50 | None | per repo, unknown | CC0-1.0 (aukerman, seneca checked via API) | Yes | None | P3 large-set (small), aerial |
| Sea-thru (D1-D5) | Underwater, colour | ~1,100 linear PNG at 0.3x size, 5 sites | Range maps (from Metashape SfM), colour charts | 38.4 GB | CC BY-NC-SA 4.0 | No | Kaggle/Hugging Face; RAW only on request | P8 colour, range-dependent attenuation |
| SQUID | Underwater stereo | 57 stereo pairs, 4 Israeli sites | Distance maps, calibration | 45.8 GB | CC BY-NC-SA 4.0 | No | Zenodo, direct | P8 colour and scale checks |
| SeaThru-NeRF scenes | Underwater, radiance fields | 4 scenes; count and res unknown | COLMAP poses | unknown | Repo code Apache-2.0; data licence unknown | unknown | Google Drive | P8 splat quality |
| Reefs4D | Coral reef 3D models | 21 models, 7 reefs, 3 time points | The models themselves (PLY) | PLY files of 14-290 MB each | CC BY-NC (Zenodo id cc-nc) | No | No source images seen in file list | Not a fit for registration |
| Submerged3D | Deep-sea wrecks | 4 scenes x 20 images, 720p | None stated | 18.5 MB listed, 5.4 GB stated | CC BY 4.0 | Yes | Zenodo | Smoke test only |
| AquaMVS Example Dataset 2 | Lab underwater MVS | 13-camera rig, 10 frames each | ChArUco board geometry | 6.2 GB zip (8.6 GB) | CC BY 4.0 | Yes | Zenodo | P8 refraction and MVS accuracy |

Rows without a [V] in the section below are [U].

## General SfM and MVS

### ETH3D high-res multi-view

- What: 15 training scenes (420 images) and 12 test scenes (445 images), indoor and outdoor, DSLR.
  [V https://www.eth3d.net/datasets]
- Camera: Nikon D3X, 6048x4032, raw NEF, JPEG and undistorted JPEG all provided; original camera model
  THIN_PRISM_FISHEYE. [V https://www.eth3d.net/documentation]
- Ground truth: Faro Focus X 330 laser scans with colour, three versions (raw, clean, eval); poses in COLMAP
  text format. Stated accuracy: unknown, the documentation page points to the paper. [V
  https://www.eth3d.net/documentation]
- Sizes (HEAD, 2026-11-24): `multi_view_training_dslr_jpg.7z` 5.05 GB; `..._undistorted.7z` 5.89 GB;
  `..._raw.7z` 13.04 GB; `..._scan_eval.7z` 1.92 GB. [V https://www.eth3d.net/data/]
- Licence: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International. [V https://www.eth3d.net/]
- Registration: none seen for downloads (direct HEAD requests succeed); the Submit link needs a login.
- Fits: P1 (GLOMAP vs COLMAP registration error against GT poses), dense and mesh accuracy against laser GT,
  P7b RAW-to-set (the NEF files are the only public RAW set here with laser GT).
- Limit: only 15 training scenes; the largest is a few dozen to a hundred images; not a P3 distribution test.

### COLMAP sample datasets

- South Building (128), Gerrard Hall (100), Person Hall (330), Graham Hall (1,273 images, interior and
  exterior). Resolution, size, licence and ground truth are not stated on the page. [V
  https://colmap.github.io/datasets.html]
- Download host is https://demuc.de/colmap/datasets/; the `*.zip` paths I guessed returned 404 today, so the
  file names are unknown. [V]
- Fits: P1 smoke runs, Graham Hall as a mid-size (1,000+) registration set for P3. No GT, so registration rate and
  reprojection error only.
- COLMAP software licence (BSD-3) is not the data licence; do not assume the data is BSD. [U]

### Tanks and Temples

- 8 intermediate, 5 advanced, 6 training scenes; images are uniformly sampled frames from 4K video at 29.97 fps;
  training scenes carry laser-scan GT, COLMAP results, camera poses and alignment matrices. Download by Google Drive
  links or a Python downloader with MD5 check; no registration required. [V https://www.tanksandtemples.org/download/]
- Licence page names CC BY 4.0, but its licence grant limits use to "non-commercial scientific research" and bars
  making the data available to third parties without written permission. The two clauses conflict; treat the data
  as non-commercial, no redistribution. [V https://www.tanksandtemples.org/license/]
- Fits: P1 and splat quality (the 3DGS paper uses these scenes). Video frames, not RAW stills.

### DTU MVS

- 124 scenes, 49 or 64 images each at 1600x1200, seven lighting conditions; structured-light point clouds and STL
  reference models as GT. Downloads: SampleSet 6.3 GB, Points 6.3 GB, Points_MVS 45 GB, Surfaces 28 GB, Cleaned
  136 GB, Rectified 123 GB. [V https://roboimagedata.compute.dtu.dk/?page_id=36]
- Terms: "freely available for research use", citation required. No named licence on the page. Commercial use
  unknown. [V same page]
- Fits: object-scale dense accuracy. Controlled robot-arm rig, so it does not stress registration.

### Not read today

BlendedMVS, Strecha fountain/herzjesu, 1DSfM, Photo Tourism, IMC PhotoTourism, Replica, EuRoC: the two URLs I tried
for 1DSfM and the ETH local-feature page returned 404, and I did not search the rest. [U] Photo Tourism and
1DSfM are internet photos of landmarks with mixed copyright; assume research-only until read.

## Radiance fields

### Mip-NeRF 360

- The scenes ship as `360_v2.zip`, 12,535,427,936 bytes (HEAD 2026-11-24), last modified 2022-03-28. [V
  https://storage.googleapis.com/gresearch/refraw360/360_v2.zip]
- The project page read today did not state the licence, per-scene image counts or resolution. The multinerf repo
  is Apache-2.0 and archived 2025-02-11; that licence covers code, not the photos. [V
  https://github.com/google-research/multinerf]
- Fits: splat quality on held-out views. Unknown data licence means local development only.

### Not read today

NeRF synthetic (Blender), Deep Blending: [U]. Both are synthetic or research-released; check licences.

## Indoor, robotics and pose priors

### ScanNet++

- 1000+ indoor scenes; sub-millimetre laser scans, 33 MP registered DSLR images, iPhone RGB-D streams, 360 degree
  RGB-D panoramas added October 2025. [V https://scannetpp.mlsg.cit.tum.de/scannetpp/]
- Access: create an account, submit an application, wait for approval, receive a personal download token. Terms of
  Use PDF shown after signup; commercial terms not read. [V same page]
- Fits: P9 (room), DSLR vs iPhone comparison, P4 pose priors. Gated; use only after the owner reads the Terms.

### ARKitScenes

- 5,047 captures of 1,661 scenes, iPhone/iPad LiDAR RGB-D with ARKit poses and LiDAR surface reconstruction;
  high-resolution data for 2,257 captures across 841 scenes. Download through `download_data.py`. [V
  https://github.com/apple/ARKitScenes]
- LICENSE is an Apple custom licence granting a "personal, non-commercial" licence "for non-commercial purposes
  only" (the text read covers the Apple Software; it is the only licence in the repo). Questions go to
  ARKitScenes-license@group.apple.com. [V https://raw.githubusercontent.com/apple/ARKitScenes/main/LICENSE]
- Fits: the closest public analogue of the owner's iPhone capture app (P10) and ARKit pose priors (P4, P9).
  Non-commercial: development use only.

### TUM RGB-D

- Kinect 640x480 at 30 Hz, motion-capture ground-truth trajectories (8 high-speed cameras, 100 Hz). CC BY 4.0;
  code BSD-2-Clause; commercial use permitted. [V https://cvg.cit.tum.de/data/datasets/rgbd-dataset]
- Fits: only the pose-prior and depth plumbing. Not photogrammetry quality imagery.

### Not read today

Replica, EuRoC: [U].

## Objects

- DTU: see above.
- CO3Dv2: 5.5 TB full set, 8.9 GB single-sequence subset, 20 GB download chunks; codebase CC BY-NC 4.0. [V
  https://github.com/facebookresearch/co3d] Not a fit: size, NC, phone-quality video.
- OmniObject3D, Google Scanned Objects, Stanford 3D Scanning Repository: not read today. [U]

## Aerial and drone

### OpenDroneMap sample sets

- The OpenDroneMap GitHub organisation hosts at least 18 `odm_data_*` repos (apt, benchmark, caliterra, copr, glam,
  langley, pacifica, seneca, lewis, bellus, rv_nir, waterbury, toledo, aukerman, zoo, garfield_msp,
  helenenschacht, monterey_road_bend). [V https://api.github.com/orgs/OpenDroneMap/repos]
- Aukerman, Seneca: licence CC0-1.0. [V repo licence API] `images/` entries: aukerman 77, seneca 167, langley 200,
  benchmark 50 (counts of directory entries via the GitHub API, not verified as image counts). Camera, resolution
  and size: unknown. No ground truth.
- Fits: aerial registration smoke tests and clone-and-go P3 trials at 100-200 images; too small for P3's 1,000+.
- Not read: UrbanScene3D, DJI samples. [U]

## Underwater

Public underwater sets with usable ground truth and a permissive licence are scarce. The best-known colour sets are
non-commercial, and the RAW files are not in the public download.

### Sea-thru (Akkaynak and Treibitz)

- Five sites D1-D5, about 1,100 images, with range maps in metres (from Metashape SfM); zero depth means no value.
  [V https://huggingface.co/datasets/bhowmikabhimanyu/seathru-dataset]
- Images are linear PNG at 0.3x original size. The original RAW files are not in the download; the authors say to
  contact them. [V same page]
- 38.4 GB; licence on the Hugging Face card is CC-BY-NC-SA-4.0. The Haifa page links Kaggle and says "RAW images"
  are included, which conflicts with the card; resolve by reading the Kaggle page. [V
  https://www.viseaon.haifa.ac.il/datasets]
- Original resolution, camera model, colour-chart presence: not read; the colour charts claim is [U].
- Fits: P8 colour against a reference target, range-dependent attenuation estimate. Non-commercial: development
  use only.

### SQUID

- 57 stereo pairs, four sites in Israel (Red Sea: Katzaa coral reef 10-15 m, Satil wreck 20-30 m; Mediterranean:
  Michmoret, Nachsolim), depths 3-30 m. RAW, TIF, calibration and distance maps included. [V
  https://zenodo.org/records/5744037]
- Zips: Katzaa 12.1 GB, Michmoret 16.9 GB, Nachsolim 10.5 GB, Satil 6.2 GB, 45.8 GB total. Licence CC-BY-NC-SA 4.0.
  [V same page]
- Satil, read 2026-11-25 (RC-P12): Nikon NEFs of 7380 x 4928; the TIFs are sRGB-encoded (not linear) and
  clip red to zero on 78-99.9% of pixels, so colour work needs the RAW. Chart annotations (corners and patch
  centres) for right-camera images ship with the evaluation code
  (`underwater-dataset-evaluation-undisorted-params.zip` on the project page), not in the dataset zips; they sit
  a few pixels off the published undistorted TIFs. The calibration is a MATLAB `stereoParameters` object,
  unreadable outside MATLAB. [V RC-P12 README]
- Only stereo pairs, so not a full SfM set; the distance maps are the value.
- Fits: P8 scale and colour checks, RAW decode test for P7b-style handling underwater.

### SeaThru-NeRF scenes

- Four scenes (IUI3 Red Sea, Curacao, Japanese Gardens Red Sea, Panama) per a search snippet; the repo ships
  `images_wb/`, `sparse/0/` and `poses_bounds.npy`; Google Drive link; photo credit Matan Yuval. Image counts,
  resolution, RAW: not stated. Repo code Apache-2.0; the data licence is not stated on the page read. [V
  https://github.com/deborahLevy130/seathru_NeRF]
- Images are white-balanced and COLMAP poses are included, so they test splat quality, not registration.
- Fits: P8 splat quality on held-out views; the same set WaterSplatting evaluates on. [U for the snippet claim]

### Other underwater sets found

- AquaMVS Example Dataset 2: 13-camera underwater rig, 10 synchronised frames per camera, independent ChArUco
  board ground truth, calibration including water-surface depth; 6.2 GB zip (8.6 GB uncompressed); CC BY 4.0;
  published 2026-07-02. Lab geometry, not a dive site. [V https://zenodo.org/records/21134749]
- Submerged3D: 4 deep-sea wreck scenes x 20 RGB images at 720p; no ground truth stated; CC BY 4.0. Too small for a
  benchmark. [V https://zenodo.org/records/15482420]
- Reefs4D: 21 PLY models of seven coral reefs at three time points; Zenodo licence id `cc-nc`; the file list I saw
  holds PLY files only, no source images. [V https://zenodo.org/api/records/7879992]
- RapidBenthos (12 photogrammetric models and underlying images, 5-15 m, coral reefs), a Zenodo record of an
  Innsbruck synthetic two-media set, and a very-shallow-water coral set on Figshare surfaced in a search but were
  not opened. [U]
- FLSea-VI (12 forward-looking visual-inertial sets, under 10 m, Kaggle): listed on the Haifa page; licence and
  size not stated. [V https://www.viseaon.haifa.ac.il/datasets]

### Not found or not checked

No public underwater dataset with laser-scan or survey-grade GT on a full dive-scale 3D scene was found. Not
checked: AQUALOC, the Underwater Caves dataset, VAROS, 100 Island Challenge, NOAA reef sets, TagLab sample data,
wreck sets on Sketchfab. [U] The Eiffel Tower deep-sea set was not found.

## Recommended starter set

| Need | Dataset | Licence | Why |
|---|---|---|---|
| RC-P1 baseline registration (GLOMAP vs COLMAP) | ETH3D high-res training scenes (JPG, 4.7 GB) | CC BY-NC-SA 4.0 | GT poses and laser scans, no registration, direct link |
| Dense and mesh accuracy vs laser GT; RAW (P7b) | ETH3D scan_eval (1.9 GB) plus NEF set (13.0 GB) | CC BY-NC-SA 4.0 | The only RAW-plus-laser public set found |
| Splat quality, held-out views | Mip-NeRF 360 (12.5 GB) | unknown (code Apache-2.0) | Standard splat benchmark; no GT, so read the licence before any release |
| ARKit-style pose priors (P4, P9, P10) | ARKitScenes | Apple custom, non-commercial | Closest analogue to the owner's iPhone capture; gated by licence terms; ScanNet++ is the alternative but needs approval |
| Large set for P3 (1,000+) | COLMAP Graham Hall (1,273 images) | not stated | Only 1,000+ set found; resolution unknown; no GT. Not high-res RAW, so it only exercises scale in image count; real P3 needs the owner's D850 set |
| Underwater P8 | SQUID (RAW, distance maps, 45.8 GB) plus AquaMVS Example 2 (6.2 GB) | CC-BY-NC-SA 4.0 and CC BY 4.0 | SQUID gives RAW and distances; AquaMVS gives refraction-aware GT under a permissive licence; SeaThru-NeRF scenes (Drive) for splat quality |

The best fits are restrictive: ETH3D, SQUID, Sea-thru and ARKitScenes all forbid commercial use. Only TUM RGB-D,
AquaMVS, Submerged3D and the CC0 ODM sets are permissive, and none of them is a strong benchmark.

## Reuse rules

- Local development and prototypes: allowed under every licence listed, including non-commercial ones.
- Published benchmark results (numbers, plots, no data): allowed with citation; ETH3D, SQUID and Sea-thru require
  attribution and share-alike for adaptations.
- Redistribute the data (including in this repo or on a shared artefact store): not under CC BY-NC-SA without
  matching licence and attribution; not at all for Tanks and Temples (written permission required), ARKitScenes
  (check the Apple terms), DTU, ScanNet++ (Terms of Use). Fetch from the source; commit only the download script.
- Ship derived models (weights trained on the data, a product that embeds results): not for any non-commercial
  set. Treat a model trained or tuned on ETH3D, SQUID, Sea-thru, Tanks and Temples, ARKitScenes or CO3D as
  non-commercial unless counsel says otherwise.
- Commercial-safe data: TUM RGB-D (CC BY 4.0), AquaMVS (CC BY 4.0), Submerged3D (CC BY 4.0), ODM CC0 sets.
- Never share an ScanNet++ download token or copy approved data to other machines without reading the Terms.

## Not verified

- Image resolution and size: COLMAP samples, Mip-NeRF 360 per scene, SeaThru-NeRF, ODM sets, Sea-thru original
  resolution, ScanNet++ and ARKitScenes sizes.
- Licences not read: Mip-NeRF 360 data, SeaThru-NeRF data, ScanNet++ Terms of Use text, COLMAP sample data, DTU
  (no named licence), CO3D data terms (only the codebase licence read).
- Datasets not opened at all: BlendedMVS, Strecha, 1DSfM, Photo Tourism, IMC, Replica, EuRoC, NeRF synthetic, Deep
  Blending, OmniObject3D, Google Scanned Objects, Stanford scans, UrbanScene3D, DJI samples, AQUALOC, Underwater
  Caves, VAROS, 100 Island Challenge, NOAA, TagLab, RapidBenthos, Sketchfab wrecks.
- Whether Sea-thru RAW is on Kaggle (the Haifa page says yes, the Hugging Face card says no).
- ETH3D laser accuracy figure, ETH3D registration wall beyond the download links I probed.
- GT accuracy of ScanNet++, ARKitScenes and DTU beyond the descriptions above.
