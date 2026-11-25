"""RC-P12 colour: does range-based correction (backscatter and attenuation, Sea-thru-like) do
what a global white balance cannot on SQUID's colour charts?

Input is SQUID Satil (non-commercial: develop only, never redistribute). Right-camera images
only, since only they have chart annotations (from SQUID's evaluation code). Three measures per
chart:
  angle        SQUID's own: the RGB angle between each grey-ramp patch (5x5 median) and pure
               grey, averaged over the six patches
  contrast     (white - black) / (white + black) of the ramp, mean over channels; haze lowers it
  chart pair   the angle between the full patch vectors of two identical charts in one image

Methods, all in linear camera RGB from the NEF registered to the undistorted TIF (squid_raw.py):
  raw          no white balance
  camera_wb    the camera's recorded white balance multipliers
  grey_world   one global grey-world white balance
  backscatter  backscatter fitted per channel against range from the darkest pixels, removed;
               then grey-world
  range        backscatter as above, then attenuation fitted per channel against range from the
               remaining signal, removed; then grey-world
The TIF as published (sRGB curve undone) is scored too, for reference.
"""

import argparse
import itertools
import json
import os
from pathlib import Path

import numpy as np
import scipy.io
import scipy.ndimage as ndi
import scipy.optimize as opt
import squid_raw
import tifffile

RECCE = Path(os.environ.get("RECCE_DATA_DIR", Path.home() / ".cache/recce"))
DATA = RECCE / "datasets/squid"
PARAMS = DATA / "eval/underwater-dataset-evaluation-undisorted-params/param_files_undistort"
SETS = {
    "image_set_01": 4336,
    "image_set_02": 4376,
    "image_set_03": 4381,
    "image_set_04": 4382,
    "image_set_06": 4318,
}
SNAP_PX = 6
RANGE_BINS = 12
DARK_FRAC = 0.01
METHODS = ("tif", "raw", "camera_wb", "grey_world", "backscatter", "range", "seathru")


def srgb_to_linear(v):
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def grey_world(img, mask):
    means = img[mask].mean(0)
    return img * (means.mean() / means)


def range_bins(rng, mask):
    edges = np.quantile(rng[mask], np.linspace(0, 1, RANGE_BINS + 1))
    for lo, hi in itertools.pairwise(edges):
        m = mask & (rng >= lo) & (rng < hi)
        if m.sum() >= 1000:
            yield m


def backscatter_model(d, b_inf, b):
    return b_inf * (1 - np.exp(-b * d))


def seathru_model(d, b_inf, b, j_res, b_res):
    """Sea-thru's backscatter fit (Akkaynak and Treibitz, CVPR 2019): the second term carries the
    direct light that the darkest pixels still reflect, which the simple model counts as
    backscatter."""
    return b_inf * (1 - np.exp(-b * d)) + j_res * np.exp(-b_res * d)


def dark_pixels(img, rng, mask):
    lum = img.sum(-1)
    ds, dark = [], []
    for m in range_bins(rng, mask):
        sel = m & (lum <= np.quantile(lum[m], DARK_FRAC))
        ds.append(rng[sel].mean())
        dark.append(img[sel].mean(0))
    return np.array(ds), np.array(dark)


def fit_seathru(img, rng, mask):
    ds, dark = dark_pixels(img, rng, mask)
    params = []
    for c in range(3):
        top = dark[:, c].max()
        params.append(
            opt.curve_fit(
                seathru_model,
                ds,
                dark[:, c],
                p0=(top, 0.2, top / 2, 0.2),
                bounds=([0, 0, 0, 0], [1, 5, 1, 5]),
                maxfev=20000,
            )[0]
        )
    return np.array(params)


def fit_backscatter(img, rng, mask):
    """B(d) = B_inf * (1 - exp(-b * d)) per channel, fitted to the darkest pixels per range bin."""
    ds, dark = dark_pixels(img, rng, mask)
    params = [
        opt.curve_fit(
            backscatter_model,
            ds,
            dark[:, c],
            p0=(dark[:, c].max(), 0.2),
            bounds=([0, 0], [1, 5]),
            maxfev=20000,
        )[0]
        for c in range(3)
    ]
    return np.array(params), ds, dark


