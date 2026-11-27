# Step 0 close-out report (2026-11-27)

The input to RC-01 Vision. It states what Step 0 set out to prove, what it proved and did not,
what the mock-ups settled, and what carries into the build. The numbers come from
[Step 0 status and findings](step0-status.md) and from each prototype's and mock-up's README,
which hold the full results and their "Not covered" lists; this report adds no new measurement.

## What Step 0 set out to do

Two tracks ran side by side ([brief](../concept/RC-brief.md) §5). The **prototypes** (RC-P1 to
RC-P13) prove how the technology works; a prototype counts as proven when it meets its stated
criterion, and a failure with its evidence is also a result. The **mock-ups** (RC-M1 to RC-M8)
work out how the product looks and behaves; a mock-up is done when the owner has judged its
concepts on screen. Step 0 ends when the mock-ups have the owner's verdicts and this report is
written (owner, 2026-11-27). Everything ran on public datasets with published references; the
owner's own captures and the friend's dive set come after.

## Outcome at a glance

| | Proven | Partly proven | Not proven | Deferred or not started |
|---|---|---|---|---|
| Prototypes (13) | 9: RC-P1, P2, P3, P4, P5 (one scene), P6, P8, P9 (the fixture), P12 (one clause moved) | 1: RC-P13 | 1: RC-P10 | 2: RC-P7 (deferred to the build), RC-P11 (waits on pose priors) |

| Mock-ups (8) | Kept by the owner | Not built |
|---|---|---|
| | 7: RC-M1 to RC-M7, every concept kept; RC-M5 and the coach added to RC-M1 and RC-M2 judged good to go as a prototype (2026-11-27) | RC-M8 (after RC-P11) |

## The prototypes

