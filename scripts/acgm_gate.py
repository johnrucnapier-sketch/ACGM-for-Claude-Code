#!/usr/bin/env python3
"""ACGM v0.4 structural gate for destructive operations.

Invoked by pretool-destructive-bash.sh only after the cheap whitelist matched.
Reads the PreToolUse payload on stdin, emits a PreToolUse hook decision on
stdout, and never exits non-zero: a broken gate must not block work.

Three checks, all decidable from the tool call and the transcript. None of them
can be satisfied by prose alone -- that is the whole point. v0.1 grepped for the
literal markers "(a)".."(d)" and was satisfied by four characters.

  FIELDS     four named fields, each carrying real content
  STANDALONE the destructive command is the only operative segment
  EVIDENCE   a read-only tool call already happened in this session

A complete gate still returns "ask". Evidence is not authorization.
"""

from __future__ import annotations

import json
import os
import re
import sys

FIELDS = (
    "ACGM-EVIDENCE",
    "ACGM-CURRENT-STATE",
    "ACGM-VERIFY-AFTER",
    "ACGM-ROLLBACK",
)

# A field whose value is a template, a shrug, or an inherited claim is absent.
PLACEHOLDER = re.compile(
    r"^\s*(?:<[^>]*>|\(.*\)|todo|tbd|n/?a|none|-+|\.\.\.|待定|略|同上|见上)\s*$",
    re.IGNORECASE,
)
MIN_FIELD_CHARS = 12

# Segment separators that bind separate operations into one invocation.
SEPARATORS = re.compile(r";|&&|\|\||(?<!\|)\|(?!\|)|\n")
# Segments that only prepare the environment are not separate operations.
PREPARATORY = re.compile(r"^\s*(?:cd|export|set|umask|source|\.)\b")
SUBSTITUTION = re.compile(r"\$\(|`")

# Bash that reads without changing state. Used to confirm evidence exists.
READ_ONLY_BASH = re.compile(
    r"^\s*(?:ls|cat|head|tail|wc|stat|file|find|grep|rg|ps|df|du|which|type|env|"
    r"pwd|echo|printf|date|shasum|sha256sum|md5|diff|jq|sort|uniq|awk|sed(?!\s+-i)|"
    r"git\s+(?:status|log|show|diff|ls-tree|ls-files|rev-parse|rev-list|describe|"
    r"branch(?!\s+-[dD])|remote|config\s+--get|cat-file|hash-object|fetch)|"
    r"claude\s+plugin\s+(?:list|details|validate)|npm\s+(?:view|ls)|python3?\s+-c)\b"
)
READ_ONLY_TOOLS = {"Read", "Grep", "Glob", "NotebookRead", "WebFetch", "WebSearch"}
EVIDENCE_WINDOW = 12


def emit(decision: str | None, reason: str = "") -> None:
    """Write a hook result and stop. `None` means pass through silently."""
    if decision is None:
        print("{}")
    else:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": decision,
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    sys.exit(0)


