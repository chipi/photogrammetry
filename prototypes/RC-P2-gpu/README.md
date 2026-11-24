# RC-P2 — The expensive stages on the GPUs

**Proves:** The two platform facts the hardware pillar rests on. See the
[brief](../../docs/concept/RC-brief.md) §5.

**Proven when:** COLMAP's dense depth runs on one ETH3D scene on the X3 through a HIP build
(gfx1151) and on the GB10 through CUDA, and gsplat trains a splat on the GB10 — or each failure is
recorded with the error and what was tried. The GB10's available CUDA time under its shared-GPU
schedule is recorded. If neither GPU path works, the rented GPU becomes the planned CUDA worker and
the architecture sketch says so.

Status: **proven** (2026-11-24). Both halves pass. The GB10 half (dense depth through CUDA, gsplat
training) passed first; the X3 half (dense depth through a HIP build for gfx1151, in Docker) is also a
pass, not a recorded failure, with one intermittent GPU abort recorded in its section.

## Data

ETH3D `courtyard` (38 DSLR images, CC BY-NC-SA 4.0), downloaded for RC-P1 into
`~/.cache/recce/datasets/eth3d/courtyard`. The input model is RC-P1's GB10 COLMAP incremental model,
`~/.cache/recce/runs/p1/gb10/courtyard/colmap_incremental/0` (38/38 images registered, 23,042 points).

## Run (GB10)

The GB10 is `aarch64`, Ubuntu 24.04, with the host CUDA 13.0 toolkit (`nvcc` 13.0.88, `gcc` 13.3).
Everything installs under `~/.cache/recce` in the user account; nothing is system-wide.

Dense depth uses RC-P1's conda-forge environment (pycolmap 4.2.1, `has_cuda` True):

```bash
bash run_dense.sh courtyard 2000      # detached-friendly; writes runs/p2/gb10/dense_courtyard/
```

`run_dense.py` runs `pycolmap.undistort_images`, `pycolmap.patch_match_stereo` (CUDA; photometric
pass, then geometric pass) and `pycolmap.stereo_fusion` to `fused.ply`, and writes `results.json`.
`sample_gpu.sh` logs GPU utilisation, the compute processes and `free -g` every 5 s beside it.

The gsplat environment is a micromamba Python 3.12 (conda-forge, for `Python.h`) with PyPI packages:

```bash
micromamba create -p ~/.cache/recce/gsplatenv -c conda-forge python=3.12 pip
export CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=12.1
uv pip install --python ~/.cache/recce/gsplatenv/bin/python torch torchvision \
    --index-url https://download.pytorch.org/whl/cu130
uv pip install --python ~/.cache/recce/gsplatenv/bin/python gsplat==1.5.3 ninja setuptools wheel
git clone --branch v1.5.3 --depth 1 https://github.com/nerfstudio-project/gsplat.git ~/.cache/recce/gsplat-src
cd ~/.cache/recce/gsplat-src
uv pip install --python ~/.cache/recce/gsplatenv/bin/python -r examples/requirements.txt --no-build-isolation
bash run_gsplat.sh courtyard 7000     # runs examples/simple_trainer.py on the dense run's undistorted workspace
```

