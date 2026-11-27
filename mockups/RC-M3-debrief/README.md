# RC-M3 — The debrief

**Shows:** the report a person reads after a run, in two layers, with every number checked by
replaying the tool call that gives it.

- **Without AI** (the default; owner, 2026-11-27: "Recce is complete without AI"): the engine
  writes the debrief from templates and rules over the quality state (`rules_debrief.py`): what
  holds, the weakest regions by rule, and a new photo for each, placed by the engine's
  where-to-stand rule (`plan_shots.py`). The readiness stamps are rules too.
- **With your own AI connected** (opt-in, "Bring your own AI": an OpenAI-compatible endpoint,
  hosted or local): the AI reads the engine's debrief through Recce's tools and adds what rules
  cannot write (idea 5): what the model is good for in plain words, which weak region to fix
  first for web viewing and for measurement, and a walking order with what else to bring. Its
  sections sit above the engine's, marked AI. Positions still come from the engine.
- **Evidence handles** (idea 10): every number in a sentence is underlined when a tool call backs
  it. Picking the sentence flies the scene to its region, puts its photos on their cameras and
  lists each handle with the value claimed and the value replayed. A number nothing backs gets a
  wavy red line, and the sentence is marked unsupported. The check is mechanical (`verify.py`),
  not the agent's word.
- **Readiness stamps** (idea 16): web viewing, measurement, robot localisation, print, each pass,
  fail or unknown, with its requirement written beside it and its evidence replayed like a
  handle. The stamps are rules over the same tools, not the agent's opinion.
- **The agent as a scene editor** (idea 18): without AI the engine places labels on the weakest
  regions and ghost cameras where its rule says to stand; with AI the agent places them through
  `place_label` and `place_camera`, at the engine's spots. Either way the person drags one to
  move it or deletes it, and the panel shows what the engine would read back.

The frame follows RC-M1 and RC-M2 (tokens, IBM Plex, light and dark); the report itself is set in
Plex Serif, as the one surface that reads as a written document.

## What the runs showed

**Where to stand belongs to the engine.** Three agent runs, 2026-11-27, Claude Sonnet, US$0.13
to 0.18 each. The real photos were all taken by hand: every camera centre is 1.58–1.81 m up.

| | Run 1 | Run 2 | Run 3 (shown with AI on) |
|---|---|---|---|
| Tools added | RC-P3's three, `get_products`, the scene tools | `list_cameras` | `get_engine_debrief`, `suggest_shots`; the prompt asks the AI to build on the engine's debrief |
| Supported / unsupported | 8 / 4 | 8 / 4 | 4 / 5 |
| New shots a photographer can use | **0 of 3**: behind the east wall (x 23.9 m; points end at 21.9 m), 8 m up, 0.5 m up | **2 of 3**: the third on the west wall's line, 22 points within 0.3 m of its sight line | **3 of 3**: the engine's spots, at 1.7 m |

