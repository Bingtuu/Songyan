# Task 152: critical 设定显式 resolve / 作废出口

> **Phase**: V6 阶段 B（末端治理）
> **优先级**: P1（把 critical 的"沉寂归档"替换为真回收路径，收口 orphan 生命周期）
> **依赖**: 阶段 0（Task 144 状态机范式）+ Task 149（候选态）+ Task 150（分类收紧）；建议阶段 B 内最后做
> **预计工作量**: 中（拆 152a 生命周期数据/仓储 + 152b 结算联动与 MR/orphan 剔除）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 B

---

## Goal

为 critical 设定提供**显式的"剧情已交代 → resolve"或"确认废弃 → abandon"出口**，替代当前"只能靠久未提及被沉寂归档"的隐式路径。显式 resolve 的设定不再计入 orphan、移出 MR 注入；废弃设定同样移出，但两者与"被系统遗忘（逾期归档）"在度量上可区分——让 orphan 曲线反映真实治理，而非被沉默阈值粉饰。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **设定目前只有 `active → archived` 一条隐式生命线**，且都由"沉默"驱动：
  - `setting_tracking.status`：`update_status` / `archive_long_silent_nonessential`（`db/continuity_repo.py`，`LONG_SILENT_ARCHIVE_WINDOWS = {background:8, technical:10}`，**明确排除 critical/recurring 与人工标记**——即 critical 根本不会被自动归档，只会一直挂着变 orphan）。
  - `setting_snapshots.lifecycle_status`：`active/dormant/archived`（`settlement_repo.py` `archive_by_confidence`）。
  - `SettingEvaporator`：`_calculate_resolve_confidence` + `CONFIDENCE_ARCHIVE_THRESHOLDS` 按 confidence 归档，仍是"蒸发/归档"语义。
  - **没有 abandon 状态，也没有"剧情交代已 resolve"这一显式、可追溯的回收出口**。因此 critical 设定要么被正文持续引用、要么永远 orphan——这正是 T6b(P1=0) 难达标的结构性原因。
- **可复用范式**：Task 144 的 `PlotThread` 已有 `resolved` / `abandoned` 显式状态与 `advance_thread_status`（`_ALLOWED_TRANSITIONS`，写 `last_status_chapter`/`version_id`，T1 可追溯）。本 Task 为 critical **设定**建立类比机制（net-new，设定侧此前无此能力）。
- **证据来源**：settlement 已产出 `resolved_hooks` / `foreshadowing_updates(operation="resolve")`（见 Task 144 `_thread_economy._settlement_resolved_text`）。可据此在结算后处理判定某 critical 设定是否被本章"交代收束"，避免新增 LLM 判断。

### Cross-Task Coordination

`setting_tracking.status` 完整状态机的**权威定义见 `tasks/149-input-side-demotion.md` → Cross-Task Coordination**（不在此重画，避免漂移）。本 Task 负责其中新增的两条终态迁移：

```
active/candidate ──► resolved   （剧情交代收束，本 Task）
active/candidate ──► abandoned  （确认废弃，本 Task）
resolved / abandoned 为终态（不可再迁出）
```

- **MR 注入**：只取 `active`，`resolved`/`abandoned` 自动不进 MR。
- **orphan 分母**：`find_orphaned` 只认 `status='active'`（`continuity_repo.py:248-269`），故 `resolved`/`abandoned` 天然被排除，无需新增过滤；`collect_orphan_metrics` 复用该口径。
- **`abandoned` 触发信号**：当前仅由**显式外部信号**驱动——大纲/弧规划中标记某 critical 设定"废弃"（通过 `ArcPlan`/`PlotThread` 元数据或 CLI 配置传入），不在运行中自动判定。V7 前不扩展为自动智能废弃。
- **度量区分复用 Task 148**："显式 resolve" = `status='resolved'`；"显式 abandon" = `status='abandoned'`；"被逾期归档/遗忘" = Task 148 定义的 overdue + archived（未被显式 resolve 但 confidence/沉默阈值已归档）。

**边界（防膨胀）**：只为 critical（及可选 recurring）设定加 `resolved`/`abandoned` 两个显式终态与回收出口；不重构 background/technical 的沉默归档；不做"自动判定所有设定何时该废弃"的智能闭环（V7）。显式 resolve 优先由 **settlement 证据驱动**，abandon 可由显式信号（如大纲/线索标记废弃）驱动。

## In Scope（必须完成）

### 152a — 设定生命周期数据 + 仓储
- [ ] 为 critical 设定引入显式终态 `resolved` / `abandoned`（落在 `setting_tracking.status` 或专用列，创建前定方案：优先复用 `status` 并明确与 `active/candidate/archived` 的迁移关系；`resolved`/`abandoned` 与"沉寂 archived"在查询上可区分）。
- [ ] `SettingTrackingRepository`：`resolve_setting(tracking_id, chapter, version_id, conn=None)` / `abandon_setting(tracking_id, chapter, reason, conn=None)`，写回收章/版本/原因（T1 式可追溯）。合法迁移校验（参照 PlotThread `_ALLOWED_TRANSITIONS`：`active/candidate → resolved|abandoned`；`resolved/abandoned` 为终态）。
- [ ] 查询侧：`find_orphaned` 排除 `resolved`/`abandoned`；`db_metrics.collect_orphan_metrics` 的 orphan 分母排除显式回收，但**保留"逾期归档 vs 真 resolve"区分口径**（复用 Task 148 的 overdue/archived 区分思路，详见 Cross-Task Coordination）。

