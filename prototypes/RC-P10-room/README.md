# RC-P10 — A room from inside

**Proves:** That an interior registers as one model, and what LiDAR and ARKit add. See the
[brief](../../docs/concept/RC-brief.md), RC-P10.

**Proven when:** With poses and depth, the room gives one metric model (TSDF mesh plus splat) whose
wall lengths match the reference within 2% or 2 cm, whichever is larger; photos-only, the room
either registers as one model or the engine reports its separate components and where the links
are missing.

**Result (2026-11-26): not proven; left so by the owner (2026-11-27), pose refinement deferred to the build phase.** Against the Faro scans of three visits (190 distances over five seeds), the TSDF mesh fails the wall-length limit on 7. All seven are in 42444858, on walls 1.0–1.1 m apart, 2.2–3.8 cm short. The decision rule was set before the two new visits were scored: proven only if every mesh pair met the limit against Faro. In that room the ARKit-posed reference agrees with Faro (median −0.08%), so the failures are the mesh's own. The photos-only clause is met by the engine: `recon components` reports the components and every break.
- **Correction (2026-11-26):** "the ARKit-posed reference reads long", stated from one visit, does not hold everywhere. It read long in 42444793 (+0.51%) and 42444515 (+0.73%), and not in 42444858 (−0.08%). The earlier reading that the reference explains the failures was wrong for the room where they are.
- **With poses and depth:**
  - **Against the Faro scans' own distances** (three visits, independent of ARKit): the TSDF mesh
    meets the wall-length limit on 183 of 190 wall-to-wall distances over five RANSAC seeds. Per
    room: 85/85 (median +0.07%), 70/77 (−0.54%), 28/28 (+0.47%).
  - **Against the ARKit-posed laser reference** (five videos): 329 of 332 distances are within the
    limit. The three failures are 1.01–1.09 m pairs in 42444858, the room that also fails against
    Faro. Against Faro this reference reads +0.51%, −0.08% and +0.73% in the three rooms.
- **Splat:** trained per room in ARKit's frame (2026-11-26). Its gaussian centres sit a median 1.9–3.9 cm from the TSDF surface, and walls refitted in them meet the limit on 323 of 331 distances (median −0.44%), so mesh and splat are one metric model.
- **Photos only:** one scene registers as one component, 179 of 218 frames. The other four split
  into 2–4 components. `recon components` reports each break with the frames on either side, and
  where in the room it falls when the photos come with poses (2026-11-26).

## Data

Five ARKitScenes Training videos, the ones RC-P8 used (one per visit, picked by RC-P8's
`select_arkit.py`). All five are in the depth-upsampling subset, so each has `highres_depth`:

- **`highres_depth`:** the Faro laser scanner's mesh, rendered into 116–225 frames per video at
  1920x1440 by Apple.
- **`lowres_depth`:** the iPhone's LiDAR at 256x192 and 60 Hz, with `confidence`.
- **`lowres_wide.traj`:** ARKit's poses at 10 Hz.
- **`vga_wide`:** colour at 640x480 and 30 Hz.
- **Faro scans of visit 421012** (video 42444793): six scans, 11.4 GB, downloaded with the
  owner's go (2026-11-25). This visit was chosen because it has the most wall pairs per seed.
- **Faro scans of visits 421009 (42444858, six scans) and 421061 (42444515, three scans):**
  downloaded with the owner's go (2026-11-26) to test whether the first visit's reading held.
  42444858 holds all three failures against the ARKit reference; 42444515 holds the unexplained
  wall-to-door failure.

`highres_depth` and `confidence` (about 340 MB) come from Apple; the rest is copied from RC-P8's
DGX cache. Visits 42444821 and 42444873 have no Faro scans downloaded.

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
| walls | `uv run python room.py walls --seed N` | Wall-to-wall distances, laser reference against TSDF (below) |
| faro | `uv run python faro.py merge`, `register`, `walls` | The same wall pairs measured in the Faro scans (below) |
| components | `uv run --project ../RC-P1-registration python components.py` | Photos-only components from RC-P8's `none` runs (below) |
| splat_prep | `uv run --project ../RC-P1-registration python splat_prep.py` | COLMAP model of RC-P8's posed frames (every 12th `vga_wide` frame) with 3-D points seeded from the TSDF vertices |
| run_splat.sh | on the DGX, in a `free` window | gsplat's trainer with `--no-normalize-world-space`, so the splat stays in ARKit's frame in metres |
| splat | `uv run python splat.py` | The splat against the TSDF and the walls (below) |
| summarize | `uv run python summarize.py` | The tables below |

