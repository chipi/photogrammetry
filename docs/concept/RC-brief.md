# Recce — Project Brief

*Seed document for the concept package. Input to the Step 0 prototypes and to RC-01 Vision.*

**Version:** 0.1 · Draft
**Prefix:** RC
**Name:** Recce (chosen 2026-11-24; formerly the working name "photogrammetry")
**Date:** 2026-11-23
**Inputs:** [landscape research](../wip/research-landscape-2026-11-23.md) ·
[robotics-lab contract](../wip/robotics-lab-contract.md) ·
[hardware and parallelism](../wip/hardware-and-parallelism.md)

---

## 0. Where this comes from

Two things drive the project, in this order.

**The robotics lab.** The owner's robots map an apartment and will soon carry RGB and depth
cameras. They know where they are, they can drive to viewpoints, and they need a model they can
place back into their map — at a known scale, in a known frame, with an honest statement of what
it does not know. Nothing open offers that as a service a robot or an agent can drive.

**A talk at a diving conference.** A photogrammetrist described buying a workstation of around
€20,000 because 1,500 Nikon D850 photos of an underwater site would not assemble into a model on an
M3 Pro laptop in the course of a day (the software was most likely Metashape). That is the problem
in one sentence: large underwater sets of high-resolution RAW photos need compute that one laptop
does not have, and today the answer is to buy one very expensive machine. The owner already has
several capable machines, and a rented GPU for one night costs a fraction of that workstation.

**Not satisfied with "it looks okay".** The owner is evaluating the existing tools in parallel and
is not happy with their outputs. Common practice is to load photos into Metashape, run a few basic
steps and accept what comes out. This project goes into the matter instead: understand each step,
measure what is wrong, and see how far a few weeks of focused work with AI coding agents can push
the quality. The first horizon is weeks, not a product roadmap.

What the owner finds wrong in current outputs — all of it: blurry or smeared textures, noisy or
melted geometry, holes, colour seams, wrong colour underwater, a scale that cannot be trusted, and
slow processing. Each becomes a measurement before it becomes a fix:

| Complaint | What the engine measures |
|---|---|
| Blurry, smeared textures | Per-image sharpness at ingest; texture resolution per surface area; which images each texel blends |
| Noisy or melted geometry | Depth-map consistency across views; point density and noise against the benchmark objects |
| Holes | Coverage per region; which regions no image sees well enough |
| Colour seams | Exposure and white-balance spread across the set; seam contrast in the texture |
| Wrong colour underwater | Colour against a reference target in the scene; range-dependent attenuation estimate |
| Untrustworthy scale | Scale state on every product; error against measured distances (scale bars, tags) |
| Slow | Wall-clock time per stage and per machine, transfer time, cost per run |

**Data comes when the software is ready for it.** The owner shoots the use-case sets (objects,
room, car, bikes) once the first engine can take them, and asks a friend for a large dive set,
with the friend's Metashape result as the baseline, in that same initial phase. Until then the
engine is developed against public datasets with published ground truth (candidates to check for
licence and fit: COLMAP's sample scenes, ETH3D, Tanks and Temples, Mip-NeRF 360, and the public
underwater sets published with Sea-thru and SeaThru-NeRF).

**Two horizons.** The project is shaped for where it should be, not only for its next step.

- **In six months: three equal pillars.** All the hardware as one pool, rented GPUs included;
  robots and agents as first-class clients; a photographer's tool from RAW to model, from Lego to
  reefs. No pillar is subordinate.
- **In the first month: three starting points.** Small objects (the learning path where the
  engine is built and measured), underwater sites (the case that exposes the compute and quality
  problem), and robots (the first real client). The car, the bikes and the rest of the
  [use cases](RC-use-cases.md) follow once those three work.

*Vision sentence under consideration* (from the 2026-11-23 review): "A reconstruction engine that
always says what it knows and what it does not — scale, frame, coverage, uncertainty — so that a
person, a robot or an agent can decide what to capture next, above water and below."

## 1. What it is

A self-hosted photogrammetry system that turns photographs into 3D models — meshes, point clouds
and gaussian splats — using every machine its owner has. It is one engine with three ways in:

