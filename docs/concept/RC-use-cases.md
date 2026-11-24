# First use cases — a thought experiment

*Working document. The owner's first real scans, walked through the
[architecture sketch](RC-architecture-sketch.md) one by one, as a conceptual proof: does the shape
hold, what breaks, which options and recipes each case needs. Input to the prototypes, to RC-02 and
to RC-04.*

**Version:** 0.1 · Draft · 2026-11-23

Device facts marked *(to verify)* come from general knowledge and were not checked against a
source this session; the prototypes check them on the real devices.

---

## 1. The cases

The owner works through the same subjects with each device, in this order:

| # | Subject | iPhone 15 Pro | GoPro | Nikon D850 | Sony A1 |
|---|---|---|---|---|---|
| A | **Object** — a Lego toy, a camera, a book, a pair of shoes | UC-A1 | UC-A2 | UC-A3 | UC-A4 |
| B | **Room** — the owner's room, from inside | UC-B1 | UC-B2 | UC-B3 | UC-B4 |
| C | **Car** — in a car park, outdoors | UC-C1 (any device) | | | |
| D | **Motorbikes** (two) | UC-D1 (any device) | | | |
| E | **Mountain bike** | UC-E1 (any device) | | | |

Cases A and B are the systematic series: one subject, four devices, so every device is compared
on the same ground. C, D and E come along the way, with whichever device is at hand, and push the
engine to its limits.

## 2. The same journey, step by step

Every case follows the same eight steps through the architecture. UC-A1 walks them in full; the
others describe only what differs.

1. **Capture** — what the device records, and what the owner should do.
2. **Into the system** — which face, which files, what the ingest stage reads.
3. **Recipe** — what the engine proposes from the evidence, and why.
4. **Registration** — how the photos line up, and what is likely to resist.
5. **Scale and frame** — where metric scale comes from, or why it is arbitrary.
6. **Products** — dense cloud, mesh, texture, splat.
7. **Export** — what leaves, in which format, for which tool.
8. **Quality and advice** — what the engine reports, and what it tells the owner to reshoot.

---

## 3. Case A — an object

### UC-A1 · Object with the iPhone 15 Pro (the full walk-through)

**The four objects are four different problems:**

| Object | What it tests | Expected difficulty |
|---|---|---|
| Pair of shoes | Matte, textured, closed shape | Easy — the clean baseline |
| Book | Near-planar faces, sharp edges, thin pages; a flat cover is close to the degenerate planar case for two-view geometry | Medium — needs views around the edges, not only of the covers |
| Lego toy | Small, glossy plastic, fine detail, repeated studs (repetitive texture fools matching) | Medium to hard |
| Camera | Black body (little texture), glass lens (transparent and reflective), metal | Hard — expect holes at the lens; the splat will look better than the mesh |

**1. Capture.** What the iPhone offers, and what of it reaches the engine:

| Source | What it gives | How the engine gets it |
|---|---|---|
| Main camera, 48 MP sensor; the Camera app saves 24 MP HEIF by default, 48 MP only in HEIF Max, JPEG Max or RAW Max at 1× (verified 2026-11-24) | HEIC or JPEG, or ProRAW DNG | Web upload, or AirDrop to the laptop then upload |
| EXIF | Focal length, lens id, exposure, GPS | Read at ingest |
| Lens switching | The Camera app switches to the ultra-wide for close subjects (macro); it can be turned off with the Auto Macro button or Settings > Camera > Macro Control (verified 2026-11-24) | EXIF lens id per image — the engine groups images by lens and calibrates each separately |
| LiDAR depth | Low-resolution metric depth | **Not in plain Camera photos.** Only through a capture app (Record3D, Polycam, Scaniverse) or our own capture app (RC-P11) |
| ARKit camera poses | Metric camera positions, gravity | Same: only through a capture app's export |
| Portrait-mode depth | A depth map embedded in the HEIC *(to verify)* | Possible at ingest, but portrait mode is not a capture mode for photogrammetry |

