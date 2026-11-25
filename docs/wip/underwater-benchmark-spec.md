# Open underwater benchmark: specification (2026-11-25)

RC-P12's last clause: specify the open underwater benchmark from what the public sets lack. This
page lists the gaps, each with the evidence that shows it, then the benchmark that closes them.
Numbers come from [RC-P12](https://github.com/chipi/recce/tree/main/prototypes/RC-P12-underwater)
and [public datasets](../reference/public-datasets.md), section "Underwater".

Recce starts from one case (see the [brief](../concept/RC-brief.md), "Where this comes from"):
1,500 Nikon D850 photos of an underwater site that would not assemble on a laptop in a day. A
benchmark that tests Recce underwater tests that case: a dive-scale set of high-resolution RAW
photos from a camera in a housing, with ground truth for scale, shape and colour.

## What the public sets offer

| Set | Views | Geometric ground truth | Colour reference | RAW | Port | Licence |
|---|---|---|---|---|---|---|
| AquaMVS Example 2 | 13-camera rig, 10 frames, lab | ChArUco board, 60 mm squares | None | No | Flat water surface, cameras in air | CC BY 4.0 |
| SQUID (4 sites) | 57 stereo pairs | Stereo range maps | DGK charts at several distances | Yes (NEF) | Not documented | CC BY-NC-SA 4.0 |
| Sea-thru (D1–D5) | About 1,100 images | Range maps from Metashape | Colour charts claimed, not checked | No (linear PNG at 0.3x) | Not checked | CC BY-NC-SA 4.0 |
| SeaThru-NeRF (4 scenes) | Not stated | COLMAP poses only | None (images white-balanced) | No | Not checked | Data licence not stated |
| Submerged3D | 4 scenes x 20 images, 720p | None | None | No | Not checked | CC BY 4.0 |

## What they lack

1. **Dive-scale multi-view sets with geometric ground truth.** AquaMVS has a board in a tank;
   SQUID has stereo pairs; Sea-thru's ranges come from Metashape, a reconstruction rather than a
   measurement. No set found has hundreds of overlapping views of a site with independent scale and
   shape truth. RC-P12 shows why this matters: on SQUID Satil the eight stereo pairs barely
   overlap, only two small models register, and our dense depth keeps 0–1.1% of pixels.
2. **Colour references across many views.** SQUID's charts sit in stereo pairs, so a correction
   can be scored but not built from a reconstruction of the same site; SeaThru-NeRF's images are
   already white-balanced. RC-P12 could not test range-based correction with ranges from our own
   reconstruction for this reason.
3. **Linear RAW with intact colour.** Sea-thru ships linear PNGs at 0.3x, without RAW. SQUID ships
   RAW, but its TIFs clip red to zero on 78–99.9% of pixels, so anyone who uses the TIFs measures
   37.9–40.8° from grey on every chart whatever their method does.
4. **Documented ports.** AquaMVS models a flat water surface with the cameras in air. SQUID does
   not document its housing; our registration refines the focal length to 1.37–1.51 times the
   in-air value, which points at a flat port but is not confirmed. No set documents a dome port
   and where the lens's entrance pupil sits in it, which decides whether a pinhole model holds.
   On AquaMVS a pinhole calibration is off by −0.03% to −4.8% in scale depending on where the
   board is, against at most ±0.28% for the refractive model.
5. **Readable calibration.** SQUID's calibration is a MATLAB `stereoParameters` object; its chart
   annotations sit a few pixels off its published undistorted images, because its evaluation
   undistorts on the fly. AquaMVS's corner pixels live on images undistorted with OpenCV's new
   camera matrix, not the calibration's `K`, which RC-P12 found only by reading their source.
6. **Size.** The largest set with range maps (Sea-thru, about 1,100 images) is at 0.3x resolution
   and its ranges come from a reconstruction. Recce's
   founding case is 1,500 full-resolution RAW photos; distribution (RC-P7) and memory limits only
   show at that size.
7. **A permissive licence with truth.** Of the sets with ground truth, only AquaMVS is CC BY; every
   set with colour references forbids commercial use.

## The benchmark

### Scenes

| Scene | What | Why |
|---|---|---|
| S1 Site | One wreck or reef site, 1,000–2,000 RAW photos with a DSLR in a housing behind a dome port, in overlapping passes at two or three distances | Gaps 1, 2, 6: Recce's founding case |
| S2 Flat port | A 100–200 photo subset of S1's area through a flat port | Gap 4: the same site under both port models |
| S3 Action camera | A GoPro pass over S1's area | The owner's second underwater camera; registration of mixed sets |
| S4 Calibration | A ChArUco board photographed through each port in the water, at three or more distances | Gaps 4, 5: in-water calibration with its own truth, as AquaMVS does in a tank |
| S5 Dive set | The friend's dive set with its Metashape result, if the friend agrees to publish it | A real-world baseline against the commercial tool |

### Ground truth placed at the site

- **Scale bars:** two or more rigid bars with coded targets at a measured distance (tape or
  caliper, measured on land), seen from many views. Scored as scale error, as in RC-P9 and RC-P12.
- **Target network:** six or more coded targets whose pairwise distances are taped underwater,
  giving a shape check independent of any reconstruction.
- **Colour charts:** three or more identical charts at 1, 3 and 6 m from the main pass's camera
  path. Their patch values are measured above water under a known illuminant. This gives SQUID's
  test (charts at several ranges) in many overlapping views (gap 2).
- **Port record:** port type and dimensions, and the lens's entrance pupil position relative to the
  dome centre, measured on land.

### Measures

Every measure already exists in a prototype, so the benchmark adds no new scoring code.

| Measure | From |
|---|---|
| Registration rate, time and cost | RC-P1, RC-P7 |
| Scale error on the scale bars; target-distance error; rigid RMSE | RC-P9, RC-P12 (AquaMVS) |
| Dense and mesh accuracy against the target network | RC-P4 |
| Grey-ramp angle to grey, ramp contrast against range, chart-pair angle | RC-P12 (SQUID) |
| Splat quality on held-out views | RC-P4 |

### Format

- RAW files as they come from the camera, EXIF untouched; no derived TIFs in the release.
- Calibration as plain JSON in OpenCV's convention (`K`, distortion, `R`, `t`, port parameters),
  readable without MATLAB.
- Target and chart annotations in the pixel grid of the RAW files, with the code that produced
  them, so no annotation depends on an undistortion step the user cannot repeat.
- Measured distances and chart patch values as CSV, with the instrument and its stated accuracy.
- Licence CC BY 4.0 for the owner's own captures; S5 under whatever the friend agrees to.

## Open, for the owner

- Whether to capture S1–S4, and when: one or two dives, plus a pool session for S4.
- The licence for the owner's captures; CC BY 4.0 is the proposal.
- Whether the friend's dive set (S5) can be published, or stays a private baseline.
- Whether RC-P12's "ranges from the reconstruction" clause moves to S1, where it can be met.
