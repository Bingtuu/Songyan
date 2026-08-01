# Task 202 DONE: perplexity / 可读性可行性 spike

> **任务书**: `tasks/202-perplexity-readability-feasibility-spike.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 202 已完成离线 readability proxy 与 true perplexity 可行性 spike。

真实 perplexity 在 V10 内判定为 `defer`：仓库没有版本化中文 LM 权重，下载模型会破坏离线可复现性，tokenizer 选择会显著影响中文网文专名与设定词 PPL，且成本不可稳定约束。因此本轮只落地无需外部依赖的可读性 proxy，作为 Task 203 report-only 输入。

本任务不调用 LLM，不下载模型，不注入 Writer / CreativeDirector prompt，不进入 gate，不修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/readability_feasibility.py` |
| 薄 CLI | `scripts/run_202_readability_feasibility.py` |
| JSON 报告 | `tasks/202-readability-feasibility-report.json` |
| Markdown 报告 | `docs/reports/202-readability-feasibility-report.md` |
| 测试 | `tests/evals/test_202_readability_feasibility.py` |

---

## 报告摘要

| 指标 | 值 |
|------|---:|
| sample chapters | 60 |
| chapters with any proxy hit | 55 |
| weak proxy coverage | 13/15 |
| strong proxy false-positive pressure | 6/6 |

强样本 6/6 也命中至少一个 proxy，说明可读性 proxy 对“读感风险”有解释价值，但不能作为优秀度硬判据。

---

## 候选信号结论

| signal | decision | hit chapters | weak coverage | 结论 |
|--------|----------|-------------:|---------------|------|
| `sentence_readability` | report-only | 1 | 1/15 | 命中少，只能作为章节读感辅助字段 |
| `paragraph_readability` | report-only | 38 | 10/15 | 能解释部分弱样本，但受体裁与排版影响大 |
| `dialogue_ratio` | report-only | 12 | 3/15 | 可作为对白上下文，不判断质量 |
| `punctuation_rhythm` | report-only | 45 | 11/15 | 节奏解释力较强但误报高，低权重展示 |
| `lexical_repetition_proxy` | report-only | 18 | 7/15 | 与 197/198 重复类信号重叠，只作补充证据 |
| `perplexity_feasibility` | defer | - | - | 后置到具备固定本地模型、tokenizer policy 和成本预算的离线实验 |

---

## Perplexity 可行性判断

| 项 | 结论 |
|----|------|
| reproducible_without_external_model | false |
| requires_model_weights | true |
| requires_tokenizer_policy | true |
| decision | defer |

后置条件：

- 固定本地中文 LM 权重。
- 固定 tokenizer policy。
- 固定 batch / cost budget。
- 明确中文网文专名、设定词、体裁词的解释口径。
- 只作为 report-only，不进入 gate。

---

## Sanity check

校准真值仍只使用 Task 196 anchor + spotcheck 的 24 章 `agent-deep-read` 标注；prelabel 不作为真值。

| truth records | weak samples | weak with proxy hit | strong samples | strong with proxy hit |
|--------------:|-------------:|--------------------:|---------------:|----------------------:|
| 24 | 15 | 13 | 6 | 6 |

解读：

- 13/15 弱样本有至少一个可读性 proxy 命中，说明 proxy 有报告解释价值。
- 6/6 强样本也命中，说明 proxy 不能做 hard gate 或自动排序。
- 未解释的弱样本应继续依赖 Task 197/198/200/201 与人工判断。

---

## 边界自查

- 未调用 LLM。
- 未下载模型。
- 未新增 prompt card。
- 未改 Writer / CreativeDirector prompt。
- 未改 Agent / Workflow 节点。
- 未改 CED / five-gate / segment audit / T9。
- 未写 SQLite。
- 所有输出均为 report-only。

---

## 验证

```powershell
python scripts/run_202_readability_feasibility.py
python -m pytest tests/evals/test_202_readability_feasibility.py tests/evals/test_201_judge_bias_analysis.py tests/evals/test_200_voice_anchor_extraction.py tests/evals/test_199_style_card_extraction.py tests/evals/test_197_198_excellence_signals.py tests/evals/test_196_excellence_sampling.py -q
ruff check src/songyan/evals/readability_feasibility.py scripts/run_202_readability_feasibility.py tests/evals/test_202_readability_feasibility.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_197_198_excellence_signals.py scripts/run_199_style_card_extraction.py scripts/run_200_voice_anchor_extraction.py scripts/run_201_judge_bias_analysis.py scripts/run_202_readability_feasibility.py scripts/run_v10_ch200_climb.py
```

结果：

- Task 202 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：34 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed。
- ruff：All checks passed。

---

## 后续

Task 203 可整合 Task 197-202 输出为统一优秀度报告视图。Task 202 的信号应展示为低权重 report-only 读感 proxy；真实 PPL 仅登记为后置实验，不进入 V10 硬门。
