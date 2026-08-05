#!/bin/sh
# pretool-destructive-bash.sh — ACGM v0.4 PreToolUse gate for destructive Bash.
#
# WHAT CHANGED FROM v0.1 (and why)
#
# v0.1 grepped the agent's last reply for the literal markers "(a)".."(d)".
# That is a TEXT check: writing four characters satisfied it. Observed
# 2026-08-05 in this repository's own session — the gate fired, the agent
# rewrote the command instead of producing evidence, and the gate stopped
# firing. Nothing was verified.
#
# v0.4 checks STRUCTURE instead, because structure is mechanically decidable
# from the tool call and the transcript, and cannot be produced by prose:
#
#   1. Four NAMED fields, each with real content (placeholders rejected).
#   2. The destructive command must stand ALONE — no ';', '&&', '||', pipe,
#      redirection or command substitution binding it to other work. Evidence,
#      mutation and verification cannot be collapsed into one invocation, so
#      ordering and partial failure stay auditable.
#   3. At least one read-only tool call must already exist in this session
#      before this one. Evidence must have been gathered, not asserted.
#
# The gate returns "ask". It never grants permission: a complete gate still
# goes to the human. Non-destructive Bash and every other tool pass silently.
#
# Whitelist policy: every CASES.md entry involving a destructive operation not
# listed here MUST add a pattern. The v0.1 list missed plugin/package state
# mutation entirely — `claude plugin uninstall` passed silently on 2026-08-05
# while an `rm -rf` against a non-existent directory was gated. Misses are
# worse than false positives; extend eagerly.

set -eu

input=$(cat 2>/dev/null || true)
[ -n "$input" ] || { echo '{}'; exit 0; }

command -v jq >/dev/null 2>&1 || { echo '{}'; exit 0; }
command -v python3 >/dev/null 2>&1 || { echo '{}'; exit 0; }

tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || true)
[ "$tool_name" = "Bash" ] || { echo '{}'; exit 0; }

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
[ -n "$cmd" ] || { echo '{}'; exit 0; }

# ---- Strip heredoc bodies before matching ----
# Observed 2026-08-05: a `git commit -F -` whose message *described* a recursive
# delete tripped the filter, twice. Heredoc content is data the command writes,
# not an operation it performs, so matching it is a pure false positive.
#
# Bodies only. The `<<TAG` line itself stays, so a destructive command that also
# feeds a heredoc is still caught -- dropping everything after `<<` would trade a
# false positive for a false negative, which is the worse error here.
scan=$(printf '%s\n' "$cmd" | awk '
  /^[[:space:]]*$/ && skip { print; next }
  skip { if ($0 == term) { skip = 0 }; next }
  {
    print
    line = $0
    if (match(line, /<<-?[[:space:]]*['"'"'"]?[A-Za-z_][A-Za-z0-9_]*['"'"'"]?/)) {
      tag = substr(line, RSTART, RLENGTH)
      gsub(/^<<-?[[:space:]]*|['"'"'"]/, "", tag)
      term = tag
      skip = 1
    }
  }
')

# ---- Cheap destructive filter (runs on every Bash; keep it POSIX case) ----
is_destructive=0
case "$scan" in
  # filesystem
  *"rm -rf"*|*"rm -fr"*|*"rm -r "*|*"rm --recursive"*|*"rm -f "*|*"shred "*|*"rmdir "*) is_destructive=1 ;;
  # git history / working tree
  *"git push --force"*|*"git push -f"*|*"git reset --hard"*|*"git clean -f"*) is_destructive=1 ;;
  *"git checkout -- "*|*"git checkout ."*|*"git branch -D"*|*"git tag -d"*) is_destructive=1 ;;
  *"git rebase"*|*"git filter-branch"*|*"git filter-repo"*|*"git stash drop"*|*"git stash clear"*) is_destructive=1 ;;
  # agent / plugin / package state  (MISSING IN v0.1 — see header)
  *"claude plugin uninstall"*|*"claude plugin install"*|*"claude plugin update"*) is_destructive=1 ;;
  *"claude plugin enable"*|*"claude plugin disable"*|*"claude plugin marketplace"*) is_destructive=1 ;;
  *"npm i -g"*|*"npm install -g"*|*"npm uninstall -g"*|*"npm rm -g"*) is_destructive=1 ;;
  *"pip install"*|*"pip uninstall"*|*"brew install"*|*"brew uninstall"*|*"brew upgrade"*) is_destructive=1 ;;
  # agent-owned configuration
  *"/.claude/"*) case "$scan" in *">"*|*"rm "*|*"mv "*|*"cp "*|*"tee "*|*"sed -i"*) is_destructive=1 ;; esac ;;
  # service / system
  *"systemctl stop"*|*"systemctl start"*|*"systemctl disable"*|*"systemctl enable"*) is_destructive=1 ;;
  *"systemctl mask"*|*"systemctl restart"*|*"systemctl reload"*|*"launchctl "*) is_destructive=1 ;;
  *"dd if="*|*"mkfs"*|*"kill -9"*|*"kill -KILL"*|*"pkill "*|*"shutdown "*|*"reboot "*) is_destructive=1 ;;
  # database
  *"drop table"*|*"DROP TABLE"*|*"drop database"*|*"DROP DATABASE"*) is_destructive=1 ;;
  *"truncate "*|*"TRUNCATE "*|*"delete from"*|*"DELETE FROM"*) is_destructive=1 ;;
  # remote code execution
  *"curl "*"| sh"*|*"curl "*"| bash"*|*"wget "*"| sh"*|*"wget "*"| bash"*) is_destructive=1 ;;
esac

[ "$is_destructive" = 1 ] || { echo '{}'; exit 0; }

# ---- Structural gate (python3; only reached for destructive commands) ----
printf '%s' "$input" | ACGM_HOOK_MODE=gate python3 "$(dirname "$0")/acgm_gate.py"
