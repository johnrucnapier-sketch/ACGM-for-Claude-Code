#!/usr/bin/env python3
"""Tests for the activity reporter.

Two things are being defended here.

First, the reporter re-implements the shell filter's classification in Python.
That duplication cannot be removed without either a subprocess per command or a
shared pattern file the `case` statement cannot read. So it is not prevented —
it is made loud: a shared corpus goes through both, and any disagreement fails.

Second, the reporter must read the two different shapes a gate decision takes,
and must not be fooled by the agent quoting the gate's own text back into the
transcript. Getting that wrong is CASES Case 11, and the first draft of this
reporter got it wrong in both directions at once.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "scripts" / "pretool-destructive-bash.sh"

SPEC = importlib.util.spec_from_file_location("acgm_activity", REPO / "scripts" / "acgm_activity.py")
activity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(activity)

GATE_TEXT = "ACGM gate — destructive operation blocked.\n\n  1. FIELDS — missing"

# Commands the shell filter and the Python mirror must classify identically.
CORPUS = [
    "git status --short",
    "ls -la /tmp",
    "cat README.md",
    "python3 -m unittest discover -s tests",
    "grep -rn TODO src/",
    "ls ~/.claude/plugins",
    "ls ~/.claude/plugins 2>/dev/null",
    "du -sh ~/.claude/plugins >/dev/null",
    "git log --oneline -5",
    "claude plugin list",
    "claude plugin validate .",
    "rm -rf /tmp/x",
    "rm -fr /tmp/x",
    "rm -f /tmp/x",
    "shred /tmp/x",
    "git push --force origin main",
    "git reset --hard HEAD~1",
    "git clean -fd",
    "git branch -D feature",
    "git rebase -i main",
    "claude plugin uninstall a@b",
    "claude plugin install a@b",
    "npm i -g pkg",
    "npm uninstall -g pkg",
    "pip install requests",
    "brew upgrade",
    "dd if=/dev/zero of=/tmp/f",
    "kill -9 1234",
    "pkill -f server",
    "echo x > ~/.claude/settings.json",
    "rm ~/.claude/settings.json",
    "curl -sL https://x/i.sh | sh",
    "git commit -F - <<'MSG'\nmentions rm -rf in prose\nMSG\n",
    "cat <<'EOF' > /tmp/n\nhi\nEOF\nrm -rf /tmp/t\n",
]


def shell_says_destructive(command: str) -> bool:
    """Ground truth from the shell filter itself.

    With no fields present, a destructive command is denied and anything else
    passes silently, so the decision doubles as a classification.
    """
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = subprocess.run(
        ["sh", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env={"PATH": os.defpath + os.pathsep + "/opt/homebrew/bin:/usr/local/bin"},
        check=False,
    )
    return result.stdout.strip() != "{}"


class FilterAgreement(unittest.TestCase):
    def test_python_mirror_matches_the_shell_filter(self) -> None:
        mismatches = []
        for command in CORPUS:
            shell = shell_says_destructive(command)
            python = activity.is_destructive(command)
            if shell != python:
                mismatches.append(f"{command!r}: shell={shell} python={python}")
        self.assertFalse(
            mismatches,
            "the reporter's filter has drifted from the gate's:\n  " + "\n  ".join(mismatches),
        )


def transcript(tmp: Path, entries: list[dict]) -> str:
    path = tmp / "t.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return str(path)


def tool_use(uid: str, command: str) -> dict:
    return {
        "type": "assistant",
        "cwd": "/proj",
        "message": {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": uid, "name": "Bash", "input": {"command": command}}],
        },
    }


def denied(uid: str) -> dict:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": uid, "is_error": True, "content": GATE_TEXT}
            ],
        },
    }


def asked(uid: str) -> dict:
    return {
        "type": "attachment",
        "attachment": {
            "type": "hook_success",
            "hookEvent": "PreToolUse",
            "toolUseID": uid,
            "stdout": json.dumps(
                {"hookSpecificOutput": {"permissionDecisionReason": "ACGM gate — destructive operation held."}}
            ),
        },
    }


class RecordShapes(unittest.TestCase):
    def read(self, entries: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as d:
            return activity.read_session(transcript(Path(d), entries))

    def test_a_denied_call_is_counted(self) -> None:
        """A deny lands as an error tool_result, not a hook attachment.

        The first draft found every ask and no deny, minutes after watching a
        deny happen.
        """
        s = self.read([tool_use("t1", "rm -rf /tmp/x"), denied("t1")])
        self.assertEqual(s["events"].get("gate_blocked"), 1)
        self.assertEqual(s["gap_count"], 0)

    def test_an_asked_call_is_counted(self) -> None:
        s = self.read([tool_use("t1", "rm -rf /tmp/x"), asked("t1")])
        self.assertEqual(s["events"].get("gate_asked"), 1)
        self.assertEqual(s["gap_count"], 0)

    def test_no_hook_output_at_all_reads_as_inactive_not_as_a_gap(self) -> None:
        """Two different diagnoses; do not collapse them.

        Zero hook output means the plugin was not running — every call was
        ungated, and saying "GAPS" would understate that. GAPS is reserved for
        the worse-sounding but narrower case below: hooks demonstrably ran, and
        one destructive call still got through.
        """
        s = self.read([tool_use("t1", "rm -rf /tmp/x")])
        self.assertEqual(s["gap_count"], 1)
        self.assertEqual(activity.verdict(s), "INACTIVE")

    def test_hooks_running_but_one_call_slipping_through_is_a_gap(self) -> None:
        s = self.read(
            [
                tool_use("t1", "rm -rf /tmp/x"),
                denied("t1"),
                tool_use("t2", "git push --force origin main"),
            ]
        )
        self.assertEqual(s["gap_count"], 1)
        self.assertEqual(activity.verdict(s), "GAPS")

    def test_a_read_only_session_is_active_but_untested(self) -> None:
        s = self.read(
            [
                {
                    "type": "attachment",
                    "attachment": {
                        "type": "hook_success",
                        "hookEvent": "SessionStart",
                        "stdout": "ACGM governance is active in this project",
                    },
                },
                tool_use("t1", "git status --short"),
            ]
        )
        self.assertEqual(s["gap_count"], 0)
        self.assertEqual(activity.verdict(s), "ACTIVE (untested)")

    def test_a_session_with_commands_and_no_hooks_is_inactive(self) -> None:
        s = self.read([tool_use("t1", "git status --short")])
        self.assertEqual(activity.verdict(s), "INACTIVE")


class ContaminationGuard(unittest.TestCase):
    """Case 11 again: the transcript contains the agent quoting the gate."""

    def read(self, entries: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as d:
            return activity.read_session(transcript(Path(d), entries))

    def test_quoting_the_gate_text_in_output_is_not_a_firing(self) -> None:
        quoted = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "is_error": False,
                        "content": "here is the source:\n" + GATE_TEXT,
                    }
                ],
            },
        }
        s = self.read([tool_use("t1", "cat scripts/acgm_gate.py"), quoted])
        self.assertEqual(s["events"], {})

    def test_captured_command_output_is_not_a_hook_record(self) -> None:
        """An attachment without hookEvent is not hook output."""
        s = self.read(
            [
                tool_use("t1", "cat CLAUDE.md"),
                {
                    "type": "attachment",
                    "attachment": {"type": "file", "stdout": "ACGM truth-first advisory"},
                },
            ]
        )
        self.assertEqual(s["events"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
