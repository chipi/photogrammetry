"""RC-P8: learned (MapAnything) and classical (COLMAP, GLOMAP) registration, compared.

Runs in the pycolmap environment. MapAnything runs separately in its own environment
(infer_mapanything.py) and hands its poses over as JSON; this script prepares the scenes and
priors, runs the classical routes, bundle-adjusts the learned poses and scores every route.

    prep-eth3d SCENE OUT    ETH3D scene: images, ground truth, priors (GT intrinsics, noised poses)
    prep-arkit VIDEO OUT    ARKitScenes raw video: frames, ARKit reference, priors (intrinsics)
    colmap OUT --variant V  features, matches, classical routes, learned + BA, scores (none|prior)
"""

import argparse
import itertools
import json
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pycolmap

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "RC-P1-registration"))
from run_p1 import rotation_angle_deg, score, timed, umeyama, world_from_cam

IMAGE_EXT = {".jpg", ".jpeg", ".png"}
# ETH3D pose priors: ground truth with noise of the size an ARKit-like tracker drifts over a
# room-sized walk. A choice, not a measurement; recorded in priors.json.
NOISE_POS_FRAC = 0.01
NOISE_ROT_DEG = 1.0
GL_FROM_CV = np.diag([1.0, -1.0, -1.0])
BA_THRESHOLDS_PX = (64.0, 32.0, 16.0, 8.0, 4.0)


def rodrigues(v):
    theta = float(np.linalg.norm(v))
    if theta < 1e-12:
        return np.eye(3)
    k = np.asarray(v) / theta
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(theta) * kx + (1 - np.cos(theta)) * kx @ kx


def log_rotation(rot):
    angle = float(np.arccos(np.clip((np.trace(rot) - 1) / 2, -1.0, 1.0)))
    if angle < 1e-12:
        return np.zeros(3)
    w = np.array([rot[2, 1] - rot[1, 2], rot[0, 2] - rot[2, 0], rot[1, 0] - rot[0, 1]])
    return w * angle / (2 * np.sin(angle))


def arkit_pose_at(traj, stamp, max_gap):
    """cam_from_world (R, t) at `stamp` from the ARKit trajectory, or None outside it.

    ARKitScenes' own loader inverts each line to get the camera-to-world pose, so a line holds
    cam_from_world with OpenCV camera axes (x right, y down, z forward)."""
    i = int(np.searchsorted(traj[:, 0], stamp))
    if i == 0 or i == len(traj):
        return None
    a, b = traj[i - 1], traj[i]
    if b[0] - a[0] > max_gap:
        return None
    u = (stamp - a[0]) / (b[0] - a[0])
    ra, rb = rodrigues(a[1:4]), rodrigues(b[1:4])
    ca, cb = -ra.T @ a[4:7], -rb.T @ b[4:7]
    # Interpolate world_from_cam: orientation by slerp, camera centre linearly.
    wa = ra.T
    w = wa @ rodrigues(u * log_rotation(wa.T @ rb.T))
    c = (1 - u) * ca + u * cb
    return w.T, -w.T @ c


def quat_wxyz(rot):
    return pycolmap.Rotation3d(rot).quat[[3, 0, 1, 2]]  # pycolmap stores xyzw


def write_text_model(out, cameras, images):
    """cameras: {id: (model, w, h, params)}; images: {id: (name, camera_id, R_cw, t_cw)}."""
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{cid} {m} {w} {h} " + " ".join(f"{p:.10g}" for p in params)
        for cid, (m, w, h, params) in sorted(cameras.items())
    ]
    (out / "cameras.txt").write_text("\n".join(lines) + "\n")
    lines = []
    for iid, (name, cid, rot, t) in sorted(images.items()):
        q = quat_wxyz(rot)
        vals = " ".join(f"{x:.12g}" for x in (*q, *t))
        lines += [f"{iid} {vals} {cid} {name}", ""]
    (out / "images.txt").write_text("\n".join(lines) + "\n")
    (out / "points3D.txt").write_text("")


def pinhole_k(cam):
    """Pinhole approximation of a COLMAP camera (distortion dropped)."""
    fx, fy = cam.focal_length_x, cam.focal_length_y
    return [[fx, 0, cam.principal_point_x], [0, fy, cam.principal_point_y], [0, 0, 1]]


