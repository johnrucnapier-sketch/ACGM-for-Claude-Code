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

## 发布复核

发布前,逐条复核本次发布触及的条目:

1. 没有任何被改动的规范或机制主张是未登记的。
2. 默认硬拦截与稳定规则,状态必须是 Corroborated。
3. Observed / Reproduced 的试用,要么保持有明确边界的范围,要么带证据升级,要么否决。
4. Predictive 条目保持非阻断,且有通往测试的路径。
5. 被否决的主张从生效文档与行为中移除,但**纠正过程仍留在此处可见**。
