# 通用启动话术骨架 / Generic Session-Start Phrase

> 每次开 session 第一句贴下面整块,末尾附本次具体任务。把 `<...>` 替换成你项目的路径。
> Paste the whole block as the first message of every session; append the concrete task.

```
本 session 启用 <项目名> 治理。动手前先走 grounding(session-grounding skill):

1. 我已完整读:<宪法路径，如 docs/CONSTITUTION.md> + <根规则文件，如 CLAUDE.md>。
2. 本次落在轨道:<代码 / 内容·AI行为 / 其它——按你项目轨道划分>;已加读:<对应层文档>。
3. 简要报告本任务相关现状并沿用已有授权继续；目标、范围、权限或实质风险未明时才询问:
   - 轨道:<…>
   - git log + git status:<粘贴实际输出>
   - 我实际读代码看到的相关结构(带 path:line,不凭印象):<…>
   - 我打算改的文件清单:<具体路径列表>
   - 我打算的执行步骤:<…>
4. 改完我会跑:<你的验证脚本/测试命令>
5. 收尾给报告；commit、安装、推送各自遵守真实用户授权，不重复索取已经给出的确认。

本次具体任务:<在此写本次要做的事>
```

## 场景变体 / Scenario variants
- **续接半截活**:第 3 条额外报告"上一个 session 停在哪、留下哪些未完成/未验证项"。
- **跨切面契约改动**:额外声明影响面 + 验证方式 + 标注需人审批后才能合并。
- **不可逆/破坏性操作**:走 truth-first——核实目标、当前状态、恢复方案及已有授权；授权缺失或范围改变时才询问，动态条件按需重新核实。
