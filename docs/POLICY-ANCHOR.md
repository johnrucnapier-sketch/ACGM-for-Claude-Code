# v0.9.4: stable policy anchor

## 确定性规则

1. ACGM_POLICY_CONFIG 存在时必须是绝对路径，始终最高优先级。加载失败即 DENY；
   不退回默认 discovery。即使 CLAUDE_PROJECT_DIR 缺失，显式配置仍可用。
2. 否则要求真实 Harness 的绝对 CLAUDE_PROJECT_DIR，验证目录存在并规范化路径。
   不以 payload.cwd、Hook cwd 或临时 shell cwd 代替。缺失/异常时 fail-closed。
3. 从稳定启动目录执行只读 git rev-parse --show-toplevel：Git/worktree 项目用
   所属工作树根。清除影响定位的继承 GIT_* 环境变量，固定错误语言，超时 5 秒。
   Git 工具缺失、非“不是仓库”的错误、根不包含启动目录等均 fail-closed。
4. 明确非 Git 项目以启动目录为项目边界。不搜索其父目录，不向 / 搜索 governance。
5. 只加载 anchor/.governance/remote-path-guards.json。运行时 cd 进入其他目录，
   仍使用原 anchor；不会自动切换到另一个项目的 policy。

## 存在性与错误

| 状态 | 行为 |
|---|---|
| 稳定项目无 .governance | 普通无 guard 项目，返回空列表 |
| 可读 .governance 中没有 remote-path-guards.json | guard 是可选配置，返回空列表 |
| 明确存在的 policy 内容无效、不可读、类型错误 | DENY，不返回空列表 |
| governance 无法读取/不是目录 | DENY |
| 默认 governance 或 policy 是 symlink（含悬空链接） | DENY；需要用户显式配置 |
| 显式 policy 相对路径、缺失、损坏、不可读 | DENY |
| 无可靠启动 anchor 或 Git 定位异常 | DENY，报告 policy/configuration failure |

子目录 .governance 不覆盖 anchor policy，也不作为 fallback。若某子项目需要独立
policy，应以独立 Git/worktree 边界启动，或指定绝对 ACGM_POLICY_CONFIG。

## 必须知道的边界

- 非 Git 项目从子目录新启动一个 Session 时，该启动目录就是独立边界；不会猜测
  哪一级父目录是“真正项目”。应从项目根启动，或使用显式绝对配置。这与同一
  Session 内 cd 不同：cd 绝不更改 anchor。
- monorepo 默认共享 Git 根 policy；不自动识别其中无独立 Git 边界的逻辑子项目。
- 本修复不追踪历史上是否曾有 policy 文件。一个真正不存在的可选配置仍是未配置；
  删除文件后的持久性检测/防篡改属于后续工作，不在此次 cwd 修复中加状态框架。
- Git worktree 使用自己的顶层工作目录，不跳到共同 Git 元数据目录或主工作树。
- 旧/自建 Harness 缺少 CLAUDE_PROJECT_DIR 时必须提供显式绝对 policy；不再默默
  依据动态 cwd 工作。支持的真实 Claude Harness 已验证提供该变量。
- 每次读取仍存在通常的文件系统并发修改边界；本次不引入缓存或签名框架。
