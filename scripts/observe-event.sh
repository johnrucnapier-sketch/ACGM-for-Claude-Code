#!/bin/sh
# Local best-effort observations; never block and never change a Gate result.
export PYTHONDONTWRITEBYTECODE=1
python3 "$(dirname "$0")/acgm_observe.py" hook 2>/dev/null || printf '{}\n'
