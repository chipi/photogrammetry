# RC-M5 — Learn

**Shows:** mini-labs beside the terms of the
[photogrammetry primer](../../docs/reference/photogrammetry-primer.md) (idea 12), each with one or
two controls, and a tutor beside each lab (owner, 2026-11-27: AI as a coach, here as a tutor to a
learner). The five labs are the ones the catalogue names:

| Lab | Primer term | Controls | What moves |
|---|---|---|---|
| 1 | Triangulation and the baseline trade-off | baseline, distance | the region where two noisy rays can meet; `σZ ≈ Z²·σd / (f·B)` |
| 2 | Overlap, parallax and angles | overlap, texture | photos along a 20 m wall, matches per neighbour pair against a join line, photos per feature |
| 3 | Keypoints, and sharpness | blur, noise | Harris corners on a synthetic image: found again, lost, or spurious |
| 4 | Rolling shutter | pan speed, readout time | verticals leaning as rows are read while the camera turns |
| 5 | Refraction at the port | refractive index, field of view | rays through a flat port; centre and edge behave as different focal lengths and stop meeting in one point |

**The tutor.** Without AI, a rule reads the lab's numbers live and says what the learner sees,
why, one move to try next (with a "Try it" button that sets the controls) and what to watch.
With the person's own AI connected, a recorded answer per lab says the same in its own order,
with the moves from the lab's menu; every number it writes is checked against the fact it cites
(`../coach_lib.py`, shared with RC-M1, RC-M2 and RC-M7). Moves are marked "try in the lab",
"next capture" or "engine", so the lab points at what the idea means for a real capture. When
the learner has moved the controls away from the state the AI saw, the answer says so and offers
"Back to it".

The frame follows the other mock-ups (IBM Plex, the same tokens, dark with a light theme); the
reading text is IBM Plex Serif, since this page is read more than operated.

## Data

Synthetic by design (the plan in [visual ideas](../../docs/wip/visual-ideas.md)): nothing is
measured and no dataset is used. Every number comes from `labs.js`, one module that the page and
Node both run, so the tutor's facts are the page's own numbers.

| Shown | Status |
|---|---|
| Depth uncertainty, parallax | The primer's formula, f = 3400 px, 0.5 px matching error |
| Matches, broken links, photos per feature | A seeded simulation: features at random on a 20 m wall, each photo covers 2 m from 3 m, a feature is found again with chance 0.7, a pair joins with 50 matches (**the lab's rule**) |
| Corners found, lost, spurious | A seeded 192 by 128 image of rectangles, Gaussian blur and noise, Harris corners at a fixed threshold, matched to the sharp image's corners within 2 px |
| Shift and lean | `shift = ω · readout · f`, 3000 rows at f = 3000 px |
| Focal factors, mismatch, viewpoint spread | Snell's law through a thin flat port 30 mm from the pupil, rays traced back to the axis |
| The tutor without AI | **Rules written for the mock-up** (`labs.js`), over those numbers |
| The tutor with AI | **One recorded call per lab**, checked by `coach_lib.py` |

Drawing choices are labelled on the figure: the triangulation wedges are widened 5 times, and a
short baseline is stretched across (with its factor shown), which leaves the depth of the region
to scale.

## What the tutor did

The rule picks one move per lab: move closer (1), more overlap (2), a faster shutter (3), pan
slower (4), model the port (5). The AI tutor (Claude Sonnet, one call per lab with the facts and
the menu, no images, US$0.083 for the five) gave 3 to 4 moves per lab, ordered, with the lab
moves first and then what they mean for a real capture or the engine, and said what the lab
cannot say (in four of five, that the lab is synthetic and a real camera may differ). Of its 51
statements, 33 have every number checked, 15 are judgement and 3 are unsupported: each of the 3
repeats a true number ("3 or more frames", "50", "0") without citing it in that item, which the
rule counts against it.

| Lab | Statements | Supported | Judgement | Unsupported | Cost (US$) |
|---|---|---|---|---|---|
| 1 Triangulation | 10 | 8 | 2 | 0 | 0.016 |
| 2 Overlap | 10 | 6 | 2 | 2 | 0.017 |
| 3 Sharpness | 10 | 6 | 4 | 0 | 0.017 |
| 4 Rolling shutter | 11 | 6 | 4 | 1 | 0.016 |
| 5 Refraction | 10 | 7 | 3 | 0 | 0.017 |

## Run

```bash
cd mockups/RC-M5-learn
node tutor_facts.mjs data          # each lab's facts, moves and rule answer at its start state
python3 tutor.py data ai sonnet    # optional: the AI tutor (one call per lab)
python3 -m http.server 8799 --bind 127.0.0.1
```

Open <http://127.0.0.1:8799/>. A view is a link: `?lab=overlap` scrolls to a lab;
`&overlap=o:80,d:100` sets its controls (keys as in `labs.js`); `&ai=1`; `&theme=light`.

| File | Does |
|---|---|
| `labs.js` | The five labs: controls, start state, the numbers (facts), the menu of moves, the rule tutor |
| `index.html` | The page: the primer text, each lab's figure, controls and readouts, the tutor |
| `tutor_facts.mjs` | Writes `data/tutor_facts.json` from `labs.js` |
| `tutor.py` | The AI tutor per lab, through `../coach_lib.py` |

## Verdict

Phase 1, built 2026-11-27. **Kept: every concept is good to go as a prototype (owner, 2026-11-27).**

| Concept | Idea |
|---|---|
| A mini-lab beside each primer term, one or two controls | 12 |
| Readouts that name the formula or simulation behind them | 12, pattern |
| The tutor: what you see, why, a move to try, what to watch | pattern (owner, 2026-11-27) |
| Moves marked as lab, next capture or engine | pattern |

## Not covered

- **Synthetic only.** No lab runs on a real photo or a real reconstruction; a lab that loads one
  of the person's own photos (blur, corners) is a later step.
- **The primer is linked, not embedded.** The labs sit on their own page beside short excerpts;
  placing them inside the primer's own pages (the docs site) is not done.
- **The AI tutor answers one state per lab**, recorded; it does not answer the learner's own
  question or follow the controls. A live tutor needs the person's AI at run time.
- **The overlap lab is one row along a wall.** Side overlap, rings at several heights and the
  arc against turning on the spot are not simulated.
- **The refraction lab is a thin flat port.** Port thickness, a dome port and distance-dependent
  distortion are described, not drawn.
- **Text sizes:** figure labels and captions use the 11 px size the other mock-ups use as their
  floor; body text is 13 to 15 px.
- **Screenshots only on the X3** (headless Chromium at 1600 px and 390 px wide); not opened on
  the M4 Pro or a phone.
