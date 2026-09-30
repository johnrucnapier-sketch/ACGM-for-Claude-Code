#!/usr/bin/env python3
"""Opt-in native Claude CLI acceptance; loopback mock API and fake SSH only.

Run: python3 tests/harness_trusted_tools.py /absolute/new/lab-directory [--installed]
--installed uses ordinary user plugin discovery, never --plugin-dir; model traffic
still goes only to the loopback mock. It does not alter plugin registrations.
Raw native transcripts stay in that private lab, never in the source package.
"""
import hashlib
import http.server
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import threading


def run(lab, installed=False):
    lab = Path(lab).resolve()
    lab.mkdir(mode=0o700, parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    if installed:
        registrations=json.loads((Path.home()/'.claude/plugins/installed_plugins.json').read_text())
        entries=registrations['plugins']['acgm@acgm']
        plugin=Path(next(e['installPath'] for e in entries if e['scope']=='user'))
        market=json.loads((Path.home()/'.claude/plugins/known_marketplaces.json').read_text())['acgm']
        source=market['source']
        registered_source=Path(source['path']) if source.get('source')=='directory' else plugin
    else:
        plugin = lab/'candidate'
        shutil.copytree(repo, plugin, ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','ACGM-install*'))
    expected_version=json.loads((plugin/'.claude-plugin/plugin.json').read_text())['version']
    project=lab/'project';project.mkdir();(lab/'bin').mkdir();(lab/'captures').mkdir()
    tool='/opt/reviewed/health.sh';bad='/opt/reviewed/other-health.sh'
    body=b'#!/bin/sh\ncase "$*" in "") echo HEALTH_OK;; --json) echo \'{"healthy":true}\';; *) exit 9;; esac\n'
    fixture=lab/'health.sh';fixture.write_bytes(body);fixture.chmod(0o700)
    (lab/'other-health.sh').write_bytes(body+b'# changed fixture\n')
    digest=hashlib.sha256(body).hexdigest()
    policy={'remote_path_guards':[], 'remote_readonly_tools':[
        {'host':'fixture-host','path':p,'sha256':digest,'allowed_argv':[[],['--json']]} for p in (tool,bad)]}
    (project/'.governance').mkdir();(project/'.governance/remote-path-guards.json').write_text(json.dumps(policy))
    fake=lab/'bin/ssh'
    fake.write_text('#!'+sys.executable+'\n'+'''import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
args=sys.argv[1:]
with (root/'executed.jsonl').open('a') as f:f.write(json.dumps(args)+'\\n')
if len(args)!=2 or args[0]!='fixture-host':sys.exit(81)
payload=args[1]
paths={'/opt/reviewed/health.sh':root/'health.sh','/opt/reviewed/other-health.sh':root/'other-health.sh'}
for remote,local in paths.items():
 if payload=='sha256sum '+remote:
  print(hashlib.sha256(local.read_bytes()).hexdigest()+'  '+remote);sys.exit(0)
 if remote.endswith('/health.sh') and payload in (remote,remote+' --json'):
  sys.exit(subprocess.run(['/bin/sh',str(local)]+(['--json'] if payload.endswith(' --json') else [])).returncode)
sys.exit(82)
''');fake.chmod(0o700)
    cases=[('fake-ssh-resolution','which ssh',True),
           ('missing-hash',f"ssh fixture-host '{tool}'",False),
           ('hash-evidence',f"ssh fixture-host 'sha256sum {tool}'",True),
           ('exact-empty-argv',f"ssh fixture-host '{tool}'",True),
           ('exact-json-argv',f"ssh fixture-host '{tool} --json'",True),
           ('unknown-argv',f"ssh fixture-host '{tool} --unknown'",False),
           ('composition',f"ssh fixture-host '{tool}; rm x'",False),
           ('wrong-host',f"ssh other-host '{tool}'",False),
           ('mismatched-hash-evidence',f"ssh fixture-host 'sha256sum {bad}'",True),
           ('mismatched-hash-invocation',f"ssh fixture-host '{bad}'",False),
           ('unsupported-service',"ssh fixture-host 'systemctl restart example.service'",False),
           ('tool-failure','false',False)]
    (lab/'cases.json').write_text(json.dumps(cases,indent=2))
    recorder=lab/'recorder.py'
    recorder.write_text('''import json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
p=json.load(sys.stdin)
key=str(time.time_ns())
(root/'captures'/f'{key}.input.json').write_text(json.dumps(p))
t=Path(p.get('transcript_path','/nonexistent'))
if t.is_file():(root/'captures'/f'{key}.transcript.jsonl').write_bytes(t.read_bytes())
allowed=[c[1] for c in json.loads((root/'cases.json').read_text())]
if (p.get('tool_input') or {}).get('command') in allowed:print('{}')
else:print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':'LAB command containment'}}))
''')
    env_file=lab/'shell-env.sh'
    env_file.write_text('export PATH='+shlex.quote(str(lab/'bin')+':'+os.environ['PATH'])+'\n')
    start=lab/'session-start.py'
    start.write_text('''import os
from pathlib import Path
p=os.environ.get('CLAUDE_ENV_FILE')
if p:
 with open(p,'a') as f:f.write((Path(__file__).resolve().parent/'shell-env.sh').read_text())
print('{}')
''')
    hook=lambda p:{'type':'command','command':shlex.quote(sys.executable)+' '+shlex.quote(str(p))}
    settings={'hooks':{'PreToolUse':[{'matcher':'Bash','hooks':[hook(recorder)]}],
                       'SessionStart':[{'hooks':[hook(start)]}]}}
    (lab/'settings.json').write_text(json.dumps(settings))
    received=[];problems=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'{}')
        def do_POST(self):
            request=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            if 'count_tokens' in self.path:
                self.send_response(200);self.end_headers();self.wfile.write(b'{"input_tokens":100}');return
            n=len(received);received.append(request)
            # No SSH command is issued until the real shell proves it resolves
            # our fake executable. Abort rather than risk contacting a host.
            first_results=[b for message in request.get('messages',[]) for b in message.get('content',[]) if isinstance(b,dict) and b.get('type')=='tool_result' and b.get('tool_use_id')=='toolu_fixture_0']
            if n==1 and (len(first_results)!=1 or first_results[0].get('is_error') or str(fake) not in json.dumps(first_results[0].get('content'))):
                problems.append('Fake SSH resolution not proven');n=len(cases)
            if n<len(cases) and not problems:
                block={'type':'tool_use','id':f'toolu_fixture_{n}','name':'Bash',
                       'input':{'command':cases[n][1],'description':'Local synthetic acceptance','timeout':10000}}
                stop='tool_use'
            else:block={'type':'text','text':'LOCAL HARNESS COMPLETE'};stop='end_turn'
            msg={'id':f'msg_fixture_{n}','type':'message','role':'assistant','model':request.get('model','fixture'),
                 'content':[block],'stop_reason':stop,'stop_sequence':None,'usage':{'input_tokens':100,'output_tokens':40}}
            self.send_response(200);self.send_header('Content-Type','text/event-stream' if request.get('stream') else 'application/json');self.end_headers()
            if not request.get('stream'):self.wfile.write(json.dumps(msg).encode());return
            start_msg={**msg,'content':[],'stop_reason':None}
            blank={**block,('input' if stop=='tool_use' else 'text'):({} if stop=='tool_use' else '')}
            delta={'type':'input_json_delta','partial_json':json.dumps(block['input'])} if stop=='tool_use' else {'type':'text_delta','text':block['text']}
            events=[('message_start',{'type':'message_start','message':start_msg}),
                    ('content_block_start',{'type':'content_block_start','index':0,'content_block':blank}),
                    ('content_block_delta',{'type':'content_block_delta','index':0,'delta':delta}),
                    ('content_block_stop',{'type':'content_block_stop','index':0}),
                    ('message_delta',{'type':'message_delta','delta':{'stop_reason':stop,'stop_sequence':None},'usage':{'output_tokens':40}}),
                    ('message_stop',{'type':'message_stop'})]
            for event,data in events:self.wfile.write(f'event: {event}\ndata: {json.dumps(data)}\n\n'.encode());self.wfile.flush()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    env={k:v for k,v in os.environ.items() if not k.startswith(('ANTHROPIC_','CLAUDE_','ACGM_')) and k!='CLAUDECODE'}
    env.update({'ANTHROPIC_API_KEY':'local-fixture-not-a-secret','ANTHROPIC_BASE_URL':f'http://127.0.0.1:{server.server_port}',
                'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1',
                'DISABLE_AUTOUPDATER':'1','DISABLE_TELEMETRY':'1','DISABLE_ERROR_REPORTING':'1',
                'PATH':str(lab/'bin')+':'+os.environ['PATH'],'BASH_ENV':str(env_file),
                'ACGM_LOG_DIR':str(lab/'observations'),'ACGM_OBSERVATIONS':'1'})
    if not installed:
        env['CLAUDE_CONFIG_DIR']=str(lab/'isolated-claude')
    args=[shutil.which('claude'),'--print','--verbose','--output-format','stream-json','--include-hook-events',
          '--setting-sources','user' if installed else '', '--settings',str(lab/'settings.json'),
          '--strict-mcp-config','--tools','Bash','--allowedTools','Bash','--permission-mode','dontAsk']
    if not installed:
        args += ['--plugin-dir',str(plugin)]
    try:
        with (lab/'stream.jsonl').open('w') as out,(lab/'stderr.txt').open('w') as err:
            result=subprocess.run(args,input='Execute only the local synthetic acceptance sequence. Expected Hook denials must be retained. Do not install or bootstrap anything.',
                                  text=True,stdout=out,stderr=err,cwd=project,env=env,timeout=180)
    finally:server.shutdown();(lab/'requests.json').write_text(json.dumps(received))
    records=[json.loads(line) for line in (lab/'stream.jsonl').read_text().splitlines() if line.strip()]
    results={b['tool_use_id']:b for row in records if row.get('type')=='user'
             for b in row.get('message',{}).get('content',[]) if b.get('type')=='tool_result'}
    summary=[]
    for n,(name,command,allowed) in enumerate(cases):
        block=results.get(f'toolu_fixture_{n}')
        text=json.dumps(block,ensure_ascii=False)
        passed=block is not None and (not block.get('is_error',False) if allowed else block.get('is_error',False) and 'ACGM gate' in text)
        if name=='tool-failure':
            passed=block is not None and block.get('is_error',False) and 'ACGM gate' not in text
        summary.append({'case':name,'expected':'TOOL_FAILURE' if name=='tool-failure' else ('PASS' if allowed else 'DENY'),'verified':bool(passed)})
    executed=[json.loads(line) for line in (lab/'executed.jsonl').read_text().splitlines()] if (lab/'executed.jsonl').exists() else []
    expected=[['fixture-host',s] for s in ('sha256sum '+tool,tool,tool+' --json','sha256sum '+bad)]
    loaded=[p for row in records if row.get('type')=='system' and row.get('subtype')=='init'
            for p in row.get('plugins',[]) if p.get('name')=='acgm']
    # Directory marketplaces may load their registered source directly rather
    # than cache. Verify the resolved root AND its shipped bytes in either case.
    allowed_roots={plugin.resolve()}
    if installed:allowed_roots.add(registered_source.resolve())
    def verified_identity(p):
        root=Path(p.get('path','/nonexistent')).resolve()
        if p.get('version')!=expected_version or root not in allowed_roots:
            return False
        if installed and p.get('source')!='acgm@acgm':return False
        for file in plugin.rglob('*'):
            rel=file.relative_to(plugin)
            if any(part in ('__pycache__','.in_use') for part in rel.parts) or file.suffix=='.pyc':continue
            if file.is_file() and (not (root/rel).is_file() or file.read_bytes()!=(root/rel).read_bytes()):return False
        return True
    identity=any(verified_identity(p) for p in loaded)
    startup=any('ACGM SessionStart observed' in json.dumps(row) for row in records)
    diagnostic=any('TRUSTED_EVIDENCE_MISSING' in json.dumps(row) for row in records)
    unsupported=any('EVIDENCE_TARGET_UNSUPPORTED' in json.dumps(row) for row in records)
    observation_rows=[json.loads(line) for p in (lab/'observations').glob('*.jsonl') for line in p.read_text().splitlines()]
    gate_rows=[r for r in observation_rows if r.get('event')=='gate_decision']
    observations_verified=(len(gate_rows)==len(cases)
                           and sum(r['outcome']=='deny' for r in gate_rows)==sum(not c[2] and c[0]!='tool-failure' for c in cases)
                           and any(r.get('event')=='PostToolUse' for r in observation_rows)
                           and any(r.get('event')=='PostToolUseFailure' for r in observation_rows)
                           and any(r.get('event')=='SessionStart' for r in observation_rows)
                           and all('fixture-host' not in json.dumps(r) and '/opt/reviewed' not in json.dumps(r) for r in observation_rows))
    checks={'exit_code':result.returncode,'cases':summary,'fake_ssh_only_expected_calls':executed==expected,
            'installed_discovery':installed, 'loaded_identity_verified':identity,
            'loaded_plugin':loaded,
            'startup_observed':startup,'structured_denial_observed':diagnostic,'unsupported_target_observed':unsupported,
            'containment_errors':problems,'cli_version':subprocess.check_output([args[0],'--version'],text=True).strip()}
    checks['observations_verified']=observations_verified
    (lab/'results.json').write_text(json.dumps(checks,indent=2))
    print(json.dumps(checks,indent=2))
    return 0 if result.returncode==0 and not problems and executed==expected and identity and startup and diagnostic and unsupported and observations_verified and all(c['verified'] for c in summary) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1], '--installed' in sys.argv[2:]))
