# Task 028: Punch Engine — 刺激点控制

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 027（基线固化）
> **核心目标**: 每章刺激点密度 ≥ 1，每 1500 字情绪转折 ≥ 1

---

## Goal

解决"节奏太慢，缺乏爆炸点"的问题。通过 Punch Engine 在 CreativeDirector 阶段规划刺激点，在 Writer 阶段注入感官写作指令，在 RuleAuditor 阶段验证刺激度指标。

## In Scope

- [x] 新增 `PunchPoint` / `EmotionArcItem` / `PunchCheck` 数据模型
- [x] 扩展 `CreativeBrief` 支持 `punch_points` 和 `emotion_arc`
- [x] DB Schema 更新：`creative_briefs` 表新增 `punch_points` / `emotion_arc` 列
- [x] DB Migration：ALTER TABLE 幂等兼容逻辑
- [x] `CreativeBriefRepository` 读写新字段
- [x] CreativeDirector Prompt 条件渲染：`punch_engine_enabled` 时要求规划刺激点
- [x] CreativeDirector 解析 & 验证 `punch_points` / `emotion_arc`
- [x] Writer Prompt 条件渲染：刺激点执行清单 + 情绪曲线 + 感官写作规则
- [x] Writer 注入 `punch_points` / `emotion_arc` 变量
- [x] RuleAuditor 新增刺激度检查（`_check_punch_points`）
- [x] RuleAuditor `overall_score` 和 `summary` 考虑 punch_check
- [x] `rule_auditor_node` 从 `creative_brief` 传入 `punch_points`
- [x] 测试全部通过

## Out of Scope

- 不修改 LLMAuditor / LiteraryAuditor（Phase 1 聚焦规则层）
- 不生成新章节验证（Phase 1 完成后统一验证）
- 不修改 DB schema 其他表

## 回滚策略

- `literary` / `webnovel` 模式：`punch_engine_enabled=False`，prompt 中不渲染刺激点区块
- `CreativeBrief.punch_points` 默认为空列表，不影响旧代码
- `RuleAuditResult.punch_check` 有默认值，不影响旧代码
- DB ALTER TABLE 幂等

## 验收标准

- [x] `pytest tests/` 全部通过
- [x] `webnovel_intense` 模式加载无报错
- [x] `literary` / `webnovel` 模式行为不变
- [x] CreativeDirector 在 `webnovel_intense` 模式下输出包含 `punch_points` 和 `emotion_arc`
- [x] Writer prompt 在 `webnovel_intense` 模式下包含刺激点执行清单
- [x] RuleAuditor 在有 `punch_points` 时进行刺激度检查

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 1 详细设计
