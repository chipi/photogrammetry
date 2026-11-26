"""Build an RC-P13 scene in Blender, headless, and write .blend, .glb and renders.

    blender -b --factory-startup --python build.py -- SCENE_JSON OUT_DIR [--mesh PLY]

Colour states the source: measured grey-blue, inferred amber, unknown red. Every object carries
the element's source, uncertainty and basis as custom properties, which the glTF keeps as extras.
`--mesh` adds the reconstruction, translucent, for comparison.
"""

import itertools
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import scene as sc

COLOURS = {
    "measured": (0.42, 0.55, 0.70, 1.0),
    "inferred": (0.93, 0.62, 0.18, 1.0),
    "unknown": (0.85, 0.15, 0.15, 1.0),
    "reconstruction": (0.8, 0.8, 0.8, 0.25),
    "label": (0.05, 0.05, 0.05, 1.0),
}
# Within a source, surfaces get their own shade so a plan reads: floor light, walls dark.
SHADES = {"floor": 1.45, "ceiling": 1.25, "wall": 0.7, "terrain": 1.3, "steep_face": 0.6}


def args():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    scene_path, out = Path(argv[0]), Path(argv[1])
    mesh = Path(argv[argv.index("--mesh") + 1]) if "--mesh" in argv else None
    return scene_path, out, mesh


def material(source, kind=None):
    name = f"{source}-{kind}" if kind else source
    k = SHADES.get(kind, 1.0)
    r, g, b, a = COLOURS[source]
    colour = (min(r * k, 1), min(g * k, 1), min(b * k, 1), a)
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = colour
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = colour
    if a < 1:
        bsdf.inputs["Alpha"].default_value = a
        if hasattr(m, "blend_method"):
            m.blend_method = "BLEND"
    return m


def tag(obj, el):
    obj["recce_id"] = el["id"]
    obj["recce_kind"] = el["kind"]
    obj["recce_source"] = el["source"]
    if el.get("sigma_m") is not None:
        obj["recce_sigma_m"] = el["sigma_m"]
        obj["recce_sigma_basis"] = el["sigma_basis"]
    for k, v in (el.get("attributes") or {}).items():
        if isinstance(v, (int, float, str)):
            obj[f"recce_{k}"] = v


def link(obj, collection):
    bpy.data.collections[collection].objects.link(obj)


def new_object(name, verts, faces, mat, collection):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat)
    link(obj, collection)
    return obj


def wall(el):
    """The measured face, and behind it (away from the room) the body, coloured by the source of
    its thickness. A face whose partner draws the body gets the face alone."""
    g, at = el["geometry"], el["attributes"]
    p0, p1 = Vector((*g["p0"], 0)), Vector((*g["p1"], 0))
    n = Vector((g["normal"][0], g["normal"][1], 0)).normalized()
    face = [
        (p0.x, p0.y, g["z0"]),
        (p1.x, p1.y, g["z0"]),
        (p1.x, p1.y, g["z1"]),
        (p0.x, p0.y, g["z1"]),
    ]
    obj = new_object(el["id"], face, [(0, 1, 2, 3)], material(el["source"], "wall"), el["source"])
    if at.get("draws_body", True) and at["thickness_m"] > 0:
        back = [p0 - n * at["thickness_m"], p1 - n * at["thickness_m"]]
        corners = [p0, p1, back[1], back[0]]
        verts = [(c.x, c.y, g["z0"]) for c in corners] + [(c.x, c.y, g["z1"]) for c in corners]
        faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        src = at["thickness_source"]
        body = new_object(f"{el['id']} body", verts, faces, material(src, "wall"), src)
        body["recce_id"] = f"{el['id']} body"
        body["recce_kind"] = "wall_body"
        body["recce_source"] = src
        body["recce_thickness_m"] = at["thickness_m"]
    return obj


def cells(el, source):
    g = el["geometry"]
    s, (ox, oy), z = g["cell_m"], g["origin"], g["z"]
    bm = bmesh.new()
    index = {}

    def v(i, j):
        if (i, j) not in index:
            index[(i, j)] = bm.verts.new((ox + i * s, oy + j * s, z))
        return index[(i, j)]

    for i, j in g["cells"]:
        bm.faces.new((v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)))
    me = bpy.data.meshes.new(el["id"])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(el["id"], me)
    obj.data.materials.append(material(source, el["kind"]))
    link(obj, source)
    return obj


def height_grid(el):
    """One quad per cell the element holds; a corner's height is the mean of the element's cells
    around it, so the surface is continuous and every cell is drawn."""
    g = el["geometry"]
    h, s, (ox, oy) = g["heights_m"], g["cell_m"], g["origin"]
    nx, ny = g["shape"]
    bm = bmesh.new()
    index = {}

    def v(i, j):
        if (i, j) not in index:
            near = [
                h[a][b]
                for a in (i - 1, i)
                for b in (j - 1, j)
                if 0 <= a < nx and 0 <= b < ny and h[a][b] is not None
            ]
            index[(i, j)] = bm.verts.new((ox + i * s, oy + j * s, sum(near) / len(near)))
        return index[(i, j)]

    for i in range(nx):
        for j in range(ny):
            if h[i][j] is not None:
                bm.faces.new((v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)))
    me = bpy.data.meshes.new(el["id"])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(el["id"], me)
    obj.data.materials.append(material(el["source"], el["kind"]))
    link(obj, el["source"])
    return obj


