# RC-P9 — A robot's capture set

**Proves:** The file contract and metric placement. See the [brief](../../docs/concept/RC-brief.md) §5.

**Proven when:** `recon` reads the set, writes a model and `provenance.json`, and with exact poses
the model's scale error is under 0.5% and its placement error under 1% of the scene's extent in the
given frame *(agreed 2026-11-24)*; the frame conversions (axes, handedness, camera-to-world) are checked by
the render's known geometry.

## What is here

| File | Does |
|---|---|
| `make_fixture.py` | Runs inside Blender (headless): builds a textured room, renders 60 frames along a robot-like path, writes the capture set, the ground truth and rendered pixel markers |
| `run_p9.py` | Reads the set with `recon.capture_set`, matches features, triangulates with the given poses fixed, writes the model, `cloud.ply` and `provenance.json` |
| `measure_p9.py` | Scores the model against the fixture's known geometry; writes `results.json` |
| `../../src/recon/capture_set.py` | The reader and the pose conversion (pure Python); `tests/test_capture_set.py` tests it |
| `../../src/recon/cli.py` | `recon inspect <set>` and `recon colmap-model <set> <out>` |

## The fixture

Blender 4.5.17 LTS (official Linux x86_64 tarball, sha256 `b7d09d1a…0b8d` checked against
download.blender.org, unpacked into `~/.local/opt/`, no system install). A 6 × 5 × 2.8 m room whose
corners are not at the origin (x −1.5…4.5, y −2…3, z 0…2.8), four textured objects (a sphere, a
cylinder, a low box, a tall box), world-space procedural textures (Voronoi cells, fine noise and
speckle, strong contrast, no repetition). Cycles on the CPU, 32 samples with denoising, 1280 × 960,
Standard view transform, a fixed seed per frame. The camera runs a loop at 1.2 m height, heading
swinging ±35° about the inward direction, no roll, 60 frames. Intrinsics come from the Blender
lens: 24 mm on a 36 mm sensor width gives fx = fy = 853.333, cx = 640, cy = 480.

