# ACGM v0.9.4 安全与兼容性

正式版本说明；本工具不是任意 shell 环境的完整安全沙箱。

## 1. 根因与修订

| 根因（当前源代码核实） | v0.9.4 行为 |
|---|---|
| Remote routing 使用 payload 判定，prior evidence 使用外层 Bash 正则 | 二者复用同一 payload policy；不把 ssh 加入 READ_ONLY_BASH |
| `if transcript` / `if calls` 导致缺失证据跳过检查 | 被 gate 的操作无条件检查 evidence；缺失、空、不可读、损坏全部拒绝 |
| 只要求出现只读 tool_use，未确认工具运行成功 | 必须有同 ID 的后续 user/tool_result，且 is_error 不是 true；pending/failed 不算 |
| 四字段绑定的是文本，prior evidence 与 target 无关 | 所有可识别路径均需同 host 的实际读取；精确路径或直接父目录，禁止 basename / 子串匹配 |
| 没有声明 LOCAL/REMOTE 路径归属 | 每次 Bash 先检查 remote_path_guards；本机保护路径写入直接拒绝 |
| SSH 解析失败只是进入普通 gate，可被字段解除 | 独立 hard-deny；字段、evidence 均不能解除 |
| 截取 12 calls 后才删除当前命令，边界实际只留 11 | adapter 最多读取 13；core 先排除当前调用，再取 12 |
| 缺 jq/Python 或异常可能静默通过 | PreToolUse 输入、运行时、policy/config 异常输出 deny |

报告中的 PASS 表示不再被 ACGM 拒绝，输出 `{}` 交还宿主权限流；从不输出 allow。

## 2. 架构与配置

```text
Claude PreToolUse shell entry
  ├─ legacy destructive routing (existing compatibility filter)
  └─ acgm_gate.py: input/config I/O, Claude transcript normalization, hook output
       └─ acgm_policy.py: shared parsing / read-only / target binding /
                          execution context / evidence policy
Future Codex adapter ───────┘  (not implemented or activated by this revision)
```

共享模块不读 Claude transcript、不发平台 hook decision、不执行 shell/SSH。
`ToolCall(name, command, path, call_id, succeeded)` 是归一化接口。
现有 shell destructive filter 保留以降低迁移范围；它仍是历史平台接入技术债，
并非已经完成全面的跨平台 command routing 重构。新增安全规则只有一份。

无新增第三方依赖。JSON 示例：

```json
{
  "remote_path_guards": [
    {"host": "nas", "prefixes": ["/protected/remote/path/"]}
  ]
}
```

加载顺序：

1. 显式 `ACGM_POLICY_CONFIG` 必须为绝对路径；加载失败即拒绝。
2. 否则以稳定的 `CLAUDE_PROJECT_DIR` 定位 Git/worktree 根；非 Git 项目以启动目录为边界。
3. 从 anchor 加载 `.governance/remote-path-guards.json`，不随 shell cwd 改变。
4. 可选配置不存在时 guards 未配置；配置无效、不可读或 anchor 无法确定时拒绝。

详见 [policy anchor](POLICY-ANCHOR.md)。

prefix 使用 POSIX 路径归一化和路径组件边界；`/path-other` 不匹配 `/path`。
多个不冲突的 prefix/host 可以并存，不含环境专用规则。
`user@nas` 归一为 alias `nas`；`-o HostName=...`、`-F`、未知 SSH option 拒绝。
只支持明确解析的 SSH 选项；传输选项也采取窄支持，复杂命令需拆分/另行扩展测试。

LOCAL 拒绝：cp/mv/rm/mkdir/touch/chmod/chown/truncate/install/tee、sed -i/
--in-place、写重定向 > / >> / &> 等，目标涉及保护路径即拒绝。
cp 的源路径命中也拒绝，避免远端 source 被当成本机 source。
echo/printf/grep 的路径文本不被当成文件写入，单独检查其重定向目标。
识别保护路径的 opaque 本地调用不能获得 remote 权限；未注册任何 wrapper allowlist。
合法 `ssh nas 'cp ...'` 进入正常 evidence / fields gate，而非直接 allow。
scp/rsync 检查显式 host:path 与本地操作数；仅受支持 rsync dry-run 可静默通过，
但 transfers 没有可证明的只读 SSH payload，所以从不注册为 evidence。

## 3. Evidence 与窗口细节

- 同 host 精确 target 或**直接**父目录；不能用本地 `/remote/a` 的 Read 授权 nas
  上 `/remote/a`，也不能用 nas 的检查授权 wrong-host。
- 多个可识别路径全部需要覆盖，可由多个先前成功读取合并。
- echo/printf、grep 搜索字符串、stat format 字符串不是已读取的目标。
- 四字段继续必需，但文字不能替代工具证据。
- 成功由 transcript 的结构化 tool_result 状态证明；不证明输出本身正确，
  不解析任意程序伪装的输出，也不能确保包装程序如实上报内部失败。
