# RC-01 — Vision

**Version:** 0.8 · Draft
**Date:** 2026-11-27
**Inputs:** [brief](RC-brief.md) · [Step 0 close-out report](../wip/step0-closeout-2026-11-27.md) ·
[architecture sketch](RC-architecture-sketch.md) · [use cases](RC-use-cases.md) ·
the owner's direction after Step 0 (2026-11-27)

---

## Every capture is a mission

Someone, or something, goes into a place for a limited time and has to come back with a model
that other people will act on. The limit differs: the air in a diver's tank, the twenty minutes
in a drone's battery, the hour a robot can survive in a burned building, the afternoon a seller
has the keys to a flat, the weekend a car is clean. What does not differ is the shape of the
problem. The capture can only be judged after it is over, and by then the place is out of reach.
The gap under the hull, the field the drone missed, the room the robot never entered, the
staircase nobody photographed: all of them show up when it is too late to go back.

**Recce makes the capture answer back while the mission is still running.** After every leg of a
mission (a dive, a battery, a pass through a building, a floor of a house) it shows, within the
time before the next leg, what is already covered and what is missing, and where to go to close
it. When the gaps are closed, it finishes the model with whatever power is within reach that
night, and hands it over with a datasheet that says exactly how far it can be trusted. The point
is not a model at the end. It is leaving the place knowing the model will hold.

## Five missions

Recce is built for very different people doing the same thing.

**A diver documents a wreck for cultural heritage.** The site is protected, deep and visited
rarely; archaeologists will measure from the model for years. The mission is two or three dives a
day with surface intervals between them. What cannot be redone: the season, the weather window,
the boat.

**A drone surveys terrain before something is built.** Roads, houses, slopes and drainage are
documented for a new project. The mission is a series of flights, one battery at a time. What
cannot be redone cheaply: the crew on site, the permit, the light.

**A small robot enters a place people should not.** After a fire, or where a structure may come
down, a robot or remote vehicle goes inside so that the people outside can see how it looks
before anyone enters. The mission is one or a few passes on a weak radio link. What cannot be
redone: the time, and possibly the robot.

**An enthusiast wants a model of what they love.** A car, a mountain bike, a camera, something
built by hand. The mission is an afternoon with a phone or a camera. What cannot be redone: the
car being clean, the light being right, the patience.

**An estate agent sells a home.** The flat inside and the building outside, measured, presented
to buyers who will never visit in person. The mission is one visit with the keys. What cannot be
redone: the empty flat, the agent's afternoon.

## What every mission shares

Underneath, every mission has the same five steps.

1. **Plan.** What the model is for decides what it needs: an archaeologist needs scale and
   texture, a responder needs the layout and what was not seen, a buyer needs rooms that look
   right and measure right.
2. **Capture, in legs.** Photographs, with whatever comes with them: the phone's position and
   depth, the drone's GPS, the robot's own poses.
3. **Preview, after every leg.** In the time before the next leg, Recce adds the new
   photographs to the running model and shows a preview with its coverage: what is seen well,
   seen weakly, not seen at all, and where to stand to fix it.
4. **Full pass, when the gaps are closed.** The heavy reconstruction (dense geometry, the mesh, the
   texture, the gaussian splat) runs once, overnight or while the person does something else.
5. **Hand-over.** The model goes to whoever acts on it, with its datasheet: its true size or
   "size unknown", its frame, where it is solid, inferred or unseen, and how it was made.

The quick pass is what turns a capture into a conversation. The full pass is what makes the
result worth keeping. The datasheet is what makes it usable by someone who was not there. Step 0
showed why the datasheet matters: on a scanned room, surfaces no photograph saw were 52.4 mm off
the laser reference, surfaces seen by thirty-two or more were 14.7 mm off. A model that hides that
difference cannot be measured from, handed to a robot or used to send people into a building.

## Two speeds

**The preview: plan the next leg without waiting.** As soon as a leg's photographs are on the
laptop, Recce builds a preview from them: every camera in its place, the rough shape of the
place, coverage laid over it, and the gaps with where to stand to close them. It is the quick
pass: reduced photographs, each leg added to what came before instead of starting over, minutes
rather than hours, on the laptop in the field and offline, or on the operator's station outside
the burned building. The person walks around it, sees what the first dive or the first battery
missed, and plans the second leg on it. Nobody waits for the full render to know what to do
next. The preview does not need to be finished; it needs to be right about the gaps.

**The preview builds in front of the person's eyes.** There is no progress bar followed by a
finished model. As the photographs come in (copied off the card, sent from the phone, streamed by
the robot), each one is picked up and finds its place: the photo flies to where it was taken,
the points it shares with the others light up, and the shape of the place grows out of them. The
coverage fills in as it goes, and the gaps show up as the parts that stay dark. Everything stays
live and interactive while it builds: the person turns the model, opens a photo, follows the
threads to what it sees, and starts planning the next leg before the last photograph has landed.
Watching a reconstruction happen is also how a person learns what makes one work.

