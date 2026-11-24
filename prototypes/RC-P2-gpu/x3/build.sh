#!/usr/bin/env bash
# Builds image recce-p2-colmap-hip. At most half the cores (JOBS) so other jobs on the X3 keep running.
set -euo pipefail
cd "$(dirname "$0")"
JOBS="${JOBS:-$(( $(nproc) / 2 ))}"   # build in a container: pin with CPUSET too
docker build --label recce-p2=1 --build-arg JOBS="$JOBS" -t recce-p2-colmap-hip:latest . 2>&1 | tee "${1:-build.log}"
echo "BUILD EXIT=${PIPESTATUS[0]}"
