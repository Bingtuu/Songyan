# Task 199 DONE: style extraction → style card

> **任务书**: `tasks/199-style-extraction-to-style-card.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 199 已完成离线 style extraction → style card 流程。系统从 Task 196 accepted 样本正文与 Task 197/198 离线信号中生成可复现的 style card JSON 与 Markdown 报告。

本任务只生成“观察到的风格画像”，不是 prompt 工艺卡，不默认注入 Writer / CreativeDirector，不进入任何 gate，不修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/style_card_extraction.py` |
| 薄 CLI | `scripts/run_199_style_card_extraction.py` |
| JSON 报告 | `tasks/199-style-card-report.json` |
| Markdown 报告 | `docs/reports/199-style-card-report.md` |
| 测试 | `tests/evals/test_199_style_card_extraction.py` |

---

## Style Card schema

报告内每张 style card 包含：

| 字段 | 说明 |
|------|------|
| `narrative_voice` | dominant person、POV depth、tone、证据片段 |
| `sentence_rhythm` | 平均句长、平均段长、短/长句比例、对白比例、节奏标签 |
| `imagery_lexicon` | 高频意象、体裁词汇、从 197 报告汇总的易滥用词 |
| `exposition_style` | 说明文标记密度、设定补丁段命中、风险标签 |
| `tension_pattern` | 张力均值/峰值/波动、主要场景功能、张力模式 |
| `dialogue_style` | 全局对白比例、对白行数、样例对白；不做角色声纹 |
| `anti_patterns` | Task 197/198 风险信号聚合 |

默认输出三张卡：

- `all`
- `genre:scifi`
- `genre:xuanhuan`

---

## 报告摘要

| scope | chapters | rhythm | dialogue | exposition | tension | anti-patterns |
|-------|---------:|--------|----------|------------|---------|--------------:|
| all | 60 | short-pulse | short-exchange | mixed-exposition | flatline-risk | 12 |
| genre:scifi | 30 | short-pulse | short-exchange | mixed-exposition | flatline-risk | 10 |
| genre:xuanhuan | 30 | short-pulse | short-exchange | mixed-exposition | steady-escalation | 9 |

---

## Sanity check

校准真值仍只使用 Task 196 anchor + spotcheck 的 24 章 `agent-deep-read` 标注；prelabel 不作为真值。

| scope | strong | strong traits | weak | weak explained | weak unexplained |
|-------|-------:|--------------:|-----:|---------------:|------------------|
| all | 6 | 6 | 15 | 15 | - |
| genre:scifi | 3 | 3 | 8 | 8 | - |
| genre:xuanhuan | 3 | 3 | 7 | 7 | - |

解读：

- 强章均能抽到非空 style traits，说明 schema 在正样本上不是空壳。
- 弱章均能由 Task 197/198 anti-patterns 解释，说明报告可回溯到证据。
- 这只是方向性 sanity check，不是阈值定标，不支持进入 hard gate。

---

## 边界自查

- 未改 Writer / CreativeDirector prompt。
- 未改任何 prompt card。
- 未改 gate / CED / five-gate / segment audit / T9。
- 未新增核心 Agent / Workflow 节点。
- 未写入 SQLite；仅读 Task 196 样本 source DB 与 JSON 报告产物。
- 未做角色声纹锚点；该范围归 Task 200。

---

## 验证

```powershell
python scripts/run_199_style_card_extraction.py
python -m pytest tests/evals/test_199_style_card_extraction.py tests/evals/test_197_198_excellence_signals.py tests/evals/test_196_excellence_sampling.py -q
ruff check src/songyan/evals/style_card_extraction.py scripts/run_199_style_card_extraction.py tests/evals/test_199_style_card_extraction.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_197_198_excellence_signals.py scripts/run_199_style_card_extraction.py scripts/run_v10_ch200_climb.py
```

结果：

- Task 199 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：23 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed。
- ruff：All checks passed。

---

## 后续

Task 200 可在本任务 style card 的全局对白观察基础上，单独实现角色声纹锚点。Task 203 可消费 `tasks/199-style-card-report.json`，但展示时必须保留 report-only 与“观察画像，不是生成约束”的边界说明。
