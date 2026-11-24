# RC-P3 — Quality state an agent can read

**Proves:** That the engine's quality state is enough for an agent to find a real weakness. See the
[brief](../../docs/concept/RC-brief.md), RC-P3.

**Proven when:** `quality.json` v0 (registration rate, connected components, per-image verdict and
reason, reprojection mean and tail, coverage per region, scale state) is produced from RC-P1 and
served through three MCP read tools; then a **hold-out test**: all images seeing one region of an
ETH3D scene are removed, the region's coverage metric drops by at least half *(agreed 2026-11-24)*, an agent
with only the MCP tools names that region among the scene's regions, and when the images return the
metric recovers.

Status: **proven (2026-11-24)** on kicker and courtyard, one run each, with the limits under
"Not covered": the held-out region's coverage drops by more than half and recovers, and an agent
with only the three MCP tools names it; with the images returned, the same agent names another
region.

## Files

| File | Does |
|---|---|
| `quality.py` | RC-P1 model + database (+ ETH3D ground truth) to `quality.json` v0; builds `regions.json` |
| `holdout.py` | The hold-out test: full, held-out and returned runs, one `holdout.json` |
| `tools.py` | The three read tools as plain functions: `get_summary`, `list_regions`, `get_region` |
| `mcp_server.py` | stdio MCP server (SDK `mcp` 2.x, `MCPServer`) exposing exactly those three |
| `mcp_check.py` | Starts the server with the SDK's stdio client, lists the tools, calls each once; no LLM |
| `agent_view.py` | Prints what an agent sees through the three tools for one run |

## Run

Inputs are the RC-P1 outputs (`~/.cache/recce/runs/p1/x3/<scene>/`, with `database.db`) and the
ETH3D scene. Outputs go to `~/.cache/recce/runs/p3/<scene>/`. Nothing here is committed.

```bash
cd prototypes/RC-P3-quality
uv sync

# quality.json for an existing RC-P1 model
uv run python quality.py ~/.cache/recce/datasets/eth3d/kicker \
    ~/.cache/recce/runs/p1/x3/kicker/colmap_incremental \
    ~/.cache/recce/runs/p1/x3/kicker/database.db ~/.cache/recce/runs/p3/kicker/reference

# the hold-out test (about 40 s on kicker, CPU): writes full/, heldout/, returned/, holdout.json
uv run python holdout.py ~/.cache/recce/datasets/eth3d/kicker \
    ~/.cache/recce/runs/p1/x3/kicker ~/.cache/recce/runs/p3/kicker

# what an agent sees, without an LLM
uv run python agent_view.py kicker/heldout

# the MCP server on stdio, and a client check against it
uv run python mcp_server.py
uv run python mcp_check.py kicker/heldout
```

A run id such as `kicker/heldout` is a folder under `RECCE_P3_RUNS` (default
`~/.cache/recce/runs/p3`) that holds `quality.json`. The folder name appears in the tool output as
the `run` field. For a blind agent test, `~/.cache/recce/runs/p3/blind/<scene>` is a symlink to the
held-out run, so the agent calls the tools with `blind/kicker` and the run id does not say
"heldout". The hold-out run also exposes, through `get_summary`, only the images it was given:
the withheld images are absent, not marked.

The agent test (`agent_test`), with `mcp.json` holding
`{"mcpServers": {"recce": {"command": "uv", "args": ["run", "--directory", "<repo>/prototypes/RC-P3-quality", "python", "mcp_server.py"]}}}`:

```bash
claude -p "You have three read-only tools that describe the quality of one 3D reconstruction, \
run id 'blind/kicker'. Using only those tools, decide which single region of the scene most \
needs new photographs because the current photos cover it worst. Answer on the last line exactly \
as: REGION=<id>, then one sentence of evidence." \
  --model haiku --mcp-config mcp.json --strict-mcp-config --tools '' \
  --allowedTools 'mcp__recce__get_summary,mcp__recce__list_regions,mcp__recce__get_region'
```

## Design

**Frame.** Regions must mean the same place in every run. `quality.py` aligns each model to the
ETH3D ground-truth cameras with a Sim(3) (Umeyama on camera centres, cameras that hold points only,
as RC-P1 does) and defines regions in that frame. Without a ground truth (`--no-gt`) the frame is
the model's own and the regions are valid for that run only.

