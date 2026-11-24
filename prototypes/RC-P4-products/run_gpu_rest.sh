#!/bin/bash
# After run_courtyard.sh 3000 p1: GT-pose control (only if step 1 took <= 75 min), then the three
# 30,000-step splats, in the order of value. Stops starting jobs when the 4-hour GPU budget is spent.
# usage: nohup bash run_gpu_rest.sh &     (starts after run_courtyard.sh 3000 p1 has finished)
R=$HOME/.cache/recce; here=$(cd "$(dirname "$0")" && pwd)
status=$R/runs/p4/status.txt; log=$R/runs/p4/driver.txt
budget=$(( 4 * 3600 ))
t0=$(awk '{print $2}' "$R/runs/p4/gpu_start.txt")
say() { echo "$(date +%T) $*" >> "$log"; }
spent() { echo $(( $(date +%s) - t0 )); }

s1=2000   # step 1 had already finished (1,930 s dense + CPU steps) when the driver was restarted


if [ "$s1" -le 4500 ]; then
  say "start gt control"; bash "$here/run_courtyard.sh" 3000 gt; say "gt control done, spent $(spent)s"
else
  say "gt control skipped: step 1 took ${s1}s > 4500s"
fi

job() { # name, min seconds needed, command...
  local name=$1 need=$2; shift 2
  if [ $(( $(spent) + need )) -gt "$budget" ]; then say "skip $name: budget (spent $(spent)s, needs $need s)"; return; fi
  say "start $name"; "$@"; say "$name done, spent $(spent)s"
}
job garden 2700 bash "$here/run_gsplat.sh" garden "$R/datasets/mipnerf360/360_v2/garden" 4
job counter 1500 bash "$here/run_gsplat.sh" counter "$R/datasets/mipnerf360/360_v2/counter" 2
job courtyard_splat 2400 bash "$here/run_gsplat.sh" courtyard "$R/runs/p4/courtyard_3000_p1/dense" 2
say "driver finished, spent $(spent)s"