def fit_attenuation(direct, rng, mask):
    """mean D(d) = K * exp(-beta * d) per channel, a log-linear fit over range bins."""
    ds, means = [], []
    for m in range_bins(rng, mask):
        ds.append(rng[m].mean())
        means.append(direct[m].mean(0))
    ds, means = np.array(ds), np.maximum(np.array(means), 1e-6)
    return np.array([-np.polyfit(ds, np.log(means[:, c]), 1)[0] for c in range(3)])


def correct_range(img, rng, mask):
    bs, _, _ = fit_backscatter(img, rng, mask)
    d = np.where(mask, rng, 0.0)[..., None]
    direct = np.clip(img - backscatter_model(d, bs[:, 0], bs[:, 1]), 0, None)
    beta = np.clip(fit_attenuation(direct, rng, mask), 0, None)
    attenuated = np.where(mask[..., None], direct * np.exp(beta * d), img)
    no_back = np.where(mask[..., None], direct, img)
    st = fit_seathru(img, rng, mask)
    st_back = seathru_model(d, st[:, 0], st[:, 1], st[:, 2], st[:, 3])
    st_direct = np.where(mask[..., None], np.clip(img - st_back, 0, None), img)
    fit = {
        "b_inf": bs[:, 0].tolist(),
        "b": bs[:, 1].tolist(),
        "beta": beta.tolist(),
        "seathru": st.tolist(),
    }
    corrected = {
        "backscatter": grey_world(no_back, mask),
        "range": grey_world(attenuated, mask),
        "seathru": grey_world(st_direct, mask),
    }
    return corrected, fit


def backscatter_over_black(fit, rng_m, black):
    """Fitted backscatter at a chart's range over the chart's black patch, worst channel: above
    1 the fit removes more light than the black patch reflects. A check only; no fit sees it."""
    simple = backscatter_model(rng_m, np.array(fit["b_inf"]), np.array(fit["b"]))
    st = np.array(fit["seathru"])
    sea = seathru_model(rng_m, st[:, 0], st[:, 1], st[:, 2], st[:, 3])
    return float(np.max(simple / black)), float(np.max(sea / black))


def snap_shifts(green, charts):
    """SQUID's annotations sit several pixels off the patches in the published resizedUndistort
    TIFs (their evaluation undistorts on the fly). Shift each chart's annotation by the integer
    offset, within SNAP_PX, that puts its 18 patch centres on uniform pixels (low 5x5 spread over
    the local mean) while its grey ramp keeps its contrast; uniformity alone pulls small charts
    onto the white board. Geometry only: no colour value is fitted to the charts."""
    mean = ndi.uniform_filter(green, 5)
    var = np.maximum(ndi.uniform_filter(green**2, 5) - mean**2, 0)
    spread = np.sqrt(var) / np.maximum(mean, 1e-6)
    h, w = green.shape
    shifts = []
    for ch in charts:
        xs, ys = np.asarray(ch.horizontal), np.asarray(ch.vertical)
        best = None
        for dy in range(-SNAP_PX, SNAP_PX + 1):
            for dx in range(-SNAP_PX, SNAP_PX + 1):
                xi, yi = np.round(xs + dx).astype(int), np.round(ys + dy).astype(int)
                if xi.min() < 0 or yi.min() < 0 or xi.max() >= w or yi.max() >= h:
                    continue
                ramp = mean[yi[:6], xi[:6]]
                contrast = (ramp[0] - ramp[5]) / max(ramp[0], 1e-6)
                cost = np.median(spread[yi, xi]) - contrast
                if best is None or cost < best[0]:
                    best = (cost, dx, dy)
        shifts.append((best[1], best[2]))
    return shifts


