---
name: session-grounding
description: Use at the START of every new, resumed, cleared or compacted session, and when picking up half-done work in a governed project — before taking ANY action. 在每个新开/续接/clear/compact 后的 Session,以及接手半截工作时,动手前先走此流程。Read current truth sources, identify track and scope, report five items and WAIT for human confirmation. A summary, handoff or memory is historical evidence, never current code truth.
---

# Session Grounding

A new or resumed session rebuilds context from handoffs, memory and compacted
summaries — and that reconstruction always distorts. This ritual catches the
distortion *before* code is written, where it costs an order of magnitude less
to fix.

**Restate first, then act.** That is the whole point.

## Before acting

1. **Check that governance is actually running.** Run `acgm doctor`. An installed
   plugin record is not proof that the hooks loaded in this session. If doctor
   reports anything other than healthy, say so — do not claim governance is on.
2. **Read the constitution and the root rules file in full.** Not skim-read.
   Follow their pointers to where truth actually lives; the root rules are a map,
   never a cache of technical fact.
3. **Identify the worktree, branch, track and scope for this task.** One session
   works in one track. Cross-track work is split into explicit consecutive stages.
4. **Re-read current code, configuration and Git state now.** A handoff,
   transcript, memory entry, compacted summary or prior report tells you what was
   once said or decided. It never tells you what the system is.
5. **Report these five items, then WAIT for human confirmation before editing:**
   - track and scope;
   - current `git log` and `git status`;
   - the relevant structure you saw *by reading current sources in this session*;
   - the exact list of files you intend to change;
   - the execution and verification steps you intend to run.

After changes, run the declared checks. Close with a report and a commit draft,
and wait for human approval before committing.

## Four states, never collapsed

Keep these apart in every report. Collapsing them is how "done" gets claimed for
work that never took effect:

| State | What it proves |
|---|---|
| Source verified | the bytes you read are what you think they are |
| Configuration verified | a record or manifest says the thing is set up |
| Runtime activated | the running process actually loaded it |
| Project governed | this repository's rules are present and current |

Configuration verified does not imply runtime activated. A `--version` string,
an install record, or a cache directory is configuration. Observed hook output
in this session is activation.

## Handing off to the gate

Before a recognized irreversible, destructive or state-changing operation,
switch to:

```text
/acgm:truth-first
```

Do the read-only source check in its own call first, then carry the four fields
as comment lines on the command itself. They are evidence, not authorization:
the human still decides, and the post-action check remains owed.

---

# Session 启动 Grounding

新开或续接的 Session 靠交接、记忆和 compact 摘要重建上下文,重建必然失真。这套流程
在**写代码之前**把失真抓出来——那时修正便宜一个数量级。

**先转述,再动手。** 这就是全部要义。

## 动手之前

1. **先确认治理真的在运行。** 运行 `acgm doctor`。安装记录不能证明本 Session 加载了
   hooks。doctor 未报健康时如实说出,不得声称治理已生效。
2. **完整读宪法和根规则文件。** 不是跳读。沿它们的指针找到真值实际所在;根规则是地图,
   永远不是技术事实的缓存。
3. **识别本任务的 worktree、分支、轨道和范围。** 一个 Session 只在一个轨道;跨轨道工作
   拆成明确的连续阶段。
4. **当下重读代码、配置与 Git 状态。** 交接、transcript、记忆、compact 摘要或旧报告,
   只能证明过去说过什么、决定过什么,不能证明系统现在是什么。
5. **报告以下五项,然后等人确认再编辑:**
   - 轨道和范围;
   - 当前 `git log` 与 `git status`;
   - **本 Session 内实际读取当前真值源**后看到的相关结构;
   - 拟修改的准确文件清单;
   - 拟执行与验证的步骤。

改完运行已声明的检查。收尾给报告和 commit 草稿,等人批准后再提交。

## 四种状态,永不合并

每次报告都要分开。把它们混作一谈,正是"其实没生效"却被报成"已完成"的成因:

| 状态 | 它能证明什么 |
|---|---|
| 源已验证 | 你读到的字节确实是你以为的东西 |
| 配置已验证 | 某条记录或 manifest 声称已装好 |
| 运行时已激活 | 正在运行的进程确实加载了它 |
| 项目已治理 | 本仓库的规则存在且是当前版本 |

配置已验证不蕴含运行时已激活。`--version` 输出、安装记录、缓存目录都属于配置;本
Session 内观察到的 hook 输出才是激活。

## 转交证据门

执行已识别的不可逆、破坏性或状态变更操作前,切换到:

```text
/acgm:truth-first
```

先用独立调用做只读取证,再把四个字段作为**命令自身的注释行**带上。它们是证据,不是
授权:人仍然要拍板,后验核验义务也仍然欠着。
