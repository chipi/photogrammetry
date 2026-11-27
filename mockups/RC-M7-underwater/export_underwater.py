"""RC-M7 export: SQUID Satil images under each colour method, with ranges, charts and the
backscatter fit; and the AquaMVS rig, its rays and the board corners under the pinhole and the
refractive model. Everything goes to the gitignored data/; SQUID is non-commercial (CC BY-NC-SA
4.0) and stays on this machine.

Run under RC-P12's environment (numpy, scipy, opencv, rawpy, tifffile):
  cd prototypes/RC-P12-underwater
  uv run python ../../mockups/RC-M7-underwater/export_underwater.py \
    ../../mockups/RC-M7-underwater/data
"""

import json
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np
import scipy.io

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P12-underwater"))
import aquamvs
import colour
import squid_raw

SHOW = ("camera_wb", "grey_world", "backscatter", "range")
WIDTH = 1400
THUMB_W = 320
RAMP = np.array(  # range colour, near to far: an OKLCH-like sequential ramp in sRGB
    [[253, 231, 37], [94, 201, 98], [33, 145, 140], [59, 82, 139], [68, 1, 84]], dtype=float
)


def to_display(img, mask, scale=None):
    """Linear RGB to an sRGB JPEG array; one exposure per image so its 99.5th luminance is 0.95."""
    if scale is None:
        lum = img[mask].mean(-1)
        scale = 0.95 / max(np.quantile(lum, 0.995), 1e-6)
    v = np.clip(img * scale, 0, 1)
    v = np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)
    return (v * 255).round().astype(np.uint8)[..., ::-1], scale


def resize(bgr, width):
    h = round(bgr.shape[0] * width / bgr.shape[1])
    return cv2.resize(bgr, (width, h), interpolation=cv2.INTER_AREA)


def range_png(rng, mask, lo, hi):
    t = np.clip((np.nan_to_num(rng) - lo) / (hi - lo), 0, 1) * (len(RAMP) - 1)
    i = np.minimum(t.astype(int), len(RAMP) - 2)
    f = (t - i)[..., None]
    rgb = RAMP[i] * (1 - f) + RAMP[i + 1] * f
    rgba = np.dstack([rgb[..., ::-1], np.where(mask, 255, 0)]).astype(np.uint8)
    return rgba


