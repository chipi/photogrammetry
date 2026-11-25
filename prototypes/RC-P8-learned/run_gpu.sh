#!/bin/bash
# RC-P8 on the GB10 in a `free` window: every scene, both variants, then RC-P4's 30,000-step
# courtyard splat. Run only while the DGX is in gpu-mode free.
# usage: nohup bash run_gpu.sh > ~/.cache/recce/runs/p8/driver.out 2>&1 &
R=$HOME/.cache/recce; here=$(cd "$(dirname "$0")" && pwd)
S=$R/runs/p8; status=$S/status.txt; rm -f "$S/STOP"
P=$R/p1env/bin/python; M=$R/mapanyenv/bin/python
say() { echo "$(date +%T) $*" >> "$status"; }
nohup bash "$R/p4/sample_gpu.sh" "$S/gpu_samples.log" >/dev/null 2>&1 &
sp=$!

scenes=()
for s in pipes kicker courtyard; do
  $P "$here/run_p8.py" prep-eth3d "$R/datasets/eth3d/$s" "$S/$s" > "$S/prep_$s.log" 2>&1
  say "prep_$s EXIT=$?"; scenes+=("$s")
done
for v in 42444515 42444821 42444793 42444858 42444873; do
  $P "$here/run_p8.py" prep-arkit "$R/datasets/arkitscenes/raw/Training/$v" "$S/a$v" \
    > "$S/prep_a$v.log" 2>&1
  say "prep_a$v EXIT=$?"; scenes+=("a$v")
done
for s in "${scenes[@]}"; do
  for v in none prior; do
    $M "$here/infer_mapanything.py" "$S/$s" --variant $v > "$S/$s.infer_$v.log" 2>&1
    say "infer_${s}_$v EXIT=$?"
    $P "$here/run_p8.py" colmap "$S/$s" --variant $v > "$S/$s.colmap_$v.log" 2>&1
    say "colmap_${s}_$v EXIT=$?"
  done
done
say "p8 done"

bash "$R/p4/run_gsplat.sh" courtyard30k "$R/runs/p4/courtyard_3000_p1/dense" 2 30000
say "courtyard30k splat EXIT=$?"
touch "$S/STOP"; wait $sp
say "driver finished"
