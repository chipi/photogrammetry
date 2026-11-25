# Step 0 status and findings

Where the prototypes and mock-ups of [Step 0](../concept/RC-brief.md) stand, and what they found.
Each prototype's README in `prototypes/` holds its full numbers and its "Not covered" list; this
page is the summary. Updated 2026-11-25; see "Resume here" for the handover.

## Prototypes

| Prototype | Status | Result in one line |
|---|---|---|
| [RC-P1 Registration on every machine](https://github.com/chipi/recce/tree/main/prototypes/RC-P1-registration) | **Proven** | COLMAP and GLOMAP register kicker, courtyard and pipes on the X3, the M4 Pro and the GB10 |
| [RC-P2 The expensive stages on the GPUs](https://github.com/chipi/recce/tree/main/prototypes/RC-P2-gpu) | **Proven** | Dense depth on courtyard through CUDA on the GB10 (1,169 s) and through HIP on the X3 in a ROCm container (3,205 s, about 2.7 times slower); a gsplat splat on the GB10 |
| [RC-P3 Quality state an agent can read](https://github.com/chipi/recce/tree/main/prototypes/RC-P3-quality) | **Proven** | An agent with only three MCP read tools names the held-out region on both scenes |
| [RC-P4 Dense, mesh, texture and splat, measured](https://github.com/chipi/recce/tree/main/prototypes/RC-P4-products) | Not proven yet | Courtyard dense and mesh scored with the ETH3D tool (F1 at 5 cm: 0.35 with RC-P1 poses, 0.88 with ground-truth poses); splats on garden (PSNR 27.7) and counter (29.2); textured mesh via texrecon; six of seven complaint measurements have a first number. Open: underwater colour (needs SQUID, RC-P12) and a 30,000-step courtyard splat |
| [RC-P5 RAW to a consistent set](https://github.com/chipi/recce/tree/main/prototypes/RC-P5-raw) | **Proven** on one scene (pipes) | The minimal rawpy route registers 14/14 with the lowest white-balance spread and is chosen |
| RC-P6 Mesh and splat in the browser | Not started | Needs RC-P4's mesh and splat; the owner checks frame rate on the iPhone |
| RC-P7 Distribution on a large set | Spec written | [GPU rental spec](gpu-rental-p7.md); renting waits for the owner |
| [RC-P8 Learned and classical, compared](https://github.com/chipi/recce/tree/main/prototypes/RC-P8-learned) | Code checked on the CPU | Four routes, two variants, three ETH3D scenes and five ARKitScenes videos; the GPU run waits for a `free` window. On the CPU, MapAnything fails on a low-texture ARKit video (relative rotation 119° median on 16 frames, the same through its own demo code) and holds on a textured one (2.9°) |
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

**Poses decide dense quality.** On courtyard the same dense stage scores F1 0.35 at 5 cm from
RC-P1's poses and 0.88 from ETH3D's ground-truth poses; RC-P1's cameras sit a median 6.1 cm from
the truth after alignment. Pose refinement before dense is the first lever, ahead of any dense
setting. Why RC-P1's poses are that far off is not investigated.

**Splat quality.** gsplat at 30,000 steps reaches PSNR 27.7 on Mip-NeRF 360 garden and 29.2 on
counter, in line with published gsplat figures. On courtyard (7,000 steps) it stays low: 18.4 dB
from RC-P1's poses, 20.9 from ground-truth poses, so poses explain part of it. Garden used
14.3 GiB of GPU memory, close to what `prod` mode leaves free.

**Texture.** texrecon (BSD; dependencies BSD and MPL-2.0) textures the courtyard mesh in 52 s on
the GB10; 16% of the faces are seen by no photo.

## Mock-ups

| Mock-up | Status |
|---|---|
| [RC-M1 the run](https://github.com/chipi/recce/tree/main/mockups/RC-M1-run) (with first passes at M2 and M3) | Phase 2 done: IBM Plex, tokens, AA contrast, field shot cards; photos hang in the air with faint rays (owner feedback, 2026-11-24) |
| M2–M8 | Later, as their prototypes produce data |

## Resume here (handover, 2026-11-25)

A fresh session starts from this page. Work stopped cleanly on the owner's instruction: no process
runs on the X3 or the DGX, the DGX is in gpu-mode `prod`, and `main` holds everything finished.

**Next, in order**

1. **RC-P8 learned and classical.** Setup done and the code checked on the CPU (see its README).
   Next: a `free` window on the DGX for `run_gpu.sh`, which runs every scene and variant and then
   RC-P4's 30,000-step courtyard splat (`gsplat_courtyard30k`).
2. **RC-P12 underwater.** Restarted from scratch: no code was written. On the X3,
   `~/.cache/recce/datasets/aquamvs` (548 MB, the ground-truth core and published result folders)
   and `~/.cache/recce/datasets/squid` (781 MB, partial) remain. SQUID is non-commercial: develop
   only, never redistribute. RC-P12 also gives RC-P4 its underwater-colour measurement. If ChArUco
   detection needs OpenCV, that is a dependency to ask about.
3. **RC-P6 mesh and splat in the browser.** Waiting on the owner: a three.js splat renderer from a
   CDN (Spark, MIT, preferred) and `rerun-sdk` in RC-P6's own environment. Then the owner checks the
   frame rate on the iPhone.
4. **RC-P10 a room from inside.** Approved (ARKitScenes, Open3D); shares RC-P8's ARKitScenes data.
5. **RC-P11** after RC-P8 or RC-P10 shows pose priors help; **RC-P7** when the owner decides to rent
   ([spec](gpu-rental-p7.md)).

**Standing rules that carry over**

- Approved downloads and installs (user-level only): ETH3D and Mip-NeRF 360 data, MapAnything
  (Apache weights only), PyTorch, gsplat, texrecon, micromamba, Open3D, ARKitScenes subset,
  AquaMVS, SQUID, Blender, rawpy, the MCP SDK (RC-P3). Anything else is asked first.
- **DGX GPU windows:** standing go by day. Message the homelab session before switching; switch with
  `ssh markodragoljevic@dgx-llm-1 '~/bin/gpu-mode-swap.sh free --json'`; when the work's processes
  have exited, send it "done"; it switches back to `prod` and verifies both vLLMs. The `claude`
  account (reached through the Mac mini) runs the jobs and cannot switch modes.
- **The X3** is shared with eval-harness, which announces its test runs; heavy Recce work stays
  sequential and off cores it pins. The HIP build is the Docker image `recce-p2-colmap-hip:latest`.
- **Gate:** `make check; echo EXIT=$?` before every commit, never a filtered line; commits land on
  `main` and CI is watched to a verdict.
- Two parallel streams at most, on sonnet subagents; each writes only its own prototype folder and
  never commits.

## Open, for the owner

- Renting a GPU for RC-P7 (spec ready).
- The iPhone frame-rate check for RC-P6, once it exists.