gsplat compiles its CUDA kernels on first import against the host `nvcc`; no conda CUDA toolkit is
needed. `ninja` must be on `PATH` (`run_gsplat.sh` adds the environment's `bin`).

## Results (GB10, 2026-11-24)

Small results (logs, `results.json`, GPU samples, gsplat stats) are in `~/.cache/recce/runs/p2/gb10/`
on the workstation. Images, depth maps and PLY files stay on the DGX.

### Dense depth through CUDA: pass

Scene `courtyard`, 38 images, `max_image_size` 2000 (undistorted images and depth maps are
2000×1295), pycolmap defaults otherwise (5 PatchMatch iterations, window radius 5, geometric
consistency on).

| Stage | Time |
|---|---|
| `undistort_images` | 3.2 s |
| `patch_match_stereo` (photometric pass about 14 s per view, geometric pass about 18 s per view) | 1168.7 s |
| `stereo_fusion` | 17.0 s |

Output: 38 photometric and 38 geometric depth maps; `fused.ply` with 734,016 points (19.8 MB).
The workspace is 3.1 GB.

GPU used: the GB10. The PatchMatch log prints `gpu_index: 0` and per-sweep CUDA timings
(`cudacc.cc` lines); `nvidia-smi` listed the pycolmap process as a compute process with up to
1,483 MiB, and GPU utilisation over the 236 samples averaged 86.6% (maximum 96%). The extraction and
matching stages of RC-P1 used the same build on the GPU.

### gsplat training: pass, with a low PSNR

gsplat 1.5.3, PyTorch 2.14.1+cu130 (PyPI aarch64 wheel, `torch.cuda.is_available()` True,
device `NVIDIA GB10`), `examples/simple_trainer.py default`, training on the dense run's undistorted
workspace (`--data_factor 1`, so 2000-px images; every 8th image held out, 5 of 38).

| Item | Value |
|---|---|
| Steps | 7,000 |
| CUDA kernel compile (first import, `sm_121`) | 38 s |
| Training time (trainer's own count) | 605 s; wall time 634 s with evaluation and video |
| Gaussians at the end | 3,301,622 |
| Held-out PSNR / SSIM / LPIPS | 18.83 dB / 0.652 / 0.372 |
| Peak torch memory / GPU process memory | 4.95 GB / 6.6 GB |

Speed falls as densification adds gaussians: about 19 it/s at step 2,300, 11 it/s at step 3,750,
5 it/s at step 6,500. The PSNR is low for a splat. The cause is not investigated; this run has 33
training views of an outdoor scene, 7,000 of the usual 30,000 steps and the default densification
settings, and none of those was varied. The number shows that the training path works on the GB10,
not that the splat is good; RC-P4 measures splat quality.

### Failures on the way, and what fixed them

- A `uv venv` on the system Python 3.12 has no `Python.h`; building `fused-ssim` failed with
  `fatal error: Python.h: No such file or directory`. A micromamba Python 3.12 has the headers; the
  rebuilt environment installed `fused-ssim` and compiled gsplat's kernels.
- The first gsplat kernel build failed with `RuntimeError: Ninja is required to load C++ extensions`
  because the environment's `bin` was not on `PATH`. Adding it fixed it.

### GB10 shared-GPU schedule and available CUDA time

The DGX serves production vLLM models. It runs in one of two modes, switched by the owner with
`gpu-mode`:

- `prod`: the vLLMs hold the GPU and leave about 15 GB of the 121 GB unified memory free. CUDA jobs
  of this prototype do not run in that mode.
- `free`: the vLLMs are stopped and the owner hands the GPU over for a job. Production use is mostly
  at night, so jobs run by day in `free` mode.

Operating rule: a GPU job on the GB10 runs only while the owner has switched it to `free` mode for
that job, and the mode goes back when the job ends. The agent never switches the mode itself.

Measured memory in `free` mode (three small speech services still held about 6.4 GB of GPU memory
through the whole session):

| Moment | `free -g` used / available |
|---|---|
| Before the dense run | 37 GB / 84 GB |
| Dense run, peak used / lowest available | 47 GB / 74 GB |
| gsplat run, peak used / lowest available | 50 GB / 71 GB |

The dense run raised host memory use by 10 GB over the idle level and gsplat by 13 GB. The dense run needed 1.5 GB of GPU
memory and gsplat 6.6 GB, both inside the 15 GB that `prod` mode leaves. Whether they run correctly
beside the live vLLMs has not been tried, and sharing the GPU would slow production serving; this
prototype does not test it. Elapsed GPU time of this session: about 20 min dense depth plus about 11
min gsplat, 31 min in total.

## X3 half: dense depth through HIP on gfx1151

Docker only; nothing installed on the host. Files in `x3/`: `Dockerfile`, `build.sh`, `run_dense.sh`
(host wrapper), `dense_in_container.sh` (stages, timing, GPU sampling).

```bash
bash x3/build.sh                      # image recce-p2-colmap-hip (JOBS defaults to half the cores)
bash x3/run_dense.sh courtyard 2000   # container recce-p2-dense; outputs in ~/.cache/recce/runs/p2/x3/
```

### What was used

- Machine: AMD Ryzen AI MAX+ 395 with Radeon 8060S (Strix Halo, gfx1151), 32 threads, 124 GB unified
  memory (BIOS VRAM carve-out 1 GiB, GTT 62 GB). Host Docker 29.7.2; the user is in the `docker` group.
- Base image `rocm/dev-ubuntu-24.04:7.2.4` (ROCm 7.2.4, hipcc clang 22), run with
  `--device=/dev/kfd --device=/dev/dri --group-add video --group-add render
  --security-opt seccomp=unconfined`. `rocminfo` lists `gfx1151` ("Radeon 8060S Graphics").
- COLMAP has no official HIP release, but upstream `main` has the backend (colmap/colmap PR 4635,
  merged as PR 4795 on 2026-10-01): the `.cu` files of `src/colmap/mvs` compile unmodified through
  `src/colmap/util/cuda_to_hip.h` with `-DHIP_ENABLED=ON`. No hipify and no port were needed. The image
  builds commit `57ded392` (`colmap -h` prints "COLMAP 4.3.0.dev0 ... with HIP").
- Configure flags: `-DCUDA_ENABLED=OFF -DHIP_ENABLED=ON -DCMAKE_HIP_ARCHITECTURES=gfx1151
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DGUI_ENABLED=OFF -DOPENGL_ENABLED=OFF
  -DONNX_ENABLED=OFF -DCGAL_ENABLED=OFF`. The build takes about 3.5 min with 16 jobs.
- Input: RC-P1's X3 incremental model and the `courtyard` images, mounted read-only. Dense options match
  the GB10 run: `max_image_size` 2000, defaults otherwise (geometric consistency on). The container is
  pinned to cores 16-31 (`--cpuset-cpus`, the `CPUSET` variable in `run_dense.sh`).

### Result: pass

| Stage | X3 (HIP) | GB10 (CUDA) |
|---|---|---|
| `image_undistorter` | 6 s | 3.2 s |
| `patch_match_stereo` photometric pass | 1,541 s (about 40 s per view) | about 14 s per view |
| `patch_match_stereo` geometric pass | 1,616 s (about 43 s per view) | about 18 s per view |
| `patch_match_stereo` total | 3,205 s (53.4 min) | 1,168.7 s |
| `stereo_fusion` | 9 s | 17.0 s |

Output: 38 photometric and 38 geometric depth maps; `fused.ply` with 725,221 points (19.6 MB; the GB10
run fused 734,016 from a different sparse model). The workspace is 3.1 GB. PatchMatch on the X3 took
about 2.7 times the GB10's time on the same scene and settings.

GPU used: the PatchMatch log prints per-sweep `cudacc.cc` timings (the HIP build reuses that file
name). `rocm-smi` inside the container, sampled every 5 s (631 samples), reports GPU use averaging
97.6% (maximum 100%). The 1 GiB VRAM carve-out stayed at about 0.94 GB used, so the working memory is
GTT (shared system memory): GTT in use ranged from 26.0 to 27.6 GB, part of it from other workloads
on the machine. Host memory available stayed between 25 and 43 GB.

### Failure recorded: an intermittent GPU abort

The first full run aborted at view 27 of 38 of the photometric pass, 993 s into `patch_match_stereo`
(exit 134):

```
rocdevice.cpp :3721: Callback: Queue 0x798c08600000 aborting with error :
HSA_STATUS_ERROR_MEMORY_APERTURE_VIOLATION: The agent attempted to access memory beyond the largest
legal address. code: 0x29
*** SIGABRT received by PID 163
```

Tried: running that view (`DSC_0316.JPG`) alone, photometric pass only, same settings, completes
(exit 0, about 45 s). A second full run with the same image, flags and inputs passed all 38 views in
both passes. The abort is not tied to that view and has not reproduced; its cause is not investigated.
It happened while other workloads were using the machine's GPU and unified memory, which may be a
factor but was not tested. Logs of the aborted run are in `~/.cache/recce/runs/p2/x3-fail1/`.

### Other failures on the way

- First configure failed with `Imported target "GLEW::GLEW" includes non-existent path
  ".../GLEW_INCLUDE_DIRS-NOTFOUND"`: SiftGPU needs GLEW even with `OPENGL_ENABLED=OFF`. Adding
  `libglew-dev` to the image fixed it.
- The first dense run was stopped about 11 minutes in and restarted with the container pinned to cores
  16-31, so another job could keep cores 0-3.
- `dense_in_container.sh` first counted depth maps with a non-recursive glob and reported 0; the maps
  are in the `dslr_images/` subfolder and the count now uses `find`.

### Images and containers

Image `recce-p2-colmap-hip:latest` (9.32 GB) built on `rocm/dev-ubuntu-24.04:7.2.4` (5.16 GB, pulled
for this), and the stopped container `recce-p2-dense` (492 kB writable layer). Remove with
`docker rm recce-p2-dense; docker rmi recce-p2-colmap-hip rocm/dev-ubuntu-24.04:7.2.4`.

## Not covered

- X3: one successful run and one aborted run only; the abort is not root-caused (see the X3 section).
  No second scene, no full-resolution run, no accuracy check of the fused cloud, and no run on an idle
  GPU (other workloads were using the X3's GPU memory and cores).
- One scene only (`courtyard`); `kicker` and `pipes` are not run. One setting only
  (`max_image_size` 2000); no full-resolution (6048×4032) dense run, so its time and memory are
  unknown.
- No accuracy check of the fused cloud against ETH3D's laser scan (RC-P4's job) and no comparison
  with a CPU dense run.
- gsplat: 7,000 steps only, one run, no seed repeat; the low PSNR is unexplained; no 30,000-step run;
  no check that the splat renders correctly beyond the trainer's own metrics.
- The coexistence of these jobs with the production vLLMs in `prod` mode (see above), and the
  throughput of a CUDA job while another GPU service is under load.
- The rented-GPU fallback in the brief applies only if neither GPU path works; the GB10 path works.
