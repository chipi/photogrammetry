# The gap list as an interface for software

Date: 2026-11-24. Status: draft. A design note, not a decision; nothing here is built on either side.

Question from the owner: robots are a main consumer, and robotics-lab has a mission control and a planner. They need the gaps and shot cards through MCP (and the HTTP API and CLI) so their planning gets feedback from Recce. The human side is solved by shot cards ([visual ideas](visual-ideas.md), idea 21); this note solves it for other software.

Sources read, in this repository: [brief](../concept/RC-brief.md) §2 and §4, [architecture sketch](../concept/RC-architecture-sketch.md) §2, §3, §5, §9, §10, [visual ideas](visual-ideas.md), [robotics-lab contract](robotics-lab-contract.md), [capture-set amendments](capture-set-amendments.md), and `mockups/RC-M1-run/README.md` (outside `docs/`, so not linked).

Sources read, in robotics-lab (read-only, `main` of 2026-11-24), under `https://github.com/chipi/robotics-lab/blob/main/`:

- `docs/rfc/RFC-0025-mvp1-to-mvp2.md` (§3.5, §3.6, §5, §5.1)
- `docs/rfc/RFC-0005-missions.md` and `docs/rfc/RFC-0006-mission-control.md`
- `docs/rfc/RFC-0014-mission-control.md` (§3.1 to §3.5, §3.8)
- `apps/mission-control/CONTRACT.md` and `apps/mission-control/src/mission_control/mcp_server.py`
- `apps/mission-control/src/mission_control/auth.py`
- `libs/runner/CONTRACT.md` and `docs/uxs/UXS-001-miniview.md`

Marked "(inferred)": a statement I conclude rather than read.

## 1. The short design

The gap list is a versioned JSON document, `gaps.json`, written next to `provenance.json` by every reconstruction. Every face serves that one document and a small set of verbs over it. A gap carries its frame and scale state, a machine check that says whether a consumer may use its viewpoints as goals, and a stable id. The next capture set cites those ids. After the re-run, Recce returns a diff that says which gaps closed, which stayed open and why, and how far each new photo landed from the viewpoint it was meant to fill. Recce advises and never commands: reachability, no-go areas and the decision to move stay with the consumer.

### Robotics-lab's answers (2026-11-24)

Sent to the robotics-lab session on 2026-11-24; its reply, with the facts it cites checked in its
`mission-control` working copy (commit b84eea8). Decisions on its side are the operator's: the
amendments in section 6 and answers c, e and f are recommendations, not acceptances, and are
deferred to MVP 2 (MVP 1 is in wrap-up).

