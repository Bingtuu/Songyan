# Task 028: Punch Engine — 刺激点控制（已完成）

> **Phase**: Phase 1
> **优先级**: P0
> **依赖**: Task 027（基线固化）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

- [x] 新增数据模型：`PunchPoint`、`EmotionArcItem`、`PunchCheck`
- [x] 扩展 `CreativeBrief` 支持 `punch_points` 和 `emotion_arc`
- [x] DB Schema 更新：`creative_briefs` 表新增 `punch_points` / `emotion_arc` 列（TEXT，JSON 序列化）
- [x] DB Migration：`ALTER TABLE` 幂等兼容逻辑（`migrations.py`）
- [x] `CreativeBriefRepository` 读写新字段（JSON 序列化/反序列化）
- [x] CreativeDirector Prompt 条件渲染：`punch_engine_enabled=True` 时要求规划刺激点
- [x] CreativeDirector 解析 & 验证 `punch_points` / `emotion_arc`
- [x] Writer Prompt 条件渲染：刺激点执行清单 + 情绪曲线 + 感官写作规则
- [x] Writer 注入 `punch_points` / `emotion_arc` 变量到 prompt
- [x] RuleAuditor 新增刺激度检查（`_check_punch_points`）
- [x] RuleAuditor `overall_score` 和 `summary` 考虑 `punch_check` 结果
- [x] `rule_auditor_node` 从 `creative_brief` 传入 `punch_points`
- [x] 新增 `creative_modes/webnovel_intense.json`（Punch Engine 实验沙盒）
- [x] 测试：43 passed

---

## 关键决策

### 条件渲染策略
`punch_engine_enabled` 字段控制 Prompt 中刺激点区块的显示。`literary` 和 `webnovel` 模式默认 `False`，`webnovel_intense` 模式默认 `True`。这样保证旧模式行为不变，新模式激活 Punch Engine。

### PunchCheck 纯代码检测
刺激点密度和情绪转折的检查放在 RuleAuditor（纯代码层），不依赖 LLM。检测逻辑：统计 `punch_points` 数量和章节字数（≥1/章），统计 `emotion_arc` 变化点和字数（≥1/1500字）。检测耗时 < 200ms。

---

## 基线验证

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| 刺激点密度 | ≥ 1/章 | `PunchCheck.punch_density_ok` |
| 情绪转折 | ≥ 1/1500字 | `PunchCheck.emotion_switch_ok` |

> ⚠️ **遗留风险**：Punch Engine 自动评估脚本（刺激点密度/情绪转折量化）标记为 A3 验证项，待 Task 034 补齐。

---

## 交付物

- `src/songyan/models/creative_brief.py` — `PunchPoint` / `EmotionArcItem` / `PunchCheck`
- `src/songyan/agents/creative_director.py` — 刺激点规划注入
- `src/songyan/agents/writer.py` — 刺激点执行清单渲染
- `src/songyan/agents/rule_auditor.py` — `_check_punch_points`
- `src/songyan/db/repository.py` — `CreativeBriefRepository` 新字段
- `src/songyan/db/migrations.py` — `creative_briefs` 表迁移
- `creative_modes/webnovel_intense.json` — 实验沙盒配置

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| 自动评估未跑 | 中 | Punch 密度/情绪转折的量化指标尚未在真实章节上验证 |
| 10 章情绪全部 negative-dominant | 中 | 基线报告显示情绪曲线缺乏多样性，Phase 5 Genre 框架需补充 `emotion_arc_library` |

---

## 下一步

**Task 029: Human-in-the-Loop 增强**
- 将僵化的人工确认升级为灵活的深度协作接口
- 支持 `inject` 决策路径和人类指令注入