The capture set follows [robotics-lab's format](../../docs/wip/robotics-lab-contract.md) with the
[amendments](../../docs/wip/capture-set-amendments.md) 3 (`pose_convention`) in use:

```text
p9-room/h120/            manifest.json  images.json  cameras.json  images/000001.png …
p9-room/ground_truth.json            room planes and corners, object geometry, markers, extent
p9-room/h120.marker_pixels.json      rendered marker centroids at every fifth frame
```

Frame `map`: z up, right-handed, metres (REP-103). Each pose is the camera's, `source: truth`,
camera-to-world, with Blender's own camera axes (`camera_axes: opengl`: looks down −Z, +Y up) and
the orientation as a quaternion named `{x, y, z, w}`. Nothing in the set is converted by the
writer; `recon` converts on ingest (`camera_axes` opengl to opencv, camera-to-world to
world-to-camera) and records the conversion in `provenance.json`. Images are PNG with a sha256
each in `images.json`.

## Reproduce

```bash
F=~/.cache/recce/datasets/fixtures/p9-room
~/.local/opt/blender-4.5.17-linux-x64/blender -b -P make_fixture.py -- --out $F --height 1.2 --name h120
cd prototypes/RC-P9-robot-capture
uv run recon inspect $F/h120
uv run python run_p9.py $F/h120 ~/.cache/recce/runs/p9/h120 --free
uv run python measure_p9.py $F/h120 ~/.cache/recce/runs/p9/h120 $F
```

The render takes about 30 minutes on 8 threads of the X3 (about 20 s a frame). The prototype
environment installs `recon` as an editable path dependency (`uv add --editable ../../`); the root
package has no pycolmap dependency.

## Method

- **Model.** SIFT (pycolmap defaults) and exhaustive matching with geometric verification; the
  cameras and poses from the set are held fixed and `pycolmap.triangulate_points` makes the points.
  The extractor numbers images in thread order, so the given model takes the database's image ids.
- **Scale.** The distance between each pair of fitted opposite room planes (x, y, z) against the
  true room size. A plane is the densest 2 cm slab within 30 cm of the true wall, then a
  least-squares fit to the points within 3 cm of that slab; points inside an object's bounding
  box (grown 5 cm) and outside the room are excluded. Points have a track of at least 3 views and
  a reprojection error under 1 px.
- **Placement.** The eight room corners (intersections of the fitted planes), a sphere fit to the
  sphere's centre, a circle fit to the cylinder's axis and the low box's top height, each
  against the truth in the map frame, divided by the scene extent (the room's bounding-box
  diagonal, 8.297 m). The reported figure is the largest of the eleven.
- **Frames.** (a) The floor normal against +z, and the ceiling above the floor, +x and +y walls
  on the positive sides. (b) Seven emissive spheres sit at room corners; a second render shows
  only them, and their centroids (sub-pixel, colour-coded) are compared with the true positions
  projected through the converted poses. Two deliberately wrong conversions are run as negative
  controls. (c) A pose-free incremental model, Sim(3)-aligned onto the given camera centres.

## Results

Status: **proven (2026-11-24)** on the 1.2 m fixture, with exact poses: the three thresholds hold.
`measure_p9.py` prints `PASS`.

| Check | Measured | Threshold |
|---|---|---|
| Scale error, worst of x, y, z room spans | 0.021% (x 0.012%, y 0.012%, z −0.021%) | < 0.5% |
| Placement error, worst of 11 positions | 0.015 m = 0.18% of the 8.297 m extent | < 1% |
| Placement error, median of 11 | 0.0007 m = 0.008% of extent | |
| Room corners (8), error | 0.0002 to 0.0014 m | |
| Sphere centre error | 0.015 m (radius 0.409 against 0.400; the bottom is out of view) | |
| Cylinder axis error | 0.006 m | |
| Low box top height | 0.6999 m against 0.700 | |
| Wall and floor normals | within 0.02° of the axes | |
| Floor normal to +z | 0.001° | frame |
| Rendered markers, given convention | 22 of 22 within 2 px; median 0.056 px, max 0.164 px | frame |
| Control: camera axes read as OpenCV | 0 of 22 in front of the camera | must fail |
| Control: world read as y-up | 0 of 22 within 2 px; median 857 px | must fail |
| Model | 60 of 60 images, 76 167 points, 0.215 px mean reprojection error | |
| Pose-free run, Sim(3) onto given camera centres | 60 of 60 registered; centre residual 0.0001 m median, 0.0004 m max (0.005% of extent) | |

Timings on the X3 (CPU, shared): features 6.7 s, matching 13.4 s, triangulation 10.6 s, free
incremental map 59.5 s. `provenance.json` records the input sha256 of the three description files and
the 60 images, the tool and pycolmap versions, the parameters, the frame and axes, the conversion
applied, the scale state (`metric from given poses`, `exact: true`, `poses_refined: false`) and the
times.

## Not covered

- **A Gazebo set from robotics-lab.** It does not exist yet; the fixture is a Blender render. The
  Gazebo camera model, its distortion and its pose export (a runfile with `[w, x, y, z]`) are
  untested.
- **Noisy poses.** Every pose is exact and `source: truth`. Belief poses (SLAM drift, ARKit) need
  pose refinement, weights from `pose_sigma` and a statement of refined poses; none is built.
  Whether the scale error stays under 0.5% with noisy poses is not measured.
- **The low camera.** The 0.3 m variant of the path is not rendered; only the 1.2 m set is
  measured.
- **Real photographs.** The render has no lens distortion, no noise beyond Cycles' denoised
  samples, no motion blur, no exposure variation, and a texture designed for SIFT. Scale and
  placement here measure the pipeline's geometry, not its behaviour on real captures; the near-zero
  residuals (a fraction of a millimetre on the room planes) reflect that.
- **Frame identity and uncertainty.** `site`, `targets`, `frame_id` and `pose_sigma` are not read;
  `world_up: +y` conversion is implemented and unit-tested but not exercised on a render.
- **`recon build`.** The root `recon` command reads and converts (`inspect`, `colmap-model`); the
  reconstruction runs from `run_p9.py` because pycolmap is not a root dependency. A single
  `recon build <set> <out>` command is not wired.
- **Determinism.** Same input and parameters give the same points up to the multi-threaded SIFT
  and matching order; two runs are not compared byte for byte.
- **Mesh and splat.** The model is a point cloud (`cloud.ply`, plus the COLMAP model); no mesh.
- **Depth, distortion, several sensors, per-image intrinsics.** The reader takes one pinhole
  sensor with no distortion; other models raise an error.
- **Scale-from-the-free-run.** The pose-free run's Sim(3) scale (0.468 given metres per free
  unit) is arbitrary by construction; it serves as a consistency check, not as a scale
  measurement.
