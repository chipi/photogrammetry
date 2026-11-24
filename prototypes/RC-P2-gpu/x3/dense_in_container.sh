#!/usr/bin/env bash
# Runs inside recce-p2-colmap-hip. Inputs /in/model and /in/images (read-only), outputs /out.
# usage: dense_in_container.sh [max_image_size]
set -uo pipefail
SIZE="${1:-2000}"
WS=/out/dense
mkdir -p "$WS"
rm -f /out/STOP
(
  while [ ! -e /out/STOP ]; do
    echo "$(date +%T) $(rocm-smi --showuse --showmemuse --showmeminfo vram gtt --json 2>/dev/null | tr -d "\n ") | avail_GB=$(free -g | awk '/Mem:/{print $7}')" >> /out/gpu_samples.log
    sleep 5
  done
) &
SAMPLER=$!

stage() {
  local name="$1"; shift
  local t0=$SECONDS
  "$@" > "/out/$name.log" 2>&1
  local rc=$?
  echo "STAGE $name rc=$rc seconds=$((SECONDS - t0))" | tee -a /out/stages.txt
  return $rc
}

: > /out/stages.txt
colmap -h 2>&1 | head -3 > /out/colmap_version.txt
stage undistort colmap image_undistorter --image_path /in/images --input_path /in/model \
    --output_path "$WS" --output_type COLMAP --max_image_size "$SIZE" \
  && stage patch_match_stereo colmap patch_match_stereo --workspace_path "$WS" --workspace_format COLMAP \
    --PatchMatchStereo.max_image_size "$SIZE" --PatchMatchStereo.geom_consistency true \
  && stage stereo_fusion colmap stereo_fusion --workspace_path "$WS" --workspace_format COLMAP \
    --input_type geometric --output_path "$WS/fused.ply"
RC=$?
echo "depth_maps_photometric=$(find "$WS/stereo/depth_maps" -name "*.photometric.bin" | wc -l)" >> /out/stages.txt
echo "depth_maps_geometric=$(find "$WS/stereo/depth_maps" -name "*.geometric.bin" | wc -l)" >> /out/stages.txt
[ -f "$WS/fused.ply" ] && grep -a -m1 "element vertex" "$WS/fused.ply" >> /out/stages.txt
touch /out/STOP; wait $SAMPLER
exit $RC
