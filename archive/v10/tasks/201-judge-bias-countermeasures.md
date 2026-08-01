# Task 201: judge 偏差对策

> **阶段**: V10.3 优秀度信号包
> **类型**: 离线 report-only judge 偏差分析 / 对策协议
> **状态**: ✅ 已完成；DONE: `tasks/201-judge-bias-countermeasures-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只分析 Task 196 prelabel 与 agent-deep-read 真值的偏差，并把 Task 197/198/199/200 离线报告映射为 judge 对策协议。

本任务不调用线上多 judge，不把 judge 分数当真值，不新增核心 Agent / Workflow 节点，不修改 Writer / CreativeDirector prompt，不进入 gate，不修改 CED / five-gate / segment audit / T9 口径。

---

## 输入

| 输入 | 路径 |
|------|------|
| Task 196 样本清单 | `archive/v10/artifacts/196-excellence-sample-set.json` |
| Task 196 标注记录 | `archive/v10/artifacts/196-excellence-annotations.json` |
| Task 196 校准报告 | `tasks/196-excellence-calibration-report.md` |
| Task 197/198 信号报告 | `archive/v10/artifacts/197-198-excellence-signals-report.json` |
| Task 199 style card 报告 | `archive/v10/artifacts/199-style-card-report.json` |
| Task 200 voice anchor 报告 | `archive/v10/artifacts/200-character-voice-anchor-report.json` |

---

## Bias taxonomy

1. `leniency_bias`：单向宽松。
2. `low_score_blindness`：低分区失明。
3. `evidence_drift`：引用非逐字 / 拼接引用。
4. `engineering_artifact_blindness`：工程事故型 AI 痕迹漏判。
5. `style_vs_quality_confusion`：风格画像与质量判断混淆。
6. `voice_homogeneity_blindness`：角色声纹同质化漏判。

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/judge_bias_analysis.py` |
| 薄 CLI | `scripts/run_201_judge_bias_analysis.py` |
| JSON 报告 | `archive/v10/artifacts/201-judge-bias-report.json` |
| Markdown 报告 | `archive/v10/reports/201-judge-bias-report.md` |
| 测试 | `tests/evals/test_201_judge_bias_analysis.py` |

---

## 验收标准

- [x] 任务书与 DONE 文档落盘。
- [x] judge bias JSON + Markdown 报告落盘。
- [x] 每类 bias 有定义、证据、统计或负结论。
- [x] 明确 report-only，不污染 CED 或任何 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| 某类偏差无法用现有信号解释 | 写负结论，不编造改善效果 |
| 必须调用线上 judge 才能完成 | 停止并拆离线实验任务 |
| 必须新增 prompt card 并接运行时 | 停止并拆后续任务；201 不执行 |
