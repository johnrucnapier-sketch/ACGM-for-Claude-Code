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

A complete gate emits no decision at all: it hands back to the harness's normal
permission flow, where the human decides. Evidence is not authorization -- and
"ask" is not enforcement either, since it is a no-op wherever the permission mode
auto-accepts (EVIDENCE E-023, which is why v0.4.1 stopped returning it).

Under ACGM_HOOK_MODE=sessionend the same file reports what the session is walking
away from: unverified obligations, unruled drafts, and an uncommitted ledger.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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


FIELD_COMMENT = re.compile(r"^\s*#\s*(ACGM-[A-Z-]+)\s*[:：]\s*(.*)$")


def split_command(command: str) -> tuple[str, str]:
    """Separate the ACGM field comments from the operation itself.

    The fields live in the command from v0.8. They used to be read from the
    agent's most recent message, which put the check on the wrong side of a race:
    the transcript is not always flushed when the hook runs, so identical calls
    were sometimes accepted and sometimes denied for "missing fields" (E-027).
    Worse, a stale read surfaced an *earlier* turn's fields and authorised an
    operation they were never written for (E-025).

    The command is the one thing the hook always receives intact, and it is the
    thing being authorised. Fields carried on it cannot be stale, cannot be
    missing due to timing, and cannot belong to a different call.
    """
    fields, rest = [], []
    for line in command.splitlines():
        (fields if FIELD_COMMENT.match(line) else rest).append(line)
    return "\n".join(fields), "\n".join(rest)


def missing_fields(field_block: str) -> list[str]:
    present = {}
    for line in field_block.splitlines():
        match = FIELD_COMMENT.match(line)
        if match:
            present[match.group(1)] = match.group(2).strip().strip("`").strip()
    absent = []
    for field in FIELDS:
        value = present.get(field, "")
        if len(value) < MIN_FIELD_CHARS or PLACEHOLDER.match(value):
            absent.append(field)
    return absent


# Words that name the tool, not the thing being operated on.
NOT_A_TARGET = {
    "sudo", "env", "time", "xargs", "git", "npm", "pip", "brew", "claude", "plugin",
    "marketplace", "systemctl", "launchctl", "install", "uninstall", "update",
    "remove", "enable", "disable", "reset", "clean", "push", "force", "branch",
    "checkout", "rebase", "stash", "drop", "clear", "table", "database", "from",
    "delete", "truncate", "shred", "rmdir", "pkill", "shutdown", "reboot", "mkfs",
    "filter", "refresh", "global", "recursive", "hard",
}
TOKEN = re.compile(r"[A-Za-z0-9_.@:~/-]{3,}")


def target_tokens(command: str) -> list[str]:
    """Words from the command that name what it acts on.

    Used to bind the four fields to *this* operation. Flags and the names of the
    tools themselves are excluded; what remains is paths, ids, branch names and
    similar operands.
    """
    # The shell filter already stripped heredoc bodies and /dev/null redirects
    # before deciding this was destructive; here the raw invocation is fine,
    # because any token in it is still a token of *this* call.
    tokens = []
    for raw in TOKEN.findall(command):
        word = raw.strip("'\"`,;")
        if not word or word.startswith("-"):
            continue
        if word.lower() in NOT_A_TARGET:
            continue
        if any(ch in word for ch in "/@:") or len(word) >= 5:
            tokens.append(word)
    return tokens


def fields_name_this_target(text: str, command: str) -> bool:
    """True if the fields mention something the command actually acts on.

    Without this, the gate can be satisfied by evidence written for an earlier
    operation: the fields stay the most recent assistant text, so the next
    destructive call inherits them. Observed 2026-08-05 — a command passed on
    fields written for the previous one, and the pass was initially misread as
    the command not being destructive at all.

    A basename also counts, so a field may cite a path in a different but
    equivalent form.
    """
    tokens = target_tokens(command)
    if not tokens:
        return True  # nothing identifiable to bind to; do not invent a failure
    haystack = text.lower()
    for token in tokens:
        needle = token.lower()
        if needle in haystack:
            return True
        base = needle.rstrip("/").rsplit("/", 1)[-1]
        if len(base) >= 4 and base in haystack:
            return True
    return False


