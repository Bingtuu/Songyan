# Task 101: TemporalCompressor — 时间分层压缩

> **Phase**: V5.0 Context Diet 2.0 — 核心组件 1/4
> **优先级**: P0
> **依赖**: Task 100c（上下文压力优化完成）
> **预计工作量**: 2-3 天

---

## Goal

把 `ContextPackage` 中的 `previous_summaries` 从"平铺加载最近 N 章"改为"金字塔分层结构"，让历史信息的 token 占用从 O(n) 降到 O(log n)。

---

## Context

### 当前问题

`assemble_context_package` 中的 `_build_recent_summaries` 加载最近 10 章的逐章摘要：
- Ch50: 10 章 × ~1.5K = 15K tokens
- Ch100: 仍然是 10 章 × ~1.5K = 15K tokens（但历史累积到 100 章）
- 历史信息没有被压缩，只是被裁剪

### 目标结构

```
Ch100 加载时：
├── 最近 5 章（Ch95-99）：逐章完整摘要 ────── 40% token
├── 当前弧（Ch91-94）：弧级压缩摘要（500字）── 20% token
├── 上一弧（Ch81-90）：卷内引用摘要（300字）── 15% token
├── 历史卷（Ch1-80）：卷级主题摘要（200字）── 10% token
└── 硬约束 ───────────────────────────────── 15% token
```

---

## In Scope

- [ ] **arc_summaries 表**: 每 10 章自动生成弧摘要（复用现有 SummaryWriter）
- [ ] **volume_summaries 表**: 每 50 章自动生成卷摘要
- [ ] **`_build_pyramid_summaries`**: 替换 `_build_recent_summaries`，按分层规则组装
- [ ] **分层规则**: 
  - 最近 5 章: 逐章完整摘要
  - Ch6-10 前: 弧摘要（如果存在）
  - Ch11-50 前: 卷摘要（如果存在）
  - Ch50+ 前: 卷主题摘要
- [ ] **单元测试**: 分层结构正确；token 占用 < 平铺结构的 60%
- [ ] **Ch51 单章验证**: 确认 Writer 拿到的是金字塔而非平铺

## Out of Scope

- 不修改 SummaryWriter 的生成逻辑（复用现有）
- 不删除 `_build_recent_summaries`（保留为兼容路径，配置开关切换）
- 不修改 Writer Prompt

---

## 验收标准

| 指标 | 目标 |
|------|------|
| `previous_summaries` token 数（Ch51） | < 平铺结构的 60% |
| 弧摘要生成成功率 | 100%（每 10 章边界触发） |
| 卷摘要生成成功率 | 100%（每 50 章边界触发） |
| Ch51 单章达标率 | ≥ 75% |
| 测试通过 | pytest 新增测试全部通过 |

---

## 技术要点

- 复用 `summary_writer.py` 生成弧/卷摘要
- 弧摘要存储到 `arc_summaries` 表（chapter_start, chapter_end, summary, key_events, character_states_snapshot）
- 卷摘要存储到 `volume_summaries` 表（同上，粒度更大）
- `_build_pyramid_summaries` 查询逻辑：先查最近 5 章 → 再查当前弧摘要 → 再查上一卷摘要
- 若某层摘要不存在（如还没到 10 章边界），退化为逐章摘要

---

## 风险

- **弧摘要质量差**: 如果 SummaryWriter 生成的弧摘要丢失关键信息，Writer 会"失忆"
- **缓解**: 弧摘要必须包含 `key_events` 列表（至少 3 个），由 ContinuityAuditor 校验完整性
