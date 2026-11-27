# RC-M7 — Underwater

**Shows:** what water does to a capture and what correcting it buys, made visible (idea 8): the
water's colour against corrected colour, and refraction as a lens of water that can be switched
off. Both halves run on RC-P12's measurements.

- **Colour in water (SQUID, Satil).** One image, two corrections side by side with a wipe: as the
  camera saw it (the RAW with the camera's white balance), the water's colour removed (one white
  balance), haze removed (backscatter fitted by range and subtracted), and haze plus loss with
  range. The charts carry their range, angle to grey and contrast for the side they are on; a
  table compares both sides. The range of every pixel (SQUID's stereo) can be laid over the
  image and read under the pointer; pixels with no range are left uncorrected and the page says
  so.
- **What the water adds, by range.** The backscatter fit per channel against the darkest pixels
  it was fitted to, with each chart's black patch as an upper bound no fit sees. Where the curve
  rises above a black patch, the fit removes more light than is there.
- **The water lens (AquaMVS).** The 13-camera rig over a flat water surface and the submerged
  board, each camera as its photo of the chosen frame. The switch turns the refraction model on
  (rays bend at the surface, n = 1.333) or off (straight rays, the pinhole calibration). The
  board is drawn where each model's corners put it; each corner's miss is drawn exaggerated
  (×3 by default) and coloured at true size. Click a corner to follow its rays; per-frame
  scale-error bars compare both models.
- **A verdict by rule** on each half, over the measured numbers, stated beside it.

No AI layer: the verdicts come from the numbers alone, and nothing on this page needs an agent to
read it (pattern "AI is a layer, never a dependency").

The frame follows RC-M1 to RC-M6. One new colour, water (a teal), marks the surface, the
refractive model and the water's veil; the pinhole model is the orange used for "the other
recipe" in RC-M4.

## What the data says

All numbers are RC-P12's (2026-11-26); the page reads them, it measures nothing new.

**Colour (RGT_4318, 4 charts at 5.8–18.9 m).** One white balance takes the grey patches from
30.8° to 1.0° (median) at every range: the water's tint is one global cast here. Removing
backscatter raises chart contrast from 0.25 to 0.75 (mean), which no white balance can do, but it
tints the three nearest charts (27°, 27°, 16° from grey), where the fit removes more light than
the black patch reflects (1.06× and 1.08×). The plot shows why: near the camera the scene holds
no dark pixels, so the darkest 1% per range bin are not dark.

**Refraction (8 held-out frames).** With the water lens on, every frame's scale is within ±0.28%
and its shape within 2.4 mm (rigid RMSE). Off, the board measures up to 4.8% small and 15.1 mm out
of shape (frame 4), and how much depends on where the board is: frame 9 is 0.03% off. In frame 4
the pinhole corners are squeezed along one board axis; drawn ×10 the rows collapse into a line,
so the page defaults to ×3.

**The frame mapping was checked.** Corner frame k is the k-th frame PNG per camera in AquaMVS's
`data.zip`; frame 4's pinhole corners projected into camera e3v829d's raw frame 4 land on the
board's corners (overlay written to `data/aquamvs/check_frame4_e3v829d.jpg`, read by eye).

## Data

| Shown | Status |
|---|---|
| SQUID images under each method | Real: RC-P12's `colour.py` methods re-run on the RAW (`squid_raw.py` registration), exposed for display |
| Chart ranges, angles, contrast, black-patch ratio | Real: RC-P12's `colour_squid.json` |
| Ranges per pixel | Real: SQUID's stereo range maps |
| Backscatter fit, darkest pixels | Real: re-fitted by RC-P12's `fit_backscatter` in the export |
| AquaMVS rig, photos, corners, rays | Real: AquaMVS calibrations and corner detections, rays and triangulation by RC-P12's `aquamvs.py` |
| Per-frame and summary errors | Real: RC-P12's `aquamvs.json` |
| Board drawn per model | Rigid fit of the board to that model's corners (RC-P12's Umeyama) |
| Verdicts | **Rules written for the mock-up**, over those numbers |
| Exaggeration of misses | **Display only**, labelled on the view |

SQUID is CC BY-NC-SA 4.0 and stays on this machine; AquaMVS is CC BY 4.0. Both live in the
gitignored `data/`.

## Run

```bash
cd prototypes/RC-P12-underwater
uv run python ../../mockups/RC-M7-underwater/export_underwater.py \
  ../../mockups/RC-M7-underwater/data
cd ../../mockups/RC-M7-underwater
python3 -m http.server 8798 --bind 0.0.0.0
```

Open <http://127.0.0.1:8798/>. A view is a link: `?img=RGT_4318`, `&l=` and `&r=` (`camera_wb`,
`grey_world`, `backscatter`, `range`), `&split=0.4`; `?tab=lens&lens=0&frame=4&ex=3`;
`&theme=light`.

| File | Does |
|---|---|
| `export_underwater.py` | SQUID method images, ranges, charts and fits; the AquaMVS rig, corners and rays per model and frame; camera photos |
| `index.html` | The page: colour in water, and the water lens |

## Verdict

Phase 1, built 2026-11-27. Waiting for the owner's verdict.

| Concept | Idea |
|---|---|
| The wipe between the water's colour and a correction | 8 |
| Charts scored on the image, per side | 8 |
| The range of every pixel, laid over and read under the pointer | 8 |
| What the water adds by range, with the black-patch bound | 8 |
| The water lens switch: rays bent or straight, the board where each model puts it | 8 |
| Each corner's miss, exaggerated and coloured at true size | 8 |
| Verdicts by rule | 8, pattern |

## Not covered

- **Ranges are SQUID's stereo, not ours.** RC-P12's own reconstruction gave no depth on SQUID, so
  this page shows correction on ranges Recce could not produce for this data.
- **No 3D for the colour half.** The image is not lifted into a relief or point cloud.
- **Five SQUID images, one site; one AquaMVS rig, fresh water, a flat surface.** A housing behind a
  flat or dome port, or salt water, is not shown.
- **The refractive model is AquaMVS's calibration.** Recce does not calibrate it; the switch
  shows two given calibrations, not one camera with the lens toggled in software.
- **Display exposure** is set per image (its 99.5th luminance at 0.95), so brightness between
  methods is not comparable; the chart numbers are.
- **Screenshots only on the X3** (headless Chromium); not opened on the M4 Pro or a phone.
