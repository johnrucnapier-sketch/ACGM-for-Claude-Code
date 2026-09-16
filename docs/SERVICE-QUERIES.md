# v0.9.4: safe service queries

journalctl 支持：无参查询；-u/--unit、-S/--since、-U/--until、-n/--lines、
-p/--priority、-o/--output、--boot 的单独值或 =value；--no-pager、-a/--all、
-q/--quiet、-b（当前 boot）、-f/--follow、-r/--reverse、--utc、--no-hostname、
--list-boots、--disk-usage。

systemctl show 支持 unit 名称，-p/--property 的单独值或 =value，以及
--value、--no-pager、-a/--all、-q/--quiet。只扩展 show-first 形式；其他既有
systemctl 查询行为不改。show 是读取属性，不执行服务状态变更。

参数必须完整、明确；未知选项、缺值、空值、变量/glob 展开不认证。
不支持的查询简写（如 -n50、-b -1、选项在 show 前）仍保守进入 Gate，
不以扩大 parser 来覆盖所有命令行排列。

--rotate、--vacuum-*、--flush、--sync、--relinquish-var、--setup-keys、
--update-catalog、--cursor-file、--synchronize-on-exit 等均不在查询白名单。
额外 mutating/unknown 参数不能借前面的合法查询选项获得 read-only。

参考 systemd 官方手册：
- https://www.freedesktop.org/software/systemd/man/255/journalctl.html
- https://github.com/systemd/systemd/blob/main/man/systemctl.xml
