# RC-P13 — A structured model from a reconstruction

**Proves:** That an agent can turn a reconstruction and a little context into a structured model
(walls and rooms, passages, terrain and buildings) in which every element states whether it is
measured, inferred or unknown, and how sure it is. See the
[brief](../../docs/concept/RC-brief.md), RC-P13.

**Proven when:** In each segment the agent builds the structured model through the tool-neutral
description, every element carries a source and an uncertainty, nothing tagged measured lacks
support in the reconstruction, and the measured dimensions meet the segment's reference: room
walls and floor area within 2% or 2 cm of the Faro scan; cave passage widths and heights against
the set's reference, tolerance set when the set is chosen; drone terrain heights and building
footprints against the control points. The number of agent iterations and where they went wrong
is recorded.

**Result (2026-11-26): not proven yet.**
- **Room:** built and checked. All 13 measured dimensions are within 2% or 2 cm of the Faro scan.
  The floor-area part of the criterion is not yet compared as an area.
- **Drone:** built and checked against 58 survey points. As the model stands (RTK only), the
  ground reads 1.05 m low and 18 of 57 heights are within its stated 2σ; after one shift
  fitted on 7 control points, 50 of 50 check points are, std 0.27 m. The site has no
  buildings, so the footprint clause is not tested.
- **Buildings:** built and checked on UseGeo, from the providers' poses (our own mapping bends
  on this flight), against a tolerance fixed beforehand. Not met: against OpenStreetMap, 31 of 49
  buildings pass IoU 0.5 (80% needed). With the eaves stated, 30 of 31 areas are within their
  2σ (σ a median 29% of the area); heights within 2σ for 29 of 31. Every mapped building is
  found; merged neighbours and outlines fail it.
- **Cave:** built and checked on the authors' photogrammetric cloud. On covered sections, 11 of 17
  widths and heights are within 2% or 5 cm (a proposed tolerance), median −0.9 cm, p95 12 cm. The
  fork is marked unknown.

## Layout

| Path | What it is |
|---|---|
| `scene.py` | The tool-neutral description: schema `recce-structured/0.1`, its rules, read and write. Pure standard library, so Blender's Python imports it |
| `room/build_room.py` | Room segment: RC-P10's TSDF mesh to a scene, then the scene against the Faro scan. Runs in RC-P10's environment (Open3D) |
| `cave/build_cave.py` | Cave segment: a lava tube's cloud to stations, cross-sections and LRUD, then against the LiDAR. Runs in RC-P10's environment |
| `drone/build_drone.py` | Drone segment: RC-P8's drone model to a terrain grid, then the grid against the survey points. Runs in RC-P1's environment (pycolmap) |
| `buildings/reconstruct.py` | Buildings segment: UseGeo features and matches, triangulated from the given poses. Runs in RC-P1's environment |
| `buildings/run_dense.sh` | Dense depth and fusion in RC-P2's HIP container on the X3 |
| `buildings/fetch_osm.py` | OpenStreetMap's building outlines over the site, in a throwaway container with pyproj |
| `buildings/build_buildings.py` | The dense cloud to terrain and LOD1 buildings, checked against OpenStreetMap and the LiDAR rule. Runs in RC-P1's environment |
| `adapters/blender/build.py` | The Blender adapter: a scene to `.blend`, `.glb` (with the tags as glTF extras), a plan and perspective renders. Blender 4.5.17 LTS, headless |

Outputs go to `$RECCE_DATA_DIR/runs/p13/<segment>/<id>/`.

```bash
cd prototypes/RC-P13-structured/room
uv run --project ../../RC-P10-room python build_room.py --video 42444793
cd ../adapters/blender
~/.local/opt/blender-4.5.17-linux-x64/blender -b --factory-startup --python build.py -- \
  ~/.cache/recce/runs/p13/room/42444793/scene.json ~/.cache/recce/runs/p13/room/42444793/blender \
  --mesh ~/.cache/recce/runs/p10/42444793/tsdf.ply
```

## The description

A scene has a frame, its inputs, elements and measurements.

- **Each element:** an id, a kind (`floor`, `ceiling`, `wall`), a geometry, a source, an
  uncertainty with its basis, evidence and attributes.