def chart_scores(img, charts, rng, shifts):
    out = []
    for ch, (sdx, sdy) in zip(charts, shifts, strict=True):
        loc = np.asarray(ch.locations) + np.array([sdx, sdy])
        x0, x1 = round(loc[:, 0].min()), round(loc[:, 0].max())
        y0, y1 = round(loc[:, 1].min()), round(loc[:, 1].max())
        window = img[y0 : y1 + 1, x0 : x1 + 1]
        crop = np.stack([ndi.median_filter(window[..., c], size=5) for c in range(3)], -1)
        xa = np.round(np.asarray(ch.horizontal) + sdx).astype(int) - x0
        ya = np.round(np.asarray(ch.vertical) + sdy).astype(int) - y0
        # SQUID's annotation of RGT_4376 chart 3 puts its first grey patch outside the chart;
        # such patches are dropped rather than read off the deck.
        ok = (xa >= 0) & (xa < crop.shape[1]) & (ya >= 0) & (ya < crop.shape[0])
        all_px = np.full((len(xa), 3), np.nan)
        all_px[ok] = crop[ya[ok], xa[ok]]
        ramp = all_px[:6][ok[:6]]
        # a patch a correction drives to zero in every channel has no colour left to score; it is
        # counted as clipped instead of averaged in as NaN
        norm = np.linalg.norm(ramp, axis=1)
        lit = norm > 0
        cos = ramp[lit].sum(1) / (norm[lit] * np.sqrt(3))
        ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
        white, black = all_px[0], all_px[5]
        # channels with no signal (the TIF's clipped red) are left out rather than read as 0/0
        live = np.isfinite(white + black) & (white + black > 0)
        ratio = (white - black) / np.where(live, white + black, 1)
        out.append(
            {
                "angle_deg": float(ang.mean()) if ang.size else np.nan,
                "clipped": int((~lit).sum()),
                "range_m": float(np.nanmedian(rng[y0 : y1 + 1, x0 : x1 + 1])),
                "contrast": float(ratio[live].mean()) if live.any() else np.nan,
                "patches": int(ok[:6].sum()),
                "ramp_descending": bool((np.diff(ramp.sum(1)) < 0).all()),
                "all_px": all_px,
            }
        )
    return out


def chart_pair_angles(scored):
    """Angle between the full patch vectors (all patches, RGB) of every pair of charts."""
    angs = []
    for a, b in itertools.combinations([s["all_px"] for s in scored], 2):
        ok = np.isfinite(a).all(1) & np.isfinite(b).all(1)
        va, vb = a[ok].ravel(), b[ok].ravel()
        cos = va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb))
        angs.append(float(np.degrees(np.arccos(np.clip(cos, -1, 1)))))
    return angs


def load_ranges(set_name, source):
    """SQUID's stereo range map, or ours from recon.py (None where we have no model)."""
    if source == "squid":
        return scipy.io.loadmat(DATA / "Satil" / set_name / "distanceFromCamera.mat")["dist_map_r"]
    path = RECCE / "runs/p12/recon/ranges" / f"{set_name}_range_r.npy"
    return np.load(path).astype(np.float64) if path.exists() else None


def score_image(set_name, num, rng):
    d = DATA / "Satil" / set_name
    params = scipy.io.loadmat(
        PARAMS / f"RGT_{num}_params.mat", squeeze_me=True, struct_as_record=False
    )
    charts = np.atleast_1d(params["data"])
    tif_raw = tifffile.imread(d / f"RGT_{num}resizedUndistort.tif").astype(np.float64)
    tif = srgb_to_linear(tif_raw / 65535)
    raw, cam_wb = squid_raw.decode_linear(d / f"RGT_{num}.NEF")
    coef, norm, reg = squid_raw.register(raw, tif[..., 1])
    img = squid_raw.warp_to_tif(raw, coef, norm, tif.shape[:2])
    ok = np.isfinite(img).all(-1) & (tif[..., 1] > 0)
    log_pair = np.log(img[ok, 1] + 1e-4), np.log(tif[ok, 1] + 1e-4)
    reg["log_corr_green"] = float(np.corrcoef(*log_pair)[0, 1])
    img = np.nan_to_num(img)
    mask = ok & np.isfinite(rng) & (rng > 0)
    methods = {
        "tif": tif,
        "raw": img,
        "camera_wb": img * cam_wb,
        "grey_world": grey_world(img, mask),
    }
    corrected, fit = correct_range(img, rng, mask)
    methods.update(corrected)
    shifts = snap_shifts(tif[..., 1], charts)
    reg["snap_shifts_px"] = shifts
    scores = {k: chart_scores(v, charts, rng, shifts) for k, v in methods.items()}
    rows = []
    for i, first in enumerate(scores["raw"]):
        row = {
            "image": f"RGT_{num}",
            "chart": i,
            "range_m": first["range_m"],
            "patches": first["patches"],
            "ramp_descending": first["ramp_descending"],
        }
        for k in methods:
            row[k] = scores[k][i]["angle_deg"]
            row[f"{k}_contrast"] = scores[k][i]["contrast"]
            row[f"{k}_clipped"] = scores[k][i]["clipped"]
        row["b_over_black"], row["seathru_b_over_black"] = backscatter_over_black(
            fit, first["range_m"], first["all_px"][5]
        )
        rows.append(row)
    pairs = {"charts": len(charts), **{k: chart_pair_angles(v) for k, v in scores.items()}}
    return rows, fit, reg, pairs


