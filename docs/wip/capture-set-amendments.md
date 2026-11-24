# Capture-set format: amendments to propose to robotics-lab

Working note. The capture-set format in robotics-lab's RFC-0025 §5.1 (summarised in
[robotics-lab contract](robotics-lab-contract.md)) was written for a robot's camera. This project's
own iPhone capture app (PG-P11) and its ingest need a few additions. They are proposed here, and
sent to the robotics-lab project once PG-P1 has shown what the ingest actually needs. All are
additive: a reader of the current version keeps working on sets that do not use them.

**Status:** draft, not yet sent.

## 1. Intrinsics per image, not only per sensor

**Why.** A phone's intrinsics change frame to frame with autofocus and stabilisation (ARKit reports
`ARCamera.intrinsics` per frame — *to verify in the 2026-11-24 verification note*). A single
`cameras.json` entry per sensor cannot hold that.

**Proposal.** `cameras.json` keeps the per-sensor calibration as the default. `images.json` may
carry an optional `intrinsics` object per image (`fx`, `fy`, `cx`, `cy`, plus `distortion` with its
model name) that overrides the sensor's for that image.

## 2. An image format field

**Why.** `images/NNNNNN.png` fixes the format. A phone or a camera produces HEIC, ProRAW DNG, NEF or
ARW, and re-encoding RAW to PNG throws away what the develop stage needs.

**Proposal.** Images keep the six-digit index name but take their native extension; `images.json`
gains `format` per image (`png`, `jpeg`, `heic`, `dng`, `nef`, `arw`, …) and `bit_depth`. The rule
"lossless or uncompressed, never lossy" stays for robots; a set states `lossy: true` when it carries
HEIC or JPEG, so the engine knows.

## 3. Pose direction and axis convention, stated per set

**Why.** ARKit's world frame is y-up; RFC-0025 says right-handed, z-up, metres. Camera-to-world and
world-to-camera are both common. Nothing in the set says which a pose is, and a wrong assumption
fails silently.

**Proposal.** `manifest.json` gains `pose_convention`: `{ "direction": "camera_to_world",
"camera_axes": "opencv" | "opengl", "world_up": "+z" | "+y", "handedness": "right" }`. Robots
write their convention; the iPhone app writes ARKit's as-is; the engine converts on ingest and
records the conversion in provenance. The app never converts silently.

## 4. Pose uncertainty

**Why.** Priors are weighted in bundle adjustment. ARKit reports a tracking state, SLAM a
covariance, a simulator exact truth. Without uncertainty the engine must guess the weight.

**Proposal.** Optional `pose_sigma` per image (`rotation_deg`, `position_m`) or a 6×6 covariance;
`source: truth` implies zero; a `tracking_state` string is allowed where no number exists
(ARKit's `normal`, `limited`).

## 5. Depth confidence

**Why.** iPhone LiDAR depth comes with a per-pixel confidence map; low-confidence depth should not
weigh like high-confidence depth.

**Proposal.** Optional `confidence/NNNNNN.png` (8-bit, same index), described in `manifest.json`.

## What does not change

The manifest's integer versioning rule, the clock and epoch fields, the provenance the engine
returns, the scale-state statement, and the rule that neither project imports the other.