**The local client does the heavy lifting on the data.** Everything that touches the camera's
originals happens on the laptop: reading the RAW files, developing them into one consistent set
(white balance, exposure, colour), dropping the blurred and the duplicates, placing every
camera. That is what the Studio is for, beyond showing the preview: by the time anything leaves
the laptop, it is only what the model needs, the working images at the resolution the full pass
uses and the camera solution. A transfer that would take a hotel uplink most of a day takes
minutes to an hour. The originals never leave the person's disk.

**A darkroom in the Studio.** Developing the photographs is its own craft, and Recce treats it as
one: the RAW decoded, the lens corrected, white balance, exposure, tone and colour made to agree
across the whole set, the way a photographer would in Lightroom, but for a reconstruction rather
than a print. The person can open the develop panel, tune it and save what they like as a
preset. Recce ships its own presets too, and those are not guesses: they come out of evaluation,
the same develop settings tried on many scenes with known answers and kept where the models came
out better (more photographs placed, colour that holds across seams, texture that stays sharp). A
preset learned on a reef is different from one learned on a white-walled flat, and Recce says
which it chose and why.

**A recipe is how Recce remembers what works.** A recipe is a named, versioned set of choices
for a kind of mission: the develop preset, the lens and camera model, how photographs are
matched and placed, how the full pass builds the surface and the splat, and the evidence that
earned it, its scores on the scenes it was tested on. Recce proposes a recipe from what it sees
(the camera, the photographs, the priors, the kind of mission) and says why; the person can keep
it, change it or bring their own. The recipes and corrections learned from a person's own
cameras and captures are theirs.

**A workflow is how the person works.** Not every mission needs every step. A GoPro's JPEGs can
go straight in as they are; a D850's RAW files go through the darkroom first; a careful person
stops to look at the develop panel before anything is matched, and someone in a hurry sends
everything to the full pass the moment the gaps are closed. A workflow is the chain of steps a
project runs, in the person's order: which steps are in, which are skipped, where Recce pauses
for a look or an approval, where the full pass goes. The person builds it on a canvas, saves it,
and keeps different workflows for different kinds of project; Recce proposes one for a new
mission, with a recipe filling in each step's settings. A workflow can change in the middle of a
mission: add the darkroom after the first leg shows the colour is off, and only the steps after
the change run again. The workflow says what happens; the recipe says how well each step is
tuned.

**A project holds one place.** A wreck, a building site, a flat, a car: each is a project, the
boundary of one scene and everything done to it. A project holds two things. Its assets: the
photographs of every leg, kept as ordinary files in the project's own folder on the person's
disk, where any other tool can still open them. And its work: the workflow, the develop settings,
the recipes, every run, every model and datasheet, and the history of the missions. Recce never
changes an original; everything it does is stored as settings and results beside them, the way
Lightroom keeps a catalog beside the photographs. Switching from one project to another is one
click. Moving a project to another computer is copying its folder, or exporting it with or
without the originals; on the other side Recce finds the photographs again by their content, so
a renamed disk or a moved folder does not break anything.

**Bringing photographs in.** The person points Recce at a folder, or plugs in the camera, the
drone's card or the phone, and Recce imports: the photographs go into the project's folder, one
subfolder per leg, named by date and device, duplicates from a card imported twice left out.
Robots and the capture app deliver the same way, over the network. Inside the project, a small
library shows every photograph by leg, camera and time; any photograph opens in a viewer with its
metadata (camera, lens, exposure, position, depth, where it sits in the model) and with what the
darkroom has done to it, before and after.

**The darkroom works on groups with the same light.** A day's photographs do not share one light:
the morning dive is blue and bright, the afternoon dive greener and darker; the drone's first
battery flew in sun, the last in cloud. Recce groups the photographs of a project by leg, camera
and measured light, and proposes those groups as the units of the darkroom. The person picks one
photograph of a group, changes it, and sees the change live on that photograph and on the whole
group as a contact sheet; applying it applies to the group, never touching the originals. Then
Recce makes the groups agree with each other, because a reconstruction blends photographs from
every leg into one surface, and two lights that disagree show up as seams on the model. The
preview shows that too: a group out of line with the rest is visible on the model as a patch of
the wrong colour, and fixing it in the darkroom fixes it there.

**The full pass runs where the power is, and every case has some.** Dense geometry, the mesh,
the texture and the splat need a CUDA or HIP GPU and hours of it. Recce finds that power wherever
the person has it:

