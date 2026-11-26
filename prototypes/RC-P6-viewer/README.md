# RC-P6 — Mesh and splat in the browser

**Proves:** That one three.js scene shows the mesh and the splat together, on the laptop and the
iPhone. See the [brief](../../docs/concept/RC-brief.md) §5.

**Proven when:** A RC-P4 mesh and a splat of about one million gaussians load together in one
three.js scene from the result's files, render at 60 fps or more on the M4 Pro and 30 fps or more on
the iPhone 15 Pro *(agreed 2026-11-24)*, and the same result also exports to Rerun as the engineering view.

Status: **proven (2026-11-26).** The M4 Pro readings sit at the display's 60 Hz ceiling (58.8 to
60.0 fps); the owner judged that this meets the 60 fps clause.
- **Workstation:** the page loads the RC-P4 courtyard mesh and a 1,000,000-gaussian splat together
  from files and renders them at 59.9 fps (display-limited) on this machine's iGPU in Chromium.
- **Rerun:** the export is written and verified with Rerun's own CLI.
- **iPhone 15 Pro:** the owner measured 50.0 fps (median of 240 frames) on 2026-11-26, against the
  30 fps target (see "On the devices").
- **M4 Pro:** the owner measured 60.0, 59.9 (Chrome) and 58.8 fps (Safari), medians of 240
  frames at `dpr` 1 on a 60 Hz display, on 2026-11-26. A display caps `requestAnimationFrame` at
  its refresh rate, so these readings show the ceiling, not the headroom under it.

## On the devices

| Device | Browser | URL parameters | fps median (window of 240) | Loaded | Measured by |
|---|---|---|---|---|---|
| M4 Pro | Not named by the owner (the first reading) | `auto=1`, `dpr` 1 | 60.0 | 1,000,000 gaussians, 463,017 faces, 115 atlases | Owner, 2026-11-26, screenshot |
| M4 Pro | Chrome | `auto=1`, `dpr` 1 | 59.9 | same | Owner, 2026-11-26, screenshot |
| M4 Pro | Safari | `auto=1`, `dpr` 1 | 58.8 | same | Owner, 2026-11-26, screenshot |
| iPhone 15 Pro | Firefox for iOS (WebKit, as every iOS browser) | `auto=1&maxtex=1024`, `dpr` 2 | 50.0 at 09:06, 55.6 at 09:08 (one session; the server log shows no reload between) | 1,000,000 gaussians, 463,017 faces, 115 atlases | Owner, 2026-11-26, two screenshots |

**First attempt on the iPhone.** The page first stopped at "EncodingError: Loading error."
- **Cause:** the page decoded all 115 atlases at once, most of them 4096×4096, and WebKit refuses
  image decodes under that much memory.
- **Fix:** the page now decodes two atlases at a time on a phone (eight on a desktop, `texpar=`). It
  drops each full-size image after shrinking it, and keeps going with a grey material if one atlas
  fails (`p6Stats.texture_failures`).
- **Atlas size:** with the fix, the default 2048 px atlases still did not load on the iPhone and
  1024 px did, so phones now default to 1024. How the 2048 px load failed was not recorded.
- **iOS version:** not recorded yet.

## What is here

| File | Does |
|---|---|
| `index.html`, `viewer.js` | The viewer: three.js 0.187.0 and Spark 2.4.0 from jsDelivr (import map, exact versions), orbit controls, on-screen median fps, `window.p6Stats` |
| `reduce_splat.py` | Reduces the trained splat to a count (default 1,000,000) and writes it in the mesh's frame |
| `export_rerun.py` | Logs mesh, splat centres and the 38 camera poses to an `.rrd` |
| `p6_io.py` | Binary PLY, OBJ and COLMAP `.bin` readers in numpy; gsplat's world normalisation |
| `serve.sh` | Links the page into the data folder and serves it on `0.0.0.0:8806` |
| `pyproject.toml`, `ruff.toml` | The prototype's own environment (numpy, rerun-sdk); ruff extends the root config |

Licences: three.js MIT, Spark (`@sparkjsdev/spark`, World Labs) MIT, rerun-sdk MIT or Apache-2.0.
The page loads them from a CDN; nothing is vendored or installed locally for the web side.

## Data

Copied from the DGX (`claude@dgx-llm-1:~/.cache/recce/runs/p4/`, read-only) into
`~/.cache/recce/runs/p6/data/` on this machine, outside git:

