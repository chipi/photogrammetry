# RC-M6 — Presentation

**Shows:** a model presented to people outside the field: a guided path through the photos,
lighting and framing chosen for an audience, and a link that opens in a browser with nothing to
install (idea 7).

- **A path through the photos.** The engine orders the 38 photos into a walk (nearest neighbour,
  then 2-opt) and picks 8 stops that face apart. The camera moves along a spline through the
  stops and holds at each. The author adds, removes and reorders stops, or adds the current view
  as a free stop, marked "not a photo".
- **The stop turns into its photo.** At each stop the lens matches the photo's (the frame's
  vertical field of view comes from the photo's and the frame's aspect), and the view dissolves
  into the photo taken there, undistorted to the same pinhole camera. The audience sees where the
  model came from; the author sees whether the model and the photo agree.
- **How close is this view to a photo?** For every moment of the path: the distance to the
  nearest photo and the turn from its view direction. A band under the timeline shows it
  (at a photo, near the photos, away from the photos), and the editor shows it live.
- **Lighting and the splat's limit.** Four presets: as captured (unlit, the default), soft studio,
  low sun (turnable) and clay (shape only). Lighting changes the mesh only; the splat keeps the
  light it was photographed in, and the page says so. Away from the photos the splat breaks into
  streaks (RC-P6), so by default the mesh is drawn there instead, with a chip saying why.
- **Framing.** Fill, 16:9, 4:5 or 9:16, with thirds and a 5% safe area.
- **The link.** The whole presentation (stops, captions, look, framing, timing) is in the link;
  `?present=1` opens the audience view: a title card, captions at the stops, progress dots and an
  "About this model" card (photos, scale source, camera error against the survey, faces,
  gaussians, and that views between the stops are rendered, not photographed). The Share panel
  lists what a viewer downloads and the frame rates RC-P6 measured on the devices.