In run 1 the agent had no tool that says where the cameras stood and said so itself ("a geometric
estimate, not taken from existing camera poses"). Run 2's `list_cameras` fixed two shots; the
third shows that the agent sees no walls. So the engine now computes the spot (`plan_shots.py`):
hand height, inside the walked area, on the side the surface faces (a plane fitted to the
region's points), a clear line of sight, at least 15 degrees from every existing view. On the
nine weakest regions it finds a spot for each, 26 to 42 degrees new, with 0 to 3 points near the
line of sight; four regions on the east wall share one spot.

**What the AI adds on top.** Run 3 does not restate facts; it ranks R039 first for web viewing
(fewest points: missing surface shows) and R043 first for measurement (thinnest angle: depth is
least certain), says why the two differ, orders the walk, tells the person to bring a scale bar
and take two or three frames per spot, and explains thin angle as "judging distance with one eye
nearly closed". Its five unsupported sentences are all real citation misses, none a wrong number:
18.9 degrees and 2 cm quoted from the engine's debrief, 7 photos, the positions and a 10 mm
texel, each without its tool call.

**The engine's debrief** has 12 of 12 sentences supported, by construction: its text is filled
from the same values its handles name.

The replay checks numbers, not meaning. Run 2 wrote "81% of its few-photo fraction is flagged";
the number is right (81% of the region's points rest on two photos or fewer), the sentence
garbles it, and it still counted as supported.

## Data

Real output from [RC-P1](../../prototypes/RC-P1-registration/), [RC-P3](../../prototypes/RC-P3-quality/),
[RC-P4](../../prototypes/RC-P4-products/) and [RC-P6](../../prototypes/RC-P6-viewer/) on ETH3D
*courtyard* (CC BY-NC-SA 4.0, development use), the scene with the most prototypes on it. Nothing
from the dataset is committed: `export_scene.py`, the agent and `verify.py` write `data/`
(ignored by git).

| Shown | Status |
|---|---|
| Cameras, points, colours | Real: RC-P1's COLMAP model, in RC-P3's frame (aligned to the ETH3D cameras, so metres) |
| Regions, coverage, flags, photos per region | Real: RC-P3's `quality.json` for `courtyard/full` (54 regions of 4.86 m) |
| Scan checks of the dense cloud and mesh, texture | Real: RC-P4's measurements; the debrief says they need the laser scan, which the field lacks |
| Frame rates | Real: the owner's readings in RC-P6 (no file holds them; `export_scene.py` copies them with their source) |
| The engine's debrief, its labels and ghost cameras | **Templates and rules** (`rules_debrief.py`, `plan_shots.py`) over real data |
| The AI layer's text, labels and ghost cameras | **One agent run** (run 3); `data/run1/` and `data/run2/` keep the others |
| "Bring your own AI" settings | **Not wired**: the fields show the setting; the AI text was produced through Claude Code with the same MCP tools, not through an OpenAI-compatible endpoint |
| Supported, unsupported, judgement | Real: `verify.py` replays each handle against the same tools |
| Readiness stamps | **Rules written for the mock-up**, stated beside each stamp; their inputs are real |
| Moving and deleting annotations | In the page only; nothing is written back to `data/annotations.json` |

## Run

```bash
cd prototypes/RC-P3-quality
uv run python ../../mockups/RC-M3-debrief/export_scene.py \
  ~/.cache/recce/datasets/eth3d/courtyard ~/.cache/recce/runs ../../mockups/RC-M3-debrief/data
cd ../../mockups/RC-M3-debrief
export RECCE_P3_RUNS=~/.cache/recce/runs/p3
uv run --directory ../../prototypes/RC-P3-quality python "$PWD/rules_debrief.py" "$PWD/data"  # no AI
./write_debrief.sh sonnet   # the AI layer, then verify.py
python3 -m http.server 8795 --bind 127.0.0.1
```

Open <http://127.0.0.1:8795/>. three.js loads from jsDelivr. A view is a link:
`?ai=1` turns the AI layer on, `&pick=<n>` selects the n-th sentence or stamp (counted down the
page), `&still=1` skips the flight, `&settings=1` opens "Bring your own AI", `&theme=light`.

| File | Does |
|---|---|
| `export_scene.py` | The scene, regions, thumbnails and `products.json` |
| `plan_shots.py` | The engine's where-to-stand rule |
| `rules_debrief.py` | The debrief without AI; writes `rules.json` |
| `debrief_server.py` | The MCP server: RC-P3's three read tools, `get_products`, `get_engine_debrief`, `list_cameras`, `suggest_shots`, `place_label`, `place_camera`, `list_annotations` |
| `prompt.md` | The one prompt the AI layer gets |
| `write_debrief.sh` | Runs the agent with only those tools, then `verify.py` |
| `verify.py` | Replays the handles, marks each claim, computes the readiness stamps; writes `debrief.json` |
| `index.html` | The page |

## Verdict

Phase 1, built 2026-11-27. The owner's verdict per concept is open:

| Concept | Idea | Verdict |
|---|---|---|
| The engine's debrief without AI, complete on its own | (owner, 2026-11-27) | Open |
| The engine's where-to-stand rule | 3, 21 | Open |
| "Bring your own AI": an OpenAI-compatible endpoint, opt-in | (owner, 2026-11-27) | Open |
| The AI layer: meaning, priorities per purpose, a walking plan, above the engine's debrief | 5 | Open |
| Evidence handles: underlined numbers, replayed calls, photos on their cameras | 10 | Open |
| Unsupported numbers flagged by replay, not by the agent | 10 | Open |
| Readiness stamps with their requirements | 16 | Open |
| Agent-placed labels and ghost cameras, moved or deleted by the person | 18 | Open |

## Not covered

- **Multimodal.** The agent reads numbers and photo names; it does not look at the photos or
  renders. "Here are the three photos that hold it" comes from `images_seeing`, not from sight.
- **Meaning.** The replay checks that each number matches a tool value; a sentence that misreads
  a correct number still passes (R021 in run 2).
- **The where-to-stand rule** uses the sparse points as its only notion of walls: a wall with
  few points does not block a line of sight, and the walked area is the cameras' footprint plus
  1 m, not a map of the site. Not checked on a second scene.
- **The endpoint is not wired.** No request goes to an OpenAI-compatible endpoint; the AI text
  came through Claude Code with MCP tools. How an endpoint without tool calling would work (a
  local model, for example) is not designed.
- **The engine's debrief is fixed templates.** It is checked, but its 12 of 12 is by
  construction, and its choice of three weakest regions is one rule.
- **Three runs, one model, one scene.** No repeats; Haiku, Opus and other providers not tried.
- **The edits go nowhere.** Moving or deleting an annotation changes the page, not the file the
  agent reads; the round trip is shown as the JSON it would read.
- **The stamps' rules** are the mock-up's; their thresholds (90% within 2 cm, for example) are not
  agreed requirements.
- **Ground truth in the frame.** The scene is in metres only because RC-P3 aligns it to ETH3D's
  cameras; the run's own scale is arbitrary, and the debrief says so.
