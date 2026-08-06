#!/bin/sh
# grounding-inject.sh — ACGM v0.4 SessionStart injector.
#
# Only hooks fire automatically in Claude Code, so this points at the skills
# rather than restating them. Every word here is paid on every session: keep it
# short, and let the skills carry the detail.
#
# It also declares its own limit. A SessionStart message proves this hook ran;
# it does not prove the other hooks loaded. Saying so here is cheaper than
# letting the agent infer that governance is fully active.

set -eu

DIR="$(pwd)"
HAS_GOV="no"
for f in CLAUDE.md docs/CONSTITUTION.md CONSTITUTION.md AGENTS.md .governance/CONSTITUTION.md; do
  if [ -f "$DIR/$f" ]; then HAS_GOV="yes"; break; fi
done

DOCTOR="${CLAUDE_PLUGIN_ROOT:-.}/scripts/acgm-doctor.sh"

if [ "$HAS_GOV" = "yes" ]; then
  MSG="ACGM governance is active in this project.

Before acting, invoke \`session-grounding\`: read the constitution and root rules in full, identify track and scope, re-read current code and Git state, then report five items and WAIT for human confirmation. A handoff, memory entry or compacted summary is historical evidence — never current code truth. If this session was resumed or compacted, every inherited identifier (path, version, service, plugin id) must be re-verified at source NOW before reuse.

Before any technical conclusion, and before any irreversible, destructive or state-changing operation, invoke \`truth-first\`. The gate is structural: carry ACGM-EVIDENCE / ACGM-CURRENT-STATE / ACGM-VERIFY-AFTER / ACGM-ROLLBACK as comment lines in the command itself, with real content, and keep source inspection, the operation, and verification in three separate tool calls, and never compound the operation with ';' '&&' '|' or a computed target. A complete gate is evidence, not authorization.

Track open decision threads as you work; when one closes, draft it to \`.governance/claims/\` and request confirmation only by riding along with something you were already sending — invoke \`decision-ledger\`.

Keep four states apart: source verified, configuration verified, runtime activated, project governed. This message proves only that SessionStart ran. To check the rest: sh ${DOCTOR}

本项目已启用 ACGM 治理:动手前先走 session-grounding(读宪法+根规则、判轨道、重读当前代码与 Git 状态、报告五项等人确认);写技术结论或做不可逆/破坏性/状态变更操作前先过 truth-first(四字段写成命令自身的注释行 + 取证/操作/核验三次独立调用,四项齐全也只是证据不是授权);续接或 compact 后,一切继承的指称必须当下从源头重新验证。工作中跟踪开放的决策线程,闭合时起草进 \`.governance/claims/\`,确认只搭在本来就要发的话里(见 \`decision-ledger\`)。区分四种状态:源已验证、配置已验证、运行时已激活、项目已治理——本条消息只能证明 SessionStart 跑了。"
else
  MSG="agent-coding-governance is installed but no governance docs were found in this project. To bootstrap governance from zero, invoke the \`governance-bootstrap\` skill — a human-driven checklist, not an autonomous run. Its first step is proving the mechanism actually runs: sh ${DOCTOR}

未发现治理文档;从零建治理请调用 governance-bootstrap(人驱动清单,非自主执行)。第一步是证明机制本身在运行。"
fi

python3 - "$MSG" <<'PY'
import json, sys
print(json.dumps({
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": sys.argv[1]
  }
}))
PY
