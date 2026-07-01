# Task 147: 文学质量趋势化

> **Phase**: V6 阶段 A（度量同步）
> **优先级**: P1
> **依赖**: Task 145（度量出口框架）
> **预计工作量**: 中（维度已入库，主要是范围回读 + 滑窗趋势）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 A、§1.4-T3/T8

---

## Goal

LiteraryAuditor 的文学维度**已入库**；本 Task 增加"按章节范围回读 + 滑动窗口（W=5）趋势查询"，能按 T3/T8 口径检出"连续 N=5 章某维度均值相对基线下滑 ≥20%"。**不改变 accept 流程**（仍只诊断）。

## Context（代码核实）

- `literary_observations` 表（`schema.sql:252-266`）**已有**列：`literary_quality_score` / `character_autonomy_score` / `conceptual_grounding_score` / `fissure_preservation_score`（均 REAL），外加 `observations`（JSON 数组）、`summary`、`version_id`（FK→chapter_versions）。**无 `chapter_number` 列**——章节号只能经 `version_id → chapter_versions.chapter_number` JOIN 得到。
- `models/literary.py`：`LiteraryAuditResult` 带四个分数字段；`LiteraryObservation.observation_type` 是 Literal，含 `conceptual_idling` 等——**`conceptual_idling` 是 observation 类型（存 observations JSON 内），不是列**。
- `LiteraryObservationRepository`（`db/review_repo.py:180-256`）只有 `create` / `get_latest_id_by_version` / `get_by_version`——**无按章/范围/趋势查询**。趋势需新增一个 JOIN chapter_versions 的范围查询。
- 历史 DB `.tmp/task138n_...db` 的 `literary_observations`（599 行，覆盖 150 章）是标定 T3 的真值源；分数分布（非零行）：literary_quality 6.2–8.2 均 7.52、character_autonomy 5.5–9.0 均 7.61、conceptual_grounding 5.0–8.5 均 6.38、fissure_preservation 6.0–9.5 均 8.24。（`.tmp/*_per_chapter_metrics.jsonl` **不含**文学分数，不能用作 T3 真值。）
- T3 红线：任一文学维度滑动窗口（W=5 章）均值，相对该 run 前 10 章基线下降 **≥20%** 即触红线。T8：趋势窗口 N=5 章。

### 设计决策

1. 每章可能有多版本 → 每章取**最新 version 的最新 observation**（`created_at DESC` 内每 chapter 归一），得到"逐章文学分数序列"。
2. 趋势口径：`baseline` = 前 10 章（该 run/范围起点起）各维度均值；`window` = W=5 章滑窗均值；某维度当 `window_mean <= baseline_mean * (1 - 0.20)` 触 T3。基线不足 10 章时报"基线不足"。
3. 复用维度名：**`conceptual_grounding_score`**（不是 `conceptual_idling`）；文档明确二者区别，避免误配列。
4. 只读诊断，绝不接入 accept/gate。

## In Scope（必须完成）

- [ ] `LiteraryObservationRepository` 新增范围回读：`async list_scores_by_chapter_range(project_id, start, end) -> list[dict]`——JOIN `literary_observations`→`chapter_versions`（ON version_id），`WHERE cv.project_id=? AND cv.chapter_number BETWEEN ? AND ?`，每章取最新一条（`ORDER BY cv.chapter_number, lo.created_at DESC`，Python 侧按 chapter 去重取首），返回 `{chapter, literary_quality_score, character_autonomy_score, conceptual_grounding_score, fissure_preservation_score}`。
- [ ] 趋势模块（`src/songyan/evals/db_metrics.py`，与 145/146 同文件/包）：
  - `collect_literary_scores(project_id, start, end) -> list[LiteraryScorePoint]`（逐章序列）。
  - `detect_literary_trend(points, *, baseline_n=10, window=5, drop=0.20) -> LiteraryTrendResult`：对每个维度算 baseline 均值 + 各 W=5 滑窗均值，标出触 T3 的维度与首个触线窗口。
- [ ] `songyan metrics` 增"文学趋势"段：四维度逐章分数 + 基线 + 各滑窗均值 + T3 触线标记。
- [ ] 单测：seed literary_observations + chapter_versions（多版本/多章）→ 断言范围回读每章取最新、四维度序列正确；构造下滑序列断言 T3 检出（含基线不足、恰好 20% 边界、无下滑不误报）。

## Out of Scope（明确不做）

- 不改 LiteraryAuditor 生成逻辑、不改 accept/gate 流程（只诊断/趋势）。
- 不做文学质量"闭环修复"（V7）。
- 不新增文学维度列（复用现有四列）；`conceptual_idling` 仍留在 observations JSON，本 Task 不单独趋势化 observation 类型计数（可选增强，非必须）。

## 接口契约

```python
class LiteraryScorePoint(BaseModel):
    chapter: int
    literary_quality_score: float
    character_autonomy_score: float
    conceptual_grounding_score: float
    fissure_preservation_score: float

class LiteraryTrendResult(BaseModel):
    baseline_available: bool
    baseline: dict[str, float]                 # 维度 -> 前 baseline_n 章均值
    breached_dimensions: list[str]             # 触 T3 的维度
    first_breach_window: dict[str, int | None] # 维度 -> 首个触线窗口起始章
    windows: dict[str, list[float]]            # 维度 -> 各滑窗均值

async def collect_literary_scores(project_id, start, end) -> list[LiteraryScorePoint]: ...
def detect_literary_trend(points, *, baseline_n=10, window=5, drop=0.20) -> LiteraryTrendResult: ...
```

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_147_literary_trend.py -v` 全通过（范围回读每章取最新 + 四维度序列 + T3/T8 检出 + 边界）。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 可按 T3/T8 口径检出"连续 N=5 章某维度均值下滑 ≥20%"；**不改变 accept 流程**（无 gate 接入，单测断言只读）。
- [ ] 维度名与列一致（`conceptual_grounding_score`），文档说明与 `conceptual_idling` 的区别。
- [ ] 复跑 138n：能从 `literary_observations` 还原四维度逐章趋势（标定报告引用，校准 T3 的 20% 与基线口径）。
- [ ] 生成 `tasks/147-...-DONE.md`；更新 `tasks/V6-README.md` 与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 A（Task 147 行 + 修正说明点 2）、§1.4-T3/T8
- 代码：`db/review_repo.py`（`LiteraryObservationRepository` L180）、`models/literary.py`、`db/schema.sql:252`（literary_observations）、`db/schema.sql:179`（chapter_versions.chapter_number）
