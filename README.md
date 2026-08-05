# Agent Coding Governance

**A governance system for multi-session, long-horizon AI development — built and validated on Claude Code.**

[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSING.md) [![Docs: CC--BY--4.0](https://img.shields.io/badge/docs-CC--BY--4.0-blue.svg)](LICENSING.md) [![Dual-license](https://img.shields.io/badge/license-dual--track-lightgrey.svg)](LICENSING.md)

> English first (full). 中文完整版在下半部分 — scroll past the English.

---

> **One sentence:** long-horizon AI-driven development **rots structurally** — unless
> there is governance.
>
> Distilled from a real project (a dozen-plus versions, dozens of sessions, ~2B
> tokens of mistakes). What you get: an agent that takes fewer wrong turns, makes
> fewer fabricated claims, and does fewer destructive actions across long timelines —
> at the cost of it stopping to verify more. It ships as a Claude Code plugin
> (runtime-automatic). A generic, plugin-free scaffold is also included for other
> setups.

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

## Real-world hit rate (factual, not extrapolated)

In a **single 2–3 hour continuous work session**, this methodology triggered
**7 distinct drift detections** — including one data-migration bug that would have
**silently dropped real rows** (caught at the instant of the Bash command), and a
"your premise is false" block where a spec disagreed with code truth. One recorded
case is an **external AI's modification plan caught by the local governance before
merge**. The full, desensitized set is in **[CASES.md](CASES.md)**.

This is **one observed window, not an extrapolated average** — assess the rate on
your own project. If you install this and nothing ever triggers: either your project
isn't yet at the scale that needs it, or it isn't wired correctly.

## Quick start

### Claude Code (the plugin — runtime-automatic)

Two steps (honest — not literally one command):

1. Register the marketplace:
   ```
   /plugin marketplace add johnrucnapier-sketch/Agent-Coding-Governance-Methodology
   ```
2. Install the plugin (from the `/plugin` menu, or):
   ```
   /plugin install agent-coding-governance-methodology@agent-coding-governance-methodology
   ```

**Exact commands follow current official Claude Code docs** — CC's plugin/marketplace
syntax may change by version; if `/plugin install` differs, just open the `/plugin`
menu and install it from the marketplace you added in step 1.

*You'll know it worked when:* at the next session start the SessionStart hook
injects a grounding directive — the agent acknowledges governance and runs the
5-step grounding (or, if the project has no governance docs yet, points you to
`governance-bootstrap`) instead of diving straight into edits.

*And check it, don't assume it.* `claude plugin list` showing **enabled** is
configuration, not activation — a plugin can be registered and still fail to
load. Run `sh scripts/acgm-doctor.sh` for the configuration side, and treat
observed hook output in your own session as the only proof of activation. This
distinction is not pedantic: v0.1 of this plugin was published for three months
in a state where no clean install could load it, while appearing healthy on the
author's machine (CASES.md Case 10).

### Without the plugin (generic scaffold)

If you are not using the Claude Code plugin, a plugin-free scaffolder drops the
governance files into any project:

```
git clone https://github.com/johnrucnapier-sketch/Agent-Coding-Governance-Methodology
sh Agent-Coding-Governance-Methodology/scripts/governance-init.sh /path/to/your-project
```

It writes `CONSTITUTION.md` + `AGENTS.md` (a generic agent-governance directive) +
a `CLAUDE.md` pointer (**idempotent & non-destructive** — existing files are
skipped, never overwritten). The script is reviewable; `curl|sh` is deliberately
avoided. This is a *static scaffold*, not a runtime: whether the directive is
auto-applied depends on whether your agent reads an agents-file by convention. The
methodology is tool-agnostic in principle — adapt the generic scaffold to your setup.

### Why Claude Code only (honest)

An earlier version of this repo also targeted Codex. It was removed — deliberately.
The author's own long-horizon work is almost entirely in Claude Code; Codex was used
only for light, short tasks, with no large multi-session projects and therefore no
accumulated long-horizon pain to validate against. Shipping a "works on Codex too"
claim the author had not actually stress-tested would itself be the ② cognitive
drift this methodology exists to stop. So only what has been fully practiced ships
here: Claude Code. The principles are tool-agnostic; this is open-source — if you
work in Codex or another agent, take the generic scaffold and the principles and
adapt them to your own setup.

### How "automatic" works (stated honestly)

- **Four hooks are the runtime mechanism.** `SessionStart` injects grounding every
  session. `PreToolUse` holds destructive Bash behind a structural gate.
  `PostToolUse` advises on governance-doc writes and changes nothing.
  `SessionEnd` reports post-action checks the session is walking away from.
  Skills are invoked by the Skill tool; they do not auto-fire.
- **The gate checks structure, not wording.** It requires four named fields with
  real content, the operation isolated in its own tool call (no `;`, `&&`, pipe,
  or computed target), and a read-only call already present in the session. All
  three are decided from the tool call and the transcript, so none can be
  produced by writing text. A complete gate still asks the human — evidence is
  never authorization.
- **`sh scripts/acgm-doctor.sh` tells you what is actually wired**, and refuses to
  claim what it cannot prove: it reports runtime activation as *not provable from
  here*, because doctor is a subprocess and cannot observe the session that ran it.
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

This system **committed drift ② against itself while being built** — the builder
copied a pile of technical conclusions out of old handoff docs without reading the
code, and was caught in the act by the project owner. That is exactly the proof:
**discipline is not for "other people", it is for you, every single time you write
something right now.** Writing a real incident like this permanently into the
governance file as a cautionary case is ten times more useful than an abstract rule.

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

## Acknowledgements

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
> 提炼自一个真实项目(十几个版本、数十 session、~20 亿 token 踩坑)。你能得到的:
> 在长周期里,agent 走错路更少、编造结论更少、破坏性动作更少——代价是它会更频繁地
> 停下来核实。以 Claude Code 插件形式分发(运行时自动);另附一个无需插件的通用
> 脚手架供其它场景。

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

## 实际命中率(事实,非外推)

在**一次 2–3 小时的连续工作**里,这套方法论触发了 **7 次明确的漂移检测**——其中
一次是会**静默丢失真实数据行**的数据迁移 bug(在 Bash 命令那一刻被拦),还有一次
"你的前提不成立"阻塞(spec 与代码真值不符)。其中一例是**外部 AI 写的修改方案在
合并前被本地治理拦下**。完整脱敏案例见 **[CASES.md](CASES.md)**。

这是**一次观测窗口,不是外推的平均率**——具体频率请在你自己项目上判断。如果你装上
后什么都没触发:要么你的项目还没到需要它的规模,要么没装对。

## 快速开始

### Claude Code(插件——运行时自动)

两步(老实说,不是字面上的一条命令):

1. 注册 marketplace:
   ```
   /plugin marketplace add johnrucnapier-sketch/Agent-Coding-Governance-Methodology
   ```
2. 安装插件(用 `/plugin` 菜单,或):
   ```
   /plugin install agent-coding-governance-methodology@agent-coding-governance-methodology
   ```

**确切命令以当前 Claude Code 官方文档为准**——CC 的 plugin/marketplace 语法可能随
版本变化;若 `/plugin install` 形式不同,就打开 `/plugin` 菜单,从第 1 步加的
marketplace 里装。

*成功的样子:* 下次 session 启动时,SessionStart hook 会注入一段 grounding 指令——
agent 会先确认治理、走 5 步 grounding(或在项目还没治理文档时,引导你调
`governance-bootstrap`),而不是直接埋头改代码。

*但要去查,不要假设。* `claude plugin list` 显示 **enabled** 是**配置**,不是**激活**
——插件可以注册成功却加载失败。配置这一侧跑 `sh scripts/acgm-doctor.sh`;激活这一侧,
**只有你自己会话里观察到的 hook 输出**才算证据。这个区分不是抠字眼:本插件 v0.1 公开
发布了三个月,期间任何 clean install 都装不上,而它在作者本机上看起来一切正常
(CASES.md 案例 10)。

### 不用插件(通用脚手架)

若你不用 Claude Code 插件,有一个无需插件的脚手架,把治理文件铺进任意项目:

```
git clone https://github.com/johnrucnapier-sketch/Agent-Coding-Governance-Methodology
sh Agent-Coding-Governance-Methodology/scripts/governance-init.sh /你的项目路径
```

它写 `CONSTITUTION.md` + `AGENTS.md`(一份通用 agent 治理指令)+ `CLAUDE.md` 指针
(**幂等、非破坏**,已存在的文件只跳过、绝不覆盖)。脚本可审阅,故意不用 `curl|sh`。
这是**静态脚手架,不是运行时**:指令会不会被自动应用,取决于你的 agent 是否按约定
读取 agents 文件。方法论本身原则上工具无关——把通用脚手架按你的场景适配。

### 为什么只留 Claude Code(如实)

本仓早期版本也做过 Codex 支持,**后来主动删了**。作者自己的长周期开发几乎全程
Claude Code;Codex 只做过轻量短任务,没有大型多会话项目,因此**没有可供验证的长
周期痛点积累**。把一个作者并未真正压测过的"Codex 也能用"宣称发出去,本身就是这套
方法论要消灭的②号认知漂移。所以这里只发**作者完整实践过的**:Claude Code。原则
是工具无关的;这是开源——你若在 Codex 或别的 agent 上工作,把通用脚手架和原则拿去
按自己的场景适配。

### "自动"是怎么回事(如实)

- **四个 hook 构成运行时机制。** `SessionStart` 每个会话注入 grounding;`PreToolUse`
  把破坏性 Bash 挡在一道结构门后;`PostToolUse` 对治理文档的写入给出提醒,**不改动
  任何文件**;`SessionEnd` 报告本次会话正在丢下的后验核验。skill 由 Skill 工具调用,
  不自动点火。
- **门判结构,不判措辞。** 它要求:四个具名字段且有真实内容;操作独占一次工具调用
  (不得有 `;`、`&&`、pipe 或被计算出的目标);本会话内此前已有只读调用。三条都从
  工具调用和 transcript 判定,**都不能靠写文字生产出来**。四项齐全仍然交给人拍板
  ——证据永远不是授权。
- **`sh scripts/acgm-doctor.sh` 告诉你到底接上了什么**,并且拒绝宣称它证明不了的东西:
  它把"运行时激活"报为**子进程无法证明**,因为 doctor 观察不到调用它的那个会话。
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

这套体系**在被搭建的过程中,搭建者自己就犯了②号漂移**——从旧交接文档抄了一堆技术
结论没去读代码,被项目所有者当场抓出。这恰恰证明:**纪律不是给"别人"的,是给当下
每一次写字的你的。** 把这类真实事故永久写进治理文件当警示案例,比抽象规则有用十倍。

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

## 致谢

提炼自一个真实长周期 AI 驱动开发项目的治理实践。已剥离全部业务特质——仓库内**不含也
永不接受**任何具体项目的业务/机密内容(这本身就是 §④ 范围边界的应用)。
