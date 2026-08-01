# Task 203: 优秀度报告整合

> **阶段**: V10.3 优秀度信号包
> **类型**: 独立离线 report-only 整合报告
> **状态**: ✅ 已完成；DONE: `tasks/203-excellence-report-integration-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只整合 Task 197-202 的离线优秀度报告，输出统一 JSON 与 Markdown 视图。它不接入 `songyan report`，不调用 LLM，不重新生成正文，不写 SQLite，不修改 Writer / CreativeDirector prompt，不进入自动 gate，不修改 CED / five-gate / segment audit / T9。

禁止生成综合优秀度硬分、章节排名或 hard verdict；只输出分层观察、证据计数、局限和后续建议。Task 196 的 anchor + spotcheck agent-deep-read 24 章是唯一校准真值，prelabel 仅作低置信对照。

---

## 输入

| 输入 | 路径 | 用途 |
|------|------|------|
| Task 196 sample | `tasks/196-excellence-sample-set.json` | 样本来源与章节顺序 |
| Task 196 annotations | `tasks/196-excellence-annotations.json` | 校准真值与 prelabel 对照 |
| Task 197/198 report | `tasks/197-198-excellence-signals-report.json` | structure / ai_tone 信号 |
| Task 199 report | `tasks/199-style-card-report.json` | style card |
| Task 200 report | `tasks/200-character-voice-anchor-report.json` | voice anchors |
| Task 201 report | `tasks/201-judge-bias-report.json` | judge bias |
| Task 202 report | `tasks/202-readability-feasibility-report.json` | readability / PPL feasibility |

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/excellence_report_integration.py` |
| 薄 CLI | `scripts/run_203_excellence_report_integration.py` |
| JSON 报告 | `tasks/203-excellence-integrated-report.json` |
| Markdown 报告 | `docs/reports/203-excellence-integrated-report.md` |
| 测试 | `tests/evals/test_203_excellence_report_integration.py` |

---

## 统一 schema

- `source_artifacts`: 197-202 输入清单、路径、`generated_at`、`report_only`。
- `chapter_index`: 按 `genre/chapter` 汇总各层信号和证据。
- `signal_index`: 按 `layer/signal_id` 汇总覆盖章节、证据、校准指标和局限。
- `signal_layers`: structure / ai_tone / style / voice / judge_bias / readability。
- `calibration_truth`: Task 196 anchor + spotcheck agent-deep-read 24 章。
- `confidence_notes`: precision、recall、unknown attribution、defer、false-positive pressure 等局限。
- `task203_summary`: 可引用结论与后续路由。

---

## 验收标准

- [x] Task 203 任务书与 DONE 文档落盘。
- [x] 统一优秀度 JSON + Markdown 报告落盘。
- [x] Task 197-202 信号均被整合，并保留各自局限、校准指标和 report-only 口径。
- [x] 同时具备 chapter view 与 signal view。
- [x] 不输出综合优秀度硬分、章节排名或 hard verdict。
- [x] 不污染 CED、five-gate、segment audit、T9 或任何 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| 任一必需 JSON 缺失或 schema 不兼容 | 失败并记录，不静默跳过 |
| 任一 report artifact `report_only` 非 true | 失败 |
| 需要接入 `songyan report` 或 runtime | 停止并登记 Task 207 / 后续任务 |
