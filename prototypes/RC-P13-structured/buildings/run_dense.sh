#!/usr/bin/env bash
# Dense depth for the UseGeo given-pose model in the RC-P2 HIP container on the X3. Reuses RC-P2's
# in-container script (read-only). Pinned to cores CPUSET (default 16-31). The container runs
# detached (448 depth maps take hours); follow $RUN/dense/stages.txt, then remove the container:
#   docker logs recce-p13-dense; docker rm recce-p13-dense
# usage: run_dense.sh [max_image_size, default 1000]
set -euo pipefail
R="${RECCE_DATA_DIR:-$HOME/.cache/recce}"
RUN="$R/runs/p13/buildings/usegeo1"
IMAGES="$R/datasets/usegeo/Dataset-1/Camera_Inputs/Metashape_outputs_images"
P2="$(cd "$(dirname "$0")/../../RC-P2-gpu/x3" && pwd)"
OUT="$RUN/dense"
rm -rf "$OUT"
mkdir -p "$OUT"
docker rm -f recce-p13-dense >/dev/null 2>&1 || true
docker run -d --name recce-p13-dense --label recce-p13=1 \
  --device=/dev/kfd --device=/dev/dri --group-add video --group-add render \
  --cpuset-cpus "${CPUSET:-16-31}" --security-opt seccomp=unconfined --user "$(id -u):$(id -g)" \
  -v "$RUN/given:/in/model:ro" -v "$IMAGES:/in/images:ro" -v "$OUT:/out" \
  -v "$P2/dense_in_container.sh:/dense_in_container.sh:ro" \
  recce-p2-colmap-hip:latest bash -c 'bash /dense_in_container.sh "$0"; echo "DENSE EXIT=$?" >> /out/stages.txt' \
  "${1:-1000}"