**Regions.** A voxel grid over the points of the full run, cell edge the point cloud's
bounding-box diagonal divided by 10, 15 or 20. `holdout.py` tries all three and keeps the grid
that gives the most local hold-out (see Target choice): 1/15 on kicker (1.56 m cells, 30 regions)
and 1/20 on courtyard (4.86 m cells, 54 regions). Cells holding at least 30 points of the full run
are regions; ids (`R001`, ...) are assigned once and saved in `regions.json`, which every later run
of the scene reuses. A region with no points in a later run stays in the list with `no_points`. The
0.9-unit cell and the 30-point floor of the RC-M1 mock-up are the same idea; the cell here scales
with the scene because the ground-truth frame is metric.

**Per region.** Point count, reference point count (from the full run), the images that see it,
median triangulation angle (the largest angle between two viewing rays of a track, as COLMAP
defines it), few-photo fraction (share of points seen by at most two images), azimuth coverage
(share of 36 ten-degree bins around the vertical axis through the region's centre that hold a
camera observing the region), and the largest empty arc. Flags follow the gap-list kinds:
`thin_angle` (median angle below 8 degrees), `few_photos` (few-photo fraction above 0.5),
`no_points`.

**Coverage metric.** One scalar per region:

```
coverage = azimuth_coverage * min(1, points / reference_points)
```

`azimuth_coverage` is in 0..1 and says whether the region is seen from all sides. The second factor
says whether the region still holds the points it held in the full run. A region that loses its
cameras loses both factors. The metric is a count-and-direction measure, not a measure of how well
the region is reconstructed; reprojection error and triangulation angle sit beside it.

**Seeing.** An image sees a region when it observes at least 5 of the region's points in the model
(`SEE_MIN_OBS`); W is the set of images that see the target.

**Target choice (`plan_target`).** The target is chosen from the full model, before any remapping,
so that the hold-out is local. Candidates are regions with at least 100 points that are seen by 3
or more images and at most 35 percent of all images. For each candidate and each grid (divisor 10,
15, 20), the prediction is: withholding W leaves a region with the points that still have at least
2 observing images outside W. Collateral is the number of other regions predicted to keep under
half of their points. The pick is the lowest collateral, then the fewest images in W, then the most
points; the grid and the predicted collateral ids are written to `holdout.json` (`plan`,
`plan_table`).

**Withholding.** `holdout.py` passes the remaining image names to COLMAP's incremental mapper
(`IncrementalPipelineOptions.image_names`) and reads the RC-P1 `database.db` unchanged; features and
matches are not recomputed. The "full" quality.json is the RC-P1 COLMAP model itself; the "returned"
quality.json is a second mapper run on all images, so "returned" also shows run-to-run variation.

**Scale.** `scale.state` is `arbitrary` for every run: photos only, no scale reference.

**Per-image verdict.** `registered` (posed and observes at least one 3D point), `posed_without_points`
(posed, no point; RC-P1 found GLOMAP doing this), `not_registered`. Each carries a reason: no
verified matches, verified matches but not registered by the mapper (the mapper does not say why),
or posed in a secondary component.

## Results

Hold-out runs, 2026-11-24, X3 CPU, COLMAP incremental from the RC-P1 database, one run per scene.
"Recovered" means returned coverage at least 0.8 of full.

| Scene | Grid | Target | Withheld (of all) | Points full / held-out / returned | Coverage full / held-out / returned | Drop | Recovered |
|---|---|---|---|---|---|---|---|
| kicker | 1/15, 30 regions | R028 | 6 of 31 | 155 / 0 / 155 | 0.1667 / 0.0 / 0.1667 | 100% | yes (1.00) |
| courtyard | 1/20, 54 regions | R021 | 7 of 38 | 132 / 1 / 132 | 0.1667 / 0.0002 / 0.1667 | 99.9% | yes (1.00) |

Locality of the hold-out:

| Scene | Predicted collateral | Actual collateral (points under half of full) | Target rank by coverage, weakest first | Regions tied with target | Extra images lost by the mapper |
|---|---|---|---|---|---|
| kicker | R011, R024 | R011, R024 | 1 of 30 | none | 0 (registered 24 of 25 given; full 30 of 31) |
| courtyard | R022 | R004, R005, R008, R012, R016, R022 | 1 of 54 | none | 0 (registered 31 of 31 given) |

In both scenes the target is the unique weakest region by coverage, so the test is well posed: an
agent that reads `list_regions` finds it at the top. Compared with the first selection rule (most
points among minority-seen regions), which left 3 of 17 (kicker) and 12 of 22 (courtyard) regions
tied at coverage 0, the new rule leaves none.

