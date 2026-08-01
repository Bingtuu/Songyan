# V10 归档索引

> **状态**: 归档规划入口。
> **物理归档状态**: Task 207 不移动 V10 活跃产物；本索引用于声明后续归档路径与追溯入口。
> **阶段结论**: V10 已完成跨体裁 Ch200、优秀度信号包与结构升级 spike。

---

## 总入口

| 文件 | 用途 |
|------|------|
| `tasks/V10-README.md` | V10 事实总索引，保留为活跃历史入口 |
| `tasks/207-v10-closure-and-archive-DONE.md` | V10 收口完成报告 |
| `docs/reports/207-v10-closure-report.md` | V10 closure report |
| `tasks/V11-Plan.md` | V11 开源可用化预登记 |

---

## V10 阶段产物

### V10.1 Ch200 口径与工具

| Task | 当前路径 |
|------|----------|
| 189 baseline/checkpoints | `tasks/189-ch200-baseline-and-checkpoints-DONE.md` |
| 189 frozen baseline | `tasks/189-scifi-ch200-baseline.json` |
| 190 Ch100 inventory | `tasks/190-ch100-terminal-source-inventory-DONE.md` |
| 191 Ch200 harness | `tasks/191-ch200-harness-preparation-DONE.md` |

### V10.2 跨体裁 Ch200

| Task | 当前路径 |
|------|----------|
| 192 xuanhuan Ch200 | `tasks/192-xuanhuan-ch200-climb-DONE.md` |
| 193 wuxia Ch200 | `tasks/193-wuxia-ch200-climb-DONE.md` |
| 194 urban Ch200 | `tasks/194-urban-ch200-climb-DONE.md` |
| 195 cross-genre acceptance | `tasks/195-cross-genre-ch200-acceptance-DONE.md` |

### V10.3 优秀度信号包

| Task | 当前路径 |
|------|----------|
| 196 calibration | `tasks/196-excellence-signal-calibration-DONE.md` |
| 197 homogeneity/tension | `tasks/197-cross-chapter-homogeneity-tension-index-DONE.md` |
| 198 Chinese AI tone | `tasks/198-chinese-ai-tone-rule-pack-DONE.md` |
| 199 style card | `tasks/199-style-extraction-to-style-card-DONE.md` |
| 200 voice anchors | `tasks/200-character-voice-anchors-DONE.md` |
| 201 judge bias | `tasks/201-judge-bias-countermeasures-DONE.md` |
| 202 readability/PPL feasibility | `tasks/202-perplexity-readability-feasibility-spike-DONE.md` |
| 203 excellence integration | `tasks/203-excellence-report-integration-DONE.md` |

### V10.4 结构升级 spike

| Task | 当前路径 |
|------|----------|
| 204 KG diff | `tasks/204-kg-graph-diff-spike-DONE.md` |
| 205 FactTrack validity interval | `tasks/205-facttrack-validity-interval-spike-DONE.md` |
| 206 Storyline Tree | `tasks/206-storyline-tree-spike-DONE.md` |

### V10.5 收口

| Task | 当前路径 |
|------|----------|
| 207 closure/archive | `tasks/207-v10-closure-and-archive-DONE.md` |
| closure report | `docs/reports/207-v10-closure-report.md` |

---

## 后续物理归档计划

若后续执行物理归档，建议采用以下路径：

| 类型 | 建议归档路径 |
|------|--------------|
| Task 189-207 任务书 / DONE | `archive/v10/tasks/` |
| V10 Markdown reports | `archive/v10/reports/` |
| V10 JSON artifacts | `archive/v10/artifacts/` |
| V10 scripts / spike modules | 继续留在代码树，除非后续明确废弃 |
| V10 README | 继续保留 `tasks/V10-README.md` 作为历史事实入口 |

物理归档前必须同步：

- `AGENTS.md`
- `docs/STATUS.md`
- `docs/INDEX.md`
- `tasks/V10-README.md`
- `README.md`

---

## 不归档为生产能力的内容

以下 V10 产物保持 report-only / spike 属性，不能因归档完成而被视为 runtime 能力：

- Task 197-203 优秀度信号包；
- Task 204 KG diff；
- Task 205 FactTrack validity interval；
- Task 206 Storyline Tree。

若后续生产化，必须另立 V11+ 任务并提供回归证据。
