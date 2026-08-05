# ACGM evidence register

This register tracks the maturity of **claims**, not the popularity of wording.
It exists to stop one incident, one repeated reminder, or one attractive
explanation from quietly becoming a universal rule.

Register review: 2026-08-05 (v0.4.0).

## Maturity states

| State | What has been established | What may ship |
|---|---|---|
| **Observed** | one traceable real occurrence | a case, instrumentation, or a scoped trial — not a universal claim |
| **Reproduced** | the same mechanism occurs again under documented conditions | a scoped trial with explicit limits |
| **Corroborated** | independent observations, or observation plus faithful reproduction | stable normative wording and default behaviour |
| **Predictive** | reasoned and testable, not directly observed | a meta-observation or a test plan; never a default blocker |
| **Rejected** | contradicted, misattributed, or incident-shaped | historical record only; remove from active claims |

A state belongs to one claim, not to a topic. One case can hold an Observed weak
form and a Predictive strong form. Status changes are append-only: add a dated
note, never rewrite away the earlier judgment.

## Register

| ID | Claim | State | Evidence | Limits |
|---|---|---|---|---|
| E-001 | "ACGM's own hook intercepted the command" | **Rejected** (2026-05) | attribution audit: a third-party pre-execution gate held it | the specific win was not ACGM's |
| E-001b | Attribution to the wrong guardrail recurs whenever more than one is installed | **Reproduced** (2026-08-05) | Case 11 — two gates fired on one `toolUseID`; the agent credited the wrong one, then over-corrected to "neither", before reading raw hook stdout | attribution needs mechanism output keyed by tool call; transcript text-grep is contaminated by the agent's own quoting |
| E-002 | High-risk actions need current target / state / authority / postcondition evidence | **Corroborated** | earlier cases; plus 2026-08-05, writing `ACGM-ROLLBACK` is what prompted a cache backup that preserved the only surviving copies of three files | a filled template is not proof; a mechanism may check only a subset |
| E-003 | A started or exit-zero action retains a post-action verification obligation | **Corroborated** | earlier cases | a runtime that cannot wake later must record `pending verification`, not promise completion |
| E-014 | A text-matching gate measures compliance theatre, not evidence | **Observed** (2026-08-05) | Case 12 — the v0.1 gate passed on the literal string `(a)(b)(c)(d)`; when it did fire, the agent rewrote the command instead of producing evidence | one session, one agent; the structural replacement is new and unproven at scale |
| E-015 | A verified plugin record or cache does not prove the target runtime loaded anything | **Corroborated** (2026-08-05) | Case 10 — a published manifest that no clean install could load, while a directory-source cache made it appear healthy; Case 13 — three installed versions with the running process on a fourth, unlinked, path | doctor therefore reports activation as not provable from a subprocess |
| E-016 | A directory-source plugin cache syncs the working tree, so running bytes may have no Git identity | **Reproduced** (2026-08-05) | per-file hashing of the local cache: files from three separate commits, one untracked file, and one manifest matching no commit; `installed_plugins.json` recorded a single unrelated commit sha | `plugin update` is a no-op while the version string is unchanged; only uninstall + reinstall re-syncs |
| E-017 | Passing the official validator does not mean the plugin loads | **Observed** (2026-08-05) | a manifest declaring `hooks/hooks.json` validated cleanly and was refused at load time as a duplicate | CI must attempt a real install, not only validation |
| E-018 | Test volume is not coverage | **Observed** (2026-08-05) | the 0.3.0-rc line: ~4400 lines of tests, an 8-check release contract and a 3-OS matrix, none of which invoked `claude plugin validate` or attempted an install; ~3670 lines of installer were written to solve a two-character manifest bug | one project, one release line; stated as a caution, not a law |
| E-019 | A governance mechanism that edits the artifact it governs is itself an unlogged state change | **Observed** (2026-08-05) | Case 12 — the PostToolUse hook appended a marker into a CLAUDE.md on a false positive, while the skill text promised it did not edit files | corrected by making the response an advisory; the detector stays coarse on purpose |
| E-020 | A test suite that reads the process environment inside the code under test passes in CI and fails on real machines | **Reproduced** (2026-08-05) | the 0.3.0-rc suite: 2 failures locally, 156/156 with `CLAUDECODE` unset; CI never runs inside Claude Code so it was always green | v0.4 runs its suite with the variable both set and unset |
| E-021 | A gate keyed on the command string is a speed bump, and rewards learning nothing | **Observed** (2026-08-05) | a third-party pre-execution gate, read at source: it denies once per `sha256(command)` and allows the identical command on retry. Its own message demands three facts; **no code path reads them**. Improving the command produces a new hash and is blocked again, so resubmitting unchanged is the cheapest route | states the general shape ACGM must avoid; ACGM's own v0.1 gate was a weaker instance of it (E-014) |
| E-026 | Governance return is front-loaded, then invisible; a falling intervention count is the signature of success | **Observed** (2026-05 → 2026-08) | Case 14 — around ten parallel work streams with catastrophic cross-stream drift; a few audit rounds cleared the accumulated rot, and in the months since the mechanism has rarely produced anything resembling a rescue, because problems die during the check-current-state step | single project, single operator, self-reported. The owner's "without it the project could not have been pushed this far" is a **counterfactual that cannot be tested** and is not treated as validated anywhere. What the entry does support is a reporting rule: a low trigger count is evidence in neither direction without its denominator |
| E-027 | The gate's field check depends on a race between transcript flush and hook execution | **Reproduced** (2026-08-05) | two calls of identical shape — fields written in the same assistant turn as the destructive command — one passed and one was denied for "FIELDS missing", with the text entry present and correctly ordered in the transcript both times | the visible direction is a false denial, which is safe. The invisible direction is worse: reading a stale turn surfaces an older turn's fields, which is E-025's false pass. BINDING is currently the only thing standing between that race and an unauthorised operation. Reading the fields from the transcript at all is the root cause |
| E-025 | Evidence keyed to "the most recent message" is reusable by the next operation | **Observed** (2026-08-05) | the gate reads the last assistant text; after a gated operation succeeded, those same fields remained the most recent text and a following destructive command passed on them. The pass was first misdiagnosed as the command not being destructive | fixed by requiring an operand of the command to appear in the fields. The mirror-image failure — fields written but not yet flushed to the transcript when the hook reads it — produces a false denial and is left as-is |
| E-024 | A gate that only asks lets imprecise patterns survive indefinitely | **Observed** (2026-08-05) | within one command of switching `ask` to `deny`, a read-only inspection of `~/.claude` was blocked because the agent-config rule counted `2>/dev/null` as a write. The same pattern had been shipping since v0.4.0 and cost nothing while the decision was `ask` | argues for denying early rather than "advisory first, enforce later": enforcement is what surfaces pattern debt. One occurrence; do not generalize to all mechanisms yet |
| E-023 | A PreToolUse `ask` is not a block; under an auto-accepting permission mode it is a no-op | **Observed** (2026-08-05) | ACGM v0.4.0 returned `ask` against a real destructive command; the transcript shows the hook fired with that exact `toolUseID`, and the command executed with no prompt. No allow-rule in user or project settings matched it. The weaker third-party gate held the same class of command because it returns `deny` | v0.4.1 denies an incomplete gate and emits no decision for a complete one, so the human is reached through the normal flow. A hook cannot rely on the operator's current mode to enforce anything |
| E-022 | Substring matching over a whole Bash invocation misfires on data the command carries | **Reproduced** (2026-08-05) | a commit message *describing* a recursive delete tripped two independent gates, twice each; the heredoc body is text being written, not an operation | v0.4 strips heredoc bodies before matching and keeps the `<<TAG` line, so a destructive command that also feeds a heredoc is still caught |