def cmd_prep_eth3d(args):
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    for name, src in (
        ("images", args.scene / "images"),
        ("reference", args.scene / "dslr_calibration_jpg"),
    ):
        link = out / name
        if not link.exists():
            link.symlink_to(src.resolve())
    gt = pycolmap.Reconstruction(str(out / "reference"))
    rng = np.random.default_rng(args.seed)
    centres = np.array([world_from_cam(i)[1] for i in gt.images.values()])
    extent = float(np.linalg.norm(centres.max(0) - centres.min(0)))
    sigma = NOISE_POS_FRAC * extent
    priors = {}
    for img in gt.images.values():
        cam = gt.cameras[img.camera_id]
        r_wc, c = world_from_cam(img)
        axis = rng.normal(size=3)
        axis /= np.linalg.norm(axis)
        d_rot = rodrigues(axis * np.radians(rng.normal(0, NOISE_ROT_DEG)))
        r_wc_n, c_n = r_wc @ d_rot, c + rng.normal(0, sigma, size=3)
        cam_from_world = np.eye(4)
        cam_from_world[:3, :3] = r_wc_n.T
        cam_from_world[:3, 3] = -r_wc_n.T @ c_n
        priors[img.name] = {
            "K": pinhole_k(cam),
            "camera": {
                "model": cam.model.name,
                "width": cam.width,
                "height": cam.height,
                "params": list(map(float, cam.params)),
            },
            "cam_from_world": cam_from_world.tolist(),
        }
    (out / "priors.json").write_text(
        json.dumps(
            {
                "kind": "eth3d",
                "metric": True,
                "seed": args.seed,
                "scene_extent_m": extent,
                "noise": {
                    "position_sigma_m": sigma,
                    "position_sigma_frac_of_extent": NOISE_POS_FRAC,
                    "rotation_sigma_deg": NOISE_ROT_DEG,
                },
                "images": priors,
            },
            indent=1,
        )
    )
    print(f"prep-eth3d: {len(priors)} images, extent {extent:.2f} m, position sigma {sigma:.3f} m")


def cmd_prep_arkit(args):
    vid = args.video
    vid_id = vid.name
    traj = np.loadtxt(vid / "lowres_wide.traj")
    frames = sorted((vid / "vga_wide").glob("*.png"))
    stamps = np.array([float(f.stem.split("_")[1]) for f in frames])
    out = args.out
    if (out / "images").exists():
        shutil.rmtree(out / "images")
    (out / "images").mkdir(parents=True)
    cams, imgs, flip, priors, skipped = {}, {}, {}, {}, 0
    # ARKit poses come at 10 Hz and the vga_wide frames at 30 Hz, not always on the same clock
    # ticks (on 42444858 half the poses sit 16 ms from any frame), so each chosen frame gets
    # the pose interpolated at its own timestamp from the two poses around it.
    for j in range(0, len(frames), args.every):
        pose = arkit_pose_at(traj, stamps[j], args.max_gap)
        if pose is None:
            skipped += 1
            continue
        f, (rot, t) = frames[j], pose
        pincam = vid / "vga_wide_intrinsics" / (f.stem + ".pincam")
        w, h, fx, fy, cx, cy = np.loadtxt(pincam)
        (out / "images" / f.name).symlink_to(f.resolve())
        iid = len(imgs) + 1
        cams[iid] = ("PINHOLE", int(w), int(h), (fx, fy, cx, cy))
        imgs[iid] = (f.name, iid, rot, t)
        flip[iid] = (f.name, iid, GL_FROM_CV @ rot, GL_FROM_CV @ t)
        priors[f.name] = {
            "K": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
            "camera": {
                "model": "PINHOLE",
                "width": int(w),
                "height": int(h),
                "params": [fx, fy, cx, cy],
            },
            "cam_from_world": None,
        }
    write_text_model(out / "reference", cams, imgs)
    # Control: the same poses read with OpenGL camera axes; scoring against it must fail.
    write_text_model(out / "reference_glflip", cams, flip)
    (out / "priors.json").write_text(
        json.dumps(
            {
                "kind": "arkitscenes",
                "video": vid_id,
                "metric": True,
                "every_nth_frame": args.every,
                "pose": "interpolated at the frame timestamp (slerp, linear centre)",
                "max_pose_gap_s": args.max_gap,
                "skipped_no_pose": skipped,
                "note": "reference is ARKit's tracking, not ground truth; priors are intrinsics",
                "images": priors,
            },
            indent=1,
        )
    )
    print(f"prep-arkit {vid_id}: {len(imgs)} frames (every {args.every}th), {skipped} skipped")


