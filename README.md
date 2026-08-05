# ACGM for Claude Code

**Agent Coding Governance Methodology — a governance system for multi-session, long-horizon AI development, built and validated on Claude Code.**

[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSING.md) [![Docs: CC--BY--4.0](https://img.shields.io/badge/docs-CC--BY--4.0-blue.svg)](LICENSING.md) [![Dual-license](https://img.shields.io/badge/license-dual--track-lightgrey.svg)](LICENSING.md)

> English first (full). 中文完整版在下半部分 — scroll past the English.

---

> **One sentence:** long-horizon AI-driven development **rots structurally** — unless
> there is governance.
>
> Distilled from a real project: **months of work, several hundred thousand lines,
> shipped to an app store** — many versions, dozens of sessions, and about 2B tokens
> of mistakes. What you get: an agent that takes fewer wrong turns, makes fewer
> fabricated claims, and does fewer destructive actions across long timelines — at
> the cost of it stopping to verify more. It ships as a Claude Code plugin
> (runtime-automatic). A generic, plugin-free scaffold is included for other setups.
>
> **In progress, and meant to shrink.** As models absorb what this used to enforce,
> those mechanisms are removed rather than kept out of habit.

## What this is / why you need it

Doing **multi-session, long-horizon, possibly multi-person / multi-branch**
development with Claude Code (or a comparable AI coding agent), past a certain scale
you inevitably hit:

- a new session doesn't know what happened before; it rebuilds from handoff docs →
  necessarily distorted
- the AI **fabricates technical conclusions** from conversation residue instead of
  reading code ground truth
- an old plan is overturned but unmarked; the next session reads it and goes wrong
- governance/truth lives on a feature branch, the trunk rots, a new session on the
  old trunk reads all-wrong

**This is not operator error, it is the natural cost of this workflow.** This repo
does not eliminate rot (impossible) — it makes rot **visible, interceptable,
reversible.**

## Core: the four drift types (the mental model most worth taking with you)

First learn to **recognize which type it is**, then talk about how to fix it.

| Drift | What's wrong | Defense |
|---|---|---|
| **① Implementation** | detours when the tech is hard (hand-rolled polyfill / downgrade / silent error swallow) | Detour ban: root-cause first |
| **② Cognitive** | writes docs from impression, doesn't verify | Truth-first: conclusions carry `file:line`, ban "I recall / should be" |
| **③ Structural placement** | governance on the wrong branch, trunk rots | govern only on the trunk; trunk never allowed to rot |
| **④ Scope** | content that shouldn't be in the repo (ops/strategy) creeps in | scope boundary: for software to ship = IN, for anything else = OUT (a default you may redefine — see METHODOLOGY §10) |

> Real, desensitized cases for each drift type: see **[CASES.md](CASES.md)**.

## Real-world hit rate (what is measured, and what is not)

In a **single 2–3 hour continuous work session** in May 2026, this methodology
triggered **7 distinct drift detections** — including one data-migration bug that
would have **silently dropped real rows** (caught at the instant of the Bash
command), and a "your premise is false" block where a spec disagreed with code
truth. One recorded case is an **external AI's modification plan caught by the
local governance before merge**.

**That figure is a single window from May and has not been re-measured since.**
The project it came from has run for months longer, and the rate is now much
higher — but **[CASES.md](CASES.md) has not kept pace with the usage**, so the
honest position is: the recorded cases are a floor, not an average, and nobody
should treat the number as a benchmark.

Assess the rate on your own project. If you install this and nothing ever
triggers, one of three things is true: your project isn't yet at the scale that
needs it, it isn't wired correctly, or the gate simply had no destructive
operation to catch. Those look identical from the outside, which is why
`acgm_activity.py` reports counts **with their denominator**.

## Quick start

### Claude Code (the plugin — runtime-automatic)

Two steps (honest — not literally one command):

1. Register the marketplace:
   ```
   /plugin marketplace add johnrucnapier-sketch/ACGM-for-Claude-Code
   ```
2. Install the plugin (from the `/plugin` menu, or):
   ```
   /plugin install acgm@acgm
   ```

The same two steps from a terminal, which is the form this project's CI runs on
every push:

```
claude plugin marketplace add johnrucnapier-sketch/ACGM-for-Claude-Code
claude plugin install acgm@acgm
```

**Plugin syntax changes between Claude Code versions.** If a command differs from
what is written here, open the `/plugin` menu and install from the marketplace you
added in step 1.

**Then start a new session.** Hooks are bound when a session starts; installing or
upgrading mid-session does not change the session you are in. This catches people
out, including the author — repeatedly, while building v0.4.

*You'll know it worked when:* at the next session start the SessionStart hook
injects a grounding directive — the agent acknowledges governance and runs the
5-step grounding (or, if the project has no governance docs yet, points you to
`governance-bootstrap`) instead of diving straight into edits.

*And check it, don't assume it.* `claude plugin list` showing **enabled** is
configuration, not activation — a plugin can be registered and still fail to load:

```
sh scripts/acgm-doctor.sh            # configuration: manifest, hooks, cache drift
python3 scripts/acgm_activity.py     # activation already on record, with denominators
```

Doctor will not tell you the plugin is running, because a subprocess cannot observe
the session that started it. Only hook output you see in your own session proves
that. This distinction is not pedantic: v0.1 of this plugin was published for three
months in a state where **no clean install could load it**, while appearing healthy
on the author's machine (CASES.md Case 10).

### Without the plugin (generic scaffold)

If you are not using the Claude Code plugin, a plugin-free scaffolder drops the
governance files into any project:

```
git clone https://github.com/johnrucnapier-sketch/ACGM-for-Claude-Code
sh ACGM-for-Claude-Code/scripts/governance-init.sh /path/to/your-project
```

It writes `CONSTITUTION.md` + `AGENTS.md` (a generic agent-governance directive) +
a `CLAUDE.md` pointer (**idempotent & non-destructive** — existing files are
skipped, never overwritten). The script is reviewable; `curl|sh` is deliberately
avoided. This is a *static scaffold*, not a runtime: whether the directive is
auto-applied depends on whether your agent reads an agents-file by convention. The
methodology is tool-agnostic in principle — adapt the generic scaffold to your setup.

### Claude Code only, by design — and where Codex went

**This project is designed entirely for Claude Code.** The mechanisms here — the
hooks, the structural gate, doctor, the activity report — are written against
Claude Code's plugin and hook contracts, and have been exercised only there.

An early version bundled a Codex path. It was dropped in May 2026 for a plain
reason: the author was not using Codex enough to have validated it, and shipping
an unvalidated "works there too" claim would be the ② cognitive drift this project
exists to stop. That was a statement about the author's evidence, not about Codex.

Codex support now lives in its own repository, because **the working logic differs
enough that one plugin serving both would serve neither well**:

> **[ACGM-for-Codex](https://github.com/johnrucnapier-sketch/ACGM-for-Codex)**

The author intends to maintain both as time allows. They share the methodology and
not the mechanism, and **nothing measured in this repository validates that one**.
For any other agent, take the generic scaffold and the principles and adapt them.

### How "automatic" works (stated honestly)

- **Four hooks are the runtime mechanism.** `SessionStart` injects grounding every
  session. `PreToolUse` holds destructive Bash behind a structural gate.
  `PostToolUse` advises on governance-doc writes and changes nothing.
  `SessionEnd` reports post-action checks the session is walking away from.
  Skills are invoked by the Skill tool; they do not auto-fire.
- **The gate checks structure, not wording.** It requires four named fields carried as
  comment lines **on the command itself**, the operation isolated in its own tool
  call (no `;`, `&&`, pipe, or computed target), and a read-only call already
  present in the session. All
  three are decided from the tool call and the transcript, so none can be
  produced by writing text. An incomplete gate is **denied**: a hook that only
  asks is routed through the session's permission mode, and an auto-accepting
  mode turns asking into a no-op. Supplying the fields lifts the block; the human
  still decides through the normal flow. Evidence is never authorization.
- **`sh scripts/acgm-doctor.sh` tells you what is actually wired**, and refuses to
  claim what it cannot prove: it reports runtime activation as *not provable from
  here*, because doctor is a subprocess and cannot observe the session that ran it.
- **`python3 scripts/acgm_activity.py` answers the question doctor cannot** — did
  the plugin actually do anything, in this project or any other? It reads each
  session's recorded hook output, keyed by tool call, never by searching the
  transcript for text the agent may simply have quoted. Counts come with their
  denominator, because "the gate never fired" and "the gate is not installed"
  look identical until you know how many chances it had. The signal worth acting
  on is neither count: it is a destructive call with **no** gate decision against
  its id.
- The generic scaffold only writes static files; it is not a runtime.
- Either way, what gets wired is auto-grounding + a constitution skeleton. Full
  governance (decision log / snapshots / tracks) is **human-driven**: invoke
  `governance-bootstrap` or follow `METHODOLOGY.en.md` §12 by hand.

## The eight principles (full text: `METHODOLOGY.en.md`)

1. Store content layered by lifecycle (constitution / decision log / snapshot /
   version archive / contract / live handoff)
2. The project root rules file = meta-rules + pointers + behavior constraints,
   **never facts**
3. Truth-first (the absolute version, no grey zone) — incl. its corollary:
   summaries are never code-truth
4. The session-start grounding ritual (verify before you act)
5. Don't over-execute (expose ambiguity, don't barrel through; hard checkpoint
   before destruction)
6. Isolate work by track (don't mix cognitive contexts / verification methods)
7. One trunk, never rotting — incl. its corollary: worktree discipline
8. Scope boundary (explicit IN/OUT — default rule, redefinable per project)

## Repo structure

```
README.md                          ← what you're reading (WHY + index); English then 中文
METHODOLOGY.md / METHODOLOGY.en.md ← full methodology (8 principles + bootstrap + failure modes)
CASES.md                           ← real, desensitized drift-correction cases
.claude-plugin/
  plugin.json                      ← this repo IS a Claude Code plugin
  marketplace.json                 ← for /plugin marketplace add install
hooks/hooks.json                   ← SessionStart + PreToolUse + PostToolUse + SessionEnd (the automatic layer)
scripts/grounding-inject.sh        ← SessionStart: injects a thin grounding directive → skills
scripts/pretool-destructive-bash.sh ← PreToolUse: cheap destructive-command filter
scripts/acgm_gate.py               ← the structural gate itself, and the SessionEnd obligation report
scripts/post-tool-truth-first.sh   ← PostToolUse: advisory on governance-doc writes; edits nothing
scripts/sessionend-obligations.sh  ← SessionEnd: unverified post-action promises
scripts/acgm-doctor.sh             ← health check; reports activation as not provable from a subprocess
scripts/acgm_activity.py           ← activation already on record, across projects, with denominators
scripts/governance-init.sh         ← plugin-free generic scaffold: writes CONSTITUTION/AGENTS/CLAUDE pointer
scripts/drift-check.sh             ← static drift scanner (run manually or in CI)
tests/                             ← contract + behaviour tests, hermetic (run with CLAUDECODE set and unset)
CHANGELOG.md / EVIDENCE.md         ← release history; maturity register for every claim
skills/
  session-grounding/SKILL.md       ← invoke at: session start/resume — 5-step grounding + report first
  truth-first/SKILL.md             ← invoke at: before a technical conclusion / irreversible op — force sources
  governance-bootstrap/SKILL.md    ← invoke at: bootstrap governance from zero — human-driven 8-step checklist
templates/                         ← fully blank generic skeletons, zero business
  CONSTITUTION.skeleton.md  ADR._TEMPLATE.md  SESSION_START.skeleton.md  drift-check.stub.js
LICENSING.md / LICENSE-DOCS / LICENSE-CODE  ← dual-track: docs CC-BY-4.0, code MIT
```

## Adaptation guide: take as-is vs. must adapt to your project

**Take as-is (general skeleton)**: the four-drift classification / the eight
principles / the layered structure / the bootstrap recipe / the self-check redlines.

**Must redesign for your project (copying = another kind of drift)**:
- how tracks are split (depends on where your project's core value is, how many
  cognitive contexts)
- the concrete IN/OUT scope-boundary list (and, if needed, the IN/OUT criterion
  itself — it is a default, see METHODOLOGY §10)
- exactly which protocols your cross-cutting contracts are
- the concrete content of the redlines (decided by your product/compliance)

> Principles are the skeleton, migratable; the flesh is your project's own. Don't copy
> someone else's track/contract list.

## Real background (the strongest credibility)

This was not distilled from a toy. It comes out of a **months-long, several-hundred-
thousand-line application that shipped to an app store**, built with an agent across
dozens of sessions, many versions, and repeated requirement changes. Over that
span the methodology **measurably improved stability and reduced errors** in exactly
the place long projects fail: the second month, the fifteenth session, the third
time a requirement moved.

It also **committed drift ② against itself while being built** — the builder copied
a pile of technical conclusions out of old handoff docs without reading the code,
and was caught in the act by the project owner. That is the proof, not an
embarrassment: **discipline is not for "other people", it is for you, every single
time you write something right now.** Writing a real incident permanently into the
governance file as a cautionary case is worth ten abstract rules.

### Status: in progress, and deliberately shrinking

This is a **live project, not a finished framework**, and two forces are pulling on
it at once.

**Models keep absorbing what the tooling used to supply.** With the capability jump
in July 2026, some of what this plugin enforces is becoming native behaviour. The
plan is to **progressively remove what the model has internalised** rather than keep
it out of habit — a governance layer that never shrinks eventually becomes the
overhead it was meant to prevent. Every mechanism here should have to re-justify its
existence as models improve.

**It is tuned to what the author has actually run.** A great deal of the adaptation
in it was worked out against **Opus 4.6 – 4.8**. The author has only just started
working on **Opus 5**, so the fit there is still being learned, and this project will
keep changing as that experience accumulates. Treat version numbers here as a record
of what has been tried, not as a claim of general coverage.

## Origin — why this exists

> This section is the author's personal voice — edit it freely to your own comfort.

I have perfectionist tendencies, and I have lived with significant anxiety for a long
time. For years I could no longer do the kind of long-form writing I did as a
student — the information and thinking in my head far outran the speed at which I
could put it on paper; my execution could not keep up with my ideas. In real work, I
always felt boxed in by my own limitations.

The AI / agent era felt like a shackle coming off: the very weaknesses — "thinking
too much, writing too slowly" — turned into strengths. Wide-ranging ideas could
combine with an agent and grow into things I could never have produced alone.

Over a long stretch of agent-coding practice, hitting pitfall after pitfall, I
gradually distilled into this methodology the answer to one question: how do you keep
an agent consistent — making fewer mistakes, taking fewer wrong turns — across many
sub-projects, ultra-long timelines, heavy iteration, and changing requirements? On my
own projects it works well; and because I am risk-averse by nature, this methodology
also makes the agent more cautious, with fewer destructive actions.

I am open-sourcing it so that people doing long-horizon development with an AI coding
agent don't have to fall into the same pits I did. The principles are the
skeleton — take them and grow your own project's flesh on them.

## License / maintenance stance

- **License: dual-track** — the methodology/docs (`METHODOLOGY*.md`, `README.md`,
  `CASES.md`, `CONTRIBUTING.md`, the prose of each `SKILL.md`) under **CC-BY-4.0**;
  the code/mechanical parts (`scripts/`, `hooks/`, `templates/`, `.claude-plugin/`)
  under **MIT**. See `LICENSING.md`.
- **Cost (untested, the author's judgment):** it likely consumes *more* tokens (more
  reading code / verifying / restating / stopping to confirm), but buys fewer errors
  and fewer wrong turns, compressing the most expensive part — rework. The author is
  not token-constrained and has not measured it; assess it on your own project.
- **Maintenance:** a methodology share — issues/PRs welcome, but **self-adaptation is
  the norm; no heavy support promised.**

## Authors and acknowledgements

- **johnrucnapier-sketch** — methodology, direction, and every go/no-go decision.
- **Claude Opus 5** — co-author of the v0.4–v0.6 rebuild: the structural gate,
  doctor, the activity report, the test suites, and the case and evidence entries
  written from what went wrong while building them.

The commits carry `Co-Authored-By: Claude Opus 5`. GitHub's contributor graph is
built from author emails that resolve to accounts, so it will not list a model —
which is why the credit is stated here rather than left to be inferred from a
graph that structurally cannot show it.

Worth recording plainly, since this project is about not overclaiming: most of the
defects fixed in v0.4–v0.6 were **introduced** during that same rebuild, by the
same co-author, and were caught by reading recorded evidence rather than by being
avoided. The gate denying its own author's commands, repeatedly and correctly, is
the closest thing here to a validation.

Distilled from the governance practice of a real long-horizon AI-driven development
project. All business specificity stripped — this repo **contains, and will never
accept,** any concrete project's business/confidential content (this is itself an
application of §④, the scope boundary).

---
---

# 中文版(完整)

# Agent Coding Governance —— AI 多会话开发治理体系

**面向多会话、长周期 AI 开发的治理体系——在 Claude Code 上构建并验证。**

> 英文完整版在上半部分;以下为中文完整版。

---

> **一句话:** AI 驱动的长周期开发会**结构性地腐化**——除非有治理。
>
> 提炼自一个真实项目:**跨度数月、几十万行代码、已上线应用市场**——多个版本、数十
> session、约 20 亿 token 的踩坑。你能得到的:在长周期里,agent 走错路更少、编造结论
> 更少、破坏性动作更少——代价是它会更频繁地停下来核实。以 Claude Code 插件形式分发
> (运行时自动);另附一个无需插件的通用脚手架供其它场景。
>
> **进行时,而且以收缩为目标。** 模型内化掉的能力,就从这里移除,而不是出于惯性留着。

## 这是什么 / 为什么需要

用 Claude Code(或同类 AI 编码 agent)做**多会话、长周期、可能多人/多分支**的开发,
到一定规模后必然遇到:

- 新 session 不知道前面发生过什么,靠交接文档重建 → 必然失真
- AI 整理文档时凭对话残留**编造技术结论**,不去读代码真值
- 旧方案被推翻但没标记,下个 session 读到就走错
- 治理/真值长在某功能分支,主干腐化,新 session 落旧主干读到全错

**这不是操作失误,是这套工作流的天然成本。** 本仓库不消灭腐化(不可能),而是让它
**显性化、可拦截、可回滚**。

## 核心:四类漂移(最值得带走的心智模型)

先学会**识别是哪一类**,再谈怎么修。

| 漂移 | 错在哪 | 防线 |
|---|---|---|
| **① 实施层** | 技术不通就绕路(自写 polyfill / 降级 / 静默吞错) | 绕行禁令:先 root cause |
| **② 认知层** | 写文档凭印象,不验证真值 | 真值优先:结论必带 `文件:行号`,禁"我记得/应该" |
| **③ 结构放置** | 治理住错分支,主干腐化 | 治理只在主干 author;主干永不准腐化 |
| **④ 范围** | 不该进仓库的内容(企业经营/战略)混进来 | 范围边界:为软件上线=IN,为别的=OUT(默认判据,可按项目重定义——见 METHODOLOGY §10) |

> 每类漂移的真实脱敏案例见 **[CASES.md](CASES.md)**。

## 实际命中率(测到了什么,以及没测什么)

2026 年 5 月的**一次 2–3 小时连续工作**里,这套方法论触发了 **7 次明确的漂移检测**
——其中一次是会**静默丢失真实数据行**的数据迁移 bug(在 Bash 命令那一刻被拦),还有
一次"你的前提不成立"阻塞(spec 与代码真值不符)。其中一例是**外部 AI 写的修改方案在
合并前被本地治理拦下**。

**这个数字只是 5 月的一次窗口,此后没有再测过。** 它来自的那个项目又跑了好几个月,
实际命中率已经**远高于此**——但 **[CASES.md](CASES.md) 没有跟上使用进度**。所以如实
说:已记录的案例是**下限,不是平均值**,任何人都不该把这个数字当基准。

频率请在你自己项目上判断。如果你装上后什么都没触发,只有三种可能:项目还没到需要它
的规模、没装对、或者根本没出现过可拦的破坏性操作。**这三种从外面看一模一样**——这
正是 `acgm_activity.py` 报告计数时**必带分母**的原因。

## 快速开始

### Claude Code(插件——运行时自动)

两步(老实说,不是字面上的一条命令):

1. 注册 marketplace:
   ```
   /plugin marketplace add johnrucnapier-sketch/ACGM-for-Claude-Code
   ```
2. 安装插件(用 `/plugin` 菜单,或):
   ```
   /plugin install acgm@acgm
   ```

同样两步的终端形式,本项目的 CI 每次推送都在跑这个形式:

```
claude plugin marketplace add johnrucnapier-sketch/ACGM-for-Claude-Code
claude plugin install acgm@acgm
```

**plugin 语法会随 Claude Code 版本变化。** 若与这里写的不同,就打开 `/plugin` 菜单,
从第 1 步加的 marketplace 里装。

**然后开一个新会话。** hook 在会话启动时绑定,**中途安装或升级不会改变你当前所在的
会话**。这一点很坑人,作者本人在做 v0.4 的过程中反复栽在上面。

*成功的样子:* 下次 session 启动时,SessionStart hook 会注入一段 grounding 指令——
agent 会先确认治理、走 5 步 grounding(或在项目还没治理文档时,引导你调
`governance-bootstrap`),而不是直接埋头改代码。

*但要去查,不要假设。* `claude plugin list` 显示 **enabled** 是**配置**,不是**激活**
——插件可以注册成功却加载失败:

```
sh scripts/acgm-doctor.sh            # 配置侧:manifest、hooks、缓存漂移
python3 scripts/acgm_activity.py     # 已记录的激活情况,带分母
```

doctor **不会**告诉你插件正在运行,因为子进程观察不到启动它的那个会话。**只有你自己
会话里看到的 hook 输出**才算激活证据。这个区分不是抠字眼:本插件 v0.1 公开
发布了三个月,期间任何 clean install 都装不上,而它在作者本机上看起来一切正常
(CASES.md 案例 10)。

### 不用插件(通用脚手架)

若你不用 Claude Code 插件,有一个无需插件的脚手架,把治理文件铺进任意项目:

```
git clone https://github.com/johnrucnapier-sketch/ACGM-for-Claude-Code
sh ACGM-for-Claude-Code/scripts/governance-init.sh /你的项目路径
```

它写 `CONSTITUTION.md` + `AGENTS.md`(一份通用 agent 治理指令)+ `CLAUDE.md` 指针
(**幂等、非破坏**,已存在的文件只跳过、绝不覆盖)。脚本可审阅,故意不用 `curl|sh`。
这是**静态脚手架,不是运行时**:指令会不会被自动应用,取决于你的 agent 是否按约定
读取 agents 文件。方法论本身原则上工具无关——把通用脚手架按你的场景适配。

### 完全为 Claude Code 而设计——以及 Codex 去哪了

**这个项目是完全为 Claude Code 设计的。** 这里的机制——hooks、结构门、doctor、活跃度
报告——都是照着 Claude Code 的插件与 hook 契约写的,也只在那里被真正跑过。

早期版本里带过一条 Codex 路径,**2026 年 5 月被拿掉了**,原因很朴素:作者当时用 Codex
不够多,没有验证过它,而把一个未经验证的"那边也能用"发出去,正是这套方法论要消灭的
②号认知漂移。**那是关于作者证据不足的陈述,不是关于 Codex 的判断。**

Codex 的支持现在有自己的仓库,因为**两边的工作逻辑差异足够大,一个插件同时伺候两边,
结果是两边都伺候不好**:

> **[ACGM-for-Codex](https://github.com/johnrucnapier-sketch/ACGM-for-Codex)**

作者有时间的话会同时维护两个项目。它们**共享方法论,不共享机制**,而且**本仓测到的
任何东西都不构成对那个项目的验证**。其他 agent 请拿通用脚手架和原则去按自己的场景适配。

### "自动"是怎么回事(如实)

- **四个 hook 构成运行时机制。** `SessionStart` 每个会话注入 grounding;`PreToolUse`
  把破坏性 Bash 挡在一道结构门后;`PostToolUse` 对治理文档的写入给出提醒,**不改动
  任何文件**;`SessionEnd` 报告本次会话正在丢下的后验核验。skill 由 Skill 工具调用,
  不自动点火。
- **门判结构,不判措辞。** 它要求:四个具名字段**写在命令自身的注释行里**;操作独占一次工具调用
  (不得有 `;`、`&&`、pipe 或被计算出的目标);本会话内此前已有只读调用。三条都从
  工具调用和 transcript 判定,**都不能靠写文字生产出来**。四项不全的门是**拒绝**:
  只会 `ask` 的 hook 要经过会话的权限模式,而自动接受的模式会让「问」变成空操作。
  补齐字段解除阻断,人仍通过正常流程拍板——证据永远不是授权。
- **`sh scripts/acgm-doctor.sh` 告诉你到底接上了什么**,并且拒绝宣称它证明不了的东西:
  它把"运行时激活"报为**子进程无法证明**,因为 doctor 观察不到调用它的那个会话。
- **`python3 scripts/acgm_activity.py` 回答 doctor 回答不了的那个问题**——插件到底
  干活了没有,在本项目、在别的项目。它读每个会话记录下来的 hook 输出,**以工具调用为键**,
  绝不在 transcript 里搜文本(那可能只是 agent 自己引用过的字句)。所有计数都带分母,
  因为**"门一次没响"和"插件没装上"在没有分母时长得一模一样**。真正值得追查的信号既不是
  前者也不是后者:是**一条破坏性调用,却没有任何门裁决对上它的 id**。
- 通用脚手架只写静态文件,不是运行时。
- 两种方式接好的都是"自动 grounding + 宪法骨架"。完整治理(决策日志/快照/轨道)是
  **人驱动**的:调用 `governance-bootstrap` 或照 `METHODOLOGY.md` §12 手做。

## 八条原则(完整正文:`METHODOLOGY.md`)

1. 按生命周期分层存内容(宪法/决策日志/快照/版本归档/契约/活交接)
2. 项目根规则文件 = 元规则+指针+行为约束,**绝不放事实**
3. 真值优先(绝对版,无灰色地带)——含其推论:摘要永不作为代码真值
4. session 启动 grounding 仪式(先验证再动手)
5. 不过度执行(暴露歧义,不蛮干;销毁前硬检查点)
6. 按轨道隔离工作(不同认知上下文/验证方法不混)
7. 一个主干,永不腐化——含其推论:工作树纪律
8. 范围边界(明确 IN/OUT——默认判据,可按项目重定义)

## 仓库结构

```
README.md                          ← 你正在读的(WHY + 索引);英文在前,中文在后
METHODOLOGY.md / METHODOLOGY.en.md ← 完整方法论(八原则 + bootstrap 配方 + 失败模式)
CASES.md                           ← 真实、脱敏的漂移纠错案例
.claude-plugin/
  plugin.json                      ← 本仓即一个 Claude Code plugin
  marketplace.json                 ← 供 /plugin marketplace add 安装
hooks/hooks.json                   ← SessionStart + PreToolUse + PostToolUse + SessionEnd(自动层)
scripts/grounding-inject.sh        ← SessionStart:注入薄 grounding 指令,指向 skills
scripts/pretool-destructive-bash.sh ← PreToolUse:廉价的破坏性命令过滤
scripts/acgm_gate.py               ← 结构门本体,以及 SessionEnd 的未完成义务报告
scripts/post-tool-truth-first.sh   ← PostToolUse:治理文档写入提醒,不改任何文件
scripts/sessionend-obligations.sh  ← SessionEnd:未核验的后验承诺
scripts/acgm-doctor.sh             ← 健康检查;把"运行时激活"报为子进程无法证明
scripts/acgm_activity.py           ← 已记录的激活情况,跨项目,带分母
tests/                             ← 契约与行为测试,密封(CLAUDECODE 设与不设各跑一次)
CHANGELOG.md / EVIDENCE.md         ← 发布历史;每条主张的成熟度登记表
scripts/governance-init.sh         ← 无需插件的通用脚手架:铺 CONSTITUTION/AGENTS/CLAUDE 指针
scripts/drift-check.sh             ← 静态漂移扫描器(手动或 CI 跑)
skills/
  session-grounding/SKILL.md       ← 调用时机:session 启动/续接,5步grounding+先报告
  truth-first/SKILL.md             ← 调用时机:写技术结论/不可逆操作前,强制来源
  governance-bootstrap/SKILL.md    ← 调用时机:新项目从零建治理,人驱动8步清单
templates/                         ← 全空白通用骨架,零业务
  CONSTITUTION.skeleton.md  ADR._TEMPLATE.md  SESSION_START.skeleton.md  drift-check.stub.js
LICENSING.md / LICENSE-DOCS / LICENSE-CODE  ← 双轨:文档 CC-BY-4.0,代码 MIT
```

## 适配指南:直接拿用 vs 必须按你项目改

**直接拿用(通用骨架)**:四类漂移分类 / 八原则 / 分层结构 / bootstrap 配方 /
自检红线。

**必须按你项目重新设计(照抄=另一种漂移)**:
- 轨道怎么分(取决于你项目核心价值在哪、有几个认知上下文)
- 范围边界 IN/OUT 具体清单(如有需要,连 IN/OUT 判据本身也可改——它是默认,见
  METHODOLOGY §10)
- 跨切面契约具体是哪些协议
- 红线具体内容(你的产品/合规决定)

> 原则是骨架,可迁移;血肉是你项目自己的。别把别人的轨道/契约清单照抄。

## 真实背景(最强的可信度)

这不是从玩具项目里提炼的。它来自一个**跨度数月、几十万行代码、已经上线应用市场**的
应用——用 agent 开发,几十个 session,多个版本,反复变更的需求。在这个跨度上,这套
方法论**确实有效提高了稳定性、减少了错误**,而且正是在长项目最容易崩的地方:第二个月、
第十五个 session、需求第三次改动的时候。

它同时**在被搭建的过程中,搭建者自己就犯了②号漂移**——从旧交接文档抄了一堆技术结论
没去读代码,被项目所有者当场抓出。这不是丢人,这恰恰是证据:**纪律不是给"别人"的,
是给当下每一次写字的你的。** 把真实事故永久写进治理文件当警示案例,顶十条抽象规则。

### 状态:进行时,而且在**有意收缩**

这是一个**活的项目,不是完成的框架**,而且有两股力量同时拉扯它。

**模型正在把工具层曾经提供的东西内化掉。** 随着 2026 年 7 月这轮能力跃升,本插件强制
的一部分东西正在变成模型的原生行为。计划是**逐步移除模型已经内化的部分**,而不是出于
惯性留着——**一个只增不减的治理层,最终会变成它当初要防的那种开销**。这里每一个机制,
都应该随着模型进步重新证明自己还有存在的必要。

**它贴着作者实际跑过的东西调。** 里面大量的适配是针对 **Opus 4.6 – 4.8** 磨出来的。
作者**刚刚开始在 Opus 5 上工作**,契合度还在摸索,这个项目会随着这段经验的累积继续改。
这里的版本号请当作"试过什么"的记录,不是"普遍适用"的宣称。

## 初衷 / 为什么会有这套东西

> 这一段是作者的个人表达——这是你的声音,按你自己的舒适度自由增删。

我有完美主义倾向,也长期与焦虑相处。过去很多年,我没法再像学生时代那样做长文本写作
——脑子里的信息和思考,远远超过我能落到纸上的速度;执行能力追不上想法。在现实工作里,
我总觉得被自己的局限性卡住。

AI / agent 的时代对我像是枷锁被打开:那些"想得太多、写得太慢"的缺点,反而变成了
优势——天马行空的想法可以和 agent 结合,长出很多原本我做不出来的东西。

在长时间的 agent coding 实践里,我一次次踩坑,逐渐把"怎么让 agent 在多子项目、超长
周期、大量迭代和需求变化中仍然保持一致、少犯错、少走错路"沉淀成了这套方法论。在我
自己的项目里它效果很好;因为我本人是风险厌恶者,这套方法论也让 agent 更谨慎、破坏性
的动作更少。

我把它开源,是想让同样在用 AI 编码 agent 做长周期开发的人,不必把我踩过的坑再踩
一遍。原则是骨架,拿去按你自己的项目长出血肉。

## License / 维护态度

- **License:双轨**——方法论/文档(`METHODOLOGY*.md`、`README.md`、`CASES.md`、
  `CONTRIBUTING.md`、各 `SKILL.md` 正文)采用 **CC-BY-4.0**;代码/机械件
  (`scripts/`、`hooks/`、`templates/`、`.claude-plugin/`)采用 **MIT**。详见
  `LICENSING.md`。
- **成本(未实测,作者判断):** 很可能消耗*更多* token(更多读码/验证/转述/停下
  确认),但换来更少错误与走错路,从而压缩最贵的返工。作者不缺 token、未实测,增减
  请在你自己项目上体验。
- **维护:** 方法论分享,欢迎 issue/PR,但**自行适配为主,不承诺重度支持**。

## 作者与致谢

- **johnrucnapier-sketch** —— 方法论、方向,以及每一个放行/否决的决定。
- **Claude Opus 5** —— v0.4–v0.6 重建的共同作者:结构门、doctor、活跃度报告、测试套件,
  以及那些"在造它们的过程中翻了车、于是写下来"的案例与证据条目。

提交带 `Co-Authored-By: Claude Opus 5`。GitHub 的 contributor 图是按能解析到账号的
author 邮箱生成的,不会列出一个模型——所以署名写在这里,而不是指望一张结构上就显示不了
它的图。

有一点得如实记下,因为这个项目本身就是关于不夸大的:v0.4–v0.6 修掉的缺陷,**大多是这次
重建过程中由同一个共同作者引入的**,而它们是靠读记录抓出来的,不是靠没犯。**门反复地、
正确地拦下它自己作者的命令**——这是这里最接近"验证"的东西。

提炼自一个真实长周期 AI 驱动开发项目的治理实践。已剥离全部业务特质——仓库内**不含也
永不接受**任何具体项目的业务/机密内容(这本身就是 §④ 范围边界的应用)。
