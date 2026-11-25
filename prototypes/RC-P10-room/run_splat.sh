#!/bin/bash
# Trains a splat per room on the DGX from splat_prep.py's input, in ARKit's metric frame.
# usage: run_splat.sh <video> [steps]   (input synced to $R/runs/p10/<video>/splat_input first)
# Held-out views are every 8th image, as in RC-P4. Run only in a `free` GPU window.
vid=$1; steps=${2:-7000}
R=$HOME/.cache/recce
out=$R/runs/p10/$vid/splat
mkdir -p "$out"
export CUDA_HOME=/usr/local/cuda PATH=$R/gsplatenv/bin:/usr/local/cuda/bin:$PATH TORCH_CUDA_ARCH_LIST=12.1
cd "$R/gsplat-src/examples" || exit 2
start=$(date +%s)
"$R/gsplatenv/bin/python" simple_trainer.py default \
  --data-dir "$R/runs/p10/$vid/splat_input" --data-factor 1 --test-every 8 \
  --no-normalize-world-space \
  --result-dir "$out/result" --max-steps "$steps" \
  --eval-steps "$steps" --save-steps "$steps" --save-ply --ply-steps "$steps" \
  --disable-viewer > "$out/log.txt" 2>&1
rc=$?
echo "wall_seconds=$(( $(date +%s) - start ))" > "$out/wall.txt"
echo "splat_${vid}_${steps} EXIT=$rc" >> "$R/runs/p10/status.txt"
exit $rc