- Read/NotebookRead 使用 file_path/notebook_path；WebFetch/WebSearch 无法满足
  文件路径绑定。Bash remote evidence 必须是可解析的真实 transport。
- 绝对路径和同一 invocation 内明确 `cd` 解析的路径受绑定；无法解析 target 的
  remote write / 文件写入不接受 unrelated evidence。
- plugin ID、git ref 等非文件系统的历史 gate 仍保留较弱“存在成功只读调用”规则。
  本版没有宣称完成这些标识符的数据流/语义绑定。
- 仅 assistant/tool_use 消耗窗口；普通 assistant text、user/tool_result、progress
  以及没有成为 agent tool call 的 hook 内部进程不计数。
- 有 tool_use_id 时按 ID 排除当前；没有时只比较最后一条 Bash 是否与当前命令相同。
  这种旧 harness 回退不能区分恰好相同的 retry，已知至多多保留一条 prior call。
- 真正写入 transcript 的 retry / 辅助 tool call 仍占用 12 条窗口；不扩至 50/100，
  不无限跳过 retry。证据超窗应重新读取。
- 当前 adapter 线性扫描 JSONL，保留最后 13 个 calls；尚未优化大 transcript 的 I/O。

## 4. 验证与升级

现有正式测试：`python3 -m unittest discover -s tests -v`，共 114 项。
CI 还使用 `CLAUDECODE=1` 运行相同测试。测试中的操作字符串为 synthetic fixtures，
不代表真实远程环境的验收。编译、shell syntax 与 source hash 核对分别验证其对应层。

升级前保留已有安装与配置；从示例模板配置真实 host/prefix，不随发布提供用户配置。
使用宿主正常插件管理流程安装，再新开会话核对实际加载版本及行为。
源码发布、配置健康、运行时激活和用户验收是不同结论。
回退应恢复完整旧版本及注册配置并重新验证加载，不能只改 VERSION；旧安全边界也会恢复。

兼容性变化：缺 evidence 的历史“通过”变为拒绝；只读判定排除 Python/awk 任意代码、
find side effects、sed 写/执行、git fetch/remote mutation/branch mutation、输出文件选项；
SSH/transfer 未知或身份覆盖选项拒绝；scp -n 不再误判 dry-run；plain local rm 也经过 gate；
格式损坏/依赖故障拒绝；绝对文件 targets 全绑定；legacy non-filesystem 规则仍保留。
非 destructive / 明确 read-only 在配置有效且运行时正常时不新增 evidence 要求。

## 5. Claude Code / Codex 影响及剩余缺口

Claude：PreToolUse 输出结构、四字段、成功后交回权限流的语义不变；新增依赖是成功
tool_result 的证据要求。SessionEnd 以真实成功结果、精确 target/host 和先后顺序核验，不能依靠 assistant 自述。配置有效性/依赖异常会拒绝 Bash，属于
预期 fail-closed，可用性取舍须在部署前接受。

Codex：本次没有修改/安装 acgm-codex。未来 adapter 归一化调用、结果、host/cwd 上下文后
复用 core；需接入所有可能执行命令的 Codex 工具并验证其拒绝语义，不能宣称当前已有覆盖。

剩余安全缺口（不能把此 Hook 当 OS 隔离边界）：

- LOCAL 任意程序/脚本内部、make/npm task、没有可见受保护路径的 opaque wrapper，
  仍不被完整静态分析；没有给 opaque wrapper 授予自动 remote write 权限。
- 跨调用变量、计算/拼接路径、symlink、bind mount、继承 cwd、远端脚本的内部目标、
  shell function/alias 与可执行文件替换都超出本版模型。尤其被拆成多个变量的 remote
  prefix 可避开路径匹配；应使用账户权限/文件系统隔离作最后防线。
- host alias 不是机器身份认证，SSH config / DNS 可变化；hostname/machine-id/
  fingerprint pinning 仍应在外部做，最终写动作必须回到可解析的真实 transport。
- shell parser 是保守子集，不是完整 Bash AST；复杂合法命令可能被拒绝。已有 legacy
  substring filter 仍可能把命令文本误识别为破坏性操作。
- 动态 flags/环境对所有“只读”程序的副作用没有穷尽审计；core 强化了已知执行/写入选项，
  不是对操作系统工具的形式化无副作用证明。
- evidence 仅证明 transcript 记录了成功的关联读取；不证明内容真实、检查充分、target
  未在检查后变化、远端内部命令无隐藏错误。存在 TOCTOU；不作事务隔离。
- 默认项目配置不存在时 guards 不启用；必须由操作者部署完整配置。配置/源码/transcript
  如果仍能被同一 Agent 改写，Hook 本身不具防篡改能力。
- 非文件 targets 的语义绑定、实际 VERIFY-AFTER 内容核验、ROLLBACK 可执行性仍未完成。
