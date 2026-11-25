# RC-P12 — Underwater

**Proves:** That the pipeline holds up underwater, and what refraction modelling and range-based
colour correction add. See the [brief](../../docs/concept/RC-brief.md), RC-P12.

**Proven when:** On AquaMVS, distances between board corners are measured with the standard camera
model and with a refractive model, and the error of each is recorded; on SQUID, range-based colour
correction with ranges from the reconstruction is compared with uncorrected images on the scene's
reference targets (identical DGK Color Tools charts placed at several distances); the open
underwater benchmark is specified from what the public sets lack.

**Status (2026-11-25): not proven yet.** Both measurements are done: on AquaMVS the refractive
model measures the board to +0.017% scale and 1.15 mm rigid RMSE against −1.50% and 5.83 mm for
the pinhole model; on SQUID, range-based correction is compared with uncorrected and globally
balanced images, with SQUID's stereo ranges. Ranges from our own reconstruction were tried and
fail on SQUID Satil (see "Ranges from our reconstruction"), so that clause cannot be met on this
data. The open underwater benchmark is specified in
[underwater-benchmark-spec.md](../../docs/wip/underwater-benchmark-spec.md); its site scene (S1) is
where the ranges clause can be met, if the owner moves it there.

## Data

| Set | Licence | Used here |
|---|---|---|
| SQUID Satil: Berman, Levy, Treibitz, Avidan, "Underwater Single Image Color Restoration Using Haze-Lines and a New Quantitative Dataset", arXiv:1811.01343 (2018), the citation the project page gives | CC BY-NC-SA 4.0: develop only, never redistribute | Five right-camera NEFs with chart annotations (sets 01, 02, 03, 04, 06), their resizedUndistort TIFs and stereo range maps |
| SQUID evaluation code | Published with the dataset | The chart annotations (`param_files_undistort/RGT_*_params.mat`) and the grey-patch measure |
| AquaMVS | CC BY 4.0 | Ground-truth core (pinhole calibration and its corners); `data.zip` (6.2 GB, MD5 `0753c127a10f9a41f6b7042e9253e81f` matches) for the refractive calibration and its corners |

Everything lives under `$RECCE_DATA_DIR/datasets/` (default `~/.cache/recce`); results go to
`$RECCE_DATA_DIR/runs/p12/`. Nothing from SQUID is committed: no images, crops or renders.

## SQUID colour

```
uv run python colour.py                 # SQUID's ranges; writes runs/p12/colour_squid.json
uv run python colour.py --ranges ours   # ranges from recon.py, where a model exists
```

### What the published files hold

- **The TIFs cannot carry colour underwater.** In the five resizedUndistort TIFs red is 0 on
  78–99.9% of pixels and on the white patch of all 14 readable charts: the conversion to sRGB
  clipped it. On the RAW (NEF) red is weak but present (RGT_4336: median 371 DN above black
  against 2,829 for green). Every measurement below therefore runs on the RAW. Scored as
  published, the TIFs sit at 37.9–40.8° from grey on every chart.
- **The TIFs are not linear.** Registered against the linear RAW decode, the green channel
  follows a log-log slope of 0.459 (correlation 0.972 in log), the shape of a 1/2.2 gamma; the
  TIF column below undoes the sRGB curve.
- **The undistortion model cannot be read.** `stereoParams0.5.mat` holds a MATLAB
  `stereoParameters` object, opaque outside MATLAB. `squid_raw.py` instead registers the RAW to
  the undistorted TIF: green is phase-correlated on 256-pixel tiles, a cubic polynomial maps TIF
  pixels to RAW pixels (1.17–1.38 px RMS residual at TIF scale, 210–221 of 224–226 tiles kept),
  and the registered RAW green correlates 0.949–0.974 in log with the TIF green.
