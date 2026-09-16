# ACGM v0.9.4

## Security

- Remote read-only evidence now classifies the SSH payload using the same policy as command routing. Transfers do not certify evidence.
- Gated destructive operations fail closed when evidence is missing, unreadable, malformed, pending, failed or interrupted. A request alone is not evidence.
- Filesystem evidence is bound to every identifiable target, or its direct parent, on the same host. The window remains 12 prior tool calls.
- LOCAL / REMOTE protected-path guards reject local access treated as remote, mismatched host aliases, and unsupported transport or identity overrides.
- Project policy uses a stable project anchor rather than the current shell directory. Explicit absolute policy configuration takes precedence; invalid configuration fails closed.
- SessionEnd verification requires actual successful tool results, the exact target and host, and ordering after the declared operation. Assistant prose cannot satisfy verification.
- Read-only command classification rejects known execution, write and mutation options; parsing and runtime failures deny guarded operations.
- Supported safe queries include journalctl and systemctl show with validated options. Unknown or mutating options do not gain read-only status.

## Reliability / Audit

- CONTEXT DENY events, including JSON-escaped Hook attachments, count as blocked activity.
- Doctor ignores __pycache__, *.pyc and .in_use runtime artifacts while continuing to detect real source, Hook and configuration differences.

## Compatibility and known limitations

- Previously accepted commands without successful matching evidence can now be denied. Complex SSH options and unresolved relative targets have deliberately narrow support.
- Arbitrary opaque LOCAL wrappers are not fully inspected. ACGM is a shell-hook guardrail, not a complete sandbox for arbitrary shell environments.
- Symlinks, trusted executable replacement, computed paths, mutable remote working directories, host aliases and time-of-check/time-of-use changes remain boundaries.
- Pure read-only compound Bash may be overblocked by conservative fail-closed classification.
- Codex adapter integration is not included. Targeted simplification remains deferred.
- Publication does not install or activate the plugin locally. Runtime activation and user acceptance are separate from source tests.

## Validation

The existing formal suite passed 114/114 tests. Python compilation, shell syntax, whitespace and version checks passed; all nine frozen security-core hashes match the reviewed delivery. No experimental test matrix was added for this release.

See [security and compatibility details](SECURITY-v0.9.4.md), [policy anchoring](POLICY-ANCHOR.md) and [safe service queries](SERVICE-QUERIES.md).
