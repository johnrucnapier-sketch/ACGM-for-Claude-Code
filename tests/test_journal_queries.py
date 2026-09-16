"""rc3 canary regressions; payloads are never executed by these tests."""
import shlex
import unittest
from test_security import policy, call

QUERIES = [
    "journalctl -u fixture.service --since '2026-09-15 10:00:00'",
    "journalctl --unit=fixture.service --since=today --until=now --no-pager",
    "journalctl -n 50 -p warning -o short-iso --utc -b",
    "journalctl --list-boots", "journalctl --disk-usage", "journalctl",
    "systemctl show fixture.service --property=ActiveState,SubState --value --no-pager",
    "systemctl show -p MainPID fixture.service", "systemctl show",
]
NON_QUERIES = [
    "journalctl " + flag for flag in (
        '--rotate', '--vacuum-size=1M', '--vacuum-time=1d', '--vacuum-files=1',
        '--flush', '--sync', '--relinquish-var', '--smart-relinquish-var',
        '--setup-keys', '--update-catalog', '--cursor-file=/tmp/cursor',
        '--synchronize-on-exit=yes', '--unknown', '--rot', '-u', '--since=',
        '--unit=fixture.service --rotate', '--unit fixture.service --flush',
        '-u $OPTIONS', '--unit=fixture*', '--since --rotate')
] + ['systemctl show --unknown', 'systemctl show --property',
     'systemctl show --property=$OPTIONS', 'systemctl restart fixture.service',
     'systemctl reboot', 'reboot']

class JournalQueryTests(unittest.TestCase):
    def test_explicit_queries_are_remote_read_only(self):
        for payload in QUERIES:
            with self.subTest(payload=payload):
                command='ssh nas '+shlex.quote(payload)
                self.assertTrue(policy.bash_is_read_only(command))
                self.assertFalse(policy.remote_needs_gate(command))

    def test_state_changes_unknown_and_malformed_options_fail_closed(self):
        for payload in NON_QUERIES:
            with self.subTest(payload=payload):
                command='ssh nas '+shlex.quote(payload)
                self.assertFalse(policy.bash_is_read_only(command))
                self.assertTrue(policy.remote_needs_gate(command))

    def test_queries_do_not_authorize_file_or_host_mutation(self):
        for payload in QUERIES:
            evidence=call('ssh nas '+shlex.quote(payload))
            for mutation in ("ssh nas 'rm /production/database'",
                             "ssh nas 'systemctl restart fixture.service'", "ssh nas 'reboot'"):
                with self.subTest(payload=payload, mutation=mutation):
                    self.assertFalse(policy.has_prior_evidence([evidence], mutation))

    def test_shell_operators_cannot_hide_journal_changes(self):
        for payload in ('journalctl --no-pager; journalctl --rotate',
                        'journalctl --no-pager && systemctl reboot',
                        'journalctl --no-pager > /tmp/output',
                        'journalctl -u $(echo fixture.service)'):
            self.assertFalse(policy.bash_is_read_only('ssh nas '+shlex.quote(payload)))