- **Each measurement:** a value between elements, with its own source, uncertainty, bias and
  basis.
- **The rules:** `scene.validate` refuses a scene that breaks them, and every writer and reader
  calls it.
  - **Measured:** fitted to the reconstruction. It needs evidence, an uncertainty and the basis
    of that uncertainty.
  - **Inferred:** closed by a rule or a model. In the room segment, a single wall face's
    thickness (0.10 m) is inferred.
  - **Unknown:** inside the structure but not observed. It is drawn as a hole and never carries
    an uncertainty.

A second tool needs only `scene.py` and its own adapter. Nothing in the description is
Blender's.

## Room segment (ARKitScenes 42444793, Faro reference)

**What the builder does:**
- **Planes:** RANSAC planes on 400,000 points sampled from the TSDF mesh (seed 0). Up comes from
  the floor and the camera, as in RC-P10.
- **Floor and ceiling:** the largest up-facing and down-facing horizontal planes. Each is
  rasterised into 5 cm cells: seen cells are measured. Cells inside the seen surface and the
  walls, but not observed, are unknown.
- **Walls:** RC-P10's rule (vertical, at least 1.8 m high and 0.8 m wide), plus a density test.
  - A wall face is drawn where the mesh saw it.
  - Its body goes on the side away from the cameras.
  - Two opposite faces under 0.35 m apart are one wall, whose thickness is measured.
- **Measurements:**
  - Wall-to-wall distances use RC-P10's rule (parallel, 1 m or more apart).
  - Their uncertainty is σ 1.08 cm with a bias of −0.91 cm. That is RC-P10's TSDF error against
    the ARKit laser reference on 47 pairs in the other four rooms, so the Faro check here stays
    independent.

**Against the Faro scan:**

| Quantity | Result |
|---|---|
| Wall-to-wall distances (11) and partition thicknesses (2) | 13 of 13 within 2% or 2 cm; 12 of 13 within the stated 2σ |
| Partition thicknesses | 0.153 and 0.125 m, against Faro's 0.142 and 0.117 m |
| Room height (floor to ceiling) | 2.547 m against 2.563 m (−1.5 cm, limit 5.1 cm) |
| Floor seen by the model | 3.70 m²; Faro saw 3.60 m² of the same footprint; both saw 3.22 m² |
| Floor tagged unknown | 1.92 m², of which Faro saw 0.38 m² |
| Elements | 9 walls, floor and ceiling (measured); unseen floor and ceiling (unknown); 5 wall bodies have an inferred thickness |

**Agent iterations (the agent is the coding agent in this session; each one is a build, a
render, a look and a fix):**
1. **Walls doubled.** The TSDF sees both faces of a partition, and each face became a wall.
   The plan was also unreadable: floor and walls were one colour, and the frame was cropped.
   Fix: opposite faces under 0.35 m apart became one wall with a measured thickness; separate
   shades; framing on both axes.
2. **A false diagonal wall.** It was a RANSAC plane at about 450 points/m², against about
   10,000 for real walls, threading scattered fragments. RC-P10's height and width rule let it
   through. Fix: walls under 20% of the median wall density are dropped.
3. **A room with walls and no floor showed nothing,** neither seen nor unknown. The unknown
   floor was computed only around the seen floor, so the room the mesh never saw went missing.
   Fix: the footprint includes the area walls enclose. Also, labels stacked and some read upside
   down. Fix: dimension lines spread along the wall, text kept upright.
4. **The plan reads:** seen floor, unknown floor in red, measured and inferred wall bodies, and
   every distance with its uncertainty. Kept.

## Findings

1. **The description carries the check.** The structured model's 13 dimensions come out of the
   description, not out of Blender. The Faro check reads the same file the adapter builds from.
2. **Unknown is the hard part.** Three of four iterations were about where the model's
   knowledge ends: doubled faces, a phantom wall, a room with no floor. A model that only draws
   what it saw would have looked finished and been wrong.
3. **Thickness is measured only where both faces were seen** (2 of 7 walls). Elsewhere it is
   inferred, and the colour says so.

## Not covered

- **Floor area as an area.** The criterion's floor-area clause is reported as cell coverage
  (seen, unknown, seen by Faro). The area each room encloses is not computed as a polygon and
  compared.