| Item | From (under `runs/p4/`) | Here | Size |
|---|---|---|---|
| Textured mesh | `courtyard_3000_p1/mesh/textured.obj`, `.mtl`, 115 `textured_material*_map_Kd.png` | `data/mesh/` | 140 MB (OBJ 51.5 MB, atlases 91 MB: 6 at 4096², 2 at 2048², 12 at 1024², 26 at 512², 69 at 256²) |
| Splat, original | `gsplat_courtyard30k/result/ply/point_cloud_29999.ply` (30,000 steps, 6,190,555 gaussians) | `data/splat/courtyard_30k_full.ply` | 1,460,972,458 B (1.46 GB, 248 B per gaussian) |
| Splat, reduced | `reduce_splat.py` | `data/splat/courtyard_1m.ply` | 56,000,363 B (56 MB, 56 B per gaussian) |
| Sparse model (poses) | `courtyard_3000_p1/dense/sparse/*.bin` | `data/sparse/` | 11 MB |
| Cropped mesh, crop box, Sim(3) | `mesh/mesh_crop.ply`, `bbox.json`, `align/sim3.json` | `data/` | 9.2 MB, small |
| Rerun recording | `export_rerun.py` | `courtyard.rrd` | 33.1 MB |

The courtyard mesh and the courtyard splat come from the same RC-P1 poses and the same undistorted
workspace (`dense/`), so they share a frame up to the transform below. The `counter` splat is a
different scene and is not used. ETH3D courtyard is CC BY-NC-SA 4.0: the data stays local.

### Frame alignment

The two files are not in the same coordinates, and one transform is needed.

- **Mesh and sparse model:** the same frame. The mesh vertices (x −4.21…27.65, y −13.56…10.30,
  z −0.13…18.62) lie inside `bbox.json`'s crop box, and the sparse model's cameras are in that frame
  (`DSC_0296` at (3.39, 0.84, 1.67), its image y axis pointing to −z: the frame is z up). No mesh
  transform.
- **Splat:** trained with `normalize_world_space: true` (`cfg.yml`), so gsplat recentred, rescaled
  (factor 0.207579) and rotated the scene from the camera poses and sparse points before training,
  and the PLY holds that normalised frame. `reduce_splat.py` recomputes the same transform from
  `dense/sparse` (a numpy reimplementation of gsplat's `normalize.py`, `similarity_from_cameras`,
  `align_principal_axes` and the up-flip) and writes the splat in the model frame: positions by the
  inverse similarity, quaternions rotated, log scales shifted by −log(0.207579).
- **Check (numbers):** share of mesh vertices that fall in a 0.5 m voxel holding a splat centre:
  97.9% with the transform baked in, 12.7% with the PLY as trained, 50.2% for the baked splat
  moved 2 m in x (a control).
- **Check (picture):** the viewer looks through the training camera `DSC_0296` (`?view=` below) with
  mesh only, splat only and both; the pallet, the bin, the window frames and the bicycle line up
  between the two. The pictures were read by eye; no pixel metric was computed.
- The page rotates the model frame by −90° about x (z up to three.js y up); both objects sit in
  one group.

## Reduction rule

`reduce_splat.py` keeps the 1,000,000 gaussians with the largest `sigmoid(opacity) × exp(s0 + s1 + s2)`,
opacity times scale volume (`scale_i` are log scales). It also drops the spherical-harmonic bands
above degree 0 (`f_rest_*`): rotating them with the frame change is not implemented, and colour only
makes the file 56 MB instead of 248 MB. The kept set holds 99.8% of the total opacity-weighted volume;
the kept gaussians have a median largest axis of 6.4 cm and 99th percentile 56.5 cm (model units; the
mesh spans about 32 × 24 × 19 of them). The rule is a first choice: other scores (opacity only, opacity × maximum scale²)
give nearly the same size distribution; their visual effect is not compared.

## Setup

```bash
cd prototypes/RC-P6-viewer
uv sync            # numpy and rerun-sdk 0.44.0 in this folder's own .venv
```

`export_rerun.py` reads the atlases with Pillow, which `rerun-sdk` installs as its own dependency; it
is not declared in `pyproject.toml`. The data is copied as described in "Data" (`scp` from the DGX).

## Run

```bash
cd prototypes/RC-P6-viewer
D=~/.cache/recce/runs/p6/data
uv run python reduce_splat.py $D/splat/courtyard_30k_full.ply $D/sparse $D/splat/courtyard_1m.ply
uv run python export_rerun.py           # writes ~/.cache/recce/runs/p6/courtyard.rrd
./serve.sh                              # http://<this machine>:8806/
```