| Question | Answer | Kind |
|---|---|---|
| a. Does `point` take a yaw? | No. `point` is `{x, y, frame?: "site" \| "map"}` (`apps/mission-control/CONTRACT.md` line 99). RFC-0025's "contract 1.3: point gets yaw" is stale (1.3 shipped as calibration; the navigator contract is at 1.7); robotics-lab fixes that line. Yaw exists only on `start_pose {x, y, yaw}` and the `go_to_object` result `stand {x, y, yaw, frame}`. | Fact |
| a. Conventions | Yaw in radians about +z, zero along +x, counter-clockwise positive (REP-103; robotics-lab's `docs/wip/SENSORS-VS-ROS.md`). Quaternions: runfiles store `[w, x, y, z]` (ADR-0016); the wire to Foxglove and ROS uses named `{x, y, z, w}` (`libs/runfile/src/runfile/wire.py`). | Fact |
| b. Who mints a frame identity? | Nobody today: frames are names (`site`, `map`). Since navigator contract 1.5 a goal's frame is set per goal by `start_pose`, and the answer's `placed {pose, frame}` gives mapd's frame in the map's. A site has `dock_pose {x, y, yaw, frame, robot, set_from}`. Nothing proves two maps are one frame after relocalisation; that is an open MVP 2 question. | Fact |
| c. Actor profile | Recommend robotics-lab's robot file: `capabilities.sensors` already lists `[{id, kind, ...}]` and the duck has a `camera` block; a camera entry (mount, height, pitch range, field of view) extends it. | Recommendation |
| d. MCP transport | Robotics-lab's MCP is stdio only, a client of a local HTTP API with bearer tokens; remote access is `tailscale serve` plus tokens (`docs/wip/STAGING-CUTOVER.md`). Recommend: Recce serves its own HTTP API on the tailnet with a token, and a stdio MCP server on the agent's machine is its client. | Recommendation |
| e. `capture_view` or `point` with a burst | A separate `capture_view` kind: each goal kind has one done-condition, and "a burst recorded" differs from "within 0.25 m". Needs a navigator contract bump and the capture trigger. | Recommendation |
| f. Robot claim lease | Shorter than a human's; the only precedent is Mission Control's drive lock lease (`lock/renew`). | Recommendation |

What changes here as a result:

- Viewpoints keep `planar.yaw` in REP-103 terms (radians, zero along +x, counter-clockwise), and
  any quaternion is named field by field (`{x, y, z, w}`), never a bare array.
- Until `capture_view` exists, a planner can send only a position (`point` has no heading), so a
  viewpoint's heading reaches the robot only through a human or a later goal kind. The loop in
  section 5 works for position today and for heading after the amendment.
- `frame.id` is minted by Recce from what the capture set states (run, site, dock pose), not
  read from robotics-lab; a match between two ids is a claim Recce cannot verify until the MVP 2
  frame question is answered. `usable_as_goal` stays false across frame ids.
- Recce's transport follows answer d: its HTTP API on the tailnet with tokens, a stdio MCP
  client beside the agent. Open question 4 below is answered by that.

## 2. What robotics-lab needs, in its own terms

| Need | Where robotics-lab says it | What follows for the gap list |
|---|---|---|
| Goals are small typed records with a validated schema; an unknown kind is refused | RFC-0014 §3.4.1; `CONTRACT.md`, Goals. Kinds: `point {x, y, frame?}`, `go_to_object`, `go_to_area`, `explore`, `inventory` | No kind takes a camera viewpoint. A planner turns a viewpoint into a `point` goal (position plus heading) or waits for a new kind (section 6). |
| A robot pose in a goal is planar: `{x, y, yaw}`, site frame, metres and radians | `CONTRACT.md`, `start_pose`; `libs/runner/CONTRACT.md`, `start_pose`. Yaw is radians, zero along +x, counter-clockwise positive (REP-103; robotics-lab answer a) | Each viewpoint carries a `planar` projection in that shape, with the 3D pose beside it. |
| Frames have names (`world`, `map`, `site`, robot frames); every response with a position names its `frame` | RFC-0025 §3.6; `CONTRACT.md` header; RFC-0014 §3.2.1 | The gap list names its frame on every position. |
| A run's `map` frame equals the site frame only when the robot starts at the dock; otherwise `localisation.frame` is `run` | RFC-0014 §3.5.1, §3.5.4, §3.3.2 | A frame needs an identity, not only a name: two `map` frames of two runs differ. |
| The scale trap: a model is metric in the poses' frame, or an explicit transform with the scale stated, or "arbitrary" | RFC-0025 §5, §5.1 | The gap list repeats the scale state and gates its own viewpoints on it. |
| Camera pose, not robot pose; the model job applies the mount (camera to base) | RFC-0025 §5; `cameras.json` in §5.1 | Viewpoints are camera poses. The consumer subtracts its own mount. |
| Who triggers a capture, and a scan goal to viewpoints, is "later" and "not designed" | RFC-0025 §3.5 (roadmap step 6), §5.1 | Recce cannot assume a robot action exists. The design offers one proposal (section 6). |
| Nothing reads a 3D model yet; a pleasing model is not collision-safe | RFC-0025 §3.5 ("do not build yet"), §5.1 | Gaps are advice. The consumer checks its own map. |
| A goal refused for a robot says why, in a field a client can show | RFC-0014 §3.2.1 | Each viewpoint has `usable_as_goal` and `unusable_reason`. |
| Agents are clients of one API; the MCP server exposes it with an allow-list, the client name is fixed, an agent runs on the simulator unless the operator allows more, and only the operator draws areas | RFC-0014 §3.2, §3.9; `mcp_server.py` (`ALLOWED`, `target` is `sim`); `auth.py` (a token names the client) | Recce copies the shape: tools are one call each, claims carry a client name, dismissing a gap is the operator's. |
| Agent first: anything a page shows is a command, and the reverse | UXS-001 (principle at line 23); [brief](../concept/RC-brief.md) §2 | Section 4 gives one verb list for all faces. |

How results flow back today: they do not. RFC-0025 §5 draws a model job that moves data across the seam and receives `mesh.ply`, `cloud.ply` and `provenance.json`. Nothing in robotics-lab consumes them, and RFC-0025 is Accepted with "nothing in it built". There is no return path for gaps, and no robotics-lab object a gap attaches to except two candidates: a site (RFC-0014 §3.5.1: id, name, site frame, dock pose) with its operator-drawn areas (§3.5.3: polygons in the site frame, `GET /sites/{s}/areas/at`), and the goal run (a goal run holds `result` and a `run_key`). A gap attaches to a site by the frame, and to an area by geometry, which Mission Control computes (inferred; Recce knows no areas).

## 3. The gap-list document

### 3.1 The example

The kicker case: ETH3D, no pose priors, so the scale is arbitrary. All numbers below are illustrative, not engine output. Only the style of the photo ids (`DSC_6487.JPG`) comes from the RC-M1 mock-up.

```json
{
  "gap_list": 1,
  "id": "gl-7f3a2c",
  "computed_at": "2026-11-24T14:02:11Z",
  "project": "kicker",
  "capture_set": { "id": "cs-01", "manifest": 1, "sha256": "b1c4...e9", "run_id": null,
                   "site": null, "targets": [] },
  "reconstruction": { "id": "rec-glomap-01", "strategy": "poses/glomap", "recipe": "object-walkaround",
                      "recipe_version": 1, "engine": { "name": "recon", "version": "0.0.0" },
                      "provenance": { "file": "provenance.json", "sha256": "5d0a...41" } },
  "ruleset": "gaps-1",
  "frame": {
    "name": "model", "id": "frm-rec-glomap-01",
    "axes": { "handedness": "right", "up": null, "units": "model" },
    "scale_state": "arbitrary",
    "placement": { "status": "none", "reason": "no pose priors, no markers" }
  },
  "pose_convention": { "direction": "camera_to_world", "camera_axes": "opencv" },
  "purpose": "measurement",
  "rankings": { "measurement": ["gap-0005","gap-0001","gap-0004","gap-0002","gap-0003"],
                "web_viewing": ["gap-0002","gap-0001","gap-0003","gap-0004","gap-0005"],
                "robot_localisation": ["gap-0005","gap-0004","gap-0001","gap-0002","gap-0003"],
                "game_asset": ["gap-0001","gap-0003","gap-0002","gap-0004","gap-0005"] },
  "complete_for": { "measurement": false, "web_viewing": false, "robot_localisation": false, "game_asset": false },
  "gaps": [
    { "id": "gap-0001", "kind": "thin_angle", "scope": "region",
      "status": { "state": "open", "since": "2026-11-24T14:02:11Z", "claims": [], "attempts": 0, "matched_from": null },
      "severity": { "level": "major", "score": 0.78, "basis": "median_angle_deg 6.1 < 15; depth_rel_sigma 0.21" },
      "priority": { "measurement": {"rank":2,"score":0.91}, "web_viewing": {"rank":2,"score":0.55},
                    "robot_localisation": {"rank":3,"score":0.60}, "game_asset": {"rank":1,"score":0.70} },
      "region": { "shape": "sphere", "centre": [1.10, 0.35, 0.52], "radius": 0.31, "units": "model" },
      "evidence": { "points": 4120, "photos": ["DSC_6487.JPG","DSC_6488.JPG","DSC_6490.JPG","DSC_6491.JPG"],
                    "triangulation_angle_deg": { "median": 6.1, "p10": 2.4, "p90": 11.0 },
                    "depth_rel_sigma": 0.21,
                    "ring": { "bins": 12, "bin_deg": 30, "azimuth_frame": "model",
                              "seen": [3,4,1,0,0,0,0,0,0,0,0,2], "unseen_arcs_deg": [[90,330]] } },
      "close_when": { "median_angle_deg_min": 15, "photos_min": 3, "points_min": 3000 },
      "viewpoints": [ {
        "id": "vp-0001a", "role": "primary",
        "pose": { "position": [1.92,-0.41,0.88], "look_at": [1.10,0.35,0.52], "up": null },
        "planar": null,
        "relative": { "to_photo": "DSC_6487.JPG", "orbit_deg": { "yaw": -38, "pitch": 4 }, "distance_ratio": 1.0 },
        "acceptance": { "kind": "arc", "about": "region.centre", "azimuth_range_deg": [60,150],
                        "distance_ratio_range": [0.8,1.4], "elevation_range_deg": [-10,25] },
        "tolerance": { "position_m": null, "position_ratio": 0.12, "look_at_cone_deg": 12, "roll_deg": 15 },
        "usable_as_goal": false, "unusable_reason": "scale_state_arbitrary" } ],
      "landmark": { "photo": "DSC_6487.JPG", "why": "nearest photo to the suggested viewpoint" },
      "text": { "title": "The dent on the left side is seen from one direction only",
                "instruction": "Stand where DSC_6487 was taken, orbit left about 40 degrees around the dent at the same distance, and take 3 photos 10 degrees apart.",
                "why": "Rays from the existing photos are nearly parallel, so depth is uncertain." },
      "hints": { "baseline_deg": { "min": 10, "target": 20 }, "photos": { "min": 3, "target": 5 },
                 "overlap_min": 0.6, "capture_mode": "locked_exposure" } },

    { "id": "gap-0002", "kind": "thin_angle", "scope": "region", "status": { "state": "open", "since": "2026-11-24T14:02:11Z", "claims": [], "attempts": 0, "matched_from": null },
      "severity": { "level": "major", "score": 0.66, "basis": "median_angle_deg 8.3 < 15" },
      "priority": { "measurement": {"rank":4,"score":0.60}, "web_viewing": {"rank":1,"score":0.80},
                    "robot_localisation": {"rank":4,"score":0.50}, "game_asset": {"rank":3,"score":0.52} },
      "region": { "shape": "sphere", "centre": [-0.62, 0.08, 0.47], "radius": 0.40, "units": "model" },
      "evidence": { "points": 6890, "photos": ["DSC_6521.JPG","DSC_6522.JPG","DSC_6523.JPG"],
                    "triangulation_angle_deg": { "median": 8.3, "p10": 3.0, "p90": 14.2 }, "depth_rel_sigma": 0.15,
                    "ring": { "bins": 12, "bin_deg": 30, "azimuth_frame": "model",
                              "seen": [0,0,0,0,2,3,3,1,0,0,0,0], "unseen_arcs_deg": [[0,120],[270,360]] } },
      "close_when": { "median_angle_deg_min": 15, "photos_min": 3, "points_min": 3000 },
      "viewpoints": [ { "id": "vp-0002a", "role": "primary",
        "pose": { "position": [-0.20,-0.90,0.60], "look_at": [-0.62,0.08,0.47], "up": null }, "planar": null,
        "relative": { "to_photo": "DSC_6522.JPG", "orbit_deg": { "yaw": 45, "pitch": 0 }, "distance_ratio": 1.1 },
        "acceptance": { "kind": "arc", "about": "region.centre", "azimuth_range_deg": [300,360],
                        "distance_ratio_range": [0.8,1.4], "elevation_range_deg": [-10,25] },
        "tolerance": { "position_m": null, "position_ratio": 0.12, "look_at_cone_deg": 12, "roll_deg": 15 },
        "usable_as_goal": false, "unusable_reason": "scale_state_arbitrary" } ],
      "landmark": { "photo": "DSC_6522.JPG", "why": "nearest photo to the suggested viewpoint" },
      "text": { "title": "The rear panel is seen from a narrow arc", "instruction": "From DSC_6522, orbit right about 45 degrees and shoot the panel.", "why": "Narrow viewing arc." },
      "hints": { "baseline_deg": { "min": 10, "target": 20 }, "photos": { "min": 3, "target": 5 }, "overlap_min": 0.6, "capture_mode": "locked_exposure" } },

    { "id": "gap-0003", "kind": "few_photos", "scope": "region", "status": { "state": "open", "since": "2026-11-24T14:02:11Z", "claims": [], "attempts": 0, "matched_from": null },
      "severity": { "level": "minor", "score": 0.41, "basis": "1380 points seen by exactly 2 photos" },
      "priority": { "measurement": {"rank":5,"score":0.35}, "web_viewing": {"rank":3,"score":0.45},
                    "robot_localisation": {"rank":5,"score":0.30}, "game_asset": {"rank":2,"score":0.62} },
      "region": { "shape": "sphere", "centre": [0.15, 1.02, 0.30], "radius": 0.25, "units": "model" },
      "evidence": { "points": 1380, "photos": ["DSC_6540.JPG","DSC_6541.JPG"], "observations_per_point": { "min": 2, "median": 2 },
                    "triangulation_angle_deg": { "median": 17.0, "p10": 9.0, "p90": 24.0 } },
      "close_when": { "observations_per_point_median_min": 3, "photos_min": 3 },
      "viewpoints": [ { "id": "vp-0003a", "role": "primary",
        "pose": { "position": [0.40,1.60,0.55], "look_at": [0.15,1.02,0.30], "up": null }, "planar": null,
        "relative": { "to_photo": "DSC_6541.JPG", "orbit_deg": { "yaw": 0, "pitch": 10 }, "distance_ratio": 0.9 },
        "acceptance": { "kind": "arc", "about": "region.centre", "azimuth_range_deg": [80,130],
                        "distance_ratio_range": [0.7,1.3], "elevation_range_deg": [0,30] },
        "tolerance": { "position_m": null, "position_ratio": 0.15, "look_at_cone_deg": 15, "roll_deg": 20 },
        "usable_as_goal": false, "unusable_reason": "scale_state_arbitrary" } ],
      "landmark": { "photo": "DSC_6541.JPG", "why": "nearest photo to the suggested viewpoint" },
      "text": { "title": "Underside of the front edge: two photos only", "instruction": "From DSC_6541, step a little closer and tilt up 10 degrees; take 2 extra photos.", "why": "Points seen by two photos cannot be checked against a third." },
      "hints": { "baseline_deg": { "min": 5, "target": 10 }, "photos": { "min": 2, "target": 3 }, "overlap_min": 0.7, "capture_mode": "locked_exposure" } },

    { "id": "gap-0004", "kind": "photo_not_joined", "scope": "photo",
      "status": { "state": "open", "since": "2026-11-24T14:02:11Z", "claims": [], "attempts": 0, "matched_from": null },
      "severity": { "level": "major", "score": 0.70, "basis": "image not registered; location unknown" },
      "priority": { "measurement": {"rank":3,"score":0.72}, "web_viewing": {"rank":4,"score":0.30},
                    "robot_localisation": {"rank":2,"score":0.95}, "game_asset": {"rank":4,"score":0.40} },
      "region": null,
      "evidence": { "photo": { "id": "DSC_6602.JPG", "sha256": "77ae...0c", "sensor": "cam-0" },
                    "solver": { "tried_pairs": 40, "best_inliers": 11, "reason_code": "too_few_matches" },
                    "prior_pose": null },
      "close_when": { "photo_registered": true },
      "viewpoints": [],
      "landmark": null,
      "text": { "title": "DSC_6602 did not join the model", "instruction": "Retake the shot from the same place with a neighbouring view: two photos that overlap it by half.", "why": "Only 11 consistent matches; the solver needs more." },
      "hints": { "photos": { "min": 2, "target": 3 }, "overlap_min": 0.5, "retake_of": "DSC_6602.JPG" } },

    { "id": "gap-0005", "kind": "no_scale", "scope": "reconstruction",
      "status": { "state": "open", "since": "2026-11-24T14:02:11Z", "claims": [], "attempts": 0, "matched_from": null },
      "severity": { "level": "major", "score": 0.85, "basis": "scale_state arbitrary; no priors, no markers" },
      "priority": { "measurement": {"rank":1,"score":1.00}, "web_viewing": {"rank":5,"score":0.05},
                    "robot_localisation": {"rank":1,"score":1.00}, "game_asset": {"rank":5,"score":0.60} },
      "region": null,
      "evidence": { "pose_priors": 0, "markers": 0, "priors_rejected": null },
      "close_when": { "scale_state_not": "arbitrary" },
      "viewpoints": [],
      "landmark": null,
      "text": { "title": "The model has no real-world size", "instruction": "Put a scale bar or a measured object in view of at least 3 photos, or tell Recce one measured distance.", "why": "Without a reference length every size and distance is unitless." },
      "hints": { "reference": { "kind": "known_length", "min_visible_in_photos": 3 }, "alternatives": ["pose_priors", "marker", "scale_hint"] } }
  ]
}
```

### 3.2 The fields

Top level.

- `gap_list` is the integer schema version. A reader accepts its own and older versions and refuses a newer one, the rule robotics-lab already applies to `manifest.json` (RFC-0025 §5.1). Fields are only added within a version; a reader ignores fields and `kind` values it does not know.
- `id` is content-addressed from the reconstruction, the ruleset and the thresholds. The same input gives the same id and the same list, as `provenance.json` promises.
- `capture_set` echoes the manifest: `id`, `manifest` version, `sha256`, the source `run_id`, an optional `site` (proposal, section 6) and `targets`, the gap ids this capture set was taken for.
- `reconstruction` names the strategy, recipe, engine version and the `provenance.json` it belongs to. Two strategies on one capture are two reconstructions and two gap lists (the RC-M1 mock-up shows GLOMAP and incremental side by side); a gap never moves between them.
- `ruleset` names the thresholds that produced the list (`gaps-1`: 15 degrees median angle, 3 photos, and so on; the values are placeholders until RC-P3 measures them (inferred)).
- `purpose`, `rankings`, `complete_for`: the list is ranked for all four purposes at once, so a consumer picks without a second call. `complete_for` is true when no gap of level major or above remains open for that purpose.
- `pose_convention` states how a pose is read. It follows the manifest field proposed in [capture-set amendments](capture-set-amendments.md) §3.

`frame` (critical).

- `name` and `id`: the id changes whenever the frame's definition changes. A consumer compares it with its own frame identity before using a position.
- `axes`: `up` is `"+z"` when the frame is gravity-aligned and `null` when it is not (a pure structure-from-motion frame has no known up).
- `units`: `"m"` or `"model"`.
- `scale_state`: `metric`, `metric-from-priors`, `scaled-by-markers` or `arbitrary` ([architecture sketch](../concept/RC-architecture-sketch.md) §2).
- `placement`: whether the frame is registered to a named external frame. `status` is `exact` (priors with `source: truth`), `estimated` (priors with `source: belief`, with `residual_rms_m`, `priors_used`, `priors_rejected`) or `none`.

Each gap.

- `id`: allocated by Recce per project, never reused, kept when a gap is matched across re-runs (`status.matched_from` names the earlier list and gap). Matching is by kind plus region overlap, or by photo id. A merge or split is recorded in the diff.
- `kind`: `thin_angle`, `few_photos`, `photo_not_joined`, `no_scale` now; `holes`, `blurred_photo`, `missing_colour_reference`, `disconnected_components` later. `scope` says whether the gap lives in a `region`, a `photo` or the whole `reconstruction`.
- `severity`: intrinsic to the evidence and the same for every purpose. `level` is `critical`, `major`, `minor` or `info`; `score` is 0 to 1; `basis` is a plain statement of the numbers behind it.
- `priority`: rank and score per purpose. Purpose changes order and level of urgency, never the evidence. A `no_scale` gap is first for measurement and rank 5 for web viewing.
- `region`: sphere (`centre`, `radius`) in the frame's units, or `null` where the location is unknown or does not apply.
- `evidence`: points, photo ids, triangulation angle percentiles, a scale-free `depth_rel_sigma` (depth uncertainty as a fraction of range, valid in any frame), the coverage `ring` (azimuth bins; `seen` holds photo counts per bin; `unseen_arcs_deg` lists the empty arcs), observations per point, the solver's `reason_code` for a photo that did not join, and `prior_pose` where the image carried one (a robot's belief), which tells where the photo was probably taken.
- `close_when`: the machine-checkable criterion the re-run evaluates. It travels with the gap so the consumer knows what "done" means before it plans.
- `viewpoints`: see below.
- `landmark`: the nearest existing photo, used to recognise the spot. It is a photo id; the image itself is served only to clients holding the image scope (section 6).
- `text`: the human card (`title`, `instruction`, `why`). The same text feeds the web shot card, so humans and machines read one source.
- `hints`: how much to capture: `baseline_deg` and `baseline_m` (metric only), `photos` min and target, `overlap_min`, `capture_mode`, and per kind extras such as `retake_of` or the scale `reference` kinds.
- `status`: the lifecycle (section 3.4).

