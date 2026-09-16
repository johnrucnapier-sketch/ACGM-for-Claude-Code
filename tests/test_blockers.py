"""Blocker regressions: classifiers only; no destructive payload executes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import acgm_policy as p
from acgm_gate import unresolved_obligations, recent_tool_uses

SAFE = ['date', 'date -u', "date '+%F'", 'uniq /remote/a', 'nvcc --version',
        'hostname', 'git status --short', 'claude plugin list', 'stat /remote/a']
UNSAFE = ['uniq $ARGS', 'uniq /remote/*', 'date +$FORMAT', 'date -s 2030-01-01', 'date 010100002030', 'uniq /remote/a /remote/b',
          'nvcc /remote/a.cu -o /remote/b', 'hostname changed', 'hostname -F /remote/a',
          'find /remote/a -fprint /remote/b', "sed -e p -e 'w /remote/b' /remote/a",
          'sort --output=/remote/b /remote/a', 'file -C -m /remote/a',
          'rg --pre /remote/program pattern /remote/a', 'ip link set eth0 down',
          'ss -K dst 127.0.0.1', 'lsof -D b/remote/a', 'git hash-object -w /remote/a',
          'git diff --ext-diff /remote/a', 'git log --output=/remote/a',
          'nvidia-smi -f /remote/a', "tmux list-panes -F '#(touch /remote/a)'",
          'kubectl get pods --raw=/remote/a', 'npm view x --logfile=/remote/a',
          'jq --run-tests /remote/a', 'python3 -c pass', 'awk system /remote/a']

def rows(cmd, ident, metadata=None, result=True):
    out = [{'type':'assistant','message':{'content':[{'type':'tool_use','id':ident,
           'name':'Bash','input':{'command':cmd}}]}}]
    if result:
        out.append({'type':'user','toolUseResult':metadata or {},'message':{'content':[
            {'type':'tool_result','tool_use_id':ident,'is_error':False,'content':'fixture'}]}})
    return out

MUT = "# ACGM-VERIFY-AFTER: inspect /remote/a after mutation\nssh nas 'chmod 600 /remote/a'"
READ = "ssh nas 'stat /remote/a'"

class BlockerTests(unittest.TestCase):
    def unresolved(self, entries):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'transcript.jsonl'
            path.write_text(''.join(json.dumps(e)+'\n' for e in entries))
            return unresolved_obligations(str(path))

    def test_argument_sensitive_forms(self):
        for cmd in SAFE:
            with self.subTest(cmd=cmd): self.assertTrue(p.bash_is_read_only(cmd))
        for cmd in UNSAFE:
            with self.subTest(cmd=cmd):
                self.assertFalse(p.bash_is_read_only(cmd))
                self.assertFalse(p.has_prior_evidence([p.ToolCall('Bash',cmd,succeeded=True)], "rm /remote/a"))
                self.assertTrue(p.remote_needs_gate('ssh nas '+__import__('shlex').quote(cmd)))

    def test_post_verification_success(self):
        self.assertFalse(self.unresolved(rows(MUT,'m')+rows(READ,'r')))

    def test_failure_metadata_never_verifies(self):
        for meta in ({'exitCode':2},{'exit_code':1},{'interrupted':True},{'is_error':True}):
            with self.subTest(meta=meta):
                self.assertTrue(self.unresolved(rows(MUT,'m')+rows(READ,'r',meta)))

    def test_pending_prose_wrong_target_host_parent_and_before_fail(self):
        cases=[rows(MUT,'m')+rows(READ,'r',result=False),
               rows(MUT,'m')+[{'type':'assistant','message':{'content':[{'type':'text','text':'I verified /remote/a successfully'}]}}],
               rows(MUT,'m')+rows("ssh nas 'stat /remote/b'",'r'),
               rows(MUT,'m')+rows("ssh other 'stat /remote/a'",'r'),
               rows(MUT,'m')+rows("ssh nas 'ls /remote'",'r'),
               rows(READ,'r')+rows(MUT,'m'),
               rows(MUT,'m',result=False)+rows(READ,'r'),
               rows(MUT.replace('inspect /remote/a','inspect /remote/b'),'m')+rows(READ,'r')]
        for case in cases:
            with self.subTest(case=case): self.assertTrue(self.unresolved(case))

    def test_result_order_and_duplicate_fail_closed(self):
        m=rows(MUT,'m'); r=rows(READ,'r')
        self.assertTrue(self.unresolved([m[0],r[0],m[1],r[1]]))
        self.assertTrue(self.unresolved(m+r+[r[1]]))

    def test_each_mutation_requires_later_check(self):
        self.assertTrue(self.unresolved(rows(MUT,'m')+rows(READ,'r')+rows(MUT,'m2')))
        self.assertFalse(self.unresolved(rows(MUT,'m')+rows(READ,'r')+rows(MUT,'m2')+rows(READ,'r2')))

    def test_shell_segmentation_regressions(self):
        for sep in (' & ', ' ; ', ' && ', ' | '):
            self.assertTrue(p.execution_problems('echo harmless'+sep+'cp /protected/a /tmp/b', [('nas','/protected')]))
        for cmd in ('(rm /protected/a)', 'echo $(rm /protected/a)', "sh -c 'rm /protected/a'"):
            self.assertFalse(p.bash_is_read_only(cmd))
            self.assertTrue(p.execution_problems(cmd,[('nas','/protected')]))
