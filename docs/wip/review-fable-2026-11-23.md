# Review of the concept-phase start (2026-11-23)

An independent advisor review (Fable 5.1, read-only) of the brief, the architecture sketch, the use
cases, the research notes and the reference documents, as they stood on 2026-11-23. Condensed;
the full findings are below by heading. External facts the reviewer did not check are marked
*(unverified)*.

## Status of the findings

| Finding | Status |
|---|---|
| Laptop "complete system" contradicts the platform matrix | Fixed 2026-11-23 (brief §1, sketch §4, open question 16) |
| Splats in the MVP: brief and sketch vs product analysis | Fixed 2026-11-23 (superseded note in the product analysis) |
| iPhone app vs non-goals and stale "later" text | Fixed 2026-11-23 (brief §2 and §4, sketch §1, use cases UC-A1) |
| Competitive gap overstated | Fixed 2026-11-23 (brief §3) |
| Prototype restructuring (merge P1/P2, drop iMac Pro, P3 onto a large set, testable criteria, own robot fixture, Chemigram route in the develop prototype, underwater criterion) | Done 2026-11-24 (brief §5, new numbering) |
| Positioning | Partly answered 2026-11-24: origin and drivers in brief §0; vision sentence recorded as a candidate |
| Licence | Decided 2026-11-24: MIT from the start ([Licensing](../LICENSING.md)) |
| Capture-set amendments, storage budget, privacy of traces, proposed tolerances | Open — with the owner |

## 1. Gaps

1. "The laptop alone is a complete system" is false with the default stack: no COLMAP dense or
   gsplat on the M4 Pro (tools overview §18).
2. RC-P3 tests the wrong input: fanning out features and matching on 60–150 iPhone photos takes
   seconds, so transfer dominates. The hours on large sets are dense depth and splat training, which
   run on one or two machines (GB10, X3 if HIP works). The riskiest unknowns — cutting and merging a
   view graph across machines (sketch Q5) and the X3 HIP dense build — are untested. "Matches a
   single-machine run" needs a tolerance: GPU SIFT is not bit-identical across CUDA, HIP and CPU.
3. Splats in or out of the MVP: documents disagreed.
4. The iPhone app contradicted the non-goals and stale "later" text in four places.
5. Prototype dependencies inverted: RC-P4 needs ARKit poses (RC-P10 or a third-party export) and
   MapAnything on CUDA (the GB10 build RC-P2 proves); RC-P5 depends on a Gazebo fixture
   robotics-lab has offered but not built.
