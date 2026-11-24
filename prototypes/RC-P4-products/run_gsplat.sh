#!/bin/bash
# Trains a splat with gsplat's example trainer and records held-out PSNR / SSIM / LPIPS.
# usage: run_gsplat.sh <name> <data_dir> <data_factor> [steps]
#   Mip-NeRF 360:  run_gsplat.sh garden  $R/datasets/mipnerf360/360_v2/garden 4
#                  run_gsplat.sh counter $R/datasets/mipnerf360/360_v2/counter 2
#   ETH3D (same poses as the mesh): run_gsplat.sh courtyard $R/runs/p4/courtyard_3000/dense 1
# Held-out views are every 8th image (the trainer's test_every default, the Mip-NeRF 360 convention).
# Run only while the owner has switched the DGX to free mode.
name=$1; data=$2; factor=$3; steps=${4:-30000}
R=$HOME/.cache/recce; here=$(cd "$(dirname "$0")" && pwd)
out=$R/runs/p4/gsplat_$name
mkdir -p "$out"; rm -f "$out/STOP"
export CUDA_HOME=/usr/local/cuda PATH=$R/gsplatenv/bin:/usr/local/cuda/bin:$PATH TORCH_CUDA_ARCH_LIST=12.1
free -g > "$out/free_before.txt"
nohup bash "$here/sample_gpu.sh" "$out/gpu_samples.log" >/dev/null 2>&1 &
sp=$!
cd "$R/gsplat-src/examples"
start=$(date +%s)
"$R/gsplatenv/bin/python" simple_trainer.py default \
  --data_dir "$data" --data_factor "$factor" --test_every 8 \
  --result_dir "$out/result" --max_steps "$steps" \
  --eval_steps 7000 "$steps" --save_steps "$steps" --save_ply --ply_steps "$steps" \
  --disable_viewer > "$out/log.txt" 2>&1
rc=$?
echo "wall_seconds=$(( $(date +%s) - start ))" > "$out/wall.txt"
echo "gsplat_${name}_${steps} EXIT=$rc" >> "$R/runs/p4/status.txt"
touch "$out/STOP"; wait $sp
