---
name: decision-ledger
description: Use throughout a session to track open decision threads and draft them to `.governance/claims/` when they close. 会话全程使用:跟踪开放的决策线程,线程闭合时起草到账本。Records what was decided and why, at the moment it is decided, so the reasoning survives a lost account, a deleted transcript or a compaction. Drafting is automatic and free; promoting a draft into a decision requires a human.
---

> **Advisory clause · single direct event of support, pending second-evidence
> confirmation** — grace period ≤ 30 days from 2026-08-06. Supporting event:
> transcript retention swept three months of history off a working machine
> (CASES.md, EVIDENCE E-028). If a second independent event is not produced in
> that window, downgrade this mechanism to a Meta-observation or remove it.

# Decision Ledger

A session's reasoning lives in the transcript. The transcript lives in vendor
storage, on a retention timer, under an account. Any one of those three can
disappear without warning, and the code that survives does not say *why* it is
shaped the way it is.

This skill writes the *why* into Git, at the moment it is decided.

## What it is not

It is not a log. It does not record tool calls, file edits or commands — those
are recoverable from the transcript and from Git, and recording them again buys
nothing while costing attention.

**Economy rule.** Do not aim for complete capture. Record only what affects a
decision or a path. When "record everything" and "record accurately" conflict,
take accuracy and drop coverage.

## Track threads, not decisions

"Was that a decision?" is an interpretive judgment, and a poor one to build on.
Track something enumerable instead:

> An **open thread** is a question that has been raised and not yet converged.
> A **decision** is an open thread collapsing from several candidates to one.

Threads can be listed, counted and carried across sessions. Decisions cannot.
This also fixes granularity for free: a feature discussed over five exchanges is
**one thread**, closing once, recorded once — not five records.

Keep the live thread list in `.governance/OPEN_THREADS.md`. It is a state file:
rewrite it, do not append to it. Closed threads leave it and live on as claims.

## When a thread closes

Only these four signals may trigger a draft. Each is observable, not felt.

| Signal | Shape |
|---|---|
| `human_ruling` | the human ruled: "that's settled", "go with this", "I accept" |
| `topic_moved` | the next message is about a different subject |
| `entered_implementation` | talk of whether/how became an actual edit or command |
| `objection_closed` | proposed → objected → revised → no further objection |

**Weak signals may not trigger a draft on their own**: many exchanges spent, a
numbered list appeared, the agent finds it important, words like "architecture"
were used. They may raise a thread's priority. They never establish closure.

Note that `topic_moved` — the strongest signal in practice — can only be observed
once the *next* topic starts. The best moment to detect closure is therefore the
moment the human is already talking to you. Mechanism and courtesy coincide here;
the ride-along rule below is built on it.

## Draft immediately, confirm later

These two are separate operations, and conflating them is the failure this skill
exists to prevent.

| | When | Who | Cost of skipping |
|---|---|---|---|
| **Draft** → `claims/` | thread closes | you, silently | none |
| **Promote** → `decisions/` | human confirms | **human only** | none — the draft stays |

Drafting never waits for confirmation. If an account is lost an hour later,
everything detected is already on disk, marked unconfirmed — which is exactly
what it is.

Confirmation is therefore not a save button. It is a stamp.

## The ride-along rule

**A confirmation request must never become an interruption of its own.** It may
only attach to something you were already going to send.

1. **Attach to your next question.** Append one line: *"Also — I drafted C-…
   about X earlier; confirm?"*
2. **Attach to your next report**, if you have nothing to ask.
3. **Otherwise accumulate.** Say nothing. Keep drafting.
4. **SessionEnd lists what is unconfirmed.** The mechanism, not you.

Never send a message solely to request confirmation, never interrupt work in
progress, and never re-ask a thread the human declined to answer.

**Frequency.** Bundle — one ride-along may carry several drafts. At most three
ride-alongs per session; past that, accumulate and let SessionEnd report. More
than five is a design smell in this skill, not a threshold to raise.

## What is actually enforced

State this honestly, because the guarantee is narrower than it looks. A hook
cannot tell "the human agreed" from "the agent decided the human agreed".

**Mechanically checkable:**

- every file in `decisions/` names an existing `claims/` file in `From:`
- an existing decision's body is not rewritten — only a supersession note appends
- the `Confirmed by:` field is present and non-empty

**Not mechanically checkable:** whether the human actually said it.

That last one belongs to audit. It is not undefended: promotion is a Git-visible
file creation, surfaced in `git status`, in the next session's grounding report,
and in the SessionEnd list. ACGM promises that a violation is **visible,
recorded and traceable** — not that it is impossible.

## Where records live

```
.governance/
├── OPEN_OBLIGATIONS.md   # verifications owed          (existing)
├── OPEN_THREADS.md       # rulings owed                (state file, rewritten)
├── claims/               # drafted by the agent, unconfirmed
└── decisions/            # confirmed by the human — these are ADRs
```

`claims/` may be written from any worktree; ids are date-based and cannot
collide. `decisions/` is governance output, so by Principle Seven it is authored
**on the trunk only** — which also removes any `ADR-NNNN` numbering collision.

Use `templates/CLAIM._TEMPLATE.md` and `templates/ADR._TEMPLATE.md`.

Writing a file into `.governance/` does not put it in the repository. Do **not**
commit on your own — Principle Six reserves that for the human. SessionEnd
records uncommitted ledger changes as an outstanding obligation instead.

## Resuming

`OPEN_THREADS.md` is what survives a compaction or a new session. On grounding,
read it: a thread still open from last time is one nobody ruled on. The last
thread of any session never gets a `topic_moved` signal — there is no next
topic — so the following session's grounding is the only place it can be caught.

---

