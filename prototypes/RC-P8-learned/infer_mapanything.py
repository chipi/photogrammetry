"""RC-P8: MapAnything (Apache checkpoint) on one prepared scene, with or without priors.

Runs in MapAnything's environment (no pycolmap there). Reads OUT/images and OUT/priors.json
written by run_p8.py, writes OUT/<variant>/mapanything.json: per image cam_from_world (OpenCV
axes) and pinhole K in the original image's pixels, plus timings and GPU peak memory.

    python infer_mapanything.py OUT --variant none|prior [--cpu] [--limit N]
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import PIL.Image
import torch

MODEL = "facebook/map-anything-apache"
IMAGE_EXT = {".jpg", ".jpeg", ".png"}


def pixel_map(size, target, k_prior=None):
    """Affine map (sx, ox, sy, oy) from original to processed pixels: x' = sx x + ox.

    MapAnything's crop_resize places the crop by the principal point when intrinsics are given
    and centres it otherwise, so the map follows the same branch as the run. Both are read off
    MapAnything's own functions, not re-derived."""
    from mapanything.utils.cropping import (
        crop_resize_if_necessary,
        rescale_image_and_other_optional_info,
    )

    blank = PIL.Image.new("RGB", size)
    if k_prior is not None:
        k = np.asarray(k_prior, dtype=np.float32)
        k1 = np.asarray(crop_resize_if_necessary(blank, resolution=target, intrinsics=k)[1])
        sx, sy = k1[0, 0] / k[0, 0], k1[1, 1] / k[1, 1]
        return (
            float(sx),
            float(k1[0, 2] - sx * k[0, 2]),
            float(sy),
            float(k1[1, 2] - sy * k[1, 2]),
        )
    probe = np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1]], dtype=np.float32)
    img, _, k1, _ = rescale_image_and_other_optional_info(
        image=blank, output_resolution=np.array(target), camera_intrinsics=probe
    )
    k1 = np.asarray(k1)
    w, h = img.size
    left, top = (w - target[0]) // 2, (h - target[1]) // 2
    return float(k1[0, 0]), float(k1[0, 2] - left), float(k1[1, 1]), float(k1[1, 2] - top)


def collect(paths, sizes, preds, processed, k_priors, target):
    """Poses (cam_from_world) and intrinsics in the original image's pixels."""
    images, maps, check = {}, {}, None
    for p, size, pred, view, k_prior in zip(paths, sizes, preds, processed, k_priors, strict=True):
        sx, ox, sy, oy = maps[p.name] = pixel_map(size, target, k_prior)
        if k_prior is not None and "intrinsics" in view:
            # infer() moves the views to the GPU in place.
            kp = torch.as_tensor(view["intrinsics"]).detach().cpu().numpy().reshape(-1, 3, 3)[0]
            mapped = (
                sx * k_prior[0][0],
                sx * k_prior[0][2] + ox,
                sy * k_prior[1][1],
                sy * k_prior[1][2] + oy,
            )
            got = (kp[0, 0], kp[0, 2], kp[1, 1], kp[1, 2])
            diff = max(abs(a - b) for a, b in zip(mapped, got, strict=True))
            check = round(float(max(check or 0.0, diff)), 4)
        k = pred["intrinsics"][0].float().cpu().numpy()
        k_orig = [
            [k[0, 0] / sx, 0, (k[0, 2] - ox) / sx],
            [0, k[1, 1] / sy, (k[1, 2] - oy) / sy],
            [0, 0, 1],
        ]
        c2w = pred["camera_poses"][0].float().cpu().numpy()
        images[p.name] = {
            "cam_from_world": np.linalg.inv(c2w).tolist(),
            "K": np.asarray(k_orig, dtype=float).tolist(),
        }
    return images, maps, check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--variant", choices=["none", "prior"], required=True)
    ap.add_argument("--cpu", action="store_true", help="force CPU (a code check, not a run)")
    ap.add_argument("--limit", type=int, default=0, help="first N images only (code check)")
    args = ap.parse_args()
    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    from mapanything.models import MapAnything
    from mapanything.utils.image import find_closest_aspect_ratio, preprocess_inputs

    device = "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    priors = json.loads((args.out / "priors.json").read_text())
    image_dir = args.out / "images"
    paths = sorted(p for p in image_dir.rglob("*") if p.suffix.lower() in IMAGE_EXT)
    if args.limit:
        paths = paths[: args.limit]
    pri = {Path(k).name: v for k, v in priors["images"].items()}

    timings = {}
    t0 = time.perf_counter()
    model = MapAnything.from_pretrained(MODEL).to(device).eval()
    timings["model_load_s"] = round(time.perf_counter() - t0, 2)

    t0 = time.perf_counter()
    views, sizes = [], []
    for p in paths:
        img = PIL.Image.open(p).convert("RGB")
        sizes.append(img.size)
        v = {"img": np.asarray(img)}
        if args.variant == "prior":
            pr = pri[p.name]
            v["intrinsics"] = torch.tensor(pr["K"], dtype=torch.float32)
            if pr["cam_from_world"] is not None:
                c2w = np.linalg.inv(np.array(pr["cam_from_world"]))
                v["camera_poses"] = torch.tensor(c2w, dtype=torch.float32)
                v["is_metric_scale"] = torch.tensor([bool(priors["metric"])])
        views.append(v)
    processed = preprocess_inputs(views)
    timings["preprocess_s"] = round(time.perf_counter() - t0, 2)
    aspect = sum(w / h for w, h in sizes) / len(sizes)
    target = find_closest_aspect_ratio(aspect, 518)

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    with torch.no_grad():
        preds = model.infer(
            processed,
            memory_efficient_inference=True,
            use_amp=device == "cuda",
            amp_dtype="bf16",
            apply_mask=True,
            mask_edges=True,
        )
    if device == "cuda":
        torch.cuda.synchronize()
    timings["inference_s"] = round(time.perf_counter() - t0, 2)

    k_priors = [pri[p.name]["K"] if args.variant == "prior" else None for p in paths]
    images, maps, map_check_px = collect(paths, sizes, preds, processed, k_priors, target)
    gpu = None
    if device == "cuda":
        gpu = {
            "name": torch.cuda.get_device_name(0),
            "peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        }
    out = args.out / args.variant
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "model": MODEL,
        "variant": args.variant,
        "device": device,
        "gpu": gpu,
        "processed_size": list(target),
        "pixel_maps": maps,
        # Prior run only: the map applied to the prior K against MapAnything's own processed K.
        "pixel_map_check_max_px": map_check_px,
        "torch": torch.__version__,
        "timings": timings,
        "images": images,
    }
    (out / "mapanything.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "images"}, indent=1))
    print(f"mapanything: {len(images)} images posed")


if __name__ == "__main__":
    main()
