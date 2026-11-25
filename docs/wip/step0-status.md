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
| [RC-P4 Dense, mesh, texture and splat, measured](https://github.com/chipi/recce/tree/main/prototypes/RC-P4-products) | Not proven yet | Courtyard dense and mesh scored with the ETH3D tool (F1 at 5 cm: 0.35 with RC-P1 poses, 0.88 with ground-truth poses); splats on garden (PSNR 27.7) and counter (29.2); textured mesh via texrecon; all seven complaint measurements have a first number (underwater colour from RC-P12, on images). The courtyard splat at 30,000 steps reaches 18.2 dB, no better than at 7,000, so steps are not the cause. Open: the texture-side parts of measurements 1 and 4 |
| [RC-P5 RAW to a consistent set](https://github.com/chipi/recce/tree/main/prototypes/RC-P5-raw) | **Proven** on one scene (pipes) | The minimal rawpy route registers 14/14 with the lowest white-balance spread and is chosen |
| [RC-P6 Mesh and splat in the browser](https://github.com/chipi/recce/tree/main/prototypes/RC-P6-viewer) | Not proven yet | The RC-P4 courtyard mesh and a 1,000,000-gaussian splat load together in three.js + Spark at 59.9 fps (display-limited) in Chromium on the X3's iGPU; the Rerun export is verified with Rerun's CLI. Open: the owner's frame-rate checks on the M4 Pro (60 fps) and the iPhone 15 Pro (30 fps); Safari not run |
| RC-P7 Distribution on a large set | Spec written | [GPU rental spec](gpu-rental-p7.md); renting waits for the owner |
| [RC-P8 Learned and classical, compared](https://github.com/chipi/recce/tree/main/prototypes/RC-P8-learned) | **Proven** | MapAnything + bundle adjustment comes close to COLMAP on ETH3D and covers frames COLMAP drops on two ARKit videos, but fails without warning on two others; its metric scale is off by up to 29% (ETH3D) and 41% (ARKit). Owner's decision: an optional second route beside COLMAP, kept only after an agreement check (not built yet), never the source of scale |
| [RC-P9 A robot's capture set](https://github.com/chipi/recce/tree/main/prototypes/RC-P9-robot-capture) | **Proven** on the 1.2 m fixture | Scale error 0.021% (limit 0.5%), placement error 0.18% of extent (limit 1%) |
| RC-P10 A room from inside | Not started | Approved: ARKitScenes, Open3D |
| RC-P11 The iPhone capture app | Not started | Starts once RC-P8 or RC-P10 shows pose priors help |
| [RC-P12 Underwater](https://github.com/chipi/recce/tree/main/prototypes/RC-P12-underwater) | Not proven yet | AquaMVS: the refractive model measures the board to +0.017% scale and 1.15 mm rigid RMSE, the pinhole model to −1.50% and 5.83 mm (−4.8% on one frame). SQUID: one global white balance on the RAW makes the grey patches grey at 6–19 m (median 1.4°); haze is what remains, and range-based backscatter removal raises contrast (mean 0.21 to 0.47) but tints the near charts. Ranges from our own reconstruction fail on SQUID (8 barely overlapping hazy stereo pairs: 0–1.1% of pixels pass PatchMatch's consistency check), so that clause cannot be met on this data. The open underwater benchmark is [specified](underwater-benchmark-spec.md). Open: the owner's call on the ranges clause |

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
from RC-P1's poses, 20.9 from ground-truth poses, so poses explain part of it; 30,000 steps from
RC-P1's poses give 18.2 dB, so the step count does not. Garden used
14.3 GiB of GPU memory, close to what `prod` mode leaves free.

**Texture.** texrecon (BSD; dependencies BSD and MPL-2.0) textures the courtyard mesh in 52 s on
the GB10; 16% of the faces are seen by no photo.

**Learned poses.** MapAnything's Apache checkpoint alone is 0.9–1.7° and 12–37 cm off on ETH3D;
bundle-adjusted from the same SIFT matches it comes close to COLMAP (0.36–0.82° relative against
0.40–0.69°). The adjustment
lets the scale drift (−41% and −74% on two ETH3D runs), so the adjusted model is anchored to
MapAnything's camera centres. On ARKitScenes it fails on one low-texture video (82° relative) and
is wrong in parts on a textured one; COLMAP registers 10–18% of the frames of the low-texture
videos. MapAnything needs 42–59 GiB of GPU memory for 90–218 views, more than `prod` mode leaves.

**Underwater.** Refraction is a scale error, not noise: on AquaMVS a pinhole calibration is off by
−0.03% to −4.8% depending on where the board is, and a refractive model by at most ±0.28%. Colour
underwater needs the RAW: SQUID's published TIFs clip red to zero on 78–99.9% of pixels. Over 6–19 m
on the Satil wreck the colour cast is nearly one global tint, which a single white balance removes;
what changes with range is contrast (0.39 to 0.07 on the grey ramp), and the simple per-image
backscatter fit restores it unevenly. Our own pipeline gets no depth from SQUID's few hazy stereo
pairs without the rig calibration. SQUID's chart annotations sit a few pixels off its published
undistorted images and are snapped before use.

## Mock-ups

| Mock-up | Status |
|---|---|
| [RC-M1 the run](https://github.com/chipi/recce/tree/main/mockups/RC-M1-run) (with first passes at M2 and M3) | Phase 2 done: IBM Plex, tokens, AA contrast, field shot cards; photos hang in the air with faint rays (owner feedback, 2026-11-24) |
| M2–M8 | Later, as their prototypes produce data |

## Resume here (handover, 2026-11-25)

A fresh session starts from this page. Updated after the RC-P8 GPU window (2026-11-25, 15:15 to
17:14): no Recce process runs on the X3 or the DGX, the homelab session has switched the DGX back to
gpu-mode `prod`, and `main` holds everything finished. RC-P8's results and the 30,000-step
courtyard splat are in their READMEs.

**Tracker.** The owner follows progress on a private page,
[Recce Step 0 Tracker](https://claude.ai/artifact/L5nUn48i3hDqYkxz9frQE5), which mirrors this page.
Republish it (read it first, then publish to the same link) whenever a row here changes.

**Next, in order**

1. **RC-P12 underwater, the rest.** Both measurements, the failed attempt at our own ranges and
   the [benchmark spec](underwater-benchmark-spec.md) are done. Left: a better backscatter fit
   (Sea-thru's local illuminant, a check against a dark target); the owner's call on whether the
   "ranges from the reconstruction" clause moves to the benchmark's site scene. Data on the
   X3: SQUID Satil (MD5 matches Zenodo's) and its evaluation code, AquaMVS core and `data.zip` (MD5
   matches). SQUID is non-commercial: develop only, never redistribute.
2. **RC-P6: the owner's frame-rate checks.** `./serve.sh` in `prototypes/RC-P6-viewer`, then
   `http://omarchy:8806/?auto=1` on the M4 Pro (60 fps) and the iPhone 15 Pro (30 fps); Safari and
   iOS are untested. If the phone cannot connect, TCP 8806 on `tailscale0` is closed.
3. **RC-P8's agreement check** (owner's decision: optional second route, kept only after a check
   against the classical model): build and test it.
4. **RC-P10 a room from inside.** Approved (ARKitScenes, Open3D); shares RC-P8's ARKitScenes data.
5. **RC-P11** after RC-P8 or RC-P10 shows pose priors help; **RC-P7** when the owner decides to rent
   ([spec](gpu-rental-p7.md)).

**Standing rules that carry over**

- Approved downloads and installs (user-level only): ETH3D and Mip-NeRF 360 data, MapAnything
  (Apache weights only), PyTorch, gsplat, texrecon, micromamba, Open3D, ARKitScenes subset,
  AquaMVS, SQUID, Blender, rawpy, the MCP SDK (RC-P3); three.js and Spark from a CDN and
  `rerun-sdk` (RC-P6's environment); scipy, tifffile and `opencv-python-headless` (RC-P12's
  environment). Anything else is asked first.
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
- The M4 Pro and iPhone frame-rate checks for RC-P6 (ready to run).
