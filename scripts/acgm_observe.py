#!/usr/bin/env python3
"""Best-effort, bounded local Hook observations. Never a permission decision.

No commands, paths, outputs, prompts, credentials or token estimates are stored.
Opaque correlation IDs use a private per-install HMAC key. No network calls.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 8 * 1024 * 1024
KEEP_DAYS = 14
CODES = set('FIELDS BINDING STANDALONE EVIDENCE EVIDENCE_TARGET_UNSUPPORTED EVIDENCE_TRANSCRIPT_INVALID POLICY_OR_RUNTIME_INVALID HOST CONTEXT REMOTE-PARSE TRUSTED_INVOCATION_SHAPE TRUSTED_EVIDENCE_MISSING TRUSTED_HASH_OR_OUTPUT_MISMATCH TRUSTED_EVIDENCE_FAILED_OR_PENDING TRUSTED_IDENTITY_OR_ARGV'.split())
TOOLS = set('Bash Read Write Edit MultiEdit Glob Grep Skill Task Agent AskUserQuestion WebFetch WebSearch NotebookRead NotebookEdit TodoWrite'.split())


def log_root():
    override = os.environ.get('ACGM_LOG_DIR')
    if override:
        if not os.path.isabs(override):
            raise ValueError('ACGM_LOG_DIR must be absolute')
        return Path(override)
    data = os.environ.get('CLAUDE_PLUGIN_DATA')
    if data and not os.path.isabs(data):
        raise ValueError('Plugin data path must be absolute')
    return (Path(data) if data else Path.home() / '.claude/plugins/data/acgm-acgm') / 'observations'


def safe_open(directory, name, flags):
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_nlink != 1 or s.st_mode & 0o077:
        os.close(fd)
        raise ValueError('Unsafe observation file')
    return fd


def make_event(payload, decision, key):
    if not isinstance(payload, dict) or not isinstance(payload.get('session_id'), str) or not payload['session_id']:
        return None
    event = 'gate_decision' if decision is not None else payload.get('hook_event_name')
    if event not in ('gate_decision', 'SessionStart', 'SessionEnd', 'PostToolUse', 'PostToolUseFailure'):
        return None
    def opaque(kind, value):
        if not isinstance(value, str) or not value:
            return None
        return hmac.new(key, (kind + '\0' + value).encode(), hashlib.sha256).hexdigest()[:32]
    tool = payload.get('tool_name')
    tool_input = payload.get('tool_input')
    command = tool_input.get('command', '') if isinstance(tool_input, dict) else ''
    if not isinstance(command, str):
        command = ''
    outcome = {'PostToolUse': 'tool_success', 'PostToolUseFailure': 'tool_failure',
               'SessionStart': 'observed', 'SessionEnd': 'observed'}.get(event, 'unknown')
    codes = []
    if decision is not None:
        if not isinstance(decision, dict):
            return None
        hook = decision.get('hookSpecificOutput') or {}
        if decision == {}:
            outcome = 'pass_through'
        elif hook.get('permissionDecision') == 'deny':
            outcome = 'deny'
            reason = hook.get('permissionDecisionReason', '')
            if '\nACGM-DIAGNOSTIC: ' in reason:
                try:
                    issues = json.loads(reason.split('\nACGM-DIAGNOSTIC: ', 1)[1])['issues']
                    codes = sorted({i.get('code') if i.get('code') in CODES else 'OTHER' for i in issues})
                except (ValueError, KeyError, TypeError, AttributeError):
                    codes = ['UNKNOWN']
            else:
                codes = ['RUNTIME_UNAVAILABLE']
        else:
            outcome = 'unknown'
    version = (Path(__file__).resolve().parent.parent / 'VERSION').read_text().strip()
    return {'schema_version': 1, 'at': datetime.now(timezone.utc).isoformat(), 'plugin_version': version,
            'event': event, 'outcome': outcome, 'reason_codes': codes,
            'tool': tool if tool in TOOLS else ('Other' if tool else None),
            'project': opaque('project', os.environ.get('CLAUDE_PROJECT_DIR') or payload.get('cwd')),
            'session': opaque('session', payload.get('session_id')),
            'call': opaque('call', payload.get('tool_use_id')),
            'command': opaque('command', command)}


def record(payload, decision=None):
    """Logging loss never changes Hook stdout, exit status or Gate policy."""
    if os.environ.get('ACGM_OBSERVATIONS', '1') == '0' or not isinstance(payload, dict) or not payload.get('session_id'):
        return
    try:
        root = log_root()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        d = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            s = os.fstat(d)
            if s.st_uid != os.getuid() or s.st_mode & 0o077:
                return
            lock = safe_open(d, '.lock', os.O_CREAT | os.O_RDWR)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                marker = '.acgm-observations-v1'
                if marker not in os.listdir(d):
                    if set(os.listdir(d)) - {'.lock'}:
                        return  # Never rotate or prune somebody else's directory.
                    marker_fd = safe_open(d, marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    with os.fdopen(marker_fd, 'wb') as f:
                        f.write(b'ACGM observations v1\n')
                else:
                    marker_fd = safe_open(d, marker, os.O_RDONLY)
                    with os.fdopen(marker_fd, 'rb') as f:
                        if f.read(64) != b'ACGM observations v1\n':
                            return
                try:
                    salt = safe_open(d, '.key', os.O_CREAT | os.O_EXCL | os.O_RDWR)
                except FileExistsError:
                    salt = safe_open(d, '.key', os.O_RDONLY)
                    with os.fdopen(salt, 'rb') as f:
                        key = f.read(33)
                    if len(key) != 32:
                        return
                else:
                    key = os.urandom(32)
                    with os.fdopen(salt, 'wb') as f:
                        f.write(key)
                row = make_event(payload, decision, key)
                if row is None:
                    return
                today = datetime.now(timezone.utc).date()
                cutoff = today - timedelta(days=KEEP_DAYS - 1)
                for name in os.listdir(d):
                    if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:\.1)?\.jsonl', name) and name[:10] < cutoff.isoformat():
                        # Only this logger's dated entries; unlink does not follow symlinks.
                        os.unlink(name, dir_fd=d)
                name = today.isoformat() + '.jsonl'
                encoded = (json.dumps(row, separators=(',', ':')) + '\n').encode()
                fd = safe_open(d, name, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
                if os.fstat(fd).st_size + len(encoded) > MAX_BYTES:
                    os.close(fd)
                    os.replace(name, today.isoformat() + '.1.jsonl', src_dir_fd=d, dst_dir_fd=d)
                    fd = safe_open(d, name, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'ab') as f:
                    f.write(encoded)
            finally:
                os.close(lock)
        finally:
            os.close(d)
    except Exception:
        # Deliberately best effort. No retry loop, transcript reads or networking.
        return


def summary(root):
    rows, seen, malformed = [], set(), 0
    for p in sorted(root.glob('*.jsonl')):
        if p.is_symlink() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:\.1)?\.jsonl', p.name):
            continue
        with p.open() as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if r.get('schema_version') != 1:
                        raise ValueError()
                    identity = (r['session'], r['call'], r['event']) if r.get('call') else (r['session'], r['event'], r['at'])
                    if identity in seen:
                        continue
                    seen.add(identity); rows.append(r)
                except (ValueError, KeyError, TypeError, AttributeError):
                    malformed += 1
    counts = Counter(r['event'] + ':' + r['outcome'] for r in rows)
    reasons = Counter(c for r in rows for c in r['reason_codes'])
    denied = Counter((r['session'], r['command']) for r in rows if r['event'] == 'gate_decision' and r['outcome'] == 'deny' and r.get('command'))
    return {'schema_version': 1, 'log_directory': str(root), 'events': dict(counts),
            'reason_codes': dict(reasons), 'sessions': len({r['session'] for r in rows}),
            'versions': sorted({r['plugin_version'] for r in rows}), 'malformed_lines': malformed,
            'repeated_same_command_denials': sum(max(0, n-1) for n in denied.values()),
            'coverage': 'Best effort, retained observations only; absence does not prove no activity. Pass-through is not authorization or execution. No token or task-success estimates.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['hook', 'gate', 'summary'])
    args = parser.parse_args()
    if args.mode == 'summary':
        print(json.dumps(summary(log_root()), ensure_ascii=False, indent=2))
        return
    try:
        raw = sys.stdin.read(2 * MAX_BYTES)
        decoder = json.JSONDecoder()
        payload, end = decoder.raw_decode(raw.lstrip())
        decision = json.loads(raw.lstrip()[end:].strip()) if args.mode == 'gate' else None
        record(payload, decision)
    except Exception:
        pass
    if args.mode == 'hook':
        print('{}')


if __name__ == '__main__':
    main()