- **Words without AI, and with it** (as RC-M3 and RC-M4). Without AI a rule writes the title,
  the introduction and a caption per stop from the geometry ("Photo 13 of 38, 7.6 m along the
  walk"). With the person's own AI connected, a model reads each stop's photo and drafts the
  words; every number it uses is checked against the model's facts, and what it says a photo
  shows is marked as its judgement. The author's own text wins over both.

The frame follows RC-M1 to RC-M4; the audience view adds IBM Plex Serif for the title and the
captions. Stops follow the camera rule (pattern "A camera is its photo"): in the editor's path
view each stop hangs as its photo, rays fading from its corners to the centre.

## What the data says

**The stop and the photo line up.** At stop 5 (`DSC_0298`) the splat render and the
undistorted photo show the bicycle shelter, its posts and the windows behind in the same places,
read by eye in headless Chromium on the X3; no pixel metric was computed. Between stops the
splat holds near the photos and smears thin structure (bicycle wheels, the shelter's cables).

| The default presentation | Value |
|---|---|
| Stops | 8 of 38 photos |
| Path | 32.8 m, 70 s at 0.8 m/s with 3.5 s at each stop |
| Time at or near a photo (band) | 94% |
| A viewer downloads | splat 56 MB; mesh 52 MB and atlases 95 MB when the mesh shows; stop photos about 6.5 MB |

The walk through all 38 photos is 66.1 m. The mesh has no surface over much of the courtyard
floor, so the overview from above shows holes; the mesh is the fallback away from the photos,
not a clean model.

**The AI layer.** One call (Claude Sonnet, `claude -p` with the Read tool, the 8 stop photos)
wrote a title, an introduction and 8 captions for US$0.064. Of the 10 drafts: 1 supported (the
introduction's two numbers, 38 photos and 8 stops, match the facts), 9 judgement (what a photo
shows, with no number), 0 unsupported. The first check marked the title unsupported for the
"3" in "3D"; the checker now treats "3D" as a word, not a number. I compared 5 of the 8 captions with their photos (stops
1 to 5) and found them accurate; stops 6 to 8 were not checked.

**Why RC-M4's call cost US$1.75.** A call with no MCP servers, no settings sources and its own
system prompt costs US$0.0009 for a one-word answer (447 input tokens). RC-M4's call ran with
`claude -p`'s default context (this machine's MCP servers, instructions and skills). I believe
that context made the difference, but I have not re-run RC-M4's call to measure it.

## Data

| Shown | Status |
|---|---|
| Mesh and splat | Real: RC-P4's mesh and RC-P6's 1,000,000-gaussian splat, `data/p6` links to RC-P6's data |
| Photo poses, the walk, the stops | Real poses (RC-P1, in RC-P6's frame); the walk and stop choice are rules written for the mock-up |
| Stop photos | Real: ETH3D's photos undistorted (its THIN_PRISM_FISHEYE calibration) into RC-P6's pinhole camera |
| Scale and camera error | Real: RC-P6's Sim(3) to ETH3D's surveyed cameras (known only for the benchmark) |
| Near a photo | **Rule written for the mock-up**: at a photo within 0.25 m and 8°, near within 2 m and 40° |
| Lighting presets | **Look written for the mock-up** (three.js Lambert over the atlases) |
| Frame rates | Real: RC-P6's measurements of the mesh and splat (X3, M4 Pro, iPhone 15 Pro), not of this page |
| Captions without AI | **Rule written for the mock-up** |
| Captions with AI | **One recorded run**, checked by `ai_present.py` |
| Public link | Not built: the link works on this network only |

## Run

```bash
cd prototypes/RC-P1-registration
uv run python ../../mockups/RC-M6-presentation/export_present.py \
  ~/.cache/recce/datasets/eth3d/courtyard ~/.cache/recce/runs/p6/data \
  ../../mockups/RC-M6-presentation/data
cd ../../mockups/RC-M6-presentation
python3 ai_present.py data sonnet      # optional: the AI layer
python3 -m http.server 8797 --bind 0.0.0.0
```

Open <http://127.0.0.1:8797/>. `?ai=1` turns the AI layer on; `?present=1` opens the audience
view; the Share panel's link carries the rest (`s=`, the state as base64 JSON). Phones load the
atlases at 1024 px, as RC-P6.

| File | Does |
|---|---|
| `export_present.py` | Photo poses in RC-P6's frame, the walk and the stops, undistorted photos and thumbnails, `meta.json` |
| `ai_present.py` | The optional AI layer and its check; writes `ai.json` |
| `index.html` | The editor and the audience view |

## Verdict

Phase 1, built 2026-11-27. Waiting for the owner's verdict.

| Concept | Idea |
|---|---|
| A path through the photos, stops as photos | 7 |
| The stop dissolves into its photo, lens matched | 7 |
| How close a view is to a photo, along the path | 7, pattern |
| Lighting presets, and the splat's limit stated | 7 |
| The mesh where the splat does not hold | 7 |
| Framing: aspect, thirds and safe area | 7 |
| The link: the audience view with "About this model" | 7 |
| Words by rule, or drafted by the person's AI, checked | 7, pattern |

## Not covered

- **Not run on a phone or the M4 Pro.** Screenshots are from headless Chromium on the X3,
  including a 390 px wide audience view; frame rates were not measured for this page, only for
  RC-P6's viewer, which loads the same files.
- **The link is local.** Hosting, access control and a smaller download for phones (decimated
  mesh, fewer gaussians) are not built.
- **One scene.** Only the courtyard; the walk and stop rules are not tried on another capture.
- **The dissolve's fit.** Checked by eye at a few stops; the principal point offset is ignored
  (the photo is centred), and no pixel metric is computed.
- **Lighting is a look, not relighting.** The atlases already hold the photos' shading; light on
  top of them doubles it. The splat cannot be relit.
- **No exported video,** no music or narration audio, no transitions other than the dissolve.
- **The AI layer** drafts for the engine's 8 stops only; added stops keep the rule's caption.
  The "Bring your own AI" settings are shown, not wired.
- **Path collisions.** The spline between stops is not checked against the mesh; between the
  default stops it stays in the open courtyard, read from the band and the screenshots only.