def pose_metrics(est, gt):
    """est, gt: {name: (R_world_from_cam, centre)}. Sim(3) on centres, as in RC-P1."""
    names = sorted(set(est) & set(gt))
    if len(names) < 3:
        return {"images_compared": len(names)}
    e_c = np.array([est[n][1] for n in names])
    g_c = np.array([gt[n][1] for n in names])
    s, rot, t = umeyama(e_c, g_c)
    pos = np.linalg.norm((s * (rot @ e_c.T)).T + t - g_c, axis=1)
    rerr = np.array([rotation_angle_deg(gt[n][0].T @ rot @ est[n][0]) for n in names])
    # The centre alignment leaves the rotation about a near-straight camera path undetermined
    # (16 ARKit frames on 42444858: 65° constant error with matching frame-to-frame motion), so
    # two numbers that do not depend on it: every camera pair's relative rotation against the
    # reference's, and the error after the best orientation-only alignment (chordal mean).
    rel = [
        rotation_angle_deg((gt[a][0].T @ gt[b][0]).T @ (est[a][0].T @ est[b][0]))
        for a, b in itertools.combinations(names, 2)
    ]
    u, _, vt = np.linalg.svd(sum(gt[n][0] @ est[n][0].T for n in names))
    r_align = u @ np.diag([1, 1, np.linalg.det(u @ vt)]) @ vt
    oerr = np.array([rotation_angle_deg(gt[n][0].T @ r_align @ est[n][0]) for n in names])
    e0, g0 = e_c - e_c.mean(0), g_c - g_c.mean(0)
    s_o = float(np.sum(g0 * (r_align @ e0.T).T) / np.sum(e0**2))
    pos_o = np.linalg.norm(s_o * (r_align @ e0.T).T - g0, axis=1)
    extent = float(np.linalg.norm(g_c.max(0) - g_c.min(0)))
    return {
        "images_compared": len(names),
        "position_m_median": round(float(np.median(pos)), 4),
        "position_frac_of_extent_median": round(float(np.median(pos) / extent), 6),
        "rotation_deg_median": round(float(np.median(rerr)), 4),
        "rotation_deg_max": round(float(rerr.max()), 4),
        "relative_rotation_deg_median": round(float(np.median(rel)), 4),
        "relative_rotation_deg_p95": round(float(np.percentile(rel, 95)), 4),
        "rotation_orientation_aligned_deg_median": round(float(np.median(oerr)), 4),
        "position_orientation_aligned_m_median": round(float(np.median(pos_o)), 4),
        "orientation_aligned_scale_error_pct": round(100 * (1 / s_o - 1), 3),
        "sim3_scale": round(float(s), 6),
        # Size of the estimate against the reference; meaningful only for a route that claims
        # metric scale.
        "scale_error_pct": round(100 * (1 / s - 1), 3),
    }


def poses_of(rec):
    return {
        Path(i.name).name: world_from_cam(i)
        for i in rec.images.values()
        if i.has_pose and i.num_points3D > 0
    }


def score_route(recons, gt, n_images, metric):
    result = score(recons, gt, n_images)
    if recons:
        largest = max(recons.values(), key=lambda r: r.num_reg_images())
        ref = {Path(i.name).name: world_from_cam(i) for i in gt.images.values()}
        pm = pose_metrics(poses_of(largest), ref)
        result["scale"] = {
            "claims_metric": metric,
            "sim3_scale": pm.get("sim3_scale"),
            "scale_error_pct": pm.get("scale_error_pct") if metric else None,
        }
    return result


def extract(db, image_dir, names, priors, variant, device, one_camera):
    if variant == "prior":
        # One camera per image, then each set to its prior intrinsics (held fixed later).
        pycolmap.extract_features(
            db,
            image_dir,
            image_names=names,
            camera_mode=pycolmap.CameraMode.PER_IMAGE,
            device=device,
        )
        with pycolmap.Database.open(db) as d:
            for img in d.read_all_images():
                p = priors[img.name]["camera"]
                cam = d.read_camera(img.camera_id)
                d.update_camera(
                    pycolmap.Camera(
                        camera_id=cam.camera_id,
                        model=p["model"],
                        width=p["width"],
                        height=p["height"],
                        params=p["params"],
                        has_prior_focal_length=True,
                    )
                )
    else:
        # A video from one phone is one camera; without EXIF the default makes one per frame.
        mode = pycolmap.CameraMode.SINGLE if one_camera else pycolmap.CameraMode.AUTO
        pycolmap.extract_features(db, image_dir, image_names=names, camera_mode=mode, device=device)