**A web interface for people.** Drop in photos from an iPhone, a GoPro, a DSLR or a drone; watch
the reconstruction build; inspect, compare and export the result.

**An HTTP API and a command line for programs.** Robots, scripts and other projects submit capture
sets — often with camera poses and intrinsics already known — and receive a model with a stated
scale, frame and provenance.

**An MCP server for agents.** An agent starts and steers reconstructions, reads their quality
state (what registered, what didn't, where coverage is thin), compares variants and says what to
capture next.

**RAW in, no detour.** Photos arrive straight off the camera — NEF, ARW, ProRAW DNG, HEIC,
GoPro JPEG or video — without a pass through Lightroom. A simple but good-enough imaging pipeline
at the front (decode, white balance, exposure and tonality matched across the whole set) makes the
photos agree with each other before they are stitched, so the model's colour and light hold
together.

Underneath sits a coordinator and a pool of workers. A worker runs on any machine — Apple silicon,
an NVIDIA ARM64 box, an AMD Linux box, a rented cloud GPU — and advertises what it can do. The
coordinator splits a reconstruction into stages and pieces and places each one where it runs best.
The laptop alone runs the system end to end as far as its hardware allows: ingest, develop,
registration and a splat (Brush on Metal) today; dense depth and meshing need a CUDA or HIP worker
until a portable dense path exists (an open question). More machines make it faster and complete,
not different. When a job
outgrows the homelab, rented cloud GPUs join the same pool — declared as infrastructure as code,
started with the owner's go, gone when the job ends.

## 2. Who it is for

Built first for one person: a photographer and underwater photographer with an iPhone 15 Pro, a
GoPro, a Nikon D850, a Sony Alpha 1, a DJI Mini 4 Pro, and a homelab of heterogeneous machines.
Built equally for that person's robots, which map an apartment and hand over well-posed capture
sets through a file contract. And built for agents, which are a first-class client rather than an
afterthought.

### What gets scanned

The range is wide on purpose, and it is the main design pressure:

| Scale | Examples | Typical capture |
|---|---|---|
| Small | Lego toys, small parts, things around the house | iPhone, DSLR, turntable |
| Medium | Mountain bike, motorbike, car | iPhone, DSLR walk-around |
| Interior | The house from inside, room by room | iPhone (LiDAR, ARKit), robots |
| Large outdoor | A whole building | DJI Mini 4 Pro, DSLR |
| Underwater | Wrecks, reefs | GoPro, DSLR in housing |

One use case cuts across scales: **realistic assets for game engines** — a model clean enough
(textured, sized, sensible polygon count) to drop into a game engine, as some phone apps do today.

### A phone capture app

A small internal iPhone app that captures and sends straight to the system — no manual upload —
and carries what a web page can't reach: LiDAR depth and ARKit camera poses, written in the same
capture-set format the robots use (prototype RC-P11). Photos-only captures still come in through the
web interface.

### The engine at the centre

The project is an engine first. At its centre is one structured, scientific model of a
reconstruction: cameras and their calibration, images and their poses, matches and tracks, the
sparse and dense geometry, the mesh and the splat — each with its units, its frame, its
uncertainty and the step that produced it. Getting that geometry right is the work; everything else
is built around it.

The web interface, the HTTP API, the command line and the MCP server are faces on that engine, not
products of their own. The principle carries over from robotics-lab's Observatory: *agent first,
human friendly* — anything a page shows is something a command answers, and the reverse. The
coordinate frame and the scale are never hidden.

**AI is optional; the product is complete without it** *(owner, 2026-11-27)*. Every view, check,
quality report, readiness verdict, gap list and suggested shot works from geometry and rules
alone, and is good enough on its own: the version without AI is not a placeholder. AI comes in
two ways, both opt-in. First, Recce is an MCP server, so a person's own agent can drive it from
outside. Second, a person brings their own AI into Recce: an OpenAI-compatible endpoint (a hosted
provider such as OpenAI or Anthropic with their key, or a local model) set once in the settings.
With it connected, features inside Recce go further: the run is explained in words, assessments
and plans are written over the rule-based ones, and an agent places labels and shots in the scene.
What the AI adds is marked as written by AI and checked against the engine's own numbers; the
engine, not the AI, supplies positions and verdicts.

**Two registers in one interface** *(owner, 2026-11-24)*. The frame — panels, lists, inspectors,
settings, the timeline of a run — is a professional tool in the family of Lightroom, Autodesk's
products, Blender and Rerun, and follows robotics-lab's look (its Observatory and Mission Control:
dark by default, an outliner, a read-only inspector, label-left and value-right in mono, shared
design tokens). The 3D scene and everything that explains a reconstruction is where the project
sets out to be different: illustrative, not technical; beautiful at every step, not only at the
end; explaining what the engine did and why, with imagery good enough to show to someone who does
not know the field. Existing tools present photogrammetry as a technical process that ends in a
mediocre model; this one shows each stage as something to look at and understand — the cameras
finding each other, the matches that hold the model together, where coverage is thin, what a
recipe changed. The geometry and the rules carry this on their own; with AI connected, agents
and multimodal models take it further: an agent can look at the intermediate products, describe
them and point at what matters. Beauty here is not decoration: the
interface is the connection between a person and the machine, and software that looks right is
simpler and more intuitive, which is what makes a complex concept understandable. That is why the
3D scenes and the explanations carry so much weight. Inspiration reaches past Rerun, Blender and
Foxglove to the most refined professional and explanatory software: colour and finishing tools
such as DaVinci Resolve, design tools such as Figma and Linear, 3D tools such as Cinema 4D and
Spline, and explanatory work such as Bartosz Ciechanowski's interactive articles and NASA's Eyes
on the Solar System. The owner's taste drives this register; the agent's part is to propose
boldly, build quickly to look at, and take critique.
The design system (RC-05) and the UX specs carry the detail.