def last_assistant_text(path: str) -> str:
    """The agent's most recent prose, where the four fields must appear."""
    text = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                blocks = message.get("content")
                if not isinstance(blocks, list):
                    continue
                buffer = "".join(
                    block.get("text", "")
                    for block in blocks
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                if buffer.strip():
                    text = buffer
    except OSError:
        return ""
    return text[-8000:]


def recent_tool_uses(path: str, limit: int) -> list[tuple[str, str]]:
    """(tool_name, command) for the most recent tool calls, oldest first."""
    calls: list[tuple[str, str]] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                blocks = message.get("content")
                if not isinstance(blocks, list):
                    continue
                for block in blocks:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    payload = block.get("input") or {}
                    command = payload.get("command", "") if isinstance(payload, dict) else ""
                    calls.append((block.get("name", ""), command))
    except OSError:
        return []
    return calls[-limit:]


def missing_fields(text: str) -> list[str]:
    absent = []
    for field in FIELDS:
        match = re.search(
            rf"{re.escape(field)}\s*[:：]\s*(.*?)(?=\n\s*ACGM-[A-Z-]+\s*[:：]|\n\s*```|\Z)",
            text,
            re.DOTALL,
        )
        if not match:
            absent.append(field)
            continue
        value = match.group(1).strip().strip("`").strip()
        if len(value) < MIN_FIELD_CHARS or PLACEHOLDER.match(value):
            absent.append(field)
    return absent


def operative_segments(command: str) -> list[str]:
    """Segments that actually do something, ignoring environment setup."""
    return [
        segment.strip()
        for segment in SEPARATORS.split(command)
        if segment.strip() and not PREPARATORY.match(segment)
    ]


def has_prior_evidence(calls: list[tuple[str, str]]) -> bool:
    # The final entry is the destructive call being gated; look behind it.
    for name, command in calls[:-1]:
        if name in READ_ONLY_TOOLS:
            return True
        if name == "Bash" and READ_ONLY_BASH.match(command or ""):
            return True
    return False


def assistant_turns(path: str) -> list[tuple[int, str, str]]:
    """(index, kind, payload) over assistant text and tool calls, in order.

    kind is "text" or "tool"; payload is the prose or the tool name.
    """
    turns: list[tuple[int, str, str]] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                message = entry.get("message")
                if not isinstance(message, dict):
                    continue
                blocks = message.get("content")
                if not isinstance(blocks, list):
                    continue
                for block in blocks:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        turns.append((len(turns), "text", block.get("text", "")))
                    elif block.get("type") == "tool_use":
                        turns.append((len(turns), "tool", block.get("name", "")))
    except OSError:
        return []
    return turns


def unresolved_obligations(path: str) -> list[str]:
    """VERIFY-AFTER promises with no room left for the check to have run.

    A declaration is settled only if at least two tool calls follow it: the
    operation itself, then the verification. One call means the operation ran
    and nothing checked it. Zero means the operation never happened, which is
    not an obligation.

    This is deliberately generous -- it cannot tell a real verification from any
    other call. It exists so a session cannot end silently on a promise, not to
    prove the promise was kept.
    """
    turns = assistant_turns(path)
    open_promises = []
    for index, kind, payload in turns:
        if kind != "text" or "ACGM-VERIFY-AFTER" not in payload:
            continue
        following = sum(1 for i, k, _ in turns if i > index and k == "tool")
        if following == 1:
            match = re.search(r"ACGM-VERIFY-AFTER\s*[:：]\s*(.+)", payload)
            promise = match.group(1).strip() if match else "(unreadable)"
            open_promises.append(promise[:160])
    return open_promises


def session_end() -> None:
    """Report VERIFY-AFTER promises the session is about to walk away from."""
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)

    transcript = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    if not transcript:
        sys.exit(0)

    promises = unresolved_obligations(transcript)
    if not promises:
        sys.exit(0)

    lines = [
        "ACGM — session ending with unverified post-action obligations:",
        "",
    ]
    lines += [f"  - {promise}" for promise in promises]
    lines += [
        "",
        "Each of these declared a check that no later tool call could have run.",
        "The operation is not done; it is unverified. Carry this into the next",
        "session and verify before building on it.",
        "",
    ]
    report = "\n".join(lines)

    # Persist only where the project already opted into governance scaffolding.
    # Creating files in someone's repository uninvited is the behaviour v0.1's
    # PostToolUse hook was corrected for; do not reintroduce it here.
    ledger_dir = os.path.join(os.getcwd(), ".governance")
    if os.path.isdir(ledger_dir):
        try:
            with open(os.path.join(ledger_dir, "OPEN_OBLIGATIONS.md"), "a", encoding="utf-8") as fh:
                fh.write(f"\n## Session ended with open obligations\n\n{report}")
        except OSError:
            pass
    sys.stderr.write(report)
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        emit(None)

    command = (payload.get("tool_input") or {}).get("command", "")
    transcript = payload.get("transcript_path") or payload.get("transcriptPath") or ""

    problems: list[str] = []

    segments = operative_segments(command)
    if len(segments) > 1:
        problems.append(
            "STANDALONE — this invocation runs %d operations in one call:\n    %s\n"
            "    Split them. Source inspection, the state change, and verification\n"
            "    must be separate tool calls, or ordering and partial failure stop\n"
            "    being auditable." % (len(segments), "\n    ".join(segments[:4]))
        )
    if segments and SUBSTITUTION.search(segments[0]):
        problems.append(
            "STANDALONE — the target is computed by command substitution, so it\n"
            "    cannot be read from the command text. Resolve it in its own\n"
            "    read-only call first, then pass the literal value."
        )

    text = last_assistant_text(transcript) if transcript else ""
    absent = missing_fields(text)
    if absent:
        problems.append(
            "FIELDS — missing or placeholder: %s\n"
            "    Each field needs current-session content, not a template and not\n"
            "    a claim inherited from a summary." % ", ".join(absent)
        )

    if transcript:
        calls = recent_tool_uses(transcript, EVIDENCE_WINDOW)
        if calls and not has_prior_evidence(calls):
            problems.append(
                "EVIDENCE — no read-only tool call precedes this one in the last\n"
                "    %d calls. Read the target's current state first; do not assert\n"
                "    it." % EVIDENCE_WINDOW
            )

    if not problems:
        # Complete gate: hand back to the harness's normal permission flow, where
        # the human decides. Never "allow" -- evidence is not authorization.
        emit(None)

    # "deny", not "ask". Observed 2026-08-05: this gate returned "ask" against a
    # real destructive command, the transcript shows the hook fired, and the
    # command ran anyway -- the session's permission mode auto-approved it. An
    # "ask" is a request routed through the permission mode; where that mode
    # auto-accepts, it is a no-op. An incomplete gate must not depend on the
    # operator's current mode to hold.
    #
    # Denying does not remove human authority, it relocates it: the block is
    # lifted by producing the evidence, and the completed gate then goes to the
    # human through the normal flow.
    emit(
        "deny",
        "ACGM gate — destructive operation blocked.\n\n"
        + "\n\n".join(f"  {index}. {problem}" for index, problem in enumerate(problems, 1))
        + "\n\nBefore retrying, state these four fields immediately above the call:\n\n"
        "    ACGM-EVIDENCE:      primary source establishing each target identifier\n"
        "    ACGM-CURRENT-STATE: the target's state, read in this session\n"
        "    ACGM-VERIFY-AFTER:  the specific post-action check and its success signal\n"
        "    ACGM-ROLLBACK:      recovery if the target or the result is wrong\n\n"
        "Supplying the four fields lifts this block; it does not authorize the\n"
        "operation. The completed gate then goes to the human as usual.",
    )


if __name__ == "__main__":
    mode = os.environ.get("ACGM_HOOK_MODE", "gate")
    if mode == "sessionend":
        session_end()
    elif mode == "gate":
        main()
    else:
        emit(None)
