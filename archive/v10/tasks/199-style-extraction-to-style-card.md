# Task 199: style extraction → style card

> **阶段**: V10.3 优秀度信号包
> **类型**: 离线 report-only 风格画像 / style card 生成
> **状态**: ✅ 已完成；DONE: `tasks/199-style-extraction-to-style-card-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只从 accepted 正文与 Task 196/197/198 离线产物中抽取“观察到的风格画像”，产出 JSON 与 Markdown style card 报告。

本任务不注入 Writer / CreativeDirector prompt，不进入自动 accept/reject gate，不修改 CED / five-gate / segment audit / T9 口径，不启动角色声纹、judge 偏差或结构 spike。

---

## 输入

| 输入 | 路径 |
|------|------|
| Task 196 样本清单 | `archive/v10/artifacts/196-excellence-sample-set.json` |
| Task 196 标注记录 | `archive/v10/artifacts/196-excellence-annotations.json` |
| Task 197/198 信号报告 | `archive/v10/artifacts/197-198-excellence-signals-report.json` |

prelabel 仅作对照，不作为真值。sanity check 只使用 anchor + spotcheck 的 24 章 agent-deep-read 标注。

---

## Style Card 最小 schema

1. `narrative_voice`：叙述人称、叙述距离、语气、证据。
2. `sentence_rhythm`：句长、段落节奏、对话比例、节奏标签。
3. `imagery_lexicon`：高频意象、体裁词汇、易滥用意象。
4. `exposition_style`：设定释放方式、说明文密度、补丁段风险。
5. `tension_pattern`：张力推进方式、平均/峰值/波动。
6. `dialogue_style`：全局对白倾向，不做角色声纹。
7. `anti_patterns`：从 Task 197/198 报告汇总的风格风险。

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/style_card_extraction.py` |
| 离线脚本 | `scripts/run_199_style_card_extraction.py` |
| JSON 报告 | `archive/v10/artifacts/199-style-card-report.json` |
| Markdown 报告 | `archive/v10/reports/199-style-card-report.md` |
| 测试 | `tests/evals/test_199_style_card_extraction.py` |

---

## 验收标准

- [x] 任务书与 DONE 文档落盘。
- [x] style card JSON + Markdown 报告落盘。
- [x] style card schema 可复现、可测试。
- [x] 报告明确 style card 是观察画像，不是生成约束。
- [x] 不触碰 prompt 注入、Writer / CreativeDirector、hard gate、CED、five-gate、segment audit、T9。
- [x] 聚焦测试、必要全量测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| 必须注入 prompt 才能完成 | 停止并拆后续任务，不在 199 内执行 |
| weak 样本无法由 anti_patterns 解释 | 记录负结论，不编造有效性 |
| style card schema 与现有 `StyleBaseline` / `DialogueStyleCard` 混淆 | 保留独立离线 schema，不写入运行时模型 |
