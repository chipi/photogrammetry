"""RC-P9 fixture: a textured room rendered along a robot-like camera path, written as a capture set.

Run headless inside Blender (no pip packages, Blender's own Python):

    blender -b -P make_fixture.py -- --out ~/.cache/recce/datasets/fixtures/p9-room \
        --height 1.2 --name h120

Frame: `map`, z up, right-handed, metres (REP-103). Poses are camera-to-world with the Blender
camera's own axes (OpenGL: looks down -Z, +Y up), orientation as a quaternion named {x, y, z, w}.
The set states that in `manifest.json` (`pose_convention`); the engine converts it.
"""

import argparse
import hashlib
import json
import math
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import bpy
import mathutils
import numpy as np

W, H = 1280, 960
LENS_MM, SENSOR_MM = 24.0, 36.0
FPS_NS = 200_000_000  # one frame per 0.2 s of robot time

# Room, in the map frame: deliberately not centred on the origin.
X0, X1, Y0, Y1, Z0, Z1 = -1.5, 4.5, -2.0, 3.0, 0.0, 2.8
CENTRE = ((X0 + X1) / 2, (Y0 + Y1) / 2)

OBJECTS = {
    "sphere": {"kind": "sphere", "centre": [2.4, 1.2, 0.4], "radius": 0.4},
    "box_low": {"kind": "box", "centre": [0.6, -0.3, 0.35], "size": [0.7, 0.5, 0.7], "yaw_deg": 0},
    "cylinder": {"kind": "cylinder", "centre": [3.8, 2.3, 0.6], "radius": 0.35, "height": 1.2},
    "box_tall": {"kind": "box", "centre": [-1.0, 0.8, 0.9], "size": [0.8, 1.2, 1.8], "yaw_deg": 0},
}

# Seven markers, one per non-black on/off colour pattern of (R, G, B), for the pixel check.
MARKERS = {
    "floor_x0y0": ((X0, Y0, Z0), (1, 0, 0)),
    "floor_x1y0": ((X1, Y0, Z0), (0, 1, 0)),
    "floor_x1y1": ((X1, Y1, Z0), (0, 0, 1)),
    "floor_x0y1": ((X0, Y1, Z0), (1, 1, 0)),
    "ceil_x0y0": ((X0, Y0, Z1), (1, 0, 1)),
    "ceil_x1y1": ((X1, Y1, Z1), (0, 1, 1)),
    "ceil_x1y0": ((X1, Y0, Z1), (1, 1, 1)),
}
MARKER_RADIUS = 0.05
MARKER_EVERY = 5


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--name", default="h120")
    p.add_argument("--height", type=float, default=1.2)
    p.add_argument("--frames", type=int, default=60)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--only-markers", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="render only the first N frames (test)")
    return p.parse_args(argv)


