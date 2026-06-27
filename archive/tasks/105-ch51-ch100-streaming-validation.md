# Task 105: Ch51-Ch100 流式验证 + 决策门 DG-1

> **Phase**: V5.0 Context Diet 2.0 — 验证阶段
> **优先级**: P0
> **依赖**: Task 104（BudgetHardCeiling 完成）
> **预计工作量**: 3-4 天

---

## Goal

全自动运行 Ch51-Ch100，流式收集指标，自动生成验证报告，触发决策门 DG-1。

---

## Context

### 验证方式

**不人工写报告**，代码自动收集：

```python
# 每章 accept 后自动写入 chapter_metrics 表
metrics = {
    "chapter_number": ch,
    "word_count_ratio": actual / target,
    "budget_used": ctx.budget_used,
    "character_states_loaded": len(ctx.character_states),
    "soft_refs_loaded": len(ctx.soft_references),
    "context_pressure": ctx.context_pressure,
    "revision_rounds": revision_count,
    "quality_gate_passed": qg_passed,
    "context_emergency": emergency_triggered,
    "content_preservation_ratio": preservation_ratio,
}
```

### 报告生成

跑完后一条命令生成：

```bash
python -m songyan eval --project proj-xxx --chapters 51-100 --report
```

输出：
```
Ch51-Ch100 流式验证报告
========================
达标率: 74% (37/50)
budget_used 均值: 0.91
budget_used > 1.0 占比: 12%
character_states 均值: 5.2
soft_refs 均值: 4.1
context_emergency 次数: 3
revision 均值: 1.3
质量门通过率: 96%
```

---

## In Scope

- [ ] **`chapter_metrics` 表**: 存储每章的流式指标
- [ ] **自动收集逻辑**: 在 accept 路径中插入 metrics 记录
- [ ] **报告生成器**: `eval --report` 命令，输出 markdown 报告
- [ ] **决策门 DG-1**:
  - 达标率 ≥ 75% → 进入 V5.1（Ch101-Ch150）
  - 达标率 < 75% → 启动 V5.0 修复（Task 108-109：活跃信息池控制）
- [ ] **自动熔断**: 连续 3 章达标率 < 60% 或连续 3 章 emergency → 自动暂停

## Out of Scope

- 不修改 Writer/Auditor 逻辑（纯监控）
- 不人工介入（除非自动熔断触发）
- 不做 Prompt 调优（属于 V5.1+）

---

## 验收标准

| 指标 | 目标 |
|------|------|
| 达标率 | ≥ 75% |
| 字数不足率 (<0.80x) | ≤ 5% |
| 字数超标率 (>1.30x) | ≤ 15% |
| budget_used 均值 | ≤ 0.95 |
| budget_used > 1.0 占比 | ≤ 10% |
| 平均 revision 轮数 | ≤ 1.5 |
| context_emergency 次数 | ≤ 5 |
| 报告生成 | 一键生成，无需人工整理 |

---

## 决策门 DG-1

```
Ch51-Ch100 验证完成
        │
        ▼
   达标率 ≥ 75%?
   ┌────┴────┐
   ▼         ▼
   是        否
   │         │
   ▼         ▼
 推进      启动 Task 108-109
 V5.1      活跃信息池控制
```

---

## 技术要点

- `chapter_metrics` 与现有 `evals` 基础设施复用，不新建复杂表
- 自动熔断通过 `raise AutoHaltException` 实现，中断生成但保留已生成章节
- 报告包含趋势图（budget_used 随章节变化、达标率分布）

---

## 风险

- **Ch80-Ch100 活跃信息池失控**: 中期是伏笔密集区，可能超标
- **缓解**: 自动熔断 + ContextEmergency 兜底；超标不致命，不达标才致命
