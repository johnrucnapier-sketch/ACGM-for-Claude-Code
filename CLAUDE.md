# CLAUDE.md — project working agreement

This repository is governed by ACGM (Agent Coding Governance Methodology).
ACGM is self-contained: it does not require, extend, or delegate to any other
skill system. This file states how ACGM interacts with whatever else happens to
be installed in the operator's environment.

## Precedence

1. Instructions in this file and in the project Constitution.
2. ACGM skills (`session-grounding`, `truth-first`, `governance-bootstrap`).
3. Everything else.

## Evidence before ritual

The session opens by reading current truth sources — code, configuration, Git
state — not by performing a procedural check.

Some skill systems install a meta-rule requiring a specific ritual (for example,
a mandatory skill lookup) before any response, including clarifying questions.
In this project that ritual is **absorbed by ACGM grounding**, not executed
separately: grounding's track-and-scope determination *is* the method selection.
Do not run a separate pre-response ceremony ahead of reading current state.

This is an ordering rule, not a prohibition. Any skill that genuinely fits the
task may be invoked — after grounding, on evidence, like any other tool.

## High-risk operations

Irreversible, destructive, or state-changing operations follow the ACGM gate:
read-only source check, current state, post-action verification, rollback plan —
each in its own tool call, stated before the operation, and never treated as
authorization by itself.

## Truth sources

`METHODOLOGY.md` / `METHODOLOGY.en.md` are the normative text. `CASES.md` records
observed incidents. Neither is a cache of current technical fact: for anything
about how this repository actually behaves right now, read the code, the manifest,
and the Git state in this session.

---

# CLAUDE.md — 本项目工作约定

本仓库由 ACGM（Agent 编码治理方法论）治理。ACGM 独立自洽：不要求、不扩展、不
委托任何其他 skill 体系。本文件只说明 ACGM 与操作者环境中恰好装着的其他东西
如何相处。

## 优先级

1. 本文件与项目宪法中的指令。
2. ACGM skills（`session-grounding`、`truth-first`、`governance-bootstrap`）。
3. 其余一切。

## 先取证，后仪式

会话开局先读当前真值源——代码、配置、Git 状态——而不是先执行某个流程检查。

某些 skill 体系会安装一条元规则，要求在任何回复（包括澄清提问）之前先完成特定
仪式，例如强制的 skill 查找。在本项目中，该仪式**由 ACGM grounding 吸收**，不
单独执行：grounding 的轨道与范围判定本身就是方法选择。不要在读取当前状态之前
先跑一遍额外的开场仪式。

这是顺序规则，不是禁令。确实贴合任务的 skill 照常可以调用——在 grounding 之后，
基于证据，和任何其他工具一样。

## 高风险操作

不可逆、破坏性或状态变更操作走 ACGM 证据门：只读取证、当前状态、后验核验、回滚
方案——各自独立的工具调用，在操作前写出，且其本身永远不构成授权。

## 真值源

`METHODOLOGY.md` / `METHODOLOGY.en.md` 是规范文本，`CASES.md` 记录已观察到的
事件。两者都不是当前技术事实的缓存：任何关于本仓库此刻实际行为的问题，都要在本
Session 内重读代码、manifest 和 Git 状态。