def texture_material(name, seed, scale=1.0, tint=(1.0, 1.0, 1.0)):
    """High-contrast, non-repeating procedural colour in world coordinates (cell size ~25 cm)."""
    rng = random.Random(seed)  # noqa: S311 (a fixed texture offset, not security)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    def node(kind, **props):
        n = nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    pos = node("ShaderNodeNewGeometry")
    off = node("ShaderNodeMapping")
    off.inputs["Location"].default_value = [rng.uniform(0, 50) for _ in range(3)]
    nt.links.new(pos.outputs["Position"], off.inputs["Vector"])

    big = node("ShaderNodeTexVoronoi", feature="F1")
    big.inputs["Scale"].default_value = 4.0 * scale
    big.inputs["Randomness"].default_value = 1.0
    nt.links.new(off.outputs["Vector"], big.inputs["Vector"])

    noise = node("ShaderNodeTexNoise", noise_dimensions="3D")
    noise.inputs["Scale"].default_value = 25.0 * scale
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.75
    nt.links.new(off.outputs["Vector"], noise.inputs["Vector"])
    ramp = node("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[1].position = 0.65
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    fine = node("ShaderNodeTexVoronoi", feature="F1")
    fine.inputs["Scale"].default_value = 55.0 * scale
    nt.links.new(off.outputs["Vector"], fine.inputs["Vector"])
    fine_ramp = node("ShaderNodeValToRGB")
    fine_ramp.color_ramp.elements[0].position = 0.05
    fine_ramp.color_ramp.elements[0].color = (0.15, 0.15, 0.15, 1)
    fine_ramp.color_ramp.elements[1].position = 0.45
    nt.links.new(fine.outputs["Distance"], fine_ramp.inputs["Fac"])

    mix1 = node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix1.inputs["Factor"].default_value = 1.0
    nt.links.new(big.outputs["Color"], mix1.inputs["A"])
    nt.links.new(ramp.outputs["Color"], mix1.inputs["B"])
    mix2 = node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix2.inputs["Factor"].default_value = 0.8
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    nt.links.new(fine_ramp.outputs["Color"], mix2.inputs["B"])
    tinted = node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    tinted.inputs["Factor"].default_value = 1.0
    tinted.inputs["B"].default_value = (*tint, 1.0)
    nt.links.new(mix2.outputs["Result"], tinted.inputs["A"])

    bsdf = node("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.9
    nt.links.new(tinted.outputs["Result"], bsdf.inputs["Base Color"])
    out = node("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def emission_material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def add_quad(name, corners, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(corners, [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def build_room():
    objs = []
    quads = {
        "floor": [(X0, Y0, Z0), (X1, Y0, Z0), (X1, Y1, Z0), (X0, Y1, Z0)],
        "ceiling": [(X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)],
        "wall_x0": [(X0, Y0, Z0), (X0, Y1, Z0), (X0, Y1, Z1), (X0, Y0, Z1)],
        "wall_x1": [(X1, Y0, Z0), (X1, Y1, Z0), (X1, Y1, Z1), (X1, Y0, Z1)],
        "wall_y0": [(X0, Y0, Z0), (X1, Y0, Z0), (X1, Y0, Z1), (X0, Y0, Z1)],
        "wall_y1": [(X0, Y1, Z0), (X1, Y1, Z0), (X1, Y1, Z1), (X0, Y1, Z1)],
    }
    tints = [
        (1, 0.9, 0.8),
        (0.8, 0.9, 1),
        (0.9, 1, 0.8),
        (1, 0.85, 0.95),
        (0.85, 1, 1),
        (1, 1, 0.8),
    ]
    for i, (name, corners) in enumerate(quads.items()):
        objs.append(add_quad(name, corners, texture_material(name, 100 + i, 1.0, tints[i])))

    for i, (name, spec) in enumerate(OBJECTS.items()):
        cx, cy, cz = spec["centre"]
        if spec["kind"] == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=spec["radius"], segments=96, ring_count=48, location=(cx, cy, cz)
            )
            bpy.ops.object.shade_smooth()
        elif spec["kind"] == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(
                radius=spec["radius"], depth=spec["height"], vertices=96, location=(cx, cy, cz)
            )
        else:
            sx, sy, sz = spec["size"]
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
            bpy.context.object.scale = (sx, sy, sz)
            bpy.context.object.rotation_euler[2] = math.radians(spec["yaw_deg"])
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(texture_material(name, 200 + i, 1.3, (1, 1, 1)))
        objs.append(obj)
    return objs


def build_lights():
    lights = []
    for i, (lx, ly) in enumerate([(0.0, -0.8), (3.0, 1.8), (0.0, 1.8), (3.0, -0.8)]):
        data = bpy.data.lights.new(f"panel{i}", "AREA")
        data.energy = 80.0
        data.size = 1.0
        obj = bpy.data.objects.new(f"panel{i}", data)
        obj.location = (lx, ly, Z1 - 0.05)
        obj.visible_camera = False
        bpy.context.scene.collection.objects.link(obj)
        lights.append(obj)
    return lights


def setup_render(scene, args):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = args.threads
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.display_settings.display_device = "sRGB"


def camera_path(n, height):
    """Robot-like loop: an ellipse about the room centre, heading swinging +-35 deg about the
    inward direction, a slow pitch change; no roll."""
    poses = []
    pitch_target = 0.7 if height > 0.6 else 0.5
    for i in range(n):
        th = 2 * math.pi * i / n
        px = CENTRE[0] + 2.0 * math.cos(th) + 0.08 * math.sin(5 * th)
        py = CENTRE[1] + 1.4 * math.sin(th) + 0.08 * math.cos(4 * th)
        swing = math.radians(35) * math.sin(3 * th)
        inward = math.atan2(CENTRE[1] - py, CENTRE[0] - px)
        yaw = inward + swing
        look = mathutils.Vector(
            (
                px + 3.0 * math.cos(yaw),
                py + 3.0 * math.sin(yaw),
                pitch_target + 0.25 * math.sin(2 * th),
            )
        )
        pos = mathutils.Vector((px, py, height))
        quat = (look - pos).to_track_quat("-Z", "Y")
        poses.append(mathutils.Matrix.LocRotScale(pos, quat, None))
    return poses


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blob_centroids(png):
    img = bpy.data.images.load(str(png))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[:, :, :3]
    bpy.data.images.remove(img)
    mx = px.max(axis=2)
    on = mx > 0.2
    pattern = (px > 0.5 * mx[:, :, None]) & on[:, :, None]
    found = {}
    for name, (_, bits) in MARKERS.items():
        sel = on & np.all(pattern == np.array(bits, dtype=bool), axis=2)
        n = int(sel.sum())
        if n < 12:
            continue
        rows, cols = np.nonzero(sel)
        if rows.min() == 0 or cols.min() == 0 or rows.max() == H - 1 or cols.max() == W - 1:
            continue
        wgt = mx[rows, cols]
        u = float(((cols + 0.5) * wgt).sum() / wgt.sum())
        # Blender pixel rows run bottom-up; report top-down image coordinates.
        v = float((H - (rows + 0.5)) @ wgt / wgt.sum())
        found[name] = {"u": u, "v": v, "pixels": n}
    return found


def main():
    args = parse_args()
    set_dir = args.out / args.name
    (set_dir / "images").mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_render(scene, args)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = LENS_MM
    cam_data.sensor_width = SENSOR_MM
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start, cam_data.clip_end = 0.05, 50.0
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    room_objs = build_room()
    lights = build_lights()
    scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0

    fx = LENS_MM / SENSOR_MM * W
    poses = camera_path(args.frames, args.height)
    if args.limit:
        poses = poses[: args.limit]

    records = []
    if not args.only_markers:
        for i, mw in enumerate(poses, start=1):
            cam.matrix_world = mw
            scene.cycles.seed = i
            path = set_dir / "images" / f"{i:06d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            q = mw.to_quaternion()  # (w, x, y, z)
            t = mw.to_translation()
            records.append(
                {
                    "index": i,
                    "file": f"images/{i:06d}.png",
                    "wall_ns": i * FPS_NS,
                    "sensor": "cam0",
                    "pose": {
                        "frame": "map",
                        "source": "truth",
                        "position": {"x": t.x, "y": t.y, "z": t.z},
                        "orientation": {"x": q.x, "y": q.y, "z": q.z, "w": q.w},
                    },
                    "settings": {"exposure": "locked", "gain": 0.0, "white_balance": "locked"},
                    "format": "png",
                    "sha256": sha256(path),
                }
            )
            print(f"rendered {i}/{len(poses)}", flush=True)

        (set_dir / "images.json").write_text(json.dumps({"images": records}, indent=2))
        (set_dir / "cameras.json").write_text(
            json.dumps(
                {
                    "cam0": {
                        "model": "pinhole",
                        "width": W,
                        "height": H,
                        "fx": fx,
                        "fy": fx,
                        "cx": W / 2,
                        "cy": H / 2,
                        "distortion": None,
                        "mount": None,
                        "note": f"{LENS_MM} mm lens, {SENSOR_MM} mm sensor width, square pixels",
                    }
                },
                indent=2,
            )
        )
        (set_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "manifest": 1,
                    "run_id": f"p9-room-{args.name}",
                    "created": datetime.now(UTC).isoformat(timespec="seconds"),
                    "generator": {
                        "tool": "blender",
                        "version": bpy.app.version_string,
                        "script": "prototypes/RC-P9-robot-capture/make_fixture.py",
                    },
                    "frame": {
                        "name": "map",
                        "axes": {"handedness": "right", "up": "+z", "units": "m"},
                    },
                    "units": "m",
                    "clock": {"epoch": 0, "kind": "synthetic", "unit": "ns"},
                    "pose_convention": {
                        "direction": "camera_to_world",
                        "camera_axes": "opengl",
                        "world_up": "+z",
                        "handedness": "right",
                    },
                    "source": {"run": f"p9-room-{args.name}", "stream": "cam0"},
                    "images_sha256": hashlib.sha256(
                        "".join(r["sha256"] for r in records).encode()
                    ).hexdigest(),
                    "site": None,
                    "targets": [],
                },
                indent=2,
            )
        )

    truth = {
        "frame": "map",
        "axes": {"handedness": "right", "up": "+z", "units": "m"},
        "room": {"x": [X0, X1], "y": [Y0, Y1], "z": [Z0, Z1]},
        "room_corners": [[x, y, z] for z in (Z0, Z1) for y in (Y0, Y1) for x in (X0, X1)],
        "extent_m": math.dist((X0, Y0, Z0), (X1, Y1, Z1)),
        "objects": OBJECTS,
        "markers": {k: list(v[0]) for k, v in MARKERS.items()},
    }
    (args.out / "ground_truth.json").write_text(json.dumps(truth, indent=2))

    # Pixel check: render only the emissive markers at a few frames and locate their centroids.
    for o in room_objs + lights:
        o.hide_render = True
    for name, (xyz, rgb) in MARKERS.items():
        bpy.ops.mesh.primitive_uv_sphere_add(radius=MARKER_RADIUS, location=xyz)
        bpy.context.object.name = f"marker_{name}"
        bpy.context.object.data.materials.append(emission_material(name, rgb))
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.view_settings.view_transform = "Standard"
    marker_dir = args.out / f"{args.name}.markers"
    marker_dir.mkdir(exist_ok=True)
    detections = {}
    for i, mw in enumerate(poses, start=1):
        if (i - 1) % MARKER_EVERY:
            continue
        cam.matrix_world = mw
        path = marker_dir / f"{i:06d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        detections[f"{i:06d}"] = blob_centroids(path)
    (args.out / f"{args.name}.marker_pixels.json").write_text(
        json.dumps(
            {
                "image_size": [W, H],
                "pixel_origin": "top-left, centres at +0.5",
                "detections": detections,
            },
            indent=2,
        )
    )
    print("fixture done:", set_dir, flush=True)


main()
