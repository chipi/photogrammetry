# RC-01 — Vision

**Version:** 0.1 · Draft
**Date:** 2026-11-27
**Inputs:** [brief](RC-brief.md) · [Step 0 close-out report](../wip/step0-closeout-2026-11-27.md) ·
[architecture sketch](RC-architecture-sketch.md) · [use cases](RC-use-cases.md) ·
the owner's direction after Step 0 (2026-11-27)

This document sets out what Recce is for, how it looks and works from the outside, and where it
starts. The brief holds where the project comes from; the close-out report holds the evidence; the
architecture (RC-04) and the design system (RC-05) follow from this.

---

## 1. The vision

> **Recce turns photographs of a real place or thing into a measured model that states what it
> knows, shows what it does not, and plans the next capture. It runs from the person's own laptop
> as a control tower: the heavy work goes to their other machines or to a GPU rented by the hour,
> and the photographs, the models and the know-how stay theirs. The same loop serves a
> photographer, a diver, a robot and an agent, above water and below.**

Three ideas carry it.

**One loop for every case.** Capture, reconstruct, debrief, brief, capture again. A shoe on a
table, a room, a car park, a drone's survey, a lava tube and a wreck differ in who captures, what
gives the model its scale, and what goes wrong; the loop is the same.

**A control tower, not a bigger computer.** The answer to a 1,500-photo dive is not a €20,000
workstation. The person's laptop runs Recce and decides; the work that needs CUDA and hours of GPU
goes where that hardware is: a machine at home, or a GPU rented by the hour and gone when the job
ends.

**Own the outcome.** The photographs stay on the person's machines unless they choose to send
them; the models carry their provenance; the recipes and corrections learned from their own
captures are theirs. Nothing depends on a subscription to someone else's cloud.

## 2. Why it exists

A photogrammetrist at a diving conference bought a workstation of about €20,000 because 1,500
Nikon D850 photos of an underwater site would not assemble on a laptop in a day. That is the
problem in one sentence: the work needs compute one laptop does not have, and today the answer is
to buy one very expensive machine.

Three more reasons sit beside it.

- **"It looks okay" is not good enough.** Common practice is to load photos into a tool, run its
  steps and accept what comes out: smeared textures, melted geometry, holes, colour seams, wrong
  colour underwater, a scale that cannot be trusted, slow processing. Recce measures each of these
  before it fixes them; Step 0 gave every one a first number.
- **Robots need honest models.** A robot that maps a home needs a model at a known scale, in a
  known frame, with a statement of what it did not see. Nothing open offers that as a service a
  robot or an agent can drive.
- **The field is where the work happens.** The person shooting a wreck, a building or a cave is
  away from home with a laptop, and wants the day's work processed by the next morning, with
  a clear answer to "what do I shoot tomorrow?"

## 3. The loop

| Step | What happens | Mission word, beside the term |
|---|---|---|
| Capture | Photos, RAW, video, poses and depth come in through one capture-set format, from a phone, a camera, a drone or a robot | sortie |
| Reconstruct | A recipe chosen for the case runs over every machine the person has | |
| Debrief (quality report) | Scale, frame, coverage and uncertainty for every part of the model, each claim with its evidence | debrief |
| Brief (gap list) | What to shoot next, from where and why: cards for a person, JSON for a robot, MCP for an agent | brief for the next sortie |

The loop is what makes a model trustworthy. Step 0 showed why: on a scanned room, surfaces that
no frame saw are 52.4 mm off the laser reference, surfaces seen by 32 or more frames 14.7 mm. A
visible gap is worth more than a pretty model, because the next capture can close it.

### The cases it serves

