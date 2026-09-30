#!/usr/bin/env python3
"""ACGM v0.4 structural gate for destructive operations.

Invoked by pretool-destructive-bash.sh only after the cheap whitelist matched.
Reads the PreToolUse payload on stdin, emits a PreToolUse hook decision on
stdout. Policy/runtime failures in PreToolUse fail closed.

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

import hashlib
import json
import os
import re
import subprocess
import sys

from acgm_policy import (
    EVIDENCE_WINDOW, SUBSTITUTION, split_command, operative_segments,
    missing_fields, fields_name_this_target, target_tokens, remote_needs_gate,
    has_prior_evidence, execution_problems, load_guards, load_policy, ToolCall, trusted_remote_readonly,
    trusted_remote_status, parse_remote, command_words, shell_words, WRITE_VERBS,
    bash_is_read_only, evidence_targets, operation_targets, literal_path, FIELD_COMMENT,
)

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


def issue(code: str, message: str, next_action: str, retryable: bool = False, **details) -> dict:
    return {"code": code, "message": message, "retryable": retryable,
            "next_safe_action": next_action, **details}


def deny(issues: list[dict]) -> None:
    # Keep Claude's supported Hook output schema. The bounded JSON diagnostic is
    # inside its reason string so both the model and the inspector see one result.
    emit("deny", "ACGM gate — destructive operation blocked.\n"
         + "\n".join(f"{i['code']}: {i['message']} Next: {i['next_safe_action']}" for i in issues)
         + "\nEvidence is not authorization; do not bypass a denial.\nACGM-DIAGNOSTIC: "
         + json.dumps({"schema_version": 1, "issues": issues}, ensure_ascii=False))


def context_issues(problems: list[str]) -> list[dict]:
    result = []
    for problem in problems:
        action = "Check the actual host, literal target and supported transport. Fields cannot waive this denial."
        if 'unsupported outer SSH shell operator' in problem:
            action = ("An outer pipe/redirection or compound shell operator is unsupported here. "
                      "Separate the remote inspection from local output processing; preserve the host, user, key and port. "
                      "Do not move a write into another wrapper to bypass the Gate.")
        result.append(issue(problem.split(" — ", 1)[0], problem, action))
    return result


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


def recent_tool_uses(path: str, limit: int | None, strict: bool = False) -> list[ToolCall]:
    """Claude adapter: normalize calls and successful matching tool results.

    A request alone is not evidence of execution. Invalid/unreadable transcripts
    contribute no evidence. Keep one extra call until the core excludes current.
    """
    calls = []
    results = {}
    seen = set()
    position = 0
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    raise ValueError("invalid entry")
                message = entry.get("message", {})
                if not isinstance(message, dict):
                    continue
                blocks = message.get("content", [])
                if not isinstance(blocks, list):
                    continue
                for block in blocks:
                    position += 1
                    if not isinstance(block, dict):
                        continue
                    if entry.get("type") == "assistant" and block.get("type") == "tool_use":
                        data = block.get("input") or {}
                        if not isinstance(data, dict):
                            raise ValueError("invalid tool input")
                        call_id = block.get("id", "")
                        if call_id and call_id in seen:
                            raise ValueError("duplicate tool id")
                        if call_id:
                            seen.add(call_id)
                        calls.append(ToolCall(
                            name=block.get("name", ""), command=data.get("command", ""),
                            path=data.get("file_path", data.get("notebook_path", "")),
                            call_id=call_id, started=position,
                        ))
                    elif entry.get("type") == "user" and block.get("type") == "tool_result":
                        call_id = block.get("tool_use_id", "")
                        if call_id in seen:
                            metadata = entry.get("toolUseResult")
                            failed = block.get("is_error", False) is not False
                            if isinstance(metadata, dict):
                                failed |= bool(metadata.get("is_error") or metadata.get("interrupted"))
                                exit_code = metadata.get("exitCode", metadata.get("exit_code", 0))
                                failed |= exit_code != 0
                            if call_id in results:
                                raise ValueError("duplicate result")
                            content = block.get("content", "")
                            if isinstance(content, list) and all(isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str) for b in content):
                                content = "".join(b["text"] for b in content)
                            text = content if isinstance(content, str) and len(content) <= 4096 else ""
                            results[call_id] = (not failed, position, text)
    except (OSError, ValueError, UnicodeError, TypeError):
        if strict:
            raise ValueError("unreadable or invalid transcript")
        return []
    selected = calls if limit is None else calls[-(limit + 1):]
    return [ToolCall(c.name, c.command, c.path, c.call_id,
                     results.get(c.call_id, (False, -1))[0], c.started,
                     results.get(c.call_id, (False, -1))[1],
                     results.get(c.call_id, (False, -1, ""))[2]) for c in selected]


def configured_policy_path(payload: dict) -> str | None:
    # Never anchor to payload.cwd: Claude updates it after a shell cd.
    path = os.environ.get("ACGM_POLICY_CONFIG")
    if path is not None:
        if not os.path.isabs(path):
            raise ValueError("ACGM_POLICY_CONFIG must be absolute")
        return path
    anchor = project_anchor()
    governance = os.path.join(anchor, ".governance")
    try:
        os.lstat(governance)
    except FileNotFoundError:
        return None  # ordinary project with no governance configuration
    if os.path.islink(governance):
        raise ValueError("project governance symlink requires explicit policy")
    # Listing distinguishes absent optional config from inaccessible governance.
    if "remote-path-guards.json" not in os.listdir(governance):
        return None
    path = os.path.join(governance, "remote-path-guards.json")
    if os.path.islink(path):
        raise ValueError("project policy symlink requires explicit policy")
    return path


def project_anchor() -> str:
    """Stable startup root, shared by Gate, SessionStart and project doctor."""
    anchor = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not os.path.isabs(anchor) or not os.path.isdir(anchor):
        raise ValueError("stable project anchor unavailable; set ACGM_POLICY_CONFIG")
    anchor = os.path.realpath(anchor)
    # Resolve only the repository containing the stable startup directory.
    # No arbitrary ancestor policy search; non-Git projects stop at startup.
    result = subprocess.run(
        ["git", "-C", anchor, "rev-parse", "--show-toplevel"],
        env={**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")}, "LC_ALL": "C"},
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
    )
    if result.returncode == 0:
        root = os.path.realpath(result.stdout.strip())
        if not os.path.isabs(result.stdout.strip()) or os.path.commonpath([root, anchor]) != root:
            raise ValueError("invalid Git project boundary")
        anchor = root
    elif "not a git repository" not in result.stderr:
        raise ValueError("project boundary resolution failed")
    return anchor


def configured_guards(payload: dict) -> list[tuple[str, str]]:
    path = configured_policy_path(payload)
    return load_guards(path) if path else []


def configured_policy(payload: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    path = configured_policy_path(payload)
    return load_policy(path) if path else ([], [])


def trusted_call(payload: dict, command: str, tools: list[dict]) -> bool:
    if not tools:
        return False
    transcript = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    calls = recent_tool_uses(transcript, EVIDENCE_WINDOW) if transcript else []
    return trusted_remote_readonly(command, tools, calls, payload.get("tool_use_id", ""))


def preflight() -> None:
    payload = json.load(sys.stdin)
    command = payload["tool_input"]["command"]
    _, operation = split_command(command)
    guards, tools = configured_policy(payload)
    problems = execution_problems(operation, guards, payload.get("cwd") or os.getcwd())
    if problems:
        deny(context_issues(problems))
    if trusted_call(payload, command, tools):
        print(json.dumps({"trusted_readonly": True, "needs_gate": False}))
        return
    from acgm_policy import command_words, split_segments
    ordinary_delete = any((w := command_words(s)) and w[0][0] == "rm" for s in split_segments(operation))
    print(json.dumps({"needs_gate": remote_needs_gate(operation) or ordinary_delete}))


def remote_probe() -> None:
    """Exit 0 when the wrapper should send this command to the gate, 1 when not.

    A separate mode rather than a branch inside the gate: the wrapper's cheap
    filter has to reach a verdict before it decides to run the gate at all.
    """
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)  # unreadable input is not evidence of safety
    command = (payload.get("tool_input") or {}).get("command", "")
    _, operation = split_command(command)
    sys.exit(0 if remote_needs_gate(operation) else 1)


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


def unresolved_obligations(path: str) -> list[tuple[int, str]]:
    """Post-action checks require successful, later, exact-target tool facts."""
    try:
        calls = recent_tool_uses(path, None, strict=True)
    except ValueError:
        return [(-1, "UNVERIFIED — transcript unavailable or invalid")]
    obligations = []
    for index, mutation in enumerate(calls):
        if mutation.name != "Bash" or bash_is_read_only(mutation.command):
            continue
        fields, operation = split_command(mutation.command)
        values = {m[1]: m[2].strip() for line in fields.splitlines()
                  if (m := FIELD_COMMENT.match(line))}
        promise = values.get("ACGM-VERIFY-AFTER")
        if promise is None:
            continue
        targets = operation_targets(operation)
        # Free prose describes the check; it cannot supply evidence or silently
        # substitute an unrelated target. Unsupported targets stay unresolved.
        declared = {literal_path(w.rstrip(".,;")) for w in target_tokens(promise)}
        observed = set()
        if mutation.finished >= 0 and targets and all(p in declared for _, p in targets):
            for check in calls[index + 1:]:
                if not check.succeeded or check.started <= mutation.finished:
                    continue
                if check.name == "Bash" and bash_is_read_only(check.command):
                    observed |= evidence_targets(check.command)
                elif check.name in ("Read", "NotebookRead") and (p := literal_path(check.path)):
                    observed.add(("", p))
        if not targets or not targets.issubset(observed):
            obligations.append((index, promise or "UNVERIFIED — empty verification requirement"))
    return obligations


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

    Persist unresolved VERIFY-AFTER declarations once per session and turn.
    Drafts and uncommitted ledger edits are transient status, printed only;
    writing those reminders into the ledger would trigger the next reminder.

    Everything here is decidable from the filesystem and the transcript. The
    hook has no judgment: it cannot tell which threads are still open, so it
    does not touch OPEN_THREADS.md. That file is the agent's to maintain, and
    the next session's grounding is where an unclosed thread gets caught.
    """
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.stderr.write("ACGM — UNVERIFIED: unreadable SessionEnd input\n")
        sys.exit(0)

    transcript = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    promises = unresolved_obligations(transcript) if transcript else [(-1, "UNVERIFIED — missing transcript")]

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
        lines += [f"  - {promise[:160]}" for _, promise in promises]
        lines += [
            "",
            "No successful later tool result establishes each declared exact target.",
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

    if has_ledger and promises:
        try:
            obligations_path = os.path.join(ledger_dir, "OPEN_OBLIGATIONS.md")
            try:
                with open(obligations_path, encoding="utf-8") as fh:
                    existing = fh.read()
            except FileNotFoundError:
                existing = ""
            # Stable on retries and transcript growth; identical checks in a
            # different session or at a different turn remain distinct debts.
            session = payload.get("session_id") or os.path.realpath(transcript)
            additions = []
            for index, promise in promises:
                key = json.dumps([session, index, promise], ensure_ascii=False)
                marker = "<!-- acgm-obligation:" + hashlib.sha256(key.encode()).hexdigest() + " -->"
                if marker not in existing:
                    additions.append(f"{marker}\n  - {promise[:160]}\n")
            if additions:
                with open(obligations_path, "a", encoding="utf-8") as fh:
                    fh.write("\n## Session ended with open obligations\n\n" + "\n".join(additions))
        except (OSError, UnicodeError):
            pass
    sys.stderr.write(report)
    sys.exit(0)


def trusted_hint(command: str, tools: list[dict], calls: list[ToolCall], current_id: str) -> list[dict]:
    # Suggest exact registered read-only forms only for the same host/path/argv.
    # Never suggest changing host, trust registry or arguments to get a pass.
    _, operation = split_command(command)
    remote = parse_remote(operation)
    if not remote or remote.error or remote.kind != "ssh":
        return []
    outer = shell_words(operation)
    if not outer or len(outer) != 3 or outer[0][0] != 'ssh' or outer[1][0] != remote.host:
        # The parser normalizes user@host and supported transport options. A
        # diagnostic must not turn that into advice to drop a user/key/port.
        return []
    words = shell_words(remote.payload)
    if not words:
        return []
    argv = [w for w, _ in words]
    entry = next((t for t in tools if t["host"] == remote.host and t["path"] == argv[0]), None)
    if entry is None:
        return []
    if argv[1:] not in entry["allowed_argv"]:
        return [issue("TRUSTED_ARGV_UNREGISTERED", "This argument vector is not registered as read-only.",
                      "Review the requested operation; do not change arguments or register new trust just to pass.")]
    code = trusted_remote_status(command, tools, calls, current_id)
    if code == "TRUSTED_READONLY":
        return []
    canonical = "ssh " + entry["host"] + " '" + " ".join(argv) + "'"
    expected = "ssh " + entry["host"] + " 'sha256sum " + entry["path"] + "'"
    retryable = code in ("TRUSTED_INVOCATION_SHAPE", "TRUSTED_EVIDENCE_MISSING")
    action = ("Use the exact standalone registered invocation and a separate single-file remote hash read."
              if retryable else "Inspect the failed, unordered or mismatched measurement. Do not update trust to silence it.")
    return [issue(code, "Exact registered read-only qualification was not established.", action, retryable,
                  canonical_invocation=canonical, expected_evidence_command=expected,
                  evidence_window=EVIDENCE_WINDOW)]


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        deny([issue("INPUT_INVALID", "Unreadable hook input.", "Provide a valid Bash hook payload.")])

    command = (payload.get("tool_input") or {}).get("command", "")
    transcript = payload.get("transcript_path") or payload.get("transcriptPath") or ""
    current_id = payload.get("tool_use_id", "")
    field_block, operation = split_command(command)
    guards, tools = configured_policy(payload)
    problems = execution_problems(operation, guards, payload.get("cwd") or os.getcwd())
    if problems:
        deny(context_issues(problems))
    if trusted_call(payload, command, tools):
        emit(None)

    segments = operative_segments(operation)
    issues = []
    if len(segments) > 1:
        issues.append(issue("STANDALONE", "Multiple operative segments in one gated call.",
                            "First separate source inspection, state change and verification into tool calls; then gather evidence and write fields for each resulting operation's own targets.", True))
    if segments and SUBSTITUTION.search(segments[0]):
        issues.append(issue("STANDALONE", "The target is computed by command substitution.",
                            "Resolve the target in a read-only call, then use its literal value.", True))

    absent = missing_fields(field_block)
    if absent:
        issues.append(issue("FIELDS", "Missing or placeholder command-comment fields.",
                            "Add the listed fields with current evidence, state, post-check and recovery details. A script argument named status does not establish read-only trust; only the exact registered tool invocation with matching hash evidence qualifies.",
                            True, missing_fields=absent))
    elif not fields_name_this_target(field_block, operation):
        issues.append(issue("BINDING", "The command-comment fields do not name this operation's target.",
                            "Describe the actual target; do not reuse another operation's fields.", True,
                            targets=sorted(set(target_tokens(operation)))[:6]))

    transcript_invalid = False
    try:
        calls = recent_tool_uses(transcript, EVIDENCE_WINDOW, strict=True) if transcript else []
    except ValueError:
        calls = []
        transcript_invalid = True
    if not has_prior_evidence(calls, command, current_id):
        targets = operation_targets(operation)
        unsupported = not targets and any(parse_remote(s) or
                         ((w := command_words(s)) and w[0][0] in WRITE_VERBS) for s in segments)
        if unsupported:
            # Four fields and unrelated reads cannot make this target supported.
            for item in issues:
                if item['code'] in ('FIELDS', 'BINDING'):
                    item['retryable'] = False
                    item['next_safe_action'] = "Resolve the unsupported resource first; fields alone cannot make this call pass."
            issues.append(issue("EVIDENCE_TARGET_UNSUPPORTED", "No supported filesystem target can bind this operation.",
                                "This version cannot verify this resource. Stop format retries; use a separately reviewed procedure or report the limitation."))
        else:
            code = "EVIDENCE_TRANSCRIPT_INVALID" if transcript_invalid else "EVIDENCE"
            issues.append(issue(code, "No successful target-bound read-only evidence in the last 12 prior calls.",
                                "Use the active session transcript and read each literal target or its direct parent on the same host. The entire evidence call must be read-only: do not combine ls with compilation, file creation or other mutations. Failed, pending or out-of-window reads do not count; a written explanation is not a tool result.",
                                not transcript_invalid,
                                targets=[{"host": h or "local", "path": p} for h, p in sorted(targets)]))
    if not issues:
        emit(None)  # Pass through to Claude's permission flow; never allow.
    hints = trusted_hint(command, tools, calls, current_id)
    if hints:
        # Missing trusted evidence has a direct read-only repair path. Suppress
        # irrelevant ordinary gate instructions without changing the verdict.
        issues = [i for i in issues if i['code'] not in ('FIELDS', 'BINDING', 'EVIDENCE')]
    deny(hints + issues)


if __name__ == "__main__":
    mode = os.environ.get("ACGM_HOOK_MODE", "gate")
    try:
        if mode == "sessionend":
            session_end()
        elif mode == "gate":
            main()
        elif mode == "remote":
            remote_probe()
        elif mode == "preflight":
            preflight()
        else:
            emit("deny", "ACGM gate — unsupported hook mode")
    except Exception:
        if mode == "sessionend":
            sys.stderr.write("ACGM — UNVERIFIED: SessionEnd policy failure\n")
            sys.exit(0)
        # Never expose paths/config contents or turn a policy failure into allow.
        deny([issue("POLICY_OR_RUNTIME_INVALID", "Policy configuration, anchor or runtime validation failed.",
                    "Check the project policy and runtime dependencies; fields cannot waive this denial.")])