Outputs go to `$RECCE_DATA_DIR/runs/p10/`. Wall time on the workstation (32 threads):
- `fuse`: 57 s for the five videos.
- `reference`: 41 s.
- `walls`: 34 s per seed.
- `faro.py`: merge 44 s, register 7 s, walls 32 s for five seeds.

**Open3D.** Open3D 0.20's legacy `ScalableTSDFVolume` returned no surface: 0 points after one
frame at the identity pose, where `UniformTSDFVolume` on the same frame gave 15,159. The cause is
not found. `fuse` uses the tensor `VoxelBlockGrid` instead.

## Wall lengths

**The measure.**
- **Walls:** up to 40 planes are found in the laser reference by repeated RANSAC (2 cm). A wall is
  a vertical plane (within 5°) whose points span at least 1.8 m in height and 0.8 m along it.
- **Refit:** each wall's plane is refitted in another cloud (points sampled from the TSDF mesh, or
  the Faro scan). The refit uses points inside the wall's footprint and within 5 cm of its plane,
  then again within 2 cm.
- **Distances:** every two parallel walls (within 5°) at least 1 m apart give one distance. It is
  measured at the laser walls' centroids, for every cloud.

These are wall-to-wall distances, not the sides of one box room. ARKitScenes videos cross doorways
and corridors, and an "outermost walls" rule picked the two faces of one interior wall on 42444873.
That rule was dropped after it was seen to fail, before any distance was compared.

**Seeds.** Open3D's RANSAC draws at random, so the planes found, and with them the pairs, change
from run to run.
- `walls --seed N` seeds it once per video. A seeded run is byte-for-byte repeatable (checked on
  seed 0), and `faro.py walls` reproduces the same pairs (checked: the same 18 distances on seed 0).
- Seeds 0–4 are reported. Earlier runs (unseeded, or seeded once for all videos) are discarded.
- One unseeded run failed a pair that no seeded run produces (finding 3).

### Against the Faro scan (42444793, visit 421012)

The six scans are stored already registered to each other. As stored, 60% of one scan's points lie
within 2 cm of another's; with either `_pose.txt` applied, 0–7%. They are merged on a 1 cm grid
(972,987 points).

The merged scan is then fitted onto the ARKit-frame reference rigidly, without scale, so its
distances stay the scanner's own:
- **Fit:** FPFH features and RANSAC, then point-to-plane ICP at 5, 2 and 1 cm.
- **Result:** ICP RMSE is 9.7 mm. Of the reference's points, 94% lie within 5 cm of the Faro scan
  and 72% within 2 cm (median 1.24 cm). The transform only says which Faro surface is which wall.

| Seed | Pairs | TSDF vs Faro, median (min, max) | Within limit | Laser reference vs Faro, median (min, max) |
|---|---|---|---|---|
| 0 | 18 | +0.10% (−0.83, +0.85) | 18/18 | +0.57% (−0.16, +1.56) |
| 1 | 17 | −0.08% (−0.99, +0.67) | 17/17 | +0.30% (−0.31, +1.01) |
| 2 | 14 | −0.04% (−0.53, +0.54) | 14/14 | +0.44% (−0.37, +1.17) |
| 3 | 21 | +0.08% (−0.82, +0.47) | 21/21 | +0.56% (−1.07, +2.12) |
| 4 | 15 | +0.08% (−0.63, +0.45) | 15/15 | +0.55% (−0.92, +2.00) |

Pooled over the five seeds, the distances span 1.12–3.39 m:
- **TSDF:** 85 of 85 within the limit, median +0.07%, 90% of absolute errors under 0.93 cm.
- **Laser reference:** median +0.51%, and 84% of its errors are long.

### Against the Faro scans of two more visits (2026-11-26)

The same `faro.py merge`, `register` and `walls`, five seeds each.

| Video (visit) | Scans, merged points | ICP at 1 cm: fitness, RMSE | Pairs | TSDF within limit | TSDF vs Faro, median | Reference vs Faro, median |
|---|---|---|---|---|---|---|
| 42444858 (421009) | 6, 2,628,257 | 0.228, 9.3 mm | 77 | 70 | −0.54% | −0.08% |
| 42444515 (421061) | 3, 479,796 | 0.538, 8.8 mm | 28 | 28 | +0.47% | +0.73% |

