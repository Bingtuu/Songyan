# Task 149: 录入侧降级（超额 critical 转候选，非硬丢弃）

> **Phase**: V6 阶段 B（末端治理）
> **优先级**: P0（阶段 B 出口 T6c 归因判据的直接实现）
> **依赖**: 阶段 0（Task 141-144 骨架/线索）+ 阶段 A（Task 145 orphan/T7 度量、148z 阈值冻结）已落地
> **预计工作量**: 中（拆 149a 数据/仓储 + 149b 路由与回升）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 B

---

## Goal

单章 settlement 写入的 `new_settings`（尤其 `category=critical`）超过阈值时，把**超额部分标记为候选（低优先）而非直接以 `active` 入库**，避免"Writer 一章甩出一堆 critical → 全部入 active → 后续全变 orphan"的录入侧放大。候选设定不注入 MR、不计入 orphan 分母，但**保留在库、可回升为正式**——绝不硬丢弃，防止事实库与正文脱节。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- `settlement_extractor/_apply.py` 的 `_update_continuity_tracking`（约 L741-760）对 `settlement.new_settings` 逐条：已存在 key → `update_last_mentioned`；新 key → `SettingTrackingRepository.create(..., category=_infer_setting_category(setting))`。
- `SettingTrackingRepository.create`（`db/continuity_repo.py:35-78`）写入 `setting_tracking`，`status` 列 `DEFAULT 'active'`。**当前不存在任何"候选/低优先/降级"状态——每条抽取到的设定都以 `status='active'` 入库**。因此本 Task 是净新增，不是修改既有降级逻辑。
- 表 `setting_tracking` 的 `status` 目前无 CHECK 约束（`category` 有 CHECK），新增 `candidate` 值预计无需改 CHECK；创建前需最终确认迁移文件（`db/migrations.py`）中该列定义。
- 148z 已把 T6c 的"被降级 critical ≤ 新增 critical 总数 15%"子句**延后到本 Task**落地度量口径。

**为什么是"降级为候选"而非"限流丢弃"**：阶段 0 骨架 + Task 144 约束已从**产生侧**压 T7；本 Task 只做治理侧兜底。硬丢弃会让正文提到、事实库却查不到的设定制造新的连续性裂缝，违背"SQLite 是唯一事实源"精神。候选是**可逆**的软降级。

## Cross-Task Coordination（阶段 B 统一口径）

### `setting_tracking.status` 完整状态机（阶段 B 权威定义）

> 本节是阶段 B `setting_tracking.status` 状态机的**唯一权威定义**；Task 151/152 引用本节，不另画图，避免多处漂移。

本 Task 引入 `candidate`；Task 152 将引入 `resolved` / `abandoned`。阶段 B 结束后完整取值含义如下：

```
active    ──► candidate   （降级，超额 critical，本 Task）
candidate ──► active      （回升，后续章再次引用，本 Task）
active    ──► archived    （沉默归档，现有逻辑，background/technical 等）
active/candidate ──► resolved   （剧情交代收束，Task 152）
active/candidate ──► abandoned  （确认废弃，Task 152）
resolved / abandoned 为终态
```

- **MR 注入**：仅取 `status == 'active'` 且 `category == 'critical'`。`candidate` / `resolved` / `abandoned` 自动不进 MR（与 Task 151/152 交叉验证）。
- **orphan 分母**：`find_orphaned` 现状 SQL 硬编码 `status = 'active'`（`continuity_repo.py:248-269`），故只要 `candidate` / `resolved` / `abandoned` 不叫 `active`，排除即**天然成立**——本 Task 不需为排除 candidate 新增过滤逻辑，只需保证降级后的 status 值不是 `active`。`collect_orphan_metrics` 复用该口径。
- **T7 口径（守约，非新增）**：`new_settings_by_chapter`（`continuity_repo.py:272-287`）现状**无 status 过滤**，按 `introduced_in_chapter, category` 分组，天然把 `candidate` 也计入写入侧。故 T7 = 写入侧全部 critical（含 `candidate`）是**现状**，不是需要新写的口径。**本 Task 明确不得给 `new_settings_by_chapter` / `collect_new_critical_rate` 增加排除 `candidate` 的过滤**——否则会用"降级"粉饰产生速率，破坏 T6c 归因。T6c 时再单独看"被降级为 candidate 的 critical 占比 ≤ 15%"。

### 超额选择策略

单章新增 critical 数超过 `critical_cap` 时，按以下规则决定哪些降级：

1. 保留证据最完整的条目：优先保留 `source_quote` 非空且能在正文中命中的条目。
2. 同证据等级下按 `new_settings` 原始顺序保留（与 settlement 输出顺序一致，可解释）。
3. 超出部分全部标记为 `candidate`。

### 阈值初版

首版 `critical_cap` 取 **3**（即单章第 4 条及以后新增 critical 降级）。该值保守，后续在 Layer 3 用 138k/138n 数据校准并在 DONE 中记录调整依据。

## In Scope（必须完成）

