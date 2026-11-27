# RC-01 — Vision

**Version:** 0.2 · Draft
**Date:** 2026-11-27
**Inputs:** [brief](RC-brief.md) · [Step 0 close-out report](../wip/step0-closeout-2026-11-27.md) ·
[architecture sketch](RC-architecture-sketch.md) · [use cases](RC-use-cases.md) ·
the owner's direction after Step 0 (2026-11-27)

---

## Leave the site knowing you have it

Every capture of the real world is a bet you only lose after you have left. The diver surfaces
from the last dive of the trip, the drone is packed, the house has been rearranged, and only then,
days later and on a machine big enough to process the photographs, does the model show the hole
under the bow, the wall nobody photographed, the scale nobody can trust. The tools on the market
sell the model. None of them sells what the person in the field needs while they can still act on
it: certainty that they got it.

**Recce is a reality-capture studio you carry.** It tells you, on the evening of the capture and
on the laptop you already travel with, what you have and what you are missing; it borrows the
power to finish the job overnight; and it hands back a model that says exactly how far it can be
trusted. You leave the site knowing you have it, or knowing precisely what to shoot tomorrow.

## The shift: from the darkroom to the studio and the farm

Photogrammetry still works like a darkroom. One expensive machine, one long process, the result at
the end, and a photogrammetrist who spends €20,000 on a workstation because 1,500 photographs of a
wreck will not assemble on a laptop in a day.

Film and visual effects solved this a generation ago. The artist works on a laptop, where they
see, judge and decide; the heavy rendering goes to a farm, owned or rented by the night, and
comes back finished. Nobody buys a render farm to make one film.

Recce brings that split to reality capture, for one person. The laptop is the studio: it reads
the RAW files, develops them into a consistent set, places every camera, and shows the model
taking shape with its gaps named, all offline, the same evening. What a laptop cannot do (dense
depth, the mesh, the splat, hours of CUDA) goes to whatever power is within reach tonight: a
machine at home, or a GPU rented by the hour from the person's own provider account, priced before
it starts and gone when it ends. A night on a rented GPU costs a few dollars. The ceiling on what
one person can capture stops being the machine they own.

## What it is like

**On a dive boat.** Four dives, 1,500 RAW photographs. In the cabin that evening, with no
connection, the laptop rebuilds the wreck camera by camera and says plainly that the port side of
the bow below two metres was never photographed; tomorrow's dive plan comes out as cards (where
to swim, at what angle, and why). On the marina's wifi it sends what the reconstruction needs, a
reduced working set, not the 75 GB of RAW that would take seventeen hours on a hotel uplink. A GPU
spins up for the night at a quoted price. In the morning the model is there, its colour corrected
for the water, its remaining gaps named, and the second dive closes them.

**At home with a phone.** A shoe on the table, twenty photographs with the iPhone, its position
and depth recorded with each one. The heavy part goes to the box in the cupboard; within the hour
later there is a model at its true size, ready for Blender or a game engine. Then the whole room,
which is the same room the robots map.

**A robot overnight.** The robot re-maps the flat while everyone sleeps and hands Recce its
photographs and poses. In the morning the model sits in the robot's own frame at its true scale,
with what changed since last month and the corner the robot never saw.

**An agent at the controls.** Someone's own agent starts the reconstruction, reads where it is
weak, compares two recipes and proposes the next capture, through the same interface a person
uses.

## What Recce is made of

**A model with a datasheet.** Every model leaves Recce the way a measuring instrument leaves the
factory: with its specification. Its true size, or "size unknown"; its frame; where it is solid,
where it is inferred, where nothing was seen. Step 0 showed why that matters: on a scanned room,
surfaces no photograph saw are 52.4 mm off the laser reference, surfaces seen by thirty-two or
more are 14.7 mm off. A model that hides that difference cannot be measured from, handed to a
robot or trusted on a dive. A model that shows it can.

**Capture as a conversation.** The person shoots, Recce answers, the person shoots again. The
answer is concrete: where to stand, what to point at, what it will fix. The finished model is
where the conversation stops, not the point of it. A person, a robot and an agent hold the same
conversation in their own language: cards, a JSON brief, MCP.

**Power on tap, decided by the person.** Compute is something switched on for a night and off in
the morning, never something bought in advance. Recce shows which machine did what, what moved
over the network and what it cost, and never rents anything without the person's go.

**Everything stays the person's.** The photographs stay on their machines unless they send them;
the models carry their history; the corrections Recce learns from their own camera, their own
housing and their own captures belong to them. Recce runs no cloud of its own; it is open source,
and the person's data has nowhere else to go.

**Places with a history.** A dive site visited each season, the rooms of a home, the flat a robot
maps every week: each becomes a place Recce remembers, not a folder of exports. The next visit
starts from the last visit's gaps.

**A teacher in the studio.** Recce explains as it goes: every stage is something to look at and
understand, from the cameras finding each other to the light falling off with depth underwater.
Small labs inside the product show the physics behind a bad capture (baseline, overlap, blur,
rolling shutter, refraction). A person's own AI, when they connect one, coaches on top: why this
capture came out the way it did and what to do about it, every number it uses checked against
Recce's own. Without it, Recce is complete. After a few outings the person reshoots less, because
they understand what the camera needs.

## Why now

Four things became true at once. Global camera solving made registration three to four times
faster. Gaussian splats made reconstructions something people want to look at. Phones
started recording their own position and depth with every photograph. And a CUDA GPU now rents
for about a third of a dollar an hour. Agents can drive tools, and local models can run beside
them. The established tools were built for one large machine and a finished photo set; none of
them is built for a person in the field, a pool of borrowed power and a conversation with the
capture.

## Where it starts

Recce starts where it can be tested at every step, and grows outward.

**At home, from simple to hard.** The iPhone capture app and an object on a table, then a whole
room. The room is the robots' world, so the home loop is also the first step of the robot loop.

**The field night, from the start.** In parallel, the split that makes the rest possible: a large
set developed and judged on the laptop, reduced, sent, reconstructed overnight on rented and home
machines, and measured at every hand-off (bytes, upload time, wall-clock, cost). Borrowed power is
the reason Recce exists, so it is built first, not added later.

Underwater, drones and caves come next on the same studio and the same farm; Step 0 already
measured what each of them needs.

## The bets

The vision stands or falls on four things, each to be proven on the owner's own captures:

1. **The night is enough.** A day's large set reconstructs overnight on borrowed machines, for a
   price one person accepts without thinking twice.
2. **What travels is small.** The laptop reduces a day's RAW to a working set a weak uplink
   carries in under an hour, without costing the model its quality.
3. **The laptop can judge alone.** Registration, the gaps and tomorrow's plan for a day's set run
   offline on the laptop the same evening.
4. **The datasheet is honest.** What every model says about itself holds against references.

## What Recce refuses to be

Not a cloud service: there is no Recce server to send photographs to. Not a survey instrument:
models state their limits instead of claiming a grade. Not the controller of robots or drones:
they capture with their own software, and Recce judges what they bring back. Not dependent on AI:
the studio is complete without it.

## Open

How the studio is delivered on the laptop (the local engine with its web interface, or a desktop
application around it); exactly what the laptop sends and at what resolution, and when the RAW
itself has to travel (full-detail texture, colour corrected by range underwater); whether a day's
registration fits in a laptop's memory; which providers to rent from first; and whether a Mac
ever runs dense depth itself.
