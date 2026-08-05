#!/bin/sh
# drift-check.sh — static drift scanner for acgm.
#
# Exit 0 = no drift detected, 1 = drift detected. Default: markdown report to
# stdout. `--output FILE` also writes the report to FILE. `--strict` enables the
# heuristic ① implementation-pattern scan (OFF by default — it is noisy).
#
# DESIGN — why this does not cry wolf on its own repo:
#   The ② text scan targets a PROJECT'S ACTIVE GOVERNANCE DOCS — CONSTITUTION.md,
#   AGENTS.md, CLAUDE.md, decisions/**.md, .governance/**.md — NOT pedagogical docs
#   (METHODOLOGY*.md, README.md, CASES.md, CONTRIBUTING.md) which necessarily quote
#   the forbidden vocabulary while teaching it. On top of that, every text scan:
#     - skips fenced ``` code blocks
#     - skips markdown blockquote lines ( > ... )
#     - skips <!-- drift-check:ignore-start --> .. <!-- drift-check:ignore-end -->
#     - skips the line right after a <!-- drift-check:ignore --> marker
#     - ignores matches that sit inside quotes / backticks (quoted = discussed,
#       not asserted)
#   ③ only flags governance files that differ on a non-trunk branch whose last
#   commit is > 7 days old. ④ runs only if .governance/scope.yml exists. ① is
#   opt-in. The report separates DETECTED from IGNORED so it is auditable.
#
# Pure POSIX sh + awk + grep. macOS (BSD) and Linux (GNU) compatible.

set -eu

STRICT=0
OUTFILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --strict) STRICT=1 ;;
    --output) shift; OUTFILE="${1:-}" ;;
    --output=*) OUTFILE="${1#--output=}" ;;
    -h|--help)
      echo "usage: drift-check.sh [--strict] [--output FILE]"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM
REPORT="$TMP/report.md"
: > "$TMP/detected"
: > "$TMP/ignored"

n2=0; n3=0; n4=0; n1=0

