#!/usr/bin/env bash
# Dense depth for each RC-P12 Satil model in the RC-P2 HIP container on the X3, one model at a time.
# Reuses RC-P2's in-container script (read-only). Pinned to cores CPUSET (default 16-31).
set -euo pipefail
R="${RECCE_DATA_DIR:-$HOME/.cache/recce}"
WORK="$R/runs/p12/recon"
P2="$(cd "$(dirname "$0")/../RC-P2-gpu/x3" && pwd)"
for model in "$WORK"/sparse/*/; do
  m="$(basename "$model")"
  OUT="$WORK/dense_$m"; mkdir -p "$OUT"
  docker rm -f recce-p12-dense >/dev/null 2>&1 || true
  docker run --name recce-p12-dense --label recce-p12=1 \
    --device=/dev/kfd --device=/dev/dri --group-add video --group-add render \
    --cpuset-cpus "${CPUSET:-16-31}" --security-opt seccomp=unconfined --user "$(id -u):$(id -g)" \
    -v "$model:/in/model:ro" -v "$WORK/images:/in/images:ro" -v "$OUT:/out" \
    -v "$P2/dense_in_container.sh:/dense_in_container.sh:ro" \
    recce-p2-colmap-hip:latest bash /dense_in_container.sh 2737 2>&1 | tee "$OUT/run.log"
  echo "MODEL $m DENSE EXIT=${PIPESTATUS[0]}"
  docker rm recce-p12-dense >/dev/null
done
