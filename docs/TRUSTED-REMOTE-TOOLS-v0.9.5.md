# v0.9.5 candidate: exact hash-pinned remote read-only tools

Historical v0.9.5 candidate specification; this capability is preserved by
v0.9.6-rc.2. See WORKFLOW-v0.9.6.md for the current candidate scope. This capability
does not turn shell Hooks into a sandbox or prove an arbitrary script read-only.

## Registry and loading

Reuse the existing stable project policy location:
`.governance/remote-path-guards.json`, or explicit absolute `ACGM_POLICY_CONFIG`.
No second discovery mechanism, global registry, plugin system or mutable trust cache.
Existing configurations remain valid. `remote_path_guards` is required (it may be
empty); `remote_readonly_tools` is optional and defaults to an empty list.

```json
{
  "remote_path_guards": [],
  "remote_readonly_tools": [
    {
      "host": "reviewed-host",
      "path": "/opt/reviewed/health.sh",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "allowed_argv": [[], ["--json"]]
    }
  ]
}
```

The hash above is an illustrative placeholder, not a trusted release digest.
A human must review the tool, its dependencies and each allowed invocation before
registering the real hash. Agent assertions and local source hashes cannot prove
current remote bytes. The implementation never edits the registry or repairs a
remote file automatically. Protect policy, Hook code and transcripts externally;
a writable policy is not a tamper-resistant authorization boundary.

Schema requires exact literal host, canonical absolute path, 64 lowercase hex
SHA256 digits and a nonempty list of exact argv vectors. Empty argv is explicit;
there is no implicit allowance when `allowed_argv` is missing. Duplicate JSON keys,
duplicate host/path entries (even identical), duplicate argv vectors, unknown entry
keys, wildcard hosts/paths, invalid hashes and relative paths fail closed.
A registered executable cannot conflict with an existing protected-path host.

V1 deliberately supports only simple path characters and argument tokens:
paths use ASCII letters/digits, underscore, dot, slash and hyphen; argv additionally
allows colon, equals and plus. No whitespace-bearing argv, interpolation, regex or
argument DSL. Paths cannot contain normalized-away components or trailing slashes.
Paths that the existing built-in read-only classifier already recognizes are
rejected at registration, rather than allowing that classifier to bypass pinning.

## Qualification flow

1. Discover and validate the existing project policy using the stable anchor.
2. Apply existing execution-context and protected-path checks first.
3. Reuse `shell_words` and `parse_remote`, then restrict their accepted subset to
   exactly `ssh host 'simple literal argv'`. No SSH options, user@host, absolute SSH
   launcher, environment prefixes, shell wrappers, comments, escapes, additional
   commands, redirection, substitution or newline are certified in this version.
4. Match registry host, absolute executable path and ordered argv vector exactly.
   Do not use basename, prefix, case folding, realpath or symlink resolution.
5. Reuse transcript normalization and the existing 12-prior-tool-call window,
   excluding the current call before taking the window. Find the latest exact
   same-host `sha256sum /registered/path` call in that window.
6. Require an actual matching successful tool result, after its request and before
   the current invocation when the latter is present in the transcript. Pending,
   failed, interrupted, duplicate/invalid and unparseable results do not qualify.
7. Require exactly one standard sha256sum text record: registered digest, two
   spaces, registered path, and optionally one trailing newline. No prose, extra
   lines, another filename, local hash, different host or assistant text qualifies.
   A newer failed/mismatched exact measurement invalidates an older good one.
8. Return `{}` through the normal host permission flow. Never emit `allow` or
   bypass unrelated context policy. Unqualified calls retain ordinary untrusted
   routing; for an opaque tool with no qualifying evidence the Gate denies.

The adapter retains at most 4096 characters per normalized result for this check.
Text blocks are accepted only when every content block is plain text. Existing
success/failure normalization is reused, not reimplemented in a second subsystem.

## Example sequence

After user registration of the reviewed digest:

```sh
ssh reviewed-host 'sha256sum /opt/reviewed/health.sh'
```

If the actual successful result matches, either separate invocation can qualify:

```sh
ssh reviewed-host '/opt/reviewed/health.sh'
ssh reviewed-host '/opt/reviewed/health.sh --json'
```

The two invocations above illustrate alternatives, not a compound Bash call.
Hash evidence expires after 12 subsequent tool calls. No wall-clock freshness
promise is made beyond the existing call window. Recheck when state may change.

## Evidence scope and limits

- A custom tool's internal read targets are opaque. It is qualified for execution,
  but does not automatically become evidence for unrelated file mutations or
  SessionEnd verification. Existing target extraction remains unchanged.
- A symlink alias is a different path and inherits no registered identity. However,
  sha256sum follows symlinks: this protocol does not establish that the registered
  path or its parent directories are non-symlinks. It does not resolve an alias
  into a registered path. Operators must govern the registered path themselves.
- Hash inspection and execution occur in separate calls. Replacement between them,
  changes to sourced files/interpreters/dependencies, trusted executable replacement,
  SSH alias/config changes and remote environment changes remain outside this
  bounded mechanism. It is not atomic hash-and-execute or dependency attestation.
- Failed/mismatched measurement never causes automatic mutation or fallback to a
  local source digest. Host keys, credentials and SSH configuration remain external.
- No changes to transfer parsing, wrappers, systemd evidence, date/ss classification,
  compound-Bash compatibility, Activity, doctor, SessionEnd or Codex adapters.

## Verification

Unit/real-Hook fixtures: `python3 -m unittest discover -s tests -v`.
The original 114 tests remain. New cases exercise schema errors, exact identities,
argv ordering, failed/interrupted/missing/stale/wrong-host hashes, output integrity,
result ordering, superseding failures, context guards and shell syntax exclusions.

Native acceptance runner:

```sh
python3 tests/harness_trusted_tools.py /absolute/new/private-lab
```

It uses the real Claude CLI, an isolated configuration directory, a temporary
candidate plugin copy, a loopback mock API and fake SSH. Before issuing SSH calls
it verifies the real shell resolves the fake executable. Fake SSH can only hash
fixed local fixtures or run the fixed read-only fixture with approved arguments.
It records ten assertions, including the seven required acceptance scenarios,
and checks denied calls never reached fake SSH. It neither installs a plugin nor
contacts a real remote host. Raw transcripts stay in the private lab, not Git.

This runner must complete successfully before recommending installation. Source
checks or a direct shell-Hook subprocess test are not native Harness acceptance.

### Candidate verification results

- Default suite: 134/134 PASS (all original 114 retained, 20 added test methods).
- CLAUDECODE=1 suite: 134/134 PASS.
- Python compilation, shell syntax, version consistency and whitespace: PASS.
- Real Claude Code 2.1.223 with fake SSH: 10/10 PASS, covering missing evidence,
  successful hash, both allowed argv vectors, unknown argv, shell composition,
  wrong host, a changed-file hash and denial of that changed tool.
- Fake SSH execution log contains only the two hash reads and two permitted tool
  executions. Denied invocations never reached the fixture executable.
- Production bytes used by native Harness match the reviewed local candidate.
- No real remote connection, local plugin installation, push or tag.

The initial Harness containment probe was rejected by existing command parsing;
the test probe was narrowed to `which ssh`. No production policy was relaxed.
After human review, a separately authorized small-scope candidate installation is
reasonable; these tests do not establish actual deployment or user acceptance.