- **Doors and openings.** They are not detected. A gap between walls shows as missing wall, and
  the unknown floor shows where nothing was seen.
- **One room.** The other four RC-P10 rooms have no Faro check here and are not built.
- **The height uncertainty.** It is plane-fit noise only, not calibrated against a reference.
- **The thin-wall uncertainty.** The partition thickness reuses the wall-distance σ, which was
  calibrated on pairs 1 m or more apart.
- **The second tool.** No second adapter exists yet; the description is meant to allow one.
- **The glTF in the RC-P6 viewer.** It is written, but not yet opened there.
- **Drone, cave and buildings segments:** below.

## Drone segment (EuroSDR P4 RTK, survey check points)

**Data.** EuroSDR RPAS benchmark, Phase 2: a DJI Phantom 4 RTK, flight 100_0004, 430 nadir
photos from 55 m over upland pasture and a quarry (CC BY 4.0). There are no buildings on the
site, so no building footprints are built or checked.
- **The reconstruction:** RC-P8's drone test, `prior_half_opencv`: RTK priors on the 215 odd
  photos, the OPENCV lens, 430 of 430 photos, 436,892 points. It stands in the RTK frame as
  mapped; no ground information goes into it.
- **The reference:** the benchmark's 58 survey points (`GCPsandCPs_coords.xlsx`): 8 ground
  control points (GA1 … GF8), 47 check points (A1 … F8) and 3 more (S1 … S3), in ETRS89 with
  ellipsoidal heights.

**What `drone/build_drone.py` does.** It follows a surveyor's terrain model:
- **Cells:** a 2 m grid over the ground the flight saw (within 25 m of a camera). A cell's height
  is the median height of its points; it is measured with at least 4 points.
- **Steep faces:** measured cells sloping more than 45° (the quarry walls) are a separate element.
- **Gaps:** a cell short of points whose 8 neighbours are mostly seen (6 or more) is inferred, at
  their mean height. Other gaps are unknown.
- **Uncertainty:** σ 0.41 m, the RMS vertical error of the 215 photos without a prior against
  their RTK centres. It is the only check of the frame the model carries without ground
  information, and it checks the cameras, not the ground.
- **The check:** each survey point's cell height against its surveyed height. Twice: as the model
  stands, and after one vertical shift fitted on the control points, checked on the rest.
- **Tolerance:** the brief sets none for the drone. By default a height is within it when inside
  2σ of the model's own stated uncertainty (`--tol-sigma 2`), so the check scores the claim the
  model makes; `--tol-m` sets a fixed one instead. With `--tol-m 0.05`, 0 of 57 heights as they
  stand and 10 of 50 after the shift are within it.

| Element | Source | Cells | Area |
|---|---|---|---|
| Terrain | measured | 26,623 | 106,492 m² |
| Steep faces | measured | 369 | 1,476 m² |
| Gaps closed from neighbours | inferred | 1,648 | 6,592 m² |
| Gaps | unknown | 1,192 | 4,768 m² |

**Against the survey points:**

| Check | Heights | Mean error | Std | p95 abs | Within the stated 2σ (0.82 m) |
|---|---|---|---|---|---|
| As the model stands (RTK only) | 57 measured | −1.05 m | 0.29 m | 1.60 m | 18 of 57 |
| After a −1.15 m shift fitted on 7 control points | 50 check points | +0.12 m | 0.27 m | 0.50 m | 50 of 50 |

GC6 falls in an inferred cell: −2.04 m as it stands. It is left out of the fit.

**Agent iterations:**
1. **37% of the grid was unknown.** The grid covered the cameras' bounding box, whose corners the
   flight never saw. Fix: only cells within 25 m of a camera.
2. **Single unknown cells were scattered over the pasture.** Grass gives few points; a 2 m cell
   with 3 points between seen neighbours is not a hole. Fix: such cells are inferred from their
   neighbours; the unknown cells left are the flight's edges and one patch in the south-east.
3. **The first check mixed sources.** GC6's inferred height entered the control-point fit. Fix:
   only measured heights are fitted and scored; inferred ones are reported apart.

