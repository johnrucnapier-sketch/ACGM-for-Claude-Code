"""Observability cannot grant permissions, leak payloads, or break the Gate."""
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import acgm_observe as observe


class Observations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.logs = self.root / 'logs'
        self.env = {'ACGM_LOG_DIR': str(self.logs), 'ACGM_OBSERVATIONS': '1',
                    'CLAUDE_PROJECT_DIR': str(self.root), 'PYTHONDONTWRITEBYTECODE': '1'}
        self.patch = patch.dict(os.environ, self.env); self.patch.start(); self.addCleanup(self.patch.stop)
        self.payload = {'session_id': 'secret-session', 'tool_use_id': 'private-call',
                        'cwd': '/private/customer-project', 'hook_event_name': 'PostToolUse',
                        'tool_name': 'Bash', 'tool_input': {'command': 'echo PRIVATE_TOKEN_abc'},
                        'tool_response': {'stdout': 'PRIVATE_OUTPUT'}, 'transcript_path': '/private/transcript'}

    def rows(self):
        return [json.loads(line) for p in self.logs.glob('*.jsonl') for line in p.read_text().splitlines()]

    def hook(self, command, extra=None):
        payload = {**self.payload, 'tool_input': {'command': command}}
        env = {**os.environ, **self.env, **(extra or {})}
        return subprocess.run(['sh', str(REPO / 'scripts/pretool-destructive-bash.sh')],
                              input=json.dumps(payload), text=True, capture_output=True, env=env)

    def test_redacted_stable_ids_and_private_permissions(self):
        observe.record(self.payload, {})
        observe.record(self.payload)
        rows = self.rows(); raw = json.dumps(rows)
        for secret in ('secret-session', 'private-call', '/private/customer-project', 'PRIVATE_TOKEN_abc', 'PRIVATE_OUTPUT', '/private/transcript'):
            self.assertNotIn(secret, raw)
        self.assertEqual(rows[0]['session'], rows[1]['session'])
        self.assertEqual(self.logs.stat().st_mode & 0o777, 0o700)
        for p in self.logs.iterdir(): self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_actual_final_gate_verdict_once_and_unchanged(self):
        for command in ('cat /tmp/file', 'rm -rf /tmp/file', "ssh fixture 'systemctl restart app.service'"):
            with self.subTest(command=command):
                before = len(self.rows())
                off = self.hook(command, {'ACGM_OBSERVATIONS': '0'})
                on = self.hook(command)
                self.assertEqual((off.returncode, off.stdout), (on.returncode, on.stdout))
                self.assertEqual(len(self.rows()), before + 1)
                row = self.rows()[-1]
                self.assertEqual(row['outcome'], 'deny' if json.loads(on.stdout) else 'pass_through')

    def test_failed_storage_cannot_change_gate(self):
        broken = self.root / 'file'; broken.write_text('not a directory')
        for command in ('cat /tmp/file', 'rm -rf /tmp/file'):
            normal = self.hook(command, {'ACGM_OBSERVATIONS': '0'})
            broken_result = self.hook(command, {'ACGM_LOG_DIR': str(broken)})
            self.assertEqual(normal.stdout, broken_result.stdout)
            self.assertEqual(normal.returncode, broken_result.returncode)

    def test_lock_contention_skips_without_waiting(self):
        observe.record(self.payload, {})
        with (self.logs / '.lock').open('r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            observe.record(self.payload, {})
        self.assertEqual(len(self.rows()), 1)

    def test_symlink_target_is_untouched(self):
        outside = self.root / 'outside'; outside.mkdir()
        self.logs.symlink_to(outside, target_is_directory=True)
        observe.record(self.payload, {})
        self.assertFalse(list(outside.iterdir()))

    def test_key_symlink_and_hardlink_are_untouched(self):
        self.logs.mkdir(mode=0o700)
        marker = self.logs / '.acgm-observations-v1'
        marker.write_text('ACGM observations v1\n'); marker.chmod(0o600)
        secret = self.root / 'secret'; secret.write_bytes(b'X' * 32); secret.chmod(0o600)
        (self.logs / '.key').symlink_to(secret)
        observe.record(self.payload, {})
        self.assertFalse(self.rows()); self.assertEqual(secret.read_bytes(), b'X' * 32)
        (self.logs / '.key').unlink(); os.link(secret, self.logs / '.key')
        observe.record(self.payload, {})
        self.assertFalse(self.rows())

    def test_unowned_existing_directory_is_not_pruned(self):
        self.logs.mkdir(mode=0o700)
        original = self.logs / '2000-01-01.jsonl'; original.write_text('keep')
        observe.record(self.payload, {})
        self.assertEqual(original.read_text(), 'keep')
        self.assertFalse((self.logs / '.key').exists())

    def test_rotates_bounds_and_retains_only_named_files(self):
        observe.record(self.payload, {})
        (self.logs / '2000-01-01.jsonl').write_text('old')
        (self.logs / 'notes.txt').write_text('keep')
        with patch.object(observe, 'MAX_BYTES', 800):
            for _ in range(5): observe.record(self.payload, {})
        self.assertLessEqual(len(list(self.logs.glob('*.jsonl'))), 2)
        self.assertEqual((self.logs / 'notes.txt').read_text(), 'keep')
        self.assertFalse((self.logs / '2000-01-01.jsonl').exists())

    def test_summary_deduplicates_callbacks_not_distinct_attempts(self):
        decision = {'hookSpecificOutput': {'permissionDecision': 'deny', 'permissionDecisionReason':
                    'ACGM-DIAGNOSTIC\nACGM-DIAGNOSTIC: ' + json.dumps({'issues': [{'code': 'FIELDS'}, {'code': 'SECRET'}]})}}
        observe.record(self.payload, decision); observe.record(self.payload, decision)
        observe.record({**self.payload, 'tool_use_id': 'second'}, decision)
        result = observe.summary(self.logs)
        self.assertEqual(result['events']['gate_decision:deny'], 2)
        self.assertEqual(result['reason_codes'], {'FIELDS': 2, 'OTHER': 2})
        self.assertEqual(result['repeated_same_command_denials'], 1)

    def test_inspector_does_not_pollute_runtime_observations(self):
        r = subprocess.run([sys.executable, str(REPO / 'scripts/acgm-explain.py'), '--project', str(self.root)],
                           input=json.dumps(self.payload), text=True, capture_output=True, env=os.environ)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(self.logs.exists())

    def test_off_and_missing_session_leave_no_files(self):
        with patch.dict(os.environ, {'ACGM_OBSERVATIONS': '0'}): observe.record(self.payload, {})
        observe.record({'tool_name': 'Bash'}, {})
        self.assertFalse(self.logs.exists())

    def test_diagnostic_explains_evidence_and_preserves_denial(self):
        response = self.hook('rm -f /tmp/file')
        self.assertIn('entire evidence call must be read-only', response.stdout)
        self.assertEqual(json.loads(response.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
        response = self.hook("ssh fixture 'cat /tmp/file' 2>&1 | head -5")
        self.assertIn('preserve the host, user, key and port', response.stdout)


if __name__ == '__main__': unittest.main()