| Case | Who captures | What gives scale and frame | What goes wrong | What comes out |
|---|---|---|---|---|
| Object (shoes, Lego, a camera) | The person, iPhone or DSLR, turntable | ARKit, a scale bar | Texture, fine detail | Mesh, splat, game asset |
| Room, home | The person with the iPhone, then the robots | ARKit and LiDAR, robot poses | Blank walls, what nobody looked at | Structured rooms, splat |
| Car, bikes | Walk-around | Priors or a measured distance | Shine, thin tubes | Mesh, presentation |
| Building, terrain | Drone | RTK, control points | Focal length traded against height | Terrain, buildings |
| Cave | Walking survey | Survey stations | Forks, narrow passages | Passage model |
| Wreck, reef | Diver, DSLR in a housing | A refractive camera model, targets | Colour, haze, refraction, 1,500 RAW photos | Model with corrected colour |
| A robot's map | The robot | Its own poses | What it did not see | A model placed in its map |

## 4. The control tower

**The laptop decides; the work goes where the hardware is.** Recce runs on the person's laptop,
in the field without a connection as well as at home. It does what a laptop does well and fast:
reading the photos, developing the RAW once for the whole set, sorting out the bad frames,
registering the cameras, and writing a debrief and a gap list the same evening, so the loop
closes in the field with no connection at all.

Then it hands off. Dense depth, which the mesh and its texture build on, needs CUDA or HIP and
hours of GPU, and does not run on a MacBook today; a Mac trains splats only with Brush, the
CUDA tools not at all (Step 0). Recce sends that work to:

- **the person's own machines**, over a private network, when they have them;
- **a GPU rented by the hour**, from the person's own account with a provider, started with their
  go, shown with its estimated cost before and its real cost after, and gone when the job ends.

This is what opens Recce to people without a workstation: an evening of a rented CUDA machine
costs a few dollars, not €20,000. The person pays for the hours they use and keeps everything
that comes out.

**Send what the next stage needs, not what the camera wrote.** 1,500 RAW photos at 50 MB are
75 GB: about 17 hours over a 10 Mbit/s hotel uplink. Developed images at the resolution dense
depth and splats work at are a fraction of that (an estimate of about 1.5 GB, to be measured).
The RAW stays on the laptop and its backup; the cut between laptop and remote is chosen from
measured sizes and times, per case. A preview goes first, the full set after, and transfers
resume where they stopped.

**The person sees and steers the whole pool.** Which machine runs which stage, how long it took,
what it cost and what moved across the network are on screen, as part of the reconstruction's
story, not in a log.

## 5. Who it is for

- **The photographer and diver** who shoots objects, places and wrecks with an iPhone, a DSLR, a
  GoPro or a drone, and wants a better model than "it looks okay", from RAW, with colour that
  holds.
- **Anyone at home with a phone and a laptop**, who can rent the heavy machine for an evening
  instead of owning it.
- **Robots**, which hand over capture sets with their poses and get a model at a stated scale in
  their own frame, with what they did not see.
- **Agents**, which drive Recce through MCP: start a reconstruction, read its quality, compare
  variants, say what to capture next.
- **Learners**, through learn mode inside the product: small labs beside the terms they explain.

## 6. How it looks and works

**Every stage is worth looking at.** The reconstruction is shown as a story: cameras finding
their place, each camera drawn as its photo hanging where it was taken, the matches that hold
the model together, where coverage is thin. The frame is a professional tool (an outliner, an
inspector, a timeline, a command palette); the 3D scene is illustrative and designed to be shown
to someone outside the field.

**Quality is on the surface, not in a log.** Light and shadow by how many photos saw a surface;
confidence solid or hatched; the reference beside the estimate where one exists; a debrief whose
every claim opens its evidence, and a claim without evidence flagged.

**The gap list is the brief for the next capture.** Each gap says where to stand, what to shoot,
why, and what it gains, on a card, on a site map, and as JSON for a robot.

**Recipes are compared, not trusted.** Two recipes on the same photos differ by one node; the page
shows what changed and what it cost, estimated before and measured after.

**Presentation stays honest.** A shared model opens on a path through its photos, with the splat
where it holds, the mesh where it does not, and an "About this model" card.

**Learn mode is inside the product** *(owner, 2026-11-27)*: small labs beside the terms they
explain (baseline, overlap, sharpness, rolling shutter, refraction), each with a tutor.