**Upload and it lines up.** The heart of the engine is registration: a thousand unordered photos
of a wreck go in, and the engine finds features, chooses which photos to compare, verifies matches
against two-view geometry, builds a view graph, solves every camera's position and refines the
whole by bundle adjustment — calibrating the lenses as it goes, across mixed cameras. It rejects
what doesn't fit with a stated reason, and when a capture falls apart into separate pieces it says
where the link is missing instead of failing silently.

**Strategies, not one pipeline.** Each stage is a contract with several implementations — global
(GLOMAP) and incremental (COLMAP) pose solving, a learned first pass, later a refractive camera
model. Named recipes bundle the right choices for a capture type (turntable object, walk-around,
interior, aerial, underwater, robot); the engine proposes one from the evidence and says why, and
falls back when a stage underperforms. Control comes in three levels — automatic, recipe, expert.
The owner's own captures, with measured reference dimensions, form a benchmark set that turns
"this strategy is better for reefs" from opinion into a table.

## 3. What makes it different

**It uses all the hardware.** Distribution exists elsewhere — WebODM schedules onto many nodes,
Meshroom runs on a render farm, Metashape Professional has network processing over shared storage,
Brush trains splats on Metal and Vulkan — but none places stages by capability across CUDA, Metal
and HIP machines that come and go, with rented GPUs joining for a night. This system treats a laptop, a GPU box and an
idle desktop as one pool, across CUDA, Metal and HIP, with workers that join and leave.

**Parallelism in every form.** Per-image and per-pair fan-out, spatial partitioning of large
scenes, a streaming pipeline that starts while photos are still uploading, and comparative runs
of different pipelines side by side.

**Known poses are first-class.** Most tools estimate everything from pixels. Here a robot's poses,
an iPhone's ARKit track or a drone's GPS are priors the pipeline uses, refines and reports on —
and the result states its scale and frame, or says plainly that the scale is arbitrary.

**Quality is visible, not implied.** Registration, reprojection error, coverage and the
differences between pipelines are state the UI shows and an agent can read — not a log file
behind a "done" flag.

**It explains as it goes.** Every stage has a picture worth looking at, not only the final model:
the reconstruction is shown as a story of how it was made, with the evidence for each claim on
screen. The 3D presentation is designed, not a default viewer with a grid.

**Underwater is a first-class case.** Refraction, colour loss with depth, backscatter and moving
subjects are the conditions the owner shoots in, not an edge case to ignore.

