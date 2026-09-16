"""Synthetic-only v0.9.4 regressions. No command payload is ever executed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import acgm_policy as policy
from acgm_gate import recent_tool_uses

PREFIX = "/protected/remote/path"
GUARDS = [("nas", PREFIX)]
FIELDS = "\n".join(f"# {field}: inspect and recover {PREFIX}/a {PREFIX}/b /remote/a /remote/b locally in fixtures" for field in policy.FIELDS) + "\n"


def call(command, succeeded=True, host="nas", call_id="evidence"):
    return policy.ToolCall("Bash", command, call_id=call_id, succeeded=succeeded)


def entries(command="ssh nas 'stat /remote/a'", success=True):
    return [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "e1", "name": "Bash", "input": {"command": command}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "e1", "is_error": not success, "content": "synthetic fixture result"}]}},
    ]


class PolicySecurityTests(unittest.TestCase):
    def test_remote_read_evidence_uses_payload_policy(self):
        for verb in ("stat", "cat", "sha256sum", "shasum"):
            command = f"ssh nas '{verb} /remote/a'"
            with self.subTest(command=command):
                self.assertTrue(policy.bash_is_read_only(command))
                self.assertTrue(policy.has_prior_evidence([call(command)], "ssh nas 'rm /remote/a'"))

    def test_mutations_malformed_and_transfers_never_evidence(self):
        for command in ("ssh nas 'cp /remote/a /remote/b'", "ssh nas 'rm /remote/a'", "ssh nas 'chmod 600 /remote/a'", "ssh nas 'cat /remote/a", "ssh nas", "scp -n /remote/a nas:/remote/b", "rsync --dry-run /remote/a nas:/remote/b", "ssh -o HostName=wrong nas 'stat /remote/a'", "ssh nas 'stat /remote/a > /remote/b'", "ssh nas 'find /remote/a -delete'", "ssh nas 'python3 -c \"print(1)\"'", "ssh nas 'source /evil; stat /remote/a'", "ssh nas 'sed -i s/a/b/ /remote/a'", "ssh nas 'awk system /remote/a'", "ssh nas 'cat /remote/a & rm /remote/b'", "source /evil; stat /remote/a", "ssh nas 'git remote add bad /remote/a'", "ssh nas 'sort -o/remote/b /remote/a'"):
            with self.subTest(command=command):
                self.assertFalse(policy.bash_is_read_only(command))
                self.assertFalse(policy.has_prior_evidence([call(command)], "ssh nas 'rm /remote/a'"))

    def test_evidence_target_and_host_binding(self):
        for evidence, expected in (("ssh nas 'stat /remote/a'", True), ("ssh nas 'ls /remote'", True), ("ssh nas 'ls /'", False), ("ssh nas 'stat /remote/ab'", False), ("ssh wrong 'stat /remote/a'", False), ("stat /remote/a", False), ("echo /remote/a", False), ("ssh nas 'echo /remote/a'", False), ("ssh nas 'grep /remote/a README.md'", False), ("ssh nas 'stat --printf /remote/a /other'", False), ("ssh nas 'stat --help /remote/a'", False)):
            with self.subTest(evidence=evidence):
                self.assertEqual(policy.has_prior_evidence([call(evidence)], "ssh nas 'rm /remote/a'"), expected)
        self.assertFalse(policy.has_prior_evidence([policy.ToolCall("Read", path="/README.md", succeeded=True)], "ssh nas 'rm /remote/a'"))

    def test_all_targets_need_evidence(self):
        command = "ssh nas 'cp /remote/a /other/b'"
        self.assertFalse(policy.has_prior_evidence([call("ssh nas 'stat /remote/a'")], command))
        self.assertTrue(policy.has_prior_evidence([call("ssh nas 'stat /remote/a /other/b'")], command))

    def test_failed_pending_and_empty_evidence(self):
        for calls in ([], [call("ssh nas 'stat /remote/a'", succeeded=False)]):
            self.assertFalse(policy.has_prior_evidence(calls, "ssh nas 'rm /remote/a'"))

    def test_window_exactly_twelve_prior_calls(self):
        command = "ssh nas 'rm /remote/a'"
        fillers = [call("echo filler", call_id=str(i)) for i in range(12)]
        evidence = call("ssh nas 'stat /remote/a'")
        current = call(command, succeeded=False, call_id="current")
        self.assertTrue(policy.has_prior_evidence([evidence] + fillers[:11], command))
        self.assertTrue(policy.has_prior_evidence([evidence] + fillers[:11] + [current], command, "current"))
        self.assertTrue(policy.has_prior_evidence([evidence] + fillers[:11] + [current], command))
        self.assertFalse(policy.has_prior_evidence([evidence] + fillers, command))
        # A completed retry is a prior call when the harness provides a new id.
        self.assertFalse(policy.has_prior_evidence([evidence] + fillers[:11] + [current], command, "new-id"))

    def test_local_writes_blocked(self):
        for command in (f"cp {PREFIX}/a {PREFIX}/b", f"mv {PREFIX}/a /tmp/b", f"rm {PREFIX}/a", f"mkdir {PREFIX}/a", f"touch {PREFIX}/a", f"chmod 600 {PREFIX}/a", f"chown root {PREFIX}/a", f"truncate -s 0 {PREFIX}/a", f"install /tmp/a {PREFIX}/a", f"tee {PREFIX}/a", f"sed -i '' s/a/b/ {PREFIX}/a", f"sed --in-place s/a/b/ {PREFIX}/a", f"echo x >{PREFIX}/a", f"printf x >> {PREFIX}/a", f"echo x | tee {PREFIX}/a", f"sudo cp /tmp/a {PREFIX}/a", f"/bin/rm {PREFIX}/a", f"cd {PREFIX} && rm a", f"bash -c 'rm {PREFIX}/a'", f"pz-remote write rm {PREFIX}/a", f"rm /protected/remote/../remote/path/a", f"cp '{PREFIX}/a b' /tmp/x"):
            with self.subTest(command=command):
                self.assertTrue(policy.execution_problems(command, GUARDS))
        self.assertTrue(policy.execution_problems("rm a", GUARDS, PREFIX))

    def test_text_and_read_operations_are_not_remote_writes(self):
        for command in (f'echo "{PREFIX}/a"', f'printf "%s\\n" "{PREFIX}/a"', f'grep "{PREFIX}/a" notes.md', f'cat {PREFIX}/a', f'echo "> {PREFIX}/a"', f'rm {PREFIX}-other/a', f"ssh nas 'cp {PREFIX}/a {PREFIX}/b'", f"ssh user@nas 'stat {PREFIX}/a'", f"ssh -p2222 -oConnectTimeout=12 nas 'stat {PREFIX}/a'"):
            with self.subTest(command=command):
                self.assertFalse(policy.execution_problems(command, GUARDS))

    def test_wrong_host_and_unparseable_transport_hard_deny(self):
        for command in (f"ssh wrong 'rm {PREFIX}/a'", f"ssh wrong 'cd {PREFIX}; rm a'", f"""ssh wrong 'bash -c "rm {PREFIX}/a" /other'""",  f"ssh -o HostName=wrong nas 'rm {PREFIX}/a'", f"ssh -F /tmp/config nas 'rm {PREFIX}/a'", "ssh nas 'rm /remote/a", 'ssh nas "rm \'/remote/a"', f"ssh nas 'stat /remote/a' > {PREFIX}/a", f"scp /tmp/a wrong:{PREFIX}/a", f"scp nas:{PREFIX}/a {PREFIX}/b", f"rsync -e evil /tmp/a nas:{PREFIX}/a", "ssh nas 'rm /remote/a $TARGET'", f"ssh nas 'ssh wrong rm {PREFIX}/a'"):
            with self.subTest(command=command):
                self.assertTrue(policy.execution_problems(command, GUARDS))

    def test_transport_routing_and_wrapper_are_not_evidence(self):
        self.assertFalse(policy.remote_needs_gate("rsync -a --delete --dry-run /tmp/src nas:/remote/a"))
        self.assertTrue(policy.remote_needs_gate("rsync -e evil --dry-run /tmp/src nas:/remote/a"))
        self.assertTrue(policy.remote_needs_gate("scp -n /tmp/src nas:/remote/a"))
        self.assertFalse(policy.bash_is_read_only("pz-remote read stat /remote/a"))
        self.assertFalse(policy.has_prior_evidence([call("cat /README.md")], "rm relative-target"))

    def test_background_separator_does_not_hide_a_protected_write(self):
        for verb in ("cp", "rm", "mv", "chmod"):
            command = f"echo harmless & {verb} {PREFIX}/a /tmp/b"
            self.assertTrue(policy.execution_problems(command, GUARDS))
        for command in ("echo text 2>&1", "echo text &>/tmp/log"):
            self.assertEqual(len(policy.split_segments(command)), 1)
        self.assertTrue(policy.execution_problems(f"echo text &>{PREFIX}/a", GUARDS))

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            for data in ({}, {"remote_path_guards": "oops"}, {"remote_path_guards": [{"host": "nas", "prefixes": ["relative"]}]}, {"remote_path_guards": [{"host": "nas", "prefixes": [PREFIX]}, {"host": "wrong", "prefixes": [PREFIX + "/a"]}]}):
                with self.subTest(data=data):
                    path.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):
                        policy.load_guards(str(path))
            path.write_text(json.dumps({"remote_path_guards": [{"host": "nas", "prefixes": [PREFIX + "/"]}]}))
            self.assertEqual(policy.load_guards(str(path)), GUARDS)


class AdapterSecurityTests(unittest.TestCase):
    def test_only_successful_results_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript"
            for rows, expected in ((entries(), True), (entries(success=False), False), (entries()[:1], False), ([], False)):
                path.write_text("\n".join(json.dumps(row) for row in rows))
                self.assertEqual(policy.has_prior_evidence(recent_tool_uses(str(path), 12), "ssh nas 'rm /remote/a'"), expected)
            path.write_text(json.dumps(entries()[0]) + "\ncorrupt\n" + json.dumps(entries()[1]))
            self.assertEqual(recent_tool_uses(str(path), 12), [])
            self.assertEqual(recent_tool_uses(directory, 12), [])
            self.assertEqual(recent_tool_uses(directory + "/missing", 12), [])

    def test_failure_metadata_cannot_be_successful_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript"
            for metadata in ({"exitCode": 1}, {"exit_code": 1}, {"interrupted": True}, {"is_error": True}):
                rows = entries()
                rows[1]["toolUseResult"] = metadata
                path.write_text("\n".join(json.dumps(row) for row in rows))
                self.assertFalse(policy.has_prior_evidence(recent_tool_uses(str(path), 12), "ssh nas 'rm /remote/a'"))

    def test_prose_and_hook_records_do_not_consume_window(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript"
            rows = entries() + [{"type": "assistant", "message": {"content": [{"type": "text", "text": "I checked it"}]}}, {"type": "progress", "data": {"hook": "helper"}}] * 50
            path.write_text("\n".join(json.dumps(row) for row in rows))
            calls = recent_tool_uses(str(path), 12)
            self.assertEqual(len(calls), 1)
            self.assertTrue(policy.has_prior_evidence(calls, "ssh nas 'rm /remote/a'"))

    def run_hook(self, command, rows=None, transcript_mode="normal", config="valid", extra_env=None):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            config_path = tmp / "policy.json"
            config_path.write_text(json.dumps({"remote_path_guards": [{"host": "nas", "prefixes": [PREFIX]}]}) if config == "valid" else "broken")
            path = tmp / "transcript.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in (rows or [])))
            payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": directory}
            if transcript_mode != "absent":
                payload["transcript_path"] = str(tmp if transcript_mode == "unreadable" else path)
            env = {"PATH": os.defpath + ":/opt/homebrew/bin:/usr/local/bin", "ACGM_POLICY_CONFIG": str(config_path)}
            env.update(extra_env or {})
            result = subprocess.run(["/bin/sh", str(REPO / "scripts/pretool-destructive-bash.sh")], input=json.dumps(payload), text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def denied(self, result, reason):
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn(reason, result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_remote_success_with_fields_through_real_hook(self):
        for verb in ("stat", "cat", "sha256sum"):
            with self.subTest(verb=verb):
                self.assertEqual(self.run_hook(FIELDS + "ssh nas 'rm /remote/a'", entries(f"ssh nas '{verb} /remote/a'")), {})
        self.assertEqual(self.run_hook(FIELDS + f"ssh nas 'cp {PREFIX}/a {PREFIX}/b'", entries(f"ssh nas 'ls {PREFIX}'")), {})

    def test_missing_unreadable_empty_and_failed_transcripts_deny(self):
        for mode in ("absent", "unreadable", "normal"):
            with self.subTest(mode=mode):
                self.denied(self.run_hook(FIELDS + "ssh nas 'rm /remote/a'", transcript_mode=mode), "EVIDENCE")
        self.denied(self.run_hook(FIELDS + "ssh nas 'rm /remote/a'", entries(success=False)), "EVIDENCE")
        self.denied(self.run_hook(FIELDS + "ssh nas 'rm /remote/a'", entries("ssh nas 'rm /remote/a'")), "EVIDENCE")

    def test_context_denial_cannot_be_waived_by_fields(self):
        for command, reason in ((f"echo harmless & cp {PREFIX}/a /tmp/b", "CONTEXT"), (f"cp {PREFIX}/a {PREFIX}/b", "CONTEXT"), (f"rm {PREFIX}/a", "CONTEXT"), (f"ssh wrong 'rm {PREFIX}/a'", "HOST"), ("ssh nas 'rm /remote/a", "REMOTE-PARSE")):
            with self.subTest(command=command):
                self.denied(self.run_hook(FIELDS + command, entries("ssh nas 'ls /remote'")), reason)

    def test_readonly_text_and_non_destructive_ignore_missing_transcript(self):
        for command in (f'echo "{PREFIX}/a"', f'grep "{PREFIX}/a" notes.md', f'printf "%s\\n" "{PREFIX}/a"', "ssh nas 'stat /remote/a'", "git status --short", "cp /tmp/a /tmp/b"):
            with self.subTest(command=command):
                self.assertEqual(self.run_hook(command, transcript_mode="absent"), {})

    def test_invalid_config_and_missing_dependencies_fail_closed(self):
        self.denied(self.run_hook("rm /remote/a", config="invalid"), "configuration")
        self.denied(self.run_hook("rm /remote/a", extra_env={"PATH": "/nonexistent-acgm-fixture"}), "ACGM")


if __name__ == "__main__":
    unittest.main()
