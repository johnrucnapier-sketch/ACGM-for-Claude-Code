#!/usr/bin/env python3
"""Behaviour tests for the SessionEnd ledger checks.

These run the real SessionEnd hook as a subprocess, the way Claude Code runs it.
Before v0.9 the sessionend mode had no tests at all, so these also cover the
pre-existing "never create files in an ungoverned project" rule.

Hermeticity is a hard requirement (EVIDENCE E-020): every test builds its own
directory and its own environment and inherits nothing but PATH.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "scripts" / "sessionend-obligations.sh"

CLAIM = """# C-20260806-01: the ledger carrier is the working tree

- **编号 / Id:** C-20260806-01
- **起草依据 / Closure signal:** human_ruling
- **状态 / Status:** 待认定 / pending
"""


def run_hook(cwd: Path, payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke the SessionEnd hook exactly as the harness would."""
    return subprocess.run(
        ["sh", str(HOOK)],
        cwd=str(cwd),
        input=json.dumps(payload or {}),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_CONFIG_GLOBAL": os.devnull},
    )


class LedgerTests(unittest.TestCase):
    def test_ungoverned_project_gets_no_files_and_no_report(self) -> None:
        """The rule v0.1's PostToolUse hook was corrected for: stay out."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_hook(root)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertFalse((root / ".governance").exists())

    def test_unruled_draft_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".governance" / "claims").mkdir(parents=True)
            (root / ".governance" / "decisions").mkdir(parents=True)
            (root / ".governance" / "claims" / "C-20260806-01.md").write_text(CLAIM, encoding="utf-8")

            result = run_hook(root)

            self.assertIn("C-20260806-01", result.stderr)
            self.assertIn("nobody has ruled on", result.stderr)
            # And it is persisted, because this project opted in.
            recorded = (root / ".governance" / "OPEN_OBLIGATIONS.md").read_text(encoding="utf-8")
            self.assertIn("C-20260806-01", recorded)

    def test_draft_named_by_a_decision_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".governance" / "claims").mkdir(parents=True)
            (root / ".governance" / "decisions").mkdir(parents=True)
            (root / ".governance" / "claims" / "C-20260806-01.md").write_text(CLAIM, encoding="utf-8")
            (root / ".governance" / "decisions" / "ADR-0001-carrier.md").write_text(
                "- **来源草案 / From:** C-20260806-01\n", encoding="utf-8"
            )

            result = run_hook(root)

            self.assertNotIn("nobody has ruled on", result.stderr)

    def test_promotion_is_matched_by_id_not_by_filename(self) -> None:
        """A decision may be named anything; only the recorded id settles it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".governance" / "claims").mkdir(parents=True)
            (root / ".governance" / "decisions").mkdir(parents=True)
            (root / ".governance" / "claims" / "C-20260806-01.md").write_text(CLAIM, encoding="utf-8")
            (root / ".governance" / "claims" / "C-20260806-02.md").write_text(CLAIM, encoding="utf-8")
            (root / ".governance" / "decisions" / "anything.md").write_text(
                "From: C-20260806-02\n", encoding="utf-8"
            )

            result = run_hook(root)

            self.assertIn("C-20260806-01", result.stderr)
            self.assertNotIn("C-20260806-02", result.stderr)

    def test_uncommitted_ledger_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "--initial-branch=main")
            (root / ".governance" / "claims").mkdir(parents=True)
            (root / ".governance" / "decisions").mkdir(parents=True)
            (root / ".governance" / "claims" / "C-20260806-01.md").write_text(CLAIM, encoding="utf-8")

            result = run_hook(root)

            self.assertIn("not in the repository", result.stderr)

    def test_committed_ledger_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "--initial-branch=main")
            (root / ".governance" / "claims").mkdir(parents=True)
            (root / ".governance" / "decisions").mkdir(parents=True)
            claim = root / ".governance" / "claims" / "C-20260806-01.md"
            claim.write_text(CLAIM, encoding="utf-8")
            decision = root / ".governance" / "decisions" / "ADR-0001-carrier.md"
            decision.write_text("From: C-20260806-01\n", encoding="utf-8")
            git(root, "add", ".governance")
            git(root, "commit", "-m", "ledger")

            result = run_hook(root)

            self.assertNotIn("not in the repository", result.stderr)

    def test_hook_never_fails_the_session(self) -> None:
        """A broken ledger must not take the session down with it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".governance").mkdir()
            # claims/ is a file where a directory is expected.
            (root / ".governance" / "claims").write_text("not a directory", encoding="utf-8")

            result = run_hook(root, {"transcript_path": "/nonexistent/transcript.jsonl"})

            self.assertEqual(result.returncode, 0)

    def test_malformed_stdin_is_survivable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                ["sh", str(HOOK)],
                cwd=tmp,
                input="not json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                check=False,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
            )
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
