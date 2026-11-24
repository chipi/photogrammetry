#!/bin/bash
# Fetches the RC-P4 data on the DGX into ~/.cache/recce/datasets (never into git).
# ETH3D courtyard laser scans (CC BY-NC-SA 4.0; the "dslr_scan_eval" archive, 182 MB) and the
# Mip-NeRF 360 scenes (360_v2.zip, 12.5 GB; data licence not stated). Needs 7z from evalenv.
set -e
R=$HOME/.cache/recce
mkdir -p "$R/datasets/eth3d/courtyard" "$R/datasets/mipnerf360"
cd "$R/datasets/eth3d/courtyard"
curl -sSL -C - -o courtyard_dslr_scan_eval.7z https://www.eth3d.net/data/courtyard_dslr_scan_eval.7z
"$R/evalenv/bin/7z" x -y courtyard_dslr_scan_eval.7z   # -> courtyard/dslr_scan_eval/{scan1,scan2}.ply, scan_alignment.mlp
cd "$R/datasets/mipnerf360"
curl -sSL -C - -o 360_v2.zip http://storage.googleapis.com/gresearch/refraw360/360_v2.zip
# garden: outdoor, 185 photos, data_factor 4; counter: smallest indoor scene, 240 photos, data_factor 2.
unzip -q -o 360_v2.zip 'garden/*' 'counter/*' -d 360_v2
