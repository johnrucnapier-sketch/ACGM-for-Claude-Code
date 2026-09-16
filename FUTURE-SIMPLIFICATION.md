# Deferred safety-semantic consolidation

v0.9.4 deferred work. No simplification authorized or performed.

- READ_ONLY_BASH / READ_ONLY_HELPER name candidates still require safe_read_options;
  the regex alone is not a public read-only verdict. Keep all callers on
  payload_is_read_only / bash_is_read_only.
- assistant_turns remains for historical compatibility but SessionEnd no longer
  calls it. Do not restore prose-based verification or delete it in this patch.
- Activity reporting still owns a stale destructive regex. Consolidation with
  actual Gate outcomes is deferred; its destructive_total is not acceptance evidence.
- Pre-evidence exact/parent policy is unchanged. Post-verification requires exact
  target+host; do not silently relax it to the prior-evidence parent rule.
- Non-filesystem VERIFY-AFTER promises without supported literal absolute targets
  remain unresolved, rather than being satisfied by unrelated tool calls.
- A recorded failed/denied mutation request may leave a conservative obligation:
  distinguishing proven non-execution from partial execution requires explicit
  normalized facts, never parsing assistant claims or error prose.
