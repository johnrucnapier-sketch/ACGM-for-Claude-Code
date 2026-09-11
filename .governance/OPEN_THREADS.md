# 开放线程 / Open threads

状态文件：重写，不追加。闭合的线程离开本表，以 `claims/` 草案形式继续存在。

最后更新：2026-09-11T09:10Z · HEAD d79fd58（本次账本提交之前）

| 线程 | 问题 | 提出于 | 状态 |
|---|---|---|---|
| T-0012 | 本地的不透明执行同样不开火：`bash X.sh`、`python X.py`、`make deploy`、`npm run migrate` 均已实测放行。是否比照远程处理 | 2026-09-11 | 开放，等人裁定。远程已修，本地未修，两者是同一个缺口 |
| T-0013 | 门仍会把**命令携带的数据**当成命令：本 session 一条只读 `grep`（搜索词含破坏性动词）与一条 commit（正文含命令替换字面量）各被误拦一次。E-022 在 heredoc 之外的同族 | 2026-09-11 | 开放，等人裁定 |
| T-0009 | `.governance/` 随仓库被打进插件包，导致每次账本提交都让 `cache matches source` 报 FAIL、都要重装一次 | 2026-09-11 | 开放，等人裁定。**本 session 已实际发生四次**，不再是推测 |
| T-0007 | 工作分支名 `feat/v0.4.0` 与其内容（0.9.2、跟踪 `origin/main`、事实上的主干）不符，是否改名 | 2026-09-11 | 开放，等人裁定 |
| T-0010 | 发布是否应当打 tag（`claude plugin tag` 可用但从未使用，远端零 tag） | 2026-09-11 | 开放，等人裁定 |

## 已闭合 / Closed this session

- T-0001 → `claims/C-20260911-01.md` —— doctor `cache matches source` 改为对 marketplace 源目录比对
- T-0002 → `claims/C-20260911-02.md` —— 重装走 uninstall + install，不走 update
- T-0005 → `claims/C-20260911-03.md` —— 从本地目录源安装时，顺序固定为「先提交，再重装」
- T-0003, T-0004, T-0006 → `claims/C-20260911-04.md` —— 立案 Case 17 / E-033、版本提至 0.9.1、Git 陈旧引用清理
- T-0008 → `claims/C-20260911-05.md` —— 四个提交推送至 GitHub main，本次不打 tag
- T-0011 → `claims/C-20260911-06.md` —— 远程执行按载荷判定，v0.9.2，误报率以本机历史实测校准

## 未确认草案 / Unconfirmed claims

C-20260911-01 至 C-20260911-06 均为 `pending`。人尚未对其内容逐条盖章，
不得升级至 `decisions/`。