**Against the reference.** Agisoft Metashape is the industry reference: mature, accurate,
$3,499 for the Professional edition with network processing. Its distribution splits work per
task onto workers sharing one storage path; it documents CUDA and OpenCL but not Metal; and its
2.3 release trains no gaussian splats and models no underwater refraction
([research](../wip/research-metashape-underwater-2026-11-23.md)). Those four gaps are this
project's openings.

*Pending:* the minimal feature set — table stakes versus differentiators — is drafted in the
[product feature analysis](../reference/product-feature-analysis.md) §6 and decided in the
interview. Agreed so far: splats are in the MVP, bounded.

## 4. Scope boundary

A reconstruction tool: photographs and poses in, models with provenance out.

### Non-goals for the concept phase

- Capture control of robots and drones. They capture with their own software (the internal iPhone
  app records a capture set; it does not steer anything); this system states
  what a good capture needs and judges a capture after the fact.
- Navigation-grade or survey-grade output. A pleasing model is not collision-safe and not a
  survey; models carry their scale and uncertainty, and say what they are not.
- A cloud service, accounts or multi-tenancy. One owner, their machines, their data.
- Model weights or tools under non-commercial licences in the default stack. They may be optional
  and are labelled where used.
- Robotics code. The robot seam is files and a command line; nothing from robotics-lab is imported.

### Name and terminology (owner, 2026-11-24)

The project is **Recce**: short for reconnaissance, the survey that goes ahead of a mission. It
fits the robots doing autonomous mapping runs and the drones surveying terrain, and works as a
verb for anyone ("recce the wreck"). The theme stays light inside the product, which has to be
plain to anyone who knows the field:

- **Domain terms come first and stay primary:** capture set, reconstruction, camera pose, point
  cloud, mesh, splat, scale, frame, coverage, quality report, gap list.
- **A few mission words are allowed, always beside the standard term,** never instead of it:
  a capture run may be called a *sortie*, the quality report a *debrief*, the gap list a
  *brief for the next sortie*. A screen title or a doc heading uses the standard term; the mission
  word is a secondary label at most.
- **No military vocabulary beyond these.** No ranks, no callsigns, no "intel", no "targets" in
  the user-facing text (the gap-list data field `targets` is a technical name, not a label).
- **The engine package and command stay `recon`**, as agreed in the robotics-lab contract.

### Settled in the interview (2026-11-23)

- **Three pillars, equal — the six-month shape.** All the hardware as one pool; robots and agents
  as first-class clients; a photographer's tool from RAW to model. No pillar is subordinate. The
  first month starts from small objects, underwater sites and robots (§0, *Two horizons*).
- **The iMac Pro is out** (2026-11-24). The design and the prototypes use the M4 Pro, the X3,
  the GB10 and rented GPUs.
- **Storage stays conservative** (2026-11-24). Keep what cannot be recomputed, evict what can, and
  add external disks to a machine when space runs short; the rule is in the
  [architecture sketch](RC-architecture-sketch.md) §8.
- **The X3 is home.** The coordinator runs on the X3, always on. The laptop is a client and a
  worker, and runs the whole system alone when offline in the field.
- **RAW pipeline: prototype both.** A minimal own pipeline (rawpy/LibRaw, set-wide white balance,
  exposure and tone) and darktable driven from its command line are compared in RC-P5.
- **The iPhone app starts in Step 0** (revised 2026-11-23; first answer was "a later surface").
  An internal capture app, installed on the owner's iPhone, records photos with ARKit poses,
  intrinsics and LiDAR depth and sends them to the engine. It writes the **same capture-set format
  as robotics-lab's robots**, so the phone and the robots share one ingest path. Web upload stays
  for photos-only captures.
- **Open source from the start, MIT** (decided 2026-11-24; first answer was "open source later").
  The default stack stays permissive (BSD, MIT, Apache). Copyleft tools run only as external
  processes, restricted weights are never shipped, and no dataset lives in the repository — the
  rules are in [Licensing](../LICENSING.md).
- **Assets land in Unreal Engine, Unity, Godot and Blender.** All four are targets for the
  game-engine use case.
