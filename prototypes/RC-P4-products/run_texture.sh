#!/bin/bash
# CPU: texture the cropped courtyard mesh from the same undistorted workspace and poses as the splat.
# usage: run_texture.sh [run name, default courtyard_3000_p1] [threads, default 2]
R=$HOME/.cache/recce; here=$(cd "$(dirname "$0")" && pwd)
run=${1:-courtyard_3000_p1}; threads=${2:-2}
out=$R/runs/p4/$run
start=$(date +%s)
"$R/p1env/bin/python" "$here/make_texrecon_scene.py" "$out/dense" "$out/texscene" || exit 1
"$R/texrecon-src/build/apps/texrecon/texrecon" --num_threads="$threads" --write_timings \
  "$out/texscene" "$out/mesh/mesh_crop.ply" "$out/mesh/textured" > "$out/log_texture.txt" 2>&1
rc=$?
echo "${run}_texture EXIT=$rc seconds=$(( $(date +%s) - start ))" >> "$R/runs/p4/status.txt"
exit $rc