- **The chart annotations are off by several pixels** in the published TIFs. SQUID's evaluation
  undistorts with MATLAB's `undistortImage` at run time, which evidently differs from the
  published files. Unshifted, the samples of RGT_4318's 10.8 m chart sat on the separators, and
  its black patch read the same as its white. Each chart's annotation is shifted by the integer
  offset within ±6 px that puts its 18 patch centres on uniform pixels while keeping the grey
  ramp's contrast; uniformity alone pulled small charts onto the white board. The shifts come out
  at x −3 to −6, y −4 to 0 on 14 of 15 charts (one systematic offset); RGT_4376 chart 3 is the
  exception (+2, −6). After shifting, 14 of 15 grey ramps descend from white to black, against 7
  before. Every chart was checked by eye on a contact sheet of crops with the centres drawn.
  Two are marginal: RGT_4336 chart 2 (tilted) and RGT_4376 chart 3 (small; its first grey patch
  is annotated outside the chart and is dropped).

The shifts are geometry only: no colour value is fitted to the charts, and no correction sees them.

### Methods

All in linear camera RGB from the registered RAW, with the SQUID stereo range map:

| Method | What it does |
|---|---|
| `raw` | No white balance |
| `camera_wb` | The camera's recorded white-balance multipliers |
| `grey_world` | One global grey-world white balance, no range |
| `backscatter` | Backscatter `B(d) = B∞ (1 − e^(−b d))` per channel, fitted to the darkest 1% of pixels in 12 range bins, subtracted; then grey-world |
| `range` | As `backscatter`, then attenuation `e^(−β d)` per channel, fitted log-linearly to the mean remaining signal per range bin, divided out; then grey-world |
| `seathru` | Sea-thru's backscatter form `B∞ (1 − e^(−b d)) + J′ e^(−b′ d)` per channel, fitted to the same dark pixels, subtracted; then grey-world. The second term carries the direct light the darkest pixels still reflect |

### Measures

