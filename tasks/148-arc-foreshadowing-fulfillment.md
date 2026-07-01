# Task 148: 弧级伏笔兑现率 + 长程伏笔台账

> **Phase**: V6 阶段 A（度量同步）
> **优先级**: P1
> **依赖**: Task 141（ArcPlan 提供弧章节范围）、Task 145（度量出口框架）
> **预计工作量**: 中
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 A

---

## Goal

基于阶段 0 的 `ArcPlan` 弧章节范围，统计**弧级伏笔兑现率**；暴露长程未兑现伏笔（source, expected, 跨度, 状态），并明确区分「被逾期归档」与「真兑现」的伏笔。

## Context（代码核实）

- `foreshadowings` 表（`schema.sql:293-307`）：`planted_in_chapter`、`expected_resolve_chapter`、`status`（planted/due/overdue/**resolved**）、`lifecycle_status`（active/dormant/archived）。**无 `arc_id` 列** → 弧归属须由 `planted_in_chapter` 落在哪个 `ArcPlan.[start_chapter,end_chapter]` 推导。
- **真兑现 vs 逾期归档判别（关键）**：二者在正交列上编码，归档方法**从不覆盖 `status`**：
  - 真兑现：`status='resolved'`（唯一置位处 `_apply.py:513-516`，settlement `operation='resolve'`）。即便之后被 `archive_resolved` 扫成 `lifecycle_status='archived'`，`status` 仍为 `resolved`。
  - 逾期归档（从未兑现）：`status IN ('planted','due','overdue') AND lifecycle_status IN ('dormant','archived')`（`archive_overdue`→dormant >5、`archive_very_overdue`→archived >15，均不动 status）。
  - 仍开放：`lifecycle_status='active' AND status != 'resolved'`。
  - **判别口径**：fulfilled ⇔ `status='resolved'`；abandoned/逾期归档 ⇔ `lifecycle_status IN ('dormant','archived') AND status != 'resolved'`。`lifecycle_status='archived'` **不**等于兑现。
- `ForeshadowingItem` 模型（`models/context.py:63`）**不带 `lifecycle_status`**——现有 repo 读法丢弃该列。→ abandoned 检测需**直接查表**（raw SQL），不能只用 `list_all`。
- `ForeshadowingRepository`（`db/settlement_repo.py:22-301`）方法：create/update_status/list_all/list_active/archive_overdue/archive_very_overdue/archive_resolved/mark_overdue/get_unresolved_ratio。无"按弧/按 lifecycle 统计"方法 → 本 Task 新增。
- `NarrativeRepository.list_arc_plans(project_id)` 与 `get_arc_for_chapter(project_id, chapter)`（`narrative_repo.py:177`，Task 141）提供弧范围/章→弧映射，复用后者做弧归属。
- **历史 DB 限制（C4）**：`arc_plans` 是 Task 141 新表，`.tmp/task138n_...db` / `task138k_...db` **早于骨架、不含 arc_plans**（`get_db()` 不自动迁移）。→ 138n 上**弧级兑现率不可复算**（所有伏笔会落"无弧散点"）；只能复算**全局台账**（resolved vs abandoned 计数）与被遗忘伏笔数。foreshadowings 781 行可用于全局口径。

### 设计决策

1. 弧归属：伏笔 `planted_in_chapter` ∈ `[arc.start_chapter, arc.end_chapter]` → 归该弧（用 `get_arc_for_chapter` 或范围桶）。落在任何 ArcPlan 外/无 arc_plans 时归"无弧散点"（仍计入全局台账）。
2. 弧级兑现率 = 该弧内 `status='resolved'` 伏笔数 / 该弧内伏笔总数（total=0 → 0.0）。
3. 长程未兑现台账：列 `status != 'resolved'` 的伏笔（source=planted_in_chapter, expected=expected_resolve_chapter, span=current_chapter − planted, 状态=open/overdue/abandoned），并**标记 abandoned（逾期归档）**（`lifecycle_status IN ('dormant','archived') AND status!='resolved'`）以区分"被系统遗忘"而非真兑现。
4. 新增按弧/按 lifecycle 的直接查表方法（含 lifecycle_status），不改现有 `list_all`/`list_active` 语义。
5. **无 arc_plans 优雅降级**：`collect_arc_fulfillment` 在 arc_plans 为空/表缺失时返回空弧列表 + 全部伏笔计入全局台账，不报错（保证历史 DB 与无大纲项目可跑）。

## In Scope（必须完成）

- [ ] `ForeshadowingRepository` 新增（raw SQL，含 lifecycle_status）：`async list_with_lifecycle(project_id) -> list[dict]`（返回 foreshadowing_id/description/planted_in_chapter/expected_resolve_chapter/status/lifecycle_status）。
- [ ] 伏笔度量模块（`src/songyan/evals/db_metrics.py`，与 145/146/147 同文件/包）：
  - `async collect_arc_fulfillment(project_id) -> list[ArcFulfillment]`：用 ArcPlan 章节范围桶化伏笔 planted_in_chapter → 每弧 `{arc_index, start, end, total, resolved, abandoned, fulfillment_rate}`。arc_plans 空 → 返回 `[]`（优雅降级）。
  - `async collect_long_range_ledger(project_id, current_chapter) -> list[ForeshadowingLedgerRow]`：所有 `status!='resolved'` 伏笔 + span + `is_abandoned`（逾期归档标记）。
- [ ] `songyan metrics` 增"弧级伏笔兑现率"与"长程伏笔台账（含被遗忘数）"两段。
- [ ] 单测：seed foreshadowings（覆盖 resolved / open / overdue+dormant / archived-unresolved / archived+resolved）+ ArcPlan → 断言弧级兑现率、abandoned 与 resolved 的区分（archived+resolved 仍算 fulfilled；archived+非 resolved 算 abandoned）、无弧散点归类、arc_plans 空时优雅降级、长程台账 span/状态。

## Out of Scope（明确不做）

- 不改伏笔生命周期/归档逻辑（只读统计）。
- 不改 SettlementExtractor 证据规则。
- 不做伏笔自动补兑现/重规划（V7）。
- 弧归属仅按 planted_in_chapter，不引入伏笔↔线索(PlotThread)显式关联（MVP；可选增强留后续）。

## 接口契约

```python
class ArcFulfillment(BaseModel):
    arc_index: int
    start_chapter: int
    end_chapter: int
    total: int
    resolved: int
    abandoned: int
    fulfillment_rate: float          # resolved / total（total=0 时 0.0）

class ForeshadowingLedgerRow(BaseModel):
    foreshadowing_id: str
    description: str
    planted_in_chapter: int
    expected_resolve_chapter: int | None
    span: int                        # current_chapter - planted_in_chapter
    status: str
    is_abandoned: bool               # 逾期归档（非真兑现）

async def collect_arc_fulfillment(project_id) -> list[ArcFulfillment]: ...
async def collect_long_range_ledger(project_id, current_chapter) -> list[ForeshadowingLedgerRow]: ...
```

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_148_foreshadowing_metrics.py -v` 全通过（弧级兑现率 + overdue/archived 区分 + abandoned 标记 + 无弧散点 + arc_plans 空降级 + 台账 span）。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] metrics 可列弧级兑现率与"被系统遗忘"（逾期归档）伏笔数。
- [ ] 单测覆盖 overdue/archived vs resolved 区分（`status='resolved'` 才算兑现；`archived` 不等于兑现）。
- [ ] **复跑 138n（限全局口径）**：能还原**全局** resolved vs abandoned 计数与被遗忘伏笔数（弧级兑现率因 138n 无 arc_plans 不可复算，标定报告注明；如需弧级 sanity，可临时对 138n 回填一条覆盖全 150 章的 ArcPlan）。
- [ ] 生成 `tasks/148-...-DONE.md`；更新 `tasks/V6-README.md` 与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 A（Task 148 行）
- 代码：`db/settlement_repo.py`（`ForeshadowingRepository` L22，archive_overdue L128 / archive_very_overdue L169 / archive_resolved L210）、`agents/settlement_extractor/_apply.py:513`（resolve 置位）、`db/narrative_repo.py`（`list_arc_plans`、`get_arc_for_chapter` L177）、`db/schema.sql:293`（foreshadowings）、`models/context.py:63`（ForeshadowingItem）
