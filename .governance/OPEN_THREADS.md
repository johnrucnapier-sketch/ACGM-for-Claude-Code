# 开放线程 / Open threads

状态文件：重写，不追加。闭合的线程离开本表，以 `claims/` 草案形式继续存在。

最后更新：2026-09-11T08:22Z · HEAD ab7b818

| 线程 | 问题 | 提出于 | 状态 |
|---|---|---|---|
| T-0003 | doctor 自指缺陷是否值得在 `CASES.md` 立案：一个自检脚本在其**官方推荐调用路径**下产出恒真绿灯 | 2026-09-11 | 开放，等人裁定 |
| T-0004 | 本次 doctor 行为变更是否需要把版本从 0.9.0 提到 0.9.1 | 2026-09-11 | 开放，等人裁定 |
| T-0006 | 陈旧的 remote-tracking ref（origin/master、origin/codex/* 共 5 个，GitHub 上已删除）与本地 master 分支是否清理 | 2026-09-11 | 人已表示暂缓；未正式裁定为「不做」 |

## 已闭合 / Closed this session

- T-0001 → `claims/C-20260911-01.md` —— doctor `cache matches source` 改为对 marketplace 源目录比对
- T-0002 → `claims/C-20260911-02.md` —— 重装走 uninstall + install，不走 update
- T-0005 → `claims/C-20260911-03.md` —— 从本地目录源安装时，顺序固定为「先提交，再重装」

## 未确认草案 / Unconfirmed claims

C-20260911-01、C-20260911-02、C-20260911-03 均为 `pending`。人尚未对其内容逐条盖章，
不得升级至 `decisions/`。
