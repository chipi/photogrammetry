# RC-P10 — A room from inside

**Proves:** That an interior registers as one model, and what LiDAR and ARKit add. See the
[brief](../../docs/concept/RC-brief.md), RC-P10.

**Proven when:** With poses and depth, the room gives one metric model (TSDF mesh plus splat) whose
wall lengths match the reference within 2% or 2 cm, whichever is larger; photos-only, the room
either registers as one model or the engine reports its separate components and where the links
are missing.

**Result (2026-11-25): partly met.**
- **With poses and depth:** the TSDF mesh meets the wall-length limit on 385 of 389 wall-to-wall
  distances, pooled over five RANSAC seeds and five scenes.
  - Four seeds pass every distance. The fifth fails 4 of 91, on two wall planes 1.05–1.24 m from
    their partners, by 2.6–3.1 cm against the 2 cm limit.
  - One scene has a scorable pair in only three of the five seeds.
- **Splat:** not trained yet. Its input is ready and needs a daytime GPU window.
- **Photos only:** one scene registers as one component, 179 of 218 frames. The other four split
  into 2–4 components. This prototype reports each break with the frames on either side and where
  in the room it falls; the engine (`recon`) has no such report yet.

## Data

Five ARKitScenes Training videos, the ones RC-P8 used (one per visit, picked by RC-P8's
`select_arkit.py`). All five are in the depth-upsampling subset, so each has `highres_depth`:

- **`highres_depth`:** the Faro laser scanner's mesh, rendered into 116–225 frames per video at
  1920x1440 by Apple.
- **`lowres_depth`:** the iPhone's LiDAR at 256x192 and 60 Hz, with `confidence`.
- **`lowres_wide.traj`:** ARKit's poses at 10 Hz.
- **`vga_wide`:** colour at 640x480 and 30 Hz.

Downloaded only the assets listed: about 340 MB of `highres_depth` and `confidence` from Apple,
the rest copied from RC-P8's DGX cache. The Faro scans themselves (58 GB for the five visits) are
not downloaded.

**Frame.** ARKitScenes' world frame is z-up, not ARKit's native y-up. `walls` takes up from the
camera (the mean image-up direction over the video, which the "sky direction Up" filter makes
meaningful). It then snaps up to the normal of the largest plane within 30° of it. The floor
normal lies 2.7–11.4° from the camera's up in the five videos. The first `walls` run assumed y-up;
the floor check failed on 42444821 and the run was discarded.

## What runs

| Step | Command | What it does |
|---|---|---|
| align | `uv run python room.py align` | Compares each laser depth frame with the LiDAR depth of the same timestamp, at the LiDAR's pixels (laser intrinsics: `lowres_wide` scaled by 7.5) |
| fuse | `uv run python room.py fuse` | TSDF of every 2nd LiDAR frame (30 Hz), confidence 2 only, 2 cm voxels, 8 cm truncation, 4 m depth limit, with the ARKit pose interpolated at each frame's timestamp (RC-P8's interpolation); colour from the nearest `vga_wide` frame. Writes `tsdf.ply` |
| reference | `uv run python room.py reference` | The laser depth frames back-projected with the same poses, every 4th pixel, 1 cm voxel grid. Writes `reference.ply` |
| walls | `uv run python room.py walls` | Wall-to-wall distances, laser against TSDF (below) |
| components | `uv run --project ../RC-P1-registration python components.py` | Photos-only components from RC-P8's `none` runs (below) |
| splat_prep | `uv run --project ../RC-P1-registration python splat_prep.py` | COLMAP model of RC-P8's posed frames (every 12th `vga_wide` frame) with 3-D points seeded from the TSDF vertices |
| run_splat.sh | on the DGX, in a `free` window | gsplat's trainer with `--no-normalize-world-space`, so the splat stays in ARKit's frame in metres |
| summarize | `uv run python summarize.py` | The tables below |

Outputs go to `$RECCE_DATA_DIR/runs/p10/`. Wall time on the workstation (32 threads):
- `fuse`: 57 s for the five videos.
- `reference`: 41 s.
- `walls`: 34 s per seed.

**Open3D.** Open3D 0.20's legacy `ScalableTSDFVolume` returned no surface: 0 points after one
frame at the identity pose, where `UniformTSDFVolume` on the same frame gave 15,159. The cause is
not found. `fuse` uses the tensor `VoxelBlockGrid` instead.

