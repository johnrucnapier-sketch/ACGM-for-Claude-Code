#!/usr/bin/env python3
"""Report ACGM's observed hook activity across recorded sessions.

`acgm doctor` deliberately refuses to report runtime activation: it runs as a
subprocess and cannot observe the session that invoked it. That honesty leaves a
gap — after the fact, you still need to know whether the plugin actually did
anything in some other project, and configuration health cannot answer it.

This closes the gap from the only source that can: the hook output recorded in
each session's transcript.

Two rules follow from CASES Case 11, where an interception was credited to the
wrong mechanism twice in a row:

  * Attribution reads the mechanism's own stdout, keyed by tool call. Never a
    text search over the transcript — that is contaminated by whatever the agent
    quoted, pasted, or `cat`-ed into the record.
  * An absence is reported with its denominator. "The gate never fired" and "the
    gate is not installed" look identical until you know how many chances it had.

The strongest signal here is neither of those counts. It is the GAP: a Bash call
that matches the destructive filter and has no gate output against its tool-use
id. That means the gate was missing, disabled, or failing at that moment.

Usage:
    acgm_activity.py                     # every project
    acgm_activity.py --project PATH      # one project
    acgm_activity.py --since 7           # sessions active in the last 7 days
    acgm_activity.py --json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

PROJECTS = os.path.expanduser("~/.claude/projects")

# Gaps listed per session before summarising. Truncation is always announced:
# a silently shortened list reads as "that was all of them".
SHOW_GAPS = 5

# Hook output fingerprints. Each is text ACGM emits and ordinary prose does not,
# so a match identifies both the mechanism and the version that produced it.
FINGERPRINTS = [
    ("session_start_governed", "ACGM governance is active in this project", "0.4"),
    ("session_start_governed", "This project uses agent-coding-governance", "0.1"),
    ("session_start_ungoverned", "no governance docs were found", "0.1/0.4"),
    ("gate_blocked", "destructive operation blocked", "0.4.1+"),
    ("gate_asked", "destructive operation held", "0.4.0"),
    ("gate_asked", "ACGM gate: this destructive Bash", "0.1"),
    ("posttool_advisory", "ACGM truth-first advisory", "0.4"),
    ("posttool_marker", "governance self-check", "0.1"),
    ("sessionend_obligation", "unverified post-action obligations", "0.4"),
]

LABELS = {
    "session_start_governed": "SessionStart · governed project",
    "session_start_ungoverned": "SessionStart · no governance docs",
    "gate_blocked": "PreToolUse · blocked",
    "gate_asked": "PreToolUse · asked (weaker: an auto-accepting mode ignores it)",
    "posttool_advisory": "PostToolUse · advisory",
    "posttool_marker": "PostToolUse · edited the file (v0.1 behaviour)",
    "sessionend_obligation": "SessionEnd · unverified obligation",
}

# Mirrors the whitelist in pretool-destructive-bash.sh. Duplication is a drift
# source, so tests/test_activity.py feeds a shared corpus to both and fails if
# they ever disagree. Divergence is not prevented here; it is made loud.
DESTRUCTIVE = re.compile(
    r"rm\s+-rf|rm\s+-fr|rm\s+-r\s|rm\s+--recursive|rm\s+-f\s|shred\s|rmdir\s"
    r"|git\s+push\s+--force|git\s+push\s+-f|git\s+reset\s+--hard|git\s+clean\s+-f"
    r"|git\s+checkout\s+--\s|git\s+checkout\s+\.|git\s+branch\s+-D|git\s+tag\s+-d"
    r"|git\s+rebase|git\s+filter-branch|git\s+filter-repo|git\s+stash\s+drop"
    r"|git\s+stash\s+clear"
    r"|claude\s+plugin\s+(?:uninstall|install|update|enable|disable|marketplace)"
    r"|npm\s+i\s+-g|npm\s+install\s+-g|npm\s+uninstall\s+-g|npm\s+rm\s+-g"
    r"|pip\s+install|pip\s+uninstall|brew\s+install|brew\s+uninstall|brew\s+upgrade"
    r"|systemctl\s+(?:stop|start|disable|enable|mask|restart|reload)|launchctl\s"
    r"|dd\s+if=|mkfs|kill\s+-9|kill\s+-KILL|pkill\s|shutdown\s|reboot\s"
    r"|drop\s+table|DROP\s+TABLE|drop\s+database|DROP\s+DATABASE"
    r"|truncate\s|TRUNCATE\s|delete\s+from|DELETE\s+FROM"
    r"|curl\s.*\|\s*sh|curl\s.*\|\s*bash|wget\s.*\|\s*sh|wget\s.*\|\s*bash",
)
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
DEVNULL = re.compile(r"[0-9]*>>?\s*/dev/null|&>\s*/dev/null|[0-9]*>&[0-9]")
AGENT_CONFIG = re.compile(r"/\.claude/")
CONFIG_WRITE = re.compile(r">|rm\s|mv\s|cp\s|tee\s|sed\s+-i")


def scannable(command: str) -> str:
    """The command with heredoc bodies and discarded-output redirects removed.

    Mirrors the two normalisation steps in the shell filter. Both exist because
    matching over the raw invocation misfires on text the command merely carries.
    """
    lines, skip, term = [], False, None
    for line in command.splitlines():
        if skip:
            if line == term:
                skip = False
            continue
        lines.append(line)
        found = HEREDOC.search(line)
        if found:
            term, skip = found.group(1), True
    return DEVNULL.sub("", "\n".join(lines))


def is_destructive(command: str) -> bool:
    scan = scannable(command)
    if DESTRUCTIVE.search(scan):
        return True
    return bool(AGENT_CONFIG.search(scan) and CONFIG_WRITE.search(scan))


def result_text(block: dict) -> str:
    """Flatten a tool_result's content to text."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def read_session(path: str) -> dict:
    """One session's tool calls and the ACGM hook output attached to them.

    A denied call and an asked call are recorded differently, which the first
    version of this reader got wrong: it found every "ask" and no "deny", while
    a deny had been observed live minutes earlier.

      ask / SessionStart / PostToolUse / SessionEnd -> attachment.stdout
      deny                                          -> tool_result, is_error

    Both are read here. Attachments are trusted when they carry a hookEvent,
    because that field marks a genuine hook record rather than captured command
    output. A tool_result must START with the gate text: a transcript also
    contains the agent quoting, printing and `cat`-ing that same text, and
    counting those was the mistake in CASES Case 11.
    """
    cwd = ""
    bash_calls: dict[str, str] = {}
    gated: set[str] = set()
    events: dict[str, int] = {}
    versions: set[str] = set()
    first = last = ""

    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            cwd = cwd or entry.get("cwd", "")
            stamp = entry.get("timestamp")
            if stamp:
                first = first or stamp
                last = stamp

            message = entry.get("message")
            if isinstance(message, dict):
                for block in message.get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" and block.get("name") == "Bash":
                        bash_calls[block.get("id", "")] = (block.get("input") or {}).get(
                            "command", ""
                        )
                    elif block.get("type") == "tool_result" and block.get("is_error"):
                        text = result_text(block).lstrip()
                        for kind, needle, version in FINGERPRINTS:
                            if not kind.startswith("gate_") or not text.startswith("ACGM gate"):
                                continue
                            if needle not in text.split("\n", 1)[0]:
                                continue
                            events[kind] = events.get(kind, 0) + 1
                            versions.add(version)
                            gated.add(block.get("tool_use_id", ""))

            attachment = entry.get("attachment")
            if not isinstance(attachment, dict) or not attachment.get("hookEvent"):
                continue
            stdout = attachment.get("stdout") or ""
            if not stdout:
                continue
            for kind, needle, version in FINGERPRINTS:
                if needle not in stdout:
                    continue
                events[kind] = events.get(kind, 0) + 1
                versions.add(version)
                if kind.startswith("gate_"):
                    gated.add(attachment.get("toolUseID", ""))

    destructive = {i: c for i, c in bash_calls.items() if c and is_destructive(c)}
    gaps = {i: c for i, c in destructive.items() if i not in gated}

    return {
        "transcript": os.path.basename(path)[:8],
        "project": cwd,
        "first": first,
        "last": last,
        "mtime": os.path.getmtime(path),
        "bash_total": len(bash_calls),
        "destructive_total": len(destructive),
        "events": events,
        "versions": sorted(versions),
        "gaps": [c[:100] for c in gaps.values()],
        "gap_count": len(gaps),
    }


