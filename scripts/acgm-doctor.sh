#!/bin/sh
# acgm-doctor.sh — ACGM v0.4 health check.
#
# Reports what it can actually establish, and refuses to report what it cannot.
#
# The hard rule here: doctor runs as a subprocess. It can read manifests, ask the
# Claude CLI what it has registered, and compare bytes. It CANNOT observe whether
# the Claude session that invoked it loaded the hooks. Configuration is not
# activation (EVIDENCE E-008). Every check below is labelled with what it proves,
# and the activation line always says "not provable from here".
#
# Exit 0 when nothing is broken, 1 when a check fails. Warnings do not fail.
#
# Usage:  sh scripts/acgm-doctor.sh [--plugin-dir <path>]

set -eu

PLUGIN_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --plugin-dir) PLUGIN_DIR="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) shift ;;
  esac
done

if [ -z "$PLUGIN_DIR" ]; then
  PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
fi

PLUGIN_ID='acgm@acgm'
fails=0
warns=0

ok()   { printf '  \033[32mPASS\033[0m  %-34s %s\n' "$1" "$2"; }
bad()  { printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$1" "$2"; fails=$((fails+1)); }
warn() { printf '  \033[33mWARN\033[0m  %-34s %s\n' "$1" "$2"; warns=$((warns+1)); }
note() { printf '  ----  %-34s %s\n' "$1" "$2"; }

printf '\nACGM doctor — %s\n\n' "$PLUGIN_DIR"

# --- 1. manifest shape ------------------------------------------------------
# Proves: the manifest would be accepted by Claude Code's loader.
# The v0.1 manifest declared "skills": "skills/" and "hooks": "hooks/hooks.json".
# Both were rejected: paths must start with "./", and hooks/hooks.json is loaded
# automatically, so declaring it is a duplicate. Nobody noticed for ~3 months
# because nothing ever validated it.
manifest="$PLUGIN_DIR/.claude-plugin/plugin.json"
if [ ! -f "$manifest" ]; then
  bad "manifest present" "missing $manifest"
elif ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$manifest" 2>/dev/null; then
  bad "manifest parses" "invalid JSON"
else
  problems=$(python3 - "$manifest" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1]))
issues = []
for key in ("skills", "hooks"):
    if key not in manifest:
        continue
    value = manifest[key]
    entries = value if isinstance(value, list) else [value]
    for entry in entries:
        if not isinstance(entry, str) or not entry.startswith("./"):
            issues.append(f"{key}: {entry!r} must start with './'")
if "hooks" in manifest:
    issues.append("hooks: hooks/hooks.json loads automatically; declaring it is a duplicate")
for key in ("name", "version", "description"):
    if not manifest.get(key):
        issues.append(f"{key}: required")
print("; ".join(issues))
PY
)
  if [ -n "$problems" ]; then bad "manifest shape" "$problems"; else ok "manifest shape" "declared paths valid"; fi
fi

# --- 2. official validator --------------------------------------------------
# Proves: the shipped package passes the same check Claude Code runs.
if command -v claude >/dev/null 2>&1; then
  if out=$(cd / && claude plugin validate "$PLUGIN_DIR" 2>&1); then
    ok "claude plugin validate" "passed"
  else
    bad "claude plugin validate" "$(printf '%s' "$out" | grep -E '❯|error' | head -2 | tr '\n' ' ')"
  fi
else
  warn "claude plugin validate" "claude CLI not on PATH; cannot validate"
fi

# --- 3. hook wiring ---------------------------------------------------------
# Proves: every registered hook command exists and is runnable. Does NOT prove
# the harness loaded them.
hooks="$PLUGIN_DIR/hooks/hooks.json"
if [ ! -f "$hooks" ]; then
  bad "hooks.json present" "missing $hooks"
else
  missing=$(PLUGIN_DIR="$PLUGIN_DIR" python3 - "$hooks" <<'PY'
import json, os, shlex, sys
root = os.environ["PLUGIN_DIR"]
data = json.load(open(sys.argv[1])).get("hooks", {})
gone = []
events = []


def resolves(command):
    """True if the command's executable exists.

    The plugin root may contain spaces, so a naive split() truncates the path.
    Try the whole expanded string first, then a shell-aware split.
    """
    expanded = command.replace("${CLAUDE_PLUGIN_ROOT}", root)
    if os.path.isfile(expanded):
        return True
    try:
        parts = shlex.split(expanded)
    except ValueError:
        return False
    return bool(parts) and os.path.isfile(parts[0])


for event, groups in data.items():
    events.append(event)
    for group in groups:
        for handler in group.get("hooks", []):
            command = handler.get("command", "")
            if command and not resolves(command):
                gone.append(command)
print("|".join(sorted(events)))
print(";".join(gone))
PY
)
  events=$(printf '%s' "$missing" | sed -n 1p)
  gone=$(printf '%s' "$missing" | sed -n 2p)
  if [ -n "$gone" ]; then bad "hook scripts exist" "$gone"; else ok "hook scripts exist" "events: $events"; fi
fi

