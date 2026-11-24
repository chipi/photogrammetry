"""Route "chemigram": Chemigram drives darktable through its command line (external process only).

One anchor image carries the edit; `propagate-state` syncs it to the rest of the set, so every
image gets the same white balance and the same exposure (the Lightroom "sync settings" step).

  - white balance: the `temperature` entry with set-wide coefficients, found by a closed loop that
    makes a neutral patch (the grey cabinet door in DSC_0634) neutral in the anchor's render.
    Chemigram's `wb-from-gray-card` verb needs a render that is not too dark; the unity-coefficient
    render of this scene is, so the same one-patch idea is iterated here on the real renders.
  - exposure: the `exposure` entry with one EV value, found by a closed loop that puts the set's
    median-of-medians luminance at TARGET_MEDIAN_LINEAR, the same target the own route uses.

The loop runs on 800 px renders; the final export is full size, cropped to the JPEG frame.
"""

import argparse
import json
import os
import subprocess

import numpy as np
from common import (
    CROP_H,
    CROP_LEFT,
    CROP_TOP,
    CROP_W,
    RUNS,
    TARGET_MEDIAN_LINEAR,
    luminance,
    raw_files,
    read_rgb,
    route_dir,
    to_linear,
    write_jpeg,
)

CHEMIGRAM = os.environ.get("CHEMIGRAM_BIN", "/work/chemigram/main/.venv/bin/chemigram")
PACKS = ["-p", "starter", "-p", "expressive-baseline"]
ANCHOR = "DSC_0634"
# Neutral patch in the anchor's 800 px render (800x532): the grey cabinet door.
PATCH = (180, 330, 30)  # x, y, half-side
LOOP_SIZE = 800
ITERATIONS = 5


def cg(env, *args, check=True):
    proc = subprocess.run(  # noqa: S603 - external process by design
        [CHEMIGRAM, *args], env=env, capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"chemigram {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}")
    return proc


def export_all(env, ids, size=None, fmt="jpeg"):
    paths = {}
    for i in ids:
        args = ["export-final", i, "--format", fmt]
        if size:
            args += ["--size", str(size)]
        cg(env, *args)
        ext = "jpg" if fmt == "jpeg" else fmt
        paths[i] = f"{env['CHEMIGRAM_WORKSPACE']}/{i}/exports/export_HEAD.{ext}"
    return paths


def apply_recipe(env, ids, coeffs, ev):
    for i in ids:
        cg(env, "reset", i)
    if coeffs is not None:
        cg(
            env,
            "apply-primitive",
            ANCHOR,
            "--entry",
            "temperature",
            "--param",
            f"red_coeff={coeffs[0]:.4f}",
            "--param",
            "green_coeff=1.0",
            "--param",
            f"blue_coeff={coeffs[2]:.4f}",
            *PACKS,
        )
    cg(env, "apply-primitive", ANCHOR, "--entry", "exposure", "--value", f"{ev:.4f}", *PACKS)
    others = [i for i in ids if i != ANCHOR]
    args = ["propagate-state", ANCHOR]
    for o in others:
        args += ["--to", o]
    cg(env, *args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene")
    parser.add_argument(
        "--wb",
        choices=["camera", "greypick"],
        default="camera",
        help="camera: no temperature entry, darktable applies each image's as-shot WB; "
        "greypick: set-wide coefficients from the grey-patch loop",
    )
    args = parser.parse_args()
    files = raw_files(args.scene)
    ids = [f.stem for f in files]
    if ANCHOR not in ids:
        raise SystemExit(f"anchor {ANCHOR} not in the set")
    base = RUNS / args.scene / "chemigram_work"
    env = {
        **os.environ,
        "CHEMIGRAM_WORKSPACE": str(base / "workspace"),
        "CHEMIGRAM_DT_CONFIGDIR": str(RUNS / "dtconf"),
    }
    (base / "workspace").mkdir(parents=True, exist_ok=True)
    for f in files:
        if not (base / "workspace" / f.stem).exists():
            cg(env, "ingest", str(f))

    coeffs = [1.875, 1.0, 1.902] if args.wb == "greypick" else None
    route = "chemigram" if args.wb == "camera" else "chemigram_greypick"
    ev = 0.0
    history = []
    for it in range(ITERATIONS):
        apply_recipe(env, ids, coeffs, ev)
        paths = export_all(env, ids, size=LOOP_SIZE)
        meds = [float(np.median(luminance(to_linear(read_rgb(p))))) for p in paths.values()]
        set_median = float(np.median(meds))
        x, y, h = PATCH
        patch = to_linear(read_rgb(paths[ANCHOR]))[y - h : y + h, x - h : x + h].reshape(-1, 3)
        r, g, b = np.median(patch, axis=0)
        history.append(
            {
                "iteration": it,
                "coeffs": coeffs and [round(c, 4) for c in coeffs],
                "ev": round(ev, 4),
                "set_median_luminance": round(set_median, 4),
                "patch_linear_rgb": [round(float(v), 4) for v in (r, g, b)],
            }
        )
        print(json.dumps(history[-1]), flush=True)
        if coeffs is not None:
            coeffs = [
                float(min(4.0, max(0.5, coeffs[0] * (g / r) ** 0.7))),
                1.0,
                float(min(4.0, max(0.5, coeffs[2] * (g / b) ** 0.7))),
            ]
        ev = min(3.0, max(-3.0, ev + 0.7 * float(np.log2(TARGET_MEDIAN_LINEAR / set_median))))

    # The last loop pass measured the recipe before the final update; apply the updated one.
    apply_recipe(env, ids, coeffs, ev)
    paths = export_all(env, ids, fmt="png")
    out = route_dir(args.scene, route) / "images/dslr_images"
    out.mkdir(parents=True, exist_ok=True)
    for i, p in paths.items():
        rgb = read_rgb(p)
        if rgb.dtype != np.uint8:
            raise SystemExit(f"{p}: expected 8-bit, got {rgb.dtype}")
        rgb = rgb[CROP_TOP : CROP_TOP + CROP_H, CROP_LEFT : CROP_LEFT + CROP_W]
        if rgb.shape != (CROP_H, CROP_W, 3):
            raise SystemExit(f"{p}: crop gave {rgb.shape}")
        write_jpeg(out / f"{i}.JPG", rgb)
        print(i, rgb.shape, flush=True)
    meta = {
        "chemigram": cg(env, "status").stdout,
        "final_coeffs_rgb": coeffs and [round(c, 4) for c in coeffs],
        "final_ev": round(ev, 4),
        "loop": history,
        "anchor": ANCHOR,
        "patch_xy_halfside_in_800px_render": PATCH,
    }
    (route_dir(args.scene, route) / "develop.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