## Wall lengths

**The measure.**
- **Walls:** up to 40 planes are found in the laser cloud by repeated RANSAC (2 cm). A wall is a
  vertical plane (within 5°) whose points span at least 1.8 m in height and 0.8 m along it.
- **Refit in the TSDF:** each wall's plane is refitted in points sampled from the TSDF mesh, inside
  the wall's footprint and within 5 cm of its plane, then again within 2 cm.
- **Distances:** every two parallel walls (within 5°) at least 1 m apart give one distance. It is
  measured at the laser walls' centroids, for both clouds.

These are wall-to-wall distances, not the sides of one box room. ARKitScenes videos cross doorways
and corridors, and an "outermost walls" rule picked the two faces of one interior wall on 42444873.
That rule was dropped after it was seen to fail, before any distance was compared.

**Seeds.** Open3D's RANSAC draws at random, so the planes found, and with them the pairs, change
from run to run. `walls --seed N` seeds it; a seeded run is byte-for-byte repeatable (checked on
seed 0). Seeds 0–4 are reported. The first, unseeded runs are discarded. One of them failed a pair
that no seeded run produces (finding 3).

Laser against LiDAR, per frame (`align`):

| Video | Laser frames | LiDAR minus laser depth, median abs / signed |
|---|---|---|
| 42444515 | 116 | 1.7 cm / −1.61% |
| 42444793 | 202 | 1.5 cm / −1.49% |
| 42444821 | 153 | 2.0 cm / −1.37% |
| 42444858 | 151 | 2.3 cm / −1.56% |
| 42444873 | 225 | 1.4 cm / −1.09% |

Distances within the limit, of those scored, per seed:

| Video | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Seed 4 |
|---|---|---|---|---|---|
| 42444515 | 4/4 | 4/4 | 9/9 | 4/4 | 7/7 |
| 42444793 | 19/19 | 29/29 | 24/24 | 18/18 | 16/18 |
| 42444821 | 28/28 | 32/32 | 29/29 | 38/38 | 37/37 |
| 42444858 | 11/11 | 17/17 | 15/15 | 14/14 | 27/29 |
| 42444873 | 0/0 | 1/1 | 1/1 | 1/1 | 0/0 |

| Seed | Within / scored | Failed pairs | Error, min / median / max | Median abs error | Wall RMS, laser / TSDF (mm) |
|---|---|---|---|---|---|
| 0 | 62/62 | none | −1.41 / −0.35 / +0.46% | 0.9 cm | 9.2 / 9.1 |
| 1 | 83/83 | none | −1.63 / −0.26 / +1.64% | 0.8 cm | 9.4 / 9.2 |
| 2 | 78/78 | none | −1.95 / −0.26 / +0.83% | 0.7 cm | 9.2 / 9.2 |
| 3 | 75/75 | none | −1.39 / −0.40 / +0.63% | 1.0 cm | 9.0 / 8.8 |
| 4 | 87/91 | 42444793 1.24 m, +2.08% and +2.10%; 42444858 1.08 m, −2.84%; 1.05 m, −2.89% | −2.89 / −0.37 / +2.10% | 0.9 cm | 9.2 / 9.0 |

Pooled over all seeds:
- 385 of 389 distances are within the limit.
- The median error is −0.33%, and 79% of errors are negative.
- 90% of absolute errors are under 2.0 cm.

The 42444873 distance, when found (seeds 1–3), is 3.97–4.00 m and off by −0.05 to −0.10%.

## Photos only

RC-P8's `colmap_incremental` runs without priors are used: every 12th `vga_wide` frame, SIFT,
exhaustive matching. Frames are taken in time order, and a frame counts as registered when it holds
3-D points, as in RC-P1. A break is a change of component between two registered frames, with any
unregistered frames in between. ARKit's poses are used only to say where a break falls.

| Video | Frames | Registered | Components (frames) | Component changes | Shared frames | One model |
|---|---|---|---|---|---|---|
| 42444515 | 90 | 28 | 15, 13 | 2 | none | no |
| 42444793 | 125 | 66 | 21, 19, 14, 13 | 4 | 0-2: 1 | no |
| 42444821 | 106 | 24 | 3, 11, 10 | 4 | none | no |
| 42444858 | 133 | 95 | 7, 68, 29 | 4 | 0-2: 7, 1-2: 2 | no |
| 42444873 | 218 | 179 | 179 | 0 | none | no (39 frames unregistered) |

