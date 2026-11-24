#!/bin/bash
# Trains a splat with gsplat's example trainer on the undistorted COLMAP workspace of the dense run.
# usage: run_gsplat.sh <scene> [steps]
scene=${1:-courtyard}; steps=${2:-7000}
R=$HOME/.cache/recce; out=$R/runs/p2/gb10/gsplat_$scene
mkdir -p "$out"; rm -f "$out/STOP"
export CUDA_HOME=/usr/local/cuda PATH=$HOME/.cache/recce/gsplatenv/bin:/usr/local/cuda/bin:$PATH TORCH_CUDA_ARCH_LIST=12.1
free -g > "$out/free_before.txt"
nohup bash "$(dirname "$0")/sample_gpu.sh" "$out/gpu_samples.log" >/dev/null 2>&1 &
sp=$!
cd "$R/gsplat-src/examples"
start=$(date +%s)
"$R/gsplatenv/bin/python" simple_trainer.py default \
  --data_dir "$R/runs/p2/gb10/dense_$scene/dense" --data_factor 1 \
  --result_dir "$out/result" --max_steps "$steps" \
  --eval_steps "$steps" --save_steps "$steps" --disable_viewer > "$out/log.txt" 2>&1
rc=$?
echo "wall_seconds=$(( $(date +%s) - start ))" > "$out/wall.txt"
echo "gsplat_$scene EXIT=$rc" >> "$R/runs/p2/gb10/status.txt"
touch "$out/STOP"; wait $sp
