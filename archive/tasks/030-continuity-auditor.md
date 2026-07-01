# Task 030: ContinuityAuditor — 跨章一致性引擎

> **Phase**: Phase 3
> **优先级**: P1
> **依赖**: Task 029（HITL 增强）已完成
> **核心目标**: orphaned settings = 0, forgotten items = 0, character state mismatch = 0

---

## Goal

消除跨章断点，自动发现设定/道具/角色的不一致。在 Settlement Extractor 提取时建立追踪数据，每 3 章自动审计一次。

## In Scope

- [x] 新增 4 个 DB 表：`setting_tracking`、`inventory_tracker`、`location_tracker`、`continuity_reports`
- [x] 新增 Continuity 模型：`ContinuityReport`、`OrphanedSetting`、`ForgottenItem`、`StateMismatch`、`OverdueForeshadowing`
- [x] 新增 Repositories：`SettingTrackingRepository`、`InventoryTrackerRepository`、`LocationTrackerRepository`、`ContinuityReportRepository`
- [x] Settlement Extractor 增强：
  - 更新 `setting_tracking`（新设定插入，已有设定更新 `last_mentioned_chapter`）
  - 从 `character_updates` 推断 inventory/location 变化
  - 自动更新 foreshadowing status（planted → due → overdue）
- [x] 新增 `ContinuityAuditor` Agent：
  - `_find_orphaned_settings`：last_mentioned_chapter 超过 3 章
  - `_find_forgotten_items`：last_used_chapter 超过 3 章
  - `_find_overdue_foreshadowings`：expected_resolve_chapter 已过
  - `_compute_health_score`：0-10 健康评分
- [x] Phase2Graph 集成：每完成 3 章自动运行 ContinuityAuditor，健康分 < 7.0 记录警告
- [x] 测试全部通过

## Out of Scope

- `_find_state_mismatches` 暂时返回空列表（`character_states` 表缺少 `chapter_number` 索引，后续增强）
- ContinuityAuditor 发现问题时不阻塞流水线（Phase 3 MVP 策略）
- 不自动注入修复指令到 CreativeBrief（Phase 4 考虑）

## 回滚策略

- 所有新增表通过 `IF NOT EXISTS` 创建
- `apply_settlement()` 的 tracking 更新在主事务外，失败不影响 settlement
- ContinuityAuditor 在 try/except 中调用，失败不阻塞流水线
- 所有新模型有默认值

## 验收标准

- [x] `pytest tests/` 全部通过
- [x] DB schema 初始化包含 4 个新表
- [x] `ContinuityAuditor` 可实例化并运行 audit
- [x] Settlement Extractor 更新 tracking 表不破坏现有测试

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 3 详细设计
