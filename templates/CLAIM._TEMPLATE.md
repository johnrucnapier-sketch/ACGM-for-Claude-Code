# C-<YYYYMMDD-NN>: <一句话说清收敛了什么 / what converged>

草案。由 agent 起草，**未经人确认**。它记录的是"一个开放线程闭合了"，不是"一件事被
决定了"——后者要人盖章才成立。

A draft, written by the agent and **not confirmed by a human**. It records that an
open thread closed. It does not establish that anything was decided.

- **编号 / Id:** C-<YYYYMMDD-NN>
- **起草于 / Drafted:** <YYYY-MM-DDThh:mmZ>
- **起草依据 / Closure signal:** <human_ruling | topic_moved | entered_implementation | objection_closed>
  - 必填，且只能是这四个之一。弱信号不构成闭合，不得起草。
- **闭合线程 / Closes thread:** <T-NNNN>
- **关联 HEAD / At commit:** <当时的 commit sha>
- **状态 / Status:** 待认定 / pending

## 收敛了什么 / What converged
<从什么候选集合，收敛到什么。一句话。>

## 依据 / Basis
<本 session 内的取证：file:line、命令输出。>
<没有取证就写「无，仅对话推断」——不许留空，不许编。>

## 未收敛的部分 / Still open
<这条线程闭合了，但顺带暴露出的新问题写这里，并在 OPEN_THREADS.md 里开新线程。无则填「无」。>
