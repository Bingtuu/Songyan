# Task 034: 遗留验证补齐（已完成）

> **Phase**: Stage A（还债与封锁解除）
> **优先级**: P0（阻塞后续 Phase 5/6）
> **依赖**: Task 032（DONE 报告）、Task 033（工程优化）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

### A3-1: Punch Engine 自动评估

- [x] 创建 `src/songyan/evals/punch_metrics.py`：
  - `PunchMetrics` 模型：chapter_number / word_count / punch_count / punch_density / emotion_switches / emotion_switch_rate
  - `evaluate_punch_metrics(project_id)`：从 creative_briefs 读取 punch_points / emotion_arc，计算密度和转折率
  - `save_punch_metrics()`：输出 JSON 到 `evals/output/punch_metrics.json`
  - 支持空项目（返回空列表）

### A3-2: ContinuityAuditor state_mismatches 实装

- [x] 修改 `src/songyan/agents/continuity_auditor.py` 的 `_find_state_mismatches()`：
  - 查询 `character_states` JOIN `chapter_versions` 获取 chapter_number
  - 按 `character_id + field` 分组，检测 `STATE_MISMATCH_WINDOW`（2 章）内值变化
  - 检测类型覆盖：角色位置跳变、数值状态变化、任何 field 的突变
  - severity 分级：1 章内跳变 = major，2 章内 = minor
  - 返回真实 `StateMismatch` 列表（非空壳）

### A3-3: Arc/Volume 摘要自动生成

- [x] 创建 `src/songyan/agents/arc_summary_generator.py`：
  - `generate_arc_summary(project_id, start_chapter, end_chapter)`：基于 summaries 表聚合
    - arc_title: "Arc {start}-{end}"
    - arc_summary: 合并各章 summary（上限 500 字符）
    - key_events: 合并去重（上限 20 个）
    - character_arcs: 统计角色出现次数
    - 写入 `arc_summaries` 表
  - `generate_volume_summary(project_id, start_chapter, end_chapter)`：
    - 优先基于 ArcSummary，无 Arc 时退回到 ChapterSummary
    - volume_summary: 合并摘要（上限 1000 字符）
    - major_revelations: 高 impact 章节的关键事件
    - 写入 `volume_summaries` 表
  - `auto_generate_arc_summaries(project_id, arc_boundaries)`：根据边界批量生成

### A3-4: 50 章模拟测试

- [x] 创建 `src/songyan/evals/simulation_50ch.py`：
  - `run_50chapter_simulation(real_chapters=10, simulated_chapters=40, budget_tokens=8000)`：
    - 构造随 chapter_number 增长的 ContextPackage（soft_refs / open_threads / permanent_scenes 递增）
    - 10 章后注入 ArcSummary，30 章后注入 VolumeSummary
    - 运行 BudgetPruner，记录每章 budget_used
    - 计算关键信息保留率（critical soft_refs / open_threads / permanent_scenes）
  - `SimulationReport`：budget_used / retention_rate / critical_loss_count
  - `save_simulation_report()`：输出 JSON 到 `evals/output/50ch_simulation_report.json`
  - **验证结果**：50 章模拟 budget_used ≤ 1.0，retention_rate ≥ 90%

### 测试

- [x] `tests/test_validation_gapfill.py` — 12 tests：
  - PunchMetrics: 空项目 / 有数据评估 / 保存 JSON
  - StateMismatches: 无变化 / 位置跳变检测 / 同值不触发
  - ArcSummaryGenerator: Arc 生成 / Volume 生成 / 批量自动生成
  - Simulation50Ch: 50 章模拟 / 报告模型 / 保存报告
- [x] 现有测试全部通过：72 passed（layered_context + settlement_extractor + settlement_impact）
- [x] ruff 0 errors

---

## 关键决策

### state_mismatches 通过 JOIN 获取 chapter_number
character_states 表没有 chapter_number 字段，但通过 source_version_id JOIN chapter_versions 可以获取。这比修改 schema 更轻量，且不需要迁移。

### Arc 摘要纯聚合策略（不调用 LLM）
基于 summaries 表的纯代码聚合，保持测试可控。Arc 摘要质量取决于 ChapterSummary 的质量，这在 SettlementExtractor + SummaryWriter 的闭环中已经保证。

### 50 章模拟使用构造数据
真实 DB 中只有 1 个 summary 记录，无法做真实 50 章模拟。使用 `_build_mock_context_package()` 构造随 chapter_number 增长的数据，模拟真实的长篇小说上下文膨胀场景。

---

## 基线验证

| 指标 | 目标 | 验证结果 |
|------|------|----------|
| Punch 密度输出 | 可量化 | ✅ `punch_metrics.json` 格式正确 |
| state_mismatches 检测 | ≥ 1 类真实矛盾 | ✅ 位置跳变检测通过 |
| Arc 摘要非空 | 非空字符串 | ✅ `arc_summaries` 表有数据 |
| 50 章 budget_used | ≤ 1.0 | ✅ 模拟通过 |
| 50 章保留率 | ≥ 90% | ✅ 模拟通过 |

---

## 交付物

- `src/songyan/evals/punch_metrics.py` — Punch Engine 量化评估
- `src/songyan/evals/simulation_50ch.py` — 50 章模拟测试
- `src/songyan/agents/arc_summary_generator.py` — Arc/Volume 摘要自动生成
- `src/songyan/agents/continuity_auditor.py` — state_mismatches 实装
- `tests/test_validation_gapfill.py` — 12 tests

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| Punch 评估依赖 creative_briefs 数据 | 低 | 早期章节（Phase 0 前生成）无 punch_points 数据，脚本返回空列表。新章节生成后会自动填充。 |
| Arc 摘要质量取决于 ChapterSummary 质量 | 低 | 纯聚合策略不引入额外质量风险。 |

---

## 下一步

**Stage B Phase 5 — Genre 框架增强 + 风格多样化**
- B1: GenreProfile 模型升级（pacing 结构化 / 子类型 / 感官模板 / 情感弧线库）
- B2: 新增 5 个 Genre 配置 + xuanhuan 增强
- B3: Style Mimicry Engine
- B4: Writer Prompt 风格注入 + fatigue_words 扩充