`serve.sh` links `index.html` and `viewer.js` into `~/.cache/recce/runs/p6/` and runs
`python3 -m http.server 8806 --bind 0.0.0.0` there. The folder then holds the page and `data/`, and
every path in the page is relative. Port 8765 is taken on this machine, hence 8806.

Open `http://localhost:8806/`. Page parameters: `auto=1` (orbit by itself), `dpr=` (pixel ratio,
capped at 2), `maxtex=` (largest atlas side; 1024 on iPhone and Android by default, no limit on a
desktop), `window=` (frames in the fps window, default 240), `sync=1` (a one-pixel readback after each
frame, so frame time includes the GPU), `mesh=`, `mtl=`, `splat=` (other paths) and
`view=<12 numbers>&fov=` (a COLMAP camera-to-world 3×4, row-major; for example the training camera
`DSC_0296`):

```text
http://localhost:8806/?view=0.433234,0.125200,-0.892543,3.390479,0.901060,-0.038227,0.432006,0.835154,0.019968,-0.991395,-0.129374,1.671166
```

The default view orbits the mesh's bounding box from outside, where the splat's floaters show; the
`view=` URL stands at a capture position, where both look like the scene.

The fps counter shows the median of the last 240 frame times (as fps) once 240 frames exist.
`window.p6Stats` holds `fps_median`, `fps_min`, `frames`, `splats`, `mesh_faces`, `mesh_materials`,
`load_s`, `dpr`, `gpu`, `ready` and `error`.

Rerun: `uv run rerun ~/.cache/recce/runs/p6/courtyard.rrd` opens the viewer on the file.

## Results

Measured 2026-11-25 on this machine (AMD Ryzen AI Max+ 395, Radeon 8060S iGPU), Chromium 152.0.7977.82
headless (`--headless=new`) on the real GPU: the page's own `p6Stats.gpu` reads
`ANGLE (AMD, Vulkan 1.4.354 (AMD Radeon 8060S Graphics (RADV STRIX_HALO)), radv)`. The harness is a
Node script over the Chrome DevTools Protocol (no packages; it is not committed): it opens the URL,
waits for `p6Stats.fps_median`, then reads `p6Stats`. Camera: `auto=1` orbit from the `DSC_0296`
position. Flags: `--enable-gpu --ignore-gpu-blocklist --use-angle=vulkan --enable-features=Vulkan`.

| Run | Window | fps median (window of 240) | fps min | Loaded |
|---|---|---|---|---|
| Display-synced, `dpr` 1 | 1280×800 | 59.9 | 30.0 | 1,000,000 gaussians, 463,017 faces, 115 atlases; mesh 1.7 s, splat 1.1 s |
| Uncapped (`--disable-frame-rate-limit --disable-gpu-vsync`), `sync=1`, `dpr` 1 | 1920×1080 | 344.8 | 51.8 | same |
| Same, `maxtex=2048` | 1920×1080 | 333.3 | 80.6 | same |
| Same as the second row, `dpr=2` (earlier run, pre-final code) | 3840×2160 | 151.5 | 41.0 | same |

What the numbers are: the first row is the 60 Hz cadence of the headless compositor, so 59.9 means
the page kept pace with 60 Hz, not that the GPU needed 16.7 ms. The uncapped rows add a pixel
readback so each frame includes the GPU's work; without it the uncapped counter reads 2,500 to
5,000 fps because the page only queues commands, and that number is meaningless. Headless draws to
no display, so these figures say the iGPU renders the scene far faster than 60 fps and say nothing
about a display's presentation, the M4 Pro or the iPhone. The minimum (30 fps once in 240 frames in
the first row) is a single slow frame, likely the splat sort catching up; not investigated.
A software control (`--use-angle=swiftshader`) rendered fewer than 240 frames in the 4-minute wait:
not meaningful, as expected.

Rerun export (`uv run python export_rerun.py`, 4 s):

```text
mesh: 463,017 faces, 1,389,051 unrolled vertices
splat centres: 1,000,000 points
cameras: 38 poses with pinholes
wrote /home/marko/.cache/recce/runs/p6/courtyard.rrd (33.1 MB)
```

Checked with Rerun's CLI (`uv run rerun`, rerun-cli 0.44.0): `rrd verify` prints
`1 file verified without error.`; `rrd stats` lists 80 static chunks over 42 entity paths; `rrd print`
shows `/world/mesh` with `Mesh3D` triangle indices, vertex colours and positions (26.5 MiB),
`/world/splat` with `Points3D` positions, colours and radii (15.3 MiB), and a `ViewCoordinates`
(z up) on `/world`. The viewer was not opened (no display here).