- **First scans, easiest to hardest:** a matte household object (clean baseline), a Lego model
  (fine detail, turntable, masking), a room (ARKit and LiDAR priors, low-texture walls), the
  mountain bike (thin tubes, spokes, shiny parts).
- **Engine language: Python first, Rust kept open.** Prototypes and the first engine are Python,
  next to the field's tooling (pycolmap, PyTorch, gsplat, rawpy). The data model is
  language-neutral from day one — a documented on-disk schema and a coordinator–worker wire
  protocol — so the coordinator or a worker agent can move to Rust where measurement says so. The
  question stays open in RC-04 and closes on the evidence from RC-P1, RC-P2 and RC-P7.

- **Architecture leanings** (own pull-based worker protocol; one three.js scene; layered capture
  advice; splats in the MVP, bounded) are recorded in the
  [architecture sketch](RC-architecture-sketch.md) §9, for the prototypes to confirm.

- **One monorepo.** Engine, workers, web UI, the iPhone app (`apps/ios/`) and infrastructure as
  code live in this repository. Robotics-lab stays separate, joined by the capture-set format.

### Open from the start

Final name; implementation language and stack; how workers are deployed and secured on
the tailnet; which mesh, point-cloud and splat formats; where photos live and how long.

## 5. Step 0 — Prototype plan

The hard parts here are computational and distributed; the architecture cannot be written honestly
until they are proven. A prototype counts as **proven** when it meets its stated criterion — not
when it looks plausible. A failure with its evidence is also a result.

*Restructured 2026-11-24* after the [advisor review](../wip/review-fable-2026-11-23.md): the
platform matrix merged into the baseline; the iMac Pro dropped from the prototypes; distribution
moved onto a large set with dense depth as its unit of work; quality state moved early with a
hold-out test; every criterion made measurable. Development runs on
[public datasets](../reference/public-datasets.md) until the owner's own captures and the
friend's dive set arrive. Numeric tolerances were agreed with the owner on 2026-11-24.

**Progress** is kept in [Step 0 status and findings](../wip/step0-status.md); each prototype's
README holds its numbers.

**Old numbers → new:** P1 and P2 → P1 · new P2 · P6 → P3 · new P4 · P7b → P5 · P7 → P6 · P3 → P7 ·
P4 → P8 · P5 → P9 · P9 → P10 · P10 → P11 · P8 → P12.