**Findings:**
1. **The stated uncertainty is wrong without ground information.** The ground reads 1.05 m low
   against the survey, while the cameras' own check gives σ 0.41 m: 18 of 57 heights are within
   the stated 2σ. The structured model claims more than it knows here.
2. **The error is mostly one offset.** After one shift fitted on 7 control points, the check
   points are 0.27 m std, all within 2σ. The spread is larger at the block's edges, as the
   residual dome in RC-P8 predicts.
3. **The offset is split, and part of it is still open.** RC-P8's "The height offset against
   the survey" takes it apart (2026-11-26): the RTK frame against a PPK solution on the local
   base, 0.12 m; the mapper's hold on the priors, 0.26 m; DJI's calibrated focal length, 0.6% too
   long, 0.28–0.36 m. About 0.25–0.38 m is not explained. A fit to an offset, a depth and a dome
   term had first pointed away from the focal length; the adjustment with all RTK centres held
   and the focal free is the cleaner test, and a full focal-free re-map gives the same answer.
   The first version of this finding (a9c1c2c) said the offset comes with the RTK positions, not
   the lens; that was wrong.

**Not covered:**
- **Buildings.** The site has none; the footprint clause is tested in the buildings segment, on
  another flight.
- **A fixed tolerance.** The default scores the model's own claim (2σ); a fixed value for the
  drone is not set by the brief.
- **Horizontal position.** Only 8 of 57 targets are located consistently across photos; the
  others vary by more than 0.15 m from photo to photo, with each photo's pose error.
- **Dense surface.** Heights come from the sparse model (about 2.3 points per m²).
- **The steep-face uncertainty.** A cell on a quarry wall reuses the open-ground σ.

## Cave segment (Grotta di Monte Intraleo, LiDAR reference)

**Data.** A lava tube on Etna, from the paper "LiDAR and Photogrammetry Data Evaluation from a
Lava Tube Mission in Sicily" (Romio et al.). It is on 4TU.ResearchData, doi
10.4121/0cc49d43-8a5c-453e-9370-8e9088b00b48, under CC BY 4.0.
- **The reconstruction:** the authors' merged photogrammetric cloud, 12.95 M points.
- **The reference:** their five LiDAR scans, merged with CloudCompare ICP, 2.41 M points.
- **What was skipped:** the authors' 1.5 GB cloud-to-cloud analysis. The robot's raw video is not
  published.
- **Getting it out:** the `.bin` files need CloudCompare 2.13 or later. Ubuntu 24.04's 2.11 refuses
  the format. Debian 13's 2.13.2 runs headless in a throwaway Docker container and exports both
  clouds to PLY, so nothing is installed on the host and the GPL tool stays outside our code.

**What `cave/build_cave.py` does.** It follows a cave survey's structure:
- **Stations:** every 1 m along the passage centreline.
- **Sections:** a cross-section at each station, made of 72 rays (every 5°) in the vertical plane
  square to the passage. A ray's length is the median distance of the cloud's points in its bin,
  within a 0.2 m slab. It is unknown where the bin has fewer than 3 points.
- **Measurements:** each section's width (left + right) and height (up + down). Each direction is
  the median of the bins within ±10°.
- **The check:** the same rays are cut in the LiDAR cloud.
- **Tolerance:** 2% or 5 cm is proposed. The brief leaves the cave's tolerance open.

**Against the LiDAR (22 stations over 22.7 m of passage):**

| Sections | Compared | Within 2% or 5 cm | Median error | p95 abs error | Width / height median |
|---|---|---|---|---|---|
| Covered (at most 6 of 72 rays unknown) | 17 | 11 | −0.9 cm | 12.3 cm | −8.2 / +5.3 cm |
| Partly covered | 19 | 8 | −3.6 cm | 61.1 cm | −5.1 / −3.0 cm |

Of the widths and heights, the LiDAR has 7 that the photos lack, and the photos have 1 that the
LiDAR lacks.

**Agent iterations:**
1. **The centreline was 58.9 m long for a 34 m cloud.** Slabs that caught a side chamber moved
   their median off the passage, so two stations jumped 8–9 m. Also, one 5° bin decided each of
   L, R, U and D. Fix: L, R, U and D come from the bins within ±10°.