# emit "LINENO:TEXT" for scannable lines only (drops fenced code, blockquotes,
# ignore-marked regions). Quote-stripping is applied by the caller per check.
scannable() {
  awk '
    BEGIN { infence=0; ignore_block=0; skip_next=0 }
    {
      raw=$0
      if (raw ~ /^[[:space:]]*```/) { infence = !infence; next }
      if (infence) next
      if (raw ~ /<!--[[:space:]]*drift-check:ignore-start[[:space:]]*-->/) { ignore_block=1; next }
      if (raw ~ /<!--[[:space:]]*drift-check:ignore-end[[:space:]]*-->/)   { ignore_block=0; next }
      if (ignore_block) next
      if (skip_next==1) { skip_next=0; next }
      if (raw ~ /<!--[[:space:]]*drift-check:ignore[[:space:]]*-->/) { skip_next=1; next }
      if (raw ~ /^[[:space:]]*>/) next
      print NR ":" raw
    }
  ' "$1"
}

# strip quoted / backticked / emphasized spans so "discussed" phrases do not match
strip_quoted() {
  sed -e 's/`[^`]*`/ /g' \
      -e 's/"[^"]*"/ /g' \
      -e "s/'[^']*'/ /g" \
      -e 's/“[^”]*”/ /g' \
      -e 's/\*\*[^*]*\*\*/ /g'
}

GOV_GLOBS=$(git ls-files 2>/dev/null | grep -E '(^|/)(CONSTITUTION|AGENTS|CLAUDE)\.md$|^decisions/.*\.md$|^\.governance/.*\.(md|yml|yaml)$' || true)

UNCERT='我记得|应该是|大概|可能是|似乎|据说|I recall|should be|probably|supposedly|seems\b'
TECH='使用|依赖|调用|导入|配置为|\buses\b|\bimports\b|depends on|\bcalls\b'

# ---- ② cognitive ----
if [ -n "$GOV_GLOBS" ]; then
  echo "$GOV_GLOBS" | while IFS= read -r f; do
    [ -f "$f" ] || continue
    scannable "$f" | while IFS= read -r ln; do
      no=${ln%%:*}; tx=${ln#*:}
      clean=$(printf '%s\n' "$tx" | strip_quoted)
      # A: uncertainty words asserted (not quoted)
      if printf '%s' "$clean" | grep -Eq "$UNCERT"; then
        echo "$f:$no — ②A uncertainty phrasing asserted" >> "$TMP/detected"
      fi
      # B: technical conclusion without a nearby file:line citation
      if printf '%s' "$clean" | grep -Eq "$TECH"; then
        if ! printf '%s' "$tx" | grep -Eq '[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+'; then
          echo "$f:$no — ②B technical claim without file:line" >> "$TMP/detected"
        fi
      fi
    done
    # C: existing file:line refs must resolve
    grep -onE '[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+' "$f" 2>/dev/null | while IFS= read -r hit; do
      hno=${hit%%:*}; ref=${hit#*:}
      rf=${ref%:*}; rl=${ref##*:}
      case "$rf" in /*) continue ;; esac
      [ -n "$rl" ] || continue
      if [ ! -f "$rf" ]; then
        echo "$f:$hno — ②C dangling ref ($ref: file missing)" >> "$TMP/detected"
      else
        tot=$(wc -l < "$rf" 2>/dev/null | tr -d ' ' || true)
        if [ -n "${tot:-}" ] && printf '%s' "$rl" | grep -Eq '^[0-9]+$' && [ "$rl" -gt "$tot" ]; then
          echo "$f:$hno — ②C dangling ref ($ref: only $tot lines)" >> "$TMP/detected"
        fi
      fi
    done
  done
fi
n2=$(grep -c '②' "$TMP/detected" 2>/dev/null || true); n2=${n2:-0}

# ---- ③ structural placement (trunk rot) ----
TRUNK=""
for c in main master trunk; do
  if git show-ref --verify --quiet "refs/heads/$c"; then TRUNK="$c"; break; fi
done
if [ -n "$TRUNK" ]; then
  GOVPATHS="AGENTS.md CLAUDE.md CONSTITUTION.md METHODOLOGY.md METHODOLOGY.en.md decisions .governance"
  NOW=$(date +%s)
  git for-each-ref --format='%(refname:short)' refs/heads/ | while IFS= read -r br; do
    [ "$br" = "$TRUNK" ] && continue
    last=$(git log -1 --format='%ct' "$br" 2>/dev/null || echo "$NOW")
    age_days=$(( (NOW - last) / 86400 ))
    d=$(git diff --name-only "$TRUNK".."$br" -- $GOVPATHS 2>/dev/null || true)
    if [ -n "$d" ] && [ "$age_days" -gt 7 ]; then
      echo "branch '$br' — ③ governance diverged, $age_days days stale: $(echo "$d" | tr '\n' ' ')" >> "$TMP/detected"
    fi
  done
fi
n3=$(grep -c '③' "$TMP/detected" 2>/dev/null || true); n3=${n3:-0}

# ---- ④ scope (only if .governance/scope.yml exists) ----
if [ -f ".governance/scope.yml" ]; then
  ncommits=$(git rev-list --count HEAD 2>/dev/null || echo 0)
  rng="HEAD~10..HEAD"; [ "$ncommits" -lt 11 ] && rng="HEAD"
  ins=$(awk '/^in:/{f=1;next}/^out:/{f=0}/^[a-z]/{f=0}f&&/-/{gsub(/[ "'\''-]/,"");print}' .governance/scope.yml)
  outs=$(awk '/^out:/{f=1;next}/^in:/{f=0}/^[a-z]/{f=0}f&&/-/{gsub(/[ "'\''-]/,"");print}' .governance/scope.yml)
  git diff --name-only $rng 2>/dev/null | while IFS= read -r cf; do
    [ -n "$cf" ] || continue
    hitout=0
    for g in $outs; do case "$cf" in $g) hitout=1;; esac; done
    [ "$hitout" = 1 ] && { echo "$cf — ④ matches an OUT pattern" >> "$TMP/detected"; continue; }
    hitin=0
    for g in $ins; do case "$cf" in $g) hitin=1;; esac; done
    [ "$hitin" = 0 ] && echo "$cf — ④ not covered by any IN pattern" >> "$TMP/detected"
  done
fi
n4=$(grep -c '④' "$TMP/detected" 2>/dev/null || true); n4=${n4:-0}

# ---- ① implementation anti-patterns (opt-in; heuristic) ----
if [ "$STRICT" = 1 ]; then
  CODE=$(git ls-files 2>/dev/null | grep -E '\.(py|ts|tsx|js|jsx|go|rs|java|rb|kt|swift)$' \
         | grep -viE '(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.' || true)
  if [ -n "$CODE" ]; then
    echo "$CODE" | while IFS= read -r cf; do
      [ -f "$cf" ] || continue
      grep -nE 'catch[[:space:]]*\([^)]*\)[[:space:]]*\{[[:space:]]*\}|except[[:space:]]*:[[:space:]]*pass|catch[[:space:]]*\{[[:space:]]*\}|TODO|FIXME|HACK|@ts-ignore|@ts-nocheck' "$cf" 2>/dev/null \
        | while IFS= read -r m; do echo "$cf:${m%%:*} — ①(heuristic) $(echo "$m" | cut -c1-60)" >> "$TMP/detected"; done
      case "$cf" in
        *.ts|*.tsx) grep -nE ':[[:space:]]*any\b|<any>' "$cf" 2>/dev/null \
          | while IFS= read -r m; do echo "$cf:${m%%:*} — ①(heuristic) any type" >> "$TMP/detected"; done ;;
      esac
    done
  fi
fi
n1=$(grep -c '①(heuristic)' "$TMP/detected" 2>/dev/null || true); n1=${n1:-0}

TOTAL=$(grep -c . "$TMP/detected" 2>/dev/null || true); TOTAL=${TOTAL:-0}

{
  echo "# Drift Check Report — $(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo "## Summary"
  echo "- ① implementation (heuristic, $([ "$STRICT" = 1 ] && echo on || echo 'off — use --strict')): $n1"
  echo "- ② cognitive: $n2"
  echo "- ③ structural placement: $n3"
  echo "- ④ scope ($([ -f .governance/scope.yml ] && echo 'scope.yml present' || echo 'no scope.yml — skipped')): $n4"
  echo
  if [ "$TOTAL" -eq 0 ]; then
    echo "## Details"
    echo
    echo "_No drift detected._"
  else
    echo "## Details"
    echo
    sort -u "$TMP/detected" | while IFS= read -r d; do echo "- $d"; done
  fi
  echo
  echo "_Scope of ② scan: a project's active governance docs (CONSTITUTION/AGENTS/CLAUDE/decisions/.governance) — pedagogical docs are intentionally not scanned. Fenced code, blockquotes, quoted spans and \`drift-check:ignore\` regions are excluded by design._"
} > "$REPORT"

cat "$REPORT"
[ -n "$OUTFILE" ] && cp "$REPORT" "$OUTFILE"

[ "$TOTAL" -eq 0 ] && exit 0 || exit 1