def split_segments(command: str) -> list[str]:
    """Split on shell separators, ignoring any that sit inside quotes.

    A ';' or a newline inside a quoted argument is data, not an operation
    boundary -- the shell does not treat it as one either. Splitting on it made a
    single `python3 -c "..."` look like twenty-two operations, and STANDALONE
    then had no satisfiable form: no way of writing that command could pass. A
    gate that states an impossible requirement teaches the operator to route
    around it (E-021), which is the failure this project is least able to afford.

    Note what is deliberately *not* done here: the quoted body is not stripped
    before the destructive filter runs. `sh -c "rm -rf /"` carries its verb
    inside quotes, and dropping it would trade a false positive for a false
    negative. Per this gate's own policy, misses are the worse error.

    Unbalanced quotes fall back to the naive split, which over-segments. That
    direction can only deny, never permit.
    """
    segments: list[str] = []
    current: list[str] = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(command):
                current.append(char)
                current.append(command[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
            current.append(char)
            index += 1
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            continue
        if char in ";\n":
            segments.append("".join(current))
            current = []
            index += 1
            continue
        if command.startswith("&&", index) or command.startswith("||", index):
            segments.append("".join(current))
            current = []
            index += 2
            continue
        if char == "|":
            segments.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    if quote:
        return SEPARATORS.split(command)
    segments.append("".join(current))
    return segments


def operative_segments(command: str) -> list[str]:
    """Segments that actually do something, ignoring environment setup."""
    return [
        segment.strip()
        for segment in split_segments(command)
        if segment.strip() and not PREPARATORY.match(segment)
    ]


def bash_is_read_only(command: str) -> bool:
    """Whether every operative segment of a Bash call only reads.

    `READ_ONLY_BASH` is anchored, so it answers "does this command *start* with a
    read-only verb". Applied to a whole invocation that is the wrong question:
    `cd repo && git status` never matched, which made the most common shape of a
    real inspection invisible to the evidence check. Ask it per segment instead --
    `PREPARATORY` already drops the `cd` -- and require *all* of them to pass, so
    `cd repo && ls && <mutation>` still does not count as evidence.
    """
    segments = operative_segments(command or "")
    return bool(segments) and all(READ_ONLY_BASH.match(segment) for segment in segments)


def has_prior_evidence(calls: list[tuple[str, str]], gated_command: str = "") -> bool:
    """Whether a read-only call already happened before the one being gated.

    PreToolUse fires *before* the call is written to the transcript, so the last
    entry is usually the previous call, not this one. Dropping it blindly threw
    away the single most useful piece of evidence -- the inspection immediately
    before -- and denied three consecutive, correctly evidenced invocations
    (2026-08-06, this gate blocking its own release's installation). Drop the
    last entry only when it really is the command being gated.
    """
    prior = calls[:-1] if calls and calls[-1][1] == gated_command else calls
    for name, command in prior:
        if name in READ_ONLY_TOOLS:
            return True
        if name == "Bash" and bash_is_read_only(command or ""):
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


CLAIM_ID = re.compile(r"C-\d{8}-\d{2}")


def pending_claims(ledger_dir: str) -> list[str]:
    """Drafted claims that no decision file references yet.

    Purely a file-existence question: a claim is pending until some file in
    decisions/ names its id. This says nothing about whether the human agreed --
    it cannot, and the skill text must not pretend otherwise.
    """
    claims_dir = os.path.join(ledger_dir, "claims")
    decisions_dir = os.path.join(ledger_dir, "decisions")
    try:
        drafted = sorted(
            name[:-3] for name in os.listdir(claims_dir)
            if name.endswith(".md") and CLAIM_ID.fullmatch(name[:-3])
        )
    except OSError:
        return []
    if not drafted:
        return []
    referenced: set[str] = set()
    try:
        for name in os.listdir(decisions_dir):
            if not name.endswith(".md"):
                continue
            try:
                with open(os.path.join(decisions_dir, name), encoding="utf-8", errors="replace") as fh:
                    referenced.update(CLAIM_ID.findall(fh.read()))
            except OSError:
                continue
    except OSError:
        pass
    return [claim for claim in drafted if claim not in referenced]


def uncommitted_ledger(ledger_dir: str) -> bool:
    """Whether .governance/ has changes that are not in the repository yet.

    Writing a file into the working tree is not the same as recording it. The
    hook only makes that gap visible -- it never commits, because Principle Six
    reserves committing for the human.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", ledger_dir],
            cwd=os.path.dirname(ledger_dir) or ".",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def session_end() -> None:
    """Report what this session is about to walk away from.

    Two independent debts, reported together because they share the only moment
    a session has left:

      obligations  a VERIFY-AFTER promise no later tool call could have kept
      ledger       drafts nobody ruled on, and ledger edits not yet committed

    Everything here is decidable from the filesystem and the transcript. The
    hook has no judgment: it cannot tell which threads are still open, so it
    does not touch OPEN_THREADS.md. That file is the agent's to maintain, and
    the next session's grounding is where an unclosed thread gets caught.
    """
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)

    transcript = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    promises = unresolved_obligations(transcript) if transcript else []

    # Persist only where the project already opted into governance scaffolding.
    # Creating files in someone's repository uninvited is the behaviour v0.1's
    # PostToolUse hook was corrected for; do not reintroduce it here.
    ledger_dir = os.path.join(os.getcwd(), ".governance")
    has_ledger = os.path.isdir(ledger_dir)
    unruled = pending_claims(ledger_dir) if has_ledger else []
    unrecorded = uncommitted_ledger(ledger_dir) if has_ledger else False

    if not promises and not unruled and not unrecorded:
        sys.exit(0)

    lines: list[str] = []
    if promises:
        lines += ["ACGM — session ending with unverified post-action obligations:", ""]
        lines += [f"  - {promise}" for promise in promises]
        lines += [
            "",
            "Each of these declared a check that no later tool call could have run.",
            "The operation is not done; it is unverified. Carry this into the next",
            "session and verify before building on it.",
            "",
        ]
    if unruled:
        lines += ["ACGM — drafted decisions nobody has ruled on:", ""]
        lines += [f"  - {claim}" for claim in unruled]
        lines += [
            "",
            "These are drafts, not decisions. They are on disk and nothing is lost,",
            "but no human confirmed them, so nothing downstream may treat them as",
            "settled.",
            "",
        ]
    if unrecorded:
        lines += [
            "ACGM — .governance/ has changes that are not in the repository.",
            "",
            "A file in the working tree survives less than a file in a commit, and",
            "the ledger exists precisely to survive. Review and commit it yourself;",
            "this hook does not commit on your behalf.",
            "",
        ]
    report = "\n".join(lines)

    if has_ledger:
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
    field_block, operation = split_command(command)

    problems: list[str] = []

    segments = operative_segments(operation)
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

    absent = missing_fields(field_block)
    if absent:
        problems.append(
            "FIELDS — missing or placeholder: %s\n"
            "    Put them in the command itself, as comment lines above the\n"
            "    operation. Each needs real content, not a template." % ", ".join(absent)
        )
    elif not fields_name_this_target(field_block, operation):
        problems.append(
            "BINDING — the fields do not name anything this command acts on:\n"
            "    %s\n"
            "    Fields copied from a previous operation would otherwise license\n"
            "    this one. Name the actual target."
            % ", ".join(sorted(set(target_tokens(operation)))[:6])
        )

    if transcript:
        calls = recent_tool_uses(transcript, EVIDENCE_WINDOW)
        if calls and not has_prior_evidence(calls, command):
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
        + "\n\nRetry with the four fields as comment lines in the command itself:\n\n"
        "    # ACGM-EVIDENCE: primary source establishing each target identifier\n"
        "    # ACGM-CURRENT-STATE: the target's state, read in this session\n"
        "    # ACGM-VERIFY-AFTER: the post-action check and its success signal\n"
        "    # ACGM-ROLLBACK: recovery if the target or the result is wrong\n"
        "    <the operation, on its own line>\n\n"
        "They travel with the operation they authorise, so they cannot be stale and\n"
        "cannot belong to a different call. Supplying them lifts this block; it does\n"
        "not authorize the operation, which still goes to the human as usual.",
    )


if __name__ == "__main__":
    mode = os.environ.get("ACGM_HOOK_MODE", "gate")
    if mode == "sessionend":
        session_end()
    elif mode == "gate":
        main()
    else:
        emit(None)