2. **Dropping the jumps greedily ate the passage.** Removing the worst station repeatedly
   cascaded from one end, leaving 2 stations. A top view of both clouds showed why: the tube forks
   near its north end, and slabs there mix both branches.
3. **A walk from the end stopped at once.** The station at the tube's mouth wobbles 63°. Fix: seed
   the walk at the station whose neighbours agree best, then walk both ways until the first break.
   The result is a 22.7 m single passage.
4. **The errors split by coverage,** so the check reports covered and partly covered sections
   apart.
5. **The plan joined the two ends into one red line** across the passage. Fix: the mouth and the
   fork are separate unknown elements. The roof half of the tube is hidden in the plan, the way a
   ceiling is.

**Findings:**
1. **Covered sections are close but biased.** Widths read about 8 cm narrow and heights about
   5 cm tall against the LiDAR. A rigid registration cannot do that, so it is likely a surface
   effect: rough lava, and cracks the photos miss. The cause is not checked.
2. **Coverage decides the error.** The 61 cm p95 sits in sections where a quarter of the rays have
   no rock. The model marks those rays unknown, but the width and height still use the rays that
   exist.
3. **The fork is not structured.** It is marked unknown. Structuring a branching passage needs a
   graph of passages, not one centreline.

**Not covered:**
- **Uncertainty.** The section rays' uncertainty (5 cm, the voxel) is not calibrated.
- **The tolerance.** It is a proposal for the owner.
- **The branches** beyond the fork.
- **The authors' own cloud-to-cloud analysis.** It is not compared with ours.
- **The reconstruction itself.** It is the authors' photogrammetry, not ours, because the raw video
  is not published.

## Buildings segment (UseGeo Dataset-1, OpenStreetMap and LiDAR references)

**Data.** UseGeo, Dataset-1 (FBK 3DOM and partners, CC BY-NC-SA 4.0, so internal prototypes
only): 224 nadir photos, 7952 × 5304, DxO-undistorted, over the edge of a town in southern
Sardinia (UTM zone 32N; the files carry no coordinate system, and zone 33 puts the site in the
sea). The providers give the interior orientation (c 4636.912 px), an exterior orientation per
photo from their own adjustment, their tie points, and a LiDAR flight (LAS 1.4, 105.9 M points;
class 4 is vegetation, the rest mostly unclassified). The LAS goes to numpy with laspy in a
throwaway container; outliers reach −225 m and +215 m around a site near 190 m and are cut at
±80 m from the median.
- **Reference 1, OpenStreetMap:** the building outlines over the site (111 ways, ODbL), fetched
  into the run directory by `buildings/fetch_osm.py` in a throwaway container with pyproj; never
  committed. They line up with the LiDAR: a shift search finds the best fit within 1 m of none.
- **Reference 2, the LiDAR:** through the model's own footprint rule (below). It has no building
  class, so it is a second check, not the main one.

**What the scripts do:**
- **`buildings/reconstruct.py`:** SIFT features (3,200 px, 16,000 per photo) and exhaustive
  matching with pycolmap, then the points triangulated from the providers' poses (`--poses given`,
  the default). `--poses mapped` runs the incremental mapper with the positions as pose priors
  and an OPENCV lens left free (finding 5).
- **`buildings/run_dense.sh`:** dense depth and fusion in RC-P2's HIP container on the X3, from the
  given-pose model at 1000 px: 2 h 42 min of patch-match, 3,280,739 fused points.
- **`buildings/build_buildings.py`:** the city model at its simplest level (CityGML LOD1).
  - **Grid:** 1 m cells; the surface is the 90th-percentile height of a cell's points.
  - **Ground:** a 30 m morphological opening of the surface, after a 3 × 3 median.
  - **Buildings:** cells more than 2.5 m above the ground and not green (excess green ≤ 0.06),
    one-cell gaps closed and specks opened away, connected where neighbouring roof heights differ
    by 1.5 m or less, at least 20 m².
  - **Each building:** a measured prism (footprint cells, ground, roof as the median cell height).
    Its area is the roof outline's; it states a bias (the eaves: 0.32 m per metre of outline) to
    the area within the walls, and a σ combining half a cell and the eaves' spread (0.75 m per
    metre of outline). The roof's σ is its cells' spread (1.4826 × median absolute deviation).
  - **The LiDAR rule:** the same, with vegetation from the class-4 share (> 0.3) or a canopy (a
    cell whose LiDAR heights spread more than 1 m, 10th to 90th percentile, with all eight
    neighbours).
  - **The check:** where the photos give a surface; each reference building against the model
    building it overlaps most. OpenStreetMap buildings less than 90% in view are left out (50).
  - **The scene:** terrain as an inferred height grid, buildings as measured prisms with their
    areas as measurements. The Blender adapter's `prism` builder extrudes them.

