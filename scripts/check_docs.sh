#!/usr/bin/env bash
# Docs checklist. Exits non-zero if any check fails.
set -u
cd "$(dirname "$0")/.."

fail=0
pass() { echo "PASS  $1"; }
skip() { echo "SKIP  $1"; }
bad()  { echo "FAIL  $1"; sed 's/^/        /' <<<"$2"; fail=1; }

mapfile -t MD < <(find docs -name '*.md' -not -path 'docs/.*' | sort; [ -f README.md ] && echo README.md)

# (1) relative markdown links resolve
out=""
for f in "${MD[@]}"; do
  dir=$(dirname "$f")
  while IFS= read -r link; do
    target=${link%%#*}
    target=${target%%\?*}
    [ -z "$target" ] && continue
    case "$target" in http*|mailto:*|/*) continue ;; esac
    [ -e "$dir/$target" ] || out+="$f -> $link"$'\n'
  done < <(sed '/^```/,/^```/d' "$f" | grep -oE '\]\([^)[:space:]]+\)' | sed -E 's/^\]\((.*)\)$/\1/')
done
[ -z "$out" ] && pass "relative links resolve" || bad "broken relative links" "${out%$'\n'}"

# (2) voice spot-checks
out=$(grep -nIiE 'the user shall|in order to|it is worth noting|at this point in time' "${MD[@]}" 2>/dev/null)
[ -z "$out" ] && pass "voice phrases" || bad "banned voice phrases" "$out"

# (3) per-artifact checks
need() { # dir glob phrase...
  local dir=$1 glob=$2; shift 2
  local o="" f p
  for f in $dir/$glob; do
    [ -e "$f" ] || continue
    for p in "$@"; do grep -q "$p" "$f" || o+="$f: missing '$p'"$'\n'; done
  done
  echo -n "$o"
}
if [ -d docs/prd ]; then
  o=$(need docs/prd 'PRD-*.md' 'Why this is a PRD')
  [ -z "$o" ] && pass "PRD gating sentence" || bad "PRD gating sentence" "$o"
else skip "PRD checks (no docs/prd yet)"; fi
if [ -d docs/rfc ]; then
  o=$(need docs/rfc 'RFC-*.md' 'Why this is an RFC' 'Alternatives considered' 'Closing evidence')
  [ -z "$o" ] && pass "RFC sections" || bad "RFC sections" "$o"
else skip "RFC checks (no docs/rfc yet)"; fi
if [ -d docs/adr ]; then
  o=$(need docs/adr 'ADR-*.md' 'Status' 'Alternatives considered')
  for f in docs/adr/ADR-*.md; do
    [ -e "$f" ] || continue
    grep -qE 'Accepted|Superseded' "$f" || o+="$f: Status is not Accepted or Superseded"$'\n'
    grep -q 'Proposed' "$f" && o+="$f: contains 'Proposed'"$'\n'
  done
  [ -z "$o" ] && pass "ADR sections" || bad "ADR sections" "${o%$'\n'}"
else skip "ADR checks (no docs/adr yet)"; fi
if [ -d docs/uxs ]; then
  o=$(need docs/uxs 'UXS-*.md' 'Visual fidelity' 'Boundary note')
  [ -z "$o" ] && pass "UXS fields" || bad "UXS fields" "$o"
else skip "UXS checks (no docs/uxs yet)"; fi

# (4) no private-guide leak
out=$(grep -rnI 'Process Guide' docs README.md AGENTS.md CLAUDE.md 2>/dev/null)
[ -z "$out" ] && pass "no private-guide references" || bad "private-guide references" "$out"

# (5) no data files tracked
if git rev-parse --git-dir >/dev/null 2>&1; then
  out=$(git ls-files -- 'data/*' 'datasets/*' 'captures/*' 'outputs/*' 'runs/*' \
    '*.NEF' '*.ARW' '*.DNG' '*.dng' '*.nef' '*.arw' '*.HEIC' '*.heic' '*.7z' '*.zip' \
    '*.ply' '*.glb' '*.splat' '*.spz' '*.mcap')
  [ -z "$out" ] && pass "no data files tracked" || bad "data files tracked" "$out"
else skip "tracked-data check (not a git checkout)"; fi

echo ""
[ $fail -eq 0 ] && echo "DOCS CHECK: PASS" || echo "DOCS CHECK: FAIL"
exit $fail