The prediction is exact on kicker and wrong on courtyard: it names one collateral region and
misses five that lost more than half of their points. The cause was not investigated; the
prediction counts observations in the full model and does not model the mapper re-solving the
geometry without W. The held-out coverage of the other regions is lower than full in other ways as
well (`actual_collateral_coverage` in `holdout.json`: kicker R011, R012, R024; courtyard R005,
R008, R012, R016, R022, R054).

Grids tried (best candidate per grid by predicted collateral, then |W|, then points):

| Scene | 1/10 | 1/15 | 1/20 |
|---|---|---|---|
| kicker | R015, collateral 2, 8 images | R028, collateral 2, 6 images (chosen) | R008, collateral 3, 6 images |
| courtyard | R008, collateral 1, 10 images | R014, collateral 2, 9 images | R021, collateral 1, 7 images (chosen) |

The mapper is not bit-reproducible: an earlier run of the previous rule on kicker returned 857
points for its target in one run and 972 in another. These results are one run each; a repeat may
shift collateral numbers.

Full-run quality.json, for reference: kicker 30 of 31 registered, 1 component, reprojection
1.23 px mean and 2.30 px p95; courtyard 38 of 38, 1 component, 1.26 px and 2.29 px.
`pipes` (14 images) has no region that qualifies for the hold-out under the old rule and was not
re-run under the new one.

Lint: `make lint` passes. The MCP check: `mcp_check.py blind/courtyard` lists
`['get_summary', 'list_regions', 'get_region']` and calls each without error.

### The agent test

A fresh Claude Haiku session (`claude -p --model haiku`) gets only this server's three tools
(`--strict-mcp-config`, no other tools) and one neutral question: which single region most needs
new photographs, answered as `REGION=<id>`. The held-out runs are reached through
`blind/<scene>`, so the run id does not say what was removed.

| Run | Target | Agent's answer | Its evidence |
|---|---|---|---|
| `blind/kicker` | R028 | R028 | "zero coverage with zero images seeing it and zero reconstructed points, despite having 155 reference points" |
| `blind/courtyard` | R021 | R021 | "coverage 0.0002, only 1 point compared to reference of 132, with 0 images viewing it" |
| `kicker/returned` (control) | none | R009 | "worst photographic coverage at 5.56% of the full 360-degree view" |
| `courtyard/returned` (control) | none | R054 | "worst coverage (0.0508) with only 5 images seeing it and a thin_angle flag" |

The prompt and command are in [Run](#run) as `agent_test`; the MCP configuration points `uv run
--directory prototypes/RC-P3-quality python mcp_server.py`.

## Not covered

- **The agent's hint.** Each region carries its point count from the full run as a reference, so
  a region that lost everything is easy to see. A real capture has no "full run"; there the
  reference is the previous session, which is the gap-list use case, not a blind discovery.
- **One agent, one model, one run per scene.** Haiku only; no repeats.
- **Prediction quality.** The collateral prediction is right on kicker and misses five of six
  collateral regions on courtyard. Locality is checked after the fact, not guaranteed.
- **Partial loss.** The target loses all or nearly all points, so "dropped by half" is met with
  margin and does not test a partial loss; the point-count factor makes this nearly automatic.
- **Repeats.** One hold-out run per scene; the mapper's run-to-run variation is seen but not
  measured.
- **Other thresholds** than 5 observations for "seeing" and 3 to 35 percent for the target.
- **Scenes:** `pipes` was not run under the planned rule; no other scene was run.
- **Ground truth in the loop.** Regions are stable because each model is aligned to the ETH3D
  cameras. A real capture has no ground truth; there the frame has to come from the first
  reconstruction and later runs need an alignment to it. Not built.
- **GLOMAP models**, other machines, and the real-time or incremental update of quality.json.
- **Reasons for `not_registered`** beyond "no matches" and "matches but the mapper did not register
  it". The mapper does not report why.
- **Dense or mesh quality**, the gap list's `photo_not_joined` and `no_scale` kinds as separate
  records (the per-image verdict and `scale` carry the same facts), shot-card viewpoints, and
  uncertainty per point.
- **Authentication and HTTP transport.** The MCP server is stdio only and read-only.
- **A test suite.** The prototype has no pytest tests; the checks are the runs above.
