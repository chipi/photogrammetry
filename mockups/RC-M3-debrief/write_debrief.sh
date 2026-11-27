#!/usr/bin/env bash
# RC-M3: one agent writes the debrief through debrief_server.py's tools only, then verify.py
# replays every handle. Writes data/agent_raw.json, data/annotations.json, data/debrief.json.
#   mockups/RC-M3-debrief/write_debrief.sh [model]      (default sonnet)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
MODEL=${1:-sonnet}
DATA=$HERE/data
rm -f "$DATA/annotations.json"
cat >"$DATA/mcp.json" <<EOF
{"mcpServers": {"recce": {"command": "uv", "args": ["run", "--directory",
  "$REPO/prototypes/RC-P3-quality", "python", "$HERE/debrief_server.py"]}}}
EOF
ALLOWED=mcp__recce__get_summary,mcp__recce__list_regions,mcp__recce__get_region,\
mcp__recce__get_products,mcp__recce__list_cameras,mcp__recce__place_label,mcp__recce__place_camera,\
mcp__recce__list_annotations
claude -p "$(cat "$HERE/prompt.md")" --model "$MODEL" --output-format json \
  --mcp-config "$DATA/mcp.json" --strict-mcp-config --tools '' --allowedTools "$ALLOWED" \
  </dev/null >"$DATA/agent_raw.json"
echo "agent done: $(wc -c <"$DATA/agent_raw.json") bytes"
uv run --directory "$REPO/prototypes/RC-P3-quality" python "$HERE/verify.py" "$DATA"