# --- 4. skills discoverable -------------------------------------------------
count=$(find "$PLUGIN_DIR/skills" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$count" -gt 0 ]; then
  bad_fm=""
  for f in "$PLUGIN_DIR"/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    head -1 "$f" | grep -q '^---$' || bad_fm="$bad_fm $(basename "$(dirname "$f")")"
    grep -q '^name:' "$f" || bad_fm="$bad_fm $(basename "$(dirname "$f")")"
  done
  if [ -n "$bad_fm" ]; then bad "skills frontmatter" "malformed:$bad_fm"; else ok "skills discoverable" "$count skill(s)"; fi
else
  bad "skills discoverable" "no SKILL.md under $PLUGIN_DIR/skills"
fi

# --- 5. registration and cache drift ---------------------------------------
# Proves: what Claude has on record, and whether the cached bytes still equal the
# source. A directory-source marketplace syncs the WORKING TREE, so a cache can
# contain uncommitted or untracked files with no Git identity, and `update` is a
# no-op while the version string is unchanged.
reg=~/.claude/plugins/installed_plugins.json
if [ -f "$reg" ]; then
  install_path=$(PLUGIN_ID="$PLUGIN_ID" python3 - "$reg" <<'PY'
import json, os, sys
try:
    data = json.load(open(sys.argv[1]))["plugins"].get(os.environ["PLUGIN_ID"], [])
    print(data[0]["installPath"] if data else "")
except Exception:
    print("")
PY
)
  if [ -z "$install_path" ]; then
    warn "plugin registered" "not in installed_plugins.json (running from a directory?)"
  elif [ ! -d "$install_path" ]; then
    bad "install path exists" "$install_path"
  else
    # A byte comparison only means something against a DIFFERENT tree. Invoked
    # from inside the cache — which is exactly how the SessionStart line tells
    # you to invoke it — PLUGIN_DIR *is* install_path, and the loop below would
    # compare the cache with itself and pass unconditionally. That is the
    # "green light that proves nothing" this whole script exists to refuse.
    # So: when the two resolve to the same tree, fall back to the marketplace's
    # own source directory, and if there isn't one, say so instead of passing.
    src="$PLUGIN_DIR"
    if [ "$(CDPATH= cd -- "$PLUGIN_DIR" && pwd -P)" = "$(CDPATH= cd -- "$install_path" && pwd -P)" ]; then
      src=$(PLUGIN_ID="$PLUGIN_ID" python3 - ~/.claude/plugins/known_marketplaces.json <<'PY'
import json, os, sys
try:
    name = os.environ["PLUGIN_ID"].split("@", 1)[1]
    source = json.load(open(sys.argv[1]))[name]["source"]
    print(source.get("path", "") if source.get("source") == "directory" else "")
except Exception:
    print("")
PY
)
    fi
    if [ -z "$src" ] || [ ! -d "$src" ]; then
      warn "cache matches source" "cannot verify from here — rerun with --plugin-dir <source tree>"
    elif [ "$(CDPATH= cd -- "$src" && pwd -P)" = "$(CDPATH= cd -- "$install_path" && pwd -P)" ]; then
      warn "cache matches source" "source is the install path — self-referential, nothing compared"
    else
      diff_count=0
      for f in $(cd "$install_path" && find . -type d \( -name __pycache__ -o -name .in_use \) -prune -o -type f ! -name '*.pyc' ! -name .in_use -print | sed 's|^\./||'); do
        [ -f "$src/$f" ] || { diff_count=$((diff_count+1)); continue; }
        a=$(shasum < "$install_path/$f" | cut -d' ' -f1)
        b=$(shasum < "$src/$f" | cut -d' ' -f1)
        [ "$a" = "$b" ] || diff_count=$((diff_count+1))
      done
      if [ "$diff_count" -eq 0 ]; then
        ok "cache matches source" "matches $src"
      else
        bad "cache matches source" "$diff_count file(s) differ from $src — reinstall; 'update' is a no-op at the same version"
      fi
    fi
  fi
else
  warn "plugin registered" "no installed_plugins.json"
fi

if command -v claude >/dev/null 2>&1; then
  status=$(cd / && claude plugin list 2>/dev/null | awk -v id="$PLUGIN_ID" '
    index($0, id) {found=1} found && /Status:/ {print; exit}' | sed 's/.*Status: *//')
  case "$status" in
    *enabled*) ok "plugin enabled" "$status" ;;
    "")        warn "plugin enabled" "not listed" ;;
    *)         bad "plugin enabled" "$status" ;;
  esac
fi

# --- 6. activation: the line doctor must never fake -------------------------
note "runtime activation" "NOT PROVABLE FROM HERE — doctor is a subprocess."
note "" "Activation means: a hook produced output in YOUR session."
note "" "Everything above is configuration. Do not report it as 'running'."
note "" "For activation already on record, across projects and sessions:"
note "" "  python3 $PLUGIN_DIR/scripts/acgm_activity.py"

printf '\n'
if [ "$fails" -gt 0 ]; then
  printf 'ACGM doctor: %d failed, %d warning(s)\n\n' "$fails" "$warns"
  exit 1
fi
printf 'ACGM doctor: configuration healthy, %d warning(s)\n\n' "$warns"
exit 0
