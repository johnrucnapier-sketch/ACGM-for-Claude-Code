# v0.9.6-rc.2 — Claude Code workflow candidate, stage 1

This candidate reduces startup and Gate interpretation work. It includes the
existing v0.9.5-rc.1 trusted remote read-only capability. It does not implement
service resource evidence, evidence leases, a Guardian, model profiles, automatic
fact correction or a handoff generator. Behavioral improvement needs real user
sessions; automated checks alone cannot establish reduced time or token cost.

## What changes

- SessionStart reports root rules, ledger presence, runtime policy validity and
  registered-tool count separately. Only that Hook is observed, not all Hooks.
- Startup and Gate share the stable project anchor, including Git worktrees and
  startup subdirectories. Policy remains anchored to CLAUDE_PROJECT_DIR, not a
  later shell cwd. Explicit ACGM_POLICY_CONFIG retains its precedence.
- Grounding reads applicable rules and task-relevant facts, reuses existing
  authorization and SOPs, and asks only about material unresolved scope/risk.
  Full installation doctor is for missing, contradictory or changed evidence.
- Gate returns reason codes with next_safe_action. Unsupported non-filesystem
  resources cannot be repaired by filling fields; no such retry is suggested.
- Exact registered read-only tools get the required single-file hash command
  and canonical invocation when appropriate. Changed hashes, wrong hosts and
  unknown arguments never cause automatic trust updates or payload execution.

## Read-only command inspection

Use the installed plugin path in place of `<plugin-root>`. The input is data,
not a shell script. This command inspects a proposed operation; it never runs it.

```sh
python3 '<plugin-root>/scripts/acgm-explain.py' --project '/absolute/project' <<'JSON'
{
  "tool_name": "Bash",
  "tool_input": {"command": "ssh reviewed-host 'systemctl restart example.service'"},
  "cwd": "/absolute/project"
}
JSON
```

For evidence-aware inspection include the real `transcript_path`, and
`tool_use_id` only if that call already exists in the transcript. Without a
transcript no prior tool evidence is established. `--project` identifies the
actual startup project; `cwd` identifies the inspected call's working directory.
Neither is an authorization token. Do not supply another project's policy to
make an operation pass.

The inspector runs the shipped Bash Hook with the payload on stdin, using the
same protected-path checks, routing, parser, fields and transcript evidence as
actual execution. It does not evaluate the command or call SSH. Exit codes:

| Code | Verdict | Meaning |
|---|---|---|
| 0 | pass_through | ACGM would not block this input at this snapshot |
| 2 | deny | ACGM blocks it; inspect issues and next_safe_action |
| 1 | error | Inspection is unavailable or input invalid; no verdict |

All outputs explicitly say `executed: false`, `authorized: false`. A pass-through
is neither a safety certificate nor permission. Local opaque wrappers remain an
existing limitation of the Hook; the inspector does not make that coverage wider.
Actual execution must pass the live Hook and Claude's normal permissions again.

## Retained boundaries

Exact host/path/argv/hash matching; successful ordered tool results; latest hash
observation wins; 12 prior calls; no assistant prose as evidence; no implicit
wrapper trust; same-host exact/parent pre-evidence and exact post-verification.
No automatic registry edits, no global Hook changes, no model-specific trust.

The action's technical correctness is not established by four comment fields.
Runtime state, dependencies, symlinks and replacement between reading and acting
remain outside this bounded static inspection. Unsupported service targets remain
unsupported in this candidate. Changes to their semantics belong to stage 3.

## User acceptance: short sessions with each backend

Start a new Claude Code session after installation; an existing session retains
its old plugin bindings. Keep the project, task, policy and backend parameters
comparable. Use a disposable project or an authorized read-only task first.

1. **Startup:** one project with rules and one with only runtime policy. The
   summary should distinguish the two without triggering bootstrap or full audit.
2. **Known read-only task:** use the existing reviewed invocation; when its exact
   hash evidence is missing, the first denial should explain the single-file
   remote read needed. No Gate source reading should be necessary.
3. **Unsupported target:** inspect (do not execute) a service change. It should
   explain that this version cannot bind the resource, not induce repeated fields.
4. **Containment:** inspect a wrong-host or failed-evidence example in a fixture;
   it must stay denied, regardless of model or explanation wording.

Record actual backend/runtime and plugin version, policy identity, task outcome,
first effective action time, Gate reasons, retries, source-code reads and user
corrections. Separate host permission, tool, gateway and ACGM errors. Record token
and timing values only where available; do not infer them from transcript length.

Stage 1 succeeds if normal work needs less rule discovery while negative cases
retain their denials. Do not treat this as validation of the deferred stages.
