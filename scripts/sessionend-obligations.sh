#!/bin/sh
# sessionend-obligations.sh — ACGM v0.4 SessionEnd hook.
#
# A session that declared ACGM-VERIFY-AFTER and then ended without room for the
# check to run has left an unverified operation behind, not a finished one.
# SessionEnd cannot inject context -- the session is over -- so this reports to
# stderr. Only new unresolved declarations append to OPEN_OBLIGATIONS.md,
# once per session and turn, and only where .governance already exists.
# Draft/worktree status never writes the ledger.
#
# Never blocks and never fails a session.

set -eu
command -v python3 >/dev/null 2>&1 || exit 0
ACGM_HOOK_MODE=sessionend exec python3 "$(dirname "$0")/acgm_gate.py"