**Two tracks, one meeting point** *(owner, 2026-11-24)*. Step 0 runs two tracks side by side. Below,
the **prototypes** (RC-P1..P13) prove how the technology works. Above, the **mock-ups** (RC-M<n>,
in `mockups/`) work out how the product looks and behaves: every concept in the
[visual ideas](../wip/visual-ideas.md) catalogue is mocked, looked at and critiqued before anything
is built. A mock-up is proven when the owner has judged it on screen and the concepts it carries
are kept, changed or dropped with a reason. Mock-ups use real outputs from the prototypes wherever
they exist (RC-P1's cameras and points first), so the picture shows real data, not invented data.
The two tracks meet in the first build phase, where the PRDs, RFCs and UX specs draw on both, and
the build starts from a worked-out design rather than discovering one.

### A — Foundation

#### RC-P1 — Registration on every machine

**Proves:** The registration core end to end on real photos, which machine runs it, and where the
time goes.
**Input:** ETH3D high-resolution training scenes (DSLR, 6048×4032, laser-scanned ground truth and
ground-truth poses; CC BY-NC-SA 4.0).
**Proven when:** GLOMAP and COLMAP each register at least two ETH3D scenes from the same verified
matches on the M4 Pro, the X3 and the GB10; each machine × stage cell is pass, fail or CPU
fallback, backed by a command and its output; per strategy, the record holds registration rate,
reprojection error (mean and 95th percentile), wall-clock time per stage, and pose error against
ETH3D's ground truth after Sim(3) alignment (rotation in degrees, position as a fraction of the
scene's extent).

#### RC-P2 — The expensive stages on the GPUs

**Proves:** The two platform facts the hardware pillar rests on.
**Proven when:** COLMAP's dense depth runs on one ETH3D scene on the X3 through a HIP build
(gfx1151) and on the GB10 through CUDA, and gsplat trains a splat on the GB10 — or each failure is
recorded with the error and what was tried. The GB10's available CUDA time under its shared-GPU
schedule is recorded. If neither GPU path works, the rented GPU becomes the planned CUDA
worker and the architecture sketch says so.

#### RC-P3 — Quality state an agent can read

**Proves:** That the engine's quality state is enough for an agent to find a real weakness.
**Proven when:** `quality.json` v0 (registration rate, connected components, per-image verdict and
reason, reprojection mean and tail, coverage per region, scale state) is produced from RC-P1 and
served through three MCP read tools; then a **hold-out test**: all images seeing one region of an
ETH3D scene are removed, the region's coverage metric drops by at least half *(agreed 2026-11-24)*, an agent
with only the MCP tools names that region among the scene's regions, and when the images return the
metric recovers.

### B — Products against ground truth

#### RC-P4 — Dense, mesh, texture and splat, measured

**Proves:** That the products are measurably good, not just plausible.
**Input:** ETH3D evaluation scans; Mip-NeRF 360 for splats.
**Proven when:** Dense cloud and mesh are scored against ETH3D's laser scans for accuracy,
completeness and F-score at ETH3D's evaluation thresholds (1, 2, 5, 10, 20 and 50 cm, with the BSD-licensed ETH3D multi-view-evaluation tool); the textured mesh
and the splat come from the same poses; the splat's PSNR and SSIM on held-out views of at least two
Mip-NeRF 360 scenes are recorded; the seven complaint measurements of §0 each have a first number.

#### RC-P5 — RAW to a consistent set

**Proves:** That a develop stage replaces the Lightroom step without hurting reconstruction, and
which develop route to use.
**Input:** ETH3D's NEF RAW files (the only public RAW set with laser ground truth found).
**Proven when:** Three routes — the dataset's own JPEGs, a minimal own pipeline (rawpy, set-wide
white balance and exposure), and Chemigram/darktable through its command line — each reconstruct
the same scene; registration rate from RAW is no worse than from JPEG; the exposure and white-balance
spread across the set and the seam contrast in the texture are measured for each; one route is
chosen on those numbers.

#### RC-P6 — Mesh and splat in the browser

**Proves:** That one three.js scene shows the mesh and the splat together, on the laptop and the
iPhone.
**Proven when:** A RC-P4 mesh and a splat of about one million gaussians load together in one
three.js scene from the result's files, render at 60 fps or more on the M4 Pro and 30 fps or more on
the iPhone 15 Pro *(agreed 2026-11-24)*, and the same result also exports to Rerun as the engineering view.

### C — Scale: the reason the project exists

#### RC-P7 — Distribution on a large set

**Proves:** The central bet — that splitting the expensive work across machines, including a
rented GPU, beats the best single machine after transfer costs.
**Input:** COLMAP's Graham Hall (1,273 images) as the public stand-in; the friend's dive set when it
arrives.
**Proven when:** Dense depth per view runs split across the GB10, the X3 and one rented GPU, and the
registration is cut into clusters solved on different machines and merged; the merged poses match a
single-machine run within 0.1° rotation and 0.1% of the scene's extent in position, and dense depth
maps match within 1% median relative difference *(agreed 2026-11-24)*; wall-clock time, transfer time and
rental cost are recorded against the fastest single machine. If splitting does not pay, the set size
at which it would is the number recorded. *Deferred to the build phase (owner, 2026-11-26): important, but not piloted in Step 0.*

#### RC-P8 — Learned and classical, compared

**Proves:** Whether MapAnything's Apache checkpoint is a useful first pass — fast poses and metric
scale — checked by bundle adjustment.
**Input:** ETH3D (ground-truth poses); ARKitScenes (iPhone ARKit poses and LiDAR; non-commercial,
development only).
**Proven when:** On both, with and without pose priors, the learned-then-bundle-adjust route and the
classical routes are compared on registration rate, pose error against ground truth, and scale
error; the result decides whether the learned first pass enters a recipe.

### D — Robots and the phone

#### RC-P9 — A robot's capture set

