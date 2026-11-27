// The five mini-labs: synthetic by design, so every number is computed here from the state and the
// same module runs in the page and in Node (tutor_facts.mjs) for the tutor's facts.

const DEG = Math.PI / 180;
const r = (x, d = 2) => Math.round(x * 10 ** d) / 10 ** d;

function rng(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const hash01 = (a, b) => rng(a * 73856093 ^ b * 19349663)();

// ---------- 1. Baseline and triangulation ----------
const baseline = {
  id: "baseline",
  term: "Triangulation and the baseline trade-off",
  primer: "#triangulation-and-the-baseline-trade-off",
  controls: [
    { key: "B", label: "Baseline", unit: "m", min: 0.02, max: 4, step: 0.01, log: true },
    { key: "Z", label: "Distance to the point", unit: "m", min: 1, max: 40, step: 0.5 },
  ],
  start: { B: 0.1, Z: 20 },
  constants: { f: 3400, sigma_d: 0.5 },
  facts(s) {
    const { f, sigma_d } = this.constants;
    const sz = (s.Z * s.Z) / (f * s.B) * sigma_d;
    return {
      baseline_m: r(s.B), distance_m: r(s.Z, 1),
      focal_px: f, matching_error_px: sigma_d,
      parallax_deg: r(2 * Math.atan(s.B / (2 * s.Z)) / DEG, 2),
      depth_sigma_mm: r(sz * 1000, 0),
      depth_sigma_share_of_distance: r(sz / s.Z, 4),
      rule_parallax_too_small_deg: 2, rule_parallax_hard_to_match_deg: 40,
    };
  },
  actions: {
    widen: { kind: "lab", text: "Widen the baseline: step further sideways between the two photos.", set: (s) => ({ ...s, B: Math.min(4, s.B * 4) }) },
    closer: { kind: "lab", text: "Move closer to the point.", set: (s) => ({ ...s, Z: Math.max(1, s.Z / 2) }) },
    narrow: { kind: "lab", text: "Narrow the baseline, so the two photos look more alike.", set: (s) => ({ ...s, B: Math.max(0.02, s.B / 3) }) },
    arc: { kind: "capture", text: "Walk in an arc around the subject instead of turning on the spot." },
  },
  tutor(f) {
    if (f.parallax_deg < f.rule_parallax_too_small_deg)
      return { see: `The rays meet at ${f.parallax_deg}°; the point could sit anywhere in a long sliver.`,
        why: `Depth uncertainty grows with the square of distance and shrinks with baseline: here ${f.depth_sigma_mm} mm at ${f.distance_m} m.`,
        act: f.distance_m > 5 ? "closer" : "widen", watch: "The sliver shortens and the depth uncertainty falls." };
    if (f.parallax_deg > f.rule_parallax_hard_to_match_deg)
      return { see: `The rays meet at ${f.parallax_deg}°: depth is sharp, but the two photos look very different.`,
        why: "A wide baseline triangulates well and matches badly: features change appearance and overlap shrinks.",
        act: "narrow", watch: "The angle drops toward 10–30°, where both matching and depth hold." };
    return { see: `The rays meet at ${f.parallax_deg}°, depth to ${f.depth_sigma_mm} mm.`,
      why: "Between the two limits: enough parallax for depth, views alike enough to match.",
      act: "arc", watch: "Every point keeps a few photos at this kind of angle." };
  },
};

// ---------- 2. Overlap and match count ----------
const WALL = 20, FOOT = 2, STANDOFF = 3, REPEAT = 0.7, JOIN = 50;
function wallFeatures(density) {
  const g = rng(7), n = Math.round(density * WALL), xs = new Float32Array(n);
  for (let i = 0; i < n; i++) xs[i] = g() * WALL;
  return xs;
}
const overlap = {
  id: "overlap",
  term: "Overlap, parallax and angles",
  primer: "#overlap-parallax-and-angles",
  controls: [
    { key: "o", label: "Overlap between neighbours", unit: "%", min: 0, max: 90, step: 1 },
    { key: "d", label: "Texture", unit: "features per metre", min: 20, max: 400, step: 10 },
  ],
  start: { o: 40, d: 100 },
  constants: { wall_m: WALL, footprint_m: FOOT, standoff_m: STANDOFF, detection_repeatability: REPEAT, rule_matches_to_join: JOIN },
  run(s) {
    const xs = wallFeatures(s.d), step = FOOT * (1 - s.o / 100);
    const frames = Math.floor((WALL - FOOT) / step + 1e-9) + 1;
    const seen = (i, k) => xs[i] >= k * step && xs[i] <= k * step + FOOT && hash01(i + 1, k + 1) < REPEAT;
    const track = new Uint16Array(xs.length), links = [];
    for (let k = 0; k < frames; k++) {
      let m = 0;
      for (let i = 0; i < xs.length; i++) if (seen(i, k)) { track[i]++; if (k + 1 < frames && seen(i, k + 1)) m++; }
      if (k + 1 < frames) links.push(m);
    }
    return { xs, step, frames, track, links };
  },
  facts(s) {
    const { frames, track, links, step } = this.run(s);
    const sorted = [...links].sort((a, b) => a - b), seen = [...track].filter((t) => t > 0);
    return {
      overlap_pct: s.o, features_per_m: s.d, frames,
      step_m: r(step), neighbour_parallax_deg: r(2 * Math.atan(step / (2 * STANDOFF)) / DEG, 1),
      matches_min: sorted[0] ?? 0, matches_median: sorted[sorted.length >> 1] ?? 0,
      broken_links: links.filter((m) => m < JOIN).length,
      share_of_features_in_3_or_more_frames: r(track.filter((t) => t >= 3).length / track.length, 3),
      mean_track_length: r(seen.reduce((a, b) => a + b, 0) / Math.max(1, seen.length), 2),
      ...this.constants,
    };
  },
  actions: {
    more_overlap: { kind: "lab", text: "Shoot with more overlap: smaller steps between photos.", set: (s) => ({ ...s, o: Math.min(90, Math.max(80, s.o + 30)) }) },
    less_overlap: { kind: "lab", text: "Shoot with less overlap: fewer photos, more baseline each.", set: (s) => ({ ...s, o: Math.max(60, s.o - 15) }) },
    texture: { kind: "lab", text: "Give the wall more texture (or pick a textured subject).", set: (s) => ({ ...s, d: Math.min(400, s.d * 3) }) },
    pattern: { kind: "capture", text: "Add texture to a blank surface: tape, a projected pattern or targets." },
  },
  tutor(f) {
    if (f.broken_links > 0)
      return { see: `${f.broken_links} of ${f.frames - 1} neighbour pairs share fewer than ${f.rule_matches_to_join} matches; the chain breaks there.`,
        why: `At ${f.overlap_pct}% overlap neighbours share little wall, and only ${f.detection_repeatability * 100}% of features are found again in each photo.`,
        act: f.overlap_pct < 60 ? "more_overlap" : "texture", watch: "Every link turns solid and no pair drops under the line." };
    if (f.overlap_pct > 85)
      return { see: `${f.frames} photos with ${f.neighbour_parallax_deg}° between neighbours.`,
        why: "Much more overlap adds photos without adding geometry: the baseline between neighbours shrinks.",
        act: "less_overlap", watch: "Fewer photos, every link still above the line." };
    return { see: `Every link holds; a feature is seen by ${f.mean_track_length} photos on average.`,
      why: "Enough shared wall for matches, enough step for parallax.",
      act: "pattern", watch: "On blank walls the same overlap gives far fewer matches; try lowering the texture." };
  },
};

// ---------- 3. Blur and features ----------
const IW = 192, IH = 128;
let baseImg = null, noiseField = null, refKeys = null;
function makeBase() {
  const g = rng(11), img = new Float32Array(IW * IH).fill(0.45);
  for (let n = 0; n < 34; n++) {
    const x0 = g() * IW, y0 = g() * IH, w = 6 + g() * 40, h = 6 + g() * 30, v = 0.1 + g() * 0.8;
    for (let y = Math.max(0, y0 | 0); y < Math.min(IH, y0 + h); y++)
      for (let x = Math.max(0, x0 | 0); x < Math.min(IW, x0 + w); x++) img[y * IW + x] = v;
  }
  noiseField = new Float32Array(IW * IH);
  for (let i = 0; i < noiseField.length; i++) noiseField[i] = Math.sqrt(-2 * Math.log(g() + 1e-12)) * Math.cos(2 * Math.PI * g());
  return img;
}
function blur(img, sigma) {
  if (sigma < 0.05) return img.slice();
  const rad = Math.ceil(3 * sigma), k = [];
  let sum = 0;
  for (let i = -rad; i <= rad; i++) { const v = Math.exp(-(i * i) / (2 * sigma * sigma)); k.push(v); sum += v; }
  const tmp = new Float32Array(img.length), out = new Float32Array(img.length);
  const at = (a, x, y) => a[Math.min(IH - 1, Math.max(0, y)) * IW + Math.min(IW - 1, Math.max(0, x))];
  for (let y = 0; y < IH; y++) for (let x = 0; x < IW; x++) { let v = 0; for (let i = -rad; i <= rad; i++) v += k[i + rad] * at(img, x + i, y); tmp[y * IW + x] = v / sum; }
  for (let y = 0; y < IH; y++) for (let x = 0; x < IW; x++) { let v = 0; for (let i = -rad; i <= rad; i++) v += k[i + rad] * at(tmp, x, y + i); out[y * IW + x] = v / sum; }
  return out;
}
function harris(img) {
  const R = new Float32Array(IW * IH), keys = [];
  const ix = (x, y) => (img[y * IW + x + 1] - img[y * IW + x - 1]) / 2, iy = (x, y) => (img[(y + 1) * IW + x] - img[(y - 1) * IW + x]) / 2;
  for (let y = 3; y < IH - 3; y++) for (let x = 3; x < IW - 3; x++) {
    let a = 0, b = 0, c = 0;
    for (let v = -2; v <= 2; v++) for (let u = -2; u <= 2; u++) { const gx = ix(x + u, y + v), gy = iy(x + u, y + v); a += gx * gx; b += gy * gy; c += gx * gy; }
    R[y * IW + x] = a * b - c * c - 0.04 * (a + b) ** 2;
  }
  for (let y = 5; y < IH - 5; y++) for (let x = 5; x < IW - 5; x++) {
    const v = R[y * IW + x];
    if (v < 1e-3) continue;
    let max = true;
    for (let dy = -2; dy <= 2 && max; dy++) for (let dx = -2; dx <= 2; dx++) if ((dx || dy) && R[(y + dy) * IW + x + dx] >= v) { max = false; break; }
    if (max) keys.push([x, y]);
  }
  return keys;
}
const features = {
  id: "features",
  term: "Keypoints, and sharpness",
  primer: "#sharpness",
  controls: [
    { key: "blur", label: "Blur (shake or focus)", unit: "px", min: 0, max: 4, step: 0.1 },
    { key: "noise", label: "Noise (high ISO)", unit: "", min: 0, max: 0.1, step: 0.005 },
  ],
  start: { blur: 2, noise: 0 },
  constants: { image_px: `${IW} by ${IH}`, detector: "Harris corners, 5 by 5 window, fixed threshold", repeat_radius_px: 2 },
  image(s) {
    if (!baseImg) { baseImg = makeBase(); refKeys = harris(baseImg); }
    const out = blur(baseImg, s.blur);
    if (s.noise > 0) for (let i = 0; i < out.length; i++) out[i] += s.noise * noiseField[i];
    return out;
  },
  run(s) {
    const img = this.image(s), keys = harris(img);
    const rep = keys.filter(([x, y]) => refKeys.some(([u, v]) => (u - x) ** 2 + (v - y) ** 2 <= 4)).length;
    return { img, keys, rep, ref: refKeys };
  },
  facts(s) {
    const { keys, rep, ref } = this.run(s);
    return {
      blur_px: s.blur, noise_sigma: s.noise,
      keypoints_sharp_clean: ref.length, keypoints: keys.length, keypoints_repeatable: rep,
      repeatable_share_of_sharp: r(rep / ref.length, 3),
      spurious_keypoints: keys.length - rep, ...this.constants,
    };
  },
  actions: {
    faster_shutter: { kind: "lab", text: "Use a faster shutter (or steady the camera): less blur.", set: (s) => ({ ...s, blur: Math.max(0, s.blur - 2) }) },
    raise_iso: { kind: "lab", text: "Raise the ISO to afford the faster shutter: some noise.", set: (s) => ({ ...s, noise: Math.min(0.1, s.noise + 0.03) }) },
    less_noise: { kind: "lab", text: "Lower the ISO: more light, or a tripod and a slower shutter.", set: (s) => ({ ...s, noise: Math.max(0, s.noise - 0.03) }) },
    refocus: { kind: "capture", text: "Check focus on the subject before the next photo." },
    drop_blurred: { kind: "engine", text: "Flag blurred photos before matching and leave them out." },
  },
  tutor(f) {
    if (f.repeatable_share_of_sharp < 0.5)
      return { see: `${f.keypoints_repeatable} of the ${f.keypoints_sharp_clean} corners of the sharp image are still found.`,
        why: `Blur of ${f.blur_px} px flattens the corners the detector needs; a photo like this adds little to matching.`,
        act: f.blur_px > 0.5 ? "faster_shutter" : "drop_blurred", watch: "The share of corners found again climbs back toward all of them." };
    if (f.spurious_keypoints > f.keypoints_repeatable * 0.3)
      return { see: `${f.spurious_keypoints} corners appear that the sharp image does not have.`,
        why: "Noise creates corners that are not on the object; they will not match in the next photo.",
        act: "less_noise", watch: "Spurious corners fall as noise falls; the true ones stay." };
    return { see: `${Math.round(f.repeatable_share_of_sharp * 100)}% of the sharp image's corners are found again.`,
      why: "Noise costs less than blur: corners survive some noise, few survive blur.",
      act: "raise_iso", watch: "Compare: blur 2 px loses more corners than noise 0.03." };
  },
};

// ---------- 4. Rolling shutter ----------
const rolling = {
  id: "rolling",
  term: "Rolling shutter",
  primer: "#rolling-shutter",
  controls: [
    { key: "w", label: "Pan speed", unit: "°/s", min: 0, max: 90, step: 1 },
    { key: "t", label: "Readout time", unit: "ms", min: 0, max: 33, step: 1 },
  ],
  start: { w: 60, t: 25 },
  constants: { focal_px: 3000, image_rows: 3000 },
  facts(s) {
    const { focal_px: f, image_rows: H } = this.constants;
    const shift = s.w * DEG * (s.t / 1000) * f;
    return {
      pan_deg_per_s: s.w, readout_ms: s.t, ...this.constants,
      top_to_bottom_shift_px: r(shift, 1), vertical_lean_deg: r(Math.atan(shift / H) / DEG, 2),
      rule_shift_matters_px: 1,
    };
  },
  actions: {
    slow_pan: { kind: "lab", text: "Pan slower, or stop for each photo.", set: (s) => ({ ...s, w: Math.max(0, Math.round(s.w / 6)) }) },
    global_shutter: { kind: "lab", text: "Use a mechanical or global shutter (no readout skew).", set: (s) => ({ ...s, t: 0 }) },
    stills: { kind: "capture", text: "Take stills, not video, where the camera allows." },
    model_rs: { kind: "engine", text: "Model the rolling shutter in bundle adjustment (a pose per row band)." },
  },
  tutor(f) {
    if (f.top_to_bottom_shift_px > f.rule_shift_matters_px)
      return { see: `Verticals lean ${f.vertical_lean_deg}°: the bottom row sees the scene ${f.top_to_bottom_shift_px} px from where the top row did.`,
        why: `The rows are read over ${f.readout_ms} ms while the camera turns ${f.pan_deg_per_s}°/s, so each row has its own pose.`,
        act: f.pan_deg_per_s > 10 ? "slow_pan" : "global_shutter", watch: "The poles stand straight and the shift drops under a pixel." };
    return { see: `The shift is ${f.top_to_bottom_shift_px} px, under a pixel.`,
      why: "Slow enough, or read fast enough, that one pose fits every row.",
      act: "stills", watch: "Video keeps the camera moving; check it there." };
  },
};

// ---------- 5. Refraction and focal length (flat port) ----------
const refraction = {
  id: "refraction",
  term: "Refraction at the port",
  primer: "#refraction-at-the-port",
  controls: [
    { key: "n", label: "Refractive index outside", unit: "", min: 1, max: 1.4, step: 0.01 },
    { key: "a", label: "Half field of view in air", unit: "°", min: 5, max: 45, step: 1 },
  ],
  start: { n: 1.33, a: 35 },
  constants: { pupil_to_port_mm: 30 },
  facts(s) {
    const ta = s.a * DEG, tw = Math.asin(Math.sin(ta) / s.n), d = this.constants.pupil_to_port_mm;
    const mEdge = Math.tan(ta) / Math.tan(tw);
    return {
      index: s.n, half_field_air_deg: s.a, half_field_water_deg: r(tw / DEG, 1),
      focal_factor_centre: s.n, focal_factor_edge: r(mEdge, 3),
      edge_mismatch_pct: r((mEdge / s.n - 1) * 100, 1),
      viewpoint_spread_mm: r(d * (mEdge - s.n), 1), ...this.constants,
    };
  },
  actions: {
    dome: { kind: "capture", text: "Use a dome port with the lens's entrance pupil at its centre." },
    model_port: { kind: "engine", text: "Model the port's refraction explicitly instead of a pinhole with distortion." },
    calibrate_wet: { kind: "capture", text: "Calibrate in the water, through the same port." },
    narrow: { kind: "lab", text: "Use only the centre of the image (a narrower field).", set: (s) => ({ ...s, a: 15 }) },
  },
  tutor(f) {
    if (f.index > 1.01 && Math.abs(f.edge_mismatch_pct) > 1)
      return { see: `The centre behaves like a lens ${f.focal_factor_centre} times longer; the edge like one ${f.focal_factor_edge} times longer.`,
        why: `No single focal length fits both: ${f.edge_mismatch_pct}% apart, and the rays no longer meet in one point (${f.viewpoint_spread_mm} mm spread). A pinhole model bends the result.`,
        act: "model_port", watch: "With refraction modelled, scale holds across the image (RC-M7: within 0.28% against 4.8% off)." };
    return { see: `Centre and edge agree to ${f.edge_mismatch_pct}%.`,
      why: f.index <= 1.01 ? "In air nothing bends at the port." : "Near the centre the bend is close to a plain zoom.",
      act: "dome", watch: "Widen the field again and the mismatch grows." };
  },
};

export const LABS = [baseline, overlap, features, rolling, refraction];
export { IW, IH, WALL, FOOT, JOIN };
