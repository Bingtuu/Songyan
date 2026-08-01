# Task 202: perplexity / 可读性可行性 spike

> **阶段**: V10.3 优秀度信号包
> **类型**: 离线 report-only spike
> **状态**: ✅ 已完成；DONE: `tasks/202-perplexity-readability-feasibility-spike-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只评估中文长篇网文中的可读性 proxy 与真实 perplexity 的工程可行性。输出用于 Task 203 报告整合的采用 / 放弃 / 后置结论。

本任务不调用 LLM，不下载外部模型，不接入 Writer / CreativeDirector prompt，不进入自动 gate，不修改 CED / five-gate / segment audit / T9 口径。若真实 perplexity 需要外部模型或不可稳定复现，则只给可行性负结论或后置结论。

---

## 输入

| 输入 | 路径 |
|------|------|
| Task 196 样本清单 | `archive/v10/artifacts/196-excellence-sample-set.json` |
| Task 196 标注记录 | `archive/v10/artifacts/196-excellence-annotations.json` |
| Task 197/198 信号报告 | `archive/v10/artifacts/197-198-excellence-signals-report.json` |
| Task 199 style card 报告 | `archive/v10/artifacts/199-style-card-report.json` |
| Task 200 voice anchor 报告 | `archive/v10/artifacts/200-character-voice-anchor-report.json` |
| Task 201 judge bias 报告 | `archive/v10/artifacts/201-judge-bias-report.json` |

---

## 候选信号

1. `sentence_readability`：句长均值、长句比例、短句密度。
2. `paragraph_readability`：段长均值、超长段比例、短段连续。
3. `dialogue_ratio`：对白占比与对白稀疏 / 过密风险。
4. `punctuation_rhythm`：问号、叹号、省略号、破折号密度。
5. `lexical_repetition_proxy`：词汇重复与低信息词密度。
6. `perplexity_feasibility`：真实 PPL 是否可复现、成本、依赖、中文适配风险。

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/readability_feasibility.py` |
| 薄 CLI | `scripts/run_202_readability_feasibility.py` |
| JSON 报告 | `archive/v10/artifacts/202-readability-feasibility-report.json` |
| Markdown 报告 | `archive/v10/reports/202-readability-feasibility-report.md` |
| 测试 | `tests/evals/test_202_readability_feasibility.py` |

---

## 验收标准

- [x] 任务书与 DONE 文档落盘。
- [x] readability / perplexity feasibility JSON + Markdown 报告落盘。
- [x] 每个候选信号都有定义、样本结果、局限和采用 / 放弃 / 后置结论。
- [x] 明确 report-only，不污染 CED 或任何 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| 真实 perplexity 需要外部模型或下载 | 写 defer / reject 结论，不硬做 |
| proxy 无法解释低分样本 | 写负结论，不编造有效性 |
| 需要接入 prompt / gate / runtime | 停止并拆后续任务 |