## Release review

Before a release, review every entry the release touches:

1. No changed normative or mechanical claim is unregistered.
2. Default hard gates and stable rules are Corroborated.
3. Observed and Reproduced trials either stay scoped with explicit limits, get
   promoted with evidence, or get rejected.
4. Predictive entries stay non-blocking and keep a path to a test.
5. Rejected claims are absent from active documentation and behaviour, while the
   correction stays visible here.

---

# ACGM 证据登记表

本表跟踪**主张**的成熟度,不是措辞的流行度。它存在的目的,是阻止"一次事件""一句反复
提醒""一个动听的解释"悄悄变成普遍规则。

登记表复核:2026-08-05(v0.4.0)。

## 成熟度状态

| 状态 | 已建立什么 | 可以发布什么 |
|---|---|---|
| **Observed 已观察** | 一次可追溯的真实发生 | 案例、instrumentation 或有范围的试用——不是普遍主张 |
| **Reproduced 已复现** | 同一机制在有记录的条件下再次发生 | 有明确边界的范围内试用 |
| **Corroborated 已佐证** | 独立观察,或观察 + 忠实复现 | 稳定的规范措辞与默认行为 |
| **Predictive 推演** | 有推理、可测试,但未直接观察到 | 元观察或测试计划;**绝不作默认拦截** |
| **Rejected 已否决** | 被推翻、归属错误,或只是个别事故 | 仅作历史记录;从生效主张中移除 |

