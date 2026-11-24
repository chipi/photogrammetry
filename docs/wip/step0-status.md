# Step 0 status and findings

Where the prototypes and mock-ups of [Step 0](../concept/RC-brief.md) stand, and what they found.
Each prototype's README in `prototypes/` holds its full numbers and its "Not covered" list; this
page is the summary. Updated 2026-11-24; work paused until 2026-11-25 on the owner's instruction.

## Prototypes

| Prototype | Status | Result in one line |
|---|---|---|
| [RC-P1 Registration on every machine](https://github.com/chipi/recce/tree/main/prototypes/RC-P1-registration) | **Proven** | COLMAP and GLOMAP register kicker, courtyard and pipes on the X3, the M4 Pro and the GB10 |
| [RC-P2 The expensive stages on the GPUs](https://github.com/chipi/recce/tree/main/prototypes/RC-P2-gpu) | **Proven** | Dense depth on courtyard through CUDA on the GB10 (1,169 s) and through HIP on the X3 in a ROCm container (3,205 s, about 2.7 times slower); a gsplat splat on the GB10 |
| [RC-P3 Quality state an agent can read](https://github.com/chipi/recce/tree/main/prototypes/RC-P3-quality) | **Proven** | An agent with only three MCP read tools names the held-out region on both scenes |
| [RC-P4 Dense, mesh, texture and splat, measured](https://github.com/chipi/recce/tree/main/prototypes/RC-P4-products) | Running | Setup done; GPU phase in progress |
| [RC-P5 RAW to a consistent set](https://github.com/chipi/recce/tree/main/prototypes/RC-P5-raw) | **Proven** on one scene (pipes) | The minimal rawpy route registers 14/14 with the lowest white-balance spread and is chosen |
| RC-P6 Mesh and splat in the browser | Not started | Needs RC-P4's mesh and splat; the owner checks frame rate on the iPhone |
| RC-P7 Distribution on a large set | Spec written | [GPU rental spec](gpu-rental-p7.md); renting waits for the owner |
| RC-P8 Learned and classical, compared | Not started | Approved: MapAnything on the GB10, ARKitScenes subset |
| [RC-P9 A robot's capture set](https://github.com/chipi/recce/tree/main/prototypes/RC-P9-robot-capture) | **Proven** on the 1.2 m fixture | Scale error 0.021% (limit 0.5%), placement error 0.18% of extent (limit 1%) |
| RC-P10 A room from inside | Not started | Approved: ARKitScenes, Open3D |
| RC-P11 The iPhone capture app | Not started | Starts once RC-P8 or RC-P10 shows pose priors help |
| RC-P12 Underwater | Not started | Approved: AquaMVS and SQUID |

## Findings

**Strategies.** On three scenes and three machines GLOMAP maps 3–4 times faster than COLMAP's
incremental mapper with the same pose accuracy (rotation within a few tenths of a degree, position
under a centimetre apart). GLOMAP's reprojection error is about twice COLMAP's on every scene and
machine (1.9–2.9 px against 1.1–1.3 px); the cause is not known.

**Scoring.** A camera a mapper poses without any 3D point is not part of the model. GLOMAP posed
one such photo on kicker about 47 m from its true place, and including it in the alignment turned
a 0.6° result into 13°. Every score now counts only cameras that hold points.

**Machines and builds.**
- pycolmap 4.2.1 from PyPI has no CUDA and no Linux ARM wheel. On the GB10 the conda-forge build
  (CUDA) is used through micromamba. It runs SIFT extraction and matching on the GPU, about three
  times faster than the CPU on the X3 or the M4 Pro.
- Runs on different machines give the same quality but not identical models: GLOMAP joined
  kicker's problem photo on the M4 Pro and the GB10, not on the X3.
- Registration of a 38-image scene peaks at 28 GB resident memory (courtyard, M4 Pro).
- Poisson meshing in the conda-forge pycolmap build for the GB10 aborts ("Failed to close loop"),
  even on a synthetic sphere. Delaunay meshing works and is used.
- COLMAP upstream has a HIP backend since 2026-10 (PR #4795). Built from `main` in a ROCm 7.2.4 container for gfx1151, it runs dense depth on the X3 at about 2.7 times the GB10's time, at 98% GPU use; one run aborted with a memory-aperture violation and a repeat passed (not root-caused). Nothing is installed on the host.

**GB10 GPU time.** The DGX serves production LLMs in gpu-mode `prod`, which leaves about 15 GB of
memory. Recce GPU work runs in a `free` window: by day under the owner's standing go, switched by
the Recce session as `markodragoljevic`, switched back to `prod` and verified by the homelab
session. Dense depth and a splat together used up to 50 GB.

**Quality state.** Coverage per region is enough for an agent to find a removed region, when the
removal is local: choosing the region whose removal touches the fewest neighbours matters, since a
naive choice left 12 of 22 regions at zero coverage and the test unanswerable.

**RAW.** A minimal pipeline (rawpy, one white balance and one exposure for the whole set)
registers as well as the camera JPEGs, with the most even colour. Chemigram, as driven here,
registered 7 of 14 photos with dark, yellow-green renders; stock darktable on the same RAW files is
neutral, so the cause lies in Chemigram's presets or the recipe used. Not investigated.

**Robot capture sets.** With exact poses the model lands within 0.021% scale and 0.18% placement;
the frame conversion (OpenGL camera axes, z-up world, `{x, y, z, w}` quaternions) is checked by
render, and both wrong-convention controls fail.

**Splat quality.** The first gsplat run (courtyard, 7,000 steps) scored PSNR 18.8 on held-out
views, low for the method; not investigated yet (RC-P4 runs 30,000 steps on Mip-NeRF 360).

## Mock-ups

| Mock-up | Status |
|---|---|
| [RC-M1 the run](https://github.com/chipi/recce/tree/main/mockups/RC-M1-run) (with first passes at M2 and M3) | Phase 2 done: IBM Plex, tokens, AA contrast, field shot cards; photos hang in the air with faint rays (owner feedback, 2026-11-24) |
| M2–M8 | Later, as their prototypes produce data |

## Open, for the owner

- Renting a GPU for RC-P7 (spec ready).
- The iPhone frame-rate check for RC-P6, once it exists.