def verdict(session: dict) -> str:
    if not session["events"]:
        return "INACTIVE" if session["bash_total"] else "IDLE"
    if session["gap_count"]:
        return "GAPS"
    if session["destructive_total"] == 0:
        return "ACTIVE (untested)"
    return "ACTIVE"


def collect(since_days: float | None, project: str | None) -> list[dict]:
    cutoff = time.time() - since_days * 86400 if since_days else 0
    sessions = []
    for path in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        if os.path.getmtime(path) < cutoff:
            continue
        session = read_session(path)
        if project and session["project"] != project:
            continue
        sessions.append(session)
    return sorted(sessions, key=lambda s: s["mtime"], reverse=True)


def render(sessions: list[dict]) -> int:
    if not sessions:
        print("\nNo sessions matched.\n")
        return 0

    print("\nACGM activity — from recorded hook output, not from configuration\n")
    gaps_total = 0
    for session in sessions:
        stamp = time.strftime("%m-%d %H:%M", time.localtime(session["mtime"]))
        state = verdict(session)
        print(f"  {state:<18}{stamp}  {session['project'] or '(unknown project)'}")
        print(
            f"  {'':<18}session {session['transcript']}…  "
            f"{session['bash_total']} Bash call(s), "
            f"{session['destructive_total']} matched the destructive filter"
        )
        for kind, count in sorted(session["events"].items()):
            print(f"  {'':<18}  {count:>4}  {LABELS.get(kind, kind)}")
        if session["versions"]:
            print(f"  {'':<18}  hook version fingerprint: {', '.join(session['versions'])}")
        if len(session["versions"]) > 1:
            print(
                f"  {'':<18}  more than one version ran in this session; gaps below may"
                f" predate the current whitelist"
            )
        gaps_total += session["gap_count"]
        for command in session["gaps"][:SHOW_GAPS]:
            print(f"  {'':<18}  UNGATED: {command.splitlines()[0][:96]}")
        hidden = session["gap_count"] - len(session["gaps"][:SHOW_GAPS])
        if hidden > 0:
            print(f"  {'':<18}  ... and {hidden} more (use --json for the full list)")
        print()

    print("  ACTIVE            hooks ran, and every destructive call was gated")
    print("  ACTIVE (untested) hooks ran, but nothing destructive was attempted —")
    print("                    the gate had no occasion to fire, which is not a failure")
    print("  INACTIVE          commands ran and ACGM produced no output at all")
    print("  GAPS              a destructive call has no gate output against its id\n")

    if gaps_total:
        print(f"  {gaps_total} ungated destructive call(s). Investigate before trusting the gate.")
        print("  A gap is judged against TODAY's whitelist, so two benign causes exist:")
        print("    - the command ran before that pattern was added to the whitelist;")
        print("    - the plugin was reinstalled mid-session, or was not installed yet.")
        print("  Anything else means the gate was absent or failing when it mattered.\n")
        return 1
    print("  No ungated destructive calls in the sessions examined.\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", help="absolute project path to filter on")
    parser.add_argument("--since", type=float, help="only sessions active in the last N days")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    if not os.path.isdir(PROJECTS):
        print(f"No transcript directory at {PROJECTS}", file=sys.stderr)
        return 0

    sessions = collect(args.since, args.project)
    if args.json:
        print(json.dumps({"sessions": sessions}, ensure_ascii=False, indent=2))
        return 1 if any(s["gap_count"] for s in sessions) else 0
    return render(sessions)


if __name__ == "__main__":
    sys.exit(main())
