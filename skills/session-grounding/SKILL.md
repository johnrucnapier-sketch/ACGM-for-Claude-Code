---
name: session-grounding
description: Re-ground a new, resumed or compacted Claude Code session in its actual project and task-relevant current facts. 开场、续接或压缩后核实项目与相关事实，沿用已有授权，不重复审批。
---

# Session Grounding

1. Verify the actual directory, Git root, branch/worktree, HEAD and worktree changes.
   Preserve unrelated and uncommitted work.
2. Read applicable project rules and the current task's relevant sources. History
   supplies context, never fresh runtime evidence. Inspect inherited identifiers
   before an action depends on them; do not audit every historical identifier.
3. Use the SessionStart project-state summary. It separates root rules, ledger
   presence and valid runtime policy; it proves only SessionStart ran. An absent
   layer does not authorize bootstrap, reinstall or configuration changes.
   Run doctor for missing, contradictory or changed installation evidence, not
   as a mandatory full plugin audit on every familiar task.
4. State the task scope and necessary checks briefly, reuse the existing SOP,
   then continue within the user's existing authorization. Ask only when the
   target, scope, permission or material risk is unresolved. Existing approval
   is not lost on resume, but dynamic conditions may need a fresh check.
5. Before a recognized state-changing operation, use truth-first. Source reads,
   mutation and post-verification remain separate. Fields and Gate pass-through
   are evidence, not authorization. Git commit/install/push follow the actual
   user authorization; do not add a second approval merely to finish grounding.

If a command is denied, follow the reason code and next_safe_action. For a
read-only check use the installed `scripts/acgm-explain.py` with a Bash Hook JSON
payload on stdin and the actual `--project` when outside a Claude session.
Include the actual `cwd` and `transcript_path` for evidence checks. No transcript
means no evidence, not an exemption. The inspector never executes the command;
pass-through neither certifies safety nor overrides Claude permissions. Do not
reverse-engineer Gate source or reformat an unsupported operation repeatedly.

Keep source verified, configuration verified, runtime observed and project rules
present as separate conclusions. Record material open decisions using
`decision-ledger`; do not create a routine activity log.

## 中文

- 核实当前目录、仓库、worktree、分支、HEAD 与未提交内容；保留无关改动。
- 阅读适用规则和当前任务相关真值源。历史只作背景；在动作依赖某个标识符前
  核实它，不把所有历史标识符重新审计一遍。
- SessionStart 分别说明根规则、台账、运行策略；只证明自身运行。缺一层不能
  推断全未启用，也不授权自动初始化或重装。安装证据缺失、矛盾或发生变化时
  再运行 doctor，不把全量插件审计作为每次熟悉任务的前置仪式。
- 简要说明范围及必要检查，复用 SOP，沿用已有用户授权继续。目标、范围、权限
  或实质风险不明确时才询问；续接不撤销已有授权，但动态条件须按需重新核实。
- 状态变更仍走 truth-first；取证、操作、后验分开，字段和 Gate 通过不构成授权。
  提交、安装、推送以真实授权为准，不为完成开场流程重复索取确认。
- 拒绝先看原因码及下一步。acgm-explain.py 仅检查，不执行；无 transcript 就
  没有工具证据，检查通过也不代表安全或授权。资源不支持时停止格式重试。
- 源码、配置、运行时及项目规则分别报告；只记录影响路径的决策与未决问题。