6. Untestable criteria: RC-P6 ("the owner agrees"), RC-P7 ("usable"), RC-P5 and RC-P9 ("a stated
   tolerance", none stated); RC-P8 has none. Suggested RC-P6 test: remove a region's images, the
   agent names the region, add them back, show the coverage metric moved.
7. The capture-set format cannot yet carry an iPhone capture: per-sensor intrinsics (ARKit's vary
   per frame with focus *(unverified)*), PNG-only images (no DNG or HEIC), no specified conversion
   from ARKit's y-up camera-to-world frame.
8. No data-volume or storage budget: 150 D850/A1 RAWs is about 8 GB before intermediates, depth
   maps and caches on every worker. Deletion by hash must also purge worker and rented-box caches.
9. Four GPU platforms is an unpriced maintenance tax; the iMac Pro costs more than it contributes.
10. The competitive gap was overstated (WebODM, Meshroom, Brush, RealityScan with AMD; splats exist
    in Pix4D, Polycam, KIRI, Postshot, WebODM).
11. Decided early without evidence: own worker protocol, SvelteKit + three.js + Spark, monorepo,
    X3 as coordinator. Decided late: what the MVP delivers for which use case, and any time budget
    for one person.
12. Privacy and licence: traces would carry home-scan file names; Refractive COLMAP's licence is
    unknown; "open source later" while licence is listed open; the benchmark set holds private
    photos.
13. Minor: primer §8 says COLMAP dense needs CUDA (also HIP); primer §13 attributes the
    range-dependent attenuation finding to Sea-thru, which applies Akkaynak and Treibitz's 2018
    revised model *(unverified detail)*.

## 2. Motivation and positioning

1. As a Metashape or RealityScan replacement it is not worth building; for objects, bikes and rooms
   free tools suffice *(RealityScan Windows-only unverified)*.
2. What no tool does: scale, frame and uncertainty as an output contract; quality as
   machine-readable state with per-image verdicts and coverage regions; robot or ARKit poses as
   weighted priors with a refinement statement; refraction and range-based colour.
3. Three equal pillars is a lack of focus. The hardware pool is mostly an engineering itch for small
   sets; its real value is "offload from the field laptop to home, burst to a rented GPU". The
   photographer pillar competes with free products. Robots and agents have no incumbent.
4. Proposed centre: the scientific reconstruction model plus agent-readable quality state, with
   underwater as the flagship domain.
5. MCP is substantive only if the loop closes: the engine names a weak link, an agent turns it into
   a capture request for a robot or a diver, the engine re-registers incrementally. Second use:
   agents running the benchmark across recipes.
6. Proposed vision sentence: "A reconstruction engine that always says what it knows and what it
   does not (scale, frame, coverage, uncertainty) so that a person, a robot or an agent can decide
   what to capture next, above water and below."

## 3. Ideas for more value

1. **Capture judge first:** a CPU-only `recon judge` — blur, exposure and white-balance variance,
   overlap, lens groups, components and weak links after a fast sparse solve — as JSON and over
   MCP; usable at the dive site and as a front end to other tools. About 2–3 weeks.
2. **Chemigram as the develop stage:** darktable headless, gray-card white balance, state
   propagation across a set; reverse: range maps become a Sea-thru primitive in Chemigram. Days.
3. **Open underwater benchmark with ground truth:** flat vs dome port, GoPro vs DSLR, scale bars and
   tags; Brown vs Refractive COLMAP vs MapAnything. A research contribution; gives RC-P8 a
   criterion.
4. **Robotics-lab as the first real client**, closing the capture-advice loop.
5. **A repeatable motorised object rig** for benchmark error bars.
6. **Rerun as the engineering viewer** until the product UI earns its place.
7. **4D reef monitoring:** two dives, co-registered, change detection.
8. **GoPro GPMF gravity and gyro as SfM priors.**

## 4. Sequencing proposed by the reviewer

This week: the shoes with the iPhone and the D850 beside an AprilTag board, COLMAP and GLOMAP on
the M4 Pro and the X3; in parallel the COLMAP HIP dense build on the X3 and pycolmap + gsplat on the
GB10; `quality.json` v0 with three MCP read tools; capture-set amendments to robotics-lab.

Restructuring: cut the iMac Pro; merge P2 into P1; move P3 after a large set exists, with dense
depth and SfM partition as the unit of work and a stated tolerance; defer P10 in favour of a
Record3D or Polycam export; replace P5's Gazebo fixture with a Blender render; Chemigram in P7b;
give P8 a criterion and move it ahead of P7.

## Questions for the owner before the vision

1. Which single result in three months makes the project worth it?
2. When is the next dive, with scale bars and both port types?
3. Has the shoes set been tried in RealityScan or Apple Object Capture?
4. Is the hardware pillar about using every machine, or about offloading from the field and
   bursting to rented GPUs?
5. Storage budget and retention rule for home scans?
6. Will robotics-lab deliver a real capture set in the first quarter, or does this project make its
   own fixture?
7. Metric tolerances for RC-P5 and RC-P9, in millimetres and as a percentage.
8. Licence: decide permissive now, or keep it open?
9. Is the iOS app worth the weeks it displaces?
10. Does the GB10's shared-GPU schedule leave enough CUDA time, or is a rented card the real CUDA worker?