- **Angle to grey** (SQUID's measure): the RGB angle between each of the six grey-ramp patches
  (5×5 median) and pure grey, averaged per chart. It is blind to haze: backscatter adds a tinted
  offset, and a grey patch plus a tinted offset is grey again after a global white balance.
- **Ramp contrast**: (white − black) / (white + black), mean over channels. Haze lowers it; a
  global white balance cannot change it.
- **Chart pair angle**: the angle between the full patch vectors (18 patches × RGB) of two
  identical charts in one image, averaged over pairs.

### Results (15 charts, 5.8–18.9 m)

| Image | Chart | Range (m) | Angle, TIF (°) | Angle, grey-world (°) | Angle, backscatter (°) | Contrast, raw | Contrast, backscatter |
|---|---|---|---|---|---|---|---|
| RGT_4318 | 0 | 5.8 | 38.5 | 1.0 | 27.1 | 0.388 | 0.904 |
| RGT_4376 | 0 | 6.9 | 37.9 | 1.6 | 5.0 | 0.411 | 0.825 |
| RGT_4318 | 1 | 7.7 | 38.3 | 0.9 | 27.0 | 0.341 | 0.916 |
| RGT_4376 | 1 | 8.8 | 37.9 | 1.5 | 4.7 | 0.297 | 0.698 |
| RGT_4336 | 1 | 10.3 | 38.4 | 1.4 | 2.2 | 0.180 | 0.247 |
| RGT_4376 | 2 | 10.4 | 38.0 | 1.4 | 4.4 | 0.263 | 0.581 |
| RGT_4318 | 2 | 10.8 | 38.6 | 0.6 | 16.4 | 0.221 | 0.803 |
| RGT_4336 | 0 | 10.9 | 38.1 | 0.5 | 0.7 | 0.168 | 0.241 |
| RGT_4381 | 0 | 14.5 | 38.1 | 0.6 | 0.9 | 0.147 | 0.228 |
| RGT_4382 | 0 | 14.7 | 38.2 | 1.6 | 3.1 | 0.156 | 0.305 |
| RGT_4336 | 2 | 15.2 | 38.1 | 1.4 | 1.4 | 0.088 | 0.121 |
| RGT_4381 | 1 | 18.3 | 38.4 | 0.7 | 1.1 | 0.075 | 0.129 |
| RGT_4376 | 3 | 18.3 | 40.8 | 4.4 | 21.3 | — | — |
| RGT_4382 | 1 | 18.8 | 38.4 | 1.8 | 3.3 | 0.092 | 0.253 |
| RGT_4318 | 3 | 18.9 | 39.6 | 1.8 | 4.8 | 0.068 | 0.387 |

RGT_4376 chart 3 has no contrast value: its white patch is the one dropped.

| Method | Angle, median (°) | Angle, mean (°) | Contrast, mean | Contrast, slope per metre | Chart pair angle, mean over 5 images (°) |
|---|---|---|---|---|---|
| TIF as published | 38.27 | 38.48 | 0.170 | −0.021 | 3.3 |
| `raw` | 31.32 | 31.25 | 0.207 | −0.024 | 4.0 |
| `camera_wb` | 31.09 | 31.01 | 0.207 | −0.024 | 4.0 |
| `grey_world` | 1.37 | 1.41 | 0.207 | −0.024 | 4.0 |
| `backscatter` | 4.38 | 8.21 | 0.474 | −0.052 | 9.2 |
| `range` | 3.39 | 7.55 | 0.474 | −0.053 | 9.0 |
| `seathru` | 4.68 | 6.76 (3 grey patches subtracted to zero, not scored) | 0.487 | −0.065 | 12.6 |

The chart pair angle per image (grey-world against backscatter): RGT_4336 2.6 / 3.7, RGT_4376
6.1 / 17.3, RGT_4381 2.5 / 3.7, RGT_4382 2.2 / 3.2, RGT_4318 6.4 / 17.9.

### Findings

1. **A global white balance on the RAW makes the grey patches grey at every range**: median 1.4°,
   no trend with range (+0.08° per metre). Over 6–19 m on this site, the colour cast is
   nearly one global tint. SQUID's grey-patch measure cannot show what range-based correction
   adds.
2. **Haze is the range effect that remains.** Uncorrected, the ramp contrast falls from 0.39–0.41
   at 6–7 m to 0.07–0.09 at 18–19 m. No white balance changes it.
3. **Removing backscatter recovers contrast, about 2.3 times on average**: 0.90 at 5.8 m and 0.39
   at 18.9 m on RGT_4318, against 0.39 and 0.07 uncorrected. It does not equalise contrast across
   range, and its contrast falls more steeply per metre than uncorrected, since it raises the near
   charts most.
4. **The backscatter fit as built tints the near charts**: 27° on RGT_4318's 5.8 and 7.7 m
   charts, and identical charts disagree more (chart pair angle 9.2° against 4.0°). The dark-pixel
   estimate is fragile on this scene. The deck holds few dark objects, and the per-bin dark
   levels jump (RGT_4318 green: 0.091, 0.099, 0.141, 0.078 over the first four bins).
   Against each chart's black patch, an upper bound on backscatter, the fitted backscatter
   reaches 105–108% in red and green but 73–82% in blue on RGT_4318's 5.8 and 7.7 m charts. The
   channels are mis-balanced, and that leaves the tint. On the other four images it stays at
   29–89% of the black patch in every channel.
5. **The attenuation step adds nothing measurable**: the fit returns β = 0 for every channel on
   two of five images (RGT_4336, RGT_4381) and near zero on a third (RGT_4318); contrast is
   unchanged against backscatter alone.
6. **Sea-thru's backscatter form does not fix it.** Checked against each chart's black patch, an
   upper bound on backscatter that no fit sees, the simple fit is over it on two charts (1.06 and
   1.08, both RGT_4318) and Sea-thru's form on three (1.05–1.26, the three nearest charts of
   RGT_4318 and RGT_4376). Three grey patches are subtracted to zero and identical charts
   disagree more (chart pair angle 12.6° against 9.2°). The model form is not the problem; the
   premise is: near the camera this deck holds no dark objects, so the darkest 1% of pixels per
   range bin are not dark, and any curve through them overestimates backscatter there.

