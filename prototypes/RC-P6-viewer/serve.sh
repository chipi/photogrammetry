#!/bin/bash
# Serve the viewer and the RC-P6 data on all interfaces, fixed port 8806.
# usage: serve.sh [port]
here=$(cd "$(dirname "$0")" && pwd)
root=$HOME/.cache/recce/runs/p6
ln -sf "$here/index.html" "$here/viewer.js" "$root/"
cd "$root" && exec python3 -m http.server "${1:-8806}" --bind 0.0.0.0
