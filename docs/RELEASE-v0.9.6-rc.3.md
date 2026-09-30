# 0.9.6-rc.3 — competition preparation patch

This release includes the previously local 0.9.5 / 0.9.6 candidates. Relative to
0.9.6-rc.2, Gate classification, authorization boundaries, exact trusted-tool
matching, the 12-call window and exact/direct-parent pre-evidence remain unchanged.
No local-write exemption, evidence lease, service-resource support or extra
mandatory declaration is introduced. It remains a release candidate.

## Changes relative to rc.2

- Explain unsupported outer SSH operators without discarding host/user/key/port.
- Explain that evidence must be a wholly read-only tool call: an `ls` combined
  with compilation is not eligible. Direct-parent evidence is still supported.
- Explain the repair order for compound operations and that `status` is not
  proof of a script's read-only identity.
- Resolve decision-ledger templates relative to the installed plugin root.
- Clarify that the non-blocking citation advisory sees only newly written text
  and can miss valid runtime evidence. Keep supported evidence; do not invent
  unrelated citations to silence it. Detection itself is unchanged.
- Add bounded local observation logs. No transmission, token estimates or
  automatic changes to project rules. Logging never grants permission.

## Local observations / 本地日志

Enabled by default for real Hook payloads with a session ID. Location:
`${CLAUDE_PLUGIN_DATA}/observations` when Claude supplies that absolute data path;
otherwise `~/.claude/plugins/data/acgm-acgm/observations`.
`ACGM_LOG_DIR` can explicitly select an absolute local destination.
Set `ACGM_OBSERVATIONS=0` in the launching process to turn observation writes off.
This switch does not disable the Gate or any governance check.

Each JSONL event contains UTC time, plugin version, event/outcome, known tool
category, reason codes, and HMAC identifiers for project/session/call/command.
The private per-install key is stored in `.key`. No command text, raw paths,
transcript content, model prompts, tool output or credentials are written.
Identifiers can correlate activity within one installation; they are pseudonymous,
not an assertion that every combination of metadata is anonymous.

Files use 0600, observation directory 0700. Non-blocking locking avoids waiting
for concurrent sessions; errors skip logging and preserve the computed Gate
verdict. Retention is 14 UTC dates, at most two 8 MiB files per date (224 MiB
maximum event content). Old files are pruned on the next successful write;
very busy days rotate out their oldest events. Missing events cannot prove that
no operation happened. The logs are a best-effort diagnostic, not an audit ledger.

Actual final Bash Gate decisions are recorded once, including pass-through.
PostToolUse / PostToolUseFailure observations distinguish tool results from Gate
decisions. SessionStart / SessionEnd mark lifecycle observations. Read-only
`acgm-explain.py` inspections are excluded to avoid counting hypothetical calls.
Pass-through is neither authorization nor successful execution. Tool success is
not task acceptance, deployment verification or a valid technical conclusion.

Aggregate locally (substitute the actual installed plugin root):

```sh
python3 '<plugin-root>/scripts/acgm_observe.py' summary
```

The summary deduplicates repeated callbacks by session/call/event, counts reason
codes and repeated identical-command denials. It does not infer total tokens,
recovery quality, cost or task success. Claude's original transcripts remain the
source for content-level review; repeated content blocks are not separate model
requests. Share selected summaries rather than `.key` or raw transcripts by default.

中文：这次只改提示、文档入口并加入观测，不改变 Gate 的放行规则。默认日志只落本机，
记录原因码、工具结果和不可直接还原的关联标识，不保存命令正文或文件内容。
比赛期间照常工作即可；结束后先查看日志汇总，再按需要对照本机原始会话分析。
日志写入失败不会改变 Gate 判定，日志也不参与之后的权限决策。

## Team installation and rollback

New users, in Claude Code:

```text
/plugin marketplace add johnrucnapier-sketch/ACGM-for-Claude-Code
/plugin install acgm@acgm
```

Existing GitHub-marketplace users, in a terminal:

```sh
claude plugin marketplace update acgm
claude plugin update acgm@acgm --scope user
claude plugin list
```

Verify `0.9.6-rc.3`, then **start a new Claude Code session**. Existing sessions
retain their previous Hook bindings. Local-directory marketplace installations
must update their registered directory source; a GitHub update does not replace it.
Do not uninstall unrelated plugins or copy someone else's global settings.

For an exact snapshot, clone this repository at tag `v0.9.6-rc.3` and register
that local directory as the marketplace. Keep the previous source/cache and data
before switching. Rollback re-registers the previous source and reinstalls
`acgm@acgm`; keep plugin data. Runtime activation still needs a new session.

## Known limits retained

`command -v ssh` can still be conservatively rejected; `which ssh` is the
supported path-inspection form. Opaque local wrappers, semantic external impact
and unrecognized shell forms remain existing boundaries. This patch does not
promise reduced total tokens, complete tracing or multi-model acceptance.

## Validation

160 automated tests pass both normally and with `CLAUDECODE=1`. Shell/Python
syntax and official marketplace validation pass. The native Claude CLI fixture
passes 12 cases, including the retained denials, successful hash-pinned reads,
an actual tool failure, plugin identity, and private observation output. The
fixture uses a loopback mock model and fake SSH; it does not establish real-model
quality or production-service safety. The rc.2 policy module is byte-identical.