**Proves:** The file contract and metric placement.
**Input:** An own fixture first — a Blender render of a room with exact camera poses, written in
the capture-set format; a Gazebo set from robotics-lab when it exists.
**Proven when:** `recon` reads the set, writes a model and `provenance.json`, and with exact poses
the model's scale error is under 0.5% and its placement error under 1% of the scene's extent in the
given frame *(agreed 2026-11-24)*; the frame conversions (axes, handedness, camera-to-world) are checked by
the render's known geometry.

#### RC-P10 — A room from inside

**Proves:** That an interior registers as one model, and what LiDAR and ARKit add.
**Input:** ARKitScenes first; the owner's room later ([use cases](RC-use-cases.md) UC-B1).
**Proven when:** With poses and depth, the room gives one metric model (TSDF mesh plus splat) whose
wall lengths match the reference within 2% or 2 cm, whichever is larger *(agreed 2026-11-24)*; photos-only,
the room either registers as one model or the engine reports its separate components and where the
links are missing.

#### RC-P11 — The iPhone capture app

**Proves:** That a small internal app captures what the Camera app cannot — ARKit poses, intrinsics
and LiDAR depth with each photo — in the shared capture-set format.
**Timebox:** one week *(agreed 2026-11-24)*; it starts once RC-P8 or RC-P10 shows that pose priors improve
the result.
**Proven when:** The app writes a capture set that the engine's ingest reads unchanged, alongside a
RC-P9 robot set; per-frame intrinsics, the image format and the ARKit-to-capture-set axis
conversion are in the format (amendments proposed to robotics-lab); photos are at the highest
resolution ARKit allows while tracking *(to verify)*.

### E — Underwater

#### RC-P12 — Underwater

**Proves:** That the pipeline holds up underwater, and what refraction modelling and range-based
colour correction add.
**Input:** AquaMVS (lab refraction tests with a ChArUco board; CC BY 4.0) and SQUID (RAW with
distance maps; non-commercial); SeaThru-NeRF scenes for splats.
**Proven when:** On AquaMVS, distances between board corners are measured with the standard camera
model and with a refractive model, and the error of each is recorded; on SQUID, range-based colour
correction with ranges from the reconstruction is compared with uncorrected images on the scene's
reference targets (identical DGK Color Tools charts placed at several distances); the open underwater benchmark is
specified from what the public sets lack. *The "ranges from the reconstruction" part moved to the open benchmark's site scene S1 (owner, 2026-11-26): on SQUID it cannot be met, and Step 0 does not test it.*

### F — Structured models *(added by the owner, 2026-11-26)*

#### RC-P13 — A structured model from a reconstruction

**Proves:** That an agent can turn a reconstruction and a little context (a few photos, one line
of description) into a structured model (walls and rooms, passages, terrain and buildings) in which
every element states whether it is measured, inferred or unknown, and how sure it is. The model is
written once in a tool-neutral description; Blender, driven headless by the agent, is the first
tool to build it, and others can follow against the same description.
**Input:** three segments. Interior: RC-P10's room with the Faro scan (ARKitScenes). Cave from
inside: a public cave set with a laser or survey reference, to be chosen. Drone over ground: EuroSDR
RPAS Phase 2, Phantom 4 RTK (CC BY 4.0), with RTK positions and ground control.
**Proven when:** In each segment the agent builds the structured model through the tool-neutral
description, every element carries a source and an uncertainty, nothing tagged measured lacks
support in the reconstruction, and the measured dimensions meet the segment's reference: room
walls and floor area within 2% or 2 cm of the Faro scan; cave passage widths and heights against
the set's reference, tolerance set when the set is chosen; drone terrain heights and building
footprints against the control points. The number of agent iterations and where they went wrong
is recorded.

### After Step 0 — the owner's data

When the engine takes captures end to end, the owner shoots the use-case sets
([use cases](RC-use-cases.md)) and asks the friend for the dive set, with its Metashape result as the
baseline. Both join the benchmark set.

## 6. Sequence after Step 0

Prototypes and mock-ups → RC-01 Vision → RC-03 Data Catalog → RC-04 Technical Architecture → RC-05 Design
System → RC-02 Project Concept → RC-00 Introduction → audit → PDF.
