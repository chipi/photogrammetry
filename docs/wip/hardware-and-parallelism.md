# Hardware and parallelism

Input to the brief. From the operator on 2026-11-23, plus what was read off the X3 itself.

## The machines

| Machine | CPU / GPU | Memory | GPU API | Notes |
|---|---|---|---|---|
| MacBook Pro M4 Pro | Apple silicon | 48 GB | Metal | Daily driver; the field machine. Apple Object Capture runs only here (and on iOS). |
| DGX Spark (GB10) | ARM64 + Blackwell, compute capability 12.1 | 128 GB unified | CUDA 13 | GPU shared with other workloads on a schedule, so its availability varies. ARM64 wheels missing for much of the stack. |
| X3 (GMKtec EVO-X3) | AMD Ryzen AI Max+ 395, 32 threads, Radeon 8060S (RDNA 3.5) | 128 GB | ROCm/HIP or Vulkan | Linux. The likely coordinator. |
| ~~iMac Pro~~ | Intel Xeon W, AMD Vega | ≥ 64 GB | Metal only, no CUDA | **Out of the design (2026-11-24).** Most of the stack ships no macOS x86_64 wheels; its cost exceeds its contribution. |

Four GPU platforms: CUDA, Metal, HIP/Vulkan and an older Metal-on-Intel. Existing tools mostly
assume one NVIDIA box.

### Measured in Step 0 (2026-11-24)

- **pycolmap packaging.** PyPI's pycolmap 4.2.1 has wheels for x86_64 Linux, Apple silicon and
  Windows, all CPU only: no CUDA, no Metal, no Linux ARM. On the GB10, conda-forge's CUDA build
  (through micromamba, user-level) runs SIFT extraction and matching on the GPU, about three times
  faster than the CPU on the X3 or the M4 Pro ([RC-P1](https://github.com/chipi/recce/tree/main/prototypes/RC-P1-registration)).
- **The GB10's schedule.** In gpu-mode `prod` the production LLMs leave about 15 GB of the 121 GB
  free. Recce GPU work runs in a `free` window (by day under the owner's standing go; the homelab
  session switches back to `prod` and verifies). CUDA dense depth plus a gsplat run peaked at
  50 GB used ([RC-P2](https://github.com/chipi/recce/tree/main/prototypes/RC-P2-gpu)).
- **Memory.** Registering a 38-image ETH3D scene peaks at 28 GB resident (M4 Pro).
- **The X3's GPU.** No ROCm on the host; COLMAP has no official HIP backend. The attempt runs in a
  ROCm container, nothing installed on the host.
- **Mapping speed.** On the busy X3 COLMAP's incremental mapper took 57 s on kicker, the M4 Pro
  17 s, the GB10 22 s; GLOMAP 3–4 times faster on every machine.

Summary of all findings: [Step 0 status and findings](step0-status.md).

## The operator's goal, in their words (paraphrased)

Large photo sets in large formats need parallelism, and existing projects don't use the hardware
well. Use everything available: a GPU where there is one, other machines through workers that are
deployed to them, and possibly more machines later. Something easy works on the laptop alone. In
the field, the laptop uploads photos; the main service may run on the X3 and hand work to the GB10
and others. Full flexibility; explore every form of parallelism.

## Forms of parallelism to explore

1. **Per-item fan-out** — feature extraction per image, matching per pair, depth per view.
   Embarrassingly parallel; most of the hours.
2. **Spatial partitioning** — split a large scene into overlapping clusters, reconstruct each on a
   different machine, merge. COLMAP's hierarchical mapper does this on one box.
3. **Streaming pipeline** — work starts while photos are still arriving; the laptop builds a quick
   preview, bigger machines take later stages.
4. **Comparative runs** — classical and learned pipelines side by side on different machines, the
   difference itself a quality signal.
5. **Capability placement** — workers advertise CUDA / Metal / HIP / CPU, memory and availability
   (including whether a shared GPU is free); the coordinator places each stage. Workers join and leave.

## Capture devices, in the order the operator plans to test

1. iPhone 15 Pro (ProRAW, LiDAR, ARKit poses)
2. GoPro
3. Nikon D850 and Sony Alpha 1 (RAW)
4. DJI Mini 4 Pro drone
5. Robots, with depth cameras and possibly motorised sliders still to choose

Underwater photography is a first-class interest of the operator, not an edge case.