- **in the laptop**, when it has the GPU: the full pass runs there, nothing is sent;
- **next to the laptop**: an external GPU or a GPU machine carried along, on the desk or in the
  van;
- **at home**: the person's own machine with a GPU, reached over their private network;
- **rented by the hour**, when they have none of these: a GPU from the person's own provider
  account, priced before it starts, approved by the person, gone when it ends. A night costs a
  few dollars.

Recce shows the time and the cost on each option before the person chooses. Nobody needs to own
the big machine, and nobody who owns one is made to rent.

## Surfaces

The same product appears in a few places, built once.

| Surface | Who uses it | Where | What runs there |
|---|---|---|---|
| **Recce Studio** (desktop, macOS and Windows, Linux too) | The person running the mission | Their laptop, in the field or at home | The interface, the local engine, the quick pass; the full pass when the laptop has the GPU for it; sends the rest out |
| **Recce on the web** | The same person away from the laptop; anyone a model is shared with | A browser, reaching the person's own home machine, or a shared link | The same interface as the Studio; the viewer and the presentation for shared models |
| **Capture app** (iPhone first) | The person capturing with a phone | On site | Photographs with position and depth; live coverage while shooting; sends to the Studio |
| **Station** for robots and vehicles | A robot, a vehicle, its operator | Beside the operator, or on the vehicle | Receives capture sets, runs the quick pass, returns the brief for the next leg |
| **Workers** | Nobody directly | Home machines, rented GPUs | The full pass |
| **Agents** | A person's own agent | Anywhere | Everything above, through MCP |

**The Studio is the website, packaged.** One web application (the interface, the 3D scenes,
three.js and splats) is the Studio's interface and the browser's. On the desktop it is wrapped
together with the local engine as a single installable application for macOS and Windows.
The wrapper is Electron *(owner, 2026-11-27)*: it ships its own Chromium, so the 3D scenes
render the same on every system, and its size is small next to the engine it carries. What
the browser shows and what the Studio shows is the same thing.

**How a robot's mission runs with Recce.** The robot's own software plans and drives;
Recce sees and advises. With robotics-lab, whose Mission Control plans and executes the owner's
robots, the shape proposed on both sides (2026-11-27, not yet decided by the operator) is:

- **A leg is a group of capture steps** in the robot's mission plan: a sequence of
  `capture_view` goals, each a place to stand and a burst to shoot.
- **During the leg, a reduced stream goes out.** The robot's recording keeps every frame and
  sends a reduced copy with poses over its link to a Recce station. The robot does the cheap
  selection (a rate, or a new frame when the pose has changed enough), within the link's budget;
  Recce does the selection that needs the model (what adds coverage). The full set follows when
  the robot is back or the link is good.
- **The station sits beside Mission Control** on the operator's machine; later, as an option,
  on the robot's own computer for when the link drops.
- **After the leg, the gaps come back as data** (`gaps.json`). The planner treats "a capture
  with open gaps" as a reason to replan, at the leg boundary; it turns the gaps into the next
  leg's capture steps, the operator reviews, and Mission Control executes. In manual mode the
  operator sees the gaps and adds the leg by hand. Recce never steers the robot.
- **In a hazard, unseen is not the same as unsafe.** For the robot in a burned building, the gaps
  have to say whether a part is merely unseen or lies behind something the model marks as
  dangerous, so the planner does not send the robot there, and each leg has a time budget the
  preview must meet. This is a safety design the operator decides with robotics-lab, not only an
  interface.

A vehicle with its own computer can carry the station on board and send only the coverage and
the gaps.

## Each mission, specialised

| | Heritage diver | Survey drone | Robot in a hazard | Enthusiast | Estate agent |
|---|---|---|---|---|---|
| **A leg** | A dive | A battery | A pass inside | A walk round the subject | A room, a façade |
| **Time for the quick pass** | The surface interval | The battery swap | Live, while the robot moves | Before packing up | Before handing back the keys |
| **How photos reach Recce** | Card to laptop on the boat | Card to laptop at the site | Selected frames over radio; the full set on return | Phone or card to laptop | Capture app, drone card |
| **What gives the scale** | Targets on the site, a refractive camera model | GPS with RTK, control points | The robot's own poses and depth | The phone's position and depth, or a scale bar | The phone's position and depth |
| **The hard part** | Refraction, colour lost in water | Height, distortion, large areas | A weak link, smoke, darkness | Shine, thin parts | Plain walls, many rooms |
| **Delivered** | A measured, colour-corrected model with its datasheet, for the archive | Georeferenced terrain and buildings, checked against control points | The layout inside and what was not seen, within the hour | A model for Blender, a game engine or a shared link | A walk-through for buyers, rooms with measured sizes |
| **Who acts on it** | Archaeologists, conservators | Planners, engineers | Responders, structural engineers | The owner, their friends | Buyers |

