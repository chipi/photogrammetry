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