**Tolerance (fixed on 2026-11-26, before any check against a clean reference).** The brief names
control points for footprints; this flight has none, so the owner agreed that a tolerance is set
here and recorded before the next check runs. On buildings of 100 m² or more in the reference,
within the area the photos cover:
- **Footprint:** a building passes when its IoU with the model building it overlaps most is 0.5
  or more.
- **Detection:** 80% or more of those buildings pass.
- **Area:** each passing building's area is within the model's stated 2σ of the reference area.
- **Height:** each passing building's height is within 2σ, once the roof height carries a σ.

The segment's clause is met when all four hold. The reference is the OpenStreetMap building
footprints for the site; the LiDAR rule stays as a second, independent check.

**Result: not met.**

| Against | Buildings of 100 m² or more | IoU ≥ 0.5 | Areas within 2σ | Heights within 2σ |
|---|---|---|---|---|
| OpenStreetMap | 49 | 31 (63%; 80% needed) | 30 of 31 | 29 of 31 |
| OpenStreetMap, odd ids only (held out from the eaves calibration) | 23 | 16 (70%) | 15 of 16 | 16 of 16 |
| LiDAR rule | 77 | 35 (45%) | 31 of 35 | 34 of 35 |

| Quantity | Against OpenStreetMap | Against the LiDAR rule |
|---|---|---|
| Reference buildings compared | 61 | 156 |
| Matched at IoU ≥ 0.3 | 45, IoU median 0.62 | 55, IoU median 0.64 |
| Area of matched, median | +14% | −5% |
| Height of matched, median | +0.09 m | +0.13 m |
| Reference cells the model has | 79% | — |
| Model cells inside the reference | 68% | — |

The ground reads +0.30 m against the LiDAR's (median). The model has 65 buildings.

**Agent iterations:**
1. **The mapped model was bent.** The incremental mapper with the given positions as 5 cm priors
   put the cameras a median 7.5 m from them (up to 53 m), their heights spread 13.8 m against
   the given 4.1 m, and the surface sat 4.2 m below the LiDAR. A pose-prior bundle adjustment
   with the intrinsics free did not pull it back: the centres still moved a median 3.2 m and
   the focal went to 4832 px. The dataset itself is consistent: its tie points sit +0.06 m from
   its LiDAR (IQR ±0.22 m), and its orientations reproject them within about 25 px, under the
   rotation R = Rx(ω) Ry(φ) Rz(κ) only. Fix: the given poses, held; our matches triangulated from
   them land −0.01 m from the LiDAR (median). The bend's cause, found later, is finding 5.
2. **The ground read 1.17 m low.** Stray points under the surface became the minimum of the
   opening. Fix: a 3 × 3 median before it.
3. **The LiDAR called trees buildings.** Two thirds of the LiDAR-only building cells were green in
   the photos; the vegetation class misses many trees. A component rule (median spread over a
   building) threw out houses joined to trees; the per-cell canopy rule keeps them.
4. **Roofs had holes.** The sparse points (about 4 per m²) covered 38% of the LiDAR's building
   cells; closing wider gaps reached 50% and merged houses. Fix: the dense cloud, 62%.
5. **The LiDAR reference was not clean enough to judge by.** Against it, footprints read 24%
   small and only 10 of 29 areas sat within 2σ; 45 of its 55 buildings under 200 m² were green
   tree crowns. Fix: the tolerance was fixed and recorded (f414c06), then OpenStreetMap became the
   reference. Against it the model's footprints read larger, not smaller, and only 51% of the
   LiDAR rule's building cells lie inside a mapped building, against 68% of the model's.
