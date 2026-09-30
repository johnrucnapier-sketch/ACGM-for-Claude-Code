"""Workflow regressions: inspect real Hooks, never execute reviewed commands."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_security import REPO
from test_trusted_tools import ENTRY, RUN, HASH, DIGEST, TOOL, rows
from acgm_gate import project_anchor
from acgm_status import project_state


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root/'project'
        self.project.mkdir()
        self.config = self.project/'.governance/remote-path-guards.json'
        self.config.parent.mkdir()
        self.config.write_text(json.dumps({'remote_path_guards': [], 'remote_readonly_tools': [ENTRY]}))
        self.transcript = self.root/'session.jsonl'
        self.env = {'PATH': os.defpath+':/opt/homebrew/bin:/usr/local/bin',
                    'PYTHONDONTWRITEBYTECODE': '1', 'CLAUDE_PROJECT_DIR': str(self.project),
                    'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

    def inspect(self, command, records=None, **payload_fields):
        self.transcript.write_text('\n'.join(map(json.dumps, records or [])))
        payload = {'tool_name': 'Bash', 'tool_input': {'command': command},
                   'cwd': str(self.project), 'transcript_path': str(self.transcript), **payload_fields}
        hook = subprocess.run(['sh', str(REPO/'scripts/pretool-destructive-bash.sh')],
                              input=json.dumps(payload), text=True, capture_output=True, env=self.env, check=True)
        explained = subprocess.run([sys.executable, str(REPO/'scripts/acgm-explain.py')],
                                   input=json.dumps(payload), text=True, capture_output=True, env=self.env)
        actual = json.loads(hook.stdout)
        report = json.loads(explained.stdout)
        self.assertEqual(report['verdict'], 'deny' if actual else 'pass_through')
        self.assertEqual(explained.returncode, 2 if actual else 0)
        self.assertFalse(report['authorized'])
        self.assertFalse(report['executed'])
        if actual:
            reason = actual['hookSpecificOutput']['permissionDecisionReason']
            self.assertEqual(report['issues'], json.loads(reason.split('\nACGM-DIAGNOSTIC: ')[1])['issues'])
        return report

    def test_real_hook_and_inspector_agree_without_execution(self):
        sentinel = self.root/'must-survive'
        sentinel.write_text('retained')
        for command in ('hostname', "ssh fixture 'hostname; nvidia-smi'",
                        "ssh fixture 'sudo hostname'", 'rm '+str(sentinel),
                        'touch '+str(self.root/'must-not-exist'),
                        "ssh fixture 'systemctl restart example.service'",
                        "ssh fixture 'nvidia-smi -pl 200'",
                        "ssh -o HostName=other fixture 'stat /tmp/x'",
                        "ssh fixture 'echo $(touch /tmp/should-not-run)'",
                        "scp ./a fixture:/tmp/b", "ssh fixture 'cat /tmp/x' > /tmp/output"):
            with self.subTest(command=command):
                self.inspect(command)
        self.assertEqual(sentinel.read_text(), 'retained')
        self.assertFalse((self.root/'must-not-exist').exists())

    def test_unsupported_resource_does_not_instruct_field_retry(self):
        r = self.inspect("ssh fixture 'systemctl restart example.service'")
        self.assertIn('EVIDENCE_TARGET_UNSUPPORTED', [i['code'] for i in r['issues']])
        self.assertTrue(all(not i['retryable'] for i in r['issues']))
        self.assertNotIn('Add the listed fields', json.dumps(r))

    def test_trusted_missing_hash_has_exact_action_and_no_field_noise(self):
        r = self.inspect(RUN)
        i = r['issues'][0]
        self.assertEqual(i['code'], 'TRUSTED_EVIDENCE_MISSING')
        self.assertEqual(i['expected_evidence_command'], HASH)
        self.assertEqual(i['canonical_invocation'], RUN)
        self.assertNotIn('FIELDS', [i['code'] for i in r['issues']])
        self.assertEqual(self.inspect(RUN, rows())['verdict'], 'pass_through')

    def test_hash_mismatch_and_failure_are_not_format_repairs(self):
        for records, code in [(rows(text='b'*64+'  '+TOOL+'\n'), 'TRUSTED_HASH_OR_OUTPUT_MISMATCH'),
                              (rows(success=False), 'TRUSTED_EVIDENCE_FAILED_OR_PENDING')]:
            r = self.inspect(RUN, rows()+[{**records[0], 'message': {'content': [
                {**records[0]['message']['content'][0], 'id': 'new'}]}}]+[
                    {**records[1], 'message': {'content': [
                        {**records[1]['message']['content'][0], 'tool_use_id': 'new'}]}}])
            self.assertEqual(r['issues'][0]['code'], code)
            self.assertFalse(r['issues'][0]['retryable'])

    def test_unknown_argv_wrong_host_and_wrappers_do_not_inherit_trust(self):
        for c in (RUN.replace('fixture', 'wrong'), RUN.replace(TOOL, 'env '+TOOL),
                  RUN.replace(TOOL, TOOL+' --unknown')):
            r = self.inspect(c, rows())
            self.assertEqual(r['verdict'], 'deny')
        r = self.inspect(RUN.replace('fixture', 'wrong'), rows())
        self.assertNotIn('canonical_invocation', json.dumps(r))

    def test_diagnostics_never_drop_ssh_identity_options(self):
        for command in (RUN.replace('ssh fixture','ssh user@fixture'),
                        RUN.replace('ssh fixture','ssh -i /keys/test fixture'),
                        RUN.replace('ssh fixture','ssh -p 2222 fixture')):
            report = self.inspect(command)
            self.assertEqual(report['verdict'],'deny')
            self.assertNotIn('canonical_invocation',json.dumps(report))

    def test_protected_path_denial_precedes_trust(self):
        self.config.write_text(json.dumps({'remote_path_guards': [{'host':'other','prefixes':['/protected']}],
            'remote_readonly_tools': [{**ENTRY, 'allowed_argv': [['/protected/a']]}]}))
        r = self.inspect(RUN.replace(TOOL, TOOL+' /protected/a'), rows())
        self.assertEqual(r['issues'][0]['code'], 'HOST')

    def test_malformed_transcript_is_visible_not_evidence(self):
        # A duplicate ID makes the entire transcript invalid.
        r = self.inspect('rm /tmp/a', rows()+rows())
        self.assertIn('EVIDENCE_TRANSCRIPT_INVALID', [i['code'] for i in r['issues']])

    def test_invalid_policy_remains_hard_denial(self):
        self.config.write_text('{broken')
        r = self.inspect('hostname')
        self.assertEqual(r['issues'][0]['code'], 'POLICY_OR_RUNTIME_INVALID')

    def test_startup_distinguishes_policy_only_rules_and_empty_project(self):
        with patch.dict(os.environ, self.env, clear=True):
            state = project_state()
            self.assertEqual(state['root_rules'], [])
            self.assertEqual(state['runtime_policy'], 'present_valid')
            self.assertEqual(state['trusted_tools'], 1)
            (self.project/'CLAUDE.md').write_text('fixture rules')
            self.assertEqual(project_state()['root_rules'], ['CLAUDE.md'])
            self.config.unlink()
            self.assertEqual(project_state()['runtime_policy'], 'absent')
            self.config.write_text('{broken')
            self.assertEqual(project_state()['runtime_policy'], 'invalid_or_unavailable')

    def test_startup_uses_startup_anchor_not_process_cwd(self):
        result = subprocess.run(['sh',str(REPO/'scripts/grounding-inject.sh')],
            input=json.dumps({'cwd':str(self.root)}),text=True,capture_output=True,env=self.env,cwd=self.root,check=True)
        msg = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        self.assertIn('present_valid',msg)
        self.assertIn('"trusted_tools": 1',msg)
        self.assertNotIn('WAIT',msg)
        self.assertNotIn('governance is active',msg)
        self.assertIn("existing authorization",msg)
        self.assertFalse((self.root/'.governance').exists())

    def test_explicit_policy_does_not_hide_missing_anchor(self):
        with patch.dict(os.environ,{**self.env,'CLAUDE_PROJECT_DIR':'/missing-fixture',
                                   'ACGM_POLICY_CONFIG':str(self.config)},clear=True):
            state=project_state()
            self.assertEqual(state['anchor_status'],'invalid_or_unavailable')
            self.assertEqual(state['runtime_policy'],'present_valid')
            self.assertIsNone(state['root'])

    def test_doctor_and_startup_share_nested_git_root(self):
        subprocess.run(['git','init','-q',str(self.project)],check=True)
        sub = self.project/'nested';sub.mkdir()
        with patch.dict(os.environ,{**self.env,'CLAUDE_PROJECT_DIR':str(sub)},clear=True):
            self.assertEqual(project_anchor(),str(self.project.resolve()))
            self.assertEqual(project_state()['runtime_policy'],'present_valid')
        result = subprocess.run([sys.executable,str(REPO/'scripts/acgm_status.py'),'--project',str(sub)],
            text=True,capture_output=True,env=self.env,check=True)
        self.assertEqual(json.loads(result.stdout)['root'],str(self.project.resolve()))

    def test_inspector_rejects_bad_input_and_missing_anchor(self):
        for payload in ({}, {'tool_name':'Write','tool_input':{'command':'hostname'}},
                        {'tool_input':{'command':12}}):
            result = subprocess.run([sys.executable,str(REPO/'scripts/acgm-explain.py')],
                input=json.dumps(payload),text=True,capture_output=True,env=self.env)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stdout)['verdict'],'error')
        self.env.pop('CLAUDE_PROJECT_DIR')
        self.assertEqual(self.inspect('hostname')['verdict'],'deny')
