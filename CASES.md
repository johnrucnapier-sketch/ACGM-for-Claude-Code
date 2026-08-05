# Drift-correction cases (real, desensitized)

> English first (full). 中文完整版在下半部分。

Real cases where this methodology triggered and corrected a drift in actual work.
All project names, code symbols, infrastructure names, versions, schema hints, and
paths are **removed** — only the drift mechanism remains. Generic, well-known
technical terms may stay.

**The first batch comes from a single 2–3 hour continuous working session.** This is
one observed window, not an extrapolated average — see `README.md` for the honesty
note on rates.

## Drift types (quick reference)

- **① Implementation** — bypassing the spec while coding, silent error-swallow,
  uncontrolled side effects
- **② Cognitive** — concluding from conversation residue / impression / assumption
  instead of reading the real code or config
- **③ Structural placement** — governance docs rotting, on the wrong branch, spec
  diverging from code truth
- **④ Scope** — crossing the project's explicit IN/OUT boundary

## Index

| # | Title | Drift | Trigger |
|---|---|---|---|
| 1 | Migration script silently drops data | ② → ① | pre-Bash gate + grounding |
| 2 | Component behavior assumed from its name | ② | truth check |
| 3 | Stale example config vs. real config | ③-adjacent | verify-before-change |
| 4 | Spec disagrees with code truth → blocked | ②+③ | "premise false" block |
| 5 | Unverifiable fact labeled, not concluded | ② | honest labeling + multi-source |
| 6 | Strong bug hypothesis forced to verify | ② preventing ① | hard truth constraint |
| 7 | External AI's plan caught before merge | ②+③ (+P0) | pre-merge full-repo scan |
| 8 | Solo, one worktree, parallel → governance nearly mislanded | ③ | grounding worktree/branch check |
| 9 | Form-complete + long autonomy + compaction = self-audit miss | ② chain | external human audit |
| 10 | A published governance plugin that could never load | ③ | official validator, run for the first time |
| 11 | Two gates, one command, credit given to the wrong one | ② | raw hook stdout in the transcript |
| 12 | A gate satisfied by four characters, while the real irreversible op passed | ① | reading the gate's own source |
| 13 | Three versions installed, running from a deleted binary | ② | `CLAUDE_CODE_EXECPATH` vs. disk |
| 14 | ~10 parallel work streams, drift cleared, then nothing dramatic ever again | ② at scale | project-internal audit rounds |

---

### Case 1 — A migration script that would silently drop data (② triggers ①)

**Situation.** Run a data migration between two SQL stores, with an out-of-date
handoff doc as the guide.

**The drift.** The migration script's table-name list was written from impression
(a wrong, simpler name). The real stores used a different actual name, holding real
rows. The wrong name existed in neither store.

**Correction.** The first command was held by a pre-execution gate — it did not run.
Instead of trusting the stale handoff, a read-only grounding checked both real
stores and **read the script's source** (not guessed): the copy loop and the
verification loop both iterate the same bad list and skip anything not in it.
Consequence chain: the wrong name is skipped; the real table, absent from the list,
is **never iterated** → its rows would be silently dropped. Worse: the script's own
two-way count check uses the *same* bad list, so it cannot see the loss and would
print success, all green.

**Fix.** One place, root-cause, minimal diff: correct the list to match the real
tables.

**If uncaught.** Real rows silently lost; self-check green; "migration successful."

### Case 2 — Component behavior assumed from its name (②)

**Situation.** Prepare a fallback deployment of a component; its method/format needed
confirming.

**The drift.** The artifact's *name* implied one method. Its actual config manifest
declared a different type and a different method. Serving had to follow the real
config, not the name.

**Correction.** Did not assume from the name — read the config manifest directly.
Also proactively admitted a second uncertainty (a capability not yet confirmed), and
instead of guessing an API, read the actually-installed source to confirm what that
build really supported.

**Fix.** Truth from the registered/declared config, not from the artifact's name.