> **建议性条款 · 单次直接事件支撑,待第二独立证据确认** —— 过渡期自 2026-08-06 起
> ≤ 30 天。支撑事件:transcript 保留期在一台在用机器上扫掉了三个月历史(见
> `CASES.md`、证据 E-028)。窗口内补不到第二个独立事件,则降级到元观察或删除。

# 决策账本

一个 session 的推理过程活在 transcript 里。而 transcript 活在厂商存储里、活在一个
保留期计时器上、活在一个账号底下。这三样任何一样都可能毫无预警地消失,而幸存下来的
代码,并不会说明它**为什么**长成这样。

这个 skill 把"为什么"在**决定发生的当下**写进 Git。

## 它不是什么

它不是日志。它不记录工具调用、文件改动或命令——那些从 transcript 和 Git 里都能恢复,
再记一遍毫无收益,却要花掉注意力。

**经济性原则。** 不追求完整保留,只记录对**决策与路径**有影响的信息。当"记全"和
"记准"冲突时,取准舍全。

## 跟踪线程,不跟踪决策

"刚才那个算不算决策"是解释性判断,不适合当地基。换一个可枚举的对象:

> **开放线程** = 一个已被提出、尚未收敛的问题。
> **决策** = 一个开放线程从多个候选收敛成一个。

线程可以列举、计数、跨 session 携带,决策不能。这同时免费解决了粒度问题:一个功能
聊了五轮,是**一条线程**,闭合一次,记一条——不是五条。

当前线程表放 `.governance/OPEN_THREADS.md`。它是状态文件:**重写,不追加**。闭合的
线程离开它,以草案形式继续存在。

## 什么时候算闭合

只有以下四个信号可以触发起草。每一个都是**可观察的**,不是"感觉到的"。

| 信号 | 形态 |
|---|---|
| `human_ruling` | 人给出裁定:"就这么定""按这个走""我接受" |
| `topic_moved` | 下一条消息已经在讲别的主题 |
| `entered_implementation` | 从"要不要/怎么做"变成了实际的编辑或命令 |
| `objection_closed` | 提出 → 反对 → 修正 → 不再有反对 |

**弱信号不得单独触发起草**:聊了很多轮、出现了编号清单、agent 觉得重要、用了"架构"
这类词。它们可以提高线程的优先级,但永远不构成闭合。

注意 `topic_moved`——实践中最强的信号——**只能在下一个话题开始时被观察到**。也就是说
检测闭合的最佳时机,正是人已经在跟你说话的时刻。机制和礼貌在这里重合,下面的搭便车
规则就建立在这一点上。

## 立即起草,稍后确认

这是两个独立操作。把它们合并,正是这个 skill 要防的失效。

| | 何时 | 谁 | 跳过的代价 |
|---|---|---|---|
| **起草** → `claims/` | 线程闭合时 | 你,静默进行 | 无 |
| **升级** → `decisions/` | 人确认时 | **只有人** | 无——草案还在 |

起草**永不等待确认**。如果一小时后账号丢了,已检测到的东西全都在磁盘上,标着"未确认"
——而它本来就是未确认的。

所以确认不是"保存"按钮,是"盖章"。

## 搭便车规则

**确认请求永远不得自成一次打扰。** 它只能挂在你本来就要发出的东西上。

1. **挂在下一次提问上。** 末尾追加一行:*"顺便,前面 X 我记了条草案 C-…,认吗?"*
2. **挂在下一次汇报上**,如果没有要问的。
3. **否则就攒着。** 什么都不说,继续起草。
4. **SessionEnd 列出未确认的。** 那是机制的事,不是你的事。

绝不为了确认而单独发消息,绝不打断进行中的工作,绝不对人已经不答的线程二次追问。

**频率。** 打包——一次搭车可带多条草案。**单 session 最多三次搭车**,超了就攒着让
SessionEnd 报。超过五次是这个 skill 的设计气味,不是可以调高的阈值。

## 到底强制了什么

这一节要说实话,因为保证比看上去窄。hook 分不清"人同意了"和"agent 认为人同意了"。

**可机械检查:**

- `decisions/` 里每个文件的 `来源草案:` 指向一个**存在的** `claims/` 文件
- 已有决策的正文不被改写——只能追加取代说明
- `确认原话:` 字段存在且非空

**不可机械检查:** 那句话人是否真的说过。

最后一条归审计层。但它并非没有防线:升级是一次 **Git 可见**的文件新增,会出现在
`git status`、下一个 session 的 grounding 报告、以及 SessionEnd 清单里。ACGM 承诺的
是让违规**可被显化、可被留痕、可被追溯**,不是让违规不可能。

## 记录放在哪

```
.governance/
├── OPEN_OBLIGATIONS.md   # 欠的验证          (已有)
├── OPEN_THREADS.md       # 欠的裁定          (状态文件,重写)
├── claims/               # agent 起草,未确认
└── decisions/            # 人已确认 —— 就是 ADR
```

`claims/` 任何工作树都可以写,编号按日期,不会冲突。`decisions/` 是治理产物,按第七
原则**只在主干 author**——这也顺带消掉了 `ADR-NNNN` 的编号冲突问题。

使用 `templates/CLAIM._TEMPLATE.md` 和 `templates/ADR._TEMPLATE.md`。

**把文件写进 `.governance/` 不等于它进了版本库。** 不要自行提交——第六原则把提交留给
人。SessionEnd 会把未提交的账本改动记成一条未了义务。

## 续接

`OPEN_THREADS.md` 是能穿过 compact 和新 session 的东西。grounding 时读它:上次还开着
的线程,就是没人裁定的线程。**任何 session 的最后一条线程永远等不到 `topic_moved`**
——后面没有下一个话题了——所以下一个 session 的 grounding 是唯一能捞到它的地方。