The seven failures in 42444858 are all walls 1.01–1.10 m apart (Faro), with the TSDF 2.2–3.8 cm
(2.1–3.5%) short. The reference is short on the same pairs, but by less (−0.4 to −2.6%). Its
global fitness is low (0.20 before ICP, 0.23 after); why is not checked.

### Against the ARKit-posed laser reference (five videos)

Laser against LiDAR depth, per frame (`align`):

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
| 42444793 | 18/18 | 17/17 | 14/14 | 21/21 | 15/15 |
| 42444821 | 28/28 | 30/30 | 24/24 | 24/24 | 35/35 |
| 42444858 | 14/15 | 9/9 | 14/16 | 20/20 | 17/17 |
| 42444873 | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 |

| Seed | Within / scored | Failed pairs | Error, min / median / max | Median abs error | Wall RMS, laser / TSDF (mm) |
|---|---|---|---|---|---|
| 0 | 64/65 | 42444858 1.07 m, −2.64% | −2.64 / −0.39 / +0.67% | 1.0 cm | 8.9 / 9.1 |
| 1 | 60/60 | none | −1.18 / −0.39 / +0.63% | 0.9 cm | 9.3 / 9.3 |
| 2 | 61/63 | 42444858 1.09 m, −2.39%; 1.01 m, −2.36% | −2.39 / −0.40 / +0.46% | 1.0 cm | 9.4 / 9.4 |
| 3 | 70/70 | none | −1.87 / −0.38 / +1.02% | 1.0 cm | 9.2 / 9.0 |
| 4 | 74/74 | none | −1.85 / −0.41 / +1.15% | 1.0 cm | 9.0 / 9.0 |

Pooled over all seeds:
- 329 of 332 distances are within the limit.
- The median error is −0.40%, and 83% of errors are negative.
- 90% of absolute errors are under 2.1 cm.

### The failures in 42444858, traced (2026-11-26)

Checked in scratch scripts against the committed outputs; nothing in the pipeline changed.
- **No room-wide surface bias that explains it.** Each wall's TSDF plane against its Faro plane,
  at the wall's centre and signed toward the cameras: median +1.00 cm (42444793, the room that
  passes), +0.38 cm (42444858), −0.09 cm (42444515), with no trend against camera distance (fitted
  slopes −0.15 to +0.54 cm per metre). A global depth scale would move every wall, so the LiDAR's
  1.1–1.6% against the rendered laser depth is not the cause of the failures.
- **One wall decides it.** In seeds 0 and 2, every failing pair shares one wall of a passage about
  1.05 m wide. That wall's TSDF plane sits 2.4–2.5 cm into the passage and is tilted 1.2–1.3°
  against Faro; its partners sit within 0.75 cm. The cameras that see it are 1.0 m or more away
  (median 1.7 m), so it is not near-range depth.
- **Partly the poses, partly the depth.** Along that wall, in 1 m pieces, the TSDF sits +3.1 and
  +1.0 cm off Faro, the ARKit-posed laser +1.3 and −0.1 cm. The laser shares ARKit's poses, so
  about 1 cm of the error comes with them; the rest is the LiDAR surface there.
- **A correction (2026-11-27):** the first version of this trace (f9e8893) took the trajectory's
  translation column as the camera centre; ARKit stores cam_from_world, so the centre is −Rᵀt.
  The per-room medians and the partners' offsets above are recomputed with the right centres;
  the failing wall's offset and the fusion results did not depend on it.
- **Fusion settings do not move it.** Re-fused in a mirror run directory and re-scored over five
  seeds: depth under 0.5 m dropped, 8 of 84 pairs fail; pixels seen at under 17° dropped, 6 of
  80; truncation 4 cm instead of 8 cm, 7 of 77 (the committed setting: 7 of 77).
- **What would fix it:** refining the poses where the passage is seen (frame-to-model ICP or a
  pose graph on the LiDAR frames). Not tried.

## The splat

One splat per room, trained on the DGX on 2026-11-26 in a `free` window (`run_splat.sh`, gsplat
1.5.3, `simple_trainer.py default`, 7,000 steps, every 8th frame held out). Each trains on RC-P8's
posed frames (every 12th `vga_wide` frame, ARKit poses), seeded with 100–200k points from the TSDF
mesh. `--no-normalize-world-space` keeps it in ARKit's frame, in metres. Each run took 162–182 s.

