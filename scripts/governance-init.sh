#!/bin/sh
# governance-init.sh — plugin-free scaffolder for acgm.
#
# What this is (honest, per the methodology's own truth-first principle):
#   This is a SCAFFOLDER, not a runtime. It writes governance files into a target
#   project so the discipline is in place from session one.
#     - Claude Code: prefer the plugin (`/plugin marketplace add ...`); its
#       SessionStart hook injects grounding automatically at runtime. You do not
#       need this script.
#     - No plugin / other setups: this writes CONSTITUTION.md + AGENTS.md (a
#       generic agent-governance directive) + a CLAUDE.md pointer as STATIC files.
#       Whether the directive is auto-applied depends on whether your agent reads
#       an agents-file by convention; this is a static scaffold, not a runtime.
#   This script gives you the grounding directive + a blank constitution. The
#   FULL governance setup (decision log, snapshots, tracks) is deliberately
#   human-driven — run the `governance-bootstrap` skill / METHODOLOGY §12 for that.
#
# Idempotent & non-destructive: existing files are never overwritten — only
# reported and skipped.
#
# Usage:  sh scripts/governance-init.sh [TARGET_DIR]   (default: current dir)

set -eu

SELF_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd "$SELF_DIR/.." && pwd)
TEMPLATE_CONSTITUTION="$REPO_ROOT/templates/CONSTITUTION.skeleton.md"

TARGET="${1:-.}"

if [ ! -d "$TARGET" ]; then
  echo "✗ Target directory not found / 目标目录不存在: $TARGET" >&2
  exit 1
fi
TARGET=$(CDPATH= cd "$TARGET" && pwd)

if [ ! -f "$TEMPLATE_CONSTITUTION" ]; then
  echo "✗ Constitution template missing / 缺少宪法模板: $TEMPLATE_CONSTITUTION" >&2
  echo "  Run this from a full clone of the methodology repo." >&2
  echo "  请在方法论仓库的完整克隆里运行本脚本。" >&2
  exit 1
fi

echo "agent-coding-governance · scaffold → $TARGET"
echo "----------------------------------------------------------------"
CREATED=0
SKIPPED=0

note_skip() {
  echo "  • skip / 跳过 (已存在,未改动): $1"
  SKIPPED=$((SKIPPED + 1))
}
note_make() {
  echo "  • create / 新建: $1"
  CREATED=$((CREATED + 1))
}

# 1. CONSTITUTION.md — copied from the blank bilingual skeleton.
if [ -f "$TARGET/CONSTITUTION.md" ]; then
  note_skip "CONSTITUTION.md"
else
  cp "$TEMPLATE_CONSTITUTION" "$TARGET/CONSTITUTION.md"
  note_make "CONSTITUTION.md  (fill every <...> — humans only / 仅人可改)"
fi

# 2. AGENTS.md — generic agent-governance directive (a static file; an agent that
#    honors an agents-file convention will read it).
if [ -f "$TARGET/AGENTS.md" ]; then
  note_skip "AGENTS.md  (exists — merge the block below by hand / 已存在,请手动并入)"
else
  cat > "$TARGET/AGENTS.md" <<'EOF'
# Agent governance / agent 治理约束

This project uses agent-coding-governance. The rules below are non-negotiable and
apply to every session. Read and follow them before doing anything.

本项目启用 agent-coding-governance。以下规则不可妥协,适用于每个 session。
动手前先读并遵守。

## Before acting / 动手前:grounding(5 steps / 五步)

1. Read `CONSTITUTION.md` + the root rules in full — not skim. /
   完整读 `CONSTITUTION.md` + 根规则,不跳读。
2. Identify which track / scope this session is in; load that layer's docs. /
   判断本次落在哪个轨道/范围,加读对应层文档。
3. Report these 5, then WAIT for human confirmation before acting: which track;
   `git log` + `git status`; structure seen by actually reading code (not memory);
   exact file list you will change; the steps you will take. /
   报告这 5 项后等人确认再动手:落在哪个轨道;`git log`+`git status`;实际读代码
   看到的结构(不凭印象);要改的文件清单;打算的执行步骤。
