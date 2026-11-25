// RC-P6: the RC-P4 textured mesh and a ~1 M gaussian splat in one three.js scene.
// Query parameters: mesh, mtl, splat (paths), auto=1 (orbit by itself), dpr, maxtex, window,
// sync=1 (a 1-pixel readback after each frame, so a frame time includes the GPU),
// view=<12 numbers> (a COLMAP camera-to-world 3x4, row-major, model frame) with fov=<vertical deg>.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { SparkRenderer, SplatMesh } from "@sparkjsdev/spark";

const q = new URLSearchParams(location.search);
const MESH = q.get("mesh") ?? "data/mesh/textured.obj";
const MTL = q.get("mtl") ?? "data/mesh/textured.mtl";
const SPLAT = q.get("splat") ?? "data/splat/courtyard_1m.ply";
const mobile = /iPhone|iPad|Android/.test(navigator.userAgent);
// iOS Safari kills a tab near 1 GB of textures; the 4096 px atlases are halved there.
const MAX_TEX = Number(q.get("maxtex") ?? (mobile ? 2048 : 0));
const WINDOW = Number(q.get("window") ?? 240);
const SYNC = q.get("sync") === "1";
const dpr = Math.min(Number(q.get("dpr") ?? window.devicePixelRatio), 2);

const $ = (id) => document.getElementById(id);
const stats = (window.p6Stats = {
  ready: false, fps_median: null, fps_min: null, fps_window: WINDOW, frames: 0, dpr, mobile,
  maxtex: MAX_TEX, splats: 0, mesh_faces: 0, mesh_materials: 0, load_s: {}, error: null,
}); // fmt: skip

const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: "high-performance" });
renderer.setPixelRatio(dpr);
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const gl = renderer.getContext();
const px = new Uint8Array(4);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101214);
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.05, 500);
const spark = new SparkRenderer({ renderer });
scene.add(spark);

// The result is z-up (the scan frame); three.js is y-up.
const world = new THREE.Group();
world.rotation.x = -Math.PI / 2;
scene.add(world);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.autoRotate = q.get("auto") === "1";
controls.autoRotateSpeed = 4;

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

async function loadTexture(url) {
  const img = new Image();
  img.src = url;
  await img.decode();
  let source = img;
  if (MAX_TEX && img.width > MAX_TEX) {
    const c = document.createElement("canvas");
    c.width = c.height = MAX_TEX;
    const ctx = c.getContext("2d");
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, 0, 0, MAX_TEX, MAX_TEX);
    source = c;
  }
  const t = new THREE.Texture(source); // flipY stays true: OBJ uv origin is bottom-left
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.needsUpdate = true;
  return t;
}

async function loadMesh() {
  const t0 = performance.now();
  const base = MESH.slice(0, MESH.lastIndexOf("/") + 1);
  const [objText, mtlText] = await Promise.all([
    fetch(MESH).then((r) => r.text()),
    fetch(MTL).then((r) => r.text()),
  ]);
  const maps = {}; // material name -> atlas file, read from the .mtl
  let cur = null;
  for (const line of mtlText.split("\n")) {
    const [k, v] = line.trim().split(/\s+/);
    if (k === "newmtl") cur = v;
    else if (k === "map_Kd") maps[cur] = line.trim().split(/\s+/).slice(1).join(" ");
  }
  const group = new OBJLoader().parse(objText);
  const materials = {};
  await Promise.all(
    Object.entries(maps).map(async ([name, file]) => {
      // Unlit: the atlas colour is the measurement, not a lighting design.
      materials[name] = new THREE.MeshBasicMaterial({
        map: await loadTexture(base + file),
        side: THREE.DoubleSide,
      });
    }),
  );
  let faces = 0;
  group.traverse((o) => {
    if (!o.isMesh) return;
    // One object with a geometry group per usemtl: OBJLoader gives it a material array.
    const pick = (m) => materials[m.name] ?? new THREE.MeshBasicMaterial({ color: 0x888888 });
    o.material = Array.isArray(o.material) ? o.material.map(pick) : pick(o.material);
    faces += o.geometry.attributes.position.count / 3;
  });
  stats.mesh_faces = faces;
  stats.mesh_materials = Object.keys(materials).length;
  stats.load_s.mesh = (performance.now() - t0) / 1000;
  world.add(group);
  return group;
}

async function loadSplat() {
  const t0 = performance.now();
  const splat = new SplatMesh({ url: SPLAT });
  await splat.initialized;
  stats.splats = splat.numSplats;
  stats.load_s.splat = (performance.now() - t0) / 1000;
  world.add(splat);
  return splat;
}

function frameCamera(obj) {
  if (q.has("view")) {
    const v = q.get("view").split(",").map(Number);
    const c2w = new THREE.Matrix4().set(...v, 0, 0, 0, 1);
    c2w.multiply(new THREE.Matrix4().makeScale(1, -1, -1)); // OpenCV camera axes to three.js
    world.updateMatrix();
    c2w.premultiply(world.matrix);
    const pos = new THREE.Vector3();
    const quat = new THREE.Quaternion();
    c2w.decompose(pos, quat, new THREE.Vector3());
    camera.position.copy(pos);
    camera.quaternion.copy(quat);
    camera.fov = Number(q.get("fov") ?? 62.4);
    camera.updateProjectionMatrix();
    controls.target.copy(pos).add(new THREE.Vector3(0, 0, -3).applyQuaternion(quat));
    controls.update();
    return;
  }
  const box = new THREE.Box3().setFromObject(obj);
  const size = box.getSize(new THREE.Vector3());
  const centre = box.getCenter(new THREE.Vector3());
  controls.target.copy(centre);
  camera.position.copy(centre).add(new THREE.Vector3(0.9, 0.5, 0.9).multiplyScalar(size.length()));
  controls.update();
}

const times = [];
let last = performance.now();
function tick(now) {
  requestAnimationFrame(tick);
  times.push(now - last);
  last = now;
  if (times.length > WINDOW) times.shift();
  stats.frames++;
  if (times.length === WINDOW && stats.frames % 30 === 0) {
    const fps = times.map((dt) => 1000 / dt).sort((a, b) => a - b);
    stats.fps_median = fps[WINDOW >> 1];
    stats.fps_min = fps[0];
    $("fps").textContent = `fps ${stats.fps_median.toFixed(1)} (median of ${WINDOW})`;
  }
  controls.update();
  renderer.render(scene, camera);
  if (SYNC) gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); // blocks until the GPU is done
}

try {
  $("info").textContent = "loading mesh and splat";
  const [mesh, splat] = await Promise.all([loadMesh(), loadSplat()]);
  $("showMesh").onchange = (e) => (mesh.visible = e.target.checked);
  $("showSplat").onchange = (e) => (splat.visible = e.target.checked);
  frameCamera(mesh);
  const dbg = gl.getExtension("WEBGL_debug_renderer_info");
  stats.gpu = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : "unknown";
  $("info").textContent =
    `${stats.splats.toLocaleString()} gaussians, ${stats.mesh_faces.toLocaleString()} faces, ` +
    `${stats.mesh_materials} atlases, dpr ${dpr}`;
  stats.ready = true;
} catch (e) {
  stats.error = String(e);
  $("info").textContent = `error: ${e}`;
  throw e;
}
requestAnimationFrame(tick);
