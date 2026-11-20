# 写一次，生成方向表

需要 Python 3.9+，不依赖机器学习环境。命令中的 `<skill>` 是本 SKILL.md 所在目录；若需定位，在 Codex 的已加载 skill 路径或 Claude Code 技能基础路径中找它。项目私有版始终传 VEM 项目根，公开版可不传 `--project`。

```text
python <skill>/scripts/history.py check --ledger research/t1_matrix_history/history.jsonl --project .
python <skill>/scripts/history.py append --ledger research/t1_matrix_history/history.jsonl --project . --batch new-batch.jsonl
python <skill>/scripts/history.py render --ledger catalog/history.jsonl
```

JSONL 每行一个对象，UTF-8。ID 在当前清单内永久唯一。`direction` 登记方向和开放例子；`run` 是一个观察（具体预测、一次回执或指定口径的本地汇总）；`comparison` 将两条观察或一条无父件的观察关联到一个方向。父子分数不复制到 comparison，由工具相减。`snapshot` 记录有日期的覆盖范围。重用已有观察直接引用其 ID。例：同名重复官方上传用新 run ID，注记重复事件，不另算一项有增益的对照。

下例是**格式示范，未执行且没有分数**。示例没有验证过新方向；真正追加时把来源换成你项目里的记录。若需录入有分结果，复制同协议的 run 结构，写 `status: scored`、实际总分与实际四项；不要把估分或未知项填为零。

```jsonl
{"kind":"direction","id":"D13","title":"按测量不确定性决定每个基因的更新幅度","example":"比较按来源重复性加权及其对照；不是必做路线。"}
{"kind":"run","id":"run-example-01","label":"预登记的不确定性模型","file":null,"channel":"development","protocol":"开发计划 / 示例","status":"not_run","total":null,"metrics":null,"sources":["source:example-plan"]}
{"kind":"comparison","id":"cmp-example-01","direction":"D13","parent":null,"child":"run-example-01","basis":"unpaired","change":"给不同基因分配不同的可信权重","data":"示例；尚未读取输入","sources":["source:example-plan"]}
```

| 字段 | 使用方式 |
|---|---|
| `channel / protocol` | `official / local / artifact / development` 四选一；协议中写清板块、时期、使用的样本与评价口径。同底稿只在同一来源、协议和分项尺度内相减。技术种子注明汇总方式。 |
| `file / label` | 保存文件名；未定位文件时 `file:null`，记录能定位的实验臂或原标签。上传 ID、时间和候选哈希各记各的，不反推上传字节。 |
| `status` | `scored / score_missing / candidate / failed / not_run / identical / unknown`。`identical` 必须有 `same_as` 引用另一个 run 和矩阵等值证据，不凭同分判定。 |
| `total / metrics / units` | 总分和四项 DE、方向、MMD、基因对差异；字段分别是 `de_score / de_direction / mmd_u / variogram`。缺则 `null`。`skill100` 表示 0–100 技能分，`raw` 表示原始指标，不混用；新口径用不同 protocol。 |
| `basis` | `paired` 同底稿，`combination` 多项合改，`family` 同族系列，`included` 已包含但无单项对照，`unpaired` 未知或无父件。前 3 种必须写 parent。 |
| `change / data / note / sources` | 简述操作、数据固定名称与时期、重要限制；来源可为项目相对路径加 `#定位信息`、HTTPS 链接，或 `source:记录键`（公开摘录回指项目私有档案）。 |
| `short / featured` | 可选的简短显示名；新比较默认进入首页，`featured:false` 仍在相应方向的全部明细里。新方向 ID 不受初始数量限制。 |

追加先校验整批，拒绝重复 ID、跨协议相减、无分状态伪填分数及悬空引用。用锁避免两个写者互相覆盖；若机器在已落账但未写完视图时中断，用 `render` 恢复，再 `check`。数值或身份需要更正时，新增有证据的更正观察与对照，用 note 注明所订正 ID；原回执保留。不要手改生成的 Markdown。