`splat.py` checks it in three ways:
- **Surface:** the distance from each confident gaussian's centre (opacity at least 0.5) to the
  TSDF mesh.
- **Walls:** room.py's walls are refitted in those centres, giving the same wall-to-wall distances
  as before, scored against the laser reference.
- **Quality:** the trainer's held-out PSNR and SSIM.

| Video | Gaussians (confident) | Centre to TSDF, median | Within 2 / 5 / 10 cm | Walls within limit, five seeds | Wall error, median | Held-out PSNR / SSIM |
|---|---|---|---|---|---|---|
| 42444515 | 1,146,511 (547,272) | 3.7 cm | 32% / 62% / 87% | 24/27 | −1.17% | 24.70 dB / 0.880 |
| 42444793 | 1,292,142 (644,248) | 1.9 cm | 52% / 80% / 97% | 82/85 | −0.81% | 26.27 dB / 0.869 |
| 42444821 | 1,021,360 (461,517) | 2.4 cm | 45% / 71% / 87% | 141/141 | −0.35% | 21.70 dB / 0.854 |
| 42444858 | 1,108,768 (494,919) | 2.7 cm | 41% / 67% / 80% | 75/77 | −0.43% | 21.76 dB / 0.800 |
| 42444873 | 1,152,569 (531,905) | 3.9 cm | 34% / 56% / 72% | 1/1 | +0.15% | 20.85 dB / 0.713 |

Pooled over the five rooms and seeds:
- 323 of 331 wall distances are within the limit, with a median of −0.44%; 89% are short.
- All eight failures are pairs 1.00–1.46 m apart, off by 2.1–3.1%.

**Reading.** The splat sits in the TSDF's frame and scale: its centres lie a median 1.9–3.9 cm from
the TSDF surface. Its walls read shorter than the TSDF's (median −0.44% against −0.40% for the TSDF
on the same reference).

Two things affect that comparison:
- **The reference reads long.** It reads +0.51% long against the Faro scan on the one visit
  checked, so against Faro the splat's walls are close to true there.
- **Floaters may pull the walls in.** Gaussians in front of a wall would pull the refitted plane
  toward the room. This is not checked separately.

## Photos only

RC-P8's `colmap_incremental` runs without priors are used: every 12th `vga_wide` frame, SIFT,
exhaustive matching. Frames are taken in time order, and a frame counts as registered when it holds
3-D points, as in RC-P1. A break is a change of component between two registered frames, with any
unregistered frames in between. ARKit's poses are used only to say where a break falls.

**The engine reports this itself (2026-11-26).** `recon components <sparse> [--capture-set <set>]`
(`src/recon/components.py`, with tests) reads the mapper's models and writes the report. Run on the
five RC-P8 models, it agrees with `components.py` on three videos. On two it finds fewer breaks,
and the engine is right:
- **The prototype's error:** `components.py` gave each frame one component label (the last that
  held it), so a frame registered in two components showed as a change of component on either side.
- **Why the engine is right:** a frame shared by two components is a link, not a break. The engine
  keeps every component a frame belongs to.

The table below uses the engine's counts.

| Video | Frames | Registered | Components (frames) | Component changes | Shared frames | One model |
|---|---|---|---|---|---|---|
| 42444515 | 90 | 28 | 15, 13 | 2 | none | no |
| 42444793 | 125 | 66 | 21, 19, 14, 13 | 3 | 0-2: 1 | no |
| 42444821 | 106 | 24 | 3, 11, 10 | 4 | none | no |
| 42444858 | 133 | 95 | 7, 68, 29 | 2 | 0-2: 7, 1-2: 2 | no |
| 42444873 | 218 | 179 | 179 | 0 | none | no (39 frames unregistered) |

The breaks, with ARKit's positions from `components.py`:
- **42444515:** both breaks are long unregistered runs: 28 frames over 11.6 s, while the camera
  moved 2.3 m and turned 95°, then 29 frames over 12.0 s.
- **42444821:** 46 unregistered frames over 18.8 s and 3.5 m, and 18 over 7.6 s and 1.6 m. The
  other two changes are between adjacent frames 0.4 s apart (0.2 m, 22–30°), where component 0
  (3 frames) sits inside a run of component 2.
- **42444793:**
  - one unregistered frame over 0.8 s (0.32 m, 27.6°);
  - 13 unregistered frames over 5.6 s (0.24 m, 46.4°);
  - two adjacent frames 0.4 s apart (0.1 m, 13.2°).