def table(header, rows):
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for r in rows:
        print("| " + " | ".join(r) + " |")


def report(rows, pairs):
    rows = sorted(rows, key=lambda r: r["range_m"])
    dist = np.array([r["range_m"] for r in rows])
    lead = ["Image", "Chart", "Range (m)"]
    print("\nGrey-ramp angle to pure grey (degrees; SQUID's measure)")
    table(
        [*lead, "Patches", "Ramp descends", *METHODS],
        [
            [r["image"], str(r["chart"]), f"{r['range_m']:.1f}", str(r["patches"])]
            + ["yes" if r["ramp_descending"] else "no"]
            + [f"{r[k]:.1f}" for k in METHODS]
            for r in rows
        ],
    )
    for k in METHODS:
        v = np.array([r[k] for r in rows])
        ok = np.isfinite(v)
        slope = np.polyfit(dist[ok], v[ok], 1)[0]
        clipped = sum(r[f"{k}_clipped"] for r in rows)
        print(
            f"{k}: mean {v[ok].mean():.2f}, median {np.median(v[ok]):.2f}, "
            f"slope {slope:+.2f}/m, grey patches clipped to zero {clipped}"
        )
    print("\nGrey-ramp contrast (white - black) / (white + black), mean over channels")
    table(
        [*lead, *METHODS],
        [
            [r["image"], str(r["chart"]), f"{r['range_m']:.1f}"]
            + [f"{r[k + '_contrast']:.3f}" for k in METHODS]
            for r in rows
        ],
    )
    for k in METHODS:
        c = np.array([r[k + "_contrast"] for r in rows])
        ok = np.isfinite(c)
        slope = np.polyfit(dist[ok], c[ok], 1)[0]
        print(f"{k}: mean {c[ok].mean():.3f}, slope {slope:+.4f}/m")
    print("\nFitted backscatter over the chart's black patch (worst channel; above 1 is too much)")
    table(
        [*lead, "Simple fit", "Sea-thru fit"],
        [
            [
                r["image"],
                str(r["chart"]),
                f"{r['range_m']:.1f}",
                f"{r['b_over_black']:.2f}",
                f"{r['seathru_b_over_black']:.2f}",
            ]
            for r in rows
        ],
    )
    print("\nChart-pair angle within an image (degrees; identical charts at different ranges)")
    table(
        ["Image", "Charts", *METHODS],
        [
            [im, str(p["charts"])] + [f"{np.mean(p[k]):.1f}" for k in METHODS]
            for im, p in pairs.items()
            if p["raw"]
        ],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ranges",
        choices=["squid", "ours"],
        default="squid",
        help="SQUID's stereo ranges, or ours from recon.py (images without a model are skipped)",
    )
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or RECCE / f"runs/p12/colour_{args.ranges}.json"
    rows, fits, regs, pairs = [], {}, {}, {}
    for set_name, num in SETS.items():
        rng = load_ranges(set_name, args.ranges)
        if rng is None:
            print(f"RGT_{num}: no range map from {args.ranges}, skipped")
            continue
        r, fits[f"RGT_{num}"], regs[f"RGT_{num}"], pairs[f"RGT_{num}"] = score_image(
            set_name, num, rng
        )
        rows.extend(r)
    args.out = out
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = {"rows": rows, "fits": fits, "registration": regs, "chart_pairs": pairs}
    args.out.write_text(json.dumps(result, indent=1))
    print("registration", json.dumps(regs))
    print("fits", json.dumps(fits))
    report(rows, pairs)


if __name__ == "__main__":
    main()
