# VEM-skill01 · 细胞 × 基因表达矩阵预测

**[查看第一版中文方向表](catalog/DIRECTIONS.md)** · [可追加的实验明细](catalog/history.jsonl) · [给 agent 的 skill](skills/vem-t1-matrix-history/SKILL.md)

这张表记录 Virtual Embryo T1 具体试过哪些操作、用了哪个父方案、总分和四项各怎么变。包括负结果、未能拆分单项增益的方案与本地开发回放。方向可以新增；表里的实验例子不是下一轮的指定路线。E10.5 验证成绩不代表 E12.5 测试成绩。

## 在 Codex 或 Claude Code 中使用

需要 Python 3.9+。两种客户端使用同一份 SKILL.md 和维护脚本，不需要 MCP 服务或模型 API key 来整理记录。在希望使用 skill 的项目中执行：

```sh
git clone https://github.com/Chemit797/VEM-skill01.git
python VEM-skill01/install.py --client both --scope project --project . --with-catalog
```

打开这个项目的新会话：

- **Codex**：`$vem-t1-matrix-history 看历史方向表，把本批有回执的结果追加进去。`
- **Claude Code**：`/vem-t1-matrix-history 看历史方向表，把本批有回执的结果追加进去。`

只装一个客户端可用 `--client codex` 或 `--client claude`。项目安装写入 `.agents/skills/` 和 `.claude/skills/`；`--scope user` 安装至 Codex 用户 skills 目录和 Claude Code 用户 skills 目录（支持 `CODEX_HOME`、`CLAUDE_CONFIG_DIR`）。程序不会覆盖已有不同内容。已有项目历史不必再使用 `--with-catalog`。

## 给下一位接手者

1. 阅读[方向表](catalog/DIRECTIONS.md)；同一方向的完整历史、父件和分项在表内对应条目下。这里是从项目明细生成的可分享摘录，`source:` 是留档的证据键，不是在线回执链接。原始预测、账号回执和本机路径不在这个仓库。
2. 每批新增实验按[记录示例](skills/vem-t1-matrix-history/references/ledger.md)放进一个 JSONL；用 `history.py append` 原子追加账本并生成中文表。可在这个仓库运行 `python skills/vem-t1-matrix-history/scripts/history.py check --ledger catalog/history.jsonl` 检查公开版是否一致。
3. 已获授权做实验时，同时给历史方向的改进和清单外自主探索留出实际机会。不规定比例，也没有“失败一次就禁用”的方向。本工具本身不训练、评分或提交预测。
