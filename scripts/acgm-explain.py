#!/usr/bin/env python3
"""Inspect a Bash call through the installed Hook; NEVER execute its command.

Input is a JSON Hook payload on stdin (tool_input.command, optional cwd,
transcript_path, tool_use_id). --project must identify the actual startup project
when CLAUDE_PROJECT_DIR is unavailable. Output is advisory, never authorization.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def inspect_call(payload: dict, project: str | None = None) -> dict:
    if (not isinstance(payload, dict) or payload.get("tool_name", "Bash") != "Bash"
            or not isinstance(payload.get("tool_input"), dict)
            or not isinstance(payload["tool_input"].get("command"), str)
            or not payload["tool_input"]["command"].strip()):
        raise ValueError("Expected a Bash payload with nonempty tool_input.command")
    payload = {**payload, "tool_name": "Bash"}
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "ACGM_OBSERVATIONS": "0"}
    if project is not None:
        if not os.path.isabs(project) or not os.path.isdir(project):
            raise ValueError("--project must be an existing absolute directory")
        env["CLAUDE_PROJECT_DIR"] = project
    # cwd belongs to the call being inspected, not the inspector's directory.
    if not payload.get("cwd"):
        payload["cwd"] = project or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    result = subprocess.run(
        ["/bin/sh", str(Path(__file__).resolve().with_name("pretool-destructive-bash.sh"))],
        input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=30,
        check=True,
    )
    hook = json.loads(result.stdout)
    if not isinstance(hook, dict):
        raise ValueError("Invalid Hook response")
    decision = hook.get("hookSpecificOutput", {}).get("permissionDecision")
    if hook != {} and decision != "deny":
        raise ValueError("Unexpected Hook response")
    reason = hook.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    marker = "\nACGM-DIAGNOSTIC: "
    diagnostic = json.loads(reason.split(marker, 1)[1]) if marker in reason else {
        "issues": ([{"code": "HOOK_UNAVAILABLE", "message": reason,
                     "retryable": False, "next_safe_action": "Inspect Hook dependencies and input."}]
                   if decision == "deny" else [])}
    return {"schema_version": 1, "verdict": "deny" if decision == "deny" else "pass_through",
            "issues": diagnostic["issues"], "executed": False, "authorized": False,
            "project": env.get("CLAUDE_PROJECT_DIR"), "cwd": payload["cwd"],
            "scope": "Current ACGM Bash Hook only; pass-through does not certify safety, runtime state or Claude permissions. Recheck at execution."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Actual absolute startup project; policy override environment still takes precedence")
    args = parser.parse_args()
    try:
        report = inspect_call(json.load(sys.stdin), args.project)
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError):
        report = {"schema_version": 1, "verdict": "error", "executed": False, "authorized": False,
                  "issues": [{"code": "INSPECTOR_INVALID", "retryable": False,
                              "message": "Invalid input, unavailable Hook or invalid Hook response.",
                              "next_safe_action": "Check input JSON, the project path and local Hook dependencies."}]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "pass_through" else (2 if report["verdict"] == "deny" else 1)


if __name__ == "__main__":
    sys.exit(main())
