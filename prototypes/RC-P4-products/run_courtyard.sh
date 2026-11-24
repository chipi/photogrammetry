#!/bin/bash
# GPU phase, ETH3D courtyard: align -> dense (GPU) -> fusion -> Delaunay mesh -> ETH3D scores.
# usage: run_courtyard.sh [max_image_size] [p1|gt]   (default 3000, half of 6048x4032; p1 = RC-P1 poses)
# "gt" is the control run: dense from ETH3D's own ground-truth poses, which separates registration error from dense error.
# Run only while the owner has switched the DGX to free mode. Detached: nohup bash run_courtyard.sh &
set -u
size=${1:-3000}
R=$HOME/.cache/recce; here=$(cd "$(dirname "$0")" && pwd)
P1=$R/p1env/bin/python; GS=$R/gsplatenv/bin/python
scene=$R/datasets/eth3d/courtyard
gt=$scene/courtyard/dslr_scan_eval/scan_alignment.mlp
poses=${2:-p1}
out=$R/runs/p4/courtyard_${size}_$poses
mkdir -p "$out"; rm -f "$out/STOP"
status=$R/runs/p4/status.txt

step() { # name, then the command; stops the chain on failure
  local name=$1; shift
  local t=$(date +%s)
  "$@" >> "$out/log_$name.txt" 2>&1; local rc=$?
  echo "courtyard_${size}_${poses}_$name EXIT=$rc seconds=$(( $(date +%s) - t ))" >> "$status"
  [ $rc -eq 0 ] || { touch "$out/STOP"; exit $rc; }
}

free -g > "$out/free_before.txt"
if [ "$poses" = gt ]; then
  model=$scene/dslr_calibration_jpg   # already in the scan frame
else
  step align "$P1" "$here/align_model.py" "$R/runs/p1/gb10/courtyard/colmap_incremental/0" \
    "$scene/dslr_calibration_jpg" "$out/align"
  model=$out/align/aligned
fi

nohup bash "$here/sample_gpu.sh" "$out/gpu_samples.log" >/dev/null 2>&1 &
sp=$!
step dense "$P1" "$here/run_dense.py" "$scene" "$model" "$out" --max-image-size "$size"
touch "$out/STOP"; wait $sp; rm -f "$out/STOP"   # GPU work ends here; the rest is CPU

bin=$R/mve-src/build/ETH3DMultiViewEvaluation
# Scores cover the scene only: cloud and mesh are cropped to the scans' bounding box (+0.5 m).
step bbox "$GS" "$here/crop.py" bbox "$gt" "$out/bbox.json"
step mesh "$P1" "$here/run_mesh.py" "$out/dense" "$out/mesh"   # Delaunay; add --poisson to retry Poisson
step crop_dense "$GS" "$here/crop.py" apply "$out/bbox.json" "$out/dense/fused.ply" "$out/fused_crop.ply"
step crop_mesh "$GS" "$here/crop.py" apply "$out/bbox.json" "$out/mesh/mesh_delaunay.ply" "$out/mesh/mesh_crop.ply"
step eval_dense "$P1" "$here/run_eval.py" "$out/fused_crop.ply" "$gt" "$out/eval_dense.json" --binary "$bin"
step sample_mesh "$GS" "$here/sample_mesh.py" "$out/mesh/mesh_crop.ply" "$out/mesh/points_crop.ply"
step eval_mesh "$P1" "$here/run_eval.py" "$out/mesh/points_crop.ply" "$gt" "$out/eval_mesh.json" --binary "$bin"
touch "$out/STOP"
