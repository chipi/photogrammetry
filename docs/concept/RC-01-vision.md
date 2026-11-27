# RC-01 — Vision

**Version:** 0.3 · Draft
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
3. **Quick pass, after every leg.** In the time before the next leg, Recce adds the new
   photographs to the running model and shows coverage: what is seen well, seen weakly, not seen
   at all, and where to stand to fix it.
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

**The quick pass runs where the person is.** It works on reduced photographs, adds each leg to
what came before instead of starting over, and aims for minutes, not hours: short enough to fit a
surface interval, a battery swap or the walk to the next room. It runs on the laptop in the
field, offline, and on the operator's station outside the burned building. What it produces is
coverage and the next shots, plus a rough model to look at; it does not need to be beautiful, it
needs to be right about the gaps.

**The full pass runs where the power is.** Dense geometry and the rest need a CUDA or HIP GPU and
hours of it. A laptop with such a GPU runs the full pass itself. A Mac does not today, and many
laptops have no GPU worth the name, so the full pass goes to a machine at home or to a GPU rented
by the hour from the person's own provider account: priced before it starts, approved by the
person, gone when it ends. A night on a rented GPU costs a few dollars; nobody needs to own the
machine.

**What travels is the working set, not the camera's files.** The quick pass has already
developed the RAW files into a consistent set and placed every camera; the full pass needs those
working images at the resolution it uses and the camera solution, not the originals. That turns
a transfer that would take a hotel uplink most of a day into one that takes minutes to an hour.
The originals stay on the person's disk.

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
Electron is the leading choice for the wrapper: it ships its own Chromium, so the 3D scenes
render the same on every system, and its size is small next to the engine it carries. Tauri,
which uses each system's own web view, is the alternative to measure against it. The decision
belongs in an RFC.

**How a robot's photographs reach Recce.** A robot does not have a card to pull. During a mission
it sends what its link allows, a stream of selected frames with their poses, to the station,
where the quick pass shows the operator what has been seen and returns the next brief as data
the robot's own software can follow. When it comes back, or when the link is good, it delivers
the full capture set, and the full pass runs. A vehicle with its own computer can carry the
station on board and send only the coverage and the brief. Recce never steers the robot; it says
what is missing.

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

**Answers while the mission runs.** The quick pass, after every leg, is what no tool offers
today; the others answer after the mission is over.

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

- **The wrapper.** Electron or Tauri, decided in an RFC on measured rendering and size.
- **The quick pass.** At which reduced resolution, how it adds a leg without starting over, and
  how fast it runs on a laptop without a GPU.
- **The robot link.** How frames are selected for a weak link, and the station's interface.
- **What the full pass needs sent,** and when the originals have to travel (full-detail texture,
  colour corrected by range underwater).
- **Renting.** Which providers first, and how data reaches them.
- **A Mac running the full pass itself,** or always sending it out.