### 152b — 结算联动 + MR/orphan 剔除
- [ ] settlement 后处理（service 层，复用 Task 144/149 同层）：依本章 `resolved_hooks` / `foreshadowing resolve` 证据，把被交代收束的 critical 设定 `resolve_setting`（可追溯到本章 version）。
- [ ] `abandoned` 由显式外部信号驱动（大纲/弧规划标记废弃），经 service 层调用 `abandon_setting`，写废弃原因。
- [ ] 显式 resolve/abandon 的设定**移出 MR 注入**（`_load_critical_mandatory_references` 过滤）与 orphan 计数。
- [ ] 度量区分：`songyan metrics` / report 能区分"显式 resolve""显式 abandon""被逾期归档/遗忘"三类，避免用 resolve 掩盖遗忘。
- [ ] 遵守边界：生命周期变更经 service/repository；不改 SettlementExtractor 证据校验规则；不新增 Agent/LLM；无骨架项目也能用（resolve 基于 settlement 证据，不强依赖 PlotThread）。

## Out of Scope（明确不做）

- 不重构 background/technical 的沉默归档逻辑（保留现状）。
- 不做"自动判定设定何时废弃"的智能闭环（V7）。
- 不做录入侧降级（149）、分类收紧（150）、MR 上限/排序（151）本身——本 Task 只加生命周期出口并在 MR/orphan 剔除处接线。

## 接口契约

```python
# repository（db/continuity_repo.py）
async def resolve_setting(
    self, tracking_id: str, chapter: int, source_version_id: str,
    conn: aiosqlite.Connection | None = None,
) -> None:
    """critical 设定被剧情交代收束：active/candidate -> resolved（可追溯）."""

async def abandon_setting(
    self, tracking_id: str, chapter: int, reason: str,
    conn: aiosqlite.Connection | None = None,
) -> None:
    """确认废弃：active/candidate -> abandoned（写原因）."""

# service（settlement 后处理）
async def resolve_settings_after_settlement(
    project_id: str, chapter_number: int, version_id: str,
    settlement: StateSettlement,
) -> list[str]:
    """依本章收束证据 resolve 相关 critical 设定；返回被 resolve 的 setting_key 列表."""
```

## 测试要求

### Layer 2: 模块测试（真实临时 SQLite；Mock LLM）
- [ ] 显式 resolve：`resolve_setting` 后 `find_orphaned` 不含该条；状态/章/版本写入正确；非法迁移（如 `resolved → active`）被拒。
- [ ] 显式 abandon：`abandon_setting` 后移出 MR 与 orphan；写入 reason。
- [ ] 结算联动：构造含 `resolved_hooks` 的 settlement → 对应 critical 设定被 `resolve_setting`（证据匹配可解释）。
- [ ] **度量区分**：造"显式 resolve""被逾期归档"两类设定，验证 metrics/report 分别计数、不混淆。
- [ ] 不误伤：仍活跃、被正文引用的 critical 不被误 resolve。

### Layer 3: 历史/小窗口验证（阶段 B 出口收口）
- [ ] 在带大纲小窗口复跑中：至少一条 critical 设定走完 `active → resolved` 并可定位收束章/version；resolve 后不再进 MR/orphan。
- [ ] 配合 Task 149/150/151 复算 Ch1-Ch50：验证 orphan 斜率 ≤138n×0.5、**P1(critical) orphan=0**（T6b）——显式回收出口是 P1=0 的关键。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_152_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] critical 设定支持显式 `resolved`/`abandoned`，可追溯、移出 MR/orphan，且与"逾期归档/遗忘"在度量上可区分。
- [ ] Layer 3 证明 ≥1 条 critical 走完显式 resolve；配合 149/150/151 达成 Ch1-Ch50 的 T6b（P1=0）。
- [ ] 不违反不可违背规则：生命周期经 service/repository；settlement 证据规则不动；不新增 Agent/LLM。
- [ ] 生成 `tasks/152-critical-explicit-resolve-abandon-DONE.md`，含生命周期方案（status vs 专列）、迁移合法性、度量区分口径、Layer 3 证据。
- [ ] 更新 `tasks/V6-README.md`（152 状态 + **阶段 B 出口结论**：Ch1-Ch50 满足 T6 全三项 + health≥7.0）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.4-T6/T8、§3 阶段 B（Task 152 行 + 阶段 B 出口）
- 现有代码：`db/continuity_repo.py`（`SettingTrackingRepository`：`update_status`/`archive_long_silent_nonessential`/`find_orphaned`）、`db/settlement_repo.py`（`archive_by_confidence`/`lifecycle_status`）、`agents/setting_evaporator/`（confidence 归档）、`db/narrative_repo.py`（PlotThread `_ALLOWED_TRANSITIONS` 范式）
- 结算证据：`workflows/_thread_economy.py`（`_settlement_resolved_text`）、Task 144/148（overdue/archived 区分）
