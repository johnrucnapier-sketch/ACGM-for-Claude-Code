#!/bin/sh
# Project state and scoped grounding; never claim all Hooks are active.
set -eu
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$(dirname "$0")/acgm_status.py" --startup
