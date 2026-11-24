# Robotics-lab: what it hands over and what it expects back

Input to the brief and to the capture-set RFC. Sources: robotics-lab's RFC-0025 §5 and §5.1
([chipi/robotics-lab](https://github.com/chipi/robotics-lab), `docs/rfc/RFC-0025-mvp1-to-mvp2.md`; Accepted 2026-11-23,
nothing built), and a message from the robotics-lab project on 2026-11-23. These are that
project's requirements; this project owns its design.

## The seam

- Two repositories, joined by a file contract: a command line plus versioned files. Neither
  imports the other. Neither project writes into the other's repository.
- Command line shape proposed there: `recon --images D --manifest M --out O`.
- Manifest versioning: a reader accepts its own and older versions and refuses a newer one.
- Agreed points get folded into RFC-0025 §5.1 by the robotics-lab project. Proposals go to it as
  messages, not commits.

## The capture set (proposed there, to be versioned together)

```text
<capture set>/
  manifest.json      # "manifest": N; run id; frames; axes; units; clock; source run, stream, sha256 per chunk
  images/000001.png  # lossless or uncompressed stills, never lossy
  depth/000001.png   # optional; 16-bit, mm; same index as images/; 0 = no data
  images.json        # per image: file, wall_ns, sensor id, camera pose + frame + source (truth|belief), actual settings
  cameras.json       # per sensor: intrinsics, distortion, resolution, mount (camera to base); all optional
```

- Exposure, gain and white balance locked for a capture; actual per-frame values recorded.
- No processing applied: no undistortion, gamma or contrast. Colour normalisation is this
  project's job.
- Poses are the camera's pose (not the robot's), nearest tick within 0.1 s; right-handed, z up,
  metres. Priors, not truth — except in a simulator, where `source: truth` is exact.
- Wall-clock nanoseconds plus a clock epoch, so a set spanning a simulator reset is not misread.

## What it wants back

- A mesh, point cloud or splat in an open format (`mesh.ply`, `cloud.ply` in its diagram).
- Known scale and a placeable frame: metric in the frame of the given poses, or an explicit
  transform with the scale stated. No poses in → say the scale is arbitrary. RFC-0025 calls this
  "the main trap".
- `provenance.json`: input checksums, tool and version, parameters, frame, scale, time.
- Poses and intrinsics optional on input; a statement of whether poses were refined, and the
  refined poses if so.
- Same input and parameters → same output, as far as possible.
- `gaps.json` beside `provenance.json`, pulled (decided 2026-11-24, recorded in robotics-lab's
  RFC-0025 §5.1, "The gap list"; design in [gap-list interface](gap-list-interface.md)).

## Settled since (2026-11-24)

The project is named Recce (this repository, `chipi/recce`); the licence is MIT. A Recce model may
feed a Gazebo world: robotics-lab designs the import in its MVP 2 (its RFC-0025 Q21). The
manifest gains `site` and `targets`; frame identity is robotics-lab's to mint, one id per map of a
site; capture is triggered by a `capture_view` goal kind after the Burger's cameras. Details in
the [gap-list interface](gap-list-interface.md), "The operator's decisions".

## Left open for this project

Splat, mesh and point-cloud
formats; colour normalisation; capture needs (overlap, speed, blur, frame count) — robotics-lab
wants these as input to how a robot drives a capture; where it runs and how
large a set may be (uncompressed 640×480 at 30 Hz is about 1.7 GB per minute); how a result is
placed into its frames; whether a model is ever used by a mapper or a judge (a pleasing model is
not collision-safe). Privacy: home scans hold faces, screens and documents, so retention matters.

## Robotics-lab today

- No real camera images exist yet. The Microduck is simulated (MuJoCo, 8×8 ToF depth, IMU,
  odometry; its "camera" is a stand-in recogniser). The NXT has no camera.
- MVP 2 is a TurtleBot3 Burger on ROS 2 Jazzy, Gazebo first; the real robot's first upgrade is an
  RGB camera plus a depth camera, model not chosen. The only measured stream is 640×480 at 30 Hz
  in Gazebo.
- Runs are MCAP (format 2); image streams live in companion `streams/<id>.mcap` files.
- Viewers: Rerun 0.43.2, Lichtblick, three.js (STL meshes). Nothing there reads PLY, glTF or
  splats yet; Rerun has unused `Mesh3D` and `GaussianSplats3D` archetypes.
- Offered: a Gazebo capture set with exact poses as an early test fixture.