def prism(el):
    """A footprint of cells extruded from z0 to z1: the roof as one quad per cell, a wall on every
    cell edge the footprint does not share."""
    g = el["geometry"]
    s, (ox, oy), z0, z1 = g["cell_m"], g["origin"], g["z0"], g["z1"]
    cells = {tuple(c) for c in g["cells"]}
    bm = bmesh.new()
    index = {}

    def v(i, j, z):
        if (i, j, z) not in index:
            index[(i, j, z)] = bm.verts.new((ox + i * s, oy + j * s, z))
        return index[(i, j, z)]

    edges = {(1, 0): ((1, 0), (1, 1)), (-1, 0): ((0, 1), (0, 0)),
             (0, 1): ((1, 1), (0, 1)), (0, -1): ((0, 0), (1, 0))}  # fmt: skip
    for i, j in cells:
        bm.faces.new((v(i, j, z1), v(i + 1, j, z1), v(i + 1, j + 1, z1), v(i, j + 1, z1)))
        for (di, dj), ((a0, b0), (a1, b1)) in edges.items():
            if (i + di, j + dj) not in cells:
                bm.faces.new(
                    (v(i + a0, j + b0, z0), v(i + a1, j + b1, z0),
                     v(i + a1, j + b1, z1), v(i + a0, j + b0, z1))
                )  # fmt: skip
    me = bpy.data.meshes.new(el["id"])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(el["id"], me)
    obj.data.materials.append(material(el["source"], "wall"))
    link(obj, el["source"])
    return obj