6. **Neighbouring houses merged.** Against OpenStreetMap, 11 of the 21 failures were one model
   building spanning several mapped houses. Fix: neighbours more than 1.5 m apart in roof height
   are separate buildings (0.6, 1.0 and 1.5 m tried; 1.5 m passes most). Passing buildings rose
   from 28 to 31 of 49, areas within 2σ from 13 to 18.
7. **The area claimed a wall footprint it cannot see.** Passing buildings read a median 19% larger
   than their mapped outline. Fix: the area is stated as the roof outline's, with the eaves as a
   bias and their spread in the σ, calibrated on the even OpenStreetMap ids (14 buildings) and
   tested on the odd ones: 15 of 16 there, 30 of 31 overall, within 2σ. The one outside
   (OpenStreetMap way 294275681, 949 m² mapped, 626 m² modelled) is a building the model cuts short.

**Findings:**
1. **Every mapped building is found, and heights are right.** Each of the 49 OpenStreetMap
   buildings of 100 m² or more overlaps a model building; heights are within their stated 2σ for
   29 of 31, median +0.09 m.
2. **Outlines fail the tolerance.** 31 of 49 pass IoU 0.5 (63%, 80% needed). Of the 18 that fail,
   7 are houses merged with a neighbour at nearly the same roof height, and 11 are one-to-one
   with an IoU of 0.21–0.49 (9 of them 0.41 or more).
3. **Nadir photos see roofs, maps draw walls.** The roof outline reaches a median 0.32 m beyond the
   mapped walls per metre of outline. The model now says its area is the roof outline's and
   states that offset.
4. **The area clause is met by claiming less.** With the eaves' spread in it, the stated area σ
   is a median 29% of the area, against a median error of 17% after the correction; 30 of 31 are
   within 2σ, one short of "each". The claim is now honest and wide; a tighter one needs walls
   the photos do not show.
5. **The bend was the lens.** The DxO-undistorted photos still carry radial distortion that the
   published pinhole interior leaves out. Holding the given poses, an OPENCV lens takes our matches
   from 6.9 px to 0.97 px mean reprojection error (k1 −0.063); a pinhole with the principal point
   free only reaches 4.9 px. Each re-map below runs the same mapper on the same matches and 5 cm
   priors:

   | Lens in the mapper | Cameras from the given, median (max) | Height spread (given 4.11 m) | Surface − LiDAR, median | Cells within 0.5 m |
   |---|---|---|---|---|
   | Published pinhole, held | 7.53 m (52.8 m) | 13.8 m | −4.21 m | 3% |
   | OPENCV refined against the given poses, held | 0.02 m (0.09 m) | 4.11 m | −0.05 m | 82% |
   | OPENCV free from the published interior (`--poses mapped`) | 0.26 m (1.32 m) | 3.93 m | −1.11 m | 67% |

   With the lens free, our own reconstruction finds the same distortion (k1 −0.063) but lengthens
   the focal to 4790 px against 4730 px, and the surface reads 1.11 m low: 1.3% of an 82 m flying
   height. That is the drone segment's pattern again, where the ground read 1.05 m low and DJI's
   focal length was part of it: in a nadir block with position priors, focal length and height
   trade against each other. The buildings stay on the given poses; the mapped model is the
   reproducible comparison (`--poses mapped`).

**Not covered:**
- **Splitting houses of one height.** Terraced houses under one roof level stay one building;
  splitting them needs roof lines or the map itself.
- **The eaves themselves.** The offset is a calibrated average, not measured per building; no
  oblique views. That it is eaves, and not the map's tracing, is not checked.
- **OpenStreetMap's own accuracy.** Its outlines are taken as truth; their source (survey,
  cadastre or tracing) is not checked, and buildings missing from the map count as extra.
- **The roof σ.** It is the roof's spread, not calibrated against a reference.
- **Roof shape.** LOD1 only: one height per building.
- **Our poses for the buildings.** The structure uses the providers' poses. Our free-lens model
  reads 1.11 m low (finding 5); breaking the focal-height trade needs ground control, oblique
  photos or a calibrated focal, none tried here.
- **The rules were tuned here.** The canopy threshold (1 m), the gap closing and the 1.5 m roof
  step were set on this site, against these references; no second site checks them.
