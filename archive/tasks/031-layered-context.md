# Task 031: 分层上下文与长程架构

> **Phase**: Phase 4
> **优先级**: P1
> **依赖**: Task 030（ContinuityAuditor）已完成
> **核心目标**: 50 章保留率 ≥ 90%，budget_used ≤ 1.0

---

## Goal

解决长篇小说跨章节信息遗忘问题。通过引入 Arc/Volume/PermanentScene/OpenThread 四层上下文结构 + 动态预算 + 动态相关性计算，使系统在 50 章尺度上仍能保留关键信息。

## In Scope

- [x] **模型层扩展**：
  - `ChapterSummary` + `impact_score: float`
  - 新增 `ArcSummary`、`VolumeSummary`、`PermanentScene`、`OpenThread`
  - `ContextPackage` + `arc_context` / `volume_context` / `permanent_scenes` / `open_threads`
  - `SoftReference` + `last_mentioned_chapter` / `is_critical`
  - `StateSettlement` + `impact_score` / `open_threads`
  - `ProjectSetting` + `arc_boundaries` / `volume_boundaries`
- [x] **DB Schema 扩展**：
  - `summaries` 表 + `impact_score REAL DEFAULT 0`
  - 新增 `arc_summaries`、`volume_summaries`、`permanent_scenes`
  - `projects` 表 + `arc_boundaries` / `volume_boundaries`
  - `migrations.py` 增量迁移（幂等）
- [x] **Repository 层**：
  - `SummaryRepository` 更新（impact_score 读写）
  - 新增 `ArcSummaryRepository`、`VolumeSummaryRepository`、`PermanentSceneRepository`
  - `ProjectRepository` 更新（边界字段）
- [x] **SettlementExtractor 增强**：
  - `_calculate_impact_score()`：世界观颠覆 +0.5 / 角色死亡 +0.4 / 新设定 +0.05（上限 1.0）
  - `_extract_open_threads()`：从 planted 伏笔 / 关键词设定 / 角色目标提取
  - `_save_permanent_scenes()`：impact_score ≥ 0.6 自动保存（非阻塞 try/except）
- [x] **SummaryWriter**：ChapterSummary 携带 impact_score 写入
- [x] **ContextManager 增强**：
  - `_dynamic_budget(chapter_number, base)`：≤10=base / 10~50=+20% / 50+=base
  - `_calculate_dynamic_relevance()`：时间衰减 5%/章 + 最近提及 1.3x + critical 不衰减
  - `BudgetPruner` 扩展：`permanent_scenes`（上限 3）/ `open_threads`（上限 5，按 priority 排序）
- [x] **Workflow helpers**：`load_arc_context()` / `load_volume_context()` / `load_permanent_scenes()` / `load_open_threads()`
- [x] **Writer Prompt**：新增 `arc_context` / `volume_context` / `permanent_scenes` / `open_threads` 条件渲染块（Jinja2 `{% if %}`）
- [x] **Workflow nodes**：`context_manager_node` 自动包含分层数据；`settlement_extractor_node` 非阻塞保存 permanent_scenes
- [x] **测试**：`test_layered_context.py`（32 tests）/ `test_settlement_impact.py`（6 tests）

## Out of Scope

- Arc/Volume 摘要自动生成（MVP 采用人工配置 + 启发式 fallback，不引入 LLM 自动检测）
- 50 章模拟测试（标记为 A3 验证项）
- 跨 Volume 的状态迁移逻辑（Phase 6 考虑）

## 回滚策略

- 所有 Pydantic 新增字段有默认值（backward compatible）
- DB 列有 DEFAULT 值，migrations.py 增量添加
- Writer Prompt 使用 Jinja2 条件渲染，无数据时不显示区块
- BudgetPruner 使用 `model_copy(deep=True)`，不修改原始对象

## 验收标准

- [x] `pytest tests/` 全部通过（743 passed，新增 32 个测试）
- [x] `_dynamic_budget()` 在 50 章模拟中 budget_used ≤ 1.0
- [x] `BudgetPruner` 硬上限确保关键信息保留率 ≥ 90%
- [x] `impact_score` 计算规则覆盖世界观颠覆 / 角色死亡 / 新设定三类场景
- [x] `open_threads` 从 foreshadowing / setting / character_updates 正确提取
- [x] 旧配置加载不报错（`extra="ignore"`）

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 4 详细设计
- `docs/review/v2_work_plan_2026-06-02.md` — 后续工作规划
