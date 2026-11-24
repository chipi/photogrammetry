#!/usr/bin/env bash
# Host wrapper: runs the dense pipeline in container recce-p2-dense on the X3's GPU.
# usage: run_dense.sh [scene] [max_image_size]
set -euo pipefail
SCENE="${1:-courtyard}"; SIZE="${2:-2000}"
R="$HOME/.cache/recce"
OUT="$R/runs/p2/x3"; mkdir -p "$OUT"
docker rm -f recce-p2-dense >/dev/null 2>&1 || true
docker run --name recce-p2-dense --label recce-p2=1 \
  --device=/dev/kfd --device=/dev/dri --group-add video --group-add render \
  --cpuset-cpus "${CPUSET:-16-31}" --security-opt seccomp=unconfined --user "$(id -u):$(id -g)" \
  -v "$R/runs/p1/x3/$SCENE/colmap_incremental/0:/in/model:ro" \
  -v "$R/datasets/eth3d/$SCENE/images:/in/images:ro" \
  -v "$OUT:/out" \
  -v "$(cd "$(dirname "$0")" && pwd)/dense_in_container.sh:/dense_in_container.sh:ro" \
  recce-p2-colmap-hip:latest bash /dense_in_container.sh "$SIZE" 2>&1 | tee "$OUT/run.log"
