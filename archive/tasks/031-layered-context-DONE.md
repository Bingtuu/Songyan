# Task 031: 分层上下文与长程架构（已完成）

> **Phase**: Phase 4
> **优先级**: P1
> **依赖**: Task 030（ContinuityAuditor）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

### 模型层扩展
- [x] `ChapterSummary` + `impact_score: float = 0.0`
- [x] 新增 `ArcSummary`：`arc_id` / `start/end_chapter` / `arc_title` / `arc_summary` / `key_events` / `resolved_threads` / `new_threads` / `character_arcs`
- [x] 新增 `VolumeSummary`：`volume_id` / `start/end_chapter` / `volume_title` / `volume_summary` / `major_revelations` / `world_state`
- [x] 新增 `PermanentScene`：`scene_id` / `chapter_number` / `scene_number` / `excerpt` / `impact_tags` / `referenced_by`
- [x] 新增 `OpenThread`：`thread_id` / `description` / `source_type` / `source_chapter` / `priority`
- [x] `ContextPackage` + `arc_context` / `volume_context` / `permanent_scenes` / `open_threads`
- [x] `SoftReference` + `last_mentioned_chapter: int | None` / `is_critical: bool`
- [x] `StateSettlement` + `impact_score: float` / `open_threads: list[str]`
- [x] `ProjectSetting` + `arc_boundaries: list[int]` / `volume_boundaries: list[int]`

### DB Schema 扩展
- [x] `summaries` 表 + `impact_score REAL DEFAULT 0`
- [x] 新增 `arc_summaries`、`volume_summaries`、`permanent_scenes`
- [x] `projects` 表 + `arc_boundaries TEXT DEFAULT '[]'` / `volume_boundaries TEXT DEFAULT '[]'`
- [x] `migrations.py` 增量迁移（幂等执行）

### Repository 层
- [x] `SummaryRepository` 更新（`impact_score` 读写）
- [x] 新增 `ArcSummaryRepository`：`create` / `get_current_arc`（按 chapter_number 范围）/ `list_by_project`
- [x] 新增 `VolumeSummaryRepository`：`create` / `get_current_volume` / `list_by_project`
- [x] 新增 `PermanentSceneRepository`：`create` / `list_by_project(limit=5)` / `add_reference`
- [x] `ProjectRepository` 更新（边界字段）

### SettlementExtractor 增强
- [x] `_calculate_impact_score()`：世界观颠覆 +0.5 / 角色死亡/重伤 +0.4 / 新设定 +0.05 each（上限 1.0）
- [x] `_extract_open_threads()`：从 `foreshadowing_updates`（planted）/ `new_settings`（关键词过滤）/ `character_updates`（goal 字段）提取
- [x] `_save_permanent_scenes()`：`impact_score >= 0.6` 时保存到 `permanent_scenes` 表（非阻塞 try/except）

### SummaryWriter
- [x] ChapterSummary 携带 `impact_score` 写入 `summaries` 表

### ContextManager 增强
- [x] `_dynamic_budget(chapter_number, base)`：≤10=base / 10~50=+20% / 50+=base
- [x] `_calculate_dynamic_relevance()`：时间衰减 5%/章（min 0.3）+ 最近提及 1.3x + `is_critical` 不衰减（cap 0.9）
- [x] `BudgetPruner` 扩展：`permanent_scenes`（上限 3）/ `open_threads`（上限 5，按 priority 排序）
- [x] `PARTITION_PRIORITY` 更新：`soft_references=10`（降级）/ `open_threads=9` / `permanent_scenes=8`

### Workflow 集成
- [x] `_helpers.py`：`load_arc_context()` / `load_volume_context()` / `load_permanent_scenes()` / `load_open_threads()`
- [x] `context_manager_node` 自动包含分层数据
- [x] `settlement_extractor_node` 非阻塞保存 permanent_scenes

### Writer Prompt
- [x] 新增 `arc_context` / `volume_context` / `permanent_scenes` / `open_threads` 条件渲染块（Jinja2 `{% if %}`）

### 测试
- [x] `tests/test_layered_context.py` — 32 tests（动态预算、动态相关性、Repository CRUD）
- [x] `tests/test_settlement_impact.py` — 6 tests（impact_score 计算、open_threads 提取）
- [x] 更新 `tests/test_context_manager.py`（BudgetPruner 扩展验证）
- [x] 总计：743 passed（新增 32 个测试）

