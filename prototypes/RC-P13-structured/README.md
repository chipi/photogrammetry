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
- **Drone:** not built. Its reconstruction runs now; see RC-P8, drone.
- **Cave:** no data yet.

## Layout

| Path | What it is |
|---|---|
| `scene.py` | The tool-neutral description: schema `recce-structured/0.1`, its rules, read and write. Pure standard library, so Blender's Python imports it |
| `room/build_room.py` | Room segment: RC-P10's TSDF mesh to a scene, then the scene against the Faro scan. Runs in RC-P10's environment (Open3D) |
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
- **Drone and cave segments:** below.

## Drone segment

EuroSDR RPAS Phase 2, Phantom 4 RTK, flight 100_0004 (430 photos, CC BY 4.0). The reconstruction
runs as RC-P8's drone test (`prototypes/RC-P8-learned/drone_rtk.py`). The structured model
(terrain cells, building footprints) is built after it.

## Cave segment

No public cave set with both photos and a laser reference was found. The best candidate is the
Grotta di Monte Intraleo lava tube on Etna (4TU.ResearchData, CC BY 4.0, 2.2 GB), which has a
photogrammetric point cloud and five merged LiDAR scans, but not the robot's raw video. Its
download waits for the owner's go.
