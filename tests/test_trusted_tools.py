"""Exact remote tool qualification. Synthetic fixtures never execute payloads."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_security import policy, REPO, entries
from acgm_gate import recent_tool_uses

TOOL = '/opt/reviewed/health.sh'
DIGEST = 'a' * 64
ENTRY = {'host': 'fixture', 'path': TOOL, 'sha256': DIGEST, 'allowed_argv': [[], ['--json']]}
HASH = f"ssh fixture 'sha256sum {TOOL}'"
RUN = f"ssh fixture '{TOOL}'"


def evidence(command=HASH, text=None, success=True, **kw):
    return policy.ToolCall('Bash', command, call_id='hash', succeeded=success,
                           started=1, finished=2, result_text=text if text is not None else DIGEST+'  '+TOOL+'\n', **kw)


def rows(command=HASH, text=None, success=True):
    data = entries(command, success)
    data[1]['message']['content'][0]['content'] = text if text is not None else DIGEST+'  '+TOOL+'\n'
    return data


class TrustedToolsTests(unittest.TestCase):
    def qualifies(self, command=RUN, calls=None, entry=None, current_id=''):
        return policy.trusted_remote_readonly(command, [entry or ENTRY], calls if calls is not None else [evidence()], current_id)

    def test_exact_empty_and_json_argv(self):
        self.assertTrue(self.qualifies())
        self.assertTrue(self.qualifies(f"ssh fixture '{TOOL} --json'"))

    def test_missing_mismatched_failed_interrupted_result(self):
        for calls in ([], [evidence(text='b'*64+'  '+TOOL+'\n')], [evidence(success=False)],
                      [evidence(text='')], [evidence(text=DIGEST+'  /other/health.sh\n')]):
            with self.subTest(calls=calls): self.assertFalse(self.qualifies(calls=calls))

    def test_latest_exact_measurement_invalidates_older_good_hash(self):
        for newer in (evidence(success=False), evidence(text='b'*64+'  '+TOOL+'\n')):
            self.assertFalse(self.qualifies(calls=[evidence(), newer]))

    def test_wrong_host_local_hash_prose_and_fake_hash_commands(self):
        for command in (f'sha256sum {TOOL}', f"ssh other 'sha256sum {TOOL}'", f"ssh fixture 'echo {DIGEST}  {TOOL}'",
                        f"ssh fixture 'sha256sum {TOOL}; echo x'", f"ssh fixture 'env sha256sum {TOOL}'",
                        f"ssh fixture 'sha256sum /alias/health.sh'", f"ssh fixture 'sha256sum {TOOL} /other'",
                        f"ssh user@fixture 'sha256sum {TOOL}'", f"ssh -p22 fixture 'sha256sum {TOOL}'"):
            with self.subTest(command=command): self.assertFalse(self.qualifies(calls=[evidence(command=command)]))

    def test_output_must_be_exact_single_sha256sum_record(self):
        for text in (f'I checked {DIGEST}  {TOOL}', DIGEST+'  '+TOOL+'\nextra\n', DIGEST+' *'+TOOL,
                     DIGEST.upper()+'  '+TOOL, DIGEST+'  '+TOOL+'\n\n', ' '+DIGEST+'  '+TOOL,
                     '\x1b[0m'+DIGEST+'  '+TOOL):
            with self.subTest(text=text): self.assertFalse(self.qualifies(calls=[evidence(text=text)]))

    def test_window_excludes_current_before_twelve(self):
        fillers = [policy.ToolCall('Bash', 'echo filler', call_id=str(i)) for i in range(12)]
        current = policy.ToolCall('Bash', RUN, call_id='now', started=50)
        self.assertTrue(self.qualifies(calls=[evidence()]+fillers[:11]+[current],current_id='now'))
        self.assertFalse(self.qualifies(calls=[evidence()]+fillers+[current],current_id='now'))
        self.assertFalse(self.qualifies(calls=[evidence()]+fillers))

    def test_result_must_finish_before_current_starts(self):
        current = policy.ToolCall('Bash', RUN, call_id='now', started=2)
        self.assertFalse(self.qualifies(calls=[evidence(),current], current_id='now'))
        self.assertFalse(self.qualifies(calls=[evidence(),current]))
        self.assertFalse(self.qualifies(calls=[policy.ToolCall('Bash',HASH,succeeded=True,result_text=DIGEST+'  '+TOOL)]))

    def test_identity_no_normalization_or_symlink_alias_inheritance(self):
        for command in (f"ssh other '{TOOL}'", "ssh fixture 'health.sh'", "ssh fixture '/alias/health.sh'",
                        "ssh fixture '/different/health.sh'", "ssh fixture '/opt/reviewed/../reviewed/health.sh'",
                        "ssh fixture '//opt/reviewed/health.sh'", f"ssh user@fixture '{TOOL}'"):
            with self.subTest(command=command): self.assertFalse(self.qualifies(command))

    def test_exact_argument_vectors_not_sets(self):
        for args in ('--unknown', '--json extra', '--json --json', '--json=true'):
            self.assertFalse(self.qualifies(f"ssh fixture '{TOOL} {args}'"))
        entry = {**ENTRY,'allowed_argv':[['--one','--two']]}
        self.assertTrue(self.qualifies(f"ssh fixture '{TOOL} --one --two'",entry=entry))
        self.assertFalse(self.qualifies(f"ssh fixture '{TOOL} --two --one'",entry=entry))

    def test_shell_operators_wrappers_environment_and_ssh_options(self):
        payloads = [TOOL+'; rm x', TOOL+' && true', TOOL+' | cat', TOOL+' $(id)', TOOL+' `id`',
                    TOOL+' > file', TOOL+' >> file', TOOL+' < file', 'VAR=x '+TOOL, 'env '+TOOL,
                    'sh '+TOOL, 'bash '+TOOL, 'sudo '+TOOL, TOOL+'\ntrue', TOOL+' # comment',
                    TOOL+' &', TOOL+' || true', TOOL+' --j*', TOOL+' "--json"']
        commands = [f"ssh fixture '{p}'" for p in payloads]
        commands += [f"VAR=x ssh fixture '{TOOL}'", f"env ssh fixture '{TOOL}'", f"ssh -i key fixture '{TOOL}'",
                     f"ssh fixture '{TOOL}' > file", f"ssh fixture '{TOOL}' && true", f'ssh fixture "{TOOL}"',
                     f"ssh fixture '{TOOL}", f"ssh fixture '{TOOL}'\n", f"# fields\nssh fixture '{TOOL}'"]
        for command in commands:
            with self.subTest(command=command): self.assertFalse(self.qualifies(command))

    def test_no_invented_target_evidence(self):
        self.assertFalse(policy.bash_is_read_only(RUN))
        self.assertEqual(policy.evidence_targets(RUN),set())
        self.assertFalse(policy.has_prior_evidence([policy.ToolCall('Bash',RUN,succeeded=True)],"ssh fixture 'rm /data/a'"))


class TrustedConfigTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'policy.json';p.write_text(json.dumps(data))
            return policy.load_policy(str(p))

    def test_existing_schema_and_optional_registry(self):
        self.assertEqual(self.load({'remote_path_guards':[]}),([],[]))
        self.assertEqual(self.load({'remote_path_guards':[],'remote_readonly_tools':[ENTRY]}),([],[ENTRY]))

    def test_bad_registry_fail_closed(self):
        bad = [None,{},'bad',[None],[{}],[ENTRY,ENTRY],[ENTRY,{**ENTRY,'sha256':'b'*64}]]
        mutations = {'host':['*','other@fixture','-o',''], 'path':['relative','/','//a','/x/../a','/x/*','/x/','/opt/reviewed/cat'],
                     'sha256':['a'*63,'g'*64,'A'*64,None], 'allowed_argv':[None,[],['--json'],[[],[]],[['*']],[['$(id)']],[['a b']]]}
        for key,values in mutations.items():
            for value in values: bad.append([{**ENTRY,key:value}])
        bad += [{**ENTRY,'extra':True}]
        for tools in bad:
            with self.subTest(tools=tools):
                with self.assertRaises(ValueError): self.load({'remote_path_guards':[],'remote_readonly_tools':tools})

    def test_duplicate_json_keys_and_guard_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'
            for raw in ('{"remote_path_guards":[],"remote_path_guards":[]}',
                        '{"remote_path_guards":[],"remote_readonly_tools":[],"remote_readonly_tools":[]}'):
                p.write_text(raw)
                with self.assertRaises(ValueError):policy.load_policy(str(p))
        with self.assertRaises(ValueError):
            self.load({'remote_path_guards':[{'host':'other','prefixes':['/opt/reviewed']}],
                       'remote_readonly_tools':[ENTRY]})


class TrustedHookTests(unittest.TestCase):
    def hook(self, command=RUN, records=None, guards=None, tools=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=root/'policy.json';transcript=root/'session.jsonl'
            config.write_text(json.dumps({'remote_path_guards': guards or [], 'remote_readonly_tools':tools if tools is not None else [ENTRY]}))
            transcript.write_text('\n'.join(json.dumps(r) for r in (records if records is not None else rows())))
            p={'tool_name':'Bash','tool_input':{'command':command},'transcript_path':str(transcript),'cwd':d,'tool_use_id':'current'}
            result=subprocess.run(['sh',str(REPO/'scripts/pretool-destructive-bash.sh')],input=json.dumps(p),text=True,capture_output=True,
                                  env={'PATH':os.defpath+':/opt/homebrew/bin','ACGM_POLICY_CONFIG':str(config)},check=True)
            return json.loads(result.stdout)

    def deny(self, result):
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')

    def test_real_hook_exact_pass_and_json(self):
        self.assertEqual(self.hook(),{})
        self.assertEqual(self.hook(f"ssh fixture '{TOOL} --json'"),{})

    def test_real_hook_failed_interrupted_missing_and_hash_mismatch(self):
        cases=[[],rows(success=False), rows(text='b'*64+'  '+TOOL+'\n')]
        for metadata in ({'interrupted':True},{'exitCode':1},{'exit_code':1},{'is_error':True}):
            records=rows();records[1]['toolUseResult']=metadata;cases.append(records)
        for records in cases:
            with self.subTest(records=records):self.deny(self.hook(records=records))

    def test_real_result_blocks_not_assistant_claims(self):
        records=rows();records[1]['message']['content'][0]['content']=[{'type':'text','text':DIGEST+'  '+TOOL+'\n'}]
        self.assertEqual(self.hook(records=records),{})
        records=rows(text='');records.append({'type':'assistant','message':{'content':[{'type':'text','text':DIGEST+'  '+TOOL+'\n'}]}})
        self.deny(self.hook(records=records))

    def test_real_hook_untrusted_variants_and_no_registration(self):
        for command in (f"ssh fixture '{TOOL} --unknown'", f"ssh fixture '{TOOL}; rm x'",f"ssh other '{TOOL}'"):
            self.deny(self.hook(command))
        self.deny(self.hook(tools=[]))

    def test_registered_tool_does_not_bypass_other_context_policy(self):
        args_entry={**ENTRY,'allowed_argv':[['/protected/a']]}
        self.deny(self.hook(f"ssh fixture '{TOOL} /protected/a'",tools=[args_entry],guards=[{'host':'other','prefixes':['/protected']}]))

    def test_adapter_ordering_and_duplicate_results(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'session.jsonl'
            records=rows();p.write_text('\n'.join(map(json.dumps,records)))
            calls=recent_tool_uses(str(p),12)
            self.assertEqual(calls[0].result_text,DIGEST+'  '+TOOL+'\n')
            self.assertTrue(policy.trusted_remote_readonly(RUN,[ENTRY],calls))
            for invalid in (records+[records[1]],list(reversed(records))):
                p.write_text('\n'.join(map(json.dumps,invalid)))
                self.assertFalse(policy.trusted_remote_readonly(RUN,[ENTRY],recent_tool_uses(str(p),12)))