### 3.3 Viewpoints, and what a consumer may and may not do

A viewpoint is a candidate, never an order. Fields: `pose` (position, `look_at`, `up`; no quaternion is primary, because robotics-lab states no order for its quaternions (RFC-0025 §3.3, truth row); an optional `quaternion_xyzw` is named when present), `planar` (`{x, y, yaw, frame}` in the robotics-lab shape plus `camera_height_m`, present only when the frame is gravity-aligned and metric), `relative` (the viewpoint expressed from a landmark photo: orbit angles about the region centre and a distance ratio; scale-free), `acceptance` (an arc or annular sector, so a planner may pick any reachable point inside it), `tolerance` (position radius, a cone half-angle for the look-at direction, roll), and the gate: `usable_as_goal` with `unusable_reason`.

Recce knows no free space. The `pose` may lie inside a wall. The `acceptance` region is how a planner finds a reachable point; the planner checks reachability, no-go areas and clearances (RFC-0014 §3.4.8) itself.

Rules by frame state. `usable_as_goal` is computed by Recce from this table; a consumer reads the flag and does not re-derive it.

| `scale_state` | `placement.status` | Consumer may | Consumer may not |
|---|---|---|---|
| `arbitrary` | `none` | Use kind, severity, priority, counts, evidence ratios, `text`, `hints` in counts and angles, the landmark photo, `relative` and its distance ratio. Show a human the card. | Treat any position, radius, baseline or tolerance as metres; send `pose` or `planar` as a goal; write anything into a map; compare positions with its own frame. `up` is `null`: no heading from the model frame is a compass or gravity direction. |
| `scaled-by-markers` | `none` | The above, plus metric sizes and distances inside the model. | Place viewpoints in the robot frame: the frame is the markers', not the robot's. A consumer with its own alignment (three or more point pairs, a landmark photo with a known pose) may transform it; Recce does not vouch for the result. |
| `metric-from-priors` | `estimated`, frame id equal to the consumer's | Use `pose` and `planar` as candidate goals after its own reachability check, and the tolerance as acceptance bounds. `usable_as_goal` is true only where `residual_rms_m` is under half the viewpoint's `position_m`. | Skip the check against its map and guardrails; treat a viewpoint as collision-safe. |
| `metric-from-priors` | `estimated`, frame id different (another run's `map`) | Use as `scaled-by-markers` above. | Assume that two `map` frames match (RFC-0014 §3.5.4). |
| `metric` or priors with `source: truth` | `exact` | As the row above `estimated`, with the tolerance at its tightest. Typical case: a simulator capture set. | Treat truth as safe to drive. |

The same rule in one line: Recce never turns a number into metres that the frame does not carry. When it cannot, it says so in `unusable_reason` (`scale_state_arbitrary`, `frame_not_registered`, `frame_id_mismatch`, `residual_too_large`, `up_unknown`).

A second, short example, the same gap in a robot capture set with exact priors (all values illustrative):

```json
"frame": { "name": "map", "id": "frm-run-0042-map", "axes": {"handedness":"right","up":"+z","units":"m"},
           "scale_state": "metric-from-priors",
           "placement": { "status": "exact", "registered_to": {"name": "site", "id": "site-home"},
                          "residual_rms_m": 0.02, "priors_used": 212, "priors_rejected": 0 } },
"viewpoints": [ { "id": "vp-0007a", "role": "primary",
  "pose": { "position": [2.31,1.40,0.18], "look_at": [3.05,2.12,0.22], "up": [0,0,1] },
  "planar": { "x": 2.31, "y": 1.40, "yaw": 0.77, "camera_height_m": 0.18, "frame": "site" },
  "tolerance": { "position_m": 0.15, "look_at_cone_deg": 10, "roll_deg": 10 },
  "usable_as_goal": true, "unusable_reason": null } ]
```

A `no_scale` gap on a robot capture set is a contract failure, not a capture gap: the set promised priors, so the gap's `evidence.priors_rejected` names why the engine did not use them, and its severity for `robot_localisation` is `critical`.

### 3.4 The lifecycle

`status.state` moves as follows.

| State | Meaning | Set by |
|---|---|---|
| `open` | Found, nobody has claimed it | Recce, on computing |
| `planned` | A consumer has a plan for it: `claims` holds `{client, plan_ref, until}` | The consumer, `mark_gap_planned`; `until` expires like a lock lease (RFC-0017 lease, inferred as a model) and the gap returns to `open` |
| `captured` | A capture set naming the gap in `targets` was ingested; the re-run is pending | Recce, on ingest |
| `closed` | The re-run met `close_when` | Recce |
| `still_open` | The re-run ran, the gap was targeted and `close_when` is not met; `attempts` increments and `last_delta` holds the change in evidence | Recce |
| `dismissed` | The operator waived it, with a reason ("unreachable", "not needed") | The operator only; an agent token cannot (as areas, `mcp_server.py`) |
| `superseded` | Merged into another gap by the matcher | Recce |

Several clients can claim one gap (a phone and a robot); claims are information, not locks, because a gap is not a safety resource. A gap not targeted by a capture keeps its state across a re-run if it still exists, and closes with `closed_by: "incidental"` if the new data met `close_when` anyway.

## 4. Faces: one verb list

One list of verbs; each face spells it in its own way. Reads are open to every client token; the writes noted below need the named scope.

| Verb | MCP tool | HTTP (proposed prefix `/api/v1`) | CLI |
|---|---|---|---|
| list | `list_gaps(project, reconstruction?, purpose?, status?, kind?, min_severity?, since_seq?)` | `GET /projects/{p}/gaps?...` | `recon gaps list` |
| get | `get_gap(id)` | `GET /gaps/{id}` | `recon gaps get ID` |
| brief | `gap_brief(project, purpose, actor?, max_gaps?, frame_id?)` | `POST /projects/{p}/gaps/brief` | `recon gaps brief --purpose P --actor FILE` |
| card | `get_shot_card(id, format)` (`json`, `markdown`, `png`) | `GET /gaps/{id}/card` | `recon gaps card ID` |
| plan | `mark_gap_planned(ids, plan_ref, until?)` (scope `plan`) | `POST /gaps/{id}/plan` | `recon gaps plan ID --ref R` |
| release | `release_gap(ids)` (scope `plan`) | `DELETE /gaps/{id}/plan` | `recon gaps release ID` |
| dismiss | not offered to agents | `POST /gaps/{id}/dismiss` (scope `operator`) | `recon gaps dismiss ID --reason R` |
| diff | `get_gap_diff(from, to?)` | `GET /gap-lists/{to}/diff?from=` | `recon gaps diff A.json B.json` |
| watch | `watch_gaps(project, since_seq)` (poll) and the resource subscription | `GET /events?since=` (server-sent events) | `recon gaps watch` |
| export | `export_gap_list(id)` | `GET /gap-lists/{id}` | `recon gaps export`, and `gaps.json` in every `--out` |

Notes on each.

- `gap_brief` is the machine form of a shot card list. Input: a purpose, an `actor` profile (kind `phone`, `drone`, `ground-robot`, `arm`; camera `height_m`, `pitch_range_deg`, `fov_deg`, `min_standoff_m`; a ground robot's profile is derivable from its `cameras.json` mount and robot file (inferred)), and optionally the consumer's `frame_id`. Output: the top `max_gaps` for that purpose, re-ranked, each with only the viewpoints the actor can reach in principle (camera height and pitch range checked, no map), `planar` filled for planar actors, a `dropped` list with the reason per omitted gap, and the same `frame` block. A consumer that skips `gap_brief` and reads `list_gaps` gets the full document.
- `mark_gap_planned` is how the loop closes on the Recce side before capture. It records the client name from the token (the token is the identity, `auth.py`) and a `plan_ref` that is opaque to Recce, for example `mc:goal-run/123`.
- `get_gap_diff` answers "what changed": per gap `closed`, `still_open` with `delta`, `new`, `regressed`, `merged`, and a `targets_report` (section 5, step 8).
- Resources. The gap list is also an MCP resource: `recon://projects/{p}/gaps` (the latest list), `recon://gap-lists/{id}` and `recon://gaps/{id}`. A client that subscribes receives resource-updated notifications when a new list or a status change lands. The dependable path is the poll with `since_seq`: robotics-lab's own MCP server exposes tools only (inferred from `mcp_server.py`), and its event stream already uses numbered events with `since` and a `gap` event for a ring that no longer holds the missed ones (`CONTRACT.md`, The event stream). Recce copies that: events `gap-list-ready`, `gap-status`, `gap-diff-ready`, each with `seq`.
- Shape of replies. Success is `{"ok": true, ...}`, failure `{"ok": false, "error": {"code", "message"}}`, with honest status codes: the robotics-lab envelope, so a client written for one speaks to the other (proposal).
- Auth. Per-client bearer tokens, the token names the client; `plan` and `release` need scope `plan`; images (landmark photos) need scope `images`; `dismiss` needs `operator`. The MCP server is a client of the HTTP API with an allow-list of routes, as robotics-lab's is (`mcp_server.py`). Its transport is open (section 8).
- File mode. `recon --images D --manifest M --out O` writes `O/gaps.json` with no server. `--previous O1/gaps.json` carries gap ids and lineage into the new list, so the loop works on files alone; statuses `planned` and `dismissed` need the server and do not exist in file mode.

## 5. The loop

1. **Capture.** A robot or phone writes a capture set. The manifest carries the frame, the pose priors (`source: truth|belief`) and, new, the `frame` identity and the `site` ([capture-set amendments](capture-set-amendments.md) already add `pose_convention`; section 6 adds the rest).
2. **Reconstruct.** `recon` or the API runs the stages and writes `gaps.json` beside `provenance.json`. The frame block carries the placement result.
3. **Fetch.** The planner (an outside agent holding both the `mission-control` and a `recon` MCP server, or Mission Control's model job) calls `gap_brief(project, purpose="robot_localisation", actor=<profile>, frame_id=<site frame id>)`.
4. **Check the frame.** If every returned viewpoint has `usable_as_goal: true`, the planner proceeds. If not, it uses the qualitative parts only (`text`, `relative`, counts) and either asks the operator for a capture by hand or raises a scale gap to the operator. No guess substitutes for the flag.
5. **Transform and plan.** The planner transforms into its goal frame: none when the frame ids match, else its own transform for that run, which Mission Control knows from the dock pose (`start_pose`, `dock_pose`: `CONTRACT.md`). It subtracts the camera mount to get a base pose (RFC-0025 §5), picks a reachable point inside `acceptance`, checks its map and guardrails, then creates a goal: today `point {x, y, frame}`, with no heading (robotics-lab answer a; RFC-0025's yaw line is stale), and `capture_view` once it exists. An agent's run goes to the simulator first (`target: sim`), and a real run needs the operator, so a gap list is rehearsed in Gazebo before it moves a real robot (RFC-0014 §3.4.2, `mcp_server.py`).
6. **Claim.** The planner calls `mark_gap_planned(ids, plan_ref="mc:goal-run/123")`.
7. **Execute and record.** The robot reaches the stand pose, takes the burst (`hints.photos`, `hints.baseline_deg`) with locked settings, and the model job writes a new capture set with `targets: [{"gap":"gap-0001","viewpoint":"vp-0001a","goal_run":123}]` and the same `site` and `frame` identity.
8. **Re-run and report.** Recce ingests the set into the same project and sets the targeted gaps to `captured`. The cached stages are reused, so only what the new photos touch re-runs ([architecture sketch](../concept/RC-architecture-sketch.md) §3). It computes a new gap list with matched ids and a diff. The diff reports, per gap: `closed`, `still_open` with the evidence delta (for example median angle 6.1 to 11.8 degrees against 15 needed, so "one more photo from the far side"), `new` gaps the extra photos exposed, `regressed` gaps, and a `targets_report` per target: which new photos registered, `viewpoint_hit` (`position_error`, `look_at_error_deg` against the tolerance), and a `miss_reason` (`photo_not_joined`, `outside_tolerance`, `blurred`, `wrong_region`). The `targets_report` is the feedback for planning: a consistent 0.3 m stand-off error tells the planner that its mount or localisation has a bias.
9. **Notify.** `gap-diff-ready` on the event stream and the resource update. The planner reads `get_gap_diff`, updates its plan, and repeats until `complete_for[purpose]` is true or the operator dismisses what is left.

## 6. Changes needed

All proposals. Neither project writes into the other's repository; robotics-lab items go as messages, as [the contract note](robotics-lab-contract.md) records.

Recce.

- Gap computation as a stage that writes `gaps.json`, with the RC-P3 quality state as its input. Thresholds are data in the ruleset.
- A `placement` result in the reconstruction's frame (fit of the priors to the reconstruction, residual, rejected priors) so `frame.placement` exists. This sits on RC-P9.
- Gap lineage and status in the metadata store (open question 3 of the sketch).
- The verbs of section 4 on the three faces, one implementation behind them.
- The manifest reader accepts `site`, `frame`, `targets`, and writes them back into `gaps.json`.
- Fixtures: the RC-P9 Blender room with exact poses (expected: planar viewpoints usable), the kicker (expected: nothing usable, `no_scale` present), and one capture set with deliberately wrong priors (expected: `no_scale` critical for robots).
- Image scope for landmark photos; gap lists never embed pixels. Home scans hold faces and documents, and the lists reveal room layout, so the retention rules of the sketch's §8 apply to gap lists too.

Robotics-lab (amendments to RFC-0025 §5.1, proposed).

- "What we want back" gains `gaps.json`, with the frame rules of section 3.3.
- The manifest gains `site {id, frame_id}`, `frame_id` for the pose frame (a run's `map` plus its start identity), and `targets`.
- A goal kind for capture, in RFC-0014 §3.4.1's style: `capture_view {pose or planar, tolerance, burst {photos, baseline_deg}, gap_ids}`, done when the burst is recorded, `result` naming the capture set. Without it, a planner can send the robot to the stand pose but nothing triggers the burst (RFC-0025 §5.1 leaves "who triggers a capture" open).
- The robot file's `capabilities` gain a camera entry (mount, height, pitch range, field of view) so an actor profile is derived, not typed.
- Site export carries the dock pose and the frame identity, so a planner proves a frame match.
- A named place for a recon MCP server in the agent's configuration, beside `mission-control`, with its own token and client name.

## 7. Alternatives considered

- **Push (Recce calls Mission Control or a webhook) against pull (consumer reads).** Pull wins. The seam is files and a command line, and neither project writes into the other (RFC-0025 §5); Recce does not know a consumer's address; a consumer that is offline loses nothing. A push adds failure handling for the consumer that Recce has no reason to own. A CLI `--on-ready COMMAND` hook is the one push offered, for local scripts.
- **A ROS-style action** (`CaptureViews.action`: goal, feedback, result). Rejected as the primary shape. A capture-and-reconstruct session spans hours and days and many processes, so a goal-feedback-result pairing between two live nodes does not model it; a document persists, diffs, replays in a test, and is read by an agent or a human. robotics-lab is ROS-aligned in names, with no ROS foundation yet (ADR-0001) and a ROS 2 bridge only in MVP 2, so an action needs the bridge first. A thin adapter that publishes `planar` as `geometry_msgs/PoseStamped` can follow the bridge (inferred). An action does fit one case, live progress while the robot shoots a burst; that case is out of scope here.
- **Gaps inside `provenance.json`.** Rejected. Provenance records how a result was made and is fixed by its hashes; gap status changes with every claim and re-run, and the gap ids must outlive any one reconstruction. The two documents point at each other by hash.
- **One document per purpose.** Rejected for the list; accepted for the brief. The list stays purpose-neutral in evidence and carries all four rankings. `gap_brief` renders a per-purpose, per-actor view on request.
- **Recce emits Mission Control goals.** Rejected. It couples Recce to goal kinds, frames and guardrails it does not own, and a goal refused by a navigator would need a feedback path anyway. Recce emits poses and acceptance regions; the planner owns goals.
- **Route planning inside Recce.** Rejected; idea 21 says "not route planning". Recce has no map.

## 8. Open questions

1. Gap matching across re-runs. Region overlap works while the frame is stable; after a re-solve in which the frame moves, matching can split or merge gaps. The rule needs evidence from RC-P1 runs of the same set with added photos.
2. Gap thresholds and severity formulas (the 15 degrees and 3 photos are placeholders). RC-P3 sets them against ground truth; the `ruleset` field exists so changing them is visible.
3. Actor profile format: Recce's own, or robotics-lab's robot file (VDA factsheet names, RFC-0014 §3.3.1) extended? One format would avoid a translation layer.
4. MCP transport. *Answered by robotics-lab (d):* Recce's HTTP API on the tailnet with tokens, and a stdio MCP server on the agent's machine as its client.
5. Whether the claim lease should be shorter for a robot than for a human, and whether Recce ever stops offering a gap a robot repeatedly missed (`attempts` is recorded; the policy is not).
6. Frame identity: who mints `frame_id` for a run's `map`, and how a planner proves two ids describe the same frame after a relocalisation (RFC-0025 §3.6 "map <- world epochs" is not verified in code).
7. Gaps on geometry that exists only in products (holes need a mesh). The schema is open-ended in `kind`; whether holes are listed by region or by mesh face ids is undecided.
8. Which purposes exist beyond the four, and who owns their definitions: Recce, or the consumer passing weights to `gap_brief`.

## 9. Not covered

- Nothing is built or measured. The example numbers are invented; the field set is a design, not a result of running the engine. No gap has been computed by Recce yet.
- The gap kinds after the first four: holes, blur and exposure, missing colour reference underwater, disconnected components. Their evidence fields, their close criteria and their viewpoints are not designed.
- Underwater and aerial frames (GPS, ENU, refractive geometry) and any actor but phone and ground robot. The `actor` list names `drone` and `arm` without a design for them.
- Live feedback while the robot shoots (a running "ghost camera" on the robot), and any on-device Recce.
- The robotics-lab side beyond reading: I read the Mission Control contract, the MCP server and RFCs, not the planner module (`planner.py`), the navigator code, flotilla's approvals or the Gazebo and Nav2 bridge. Mission Control's `/plan` takes words and returns goals; how an LLM planner would consume a gap list is not designed, and no prompt is proposed here.
- The yaw zero direction and quaternion order in robotics-lab are not stated in the documents I read (inferred in section 2); a code check of `geometry.py` and `wire.py` is still to be made.
- Flotilla: how its policy and approvals (RFC-0005, RFC-0014 §3.4.7) gate a capture goal that a gap produced. The simulator-first rule is cited; the approval path is not.
- Authorisation detail: token scopes are named, not specified; revocation and rotation follow robotics-lab's `auth.py` only by analogy (inferred).
- Privacy beyond the sentence in section 6: retention of gap lists, redaction in shot-card images, and whether a landmark thumbnail may leave the tailnet.
- Throughput and size: how large a gap list grows on a thousand-image set (a gap per region on a large site) and whether `list_gaps` needs paging; the limit of gaps in `gap_brief` is a parameter without a default.
- The human shot card and the top-down map (idea 21, M2): this note does not change them; it shares their `text` field.
- Validation of the design with a consumer: no robotics-lab maintainer has read it. It goes to that project as a message when the owner approves.