def data_key(data_id):
    return (int(data_id.sensor_id.type), data_id.sensor_id.id, data_id.id)


def write_position_priors(db, priors, sigma):
    """The extractor already writes one empty prior per image (position NaN); fill those in."""
    with pycolmap.Database.open(db) as d:
        existing = {data_key(p.corr_data_id): p for p in d.read_all_pose_priors()}
        n = 0
        for img in d.read_all_images():
            m = priors[img.name]["cam_from_world"]
            if m is None:
                continue
            m = np.array(m)
            prior = existing.get(data_key(img.data_id)) or pycolmap.PosePrior()
            prior.corr_data_id = img.data_id
            prior.position = -m[:3, :3].T @ m[:3, 3]
            prior.position_covariance = np.eye(3) * sigma**2
            prior.coordinate_system = pycolmap.PosePriorCoordinateSystem.CARTESIAN
            if data_key(img.data_id) in existing:
                d.update_pose_prior(prior)
            else:
                d.write_pose_prior(prior)
            n += 1
    return n


def learned_then_ba(out, db, image_dir, ma, priors, variant):
    """Poses from MapAnything start a coarse-to-fine loop: triangulate from the SIFT matches,
    then a full bundle adjustment, at falling thresholds. Intrinsics: the prior camera (fixed)
    or MapAnything's pinhole estimate as a SIMPLE_RADIAL start (refined)."""
    with pycolmap.Database.open(db) as d:
        db_images = d.read_all_images()
        db_cams = {c.camera_id: c for c in d.read_all_cameras()}
    cameras, images = {}, {}
    by_cam = {}
    for img in db_images:
        by_cam.setdefault(img.camera_id, []).append(img.name)
    for cid, names in by_cam.items():
        cam = db_cams[cid]
        if variant == "prior":
            p = priors[names[0]]["camera"]
            cameras[cid] = (p["model"], p["width"], p["height"], p["params"])
        else:
            ks = np.array([ma["images"][Path(n).name]["K"] for n in names])
            f = float(np.mean((ks[:, 0, 0] + ks[:, 1, 1]) / 2))
            cameras[cid] = (
                "SIMPLE_RADIAL",
                cam.width,
                cam.height,
                (f, float(ks[:, 0, 2].mean()), float(ks[:, 1, 2].mean()), 0.0),
            )
    for img in db_images:
        m = np.array(ma["images"][Path(img.name).name]["cam_from_world"])
        images[img.image_id] = (img.name, img.camera_id, m[:3, :3], m[:3, 3])
    given = out / "learned_ba" / "given"
    write_text_model(given, cameras, images)
    rec = pycolmap.Reconstruction(str(given))
    fixed = variant == "prior"
    t = {"triangulation_s": 0.0, "bundle_adjustment_s": 0.0}
    # Coarse to fine. One triangulation at COLMAP's 4 px from the learned poses kept 129
    # two-view points on pipes (distortion starts at zero), and the adjustment overfit them.
    # COLMAP's mapper started from the learned model refines well but re-normalises the model
    # and loses the metric scale (+293% on pipes), so it is not used.
    for i, thr in enumerate(BA_THRESHOLDS_PX):
        opts = pycolmap.IncrementalPipelineOptions()
        opts.triangulation.complete_max_reproj_error = thr
        opts.triangulation.merge_max_reproj_error = thr
        opts.mapper.filter_max_reproj_error = thr
        step = out / "learned_ba" / f"step{i}"
        step.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        rec = pycolmap.triangulate_points(
            rec, db, image_dir, step, clear_points=True, options=opts, refine_intrinsics=not fixed
        )
        t1 = time.perf_counter()
        ba = pycolmap.BundleAdjustmentOptions()
        ba.refine_focal_length = ba.refine_extra_params = not fixed
        ba.refine_principal_point = False
        pycolmap.bundle_adjustment(rec, ba)
        t["triangulation_s"] += round(t1 - t0, 2)
        t["bundle_adjustment_s"] += round(time.perf_counter() - t1, 2)
    model_dir = out / "learned_ba" / "0"
    model_dir.mkdir(parents=True, exist_ok=True)
    rec.write(str(model_dir))
    return rec, {k: round(v, 2) for k, v in t.items()}