### 149a — 数据模型 + 仓储支持候选态
- [ ] `setting_tracking.status` 支持新值 `candidate`（迁移；确认无 CHECK 冲突；不破坏现有 `active`/`archived` 读写）。
- [ ] `SettingTrackingRepository`：`create(..., status='active')` 允许显式传 `status='candidate'`；新增 `promote_to_active(tracking_id, chapter, version_id, conn=None)`（候选→正式，写来源章/版本）。**排除口径按 Cross-Task Coordination 守约**：`find_orphaned` 因只认 `status='active'` 天然排除 candidate（不新增过滤）；`new_settings_by_chapter`（T7）**不得**新增 candidate 过滤（天然含 candidate）。
- [ ] 单测覆盖：候选写入、候选默认不入 orphan、候选可 `promote_to_active`。

### 149b — 录入路由与回升触发
- [ ] 在 settlement 后处理（service 层，非 SettlementExtractor 内部证据校验）判定"单章 critical 录入超额"：阈值首版 `critical_cap=3`，后续在 Layer 3 用 138k/138n 校准并在 DONE 记录来源。超额的 critical 新设定按 **Cross-Task Coordination 中的选择策略** 降级为 `status='candidate'` 入库，未超额部分照旧 `active`。
- [ ] **回升机制**：候选设定在后续章被正文再次引用（复用 Task 144 的 settlement 证据文本匹配思路：thread/setting_key/name 命中，优先精确匹配、其次子串匹配）时 `promote_to_active`。回升写 `source_version_id`/章号，保持可追溯。
- [ ] 遵守边界：路由与回升逻辑在 service / repository；不改 SettlementExtractor 证据校验规则；不新增 Agent / LLM 调用；无大纲/无骨架项目也能工作（候选机制不依赖 PlotThread）。

## Out of Scope（明确不做）

- 不改 `_infer_setting_category` 的分类逻辑（那是 Task 150）。
- 不做 MR 上限自适应 / 排序（Task 151）。
- 不做 critical 的显式 resolve/作废出口（Task 152）。
- 不引入新 LLM 判断"该设定重要与否"——超额判定用可解释的计数阈值 + 证据匹配。

## 接口契约

```python
# repository（db/continuity_repo.py）
async def promote_to_active(
    self, tracking_id: str, chapter: int, source_version_id: str,
    conn: aiosqlite.Connection | None = None,
) -> None:
    """候选设定回升为正式（candidate -> active），写回被引用章/版本."""

# service（settlement 后处理，新增或并入现有 _thread_economy 同层模块）
async def demote_overflow_new_settings(
    project_id: str, chapter_number: int, version_id: str,
    settlement: StateSettlement, *, critical_cap: int,
) -> list[str]:
    """把单章超额 critical 新设定改以 candidate 入库；返回被降级的 setting_key 列表."""
```

## 测试要求

### Layer 2: 模块测试（真实临时 SQLite；Mock LLM）
- [ ] 候选写入：`create(status='candidate')` 后 `find_orphaned` 默认不含该条。
- [ ] 超额路由：构造单章 M 条 critical（M > cap），验证前 cap 条 `active`、其余 `candidate`（选择策略需确定并单测，如按 source_quote 完整度/出现顺序）。
- [ ] 回升：候选设定在后续章证据命中 → `promote_to_active`，`status` 变 `active` 且写章/版本。
- [ ] 不误伤：cap 内的章节所有 critical 仍 `active`；无骨架项目路由正常。
- [ ] **T7 口径守约**：单测确认 `collect_new_critical_rate` / `new_settings_by_chapter` 仍无 status 过滤（`candidate` 计入 T7 写入侧），并断言"仅 orphan 分母排除 candidate"。DONE 中明确该口径并核对 Layer 3 数据。

### Layer 3: 历史 DB 复算（阶段 B 出口归因）
- [ ] 用 `.tmp/task138k_ch1_ch30_rehearsal_20260629.db` 同项目复跑/复算：
  - orphan 斜率较 138n 基线下降；
  - **被降级为候选的 critical 数 ≤ 同窗口新增 critical 总数的 15%**（T6c 子句）；
  - 用 `songyan metrics` 的 orphan/T7 段读出对比曲线并入报告。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_149_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 候选态可写、默认不入 orphan、可回升为正式，全部单测覆盖。
- [ ] Layer 3 复算证明 orphan 斜率下降且被降级 critical ≤ 15%（T6c），证据入 `docs/reports/`。
- [ ] 不违反不可违背规则：录入路由经 service/repository；`character_states`/settlement 证据规则不动；候选不硬丢弃、可追溯。
- [ ] 生成 `archive/v6/tasks/149-input-side-demotion-DONE.md`，含超额阈值来源、T7 与候选口径决定、Layer 3 归因证据。
- [ ] 更新 `tasks/V6-README.md`（149 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.4-T6/T7、§3 阶段 B（Task 149 行 + 阶段 B 出口）
- 现有代码：`settlement_extractor/_apply.py`（`_update_continuity_tracking`/`_infer_setting_category`）、`db/continuity_repo.py`（`SettingTrackingRepository`）、`evals/db_metrics.py`（`collect_orphan_metrics`/`collect_new_critical_rate`）
- 阶段 A 冻结口径：`archive/v6/tasks/148z-stage-a-threshold-calibration-DONE.md`、`archive/v6/reports/v6-stageA-threshold-calibration.md`