---

## 关键决策

### impact_score 纯代码规则
不调用 LLM，完全基于 settlement 数据做规则计算。这保证测试可控、执行快速（< 1ms），且不受 LLM 输出波动影响。规则设计：世界观颠覆（最高权重 0.5）> 角色死亡（0.4）> 新设定（0.05 each）。上限 1.0 防止累积溢出。

### PermanentScene 简化策略
不按 scene 分割章节，整个章节视为一个 permanent scene。`excerpt` = content 前 200 字；`impact_tags` 从 settlement 推断。这是工程 trade-off：牺牲粒度换取实现速度和测试稳定性。

### OpenThread 纯代码提取
不调用 LLM，从三类 settlement 数据中提取：foreshadowing_updates（status=planted）、new_settings（含关键词如"谜团""秘密""真相"）、character_updates（goal 字段非空）。规则透明、测试可预测。

### 动态预算三层分段
前 10 章基础预算（精细上下文期），10~50 章 +20%（分层摘要介入期），50+ 章回归基础（依赖 Volume 摘要）。分段依据：前 10 章需要精细记忆，中期需要更多 token 承载分层摘要，后期 Volume 摘要压缩信息后基础预算足够。

---

## 基线验证

| 指标 | 目标 | 当前状态 |
|------|------|----------|
| 50 章 budget_used | ≤ 1.0 | 单元测试验证通过，未跑完整 50 章模拟 |
| 关键信息保留率 | ≥ 90% | BudgetPruner 硬上限确保，未跑完整模拟 |
| impact_score 计算 | 规则覆盖 | 三类场景（世界观/角色/设定）100% 覆盖 |

> ⚠️ **遗留风险**：50 章模拟测试标记为 A3 验证项，待 Task 034 补齐。

---

## 交付物

- `src/songyan/models/context.py` — 分层上下文模型（ArcSummary / VolumeSummary / PermanentScene / OpenThread）
- `src/songyan/models/settlement.py` — `StateSettlement` 扩展
- `src/songyan/models/project.py` — `ProjectSetting` 扩展
- `src/songyan/db/layered_context_repo.py` — Arc/Volume/PermanentScene Repository
- `src/songyan/db/schema.sql` — Phase 4 表结构
- `src/songyan/db/migrations.py` — 增量迁移
- `src/songyan/agents/settlement_extractor.py` — impact_score / open_threads / permanent_scenes
- `src/songyan/agents/context_manager.py` — 动态预算 + 动态相关性 + BudgetPruner
- `src/songyan/agents/writer.py` — 分层上下文 Prompt 渲染
- `src/songyan/workflows/_helpers.py` — 分层数据加载 helpers
- `prompts/cards/writer/1.0.4.yaml` — Writer Prompt 条件渲染块
- `tests/test_layered_context.py` — 32 tests
- `tests/test_settlement_impact.py` — 6 tests

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| Arc/Volume 摘要为空壳 | 中 | `ArcSummary` / `VolumeSummary` 模型和 Repository 已就位，但摘要内容为空字符串。MVP 采用人工配置 `arc_boundaries` + 启发式 fallback，未引入 LLM 自动检测。需 A3 补齐自动生成。 |
| 50 章模拟未跑 | 高 | 仅通过单元测试验证 budget 逻辑，未在 40 章模拟 + 10 章真实数据上验证保留率。需 A3 补齐。 |
| 第 6 代实验体消失 | 中 | 基线人工报告记录的实际断点，ContinuityAuditor 因 state_mismatches 为空壳未能自动捕获。 |

---

## 下一步

**Stage A 还债阶段（Task 032~034）**
- A1: 补齐 028~031 的 DONE 报告（当前任务）
- A2: Task 025 工程优化收尾（模糊匹配 / 成本估算 / 上下文压缩）
- A3: 遗留验证补齐（Punch 评估 / state_mismatches 实装 / Arc+Volume 摘要 / 50 章模拟）

**Stage B Phase 5 — Genre 框架增强 + 风格多样化**
- B1: GenreProfile 模型升级（pacing 结构化 / 子类型 / 感官模板 / 情感弧线库）