def ma_as_reconstruction_poses(ma):
    out = {}
    for name, v in ma["images"].items():
        m = np.array(v["cam_from_world"])
        r_wc = m[:3, :3].T
        out[Path(name).name] = (r_wc, -r_wc @ m[:3, 3])
    return out


def cmd_colmap(args):
    root = args.out
    priors_all = json.loads((root / "priors.json").read_text())
    priors = priors_all["images"]
    variant = args.variant
    out = root / variant
    ma_path = out / "mapanything.json"
    ma = json.loads(ma_path.read_text()) if ma_path.exists() else None
    for sub in ("database.db", "colmap_incremental", "glomap_global", "learned_ba"):
        p = out / sub
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    image_dir = root / "images"
    names = sorted(
        str(p.relative_to(image_dir)) for p in image_dir.rglob("*") if p.suffix.lower() in IMAGE_EXT
    )
    priors = {Path(k).name: v for k, v in priors.items()}
    priors = {n: priors[Path(n).name] for n in names}
    gt = pycolmap.Reconstruction(str(root / "reference"))
    controls = {}
    if (root / "reference_glflip").exists():
        controls["glflip"] = pycolmap.Reconstruction(str(root / "reference_glflip"))

    db = out / "database.db"
    shared = {}
    # The GB10's pycolmap is a CUDA build; with the GPU hidden it must be told to use the CPU.
    device = pycolmap.Device.cpu if args.cpu else pycolmap.Device.auto
    one_camera = priors_all["kind"] == "arkitscenes"
    timed(
        shared,
        "features_s",
        lambda: extract(db, image_dir, names, priors, variant, device, one_camera),
    )
    timed(shared, "matching_s", lambda: pycolmap.match_exhaustive(db, device=device))
    sigma = priors_all.get("noise", {}).get("position_sigma_m", 1.0)
    n_pose_priors = write_position_priors(db, priors, sigma) if variant == "prior" else 0

    results = {
        "scene": root.name,
        "variant": variant,
        "kind": priors_all["kind"],
        "machine": {"host": platform.node(), "arch": platform.machine()},
        "pycolmap": pycolmap.__version__,
        "cuda": bool(getattr(pycolmap, "has_cuda", False)),
        "images": len(names),
        "position_priors_written": n_pose_priors,
        "shared_timings": shared,
        "routes": {},
        "controls": {},
    }
    classical_routes(results, out, db, image_dir, gt, controls, n_pose_priors)
    if ma is not None:
        learned_routes(results, out, db, image_dir, gt, ma, priors)
    else:
        results["routes"]["mapanything"] = "not run: no mapanything.json"

    (out / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


def classical_routes(results, out, db, image_dir, gt, controls, n_pose_priors):
    variant, n = results["variant"], results["images"]
    inc = pycolmap.IncrementalPipelineOptions()
    glo = pycolmap.GlobalPipelineOptions()
    if variant == "prior":
        inc.ba_refine_focal_length = inc.ba_refine_principal_point = False
        inc.ba_refine_extra_params = False
        inc.use_prior_position = n_pose_priors > 0
    routes = [
        ("colmap_incremental", lambda o: pycolmap.incremental_mapping(db, image_dir, o, inc)),
        ("glomap_global", lambda o: pycolmap.global_mapping(db, image_dir, o, glo)),
    ]
    for name, run in routes:
        o = out / name
        o.mkdir()
        t = {}
        try:
            recons = timed(t, "mapping_s", lambda r=run, d=o: r(d))
            for i, r in recons.items():
                (o / str(i)).mkdir(exist_ok=True)
                r.write(str(o / str(i)))
        except Exception as e:  # a failing route is a result, not a crash
            results["routes"][name] = {"timings": t, "error": repr(e)}
            continue
        # Position priors put the incremental model in the metric frame of the priors.
        metric = variant == "prior" and name == "colmap_incremental" and n_pose_priors > 0
        results["routes"][name] = {"timings": t, **score_route(recons, gt, n, metric)}
        for cname, cgt in controls.items():
            results["controls"][f"{name}_vs_{cname}"] = score_route(recons, cgt, n, False)


def learned_routes(results, out, db, image_dir, gt, ma, priors):
    n = results["images"]
    ref = {Path(i.name).name: world_from_cam(i) for i in gt.images.values()}
    results["routes"]["mapanything"] = {
        "timings": ma["timings"],
        "gpu": ma.get("gpu"),
        "registered": len(ma["images"]),
        "registration_rate": len(ma["images"]) / n,
        "note": "every input image gets a pose; registration rate says nothing here",
        "pose_error": pose_metrics(ma_as_reconstruction_poses(ma), ref),
    }
    try:
        rec, t = learned_then_ba(out, db, image_dir, ma, priors, results["variant"])
        results["routes"]["mapanything_ba"] = score_learned_ba(out, rec, ma, gt, n, t)
    except Exception as e:
        results["routes"]["mapanything_ba"] = {"error": repr(e)}


def anchor_to_learned(rec, ma):
    """Bundle adjustment leaves the gauge free and lets the scale drift (on the GB10: kicker
    -39.6%, courtyard with priors -75.4%, against MapAnything's +4.1% and -5.3%). Map the
    adjusted model onto MapAnything's camera centres with a Sim(3): the scale comes from the
    learned pass, the shape from the adjustment. Returns how far the adjustment had drifted."""
    learned = ma_as_reconstruction_poses(ma)
    names = [
        Path(i.name).name
        for i in rec.images.values()
        if i.has_pose and Path(i.name).name in learned
    ]
    by_name = {Path(i.name).name: i for i in rec.images.values()}
    src = np.array([world_from_cam(by_name[n])[1] for n in names])
    dst = np.array([learned[n][1] for n in names])
    s, rot, t = umeyama(src, dst)
    rec.transform(pycolmap.Sim3d(s, pycolmap.Rotation3d(rot), t))
    return {"images": len(names), "ba_scale_drift_pct": round(100 * (1 / s - 1), 3)}


def drop_outlier_points(rec, max_error=BA_THRESHOLDS_PX[-1]):
    """The last adjustment can push a few points far off (mean error 1e150 px on 42444858 and
    42444873), and pycolmap keeps the errors from triangulation until asked. Recompute, then
    drop points above the loop's last threshold, as the loop's own filter would have."""
    rec.update_point_3d_errors()
    bad = [i for i, p in rec.points3D.items() if not np.isfinite(p.error) or p.error > max_error]
    for i in bad:
        rec.delete_point3D(i)
    rec.update_point_3d_errors()
    return len(bad)


def score_learned_ba(out, rec, ma, gt, n, timings):
    dropped = drop_outlier_points(rec)
    anchor = anchor_to_learned(rec, ma)
    anchor["points_dropped_after_last_ba"] = dropped
    anchored = out / "learned_ba" / "anchored"
    anchored.mkdir(parents=True, exist_ok=True)
    rec.write(str(anchored))
    return {
        "timings": {**ma["timings"], **timings},
        "anchor_to_learned": anchor,
        **score_route({0: rec}, gt, n, True),
    }


def cmd_rescore_ba(args):
    """Re-score the saved learned + BA model (learned_ba/0) without running anything again."""
    out = args.out / args.variant
    results = json.loads((out / "results.json").read_text())
    ma = json.loads((out / "mapanything.json").read_text())
    gt = pycolmap.Reconstruction(str(args.out / "reference"))
    rec = pycolmap.Reconstruction(str(out / "learned_ba" / "0"))
    old = results["routes"].get("mapanything_ba", {})
    t = {k: v for k, v in old.get("timings", {}).items() if k not in ma["timings"]}
    results["routes"]["mapanything_ba"] = score_learned_ba(out, rec, ma, gt, results["images"], t)
    (out / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results["routes"]["mapanything_ba"], indent=2))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep-eth3d")
    p.add_argument("scene", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--seed", type=int, default=0)
    p = sub.add_parser("prep-arkit")
    p.add_argument("video", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--every", type=int, default=12, help="every Nth vga_wide frame (30 Hz)")
    p.add_argument("--max-gap", type=float, default=0.15, help="max gap between the two poses, s")
    p = sub.add_parser("rescore-ba")
    p.add_argument("out", type=Path)
    p.add_argument("--variant", choices=["none", "prior"], required=True)
    p = sub.add_parser("colmap")
    p.add_argument("out", type=Path)
    p.add_argument("--variant", choices=["none", "prior"], required=True)
    p.add_argument("--cpu", action="store_true", help="SIFT on the CPU (GPU hidden)")
    args = ap.parse_args()
    start = time.perf_counter()
    commands = {
        "prep-eth3d": cmd_prep_eth3d,
        "prep-arkit": cmd_prep_arkit,
        "colmap": cmd_colmap,
        "rescore-ba": cmd_rescore_ba,
    }
    commands[args.cmd](args)
    print(f"{args.cmd} done in {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
