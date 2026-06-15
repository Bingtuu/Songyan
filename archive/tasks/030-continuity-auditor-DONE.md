# Task 030: ContinuityAuditor — 跨章一致性引擎（已完成）

> **Phase**: Phase 3
> **优先级**: P1
> **依赖**: Task 029（HITL 增强）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

- [x] 新增 4 个 DB 表：`setting_tracking`、`inventory_tracker`、`location_tracker`、`continuity_reports`
- [x] 新增 Continuity 模型：
  - `ContinuityReport`（整体健康分 + 问题列表）
  - `OrphanedSetting`（ orphaned 设定）
  - `ForgottenItem`（遗忘道具）
  - `StateMismatch`（状态矛盾）
  - `OverdueForeshadowing`（逾期伏笔）
- [x] 新增 Repositories：
  - `SettingTrackingRepository`
  - `InventoryTrackerRepository`
  - `LocationTrackerRepository`
  - `ContinuityReportRepository`
- [x] Settlement Extractor 增强：
  - 更新 `setting_tracking`（新设定插入，已有设定更新 `last_mentioned_chapter`）
  - 从 `character_updates` 推断 inventory/location 变化并写入 tracker 表
  - 自动更新 foreshadowing status：`planted` → `due` → `overdue`
- [x] 新增 `ContinuityAuditor` Agent：
  - `_find_orphaned_settings`：`last_mentioned_chapter` 超过 3 章未引用
  - `_find_forgotten_items`：`last_used_chapter` 超过 3 章
  - `_find_overdue_foreshadowings`：`expected_resolve_chapter` 已过
  - `_compute_health_score`：0-10 健康评分（满分 = 无问题）
  - `_find_state_mismatches`：暂时返回空列表（`character_states` 表缺少 `chapter_number` 索引，标记为 A3 增强项）
- [x] Phase2Graph 集成：每完成 3 章自动运行 `ContinuityAuditor`，健康分 < 7.0 记录警告
- [x] 测试：45 passed

---

## 关键决策

### 追踪更新在主事务外执行
Settlement Extractor 的 `apply_settlement()` 中，tracking 表更新（setting/inventory/location）在独立的 try/except 块中执行。即使 tracking 更新失败，主 settlement 事务仍然成功提交。这避免了 tracking 逻辑的错误破坏核心结算流程。

### 非阻塞审计策略
ContinuityAuditor 在 Phase2Graph 中通过 try/except 调用，审计失败不阻塞流水线。Phase 3 MVP 策略是"发现问题但不自动修复"，修复决策留给 Phase 4 的分层上下文系统。

---

## 基线验证

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| orphaned settings | = 0 | `ContinuityReport.orphaned_settings` 为空 |
| forgotten items | = 0 | `ContinuityReport.forgotten_items` 为空 |
| 连续性健康分 | ≥ 7.0 | `ContinuityReport.overall_health_score` |

> ⚠️ **数据失真说明**：基线一致性评分 10.0 因无 DB 历史数据（文件系统 fallback 模式），实际断点（第 6 代实验体消失、120Hz 干扰器遗忘）仅在人工报告 `orbital_horror_ch2_ch11_assessment.md` 中记录。`state_mismatches` 检测待 A3 增强。

---

## 交付物

- `src/songyan/agents/continuity_auditor.py` — ContinuityAuditor Agent
- `src/songyan/agents/settlement_extractor.py` — tracking 更新逻辑
- `src/songyan/db/schema.sql` — 4 个新表定义
- `src/songyan/db/migrations.py` — 增量迁移
- `src/songyan/db/continuity_repo.py` — 4 个 Repository
- `src/songyan/models/continuity.py` — Continuity 模型

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| state_mismatches 为空壳 | 高 | `_find_state_mismatches` 返回空列表，无法检测角色状态矛盾、道具状态跳变等真实问题。需 A3 基于 `character_states` 历史对比实现。 |
| 数据失真 | 中 | 基线评分 10.0 不可信，需 C1 随机一致性测试补量化数据。 |

---

## 下一步

**Task 031: 分层上下文与长程架构**
- 引入 Arc/Volume/PermanentScene/OpenThread 四层上下文
- 解决 50 章尺度上的信息遗忘问题
