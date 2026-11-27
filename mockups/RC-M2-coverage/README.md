# RC-M2 — Coverage and confidence

**Shows:** one room from inside, with four overlays over the same real mesh, and the evidence that
the overlays are honest.

- **Light and shadow** (idea 3): the photo colour of the surface, lit by how many depth frames saw
  it and dimmed where few did. The next shot is a ghost camera, with a shot card and the same gap
  as a robot brief (idea 21, carried over from RC-M1).
- **Confidence on the surface** (idea 4): the model's support for each point drawn as colour, and
  hatched away below a threshold: solid where the model has evidence, sketchy where it has little.
  Values blend across faces, so uncertainty fades instead of switching patch by patch.
- **Against Faro**: the distance to the laser scan of the same visit, which the model never saw.
  It is the check the product cannot run in the field, shown so the two overlays above can be
  judged.
- **Structure**: RC-P13's structured model of the same room, its walls and floor tagged measured,
  inferred or unknown, over the mesh.

Across all four: **honest colour** (idea 14), with every ramp built in OKLCH so lightness rises
linearly with the data, a colour-blind-safe variant (blue to yellow) and a lightness-only one, and a
"what this colour means" legend beside the scene. Also the **coverage glyph** (idea 13): one ring,
a sector per horizontal direction, filled where frames saw the picked point from that side; the
same glyph is meant for the phone (M8). Below the scene, a chart asks whether the model knows where
it is wrong: the error against Faro, binned by how many frames saw the surface.

The frame follows RC-M1 (tokens, IBM Plex, light and dark) but is a single page, not RC-M1's full
shell.

## What the data says

The chart is the point of the mock-up. On 42444793, surfaces no frame saw are a median 52.4 mm
off Faro; surfaces seen by 32 or more frames, 14.7 mm. In between the error falls with the frame
count (34–45 mm under 4 frames, 26 mm at 8–15, 15 mm at 16–31). The model's own evidence predicts
its error, so shadow and hatching are not decoration. The 90th percentiles overlap (35 to 205 mm),
so a single dark or lit spot proves nothing; the legend says so.

## Data

Real output from [RC-P10](../../prototypes/RC-P10-room/) and
[RC-P13](../../prototypes/RC-P13-structured/) on ARKitScenes video 42444793 and its Faro scan.
Nothing from the dataset is committed: `export_room.py` writes `data/room.bin` and
`data/room.json` (ignored by git) from the local runs.

| Shown | Status |
|---|---|
| Mesh, its colours and normals | Real: RC-P10's TSDF mesh (102,832 vertices) |
| Frames that saw a point | Real, computed by `export_room.py`: each of 750 LiDAR frames (every 4th) counts a vertex it projects onto, facing it, within 5 cm of its own depth |
| Direction spread and the glyph's sectors | Real, from the same frames: 1 − the length of the mean viewing direction; 12 horizontal sectors |
| Support (the model's claim) | **Rule written for the mock-up**: frames on a log scale up to 32, discounted by up to 40% when all views came from one side; hatched below 0.55. It uses the model's evidence only, never Faro |
| Distance to Faro | Real: nearest-point distance from each vertex to the Faro scan, registered by RC-P10 |
| Structured elements | Real: RC-P13's `scene.json` for the room |
| The camera path | Real: ARKit's poses, levelled into RC-P13's frame |
| The next shot | **Heuristic**: the 0.5 m cell with most wall vertices seen by fewer than 4 frames, up to 1.4 m out on the side the phone was, at the capture's median height |
| Robot brief | The shape of the gap-list draft (`gap_list` 1), filled from the one gap |

## Run

```bash
cd prototypes/RC-P10-room
uv run python ../../mockups/RC-M2-coverage/export_room.py 42444793 \
  ../../mockups/RC-M2-coverage/data
cd ../../mockups/RC-M2-coverage && python3 -m http.server 8794 --bind 0.0.0.0
```

Open `http://<host>:8794/`. three.js loads from jsDelivr. A view is a link:
`?mode=coverage|confidence|truth|structure&ramp=uniform|cbsafe|lum&pick=<vertex>|ghost&theme=light`.

## Verdict

Phase 1, built 2026-11-27. The owner's verdict per concept is open:

| Concept | Idea | Verdict |
|---|---|---|
| Light and shadow on the photo colour | 3 | Open |
| Confidence as solid and hatched | 4 | Open |
| The truth overlay beside the claim | 4 | Open |
| OKLCH ramps, colour-blind-safe and lightness-only variants, legend | 14 | Open |
| The coverage glyph | 13 | Open |
| "Does the model know where it is wrong?" chart | 4, 14 | Open |
| Structure over the mesh | (RC-P13) | Open |
| Next shot as ghost camera, card and brief | 3, 21 | Open |

## Not covered

- **One room.** The other Faro rooms (42444858, 42444515) are not exported.
- **The support rule is not calibrated.** Its threshold (0.55) and weights are chosen for the look,
  not fitted to the error.
- **Vertical coverage.** The glyph's sectors are horizontal; a point seen only from above fills
  them like one seen level.
- **Occlusion is the depth frame's.** A vertex counts as seen when the frame's own depth agrees
  within 5 cm; a thin object in front of a wall can still pass.
- **One gap.** The gap list shows the single largest weak patch, not a ranked list as RC-M1 does.
- **Motion.** Nothing animates yet; the light and shadow could grow as frames arrive (idea 17, M8).