- **42444858:**
  - 8 unregistered frames over 3.6 s (0.52 m, 6.7°);
  - 6 unregistered frames over 2.8 s (1.94 m, 43.7°).
- **Shared frames:** in 42444858, component 0 lies inside component 2 (all 7 of its frames are in
  both). In 42444793, components 0 and 2 share one frame. A frame in two components is a link the
  mapper did not merge on.

**Not yet in the engine:** where a break is, in the room, needs poses. The engine gives it when the
photos come in a capture set with poses (ARKit, a robot). These five videos have no capture set yet,
so the places above come from `components.py`.

## Findings

1. **The TSDF's bias against Faro differs by room, and in one room it fails.** Over three visits:
   - **The TSDF against Faro:** +0.07% (42444793), −0.54% (42444858), +0.47% (42444515).
   - **The ARKit-posed reference against Faro:** +0.51%, −0.08% and +0.73% in the same rooms.
   - **Withdrawn:** the first visit's reading, that "the reference reads long, so most of the
     TSDF's error against it is the reference's", held in two rooms. In 42444858, where the
     failures are, the reference agrees with Faro and the TSDF is short.
   - **The LiDAR depth** reads 1.09–1.61% shorter than Apple's rendered laser depth in all five
     videos. How that turns into a room-dependent wall error is not established.
   - **Traced (2026-11-26):** not a room-wide bias. One wall of a 1.05 m passage sits 2.4–2.5 cm
     into it, about 1 cm with ARKit's poses and the rest from the LiDAR surface; three fusion
     settings leave it in place. Wall medians per room are +1.00, +0.38 and −0.09 cm.
2. **Failures sit at short distances, where the 2 cm floor binds.**
   - **Against Faro:** all seven failures are 1.01–1.10 m pairs in 42444858, 2.2–3.8 cm short.
   - **Against the ARKit reference:** all three seeded failures are 1.01–1.09 m pairs in the same
     room, 2.4–2.6% short.
   - **Elsewhere:** the other two Faro rooms have 17 pairs under 1.3 m (from 1.00 m); the TSDF
     error on them is at most 1.01%.
   - An unseeded run also failed a 1.17 m pair in 42444515 at +3.71%. That pair is between a wall
     and a closed door at the end of a corridor, 2.6 m from the camera that sees the door most
     squarely (`vga_wide/42444515_3700.880.png`).
     - At the door, the laser points lie mostly within ±3 cm of the plane. The TSDF surface in the
       same footprint spreads 0–15 cm in front of it.
     - No seeded run has a 42444515 pair near 1.17 m. The cause is not established.
3. **42444873 is barely scorable.** It yields one parallel pair at least 1 m apart in one seed of
   five. Its laser cloud spans 15 m by 10 m, so the rule finds few of its walls. Why is not
   checked; non-parallel walls (more than 5° apart) and pieces of one wall closer than 1 m are
   both excluded by the rule.
4. **Photos-only registration of these videos is poor.**
   - COLMAP registers 23–71% of frames in four videos, and 82% in 42444873.
   - The breaks are either long unregistered runs (11–19 s) or turns between adjacent frames.
   - What the camera sees during the long runs is not checked.
5. **The engine reports components, but does not register.** `recon components` reads a mapper's
   output and reports the components and the breaks between them. `recon` has no registration step
   of its own yet, so the mapper (here COLMAP) runs outside it.

## Not covered

- **Two videos have no independent reference.** Faro covers 42444793, 42444858 and 42444515
  (190 distances over five seeds). 42444821 and 42444873 are scored only against the ARKit-posed
  laser reference, which shares the TSDF's poses: a pose error common to both is not seen there.
- **The splat is not checked against Faro.** Its walls are scored only against the ARKit-posed
  reference.
- **Pose refinement.** The failures in 42444858 trace to one wall of a 1 m passage, partly to
  ARKit's poses there and partly to the LiDAR surface ("The failures in 42444858, traced"). No
  pose refinement is tried, so whether it fixes them is not known.
- **The Faro walls come from the reference's planes.** The reference picks and places each wall,
  and the Faro scan is refitted there. A wall the reference misses is not measured in the scan.
- **The splat:** 7,000 steps only, default densification, no seed repeat. Floaters are not filtered or counted beyond the opacity cut, and the splat is not viewed in the browser.
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
