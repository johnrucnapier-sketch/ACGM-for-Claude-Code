#!/bin/sh
# post-tool-truth-first.sh — ACGM v0.4 PostToolUse advisory (Edit|Write|MultiEdit).
#
# WHAT CHANGED FROM v0.1 (and why)
#
# v0.1 appended a marker comment to the governance file it had just flagged.
# Observed 2026-08-05: it silently modified a CLAUDE.md that a human had not
# reviewed, and the flag itself was a false positive. Two problems, one root:
# the response was disproportionate to the confidence.
#
#   - A governance mechanism that edits the artifact it governs is itself an
#     unlogged state change. That is the drift this project exists to prevent.
#   - The v0.1 skill text already promised "it does not edit the file for you".
#     Implementation and documentation disagreed; the implementation was wrong.
#
# v0.4 returns an advisory into the agent's context and touches nothing. A false
# positive now costs a sentence the agent can weigh and discard, instead of a
# stray comment committed into someone's repository.
#
# The heuristic is deliberately still coarse. Distinguishing a normative rule
# ("do not call X directly") from a factual claim ("this calls X") is not a
# regex problem. Coarse detection is acceptable precisely because the response
# is now cheap; do not trade that back for a cleverer matcher.
#
# Scope: active governance docs only (CONSTITUTION / AGENTS / CLAUDE /
# decisions/** / .governance/**). Pedagogical docs (METHODOLOGY* / README /
# CASES / CONTRIBUTING) quote the forbidden vocabulary while teaching it;
# flagging them would be the very drift this guards against.

set -eu

command -v jq >/dev/null 2>&1 || { echo '{}'; exit 0; }
input=$(cat 2>/dev/null || true)
[ -n "$input" ] || { echo '{}'; exit 0; }

path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -n "$path" ] || { echo '{}'; exit 0; }

base=${path##*/}
is_governance=0
case "$base" in
  CONSTITUTION.md|AGENTS.md|CLAUDE.md) is_governance=1 ;;
esac
case "$path" in
  */decisions/*|decisions/*|*/.governance/*|.governance/*) is_governance=1 ;;
esac
[ "$is_governance" = 1 ] || { echo '{}'; exit 0; }

written=$(printf '%s' "$input" | jq -r '
  (.tool_input.new_string // empty),
  (.tool_input.content // empty),
  ((.tool_input.edits // []) | map(.new_string // empty) | join("\n"))
' 2>/dev/null || true)
[ -n "$written" ] || { echo '{}'; exit 0; }

# An explicit opt-out keeps the advisory from repeating on a reviewed document.
printf '%s' "$written" | grep -q 'ACGM-REVIEWED' && { echo '{}'; exit 0; }

# Quoted, backticked and emphasised spans are discussed, not asserted.
prose=$(printf '%s\n' "$written" | sed \
  -e 's/`[^`]*`/ /g' -e 's/"[^"]*"/ /g' -e "s/'[^']*'/ /g" \
  -e 's/“[^”]*”/ /g' -e 's/\*\*[^*]*\*\*/ /g')

UNCERTAIN='我记得|应该是|大概|可能是|似乎|据说|印象中|I recall|should be|probably|supposedly|seems|if I remember'
ASSERTION='使用|依赖|调用|导入|配置为|运行在|存储在|uses|imports|depends on|calls|is configured|runs on|stored in'
CITATION='[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+'

finding=""
if printf '%s' "$prose" | grep -Eq "$UNCERTAIN"; then
  finding="asserted uncertainty ('I recall' / 'should be' / '我记得' / '应该是')"
elif printf '%s' "$prose" | grep -Eq "$ASSERTION"; then
  printf '%s' "$written" | grep -Eq "$CITATION" || \
    finding="a technical claim with no file:line citation"
fi

[ -n "$finding" ] || { echo '{}'; exit 0; }

ADVISORY="ACGM truth-first advisory — the write to ${base} contains ${finding}.

This is a coarse heuristic and may be wrong; nothing has been changed. If the
text states how the system currently behaves, re-read the source in this session
and cite file:line. If it is a rule, a goal, or a quoted example, no citation is
needed — add ACGM-REVIEWED to the document to stop this advisory recurring.

Never resolve this by weakening the claim into vaguer wording."

jq -n --arg advisory "$ADVISORY" '{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": $advisory
  }
}'
