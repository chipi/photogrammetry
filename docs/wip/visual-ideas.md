# Visual ideas and the mock-up plan

The catalogue of concepts for the 3D scene, the explanations and the frame, and the mock-ups that
work them out. The direction behind them is in the [brief](../concept/RC-brief.md) §2 ("Two
registers in one interface"); the mock-up track is in §5 ("Two tracks, one meeting point"). Every
entry is a direction to mock, not a decision: a mock-up keeps, changes or drops it, with a reason.

Sources: ideas 1–8 were proposed on 2026-11-24 and approved by the owner the same day; ideas 9–20
and the patterns come from the [UX inspiration research](research-ux-inspiration-2026-11-24.md)
of the same day, also approved as directions. Source tags `[V]` and `[U]` there apply here.

## The ideas

| # | Idea | What it explains | Source | Mock-up |
|---|---|---|---|---|
| 1 | **The model builds itself on screen.** Each photo's camera snaps into place and the point cloud fills in as registration runs; afterwards it replays as a short film of the reconstruction. | How registration works, and where it went wrong | Owner session | M1 |
| 2 | **Matches drawn as threads.** Thin lines link each photo to the points it sees; a part held by few threads looks fragile. | Why a part of the model is weak, before any error number | Owner session | M1 |
| 3 | **Gaps as light and shadow.** Areas no photo covered are dim, well-covered areas lit; the next shot appears as a ghost camera that can be sent to a phone or a robot. | Coverage, and what to capture next | Owner session | M2 |
| 4 | **Confidence on the surface.** Uncertain geometry is drawn sketchy or translucent, solid geometry solid, instead of a rainbow error map; uncertainty blends softly between cameras rather than as a patchwork. | Uncertainty, read at a glance | Owner session; Womp soft blending | M2 |
| 5 | **An agent narrates the run.** A multimodal agent looks at the intermediate products and writes a short illustrated debrief ("the left side of the wreck rests on 12 photos; here are the three that hold it"). | The whole run, in words and pictures | Owner session | M3 |
| 6 | **Compare like a photographer.** A before/after split slider: COLMAP against GLOMAP, JPEG against RAW, one recipe against another, on the same view. | What a strategy or recipe changed | Owner session; Resolve wipe | M4 |
| 7 | **A presentation mode.** Lighting, framing and a camera path for showing a model to people outside the field; a first-class output, shareable as a browser link with no install. | The result, to an audience | Owner session; Shapr3D review link | M6 |
| 8 | **Underwater, made visible.** Toggle between the water's colour and the corrected colour; the refraction correction shown as a lens of water that can be switched off. | Colour loss and refraction | Owner session | M7 |
| 9 | **Plural timelines.** A run has a timeline per axis (photo order, capture time, registration order, optimiser iteration); a picker chooses which drives the scene; static facts (intrinsics, scale reference) belong to all of them. | That a reconstruction has more than one "when" | Rerun | M1 |
| 10 | **Evidence handles.** Every sentence and number in a debrief or report has a handle that selects its photos or matches and flies the camera there; a sentence without one is flagged as unsupported. Phrases open in place to show their photos. | Why to believe a claim | Agent UX pattern; Spline MCP; Nicky Case's Nutshell | M3 |
| 11 | **The engine's belief at step k.** Scrub what the engine believed at each iteration, including poses it later discarded. | Hidden state: how the solver got there | Bret Victor | M1 |
| 12 | **Mini-labs.** Small reader-driven demonstrations beside a term (baseline and triangulation, overlap and match count, blur and features, rolling shutter, refraction and focal length), one or two controls each. | The concepts themselves, by touch | Ciechanowski; Distill | M5 |
| 13 | **A shared coverage glyph.** One ring or sphere glyph that fills as angles are covered, drawn the same on the web, the phone and an operator's tablet, with named reasons for its advice. | Coverage, learned once, read everywhere | Apple's capture dial | M2, M8 |
| 14 | **Honest colour.** Every ramp in the scene is perceptually uniform (built in LCH), with a colour-blind-safe variant, a luminance-only fallback and a "what this colour means" legend on every overlay. | That equal steps in the data look equal | Linear | M2 (rule for all) |
| 15 | **One verb list.** One registry of actions powers the command palette (Cmd+K), the CLI subcommands, the HTTP routes and the MCP tools. | That people and agents do the same things | Raycast; Rerun | M0 |
| 16 | **Readiness stamps.** The quality report ends with named uses (survey, robot localisation, print, web viewing), each pass, fail or unknown against stated requirements. | What the model is good for | NVIDIA Omniverse SimReady | M3 |
| 17 | **Live registration during capture.** For a streaming source each arriving frame registers into the model in view; a frame that fails shows as a ghost at its expected pose. | That the capture is working, while it happens | Capture One tethering; Apple point-cloud preview | M8 |
| 18 | **The agent as a scene editor.** The agent places ghost cameras, labels and a camera path into the scene through MCP; the person moves or deletes them. | Agent and person working on one scene | Spline MCP | M3 |
| 19 | **Replay the moment.** One click replays the iterations around the step with the largest residual jump, with camera positions before and after shown as a fading trail. | Where it went wrong, without searching | NASA Eyes replay; Flightradar24 trails | M1 |
| 20 | **Frame the cost.** Every recipe shows a time and energy estimate before it runs and the measured figure after. | What a choice costs | Autodesk Flow Studio credits | M4 |
| 21 | **The gap list for the next session.** After an upload, every gap is listed and ranked, not only the weakest: thin coverage, few photos, photos that did not join, pieces that did not connect, missing scale. Each gap becomes a shot card: where to stand (a ghost camera, and the nearest photo already taken as a reference to recognise the spot), what to shoot and why. A top-down map numbers the gaps; the next upload ticks closed gaps off. The same list goes to the phone app, and to a robot as a machine-readable brief. Not route planning. | What to do tomorrow, in the field | Owner, 2026-11-24 | M2 |

## Patterns for every surface

- **One time cursor drives every panel** (Rerun, Foxglove): scene, photo strip, match graph and
  plots move together, with no visible lag.
- **Analysis is an overlay, never a replacement** (Halide's zebras and peaking, Forma's layers):
  each overlay has one toggle and leaves the scene underneath.
- **Show the data, show hidden state, concrete before abstract** (Bret Victor): explanations start
  from one camera and one point, then widen to the whole set.
- **Drill in with breadcrumbs** (Blender 5.0): run, stage, step, without losing place.
- **Recipes are node graphs with swap-in-place** (Houdini, Blender's Swap Node): a strategy is
  swapped and keeps its connections; two recipes compare by the node that differs.
- **Motion is optional** (Blender's Reduce Motion): every animation has a still equivalent.
- **A camera is its photo** (owner, 2026-11-24, restated 2026-11-27): a photo hangs where it was
  taken as a crisp image plane with no outline; a dot marks the camera centre; four hairline rays
  run from the photo's corners and fade towards the centre, so the light reads as travelling and the
  photo as the surface. No edges close a pyramid. A shot not yet taken is a dotted outline with
  faint rays. Every scene with cameras follows this. A setting replaces the photos with a solid
  fill (owner, 2026-11-27), for large sets or slow devices where hundreds of textures cost frame
  rate; the dot and the fading rays stay the same. Not built yet; its saving is not measured.
- **AI is a layer, never a dependency** (owner, 2026-11-27): each view works with no AI connected;
  with the person's own AI connected, what it adds is marked as written by AI and checked against
  the engine's numbers.
- **The frame follows robotics-lab** (Observatory, Mission Control): dark by default, outliner,
  read-only inspector, label left and value right in mono; tokens derived from base, accent and
  contrast (Linear's approach).

## The mock-ups

Each mock-up is a page in `mockups/RC-M<n>-<slug>/`, built to be looked at and critiqued. It uses
real prototype output wherever it exists; where it does not, it says plainly which data is
stand-in. A mock-up ends with the owner's verdict per concept: kept, changed or dropped, with the
reason.

| Mock-up | Shows | Ideas | Data |
|---|---|---|---|
| **M0 — The frame** | The shell every view lives in: top bar, outliner, inspector, timeline, command palette, light and dark | 15, patterns | Any |
| **M1 — The run** | A reconstruction replayed: cameras snapping in, threads, plural timelines, belief at step k, replay the moment | 1, 2, 9, 11, 19 | RC-P1 kicker (COLMAP and GLOMAP) |
| **M2 — Coverage and confidence** | Light and shadow, ghost camera, the coverage glyph, confidence on the surface, honest colour | 3, 4, 13, 14 | RC-P1, then RC-P4 meshes |
| **M3 — The debrief** | The agent's illustrated report with evidence handles, readiness stamps, agent-placed annotations | 5, 10, 16, 18 | RC-P1 and RC-P3 quality state |
| **M4 — Recipes and comparison** | The recipe graph, swap-in-place, split-slider compare, cost before and after | 6, 20 | RC-P1's two strategies |
| **M5 — Learn** | Mini-labs beside the terms of the primer | 12 | Synthetic, by design |
| **M6 — Presentation** | Lighting, framing, camera path, shareable link | 7 | RC-P4 mesh and splat |
| **M7 — Underwater** | Water colour against corrected colour, the refraction lens | 8 | RC-P12 public underwater sets |
| **M8 — Capture** | The phone's coverage glyph and live registration | 13, 17 | RC-P11 iPhone app |

Order: M0 and M1 first (they set the frame and use the data RC-P1 already has), then M2, M3 and M4;
M5–M8 follow the prototypes they depend on.

## Decided by the owner (2026-11-24)

- **Technology:** mock-ups are plain HTML with three.js; the product's UI moves to its own stack
  later. Whether that stack is SvelteKit (the default in the owner's other projects) is reopened
  and decided on evidence from the mock-ups, not by habit.
- **Two passes:** phase 1 is rough but still good-looking, to settle the concepts; phase 2
  polishes the chosen direction.

## Status

| Mock-up | Phase | Where |
|---|---|---|
| M0 + M1, first passes at M2 and M3 | Phase 1 built 2026-11-24, **owner verdict: kept, all concepts shown** ("we really love everything"; the gap list "exactly what I wanted"). Phase 2 done the same day: IBM Plex, tokens, AA contrast, field shot cards; photos hang in the air with faint rays (owner feedback) | [mockups/RC-M1-run](https://github.com/chipi/recce/tree/main/mockups/RC-M1-run) |
| M2 | Phase 1 built 2026-11-27 on RC-P10's room 42444793 and RC-P13's structure. **Owner verdict (2026-11-27): all concepts kept**; finished in the build phase | [mockups/RC-M2-coverage](https://github.com/chipi/recce/tree/main/mockups/RC-M2-coverage) |
| M3 | Phase 1 built 2026-11-27 on ETH3D courtyard: the engine's debrief without AI, an opt-in AI layer over it ("Bring your own AI"), handles replayed by `verify.py`, readiness stamps, the engine's where-to-stand rule. **Owner verdict (2026-11-27): all concepts kept** | [mockups/RC-M3-debrief](https://github.com/chipi/recce/tree/main/mockups/RC-M3-debrief) |
| M4 | Phase 1 built 2026-11-27 on ETH3D kicker and courtyard: recipe graph with swap in place, the wipe, what changed (rule, or opt-in AI), cost estimated before and measured after (time and energy). **Owner verdict (2026-11-27): all concepts kept** | [mockups/RC-M4-recipes](https://github.com/chipi/recce/tree/main/mockups/RC-M4-recipes) |
| M6 | Phase 1 built 2026-11-27 on ETH3D courtyard (RC-P4 mesh, RC-P6 splat): a path through the photos where each stop dissolves into its photo with the lens matched, how close each moment is to a photo, lighting presets with the splat's limit stated, the mesh where the splat does not hold, framing, and a link to the audience view; words by rule, or drafted by the person's AI and checked. **Owner verdict (2026-11-27): all concepts kept** | [mockups/RC-M6-presentation](https://github.com/chipi/recce/tree/main/mockups/RC-M6-presentation) |