The answer for Recce, so far: on this water and range span, a global white balance from the RAW
already holds colour; haze is what range-based correction has to remove; and a backscatter fit
from the image alone removes it unevenly, whichever model is fitted. A known dark target in the
scene (a chart's black patch at several ranges, as the
[benchmark spec](../../docs/wip/underwater-benchmark-spec.md) places) gives the fit what the image
cannot; on SQUID that would score the correction on the targets that built it, so it waits for a
set with more targets than it scores on.

### Not covered

- **Ranges come from SQUID's stereo, not from our reconstruction**, which the criterion asks for;
  ours fail on this data (next section).
- Five images, one site (Satil), 15 charts. Katzaa, Michmoret and Nachsholim are not downloaded.
- Only the grey ramp and patch vectors are compared; the colour patches have no reference values
  (the DGK chart's published colour values are not used).
- Sea-thru's backscatter form is tried; its local space average illuminant (per-pixel
  attenuation from the neighbourhood) is not. With backscatter already overestimated near the
  camera, an attenuation estimate built on top of it inherits the error.
- The TIF linearity check is on one image (LFT_3875) and the green channel; red had too little
  signal to fit (correlation 0.52).
- The registration's 1.2–1.4 px residual is at TIF scale; on far charts a patch is about 5 px wide,
  so samples may touch patch edges there despite the shift.
- The annotation shifts were checked by eye, not against an independent detection.
- RGT_4384, RGT_4388 and RGT_4351 have no annotated charts and are not used.

### Ranges from our reconstruction

```
uv run python recon.py prep                                         # 16 PNGs
uv run --project ../RC-P1-registration python recon.py register     # pycolmap, CPU
./run_dense.sh                                                      # RC-P2 HIP container, X3
uv run python recon.py ranges                                       # depth -> range, vs SQUID
```

All 16 Satil images (8 stereo pairs) are registered together, left and right each with one
shared SIMPLE_PINHOLE camera (the images are already undistorted), from a focal prior of
2,661 px. That is the in-air focal length of the NEFs' Nikon D810 and 35 mm lens at this image
scale. Dense depth is COLMAP PatchMatch with geometric consistency at full size.

- **Registration:** the sets barely overlap. Left and right of one set match well (164–3,603
  verified matches); across sets only 03 with 04 match well (579–1,303), the rest under 70.
  With the default 16° initial triangulation angle only sets 03+04 form a model; at 2° sets
  02+06 do too. Sets 01, 05, 07 and 08 register
  in no model, so their right images (RGT_4336 among them, with 3 charts) get no range.
- **Focal length:** bundle adjustment moves it from 2,661 to 3,637–4,008 px (1.37–1.51 times
  the in-air value) on both models. A flat port would give about 1.33 times; which port SQUID
  used is not verified.
- **Dense depth fails.** Geometric consistency keeps 0.0% of pixels on sets 03/04 and
  0.4–1.1% on 02/06; fusion yields 0 points. The photometric maps fill 98.5–100% of pixels,
  but they do not follow SQUID's ranges: Spearman correlation −0.07 to 0.22, 5–8% of pixels
  within 10% after the best single scale. Where geometric depth exists, it differs from
  SQUID's by a median 5.6–21% after scaling, and the two images of one model need scales 0.157
  and 0.257, so the model's own scale is not consistent either.

So the colour comparison has no ranges of ours to run on. For Recce this says: a stereo pair
(or a few hazy, barely overlapping pairs) is not a multi-view capture set. Without the rig's
calibration (baseline, rectification), the general SfM and PatchMatch route gives no depth
here, where SQUID's calibrated stereo does. A capture underwater needs either many overlapping
views or a calibrated rig with a stereo-matching path.

## AquaMVS refraction

```
uv run python aquamvs.py     # writes runs/p12/aquamvs.json, prints the tables below
```