Breaks, from `components.py`:
- **42444515:** both breaks are long unregistered runs: 28 frames over 11.6 s, while the camera
  moved 2.3 m and turned 95°, then 29 frames over 12.0 s.
- **42444821:** 46 unregistered frames over 18.8 s and 3.5 m.
- **42444793 and 42444858:** most breaks are between adjacent frames, 0.4 s apart and 0.1–0.2 m
  apart, turning 13–22°.
- **Shared frames:** in 42444858, component 0 lies inside component 2 (all 7 of its frames are in
  both). In 42444793, components 0 and 2 share one frame. A frame in two components is a link
  COLMAP did not merge on.

## Findings

1. **The LiDAR reads short, and the TSDF inherits it.**
   - LiDAR depth is 1.09–1.61% shorter than the laser depth of the same frame (median, per frame,
     five videos).
   - TSDF wall distances are a median 0.33% short, and 79% of them are short.
   - The two short failures (−2.84%, −2.89%) are about twice that bias.
   - Whether the bias is the LiDAR's or comes from Apple's laser-to-ARKit registration is not
     separated here. The Faro scans' own distances would separate them.
2. **Failures sit at short distances, where the 2 cm floor binds.**
   - All four seeded failures are 1.05–1.24 m pairs. They come from two wall planes, each about
     1.5 m wide: one in 42444793 (+2.6 cm) and one in 42444858 (−3.0 cm).
   - An unseeded run also failed a 1.17 m pair in 42444515 at +3.71%. That pair is between a wall
     and a closed door at the end of a corridor, 2.6 m from the camera that sees the door most
     squarely (`vga_wide/42444515_3700.880.png`).
     - At the door, the laser points lie mostly within ±3 cm of the plane. The TSDF surface in the
       same footprint spreads 0–15 cm in front of it.
     - No seeded run has a 42444515 pair near 1.17 m. The cause is not established.
3. **42444873 is barely scorable.** It yields one parallel pair at least 1 m apart in three seeds
   (3.97–4.00 m, error −0.05 to −0.10%) and none in two. Its laser cloud spans 15 m by 10 m, so the
   rule finds few of its walls. Why is not checked; non-parallel walls (more than 5° apart) and
   pieces of one wall closer than 1 m are both excluded by the rule.
4. **Photos-only registration of these videos is poor.**
   - COLMAP registers 23–71% of frames in four videos, and 82% in 42444873.
   - The breaks are either long unregistered runs (11–19 s) or turns between adjacent frames.
   - What the camera sees during the long runs is not checked.
5. **The report is the prototype's, not the engine's.** The clause asks that the engine report its
   components and where the links are missing. `components.py` produces that report from COLMAP's
   output; `recon` has no registration step yet.

## Not covered

- **The reference is not independent of ARKit.** The laser frames are back-projected with the
  same ARKit poses as the TSDF:
  - A pose error common to both is not seen. The laser walls' RMS (median 9.0–9.4 mm per seed)
    bounds pose inconsistency across the frames that see one wall, not drift across the room.
  - The Faro scans' own frame (58 GB, about 5.6–15.3 GB per visit) would give an independent
    distance. Not downloaded; it needs the owner's go.
- **No splat yet.** The splat half of the first clause is not tested. Inputs are ready for all five
  videos (90–218 images each, 100–200k seed points); `run_splat.sh` waits for a daytime GPU window.
  - Not checked: whether the splat stays metric (its Gaussians against the TSDF) and its held-out
    PSNR.
- **Lengths along a wall are not measured.** The distance between two opposite walls is the length
  of the walls that join them. The extent of a plane's points along itself was not used, since
  furniture and partial coverage cut it short.
- **The pairing rule is mine, set before any comparison.** It admits pairs that face the same way
  (the door pair above) and pairs across a doorway. A rule restricted to facing walls was not tried,
  so that the measure would not change after its failures.
- **One TSDF setting.** 2 cm voxels, 8 cm truncation, confidence 2 only, every 2nd frame; no sweep.
- **Photos only:**
  - Only COLMAP's incremental mapper is used, from RC-P8, at every 12th frame. Denser sampling,
    sequential matching, loop closure and GLOMAP are not tried here.
  - "Where the links are missing" is given as frames, times and ARKit positions, not as regions of
    the room's model.
- **The owner's room (UC-B1) is not captured;** all data is ARKitScenes.