The owner shoots 60–150 photos in two or three rings around the object at different heights, with
overlap between neighbours, exposure and focus locked (long-press AE/AF lock), on a plain matte
background, in diffuse light. **The finding:** the plain Camera app gives photos and EXIF only. The
LiDAR and ARKit data the owner wants to reuse needs a capture app's export — which is exactly what
the later iPhone app exists for. Until then there are two ways in: *photos-only* (Camera app) and
*pose-and-depth* (a capture app's export).

**2. Into the system.** The owner opens the web UI on the phone and uploads. Risk: Safari may
convert HEIC on upload: it transcodes a file whose type is not in the page's `accept` list (verified 2026-11-24), so the upload page lists HEIC and DNG explicitly; what the photo picker hands over is tested on the phone — acceptable for a first test, but the ingest stage
records which happened. ProRAW DNG files come through the Files picker. A capture-app export comes
in as a folder: images, intrinsics, poses, depth.

**3. Recipe.** Evidence: one device, 60–150 images, not sequential, no GPS worth trusting
indoors, the owner tagged "object". The engine proposes `object-walkaround`: retrieval-plus-
exhaustive pair selection (small set, so exhaustive is affordable), incremental COLMAP or GLOMAP
(RC-P1 decides the default), automatic background mask. With a capture-app export, it proposes
`object-walkaround+priors`: ARKit poses as priors, LiDAR depth as a dense-stage prior.

**4. Registration.** Shoes register cleanly. The book's covers alone would be near-degenerate;
views of the spine and edges carry it. Lego studs produce repetitive matches; geometric
verification rejects most of the false ones, and masks keep the background from dominating. The
camera's glass returns false matches that move with the viewpoint; bundle adjustment marks those
points as high-error, and they are filtered. **What resists:** the iPhone's per-photo processing
(Smart HDR, Deep Fusion) tone-maps each photo differently, and ProRAW is captured together with that processing, so it is not radiometrically linear (verified 2026-11-24). Matching
tolerates it; texturing does not — hence ProRAW and the develop stage.

**5. Scale and frame.** Photos-only: **arbitrary scale**, stated as such, unless the owner puts a
marker (an AprilTag sheet) or a ruler in the scene, or enters one measured distance in the UI.
With ARKit priors: **metric from priors**, in ARKit's gravity-aligned frame. The model's "up" is
known from gravity (ARKit) or from the ground plane.

**6. Products.** Dense depth on the GB10 (CUDA) or the X3 (a HIP build, unproven); Poisson mesh;
texture with exposure-matched images; a splat from the same poses (on the GB10 with gsplat, or with
Brush on the laptop alone).

**7. Export.** GLB with textures (Blender, Godot, Unity, Unreal), USDZ (iPhone Quick Look), OBJ
and PLY; the splat as GLB with `KHR_gaussian_splatting` and as PLY. Every export states units and
up axis.

**8. Quality and advice.** Registered 142/150, with the reasons for the eight rejects (blur, too
little overlap). Reprojection error per image. Coverage regions: "the underside of the shoe is not
covered — turn it over and shoot one more ring, keeping the background"; "the lens of the camera is
missing in the mesh; it is present in the splat."

**Verdict.** Works for shoes and the book; works with masks and care for Lego; the camera works as
a splat and partially as a mesh. **Options this case needs:** lens grouping by EXIF; automatic
background masks; a two-sided capture mode (object turned over between rings, merged as one
model); a scale-entry tool; ProRAW through the develop stage.

### UC-A2 · Object with the GoPro

**Differs from A1:**
- **Lens.** GoPro photos in Wide/HyperView are strongly distorted; HERO13 photos offer Wide (16–34 mm) and Linear (19–39 mm) only, and RAW (.gpr) requires Wide (verified 2026-11-24); Linear
  mode is dewarped in-camera to a near-pinhole image at some cost in field of view. The recipe
  differs: a fisheye camera model for Wide, pinhole for Linear. The engine reads the lens mode from
  metadata where it can (the GPMF spec defines field-of-view and projection tags; whether HERO13 photos write them is tested on a real file).
- **Close focus and resolution.** The GoPro has fixed focus (minimum distance unpublished; measured on the camera); the Macro Lens Mod focuses at 11–75 cm and, like every lens mod, is calibrated as its own camera; a
  small Lego model fills little of the wide frame, so effective resolution on the object is low.
  Shoes and the book are better targets than Lego.
- **Capture.** Time-lapse photo (a frame every 0.5 s) while walking around is the natural mode;
  video works but brings rolling shutter and motion blur. For video the frame-select stage picks
  sharp, well-spaced frames.
- **Metadata.** GPMF carries gyro, accelerometer and gravity; gravity gives "up", and gyro could
  seed rotations *(no evidence found yet of GPMF used as an SfM prior — an opening, not a given)*.
- **Into the system.** SD card or USB to the laptop, then upload; Open GoPro over Wi-Fi later.

**Verdict.** Works for medium objects in Linear mode; Wide mode needs the fisheye model to be good;
small objects are a poor fit. **Options:** fisheye camera model; frame selection for video and
time-lapse; GPMF gravity as "up".

### UC-A3 / UC-A4 · Object with the Nikon D850 and the Sony A1

**Differs from A1:**
- **Files.** NEF and ARW RAW, 45.7 MP and 50.1 MP, tens of MB each — 150 photos is several GB.
  LibRaw lists both cameras; whether the A1's compressed ARW variants decode correctly in rawpy is
  unverified (RC-P5).
- **Develop.** This is the case the develop stage exists for: one white balance and one exposure
  across the set, a neutral tone curve, no per-photo look. Without it the texture shows seams.
- **Resolution pyramid.** Matching at full 45–50 MP is slow and unnecessary; the engine extracts
  features at a reduced size and keeps full resolution for dense depth and texture.
- **Lens.** A prime or a zoom fixed at one focal length; aperture f/5.6–f/8; a tripod or a fast
  shutter. The lens model from EXIF initialises calibration; a zoom moved mid-set splits the set
  into calibration groups, which the engine detects from EXIF focal length.
- **Turntable option.** With a DSLR on a tripod and the object on a turntable, the background is
  static while the object turns. The background must be masked out or be featureless, or it pulls
  the solution towards "the camera never moved". This is the `object-turntable` recipe.
- **Scale.** A printed AprilTag board beside the object gives metric scale and up.

**Verdict.** The best object quality of the four devices; the heaviest data; the strongest test of
the develop stage and of distribution (feature extraction over hundreds of large images fans out
well). **Options:** RAW develop; resolution pyramid; calibration groups by focal length; turntable
recipe with static-background exclusion; marker-based scale.

---

## 4. Case B — a room

### UC-B1 · Room with the iPhone 15 Pro

**What makes a room different from an object:** the camera is inside the subject looking out.
Walls are often plain (little texture); windows and mirrors reflect; lighting is mixed (daylight
and lamps); furniture occludes. And the classic mistake: standing in the middle and turning on the
spot gives no parallax — pure rotation is the degenerate case, and nothing triangulates.

- **Capture.** Walk along the walls, facing across the room, in overlapping passes at two heights;
  corners and doorways shot deliberately. Two modes:
  - *Photos-only* — the Camera app. Plain walls will resist registration.
  - *Pose-and-depth* — a capture app's export with ARKit poses and LiDAR depth. **This is where
    the iPhone's extra sensors matter most:** ARKit poses hold the solution together across plain
    walls, LiDAR depth gives geometry where photos have no texture, and the scale is metric.
- **Recipe.** `interior`: sequential and retrieval pair selection, ARKit priors if present, the
  learned first pass (MapAnything) when texture is low, TSDF fusion from LiDAR depth alongside
  photo-based dense depth.
- **Registration.** Photos-only: expect the room to break into pieces at plain walls; the engine
  reports the separate components and where the links are missing ("the wall between the window and
  the door has no overlap"). With priors: one model.
- **Scale and frame.** Metric from ARKit, gravity-aligned; or one tape-measured wall length entered
  in the UI.
- **Products.** A metric mesh for measuring and for robotics-lab comparisons; a splat for viewing,
  where a room looks far better than as a mesh.
- **Privacy.** A room scan holds screens, documents and photos on walls; the project is marked
  "never leaves home" by default.

**Verdict.** Photos-only is the honest stress test and may fail at plain walls; pose-and-depth is
expected to work and is the case for the capture-app route. **Options:** pose priors; depth fusion;
learned first pass for low texture; component reporting; the default "stays home" for interiors.

### UC-B2 · Room with the GoPro

- The wide field of view helps a room: more overlap per frame, more texture in each image, fewer
  photos needed. The fisheye model is required.
- Indoors the GoPro's small sensor raises noise and lengthens exposure; video blurs in low light.
  Time-lapse photo in good light, or video with plenty of light.
- No depth, no poses; GPMF gravity gives "up". Scale arbitrary without a measured distance.

**Verdict.** Likely registers better than iPhone photos-only thanks to the field of view; detail is
lower. **Options:** fisheye model; frame selection; low-light warnings at ingest (ISO and shutter
read from EXIF).

### UC-B3 / UC-B4 · Room with the Nikon D850 and the Sony A1

- A wide lens (or the widest the owner has) and a tripod for low light; mixed light makes white
  balance across the set matter even more — the develop stage again.
- Highest detail and the largest data; the case where distribution and rented workers start to
  matter.
- No poses, no depth; scale from a tape measure or a marker on the wall.

**Verdict.** Works where there is texture; plain walls resist as with the iPhone photos-only.
**Options:** as UC-B1 photos-only, plus RAW develop and tripod-aware capture advice.

---

## 5. Case C — a car in a car park

- **Size and height.** About 4.5 m long and 1.5 m high; the roof needs views from above — a step
  ladder, a pole, or the DJI Mini 4 Pro (a natural moment to bring the drone in).
- **Surfaces.** Glossy paint and glass reflect the surroundings, and reflections move with the
  viewpoint: false matches, holes in the mesh. Overcast light is far better than sun; a polarising
  filter on the DSLR cuts reflections.
- **Outdoors.** Other cars, people, moving shadows: masks and a moving-object filter. Sun moves
  over a long capture; exposure locked anyway.
- **Recipe.** `object-walkaround` at large scale, or `aerial` for the roof pass when the drone is
  used, merged into one model through shared images.
- **Scale.** The wheelbase from the car's specification, or a tape-measured distance; GPS (phone or
  drone) gives rough scale and north.
- **Products.** The splat is the showpiece; the mesh is good on matte parts (tyres, trim) and holed
  on glass. Paint reconstructs if overcast.

**Verdict.** Works as a splat; works partially as a mesh; the drone pass is what makes the roof
whole. **Options:** reflective-surface handling (masks, robust filtering); moving-object masks;
multi-device merge (ground photos plus drone); scale from a known dimension.

## 6. Case D — the motorbikes

- Chrome, polished metal and black engine parts; thin cables and spokes; deep occlusions between
  engine, frame and wheels.
- Capture in rings at several heights plus close passes into the engine bay; overcast light or a
  shaded garage.
- The mesh struggles with thin and shiny parts; the splat handles them far better.
- Two motorbikes: the same recipe twice — a first use of the benchmark idea across subjects.

**Verdict.** Splat good, mesh partial; a strong showcase for "same poses, two products".
**Options:** splat as the primary product for this subject type; mesh cleanup; close-pass capture
advice.

## 7. Case E — the mountain bike

- The hardest object: thin tubes, spokes, cables, and very little surface per view — most of each
  photo is background seen *through* the bike.
- Masks are mandatory; a plain background (a wall, a sheet) makes them reliable. On a work stand,
  the bike can be turned like a turntable — the `object-turntable` recipe with static background
  exclusion.
- The mesh of the spokes is expected to fail; the frame and wheels' rims work. The splat renders
  the spokes acceptably *(expected, not verified)*.

**Verdict.** The stress test RC-P1's order puts last for a reason. **Options:** strong masking;
turntable recipe; thin-structure handling is a later research item (mesh from splats).

---

## 8. What the thought experiment shows

### What holds

- The **eight-step journey fits every case** without a new component: ingest, recipe, registration,
  scale, products, export, quality and advice cover them all.
- **Recipes are necessary, not decoration.** Within these first cases alone the engine needs at
  least `object-walkaround`, `object-turntable`, `interior` and `aerial`, each differing in pair
  selection, priors, masking and camera model.
- **Scale state earns its place.** Half the cases end with arbitrary scale unless the owner adds a
  marker or a measurement; the engine must say so every time.
- **Same poses, two products** pays off on exactly the owner's subjects: glass, chrome, spokes.

### What breaks, or needs care

| Problem | Cases | Answer in the design |
|---|---|---|
| iPhone LiDAR and ARKit are not in Camera-app photos | A1, B1 | Two ingest routes: photos-only and pose-and-depth (capture-app export); the iPhone app later |
| Per-photo processing in the iPhone (Smart HDR) | A1, B1 | ProRAW plus the develop stage; detect inconsistent tone across the set at ingest |
| Automatic lens switching (macro) | A1 | Group by lens id from EXIF; calibrate per group; warn |
| Safari HEIC to JPEG on upload | A1, B1 | Record what arrived; offer the Files route for originals |
| Fisheye distortion | A2, B2 | Fisheye camera model in the recipe |
| Rolling shutter and blur in video | A2, B2 | Frame selection; prefer time-lapse photos |
| Repetitive texture (Lego studs) | A1–A4 | Geometric verification; masks; retrieval pairs |
| Reflective and transparent surfaces | A1 (camera), C, D | Masks, robust filtering, splat as the faithful product |
| Plain walls, pure rotation | B1–B4 | Pose priors, LiDAR depth, the learned first pass; capture advice ("move, don't turn") |
| Static background on a turntable | A3, A4, E | `object-turntable` recipe with background exclusion |
| Very large RAW sets | A3, A4, B3, B4 | Resolution pyramid; distribution; resumable upload |
| Thin structures | D, E | Splat first; mesh-from-splat later |
| Roof and top views | C | The drone; multi-device merge |
| Moving people and cars outdoors | C | Moving-object masks |

### Indoors against outdoors

| Concern | Indoors | Outdoors |
|---|---|---|
| Light | Low and mixed: noise, long exposures, white-balance mismatch | Strong and moving: harsh shadows, specular highlights; overcast is best |
| Background | Static, often plain | Busy and moving: people, cars, trees in wind |
| Scale sources | ARKit, LiDAR, tape, markers | GPS (rough), known dimensions, markers, drone |
| Typical recipe | `interior`, `object-turntable` | `object-walkaround`, `aerial` |
| Privacy | High (homes) — stays home by default | Lower; rented workers allowed by default |

### Engine capabilities this adds to the requirements

1. Two ingest routes for the iPhone: photos-only and pose-and-depth (capture-app exports first).
2. Calibration groups by lens and focal length from EXIF.
3. A fisheye camera model alongside the pinhole and Brown models.
4. Frame selection for video and time-lapse.
5. A resolution pyramid: features at reduced size, dense and texture at full size.
6. Automatic background masks, and moving-object masks outdoors.
7. Recipes: `object-walkaround`, `object-turntable` (static background exclusion), `interior`
   (priors, depth fusion, learned first pass), `aerial`; multi-device merge across them.
8. Scale entry: markers (AprilTag boards), one measured distance, or a known dimension.
9. Ingest checks: tone inconsistency across the set, HEIC transcoding, low-light warnings.
10. Component reporting when a capture breaks into pieces, with where the link is missing.
11. Per-project "stays home" defaults by capture type.

### Which prototype proves what

| Case | Proven by |
|---|---|
| UC-A1 shoes, book | RC-P1 (baseline), RC-P8 (learned vs classical, with and without ARKit priors) |
| UC-A1 Lego, camera | RC-P1 extended; RC-P6 (splat vs mesh in the viewer) |
| UC-A2 | RC-P1 (fisheye model on every machine) |
| UC-A3, UC-A4 | RC-P5 (RAW develop), RC-P7 (distribution over large images) |
| UC-B1 | RC-P8 (priors), plus **RC-P10 — a room from inside** (TSDF from LiDAR, plain walls, components) |
| UC-B2–B4 | RC-P10 |
| UC-C1, D1, E1 | After Step 0 — the first real tests of the v1 recipes |

## 9. The owner's kit and answers (2026-11-23)

- **GoPro:** HERO13 Black. *(To verify: RAW photo (GPR) support and in which modes; lens modes
  available in photo and time-lapse; whether the HB-series lens mods — Macro, Ultra Wide — are
  worth testing for objects.)*
- **Lenses:** a wide range for both the D850 and the A1; the engine's recipes name what fits —
  a macro or short-tele prime around 90–105 mm at f/8–f/11 on the tripod for small objects
  (Lego, the camera), a normal prime around 35–50 mm for shoes, books and the motorbikes, a wide
  prime around 20–24 mm for the room and the car. One focal length per capture set.
- **Tripod:** yes. **Neutral background:** yes. **Turntable:** improvised — the `object-turntable`
  recipe is tested from the start.
- **Markers and scale bars:** acceptable in the first tests. A printed AprilTag board is the
  default scale and "up" source for object captures.
- **iPhone pose-and-depth route:** the owner is ready to build an internal iPhone capture app now
  rather than depend on a third-party app. See RC-P11 in the [brief](RC-brief.md).
