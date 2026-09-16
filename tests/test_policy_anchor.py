"""Stable policy discovery using synthetic local projects only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from test_security import REPO, policy
from acgm_gate import configured_guards

class PolicyAnchorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project'
        (self.root/'maint/tools/deep').mkdir(parents=True)
        self.config=self.root/'.governance/remote-path-guards.json'
        self.config.parent.mkdir()
        self.config.write_text(json.dumps({'remote_path_guards':[{'host':'nas','prefixes':['/protected/remote/path']}]}))
        self.env={'PATH':os.defpath+':/opt/homebrew/bin','CLAUDE_PROJECT_DIR':str(self.root),
                  'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull}

    def guards(self,cwd,**env):
        with patch.dict(os.environ,{**self.env,**env},clear=True):
            return configured_guards({'cwd':str(cwd)})

    def hook(self,cwd,command,**env):
        result=subprocess.run(['sh',str(REPO/'scripts/pretool-destructive-bash.sh')],
            input=json.dumps({'tool_name':'Bash','tool_input':{'command':command},'cwd':str(cwd)}),
            env={**self.env,**env},text=True,capture_output=True,check=True)
        return json.loads(result.stdout)

    def test_root_nested_deep_and_changed_cwd_same_guard(self):
        for cwd in (self.root,self.root/'maint/tools',self.root/'maint/tools/deep',Path('/tmp')):
            with self.subTest(cwd=cwd):
                self.assertEqual(self.guards(cwd),[('nas','/protected/remote/path')])
                result=self.hook(cwd,'cp /protected/remote/path/a /protected/remote/path/b')
                self.assertIn('CONTEXT',result['hookSpecificOutput']['permissionDecisionReason'])
                self.assertEqual(self.hook(cwd,"ssh nas 'stat /protected/remote/path/a'"),{})

    def test_git_start_in_subdir_resolves_root(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.assertEqual(self.guards('/tmp',CLAUDE_PROJECT_DIR=str(self.root/'maint/tools/deep')),
                         [('nas','/protected/remote/path')])

    def test_git_worktree_marker_resolves_worktree_not_primary(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=f@example.invalid',
                        '-c','core.hooksPath=/dev/null','commit','--allow-empty','-qm','fixture'],check=True)
        worktree=Path(self.tmp.name)/'worktree'
        subprocess.run(['git','-C',str(self.root),'worktree','add','-q','--detach',str(worktree)],check=True)
        (worktree/'.governance').mkdir();(worktree/'.governance/remote-path-guards.json').write_bytes(self.config.read_bytes())
        (worktree/'nested').mkdir()
        self.assertEqual(self.guards('/tmp',CLAUDE_PROJECT_DIR=str(worktree/'nested')),[('nas','/protected/remote/path')])

    def test_explicit_absolute_wins_and_bad_explicit_fails(self):
        self.assertEqual(self.guards('/tmp',CLAUDE_PROJECT_DIR='/missing',ACGM_POLICY_CONFIG=str(self.config)),[('nas','/protected/remote/path')])
        for name in ('relative.json',str(self.root/'missing.json')):
            with self.assertRaises((ValueError,OSError)):
                self.guards('/tmp',ACGM_POLICY_CONFIG=name)
        self.config.write_text('{broken')
        self.assertEqual(self.hook('/tmp','cat /tmp/a',ACGM_POLICY_CONFIG=str(self.config))['hookSpecificOutput']['permissionDecision'],'deny')

    def test_absent_guard_is_optional_but_malformed_unreadable_is_not(self):
        self.config.unlink()
        self.assertEqual(self.guards(self.root),[])
        self.config.write_text('{broken')
        with self.assertRaises(ValueError):self.guards(self.root)
        with patch('acgm_gate.load_guards',side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError):self.guards(self.root)
        self.config.unlink();self.config.parent.rmdir()
        self.assertEqual(self.guards(self.root),[])

    def test_unknown_anchor_and_governance_symlinks_fail_closed(self):
        for anchor in ('','relative','/nonexistent-fixture'):
            with self.assertRaises(ValueError):self.guards(self.root,CLAUDE_PROJECT_DIR=anchor)
        self.config.unlink();self.config.symlink_to('/nonexistent-fixture')
        with self.assertRaises(ValueError):self.guards(self.root)
        self.config.unlink();self.config.parent.rmdir();self.config.parent.symlink_to('/nonexistent-fixture')
        with self.assertRaises(ValueError):self.guards(self.root)

    def test_no_cross_project_or_nested_override(self):
        nested=self.root/'maint/tools/.governance';nested.mkdir()
        (nested/'remote-path-guards.json').write_text('{invalid shadow policy')
        self.assertEqual(self.guards(nested.parent),[('nas','/protected/remote/path')])
        other=Path(self.tmp.name)/'other';other.mkdir()
        self.assertEqual(self.guards(self.root,CLAUDE_PROJECT_DIR=str(other)),[])
        # No Git and starting in a subdirectory defines its own project boundary.
        empty=self.root/'maint/tools/deep'
        self.assertEqual(self.guards(empty,CLAUDE_PROJECT_DIR=str(empty)),[])

    def test_invalid_git_boundary_does_not_fall_back_to_empty(self):
        for result in (subprocess.CompletedProcess([], 1, "", "broken repository"),
                       subprocess.CompletedProcess([], 0, "/unrelated/root\n", "")):
            with patch('acgm_gate.subprocess.run',return_value=result):
                with self.assertRaises(ValueError):self.guards(self.root)
