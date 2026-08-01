# Task 201 DONE: judge 偏差对策

> **任务书**: `tasks/201-judge-bias-countermeasures.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 201 已完成离线 judge 偏差分析与对策协议。报告只消费 Task 196-200 已落盘产物，不调用新 LLM judge，不新增 prompt card，不进入 Writer / CreativeDirector / gate / CED / five-gate / segment audit / T9。

六类 bias 均有统计或证据支撑；对策以协议形式输出，不声明 judge v2 已改善。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/judge_bias_analysis.py` |
| 薄 CLI | `scripts/run_201_judge_bias_analysis.py` |
| JSON 报告 | `archive/v10/artifacts/201-judge-bias-report.json` |
| Markdown 报告 | `archive/v10/reports/201-judge-bias-report.md` |
| 测试 | `tests/evals/test_201_judge_bias_analysis.py` |

---

## 关键统计

| 指标 | 值 |
|------|---:|
| agent-deep-read truth records | 24 |
| prelabel records | 48 |
| paired spotcheck records | 12 |
| major deltas ≥2 | 24 |
| supported biases | 6 |
| prelabel evidence fidelity | 0.791 |

注：Task 201 的 evidence fidelity 为当前源码的 whitespace-normalized 逐字复算结果；Task 196 校准报告使用更严格口径记录为 70.1%。二者方向一致：prelabel evidence 保真显著低于 agent-deep-read。

---

## Bias taxonomy 结果

| bias | status | 关键证据 |
|------|--------|----------|
| `leniency_bias` | supported | 48 个 paired 维度中 positive_delta=46、negative_delta=0、major_delta≥2=24 |
| `low_score_blindness` | supported | prelabel 低分区 ≤2 为 0；truth 低分区 ≤2 为 37 |
| `evidence_drift` | supported | prelabel quote 134 条，verbatim 106 条，fidelity=0.791 |
| `engineering_artifact_blindness` | supported | 7 个 truth low-ai-tone 样本有 Task 198 工程事故类信号 |
| `style_vs_quality_confusion` | supported | 6 个强真值样本也有 style risk，说明 style risk 不等于质量缺陷 |
| `voice_homogeneity_blindness` | supported | ai_tone major_delta≥2 为 9；Task 200 unknown attribution ratio=0.599 |

---

## 对策协议

| protocol | status | 说明 |
|----------|--------|------|
| `anchor_example_injection` | recommended | 用 Task 196 强/弱 anchor 示例校准 judge；201 不新增或运行 prompt card |
| `forced_checklist` | recommended | scoring 前强制检查 197/198/200 的结构、工程事故、声纹证据 |
| `verbatim_evidence_check` | guardrail-only | evidence_quote 必须能在 accepted 正文中检索 |
| `prelabel_downweighting` | recommended | prelabel 只作广覆盖对照，不作真值 |
| `blind_review_protocol` | future-experiment | 后续多 judge / 盲评 / 对照实验协议；201 不执行 |
| `goodhart_guardrail` | guardrail-only | 不直接用 judge 分数优化生成或进入 gate |

---

## 边界自查

- 未调用 LLM。
- 未新增 prompt card。
- 未改 Writer / CreativeDirector prompt。
- 未改 Agent / Workflow 节点。
- 未改 CED / five-gate / segment audit / T9。
- 未写 SQLite。
- 未把 prelabel 当真值。

---

## 验证

```powershell
python scripts/run_201_judge_bias_analysis.py
python -m pytest tests/evals/test_201_judge_bias_analysis.py tests/evals/test_200_voice_anchor_extraction.py tests/evals/test_199_style_card_extraction.py tests/evals/test_197_198_excellence_signals.py tests/evals/test_196_excellence_sampling.py -q
ruff check src/songyan/evals/judge_bias_analysis.py scripts/run_201_judge_bias_analysis.py tests/evals/test_201_judge_bias_analysis.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_197_198_excellence_signals.py scripts/run_199_style_card_extraction.py scripts/run_200_voice_anchor_extraction.py scripts/run_201_judge_bias_analysis.py scripts/run_v10_ch200_climb.py
```

结果：

- Task 201 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：30 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed。
- ruff：All checks passed。

---

## 后续

Task 202 可进入 perplexity / 可读性可行性 spike。Task 203 可消费 `archive/v10/artifacts/201-judge-bias-report.json`，但展示时必须保留 report-only 与“对策协议，不是已上线 judge 改善”的边界说明。
