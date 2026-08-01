# Task 197: 跨章同质化 / 多样性 / 叙事张力指数

> **阶段**: V10.3 优秀度信号包
> **类型**: 离线 report-only 量具 / 结构型信号
> **状态**: ✅ 已完成；DONE: `tasks/197-cross-chapter-homogeneity-tension-index-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只实现离线 report/observe 信号，不进入 Writer / CreativeDirector prompt，不进入自动 accept/reject gate，不修改 CED / five-gate / segment audit / T9 口径。

Task 196 的 prelabel 仅作对照，不当真值；Task 197 的校准真值只使用 anchor + spotcheck 的 24 章 agent-deep-read 标注。

---

## 输入

| 输入 | 路径 |
|------|------|
| 样本清单 | `tasks/196-excellence-sample-set.json` |
| 标注记录 | `tasks/196-excellence-annotations.json` |
| 校准报告 | `tasks/196-excellence-calibration-report.md` |

---

## 信号定义

Task 197 最小信号包：

1. `scene_function_homogeneity`：按弧段统计场景功能占比，识别单一功能占比过高。
2. `beat_rhythm_repetition`：将章节切成四段，识别桥段功能签名重复。
3. `tension_flatline`：用段落级危险 / 冲突 / 揭示词与标点估算张力，识别低均值、低峰值、低波动。
4. `motif_reuse_density`：识别高频意象 / 冲突词复用密度偏高的章节。

这些信号只用于定位可疑章节，不给自动判定结论。

---

## 输出

| 输出 | 路径 |
|------|------|
| 共享模块 | `src/songyan/evals/excellence_signals.py` |
| 离线脚本 | `scripts/run_197_198_excellence_signals.py` |
| 结构化报告 | `tasks/197-198-excellence-signals-report.json` |
| Markdown 报告 | `docs/reports/197-198-excellence-signals-report.md` |
| 聚焦测试 | `tests/evals/test_197_198_excellence_signals.py` |

---

## 验收标准

- [x] 从 Task 196 样本读取 accepted 正文。
- [x] 至少输出 JSON + Markdown 两种报告。
- [x] 每个命中有章节、信号 ID 和证据定位。
- [x] 校准使用 anchor + spotcheck，不使用 prelabel 作为真值。
- [x] 报告显式标注 report-only，不污染 CED / hard gate。
- [x] 聚焦测试和 ruff 通过。

---

## 校准结论

Task 197 在 24 章 agent-deep-read 真值上的结果：

| evaluated | truth+ | detected+ | TP | FP | FN | precision | recall |
|-----------|--------|-----------|----|----|----|-----------|--------|
| 24 | 10 | 20 | 8 | 12 | 2 | 0.40 | 0.80 |

结论：Task 197 第一批结构型信号是高召回、低精度的观察量具，只能 report-only 使用。`beat_rhythm_repetition` 与 `scene_function_homogeneity` 容易把稳定类型结构识别为同质化，后续 Task 203 展示时应标为候选风险，而非缺陷结论。

---

## 后续路由

- Task 203 可整合本任务 JSON，但必须保留 report-only 标签。
- 若要提升精度，应后续单独立项，加入更多体裁样本与人工标注，不得直接转 hard gate。