4. After changes, run the verification scripts. / 改完跑验证脚本。
5. Closing report + commit draft — wait for human approval before committing. /
   收尾报告 + commit 草稿,等人审批再 commit。

## Before any technical conclusion or irreversible action / 写结论或不可逆操作前:truth-first

- Every claim carries `file:line` from grep/reading code. No "I think / usually /
  I recall". If you cannot read a truth source, say so — never guess. /
  每条结论带 grep/读码得到的 `文件:行号`。禁"我觉得/通常/我记得"。读不到真值就直说,不许编。
- A summary is never code-truth: never inherit a code fact from a summary,
  handoff, or memory layer — read it from the code now. /
  摘要永不作为代码真值:不从摘要/交接/记忆层继承代码事实——当下从代码读。
- Before destructive ops: list what is affected + write a rollback + quote the
  human's authorization verbatim. /
  破坏性操作前:列影响面 + 写回滚 + 原文引用人的授权。

## Scope / 范围

Default rule: only content needed for the software to be built / shipped / run
belongs here; business / strategy / non-software planning is OUT. This criterion
is a default — redefine it for your project if needed, but keep it explicit. /
默认判据:只有"为软件能开发/上线/运行"的内容属于这里;经营/战略/与软件无关的
规划 = OUT。此判据是默认值——需要可按项目重定义,但必须显式。

> Full methodology: see the acgm repo
> (METHODOLOGY.md). Full setup is human-driven (governance-bootstrap / §12). /
> 完整方法论见 acgm 仓库;完整搭建是人驱动的。
EOF
  note_make "AGENTS.md  (generic agent-governance directive)"
fi

# 3. CLAUDE.md — thin pointer (Principle 2: meta + pointers, never facts).
if [ -f "$TARGET/CLAUDE.md" ]; then
  note_skip "CLAUDE.md  (exists — left untouched / 已存在,未改动)"
else
  cat > "$TARGET/CLAUDE.md" <<'EOF'
# Root rules — meta + pointers, never facts / 根规则 — 元规则+指针,绝不放事实

This project uses agent-coding-governance.

- If the Claude Code plugin is installed, its SessionStart hook injects the
  grounding directive automatically — follow it. If not, the same rules live in
  `AGENTS.md`; read and follow them.
- Governance constitution: `./CONSTITUTION.md` (humans only).
- This file holds only meta-rules, pointers, and behavior constraints — never
  facts that can be re-derived from code (Principle 2).

本项目启用 agent-coding-governance。

- 装了 Claude Code 插件:SessionStart hook 会自动注入 grounding 指令,照做。
  没装:同样的规则在 `AGENTS.md`,读它并遵守。
- 治理宪法:`./CONSTITUTION.md`(仅人可改)。
- 本文件只装元规则、指针、行为约束——绝不写能从代码反推的事实(第 2 原则)。
EOF
  note_make "CLAUDE.md  (thin pointer)"
fi

echo "----------------------------------------------------------------"
echo "Done / 完成: created $CREATED, skipped $SKIPPED."
echo
echo "Next / 接下来:"
echo "  1. Fill CONSTITUTION.md — every <...>. Humans only. / 填宪法,仅人可改。"
echo "  2. Claude Code users: install the plugin for runtime auto-grounding. /"
echo "     Claude Code 用户:装插件以获得运行时自动 grounding。"
echo "  3. No plugin: point your agent at AGENTS.md (agents that honor an"
echo "     agents-file will read it automatically). / 不用插件:让你的 agent"
echo "     读 AGENTS.md(按约定读 agents 文件的 agent 会自动读)。"
echo "  4. Full governance (decision log, snapshots, tracks) is human-driven —"
echo "     run governance-bootstrap / METHODOLOGY §12. /"
echo "     完整治理(决策日志/快照/轨道)是人驱动的——走 governance-bootstrap / §12。"
