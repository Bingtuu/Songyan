# Task 171a-1: 文学量具效度量化（≥2 体裁盲标 ground truth + voice/exposition P/R/F1）

> **框架**: `docs/reports/v7-literary-framework-review.md` §8 B 组（B2/B3）
> **类型**: 量具效度量化（171a 拆分续做）
> **优先级**: P1（171a 代码侧已达标；本任务补齐量化效度）
> **依赖**: Task 171a 代码侧完成（B1/B4/B5 已落地，注入路径已实证）
> **状态**: ✅ **完成**（B2/B3 达标；见 `171a-1-metric-validity-quantification-DONE.md`）
> **负责人**: songyan-agent

---

## 立项依据

Task 171a 已完成量具的代码侧重建（构念重定义 + 归因召回 + 体裁解耦通电），并在真实 scifi prose 上实证注入生效（`archive/v7/reports/task-171a-metric-validity-report.md`）。但框架 §8 的 **B2/B3**（≥2 体裁盲标 ground truth + voice/exposition P/R/F1 ≥ 0.8）需要两项 171a 无法即时满足的前置——第二体裁 prose 语料、遮机器分的盲标——故拆出本任务。

## 任务边界

只做**效度量化**，不再改量具逻辑（除非量化暴露新 bug）。产出可信的 voice/exposition 精度数字，作为 171c 提质"可归因"的前提。

## 目标

1. **第二体裁小样本生成**：从项目已配的非科幻体裁（wuxia / urban 等，见 `genres/`）中选 1 个对话属性不同的，生成小样本（对话密集 + 稀疏各若干章）。隔离 DB、observe 模式、真实 API。
2. **盲标 ground truth**：复用/扩展 `scripts/run_170m_ground_truth_export.py` 为体裁无关 + 遮机器分版本，覆盖 scifi（复用 170p/170i DB）+ 第二体裁，含对话密集/稀疏两类场景。
3. **P/R/F1 reeval**：复用/扩展 `scripts/run_170m_reeval.py`，对 voice（`human_voice_homogeneity`）与 exposition（`exposition_carrier`）分别计算 precision/recall/F1。
4. **出口判定**：
   - voice/exposition 任一维度 P/R/F1 ≥ 0.8 → 该维度"可信"，可进入 171c 对应维度提质。
   - 未达标维度 → 按框架 §8.5：voice 若无法达标则**永久转人工抽读**，退出自动判据；exposition 单独判定。

## 验收标准
- ≥2 体裁盲标 GT 文件落地（`.tmp/ground_truth/task171a1_*`）。
- `archive/v7/reports/task-171a-1-metric-prf-report.md`：voice/exposition 各维度 P/R/F1 + 逐条误报/漏报样例 + 出口判定。
- `ruff`/pytest 通过（若含代码改动）。

## 交付物（预期）
- `scripts/run_171a1_ground_truth_export.py`、`scripts/run_171a1_reeval.py`
- `.tmp/ground_truth/task171a1_<genre>_ground_truth.jsonl`（≥2 体裁）
- `archive/v7/reports/task-171a-1-metric-prf-report.md`
- `archive/v7/tasks/171a-1-metric-validity-quantification-DONE.md`

## 明确不做
- 不改生成侧行为（那是 171c）；不阻塞 Ch200 主线；不放宽任何冻结口径。
