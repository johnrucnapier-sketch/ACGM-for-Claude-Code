---
name: truth-first
description: Use BEFORE writing any technical conclusion (docs, commit messages, code comments, reports) and BEFORE any irreversible, destructive or state-changing operation. 写技术结论,或做不可逆/破坏性/状态变更操作前调用。Requires file:line sourcing from the current session, bans "I think / should be / I recall", and requires the four ACGM-EVIDENCE / ACGM-CURRENT-STATE / ACGM-VERIFY-AFTER / ACGM-ROLLBACK fields with source inspection, mutation and verification in separate tool calls.
---

# Truth-First

Conversation residue, handoffs and compacted summaries drift into being treated
as current technical truth. The hooks cover a narrow mechanical subset; this
skill supplies the judgment no mechanism can infer.

## Technical claims

Every technical conclusion you write must:

- come from code, configuration, schema or runtime state read **in this session**;
- carry a concrete `file:line` when the truth source is a file;
- distinguish current fact, historical decision, inference, and open unknown;
- avoid "I think", "usually", "should be", "I recall" as substitutes for evidence.

Never copy a technical claim out of history, superseded documents, old handoffs,
transcripts, memory retrieval or version snapshots. Those establish what was once
said. They do not establish what the system is.

If a truth source cannot be read, name exactly what went unverified and stop
there. An unknown written as a conclusion is worse than an admitted gap.

**Redline:** the moment "I recall" or "should be" forms in your head, or you reach
for an old document as a citation — stop and go verify. A paragraph written
without a source gets a source or gets deleted. Never resolve a missing citation
by softening the claim into vaguer wording; vagueness is not honesty.

The PostToolUse advisory may flag a governance-file write. It does not edit the
file and it is sometimes wrong. Re-read the source and either cite or correct the
claim yourself.

## The gate — what the mechanism actually checks

Before an irreversible, destructive or state-changing operation, three conditions
must hold. They are checked structurally, from the tool call and the transcript,
because prose can be produced without evidence and structure cannot.

**1 · FIELDS** — state all four immediately before the call, each with real
content. Templates, `TBD`, `n/a`, `待定` and inherited claims do not count:

```text
ACGM-EVIDENCE:      primary source establishing each target identifier
ACGM-CURRENT-STATE: the target's state, observed now
ACGM-VERIFY-AFTER:  the specific post-action check and its success signal
ACGM-ROLLBACK:      recovery if the target or the result is wrong
```

**2 · STANDALONE** — the operation runs in its own tool call. Do not bind it to
other work with `;`, `&&`, `||`, a pipe, a redirection or a subshell, and do not
compute its target with command substitution. Source inspection, the state
change, and verification are three separate calls. Collapsed into one, ordering
and partial failure stop being auditable, and a computed target cannot be read
from the command text at all.

**3 · EVIDENCE** — a read-only tool call establishing the target must already
exist in this session, before the operation. Resolve identifiers by looking, not
by asserting.

An incomplete gate is **denied**, not merely questioned. A hook that only asks is
routed through the session's permission mode, and where that mode auto-accepts,
asking is a no-op — observed 2026-08-05, when this gate returned `ask` against a
real destructive command and the command ran anyway. Supplying the four fields
lifts the block; it does not authorize the operation. A complete gate is evidence,
the human still decides through the normal flow, and the post-action obligation
is still open.

## After the operation

Run `ACGM-VERIFY-AFTER` and read the result. Exit code zero is not verification
unless zero proves the intended state. If the session ends before verification
lands, record it as an open obligation — never as done.

## What is not yours to change

The Constitution is human-owned. Propose the amendment and the evidence; do not
edit `CONSTITUTION.md` through any agent write path, including a Bash command
that might mutate it. A plainly read-only command may inspect it; anything
compound is refused because it cannot be proven read-only.

---

# 真值优先

对话残留、交接和 compact 摘要会漂移成"当前技术真值"。Hooks 只覆盖一个很窄的机械子集,
本 skill 负责机制无法推断的判断。

## 技术结论

任何你写下的技术结论必须:

- 来自**本 Session 内**读取的代码、配置、schema 或运行状态;
- 真值源是文件时,附具体 `文件:行号`;
- 区分当前事实、历史决策、推断、仍未解决的未知;
- 不用"我觉得""通常""应该是""我记得"代替证据。

不得从历史、已被推翻的文档、旧交接、transcript、记忆检索或版本快照抄技术结论。这些
来源能证明过去说过什么,不能证明系统现在是什么。

读不到真值源时,明确说出哪一项未验证,并停在这里。把未知写成结论,比承认缺口更糟。

**红线:** 脑子里冒出"我记得""应该是",或想拿旧文档当引用 —— 立刻停下去验证。写完一段
没带来源,就补来源或删掉。**绝不用把结论改模糊的方式绕过缺失的引用;模糊不是诚实。**

PostToolUse advisory 可能标记治理文档的写入。它不会改文件,而且有时是错的。你要自己
重读源头,补引用或改结论。

## 证据门 —— 机制实际检查什么

不可逆、破坏性或状态变更操作前,三个条件必须成立。它们从工具调用和 transcript 做
**结构判定**,因为文字可以在没有证据的情况下写出来,结构不能。

**1 · FIELDS** —— 紧邻操作之前写出四个字段,各自要有真实内容。模板、`TBD`、`n/a`、
"待定"和从摘要继承的说法都不算:

```text
ACGM-EVIDENCE:      建立每个目标标识符的一手来源
ACGM-CURRENT-STATE: 刚刚观察到的目标当前状态
ACGM-VERIFY-AFTER:  具体的后验检查命令与成功信号
ACGM-ROLLBACK:      目标或结果错误时的恢复方案
```

**2 · STANDALONE** —— 操作独占一次工具调用。不得用 `;`、`&&`、`||`、pipe、重定向或
subshell 把它和其他工作绑在一起,也不得用命令替换计算它的目标。取证、状态变更、核验
是三次独立调用。挤进一条命令后,顺序和部分失败就不可审计;而被计算出来的目标,根本
无法从命令文本里读出。

**3 · EVIDENCE** —— 本 Session 内、在该操作之前,必须已经存在一次确立目标的只读工具
调用。标识符靠看,不靠断言。

四项不全的门是**拒绝**,不是"问一句"。只会 `ask` 的 hook 要经过会话的权限模式,而在自动
接受的模式下,问等于没问 —— 2026-08-05 实测:本门对一条真实破坏性命令返回了 `ask`,命令
照样执行了。补齐四个字段**解除阻断,但不构成授权**。四项齐全只是证据,人仍然通过正常流程
拍板,后验义务也仍然欠着。

## 操作之后

运行 `ACGM-VERIFY-AFTER` 并读结果。除非 exit code 0 能证明预期状态,否则它本身不算
验证。Session 在核验落地前结束的,记为未完成义务 —— 不许记成已完成。

## 不归你改的东西

Constitution 归人所有。可以提修订建议和证据,但不得通过任何 agent 写入路径修改
`CONSTITUTION.md`,包括可能写入它的 Bash 命令。明确只读的命令可以查看;任何复合命令
一律拒绝,因为无法证明它只读。
