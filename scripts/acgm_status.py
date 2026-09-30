"""Read-only project state shared by SessionStart and doctor. No activation claim."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from acgm_gate import configured_policy_path, project_anchor
from acgm_policy import load_policy


def project_state() -> dict:
    state = {"root": None, "anchor_status": "unknown", "root_rules": [], "ledger_present": False,
             "runtime_policy": "unknown", "protected_paths": 0, "trusted_tools": 0,
             "runtime_activation": "not_proven"}
    try:
        root = Path(project_anchor())
        state.update(root=str(root), anchor_status="valid", root_rules=[p for p in (
            "CLAUDE.md", "AGENTS.md", "CONSTITUTION.md", "docs/CONSTITUTION.md",
            ".governance/CONSTITUTION.md") if (root/p).is_file()],
            ledger_present=(root/".governance").is_dir())
    except (ValueError, OSError, TypeError, subprocess.SubprocessError):
        state["anchor_status"] = "invalid_or_unavailable"
    try:
        path = configured_policy_path({})
        guards, trusted = load_policy(path) if path else ([], [])
        state.update(runtime_policy="present_valid" if path else "absent",
                     protected_paths=len(guards), trusted_tools=len(trusted))
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError):
        state["runtime_policy"] = "invalid_or_unavailable"
    return state


def startup_message(state: dict) -> str:
    script = Path(__file__).resolve().with_name("acgm-explain.py")
    return ("ACGM SessionStart observed; other Hook activation is not proven.\n"
            "Project state (configuration only): " + json.dumps(state, ensure_ascii=False) + "\n"
            "Use session-grounding: verify this worktree and task-relevant current facts. "
            "Read applicable rules, reuse existing SOPs, and continue within the user's existing authorization; "
            "ask only if scope, target, permission or material risk is unresolved. "
            "Do not bootstrap or reinstall merely because a layer is absent. "
            "Invalid policy needs diagnosis; do not bypass it.\n"
            "Gate denial: follow its reason code and next_safe_action. For a read-only inspection, "
            "send a Bash Hook JSON payload to python3 " + shlex.quote(str(script)) + "; "
            "it never executes the command. Do not read Gate source to guess a bypass. "
            "Evidence is not authorization; state changes still require truth-first and post-verification.\n"
            "本次只证明 SessionStart 已运行。按任务核实当前状态并沿用已有授权；缺少某层治理不等于所有层都未启用。"
            "拒绝先看原因与下一步，不重复试格式、不绕过 Gate。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--startup", action="store_true")
    args = parser.parse_args()
    if args.project:
        os.environ["CLAUDE_PROJECT_DIR"] = args.project
    payload = {}
    if args.startup:
        try:
            payload = json.load(sys.stdin)
            if not os.environ.get("CLAUDE_PROJECT_DIR"):
                os.environ["CLAUDE_PROJECT_DIR"] = payload.get("cwd") or os.getcwd()
        except (ValueError, AttributeError):
            if not os.environ.get("CLAUDE_PROJECT_DIR"):
                os.environ["CLAUDE_PROJECT_DIR"] = os.getcwd()
    state = project_state()
    if args.startup:
        try:
            from acgm_observe import record
            record({**payload, "hook_event_name": "SessionStart"})
        except Exception:
            pass
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                "additionalContext": startup_message(state)}}, ensure_ascii=False))
        return 0
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 1 if "invalid_or_unavailable" in (state["runtime_policy"], state["anchor_status"]) else 0


if __name__ == "__main__":
    sys.exit(main())
