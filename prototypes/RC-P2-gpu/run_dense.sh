#!/bin/bash
# Runs the dense stage detached-friendly. usage: run_dense.sh <scene> [max_image_size]
scene=${1:-courtyard}; size=${2:-2000}
R=$HOME/.cache/recce; out=$R/runs/p2/gb10/dense_$scene
mkdir -p "$out"; rm -f "$out/STOP"
free -g > "$out/free_before.txt"
nohup bash "$(dirname "$0")/sample_gpu.sh" "$out/gpu_samples.log" >/dev/null 2>&1 &
sp=$!
"$R/p1env/bin/python" "$(dirname "$0")/run_dense.py" "$R/datasets/eth3d/$scene" "$R/runs/p1/gb10/$scene" "$out" --max-image-size "$size" > "$out/log.txt" 2>&1
echo "dense_$scene EXIT=$?" >> "$R/runs/p2/gb10/status.txt"
touch "$out/STOP"; wait $sp
