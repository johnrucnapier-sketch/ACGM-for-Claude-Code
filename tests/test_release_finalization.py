"""Non-policy release regressions; doctor runs only on synthetic trees."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_activity import activity, tool_use, denied, asked
from test_security import REPO

class ActivityFinalTests(unittest.TestCase):
    def test_destructive_context_allowed_and_held(self):
        context=denied('c')
        context['message']['content'][0]['content']='ACGM gate — CONTEXT — This path belongs to remote host "nas".'
        allowed={'attachment':{'hookEvent':'PreToolUse','command':activity.GATE_HOOK,
                              'toolUseID':'a','stdout':'{}'}}
        entries=[tool_use('d','rm -rf /tmp/a'),denied('d'),tool_use('c','cp /protected/a /tmp/b'),context,
                 tool_use('a','cat /tmp/a'),allowed,tool_use('h','rm -rf /tmp/h'),asked('h')]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'t.jsonl';p.write_text('\n'.join(json.dumps(e) for e in entries))
            s=activity.read_session(str(p))
        self.assertEqual(s['events'],{'gate_blocked':2,'gate_allowed':1,'gate_asked':1})

    def test_context_attachment_is_blocked(self):
        entries=[tool_use('c','cp /protected/a /tmp/b'),{'attachment':{
            'hookEvent':'PreToolUse','command':activity.GATE_HOOK,'toolUseID':'c',
            'stdout':json.dumps({'hookSpecificOutput':{'permissionDecision':'deny',
                'permissionDecisionReason':'ACGM gate — CONTEXT — protected path'}})}}]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'t.jsonl';p.write_text('\n'.join(json.dumps(e) for e in entries))
            self.assertEqual(activity.read_session(str(p))['events'],{'gate_blocked':1})

class DoctorFinalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source';self.cache=self.root/'cache'
        shutil.copytree(REPO,self.source,ignore=shutil.ignore_patterns('.git','__pycache__'))
        shutil.copytree(self.source,self.cache)
        plugins=self.root/'.claude/plugins';plugins.mkdir(parents=True)
        (plugins/'installed_plugins.json').write_text(json.dumps({'plugins':{'acgm@acgm':[{'installPath':str(self.cache)}]}}))
        (plugins/'known_marketplaces.json').write_text(json.dumps({'acgm':{'source':{'source':'directory','path':str(self.source)}}}))
        bin=self.root/'bin';bin.mkdir();cli=bin/'claude';cli.write_text('#!/bin/sh\nprintf "acgm@acgm\\nStatus: enabled\\n"\n');cli.chmod(0o755)
        self.env={'HOME':str(self.root),'PATH':str(bin)+':/opt/homebrew/bin:'+os.defpath}

    def doctor(self):
        return subprocess.run(['sh',str(REPO/'scripts/acgm-doctor.sh'),'--plugin-dir',str(self.cache)],
                              env=self.env,text=True,capture_output=True)

    def test_only_pycache_differences_pass(self):
        p=self.cache/'scripts/__pycache__';p.mkdir(exist_ok=True);(p/'a.pyc').write_bytes(b'cache')
        (self.cache/'standalone.pyc').write_bytes(b'compiled')
        self.assertEqual(self.doctor().returncode,0)

    def test_only_in_use_file_or_directory_pass(self):
        p=self.cache/'.in_use';p.write_text('runtime lock')
        self.assertEqual(self.doctor().returncode,0)
        p.unlink();p.mkdir();(p/'runtime').write_text('lock')
        self.assertEqual(self.doctor().returncode,0)

    def test_real_source_hook_and_config_differences_fail(self):
        for name in ('scripts/acgm_policy.py','scripts/pretool-destructive-bash.sh','hooks/hooks.json'):
            with self.subTest(name=name):
                p=self.cache/name;original=p.read_bytes();p.write_bytes(original+b'\n')
                result=self.doctor();self.assertEqual(result.returncode,1)
                self.assertIn('file(s) differ',result.stdout);p.write_bytes(original)