**If uncaught.** Wrong serving config; the failure mode is silent (loads fine, the
feature just doesn't work) — far harder to localize later.

### Case 3 — Stale example config vs. the real one (③-adjacent, over-change prevention)

**Situation.** Plan to stop a non-production component; *assumed* a coordinated
change to a separate gateway would also be needed.

**The drift.** The repo's `*.example` config showed a two-endpoint setup; the real
deployed config used only one. The example was simply stale.

**Correction.** Read the real deployed config, not the example. The coordinated
gateway change turned out to be unnecessary — the planned action had zero impact on
the other component. A whole risky production change was removed from the plan.

**Fix.** Act on the real config; do not touch what the stale example implied.

**If uncaught.** A completely unnecessary production change — every needless prod
change is added risk for no benefit.

### Case 4 — Spec disagrees with code truth → block, don't proceed (②+③)

**Situation.** A spec and some system descriptions described a baseline; the actual
running reality differed.

**The drift.** Spec and descriptions were both out of sync with reality (③ doc rot);
proceeding on them would compound ②.

**Correction.** Read the code → found current reality ≠ the spec's stated baseline.
Marked every mismatched item "not truth," and raised a **block: 'your premise is
false'** — did not proceed; aligned first, then updated the governance docs from
code truth (not the reverse).

**Fix.** Governance docs follow code truth; the spec is corrected to match reality,
not acted upon.

**If uncaught.** Every downstream decision built on a false premise; by the time it
surfaces, several layers of error are stacked and localization cost multiplies.

### Case 5 — An unverifiable fact, labeled rather than concluded (②)

**Situation.** Confirm whether a named artifact/variant existed and was usable.

**The drift (avoided).** The primary lookup channel was unreliable from the work
machine; the fact **could not be authoritatively verified** there.

**Correction.** Did not conclude or fabricate — explicitly labeled "**not verified
from here; cannot conclude**," then used reachable parallel channels. A source that
*could* be read directly was used at full confidence; one that could not was graded
**one notch lower** and not mixed in with high-confidence conclusions. Result: the
spec had named an artifact that **did not exist** and a variant that could not fit
the available resources.

**Fix.** Decisions that pick a specific artifact escalate to a human; the
methodology does not silently self-select.

**If uncaught.** Build toward a nonexistent / unfittable target; all downstream work
wasted.

### Case 6 — A strong bug hypothesis forced through verification (② preventing ①)

**Situation.** A client error appeared with a fully self-consistent root-cause story
that explained every observed symptom.

**The drift (avoided).** The hypothesis was *so* coherent it was tempting to act on
it as a conclusion.

**Correction.** It was labeled "**strong hypothesis — pending truth verification,
not from impression**," and the hard rule forced reading the actual API contract and
the actual source before any change.

**Fix.** Change based on read truth, not on an assumption — however convincing.

**If uncaught.** Likely "fixing" the wrong place: if the real cause was elsewhere,
the symptom persists *and* correct code was broken — rollback + re-work, multiplied
cost.

### Case 7 — An external AI's plan caught before merge (②+③, plus a P0)

**Situation.** A second AI assistant was brought in as an advisor and produced a
multi-step modification plan for this very repository. The plan was run through the
local governance **before** anything was merged.

**The drift (in the advisor's plan).** ② — conclusions drawn from conversation
residue without reading the full current repo state. ③ — changing one file's rule
without scanning the whole repo, which would have produced spec divergence across
several files. Plus a **P0, irreversible**: it would have published a real-project
fingerprint into a public repo and broken the repo's own scope-boundary promise.

**Correction.** A pre-merge full-repo consistency scan found: conflicts with
already-merged conventions in 5+ files, contradictions with the methodology's own
principles in 2 places, and the irreversible exposure — all intercepted before
landing.

**Fix.** The plan was reworked: hard-abstract the exposure, sweep the rule change
consistently across all files, reconcile the internal contradictions.

**If uncaught.** First public release would have broken its own promises (the
scope-boundary claim, a freshly-published convention), leaked an irreversible
fingerprint, shipped a self-contradiction, and a self-flagging checker. The strongest
proof of this methodology is not catching a human — it is catching *another AI
brought in to help*, before it landed.

### Case 8 — Solo, one worktree, parallel work → governance nearly lands on the wrong branch (③)

**Situation.** One agent session was authoring governance docs on the trunk. The same
person, elsewhere against the *same working directory*, did work on another line and
`checkout`ed a branch.

**The drift.** Branch state is a property of the directory, not the session — so the
governance edits "magically" ended up on that feature branch (the edge of
structural-placement drift). No second person was involved; it was a self-collision.

**Correction.** Session-start grounding caught that the worktree/branch was wrong; a
stop + reflog inspection located it before it compounded. The root fix is physical:
one line = one dedicated worktree, the main tree pinned to the trunk.

**Fix.** Worktree discipline (Principle Seven · corollary): isolate each line in its
own worktree; never switch branches in the main (trunk) tree.

**If uncaught.** Governance authored on a feature branch, the trunk silently stale —
classic ③; the next session on the old trunk reads all-wrong.

### Case 9 — Form-complete + long autonomous execution + compaction = ACGM design dead-zone (chained ② failure)

**Situation.** Sandbox evaluation work across ~2 days, multiple session compactions,
high-density Bash operations including state-changing ones (service start/stop,
artifact load/unload, async background long-running jobs).

**The drift — a four-step chain, all variants of ②.**

1. *Compaction inheritance.* A session-resume marker appears in the transcript
   ("This session is being continued from a previous conversation..."). Identifiers
   for services, configurations, and resource states are inherited from the
   compacted summary, with no mechanism requiring re-verification at the source.

2. *Form-complete grounding report.* The agent posts a structured grounding
   report — track / git status / change-set / steps, all sections present. Some
   items (track, git state, latest commit) had corresponding tool-use evidence in
   the same conversational block. But other specific numeric and identifier
   claims (prior outcomes, capacity ceilings) had **no corresponding tool use**
   in this block — inherited from the compacted summary. Form was perfect;
   substance was partial.

3. *Operational name from memory.* The agent issued destructive Bash using a
   session-internal alias (a one-off label established earlier) as the canonical
   service identifier, without a fresh listing query verifying the real
   identifier. The real identifier differed; the command would have stopped a
   wrong target.

4. *Started-and-forgotten.* The agent then launched an auto-restarting service
   and stopped following it. The service failed, the auto-restart cycled,
   hardware risk was present — none of this surfaced until the human, hours
   later, pointed it out.

**Correction.** External human audit caught the chain. The methodology was then
extended at the normative layer (Stance section's three-layer model + new
corollaries) plus a single targeted mechanism layer (PreToolUse hook on
destructive Bash, with the source-citation check verified mechanically against
the transcript). The CONTRIBUTING 2-independent-evidence rule was added in the
same revision to prevent over-fitting to this single incident.

**Fix.** Norms now name each failure mode explicitly (operational truth /
post-action self-monitoring / grounding before destructive ops / compaction
re-verify / ritual-compliance criterion); one mechanism layer covers the
mechanically-checkable subset; the rest is owned by the audit layer (the honest
position, not a workaround).

**If uncaught.** All four failures compound — wrong target stopped, hardware
risk ignored, downstream decisions built on inherited un-verified facts;
localization cost grows by orders of magnitude hours after the fact.

**Mirror to Case 7.** Case 7 was "external AI's plan caught by local governance
before merge" — local governance catching outside drift. **Case 9 is the inverse
mirror:** local governance failing to catch *itself* under a specific
combination of conditions (long autonomy + compaction + form-completeness).
This is the methodology's second self-audit moment (the first being the ②
the README cites). Each such moment extends ACGM rather than discredits it.

---

### Case 10 — A published governance plugin that could never load (③)

**Situation.** ACGM v0.1 was released publicly in May 2026 and used daily on the
author's machine for months. On 2026-08-05 the official validator was run against
the repository for the first time.

**The drift.** `plugin.json` declared `"skills": "skills/"` and
`"hooks": "hooks/hooks.json"`. The loader requires declared paths to start with
`./`, and `hooks/hooks.json` is loaded automatically, so declaring it fails as a
duplicate. The published package could not be installed by anyone.

It appeared to work locally for a reason that is worse than the bug. The plugin
was registered from a **directory-source marketplace**, which syncs the working
*tree*, not the Git tree. When the cache was built, the working directory held an
uncommitted, never-committed variant of `plugin.json` that happened to be valid.
The running bytes therefore had no Git identity at all, and the cache accumulated
files from three separate commits plus one untracked file.

**The fix already existed, and was thrown away.** A session note from the release
two and a half months earlier records exactly this change — array form, `hooks`
key removed — sitting in the working tree, reverted with `git checkout` as *"risk
unknown (could break hook loading), out of scope"*. That discarded edit is the
variant the cache had captured. **The only version of the manifest that worked was
the one deliberately discarded as too risky to keep**, and reverting it is what
made the published package unloadable while the machine kept running fine.

The reasoning was locally sound: an unverified change to plugin loading, late in a
release, out of the round's scope. What was missing was the cheap check that would
have settled it in seconds — the official validator, which was never run.

**Why nothing caught it.** The successor release added ~4400 lines of tests, an
8-check release contract, and a 3-OS CI matrix. None of them ever invoked
`claude plugin validate`, and none asked whether the package could be installed.
It then added a ~3670-line installer to solve reported installation failures. The
cause was two missing `./` prefixes.

**Correction.** Fix the manifest; add contract tests that encode the loader's
rules; make "Claude Code accepts the package" a CI job that installs from the
checkout and asserts `enabled`. Note that `validate` passing is still not loading:
the duplicate-hooks configuration validates cleanly and is refused at load time.

**Generalization.** A governance mechanism must prove it is installable before it
makes any claim about governing anything. Test volume is not coverage; 4400 lines
of tests that never ask the one question that matters are 4400 lines of comfort.

---

### Case 11 — Two gates, one command, credit given to the wrong one (②)

**Situation.** During the same session, a destructive `rm -rf` was held by a
pre-execution gate. The agent reported that ACGM's own hook had caught it.

**The drift.** Two plugins were installed, each with a PreToolUse gate. The
message rendered to the user came from the third-party one. The agent attributed
the interception to ACGM based on the visible text and on its expectation of
which mechanism was active. Later, correcting itself from the wording mismatch,
it over-corrected to "it was not ACGM at all" — also wrong.

Only the raw hook output settled it: the transcript contains a `PreToolUse`
attachment whose stdout carries ACGM's own `permissionDecision: "ask"` against
that exact `toolUseID`. **Both** gates fired. The agent had been wrong twice, in
opposite directions, before reading the evidence.

**Why this matters here.** This register already contains a rejected claim of
exactly this shape: an earlier interception credited to ACGM was found to have
been held by a third-party gate. The failure mode reproduced, with a different
agent, in the project that documented it.

**Correction.** Attribution requires the mechanism's own output, keyed by tool
call — never the message a human happened to see, and never the absence of an
expected phrasing. Grepping a transcript for a gate's text is not attribution
either: the counts were contaminated by the agent having `cat`-ed the hook script
into the same transcript minutes earlier.

**Generalization.** In an environment with more than one guardrail, "what stopped
this?" is an evidence question. An intervention you cannot key to a mechanism is
not a win you may claim.

---

### Case 12 — A gate satisfied by four characters, while the real irreversible op passed (①)

**Situation.** Reading the v0.1 PreToolUse gate's source, in the same session in
which it had fired.

**The drift — three defects in the mechanism itself.**

1. *Text where structure was needed.* The gate grepped the agent's previous reply
   for the literal markers `(a)`–`(d)`. Four characters satisfied it. Form
   compliance was, mechanically, the pass condition — the exact behaviour the
   methodology names as performative compliance.
2. *Whitelist mismatch.* The session's genuinely irreversible operations were
   plugin uninstalls, which were not on the destructive list and passed
   silently. The operation that *was* gated targeted a directory that did not
   exist. The gate caught the harmless case and missed the real one.
3. *Zero bypass cost.* Held once, the agent removed `rm -rf` from the command and
   proceeded. The outcome was good — the deletion had been unnecessary — but
   nothing was verified. The gate changed the wording, not the evidence.

A fourth defect surfaced in the PostToolUse hook the same day: on a false
positive, it **appended a marker comment into the governance file it had just
flagged**. The skill text promised it did not edit files. Implementation and
documentation disagreed, and a governance mechanism silently mutating the
artifact it governs is itself an unlogged state change.

**Correction.** Check structure instead of prose — named fields with real content;
the operation isolated in its own tool call with no `;`/`&&`/pipe/computed
target; a read-only call already present in the session. All three are decidable
from the tool call and the transcript, so none can be produced by writing text.
Extend the whitelist to plugin/package/config state. Make the PostToolUse
response an advisory that touches nothing.

**Generalization.** A gate that reads what the agent *says* measures compliance
theatre. A gate that reads what the agent *did* measures evidence. Prefer a coarse
detector with a cheap response over a clever detector with an expensive one.

---

### Case 13 — Three versions installed, running from a deleted binary (②)

**Situation.** A question about why a session showed a smaller context window than
expected.

**The drift.** Three installations of the same tool coexisted: a package manager's
copy on disk at one version, the desktop application's bundled copy at a second,
and the **actually executing process at a third** — whose directory had been
replaced during startup, leaving the process running from an unlinked file.

Every single-point check gave a different, confidently wrong answer.
`tool --version` in the shell reported the package-manager copy. Listing the
application's directory reported the bundled copy. Only the running process's own
`EXECPATH` revealed what was executing, and that path no longer existed on disk.

**Correction.** Read the running process's own identity, not a name resolved
through `PATH` and not a directory listing.

**Generalization.** This is the four-state separation in its purest form. Source
verified, configuration verified and runtime activated were three different
answers at the same instant — and the runtime one had no disk identity to check
against. Any claim of the form "we are running version X" needs the runtime's own
evidence, or it is configuration wearing a runtime's clothes.

---

### Case 14 — The rescue happens once; after that, success looks like nothing (② at scale)

**Situation.** May 2026, on a long-horizon application that later shipped. Around
ten parallel work streams were running against the same project. Information
error between them had become, in the owner's words, catastrophic: sessions
inheriting each other's stale conclusions, decisions overturned in one stream and
still live in another, no shared notion of which statement was current.

This is the condition the four drift types describe, all at once and compounding.

**What happened after the governance layer went in.** A few rounds of
project-internal audit — not new features, just reading current sources against
what the documents claimed — resolved the accumulated worktree confusion, the
drift, and the rot. The effect at that point was dramatic and easy to see.

**And then it stopped being dramatic.** In the months since, the layer has rarely
produced anything that felt like a rescue. Not because it stopped working — because
most problems now die in the first round, during the check-the-real-state step,
before they become anything worth naming. The owner's own summary: *there is not
much of that "it saved the project" feeling any more; but without it, the project
could not have been pushed this far.*

**What this case is actually about.** Governance return is **front-loaded, then
invisible**:

| Phase | What it does | What it looks like |
|---|---|---|
| First | clears accumulated rot | dramatic, countable, obvious |
| After | prevents new rot | **nothing happens** |

Counting saves measures the second phase at exactly zero. A tool that stops being
dramatic is not a tool that stopped mattering — it is what a working preventive
mechanism is supposed to look like.

**Reporting consequence.** A falling intervention count is the expected signature
of success, and is therefore worthless as evidence in either direction on its own.
It must be reported with its denominator — how many chances the mechanism had —
which is why `acgm_activity.py` separates `ACTIVE` from `ACTIVE (untested)` and
treats the second as a normal, healthy state rather than a warning.

**Limit, stated deliberately.** "Without it the project could not have been pushed
this far" is the owner's assessment of a **counterfactual that cannot be tested**.
It is recorded here as their judgment, and it is not treated as a validated claim
anywhere in this repository (EVIDENCE E-026).

---

## How it adds up

| Case | Trigger | Key action |
|---|---|---|
| 1 | pre-Bash gate + grounding | hold the command → read real stores → read source → derive consequence |
| 2 | truth check | refuse name-based assumption → read config + source |
| 3 | verify-before-change | read real config vs. stale example → drop needless change |
| 4 | block on false premise | reality ≠ spec → refuse to proceed |
| 5 | honest labeling | unverifiable → label + grade by confidence, don't mix |
| 6 | hard truth constraint | strong hypothesis ≠ conclusion → force read |
| 7 | pre-merge full scan | external plan vs. whole repo → intercept before landing |
| 8 | grounding worktree/branch check | shared dir + branch switch → caught before governance lands on the wrong branch |
| 9 | external human audit | norms extended at normative + mechanism layers; 2-independent-evidence rule added to prevent incident over-fitting |

**Common pattern:**

1. **Stop just before acting** — almost every case is caught at the moment of
   "about to do it," not cleaned up afterward.
2. **Refuse non-code input as truth** — names, specs, system descriptions, stale
   handoffs, stale examples, and self-consistent hypotheses all do not count.
3. **Honest labeling is a mechanism, not rhetoric** — "I could not verify,"
   "lower confidence," "strong hypothesis pending verification" — the label itself
   triggers re-verification.
4. **There is no "I assumed"** — even a flawless-looking assumption is forced
   through truth verification.

## Contributing a case

Real, desensitized cases are welcome by PR. Format and the non-negotiable
desensitization rules: see [CONTRIBUTING.md](CONTRIBUTING.md).

---
---

# 漂移纠错案例集(真实、脱敏)

> 英文完整版在上半部分;以下为中文完整版。

方法论在实际工作中触发并纠错的真实案例。所有项目名、代码符号、基础设施名、版本、
schema 提示、路径均已**移除**——只留漂移机制。通用、公开熟知的技术名词可保留。

**第一批来自一次 2–3 小时的连续工作。** 这是一次观测窗口,不是外推的平均率——
频率的诚实说明见 `README.md`。

## 漂移类型(速查)

- **① 实施层** —— 写代码时绕开规范、静默吞错、不可控副作用
- **② 认知层** —— 凭对话残留/印象/假设下结论,不读真实代码或配置
- **③ 结构放置** —— 治理文档腐化、放错分支、spec 与代码真值分叉
- **④ 范围** —— 越过项目显式的 IN/OUT 边界

## 索引

| # | 标题 | 漂移 | 触发 |
|---|---|---|---|
| 1 | 迁移脚本静默丢数据 | ② → ① | 执行前拦截 + grounding |
| 2 | 凭名字假设组件行为 | ② | 真值核查 |
| 3 | 过期示例配置 vs 真实配置 | ③ 近邻 | 改前先核实 |
| 4 | spec 与代码真值不符 → 阻塞 | ②+③ | "前提不成立"阻塞 |
| 5 | 无法验证的事实:标注而非下结论 | ② | 诚实标注 + 多源 |
| 6 | 强 bug 假设被强制验证 | ② 防 ① | 硬真值约束 |
| 7 | 外部 AI 方案在合并前被拦 | ②+③(+P0) | 合并前全仓扫描 |
| 8 | 单用户·单工作树·并行 → 治理险落错分支 | ③ | grounding 工作树/分支核查 |
| 9 | 形式完整 + 长自主 + compaction = 自审漏抓 | ② 链 | 外部人审 |
| 10 | 一个从来装不上的已发布治理插件 | ③ | 首次运行官方校验器 |
| 11 | 两道门拦同一条命令,功劳记错了对象 | ② | transcript 里的原始 hook stdout |
| 12 | 四个字符就能过的门,真正不可逆的操作却溜了 | ① | 读门自己的源码 |
| 13 | 装着三个版本,跑的是已被删除的二进制 | ② | `CLAUDE_CODE_EXECPATH` 对照磁盘 |
| 14 | 十来条并行工作流,漂移被清理,此后再没有过戏剧性拯救 | ② 规模化 | 项目内审计轮次 |

---

### 案例 1 —— 会静默丢数据的迁移脚本(②触发①)

**情境。** 在两个 SQL 存储之间做数据迁移,有一份过期交接文档作引导。

**漂移。** 迁移脚本的表名列表是凭印象写的(一个更简单的错名)。两端真实存储用的是
另一个真实名字,里面有真实数据行。那个错名两端都不存在。

**纠错。** 首条命令被执行前的拦截挡住——没让它跑。没有信过期交接文档,而是做只读
grounding 核对两端真实存储,并**读了脚本源码**(没猜):拷贝循环和校验循环用的是
同一份坏列表,不在列表里的一律跳过。后果链:错名被跳过;真表不在列表里,**根本
不会被遍历** → 它的数据行会被静默丢弃。更糟:脚本自带的双向计数校验用的是*同一份*
坏列表,查不到这次丢失,会照常打印成功、全绿。

**修复。** 一处、root-cause、最小 diff:把列表改成与真实表对齐。

**如果未拦截。** 真实数据行静默丢失;自检全绿;"迁移成功"。

### 案例 2 —— 凭名字假设组件行为(②)

**情境。** 准备某组件的备用部署,需要确认它的方式/格式。

**漂移。** 制品的*名字*暗示了一种方式。它实际的配置清单声明的是另一种类型、另一种
方式。部署必须按真实配置走,不按名字。

**纠错。** 没凭名字假设——直接读配置清单。同时主动承认第二处不确定(一项能力尚未
坐实),没有去猜 API,而是读实际安装的源码确认该构建到底支持什么。

**修复。** 真值以声明/注册的配置为准,不以制品名字为准。

**如果未拦截。** 部署配置错;失败方式是静默的(能加载、功能就是不生效)——日后更难
定位。

### 案例 3 —— 过期示例配置 vs 真实配置(③ 近邻,防过度变更)

**情境。** 计划停掉一个非生产组件;*以为*还需要协同改一个独立网关。

**漂移。** 仓库的 `*.example` 配置写的是双端点;真实部署的配置只用了一个。示例只是
过期了。

**纠错。** 读真实部署配置,不读示例。那个协同网关变更其实没必要——计划动作对另一个
组件零影响。一整个有风险的生产变更被从计划里拿掉。

**修复。** 按真实配置行动;过期示例暗示的东西不碰。

**如果未拦截。** 一次完全没必要的生产变更——每次多余的生产改动都是无收益的额外风险。

### 案例 4 —— spec 与代码真值不符 → 阻塞,不推进(②+③)

**情境。** 一份 spec 和一些系统描述描述了某基线;实际运行的现实与之不同。

**漂移。** spec 与描述都和现实脱节(③ 文档腐化);照它们推进会叠加②。

**纠错。** 读代码 → 发现当前现实 ≠ spec 所述基线。把每处不符标"不当真值",并提出
**阻塞:"你的前提不成立"**——不推进;先对齐,再用代码真值反过来更新治理文档(不是
反着来)。

**修复。** 治理文档以代码真值为准;spec 被改成与现实一致,而不是照它行动。

**如果未拦截。** 所有下游决策建立在错误前提上;等暴露时已堆了几层错,定位代价数倍。

### 案例 5 —— 无法验证的事实,标注而非下结论(②)

**情境。** 确认某个被点名的制品/变体是否存在、是否可用。

**漂移(被规避)。** 主查询通道在工作机上不可靠;那个事实在那里**无法权威验证**。

**纠错。** 没下结论也没编造——明确标注"**没能从这里验证;不能就此下结论**",改走
可达的并行通道。能直接读到的源用满档可信度;读不到的**降一档**,不与高可信度结论
混用。结果:spec 点名了一个**不存在**的制品、以及一个资源装不下的变体。

**修复。** 选定具体制品这类决策上交给人;方法论不静默自选。

**如果未拦截。** 朝一个不存在/装不下的目标推进;所有下游工作作废。

### 案例 6 —— 强 bug 假设被强制走验证(② 防 ①)

**情境。** 一个客户端报错,有一套完全自洽、能解释所有现象的 root-cause 故事。

**漂移(被规避)。** 这个假设*太*自洽,很容易被当结论直接动手。

**纠错。** 它被标注为"**强假设——待真值验证,不凭印象**",硬规则强制在任何改动前
先读真实接口契约和真实源码。

**修复。** 基于读到的真值改,不基于假设改——无论假设多有说服力。

**如果未拦截。** 很可能"修"错地方:真因若在别处,现象依旧 *且* 把对的代码改坏——
回滚 + 返工,代价翻倍。

### 案例 7 —— 外部 AI 的方案在合并前被拦(②+③,外加一个 P0)

**情境。** 请来第二个 AI 助手当顾问,它为这个仓库本身写了一份多步修改方案。该方案
在任何东西合并**之前**被本地治理过了一遍。

**漂移(在顾问方案里)。** ② —— 凭对话残留下结论,没读全仓当前状态。③ —— 改一处
规则不扫全仓,会在多个文件造成 spec 分叉。外加一个 **P0,不可逆**:它会把一个真实
项目指纹发布进公开仓,违反仓库自己的范围边界承诺。

**纠错。** 合并前的全仓一致性扫描发现:与已合并约定冲突 5+ 文件、与方法论自身原则
矛盾 2 处、以及那个不可逆暴露——全部在落地前拦下。

**修复。** 方案被重做:狠抽象那处暴露、把规则改动全仓一致地扫一遍、消解内部矛盾。

**如果未拦截。** 首次公开发布就会破自己的承诺(范围边界宣称、刚发布的约定)、泄露
不可逆指纹、发出一个自相矛盾、以及一个会自我误报的检查器。这套方法论最强的证明,
不是抓人犯错——是抓*另一个被请来帮忙的 AI*,在它落地之前。

### 案例 8 —— 单用户、单工作树、并行 → 治理险落错分支(③)

**情境。** 一个 agent session 在主干写治理文档;同一人在另一处、对**同一个工作目录**做别条线的工作,`checkout` 切了分支。

**漂移。** 分支状态是目录的属性,不是 session 的属性——于是治理修改"凭空"落到了那条功能分支(结构放置漂移的边缘)。没有第二个人,是自我碰撞。

**纠错。** session 启动 grounding 抓到所在工作树/分支不对;停下 + 排查 reflog,在它扩大前定位。根治是物理的:一线一独立工作树,主树钉死主干。

**修复。** 工作树纪律(第七原则·推论):每条线隔离在自己的工作树;主(主干)树内绝不切分支。

**如果未拦截。** 治理被 author 到功能分支、主干静默变旧——典型 ③;下个落旧主干的 session 读到全错。

### 案例 9 —— 形式完整 + 长自主执行 + compaction = ACGM 设计死角(② 链式失效)

**情境。** 沙盒评估类工作约 2 天,多次 session compaction,高密度 Bash 操作(含状态变更类:服务启停、制品加载/卸载、后台长跑任务)。

**漂移 —— 四步链,全是 ② 的不同变体:**

1. *Compaction 继承。* transcript 里出现 session 续接标记("This session is being continued from a previous conversation...")。服务、配置、资源状态的指称从压缩摘要继承,**无机制要求当下从源头 re-verify**。

2. *形式完整的 grounding 报告。* agent 输出一份结构化 grounding 报告——轨道 / git 状态 / 改动池 / 步骤,五块齐全。其中一些项(轨道、git 状态、最新提交)有同段对话内的工具调用证据。但另一些具体数字和指称声明(以往结果、资源上限)**在本段内无对应工具调用** —— 继承自 compaction 摘要。**形式上完美,实质上一半**。

3. *凭记忆操作命名。* agent 用 session 内别名(早先建立的一次性标签)当作正式服务标识符,直接发出破坏性 Bash,**未当下查询真实标识符**。真实名不同,该命令会停掉错的目标。

4. *启了就不管。* agent 启动一个自启动服务后,不再监控。服务挂掉、自启动循环、硬件风险——所有这些都**未被察觉**,直到数小时后用户主动指出。

**纠错。** 外部人审抓到这条链。方法论随即在规范层(元立场三层结构 + 多条新推论)+ 一个精准的机制层(PreToolUse 只盯破坏性 Bash + (a) 源验证机械化)同时扩,**且加入 CONTRIBUTING 的 2-独立证据规则**,以防止对这一次事故 1:1 过拟合。

**修复。** 规范明文命名每一类失效模式(操作真值 / async 自监控 / 破坏性前 grounding / compaction re-verify / 仪式合规判据);机制层覆盖可机械检查的子集;其余由审计层关闭——这是诚实立场,不是变通。

**如果未拦截。** 四层失效叠加 —— 停错目标、硬件风险被忽视、下游决策建立在继承的未验证事实上;事后定位代价数小时后指数放大。

**与案例 7 互为镜像。** 案例 7 是"外部 AI 的方案在合并前被本地治理拦下" —— 本地治理抓住外部漂移。**案例 9 是它的反镜**:本地治理在特定条件组合(长自主 + compaction + 形式完整)下**漏抓自己**。这是方法论的第二次自审时刻(第一次是 README 引用的那个 ②)。每次这样的时刻都是 ACGM 自身成长的契机,而不是 ACGM 失败的证据。

---

### 案例 10 —— 一个从来装不上的已发布治理插件(③)

**情境。** ACGM v0.1 于 2026 年 5 月公开发布,作者本机日常使用数月。2026-08-05,官方
校验器**第一次**被拿来跑这个仓库。

**漂移。** `plugin.json` 声明了 `"skills": "skills/"` 和 `"hooks": "hooks/hooks.json"`。
加载器要求声明路径以 `./` 开头;而 `hooks/hooks.json` 本就自动加载,再声明一次会作为
重复项失败。**这个已发布的包,谁都装不上。**

它在本机"能用"的原因比 bug 本身更糟。插件是通过 **directory 源 marketplace** 注册的,
而这种源同步的是**工作目录**,不是 git tree。建缓存时,工作区里恰好有一份未提交、且
此后从未提交过的 `plugin.json`,而那一份是合法的。于是**真正在运行的字节没有任何 git
身份**,缓存里还层积了来自三个不同提交的文件,外加一个未跟踪文件。

**修复曾经存在,而且被主动丢掉了。** 两个半月前那次发布的会话记录里,原样记着这个改动
——数组形式、删掉 `hooks` 键——当时它躺在工作区里,被以*"风险未知(可能破坏 hook 加载)、
超出本轮范围"*为由 `git checkout` 撤销。**被丢弃的正是缓存捕获的那一份。** 换句话说:
**manifest 唯一能用的版本,恰恰是被当作"太冒险而不予保留"的那一版**;撤销它,才使已发布
的包无法加载,而本机依旧运行如常。

当时的判断在局部是成立的:临近发布、超出本轮范围、一个未经验证的加载相关改动。缺的只是
那个几秒钟就能定论的廉价检查——**官方校验器,从来没被跑过**。

**为什么没人发现。** 后继版本加了约 4400 行测试、8 项发布契约检查、3 操作系统的 CI
矩阵。**没有任何一项调用过 `claude plugin validate`**,也没有任何一项问过"这个包能被
装上吗"。随后它又加了约 3670 行安装器去解决用户报告的安装失败。真实原因是两个缺失的
`./`。

**纠正。** 修 manifest;补上把加载器规则编码进去的契约测试;把"Claude Code 是否接受这
个包"做成 CI 任务——从检出目录真装一次,断言 `enabled`。同时记住:**`validate` 通过仍
然不等于能加载**——重复 hooks 那种配置校验器是放行的,加载器才拒绝。

**一般化。** 治理机制在治理任何东西之前,必须先证明自己装得上。**测试的体量不是覆盖率;
4400 行从不追问那个关键问题的测试,是 4400 行的自我安慰。**

---

### 案例 11 —— 两道门拦同一条命令,功劳记错了对象(②)

**情境。** 同一 Session 中,一条破坏性 `rm -rf` 被执行前的门拦下。Agent 报告说是 ACGM
自己的 hook 拦的。

**漂移。** 当时装着两个插件,各有一道 PreToolUse 门。**渲染给用户看的那段文字来自第三方
那个。** Agent 根据看到的文字、以及自己对"哪个机制在起作用"的预期,把拦截归给了 ACGM。
后来它从措辞对不上察觉有异,自我纠正为"根本不是 ACGM"——**这次又错了,方向相反**。

只有原始 hook 输出能定论:transcript 里有一条 `PreToolUse` attachment,其 stdout 携带
ACGM 自己的 `permissionDecision: "ask"`,对应的正是那一条 `toolUseID`。**两道门都开火
了。** 在读证据之前,agent 已经朝两个相反方向各错了一次。

**为什么这条特别重要。** 本项目的证据登记表里,已经有一条被判为 Rejected 的同型主张:
早先一次被记为 ACGM 拦截的事件,查实是第三方门拦的。**这个失效模式,在记录了它的项目
里,换了一个 agent,又复现了一次。**

**纠正。** 归属判定必须用机制自身的输出,并以工具调用为键——不能用人恰好看到的那段文字,
也不能用"没出现预期措辞"来反推。**在 transcript 里 grep 门的文本也不算归属**:那次计数
就被污染了,因为 agent 几分钟前刚把 hook 脚本 `cat` 进了同一份 transcript。

**一般化。** 在有多道护栏的环境里,"是什么拦住了它"是一个证据问题。**无法与某个机制对上
号的拦截,不是你可以宣称的战果。**

---

### 案例 12 —— 四个字符就能过的门,真正不可逆的操作却溜了(①)

**情境。** 在门刚刚开过火的同一 Session 里,读它的源码。

**漂移——机制自身的三个缺陷。**

1. *该用结构的地方用了文字。* 门 grep agent 上一条回复里的字面标记 `(a)`–`(d)`。**四个
   字符就能满足它。** 从机械层面看,形式合规就是放行条件——恰恰是方法论自己命名的"表演式
   服从"。
2. *白名单错配。* 本 Session 真正不可逆的操作是插件卸载,**不在破坏性清单里,静默通过**。
   而被拦下的那条,目标是一个**并不存在的目录**。门抓住了无害的,漏掉了真的。
3. *绕过成本为零。* 被拦一次后,agent 把 `rm -rf` 从命令里删掉,继续执行。结果是好的
   ——那次删除本就多余——**但什么都没被验证。门改变的是措辞,不是证据。**

同一天,PostToolUse hook 暴露了第四个缺陷:在一次**误报**上,它**把一条标记注释追加写进
了它刚刚标记的那份治理文件**。而 skill 正文明写它不会改文件。实现与文档不一致,并且
**一个静默改写被治理对象的治理机制,本身就是一次未记录的状态变更**。

**纠正。** 改判结构而非文字——具名字段且有真实内容;操作独占一次工具调用,不得有
`;`/`&&`/pipe/被计算出的目标;本 Session 内此前必须已有只读调用。这三条都能从工具调用和
transcript 判定,所以**都不能靠写文字生产出来**。白名单扩到插件/包/配置状态。PostToolUse
改为只给 advisory,不碰任何文件。

**一般化。** 读 agent **说了什么**的门,量的是合规表演;读 agent **做了什么**的门,量的是
证据。**宁要"粗检测 + 廉价响应",不要"精检测 + 昂贵响应"。**

---

### 案例 13 —— 装着三个版本,跑的是已被删除的二进制(②)

**情境。** 起因只是一个问题:为什么这个会话的上下文窗口比预期小。

**漂移。** 同一个工具的三份安装同时存在:包管理器在磁盘上的一份是一个版本,桌面应用自带
的一份是第二个版本,而**真正在执行的进程是第三个版本**——它的目录在启动过程中被替换,
进程于是运行在一个已被 unlink 的文件上。

**每一种单点检查都给出了不同的、且自信的错误答案。** shell 里 `tool --version` 报的是包
管理器那份;列应用目录看到的是自带那份;只有运行进程自身的 `EXECPATH` 揭示了实际执行的
是什么——而那个路径**在磁盘上已经不存在了**。

**纠正。** 读运行进程自身的身份,而不是经 `PATH` 解析出来的名字,也不是目录列表。

**一般化。** 这是四状态分离最纯粹的形态。**源已验证、配置已验证、运行时已激活,在同一
时刻是三个不同的答案**——而运行时那个答案在磁盘上根本没有可对照的身份。任何"我们正在运行
版本 X"的说法,要么拿得出运行时自身的证据,要么它只是穿着运行时外衣的配置。

---

### 案例 14 —— 拯救只发生一次,此后成功的样子就是什么都没发生(② 规模化)

**情境。** 2026 年 5 月,一个后来上线的长周期应用。**大约十条并行工作流**同时跑在同一个
项目上。它们之间的信息误差,用所有者的话说,已经是**灾难性的**:session 互相继承对方
的陈旧结论、一条流里已经推翻的决定在另一条流里仍然生效、**没有任何共识来判断哪句话是
当前的**。

这正是四类漂移同时发生、并且互相放大的状态。

**治理层装上之后发生了什么。** 几轮**项目内审计**——不做新功能,只是拿当前真值源去对
文档里的说法——把积压的工作树混乱、漂移和腐化清理掉了。**那个阶段的效果剧烈且一眼可见。**

**然后它就不再剧烈了。** 此后数月,这一层很少再产生什么"像是拯救"的时刻。不是因为它
不работает了,而是因为**绝大多数问题现在死在第一轮**——死在"核对真实状态"那一步,还没
长成值得起名字的东西。所有者自己的总结:*之后不太有那种"拯救了项目"的感觉;但如果没有
这个东西,这个项目没法推进到这个程度。*

**这个案例真正在讲的事。** 治理的回报是**前置的,然后隐形**:

| 阶段 | 它在做什么 | 看起来是什么样 |
|---|---|---|
| 第一阶段 | 清理存量腐化 | 剧烈、可数、明显 |
| 之后 | 阻止增量腐化 | **什么都没发生** |

用"救了几次"去衡量,第二阶段的读数**恒为零**。**一个不再惊心动魄的工具,不等于一个不再
重要的工具**——那恰恰是一个有效的预防机制该有的样子。

**由此得到的报告纪律。** 干预次数下降是成功的预期特征,因此**它单独作为证据,朝任何方向
都是无效的**。它必须带分母报告——机制到底有过多少次机会——这正是 `acgm_activity.py` 把
`ACTIVE` 和 `ACTIVE (untested)` 分开、并把后者视为**正常健康状态而非警告**的原因。

**边界,刻意写明。** "没有它这个项目推进不到这个程度"是所有者对一个**无法被检验的反事实**
的判断。这里如实记录为他的判断,**本仓库任何地方都不把它当作已验证的主张**(EVIDENCE
E-026)。

---

## 联起来看

| 案例 | 触发 | 关键动作 |
|---|---|---|
| 1 | 执行前拦截 + grounding | 拦命令 → 读真实存储 → 读源码 → 推后果 |
| 2 | 真值核查 | 拒绝凭名字假设 → 读配置 + 源码 |
| 3 | 改前先核实 | 读真实配置 vs 过期示例 → 砍掉多余变更 |
| 4 | 前提不成立即阻塞 | 现实 ≠ spec → 拒绝推进 |
| 5 | 诚实标注 | 无法验证 → 标注 + 按可信度分档,不混用 |
| 6 | 硬真值约束 | 强假设 ≠ 结论 → 强制读真值 |
| 7 | 合并前全仓扫描 | 外部方案 vs 全仓 → 落地前拦截 |
| 8 | grounding 工作树/分支核查 | 共用目录+切分支 → 在治理落到错分支前拦下 |
| 9 | 外部人审 | 规范+机制层一并扩,同时加 2-独立证据规则防止过拟合 |

**共同模式:**

1. **动手前停一下** —— 几乎每个案例都是在"快要动手"那一刻被拦下,不是事后补救。
2. **拒绝把非代码输入当真值** —— 名字、spec、系统描述、过期交接、过期示例、自洽
   假设,全都不算。
3. **诚实标注是机制不是修辞** —— "我没能验证""可信度低一档""强假设待验证"——
   标注本身就触发再次验证。
4. **不存在"我以为"** —— 即使假设看起来无懈可击,照样强制走真值验证。

## 贡献案例

欢迎 PR 提交真实、脱敏的案例。格式与不可商量的脱敏要求:见
[CONTRIBUTING.md](CONTRIBUTING.md)。
