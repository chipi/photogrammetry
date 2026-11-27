# RC-M3 — The debrief

**Shows:** the report a person reads after a run, written by an agent from the engine's quality
state alone and checked by replaying every tool call it quotes.

- **An agent narrates the run** (idea 5): one real agent run (Claude Sonnet through `claude -p`)
  with only this mock-up's MCP tools writes the debrief in three sections: what holds, what is
  weak, what to shoot next. Each claim about a region names the region and up to three photos
  that hold it.
- **Evidence handles** (idea 10): every number in a sentence is underlined when a tool call backs
  it. Picking the sentence flies the scene to its region, puts its photos on their cameras and
  lists each handle with the value claimed and the value replayed. A number nothing backs gets a
  wavy red line, and the sentence is marked unsupported. The check is mechanical (`verify.py`),
  not the agent's word.
- **Readiness stamps** (idea 16): web viewing, measurement, robot localisation, print, each pass,
  fail or unknown, with its requirement written beside it and its evidence replayed like a
  handle. The stamps are rules over the same tools, not the agent's opinion.
- **The agent as a scene editor** (idea 18): the agent places labels and ghost cameras through
  `place_label` and `place_camera`; the person drags one to move it or deletes it, and the panel
  shows what the agent would read back through `list_annotations`.

The frame follows RC-M1 and RC-M2 (tokens, IBM Plex, light and dark); the report itself is set in
Plex Serif, as the one surface that reads as a written document.

## What the runs showed

Two agent runs, 2026-11-27, Claude Sonnet, US$0.16 and US$0.18, 16 and 18 turns.

| | Run 1 | Run 2 (shown) |
|---|---|---|
| Tools | RC-P3's three, `get_products`, the three scene tools | Same, plus `list_cameras` |
| Claims supported / unsupported / judgement | 8 / 4 / 0 | 8 / 4 / 0 |
| Unsupported because | "x near 21.87" (no tool says it); the three shots' own coordinates | "38" in the registration sentence (it cited the rate, not the count); the three shots' own coordinates |
| Ghost cameras a photographer can use | **0 of 3**: one at x 23.9 m, behind the east wall (points end at 21.9 m); one 8 m up; one 0.5 m up | **2 of 3**: at 1.8 m, 0.9 and 2.0 m from a real camera; the third at x −3.4 m, on the west wall's line, with 22 points within 0.3 m of its line of sight |

The real photos were all taken by hand: every camera centre is 1.58–1.81 m above the ground. In
run 1 the agent had no tool that says where the cameras stood, so it could not follow the prompt's
"near the cameras that already see the region"; it said so in its own sentences ("a geometric
estimate, not taken from existing camera poses"). One tool, `list_cameras`, fixed two of the three
shots. The third shows what is still missing: the agent sees no walls, so a shot "on the opposite
side" can land in one. In the product the gap list computes where to stand (RC-M1, RC-M2) and the
agent explains and places it; it should not invent the position.

The replay checks numbers, not meaning. Run 2 writes "81% of its few-photo fraction is flagged"
for R021; the number is right (81% of the region's points rest on two photos or fewer) and the
sentence garbles it, and it still counts as supported.

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
| The debrief text, its handles, labels and ghost cameras | **One agent run** (run 2); `data/run1/` keeps run 1 |
| Supported, unsupported, judgement | Real: `verify.py` replays each handle against the same tools |
| Readiness stamps | **Rules written for the mock-up**, stated beside each stamp; their inputs are real |
| Moving and deleting annotations | In the page only; nothing is written back to `data/annotations.json` |

## Run

```bash
cd prototypes/RC-P3-quality
uv run python ../../mockups/RC-M3-debrief/export_scene.py \
  ~/.cache/recce/datasets/eth3d/courtyard ~/.cache/recce/runs ../../mockups/RC-M3-debrief/data
cd ../../mockups/RC-M3-debrief
RECCE_P3_RUNS=~/.cache/recce/runs/p3 ./write_debrief.sh sonnet   # the agent, then verify.py
python3 -m http.server 8795 --bind 127.0.0.1
```

Open <http://127.0.0.1:8795/>. three.js loads from jsDelivr. A view is a link:
`?pick=<n>` selects the n-th sentence or stamp (counted down the page), `&still=1` skips the
flight, `&theme=light`.

| File | Does |
|---|---|
| `export_scene.py` | The scene, regions, thumbnails and `products.json` |
| `debrief_server.py` | The agent's MCP server: RC-P3's three read tools, `get_products`, `list_cameras`, `place_label`, `place_camera`, `list_annotations` |
| `prompt.md` | The one prompt the agent gets |
| `write_debrief.sh` | Runs the agent with only those tools, then `verify.py` |
| `verify.py` | Replays the handles, marks each claim, computes the readiness stamps; writes `debrief.json` |
| `index.html` | The page |

## Verdict

Phase 1, built 2026-11-27. The owner's verdict per concept is open:

| Concept | Idea | Verdict |
|---|---|---|
| The agent's written debrief, three sections | 5 | Open |
| Evidence handles: underlined numbers, replayed calls, photos on their cameras | 10 | Open |
| Unsupported numbers flagged by replay, not by the agent | 10 | Open |
| Readiness stamps with their requirements | 16 | Open |
| Agent-placed labels and ghost cameras, moved or deleted by the person | 18 | Open |

## Not covered

- **Multimodal.** The agent reads numbers and photo names; it does not look at the photos or
  renders. "Here are the three photos that hold it" comes from `images_seeing`, not from sight.
- **Meaning.** The replay checks that each number matches a tool value; a sentence that misreads
  a correct number still passes (R021 in run 2).
- **Positions the agent chose.** Ghost-camera coordinates have no tool behind them, so their
  sentences are always unsupported; a handle to `list_annotations` would make them traceable
  but not right. Walls and occlusion are not checked.
- **Two runs, one model, one scene.** No repeats; Haiku and Opus not tried.
- **The edits go nowhere.** Moving or deleting an annotation changes the page, not the file the
  agent reads; the round trip is shown as the JSON it would read.
- **The stamps' rules** are the mock-up's; their thresholds (90% within 2 cm, for example) are not
  agreed requirements.
- **Ground truth in the frame.** The scene is in metres only because RC-P3 aligns it to ETH3D's
  cameras; the run's own scale is arbitrary, and the debrief says so.