## What success looks like

**For every mission:**

- No one goes back to a site because of a gap Recce could have shown before they left.
- The quick pass after each leg arrives before the next leg starts.
- The full pass runs on power the person did not have to buy, at a cost they saw before they
  approved it.
- Every model that leaves Recce carries its datasheet, and what the datasheet says holds against
  a reference.
- The photographs and the models never leave the person's control unless they send them.

**For each mission:**

- **The diver** closes the morning's gaps in the afternoon dive and leaves the site with a model
  the archaeologists measure from without asking how it was made.
- **The drone crew** packs up after the last battery knowing the area is covered, and the next
  morning's terrain meets the control points.
- **The responders** see the inside of the building within the hour, with the unseen parts marked
  as unseen, before anyone walks in.
- **The enthusiast** gets a model they are proud to show, from a phone and an evening of rented
  power, and reshoots less each time because Recce explained what went wrong.
- **The agent** leaves the flat with every room covered and sends buyers a walk-through the same
  day, with sizes that hold.

## What makes Recce

**Answers while the mission runs.** The preview grows live from the first photograph of every
leg; no tool offers that today, the others answer after the mission is over.

**Power without owning it.** The heavy work goes where the hardware is, at home or rented for a
night, decided and paid for by the person.

**Models that state their limits.** The datasheet travels with every model: true size or not,
solid or inferred or unseen.

**One mission shape for people, robots and agents.** The same brief goes to a person as cards on
a screen, to a robot as data, to an agent through MCP.

**Places with a history.** A wreck visited each season, a site before and after construction, a
building before and after the fire, a home sold twice: each becomes a place Recce remembers. The
next mission starts from the last one's gaps.

**It explains and it teaches.** Every stage is something to look at and understand. Small labs
inside the product show the physics behind a weak capture. A person's own AI, when they connect
one, coaches on top: why the capture came out the way it did and what to do about it, its numbers
checked against Recce's. Without AI, Recce is complete.

**It is the person's.** Open source, running on their machines, with no Recce cloud to send
anything to.

## Why now

Global camera solving made registration three to four times faster, which is what makes a quick
pass between legs thinkable. Gaussian splats made reconstructions something people want to look
at. Phones record their own position and depth with every photograph, and robots and drones
carry the same. A CUDA GPU rents for about a third of a dollar an hour. Agents can drive tools,
and local models run beside them. The established tools were built for one large machine and a
finished set of photographs; none of them is built for a mission that is still running.

## Where it starts

**At home, with the phone and the Studio.** The capture app and an object on a table, then a whole
room. It is the enthusiast's and the estate agent's mission at its smallest, and the room is the
robots' world.

**The quick pass and the full pass, split, from the start.** In parallel: the quick pass on the
laptop and the full pass on a rented GPU and home machines, measured at every hand-off (what is
sent, how long it takes, what it costs, how long each pass runs). Borrowed power and the quick pass
are what every mission depends on, so they are built first.

The drone, the dive and the robot in a hazard follow on the same shape; Step 0 already measured
what each of them needs (RTK and control points, the refractive camera model and colour in water,
a robot's capture set and frame).

## The bets

1. **The quick pass fits between legs.** Coverage and the next shots for a leg's photographs
   arrive within a surface interval, a battery swap, or live for a robot.
2. **The quick pass is right about the gaps.** What it calls covered is covered in the full pass.
3. **What travels is small enough.** The working set crosses a field connection in minutes to an
   hour without costing the model its quality.
4. **A night of borrowed power is enough,** at a price one person accepts.
5. **The datasheet is honest** against references, on real missions.

## What Recce refuses to be

Not a cloud service: there is no Recce server to send photographs to. Not a survey instrument:
models state their limits instead of claiming a grade. Not the controller of robots or drones:
they capture with their own software, and Recce tells them what is missing. Not dependent on AI.

## Open

- **The preview.** At which reduced resolution, how it adds a leg without starting over, how
  fast it runs on a laptop without a GPU, and how close it looks to the final model.
- **The robot link.** The transport for the reduced stream over a weak link and its back-pressure;
  the hazard rules for unseen against unsafe (with robotics-lab and the operator).
- **What the full pass needs sent,** and when the originals have to travel (full-detail texture,
  colour corrected by range underwater).
- **Renting.** Which providers first, and how data reaches them.
- **The develop module.** Which libraries for lens correction and colour, and how presets are
  evaluated across scenes; how light groups are found and matched across legs; its own prototypes.
- **The project format.** What the project file holds, how an export carries the originals or
  only the working set, and how a project on two computers stays in step.
- **A Mac running the full pass itself,** or always sending it out.