状态属于**一条主张**,不属于一个话题。同一个案例可以同时有 Observed 的弱形式和
Predictive 的强形式。状态变更只追加:加一条带日期的说明,**不许把先前的判断改掉**。

## 登记

| ID | 主张 | 状态 | 证据 | 边界 |
|---|---|---|---|---|
| E-001 | "是 ACGM 自己的 hook 拦下了那条命令" | **Rejected**(2026-05) | 归属审计:实际是第三方执行前门拦的 | 那次具体战果不属于 ACGM |
| E-001b | 只要装了不止一道护栏,归属错误就会反复发生 | **Reproduced**(2026-08-05) | 案例 11——两道门在同一 `toolUseID` 上开火;agent 先记错对象,又过度纠正为"两个都不是",直到读原始 hook stdout | 归属必须用以工具调用为键的机制输出;在 transcript 里 grep 文本会被 agent 自己的引用污染 |
| E-002 | 高风险操作需要当下的目标/状态/授权/后置条件证据 | **Corroborated** | 既往案例;另 2026-08-05,正是"写 `ACGM-ROLLBACK`"这一步促成了一次缓存备份,保住了三个文件仅存的副本 | 填满模板不是证明;机制只能检查子集 |
| E-003 | 已启动或 exit 0 的动作仍欠一次后验核验 | **Corroborated** | 既往案例 | 无法稍后唤醒的运行时必须记 `pending verification`,不得承诺自动完成 |
| E-014 | 文本匹配的门量的是合规表演,不是证据 | **Observed**(2026-08-05) | 案例 12——v0.1 的门被字面字符串 `(a)(b)(c)(d)` 满足;真正开火那次,agent 改写命令而非拿出证据 | 单 Session 单 agent;结构化替代方案是新的,尚未在规模上验证 |
| E-015 | 已验证的插件记录或缓存,不能证明目标运行时加载了任何东西 | **Corroborated**(2026-08-05) | 案例 10——一个 clean install 装不上的已发布 manifest,却因 directory 源缓存显得健康;案例 13——装着三个版本,运行进程却在第四条已被 unlink 的路径上 | 因此 doctor 把"运行时激活"报为**子进程无法证明** |
| E-016 | directory 源插件缓存同步的是工作目录,故运行字节可能没有任何 git 身份 | **Reproduced**(2026-08-05) | 对本机缓存逐文件哈希:来自三个不同提交的文件、一个未跟踪文件、一份不匹配任何提交的 manifest;而 `installed_plugins.json` 只记了一个不相干的 commit sha | 版本号不变时 `plugin update` 是空操作;只有卸载重装才会重新同步 |
| E-017 | 通过官方校验器不等于插件能加载 | **Observed**(2026-08-05) | 声明了 `hooks/hooks.json` 的 manifest 校验干净通过,加载时以"重复"被拒 | CI 必须尝试真实安装,不能只做校验 |
| E-018 | 测试的体量不是覆盖率 | **Observed**(2026-08-05) | 0.3.0-rc 线:约 4400 行测试、8 项发布契约、3 操作系统矩阵,无一调用 `claude plugin validate` 或尝试安装;为一个两字符的 manifest bug 写了约 3670 行安装器 | 单项目单发布线;作为告诫,不作定律 |
| E-019 | 会修改被治理对象的治理机制,本身就是一次未记录的状态变更 | **Observed**(2026-08-05) | 案例 12——PostToolUse hook 在一次误报上往 CLAUDE.md 追加了标记,而 skill 正文声称它不改文件 | 已改为只给 advisory;检测器**故意保持粗糙** |
| E-020 | 在被测代码内部读进程环境的测试套件,会 CI 全绿、真机报错 | **Reproduced**(2026-08-05) | 0.3.0-rc 套件:本机 2 项失败,`CLAUDECODE` 清掉后 156/156;CI 永远不在 Claude Code 里跑,所以一直是绿的 | v0.4 的套件在该变量设与不设两种情况下各跑一次 |
| E-021 | 以命令字符串为键的门只是减速带,而且奖励"什么都没学到" | **Observed**(2026-08-05) | 读了某第三方执行前门的源码:它按 `sha256(命令)` 只拒一次,同样的命令重交即放行。它的提示要求三项事实,**代码里没有任何一处读取它们**。改进命令会产生新哈希、再次被拒,于是**原样重交是最省事的路径** | 这条描述的是 ACGM 必须避免的一般形态;ACGM 自己 v0.1 的门是它的弱化版(E-014) |
| E-026 | 治理回报前置、随后隐形;干预次数下降是成功的特征 | **Observed**(2026-05 → 2026-08) | 案例 14 —— 约十条并行工作流、跨流漂移灾难性;几轮审计清掉存量腐化,此后数月机制很少再产生像样的"拯救",因为问题都死在核对当前状态那一步 | 单项目、单使用者、自述。所有者那句"没有它推进不到这个程度"是**无法检验的反事实**,任何地方都不作已验证处理。本条真正支撑的是一条报告纪律:**低触发数在没有分母时,朝任何方向都不是证据** |
| E-027 | 门的字段检查依赖"transcript 落盘"与"hook 执行"之间的竞态 | **Reproduced**(2026-08-05) | 两次形状完全相同的调用——字段与破坏性命令写在同一个 assistant 轮次——**一次通过,一次以"FIELDS 缺失"被拒**,而两次的文本条目都在 transcript 里且顺序正确 | 可见的方向是误拒,安全。**不可见的方向更糟**:读到陈旧轮次就会看到更早那一轮的字段,即 E-025 的假放行。**BINDING 目前是唯一挡在这场竞态和一次未授权操作之间的东西**。根因是"从 transcript 里读字段"这件事本身 |
| E-025 | 以"最近一条消息"为键的证据,会被下一个操作复用 | **Observed**(2026-08-05) | 门读最后一段 assistant 文本;一次受门操作成功后,同一份字段仍是最新文本,**紧接着的破坏性命令就靠它通过了**。这次通过起初被误判成"该命令不算破坏性" | 修法是要求字段中出现命令的一个操作对象。镜像的失效——字段写了但 hook 读取时尚未落盘——产生的是误拒,安全,故只记录不修 |
| E-024 | 只会"问"的门,会让不精确的匹配模式无限期存活 | **Observed**(2026-08-05) | 从 `ask` 改成 `deny` 之后的**第一条命令**,就是一次对 `~/.claude` 的只读检查被拦——因为 agent 配置规则把 `2>/dev/null` 里的 `>` 算成了写入。同一个模式从 v0.4.0 起就在跑,在裁决是 `ask` 时它不产生任何代价 | 支持"早点真拦"而不是"先建议、以后再强制":**是强制本身让模式债浮出水面**。单次观察,尚不可推广到所有机制 |
| E-023 | PreToolUse 的 `ask` 不是阻断;在自动接受的权限模式下它是空操作 | **Observed**(2026-08-05) | ACGM v0.4.0 对一条真实破坏性命令返回 `ask`;transcript 显示 hook 确实以该 `toolUseID` 触发,而命令**无任何提示直接执行**。用户级与项目级 settings 中没有任何 allow 规则命中它。那个弱得多的第三方门反而拦住了同类命令,**因为它返回 `deny`** | v0.4.1 对不完整的门返回 `deny`,对完整的门不发裁决,让人通过正常流程拍板。**hook 不能依赖操作者当前的模式来实施任何约束** |
| E-022 | 对整条 Bash 调用做子串匹配,会被命令携带的数据误伤 | **Reproduced**(2026-08-05) | 一条**描述**递归删除的 commit message 触发了两道独立的门、各两次;heredoc 正文是被写入的文本,不是被执行的操作 | v0.4 在匹配前剥离 heredoc 正文并保留 `<<TAG` 行,因此"既执行破坏性操作又带 heredoc"的命令仍会被抓住 |

## 发布复核

发布前,逐条复核本次发布触及的条目:

1. 没有任何被改动的规范或机制主张是未登记的。
2. 默认硬拦截与稳定规则,状态必须是 Corroborated。
3. Observed / Reproduced 的试用,要么保持有明确边界的范围,要么带证据升级,要么否决。
4. Predictive 条目保持非阻断,且有通往测试的路径。
5. 被否决的主张从生效文档与行为中移除,但**纠正过程仍留在此处可见**。