| Prototype | Status | What it showed |
|---|---|---|
| RC-P1 Registration on every machine | Proven | COLMAP and GLOMAP register kicker, courtyard and pipes on the X3, the M4 Pro and the GB10. GLOMAP maps 3–4 times faster with the same pose accuracy and about twice the reprojection error (1.9–2.9 px against 1.1–1.3 px), cause unknown |
| RC-P2 The expensive stages on the GPUs | Proven | Dense depth on courtyard in 1,169 s through CUDA on the GB10 and 3,205 s through HIP on the X3 (a ROCm container, COLMAP's new HIP backend); a gsplat splat on the GB10 |
| RC-P3 Quality state an agent can read | Proven | An agent with three MCP read tools names the held-out region on both scenes, once the removal is local |
| RC-P4 Dense, mesh, texture and splat, measured | Proven | Courtyard F1 at 5 cm 0.35 from RC-P1's poses, 0.88 from ground-truth poses; splats at PSNR 27.7 (garden) and 29.2 (counter); every one of the seven complaints has a first number |
| RC-P5 RAW to a consistent set | Proven on one scene | The minimal rawpy route registers 14 of 14 with the most even white balance and is chosen |
| RC-P6 Mesh and splat in the browser | Proven | Mesh and a 1,000,000-gaussian splat together in three.js and Spark: 59.9 fps on the X3's iGPU, 58.8–60.0 on the M4 Pro (60 Hz display), 50.0 on the iPhone 15 Pro against 30 |
| RC-P7 Distribution on a large set | Deferred to the build (owner, 2026-11-26) | Not run; the [GPU rental spec](gpu-rental-p7.md) is ready |
| RC-P8 Learned and classical, compared | Proven | MapAnything plus bundle adjustment comes close to COLMAP on ETH3D and covers frames COLMAP drops on two ARKit videos, but fails without warning on two others; its metric scale is off by up to 29% (ETH3D) and 41% (ARKit). An agreement check gets 15 of 16 runs right with no wrong pass |
| RC-P9 A robot's capture set | Proven on the 1.2 m fixture | Scale error 0.021% (limit 0.5%), placement 0.18% of extent (limit 1%); frame conversions checked by render, wrong conventions fail |
| RC-P10 A room from inside | Not proven | 183 of 190 Faro distances within 2% or 2 cm; the seven failures are one 1.05 m passage, the mesh's own. Photos only: one of five rooms registers as one model, and `recon components` reports the breaks |
| RC-P11 The iPhone capture app | Not started | Starts once RC-P8 or RC-P10 shows pose priors help; RC-P10's finding (with poses and depth the rooms meet the wall limit, photos only four of five split) is the evidence, and the owner puts it in context |
| RC-P12 Underwater | Proven, one clause moved | Refractive model +0.017% scale and 1.15 mm RMSE against pinhole −1.50% and 5.83 mm (−4.8% on one frame). One white balance on the RAW makes grey patches grey at 6–19 m (median 1.4°). Ranges from our own reconstruction fail on SQUID; that clause moved to the open benchmark's site scene S1 |
| RC-P13 A structured model | Partly proven, closed by the owner | Room 13 of 13 dimensions within 2% or 2 cm of Faro; cave 11 of 17 within 2% or 5 cm (not met); drone 50 of 50 check points within 2σ after one shift from control points, 0.25–0.38 m of the offset unexplained; buildings 31 of 49 at IoU 0.5 against 80% needed (not met) |

## What the evidence says about the vision

The vision sentence under consideration in the brief is: "A reconstruction engine that always
says what it knows and what it does not — scale, frame, coverage, uncertainty — so that a person,
a robot or an agent can decide what to capture next, above water and below." Step 0 tested each
part of it.

**Scale comes from priors and references, never from pixels alone.** With exact poses a robot's
set lands within 0.021% scale (RC-P9); RTK priors on half a drone's photos fix scale to +0.025%
(RC-P8, RC-P13); a learned model's metric scale is off by up to 41% (RC-P8), so it never sets
scale. A photos-only reconstruction has no scale, and the mock-ups say so on screen (RC-M1's "scale: arbitrary"). The
drone and building segments show a second limit: a focal length 0.6–1.3% long trades against
flying height, so the surface reads 0.3–1.1 m low until control points or a calibrated lens
pin it.

**Frame is a contract that can be checked.** The robot set's axes, handedness and quaternion
order are verified by render, and both wrong conventions fail (RC-P9).

**Coverage predicts error, and an agent can read it.** On RC-P10's room, surfaces no frame saw
are 52.4 mm from the Faro scan and those seen by 32 or more frames 14.7 mm (RC-M2). An agent
with read tools finds a held-out region (RC-P3). Where to stand next is the engine's job: an
agent inventing positions put 0 of 3 shots where a photographer can stand, and 3 of 3 with the
engine's spots (RC-M3).

**Uncertainty can be carried per element.** A structured model tags every wall, floor and
passage as measured, inferred or unknown with its sigma (RC-P13); the room meets its reference on
every measured dimension and marks 1.92 m² of floor it never saw as unknown, not guessed.

**Underwater is a scale problem first.** A pinhole calibration through a flat port misses scale
by up to 4.8% depending on where the object is; a refractive model holds ±0.28% (RC-P12). Colour
needs the RAW: the published TIFs clip red to zero on 78–99.9% of pixels. The cast at 6–19 m is
one global tint; what changes with range is contrast, which the simple backscatter fit restores
unevenly.

**The central bet is not yet tested.** That splitting the work across machines and a rented GPU
beats the best single machine (RC-P7) is the reason the project exists, and Step 0 did not run
it. What exists is the ground under it: the same registration on three machines and three
architectures (RC-P1), dense depth on CUDA and HIP (RC-P2), and the measurement that dense depth
and a splat together need up to 50 GB of GPU memory.

## The seven complaints, first numbers

The brief turns each of the owner's complaints into a measurement (§0). Each now has a first
number (RC-P4, RC-P12):

| Complaint | First number |
|---|---|
| Blurry, smeared textures | A texel covers a median 10.2 mm on seen faces; 89% of the textured area comes from one photo |
| Noisy or melted geometry | Courtyard F1 at 5 cm: 0.35 from our poses, 0.88 from ground-truth poses; poses decide dense quality |
| Holes | 16% of the courtyard mesh's faces are seen by no photo |
| Colour seams | Median ΔE 2.48 across seams against 2.14 inside patches |
| Wrong colour underwater | Grey patches a median 31.1° from grey with the camera's white balance, 1.4° after one white balance on the RAW (15 charts, 6–19 m) |
| Untrustworthy scale | Pinhole underwater up to −4.8%; learned metric scale up to 41% off; robot priors 0.021% |
| Slow | GLOMAP maps 3–4 times faster than COLMAP; dense depth 1,169 s (GB10, CUDA) against 3,205 s (X3, HIP) |

## What the mock-ups settled

Seven mock-ups were built on real prototype output, except RC-M5, which is synthetic by design.
The owner kept every concept of RC-M1 to RC-M7, the coach on RC-M1 and RC-M2 included; what goes into the product is
decided when the build starts. The patterns they share ([visual ideas](visual-ideas.md)):

- **The reconstruction as a story with evidence** (RC-M1, RC-M3): the run replayed camera by
  camera, a debrief whose every claim opens its evidence in the scene, and a claim without
  evidence flagged.
- **Quality on the surface** (RC-M2): light and shadow by how many frames saw a surface,
  confidence as solid or hatched, the reference beside the estimate where one exists.
- **The gap list as the brief for the next capture** (RC-M1): each gap with where to stand, what
  to shoot and why, a site map, and the same list as JSON for a robot.
- **Recipes as node graphs, compared by the node that differs**, with cost estimated before and
  measured after (RC-M4).
- **A presentation that stays honest** (RC-M6): a path through the photos, the splat where it
  holds and the mesh where it does not, and an "About this model" card on every shared link.
- **Underwater made visible** (RC-M7): the water's colour against each correction, and the
  refraction as a lens that can be switched off.
- **A camera is its photo**: every scene draws a camera as its image where it was taken.
- **AI is optional, and a coach when present** (owner, 2026-11-27): every view works from
  geometry and rules alone; with the person's own AI connected it explains why, orders a plan
  from the engine's own actions, says how to know it worked and what the facts cannot say, and
  every number it writes is checked against the fact it cites. One recorded call each on RC-M1,
  M2 and M7 cost US$0.038–0.082; RC-M5's five tutor calls cost US$0.083 together. Unsupported
  statements per mock-up: 0 (RC-M1, RC-M7), 1 (RC-M2), 3 of 51 (RC-M5). One wrong statement
  without a number got through on RC-M1; the checker cannot catch such a statement.
- **What an AI call costs depends on its context, not its prompt**: the same call cost US$1.75
  with an agent's default context and US$0.028 without it (RC-M4).

## Decided by the owner during Step 0

- AI is optional; Recce is complete without it, and is an MCP server for a person's own agent
  (2026-11-27).
- The learned route is an optional second route beside COLMAP, kept only after the agreement
  check, never the source of scale (RC-P8).
- Recipes, per-device corrections and tuned settings live in a separate private repository; the
  public engine keeps them separable (2026-11-26).
- RC-P7 moves to the build phase; RC-P10 stays not proven with its cause recorded, pose
  refinement moves to the build; RC-P13 closes partly proven; the cave tolerance is 2% or 5 cm
  (2026-11-26 and 2026-11-27).
- The underwater benchmark capture is decided after the rest of Step 0 (2026-11-26).

## Carried into the build

| Open | Where it stands |
|---|---|
| Distribution across machines and a rented GPU (RC-P7) | Not run; the deciding test of the project's central bet |
| The iPhone capture app (RC-P11) and its mock-up (RC-M8) | Not started; whether RC-P10's finding opens it is the owner's call |
| Pose refinement | The first lever on dense quality (F1 0.35 against 0.88), and the untried fix for RC-P10's short walls |
| Why RC-P1's poses sit 6.1 cm from courtyard's truth; why GLOMAP's reprojection is twice COLMAP's | Not investigated |
| Splats seen from outside the capture positions | Needles and floaters; quality was not a clause of RC-P6 |
| Building outlines (RC-P13) | 31 of 49 at IoU 0.5; merged neighbours and roof-against-wall outlines fail |
| The underwater ranges clause (RC-P12) and the benchmark capture | Moved to the benchmark's site scene S1; capture decided later |
| Engine language and UI stack | Python stays; Rust was to close on RC-P1, RC-P2 and RC-P7, and RC-P7 is missing. The UI stack is decided on the mock-ups' evidence |

## What RC-01 Vision can take from this

These are proposals for the owner, drawn from the evidence above:

- The vision sentence holds as written: each of its parts (scale, frame, coverage, uncertainty,
  the next capture, above water and below) has a working first result.
- Scale is stated, never inferred: from priors, references or control points, or reported as
  arbitrary. A learned model may propose poses; it never sets scale.
- The engine supplies positions, numbers and verdicts; an AI explains, orders and coaches, and is
  checked against the engine.
- Distribution remains untested; where it sits in the build's order is open.

Decided by the owner after this report (2026-11-27): the first case is the owner's home with the iPhone app, objects first and then a whole room, leading into the robot cases; learn mode is a feature inside the product. Both are recorded in the [brief](../concept/RC-brief.md) §4.

## Not covered

- **Public data only.** No owner capture and no dive set; one scene per prototype in several
  cases (RC-P5 on pipes, RC-P9 on its fixture, RC-P12 on one site and one rig).
- **This report summarises;** it does not re-run or re-check any number. The prototype READMEs
  are authoritative.
- **Mock-up verdicts are on concepts,** not on finished design; RC-M2 to RC-M7 had one phase each.
- **No cost model** for a full capture end to end: per-stage times exist for single scenes, not
  for a 1,500-photo set.