def squid(out: Path) -> dict:
    rows = json.loads((colour.RECCE / "runs/p12/colour_squid.json").read_text())["rows"]
    images = []
    for set_name, num in colour.SETS.items():
        d = colour.DATA / "Satil" / set_name
        params = scipy.io.loadmat(
            colour.PARAMS / f"RGT_{num}_params.mat", squeeze_me=True, struct_as_record=False
        )
        charts = np.atleast_1d(params["data"])
        tif = colour.srgb_to_linear(
            colour.tifffile.imread(d / f"RGT_{num}resizedUndistort.tif").astype(np.float64) / 65535
        )
        raw, cam_wb = squid_raw.decode_linear(d / f"RGT_{num}.NEF")
        coef, norm, _ = squid_raw.register(raw, tif[..., 1])
        img = np.nan_to_num(squid_raw.warp_to_tif(raw, coef, norm, tif.shape[:2]))
        rng = colour.load_ranges(set_name, "squid").astype(np.float64)
        mask = (tif[..., 1] > 0) & np.isfinite(rng) & (rng > 0)
        methods = {"camera_wb": img * cam_wb, "grey_world": colour.grey_world(img, mask)}
        corrected, fit = colour.correct_range(img, rng, mask)
        methods.update(corrected)
        name = f"RGT_{num}"
        for k in SHOW:
            bgr, _ = to_display(methods[k], mask)
            cv2.imwrite(
                str(out / f"{name}_{k}.jpg"), resize(bgr, WIDTH), [cv2.IMWRITE_JPEG_QUALITY, 88]
            )
        bgr, _ = to_display(methods["grey_world"], mask)
        cv2.imwrite(
            str(out / f"{name}_thumb.jpg"), resize(bgr, THUMB_W), [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        lo, hi = 2.0, 20.0
        cv2.imwrite(str(out / f"{name}_range.png"), resize(range_png(rng, mask, lo, hi), WIDTH))
        step = 8
        grid = np.where(mask, np.nan_to_num(rng), 0)[::step, ::step]
        shifts = colour.snap_shifts(tif[..., 1], charts)
        scored = colour.chart_scores(img, charts, rng, shifts)
        boxes = []
        for i, (ch, (sx, sy)) in enumerate(zip(charts, shifts, strict=True)):
            loc = np.asarray(ch.locations) + np.array([sx, sy])
            row = next(r for r in rows if r["image"] == name and r["chart"] == i)
            boxes.append(
                {
                    "chart": i,
                    "box": [float(loc[:, 0].min()), float(loc[:, 1].min()),
                            float(loc[:, 0].max()), float(loc[:, 1].max())],
                    "range_m": round(row["range_m"], 2),
                    "angle": {k: _r(row[k]) for k in ("tif", *SHOW)},
                    "contrast": {k: _r(row[f"{k}_contrast"], 3) for k in SHOW},
                    "black": [float(x) for x in scored[i]["all_px"][5]],
                    "b_over_black": _r(row["b_over_black"], 2),
                }
            )  # fmt: skip
        ds, dark = colour.dark_pixels(img, rng, mask)
        images.append(
            {
                "name": name,
                "size": [tif.shape[1], tif.shape[0]],
                "range_lo_hi": [lo, hi],
                "range_grid": {"step": step, "w": grid.shape[1], "h": grid.shape[0],
                               "cm": (grid * 100).round().astype(int).ravel().tolist()},
                "charts": boxes,
                "fit": {"b_inf": fit["b_inf"], "b": fit["b"], "beta": fit["beta"]},
                "dark": {"range_m": ds.round(3).tolist(), "rgb": dark.round(5).tolist()},
            }
        )  # fmt: skip
        print(name, len(boxes), "charts", flush=True)
    return {"images": images}


def _r(v, n=2):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def frame_files(zf: zipfile.ZipFile) -> dict[str, list[str]]:
    """Each camera's frame PNGs in data.zip, sorted: corner frame k is the k-th file."""
    out: dict[str, list[str]] = {}
    for n in zf.namelist():
        if "/aquamvs_ground_truth_analysis/frames/" in n and n.endswith(".png"):
            out.setdefault(n.split("/")[-2], []).append(n)
    for v in out.values():
        v.sort()
    return out


def aquamvs_rig(out: Path) -> dict:
    measured = {
        m["model"]: m for m in json.loads((colour.RECCE / "runs/p12/aquamvs.json").read_text())
    }
    zpath = colour.RECCE / "datasets/aquamvs/data.zip"
    zf = zipfile.ZipFile(zpath)
    frames_by_cam = frame_files(zf)
    models = {}
    for name, cal_path, cor_path in aquamvs.RUNS:
        cams, interface, board = aquamvs.load_calibration(cal_path)
        cal = json.loads(Path(cal_path).read_text())
        z = np.load(cor_path, allow_pickle=True)
        frames, cam_ids, ids, pixels = z["frame_idx"], z["camera_id"], z["corner_id"], z["pixels"]
        cam_names = sorted(cams)
        cam_out = []
        for c in cam_names:
            intr = cal["cameras"][c]["intrinsics"]
            k = aquamvs.undistorted_k(intr)
            cam_out.append(
                {
                    "name": c,
                    "centre": cams[c]["C"].round(5).tolist(),
                    "R": np.array(cal["cameras"][c]["extrinsics"]["R"]).round(6).tolist(),
                    "f": float(k[1, 1]),
                    "size": intr["image_size"],
                }
            )
        per_frame = {}
        for f in np.unique(frames):
            corners = []
            for cid in np.unique(ids[frames == f]):
                sel = (frames == f) & (ids == cid)
                if sel.sum() < aquamvs.MIN_VIEWS:
                    continue
                rays = [
                    aquamvs.ray(cams[c], p, interface)
                    for c, p in zip(cam_ids[sel], pixels[sel], strict=True)
                ]
                x, rms = aquamvs.intersect([o for o, _ in rays], [d for _, d in rays])
                corners.append(
                    {
                        "id": int(cid),
                        "xyz": x.round(5).tolist(),
                        "board": aquamvs.board_xy(int(cid), board).round(4).tolist(),
                        "cams": [cam_names.index(c) for c in cam_ids[sel]],
                        "hits": [o.round(5).tolist() for o, _ in rays],
                        "spread_mm": round(rms * 1000, 3),
                    }
                )
            pts = np.array([c["xyz"] for c in corners])
            model = np.array([[*c["board"], 0.0] for c in corners])
            r, t = aquamvs.umeyama_rigid(model, pts)
            per_frame[int(f)] = {
                "corners": corners,
                "board_R": r.round(6).tolist(),
                "board_t": t.round(5).tolist(),
                "metrics": next(m for m in measured[name]["frames"] if m["frame"] == int(f)),
            }
        models[name] = {
            "n_water": interface["n_water"],
            "water_z": float(np.mean([cams[c]["water_z"] for c in cam_names])),
            "cameras": cam_out,
            "frames": per_frame,
            "summary": measured[name]["summary"],
        }
    (out / "thumbs").mkdir(exist_ok=True)
    frame_ids = sorted(models["refractive"]["frames"])
    for cam, names in frames_by_cam.items():
        for f in frame_ids:
            arr = cv2.imdecode(np.frombuffer(zf.read(names[f]), np.uint8), cv2.IMREAD_COLOR)
            cv2.imwrite(str(out / "thumbs" / f"{cam}_{f}.jpg"), resize(arr, THUMB_W),
                        [cv2.IMWRITE_JPEG_QUALITY, 82])  # fmt: skip
    check_frame_mapping(zf, frames_by_cam, out)
    return {"board": board, "frames": frame_ids, "frame_files": {
        f: Path(frames_by_cam["e3v829d"][f]).name for f in frame_ids}, **models}  # fmt: skip


def check_frame_mapping(zf, frames_by_cam, out):
    """Projects frame 4's pinhole corners into camera e3v829d's raw frame 4 (index 4 in the sorted
    file list) and writes the overlay; the dots sit on the board's corners if the mapping holds."""
    _, cal_path, cor_path = aquamvs.RUNS[0]
    cal = json.loads(Path(cal_path).read_text())["cameras"]["e3v829d"]
    z = np.load(cor_path, allow_pickle=True)
    sel = (z["frame_idx"] == 4) & (z["camera_id"] == "e3v829d")
    pts = z["points"][sel].astype(np.float64)
    r = np.array(cal["extrinsics"]["R"])
    t = np.array(cal["extrinsics"]["t"], dtype=np.float64)
    k = np.array(cal["intrinsics"]["K"])
    dist = np.array(cal["intrinsics"]["dist_coeffs"], dtype=np.float64)
    px, _ = cv2.projectPoints(pts, cv2.Rodrigues(r)[0], t, k, dist)
    img = cv2.imdecode(np.frombuffer(zf.read(frames_by_cam["e3v829d"][4]), np.uint8), 1)
    for x, y in px.reshape(-1, 2):
        cv2.circle(img, (round(x), round(y)), 6, (0, 0, 255), 2)
    cv2.imwrite(str(out / "check_frame4_e3v829d.jpg"), resize(img, 800))


def main() -> None:
    out = Path(sys.argv[1])
    (out / "squid").mkdir(parents=True, exist_ok=True)
    (out / "aquamvs").mkdir(parents=True, exist_ok=True)
    rig = aquamvs_rig(out / "aquamvs")
    (out / "aquamvs.json").write_text(json.dumps(rig, separators=(",", ":")))
    print("aquamvs", len(rig["frames"]), "frames")
    sq = squid(out / "squid")
    (out / "squid.json").write_text(json.dumps(sq, separators=(",", ":")))


if __name__ == "__main__":
    main()