Rerun takes one albedo texture per mesh and texrecon writes 115 atlases, so the export colours each
face corner by the atlas texel at its uv (nearest texel, 1,389,051 unrolled vertices) instead of
logging the texture.

### To measure by the owner

M4 Pro (60 fps or more): 58.8 to 60.0 fps, measured 2026-11-26, met by the owner's judgement.
iPhone 15 Pro (30 fps or more): 50.0 fps, measured 2026-11-26.

1. On this machine run `./serve.sh` (it stays in the foreground). This machine is `omarchy` on the
   tailnet, `100.92.54.65`.
2. On the Mac or the iPhone (on the tailnet) open `http://omarchy:8806/?auto=1` (or
   `http://100.92.54.65:8806/?auto=1` if MagicDNS does not resolve it). The first load downloads
   about 200 MB over the tailnet (mesh 140 MB, splat 56 MB); the mesh needs a few seconds to parse.
   The page is plain HTTP; WebGL 2 does not need HTTPS.
3. Wait until the top-left line shows `1,000,000 gaussians, 463,017 faces, 115 atlases`. Read the
   `fps` value after it settles (about 10 s). With `auto=1` the camera moves by itself; drag to
   orbit and pinch to zoom on top of that. Note the value and the scene from the `view=` URL as well.
4. Mac: use the same page in Safari and Chrome; the Safari Web Inspector console (Develop menu) or
   Chrome's console takes `JSON.stringify(p6Stats)`. A ProMotion display may run `requestAnimationFrame`
   at 120 Hz; the target is 60 fps or more.
5. iPhone: turn Low Power Mode off (it caps Safari at 30 fps); the counter is on screen. If the tab
   reloads or the page stays at "loading", note it: the OBJ is a 51.5 MB text file parsed on the main
   thread and the atlases need about 300 MB of GPU memory at `maxtex=2048` (about 620 MB at full
   size, `?maxtex=4096`); try `?maxtex=1024`. Record iOS version and Safari version.
6. This machine's host firewall was not inspected (`sudo` is not available to the agent that built
   this). If the phone cannot connect while `curl http://100.92.54.65:8806/index.html` on this
   machine works, the host firewall needs TCP 8806 open on `tailscale0`; nothing was changed.

## Not covered

- **Headroom on the M4 Pro.** Its readings are capped by a 60 Hz display at `dpr` 1; frame time
  under the cap, the minimum fps (`p6Stats.fps_min`) and a Retina canvas (`dpr` 2) are not
  measured. Safari read 58.8, 2% under the ceiling; whether those frames were late from the GPU
  or the display timing is not checked.
- **The iPhone** ran one session in one browser (Firefox for iOS), at `maxtex=1024`, with the iOS
  version unrecorded; Safari on the iPhone was not run. Thermal behaviour over a longer session
  was not watched on either device.
- **A real display on the workstation.** Its measurements are headless; presentation, vsync and thermal throttling
  are unmeasured, and so is frame time on a 4K or retina canvas beyond one early run.
- **Visual quality.** The splat is RC-P4's courtyard splat (18.21 dB held-out PSNR, built on poses
  that RC-P4 found weak); the default orbit view from outside shows streaks and floaters. The
  reduction's effect on quality is not measured against the 6.19 M original (no render comparison,
  no PSNR), and the degree-0 colour drops view-dependent shading.
- **Unlit mesh.** The mesh uses `MeshBasicMaterial`; the OBJ holds 463,017 faces of the
  502,902 in RC-P4's cropped mesh, and the gaps show as holes; the Delaunay mesh is untrimmed beyond
  RC-P4's crop.
- **The `counter` splat** and any other scene; the splat's orientation transform (quaternion and
  scale baking) is checked only by eye against the mesh at one camera, not by a numerical test.
- **Rerun in the GUI.** The `.rrd` is verified by the CLI only. A read-back through the SDK needs
  `datafusion` (`rerun-sdk[catalog]`), which is not approved and not installed. The splat is logged
  as centres (no ellipsoids, no covariance); the mesh colour is a nearest-texel sample.
- **Offline use.** The page needs the CDN; nothing is cached or vendored. No bundler, no minified
  build.
- **A committed test.** There is no automated test for the viewer; the measurement harness lives
  outside the repository.