The rig is 12 cameras above a flat water surface looking down at a submerged 12 x 9 ChArUco
board of 60 mm squares; 8 held-out frames (not used in calibration). For each model, AquaMVS's
2-D corner detections through that model's calibration are triangulated here: every camera
that sees a corner casts a ray, straight for the pinhole calibration (`n_water` 1.0), bent at
the water surface by Snell's law for the refractive one (`n_water` 1.333, surface at
z = 1.0306 m), and the corner is the least-squares point nearest all its rays. Corners seen by
fewer than two cameras are skipped.

- **The pixels are on AquaMVS's undistorted images**, whose camera matrix is OpenCV's
  `getOptimalNewCameraMatrix(K, dist, alpha=0)`, not the calibration's `K`. With `K`, the rays
  of different cameras missed each other by 11 mm under both models. With the new matrix,
  AquaMVS's own 3-D corners lie on these rays (0.0 mm median in every camera), which checks
  the ray model against theirs. `opencv-python-headless` is in this prototype's environment
  for that one call (owner's approval, 2026-11-25).
- **Each calibration needs its own corner file.** The core's `modern_refractive` corners sit
  2–8 mm off the rays of the refractive calibration in `data.zip`; they belong to another
  refractive run. The refractive measurement uses the corners in `data.zip`.

| Model | Corners | Scale error (%) | Adjacent-corner error (mm) | Adjacent-corner RMS (mm) | Rigid RMSE (mm) | Ray spread (mm) |
|---|---|---|---|---|---|---|
| Pinhole | 654 | −1.496 | −1.009 | 1.470 | 5.83 | 0.85 |
| Refractive | 664 | +0.017 | +0.005 | 0.367 | 1.15 | 0.35 |

Scale error is the median over all corner pairs of measured over true distance, minus one,
averaged over frames. Adjacent-corner error compares neighbours 60 mm apart. Rigid RMSE is the
residual after a rotation and translation (no scale) of the board model onto the corners. Ray
spread is the RMS distance of a corner's rays from the triangulated point.

| Frame | Pinhole: scale (%) / rigid (mm) | Refractive: scale (%) / rigid (mm) |
|---|---|---|
| 1 | −3.24 / 14.56 | +0.11 / 1.21 |
| 2 | −0.13 / 1.58 | −0.13 / 0.75 |
| 3 | −1.32 / 4.49 | −0.07 / 0.78 |
| 4 | −4.83 / 15.09 | +0.28 / 2.38 |
| 6 | −1.01 / 3.71 | −0.07 / 0.62 |
| 7 | −1.25 / 4.44 | +0.17 / 1.30 |
| 8 | −0.15 / 1.38 | −0.15 / 1.13 |
| 9 | −0.03 / 1.42 | −0.02 / 1.01 |

### Findings

1. **Modelling refraction takes the scale error from −1.5% to +0.02%** and the board's shape
   error from 5.8 mm to 1.2 mm RMS. AquaMVS's published figures, from their dense-stage
   corners and a Umeyama fit, are −0.994% against +0.064% and 5.91 against 1.08 mm; the rigid
   figures agree with ours within 0.1 mm.
2. **The pinhole error depends on where the board is**: from −0.03% and 1.4 mm (frame 9) to
   −4.83% and 15.1 mm (frame 4), so a single error figure understates it. This fits a pinhole
   calibration absorbing refraction for some board positions and not others; which positions,
   and why, is not tested. The refractive model stays within ±0.28% and 2.4 mm on every frame.

### Not covered

- One rig, one water body (fresh water), one board; flat interface only. A camera in a
  housing behind a flat or dome port needs a different refraction model.
- The corners are AquaMVS's detections; detection itself (ChArUco, OpenCV's aruco module) is
  not re-run here.
- The calibrations are AquaMVS's; refractive calibration itself is not re-done.
- No reconstruction of ours (registration, dense) is run on AquaMVS images; the measurement is
  of the camera models, given their calibration.