**AI is optional, and a coach when present.** Every view, check, debrief and gap list works from
geometry and rules alone. With the person's own AI connected (their provider or a local model),
it explains why a result is the way it is, orders a plan from the actions the engine can carry
out, says how the person will know it worked and what the facts cannot say. Every number it
writes is checked against the engine's own. The engine supplies positions and verdicts; the AI
explains them.

## 7. Principles

Each comes from Step 0's evidence ([close-out report](../wip/step0-closeout-2026-11-27.md)).

1. **Scale is stated, never guessed.** From priors, references or control points, or reported as
   arbitrary. Robot poses gave 0.021%, RTK priors +0.025%; a learned model's metric scale was off
   by up to 41%, so it never sets scale.
2. **Say what is not known.** Coverage predicts error; an unseen floor is marked unknown, not
   filled in.
3. **The engine supplies facts and positions; AI explains and is checked.** An agent inventing shot
   positions put 0 of 3 where a photographer can stand; with the engine's spots, 3 of 3.
4. **Complete without AI.** The version without AI is the product, not a placeholder.
5. **The laptop is the control tower; hardware is rented, not bought.** Offloading is built from
   the start, rented GPUs included.
6. **Move results, not raw data.** Each stage sends the smallest thing the next stage needs.
7. **Own the outcome.** Self-hosted and open source (MIT); photos, models and learned recipes stay
   with the person; rented machines work under the person's own account and leave nothing behind.
8. **Explain as it goes, beautifully.** The interface is how a person understands the machine.

## 8. Where it starts

The build starts with two tracks in parallel *(owner, 2026-11-27)*:

- **At home with the iPhone.** The iPhone capture app (RC-P11) and the owner photographing at
  home, from simpler to more complex: objects first, then a whole room. The room is the setting
  the robots map, so it leads into the robot cases.
- **The field night.** The laptop develops, registers and debriefs a large set; dense depth and a
  splat run on a rented GPU and the owner's machines; the bytes at each hand-off, the upload time,
  the wall-clock and the cost are measured, and the cut between laptop and remote is chosen from
  them. This is where the central bet (RC-P7: distributing the work beats the best single machine)
  is tested.

Underwater, drones and caves follow on the same loop and the same pool.

## 9. What it is not

- **Not a cloud service.** No accounts, no multi-tenancy, no photos on Recce's servers: there are
  none. A rented GPU is the person's own, for the hours they choose.
- **Not survey-grade or navigation-grade.** Models carry their scale and uncertainty and say what
  they are not.
- **Not capture control.** Robots and drones capture with their own software; Recce says what a
  good capture needs and judges it after.
- **Not dependent on AI**, and never shipping restricted model weights by default.

## 10. How the vision is checked

The vision holds when these are true, each measured on the owner's own captures:

- **The field night:** a day's large set, shot away from home, is developed and debriefed on the
  laptop the same evening, and reconstructed overnight on rented or own machines; the cost and
  the time are known before it starts and recorded after. Targets for time and cost are set from
  the field-night proof.
- **The home loop:** an object and a room captured with the iPhone come out at a stated scale,
  with a gap list whose next shots, once taken, close the gaps they name.
- **The robot loop:** a robot's capture set gives a model in the robot's frame at a stated scale,
  within the tolerances Step 0 used (0.5% scale, 1% placement).
- **The honesty check:** no model leaves Recce without its scale state, its frame and its
  coverage, and no claim in a debrief lacks its evidence.

## 11. Open

- **The field client.** In the field something runs on the laptop: the local engine serving the
  same web UI is the current design; whether it is packaged as a desktop application is decided
  later *(open, owner, 2026-11-27)*.
- **The field split.** What leaves the laptop, at which resolution; whether registration of
  1,500 photos fits on the laptop (38 photos already peaked at 28 GB); when the RAW or full
  resolution must travel (full-detail texture, underwater colour corrected by range).
- **Renting.** Which providers first, and how data reaches them: from the laptop over the uplink,
  or staged near them.
- **A portable dense path** for Macs, or dense always on a CUDA or HIP machine.
- **Where recipes and corrections live.** A private repository beside the owner's data; how a
  person shares them, if at all.