def label(text, location, collection, size=0.12):
    curve = bpy.data.curves.new(text, "FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new(f"label {text}", curve)
    obj.location = location
    obj.data.materials.append(material("label"))
    link(obj, collection)
    return obj


def import_mesh(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.ply_import(filepath=str(path))
    (obj,) = set(bpy.data.objects) - before
    for c in obj.users_collection:
        c.objects.unlink(obj)
    link(obj, "reconstruction")
    obj.data.materials.clear()
    obj.data.materials.append(material("reconstruction"))
    return obj


def camera(name, location, target, ortho_scale=None):
    cam = bpy.data.cameras.new(name)
    if ortho_scale:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    obj = bpy.data.objects.new(name, cam)
    obj.location = location
    obj.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(obj)
    return obj


def render(cam, path, hide):
    s = bpy.context.scene
    s.camera = cam
    for name in hide:
        bpy.data.collections[name].hide_render = True
    s.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    for name in hide:
        bpy.data.collections[name].hide_render = False


def build_elements(s):
    builders = {
        "wall_face": wall,
        "cells": lambda el: cells(el, el["source"]),
        "polyline": polyline,
        "height_grid": height_grid,
        "prism": prism,
    }
    objs = []
    for el in s["elements"]:
        build = builders.get(el["geometry"]["type"])
        if build is None or (el["geometry"]["type"] == "cells" and not el["geometry"]["cells"]):
            continue
        obj = build(el)
        tag(obj, el)
        objs.append(obj)
    sections = [e for e in s["elements"] if e["geometry"]["type"] == "ray_section"]
    if sections:
        objs += passage(sections)
    return objs


def ring(g):
    """A section's rays as points: left is the passage tangent turned 90 degrees, up is +z."""
    c, t = Vector(g["station"]), Vector(g["tangent"])
    left = Vector((-t.y, t.x, 0)).normalized()
    up = Vector((0, 0, 1))
    return [
        None
        if r is None
        else c + r * (math.cos(math.radians(a)) * left + math.sin(math.radians(a)) * up)
        for a, r in zip(g["angles_deg"], g["radii_m"], strict=True)
    ]


def passage(sections):
    """The tube between consecutive sections. A quad is measured where all four rays hit rock;
    where any is unknown it is drawn red from the rays that exist, and skipped if fewer than 3."""
    rings = [ring(e["geometry"]) for e in sections]
    quads = {(s, half): ([], []) for s in ("measured", "unknown") for half in ("roof", "floor")}
    n = len(rings[0])
    for a, b in itertools.pairwise(rings):
        for k in range(n):
            pts = [a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]]
            have = [p for p in pts if p is not None]
            src = "measured" if len(have) == 4 else "unknown"
            if len(have) < 3:
                continue
            # Rays 0-180 degrees run left, up, right: the roof, hidden in the plan like a ceiling.
            half = "roof" if 0 < sections[0]["geometry"]["angles_deg"][k] < 180 else "floor"
            verts, faces = quads[(src, half)]
            base = len(verts)
            verts += [tuple(p) for p in have]
            faces.append(tuple(range(base, base + len(have))))
    objs = []
    for (src, half), (verts, faces) in quads.items():
        if faces:
            obj = new_object(f"passage {half} {src}", verts, faces, material(src, "wall"), src)
            obj["recce_id"] = f"passage-{half}-{src}"
            obj["recce_kind"] = "ceiling" if half == "roof" else "passage_floor"
            obj["recce_source"] = src
            objs.append(obj)
    return objs


def polyline(el):
    """A thin strip along the points, flat in plan, so it shows from above."""
    pts = [Vector(p) for p in el["geometry"]["points"]]
    verts, faces = [], []
    for a, b in itertools.pairwise(pts):
        d = (b - a).normalized()
        side = Vector((-d.y, d.x, 0)) * 0.05
        base = len(verts)
        verts += [tuple(a - side), tuple(b - side), tuple(b + side), tuple(a + side)]
        faces.append((base, base + 1, base + 2, base + 3))
    return new_object(el["id"], verts, faces, material(el["source"]), el["source"])


def dimension(m, a, b, slot=0):
    """A dimension line from face a, square to face b, with the value on it. Lines from the same
    face are spread along it by `slot` so their labels do not stack (iteration 3)."""
    pa0, pa1 = Vector((*a["p0"], 0)), Vector((*a["p1"], 0))
    frac = 0.5 + (0.18 * ((slot + 1) // 2) * (1 if slot % 2 else -1))
    ca = pa0 + (pa1 - pa0) * min(max(frac, 0.1), 0.9)
    nb = Vector((b["normal"][0], b["normal"][1], 0)).normalized()
    cb = ca - (ca - Vector((*b["p0"], 0))).dot(nb) * nb
    z = max(a["z1"], b["z1"]) + 0.05
    d = (cb - ca).normalized()
    side = Vector((-d.y, d.x, 0)) * 0.01
    verts = [(p.x, p.y, z) for p in (ca - side, cb - side, cb + side, ca + side)]
    line = new_object(f"dimension {m['id']}", verts, [(0, 1, 2, 3)], material("label"), "labels")
    line["recce_measurement"] = m["id"]
    mid = (ca + cb) / 2 + Vector((-d.y, d.x, 0)) * 0.06
    lab = label(f"{m['value_m']:.3f} ± {m['sigma_m']:.3f}", (mid.x, mid.y, z), "labels", 0.09)
    angle = math.atan2(d.y, d.x)
    if abs(angle) > math.pi / 2:  # keep text upright in the plan
        angle -= math.copysign(math.pi, angle)
    lab.rotation_euler = (0, 0, angle)
    lab["recce_measurement"] = m["id"]


def main():
    scene_path, out, mesh_path = args()
    s = sc.read(scene_path)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in (*sc.SOURCES, "labels", "reconstruction"):
        bpy.context.scene.collection.children.link(bpy.data.collections.new(name))
    objs = build_elements(s)
    by_id = {e["id"]: e for e in s["elements"]}
    slots = {}
    for m in s["measurements"]:
        if m["id"].startswith("distance-"):
            first = m["of"][0]
            slots[first] = slots.get(first, -1) + 1
            dimension(m, *(by_id[i]["geometry"] for i in m["of"]), slot=slots[first])
    if mesh_path:
        import_mesh(mesh_path)
    xs = [v.co.x for o in objs for v in o.data.vertices]
    ys = [v.co.y for o in objs for v in o.data.vertices]
    zs = [v.co.z for o in objs for v in o.data.vertices]
    centre = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    xspan, yspan = max(xs) - min(xs), max(ys) - min(ys)
    span = max(xspan, yspan)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.rotation_euler = (math.radians(40), 0, math.radians(30))
    bpy.context.scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("world")
    world.color = (0.95, 0.95, 0.93)
    bpy.context.scene.world = world
    r = bpy.context.scene.render
    r.engine = "BLENDER_WORKBENCH"
    bpy.context.scene.display.shading.color_type = "MATERIAL"
    r.resolution_x, r.resolution_y = 1600, 1200
    fit = max(xspan, yspan * 4 / 3) * 1.1
    top = camera("top", (centre[0], centre[1], max(zs) + 10), centre, ortho_scale=fit)
    persp = camera(
        "perspective",
        (centre[0] - span * 0.9, centre[1] - span * 1.1, max(zs) + span * 0.9),
        centre,
    )
    # The plan hides the ceiling so the floor and walls show from above.
    ceiling = [o for o in objs if o["recce_kind"] == "ceiling"]
    for o in ceiling:
        o.hide_render = True
    render(top, out / "plan.png", hide=["reconstruction"])
    render(persp, out / "perspective.png", hide=["reconstruction", "labels"])
    if mesh_path:
        render(persp, out / "perspective_with_mesh.png", hide=["labels"])
    for o in ceiling:
        o.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"))
    bpy.ops.export_scene.gltf(
        filepath=str(out / "scene.glb"), export_extras=True, export_format="GLB"
    )
    counts = {k: sum(o["recce_source"] == k for o in objs) for k in sc.SOURCES}
    print("RECCE BUILD", json.dumps({"objects": len(objs), "by_source": counts}))


if __name__ == "__main__":
    main()
