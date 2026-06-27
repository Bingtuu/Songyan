# Task 078: 伏笔生命周期管理 + ContinuityAuditor 输出预算化

> **Phase**: V3.1 100章架构改造 — Phase A 止血
> **优先级**: P0
> **依赖**: 077（推荐先完成 setting 库，因两者的过滤逻辑在 ContextManager 中交汇）
> **预计工作量**: 中-大（2-4 天）

---

## Goal

两件事：一是 foreshadowing 自动归档 + human_marks 时间窗口过滤；二是在 ContinuityAuditor 写入约束之前增加**输出预算化**——当已累积约束超过阈值时停止写入新约束，阻断正反馈回路。

## Context

V3.1 验证报告问题 4.2.1（ContinuityAuditor 约束爆炸）：Ch48 时 `constraints_written=236`，health score=0.0。

这些约束全部写入 human_marks 表，下一章作为 hard_constraints 加载到上下文。DB 中 foreshadowings 达 49 条，未解决 human_marks 达 **73 条**。

**正反馈回路**：
```
ContinuityAuditor 发现问题 → 写入 human_marks
  → 下一章上下文更大 → Writer 在更拥挤的 prompt 中更容易遗漏
    → ContinuityAuditor 发现更多问题 → 写入更多 human_marks（循环）
```

078 的前半部分（归档 + 窗口过滤）切断这个回路的一个路径。后半部分（输出预算化）切断另一个路径——当约束已经过多时，**审计器自己停下来**。

## In Scope

### 1. Foreshadowing 自动归档

- [ ] `ForeshadowingRepository` 新增 `archive_overdue()`：`expected_resolution_chapter × 1.2 < current_chapter && status='active'` → 改为 `archived`
- [ ] `SettlementExtractor` 的 accept 后路径中调用归档（失败不阻塞）
- [ ] `ContinuityAuditor._find_overdue_foreshadowings()` 排除已归档

### 2. Human_marks 时间窗口过滤

- [ ] `assemble_context_package()` 中修改 marks 过滤：只保留最近 3 章写入的 + priority=P0 的 + 所有 previously unresolved 的
- [ ] 其余 marks 不进入 `ContextPackage.hard_constraints`
- [ ] `total_foreshadowings_count`, `total_human_marks_count`, `loaded_human_marks_count` 监控字段

### 3. ContinuityAuditor 输出预算化（新增架构级加固）

- [ ] 在 `ContinuityAuditor.write_constraints()` 中增加**输出预算**：
  - 检查当前 chapter 已有的 constraint 数（`self.report_repo.count_by_chapter()` 或类似）
  - 若当前 chapter 已有 ≥ 20 条 unresolved constraints，**跳过本次写入**
  - 记录跳过的约束数量到 structlog（`continuity_auditor.constraints_deferred=N`）
  - 将跳过的约束 ID 列表写入 Phase1State.`_deferred_constraints: list[str]`
- [ ] 在 `ContinuityAuditor._generate_constraints()` 中增加**生成预算**：
  - 若已生成的 constraint 数 ≥ 30，停止生成新的，记录截断日志
  - 即使还有更多问题未发现，也不生成更多约束
- [ ] 在 `_compute_health_score()` 中增加**容忍窗口**：
  - 章节数 ≤ 30：score = 10 - issues × factor（当前逻辑，严格）
  - 章节数 > 30：score = 10 - issues × factor × 0.5（放宽到一半，承认长期运行中必然有遗留问题）
  - 确保 score 不低于 2.0（即使是 Ch100，也不应该 score=0）
- [ ] Phase1State 新增 `_deferred_constraints: list[str]` + `_continuity_budget_exhausted: bool`

## Out of Scope

- 不修改 ContinuityAuditor 的 audit 逻辑（扫描和发现照常进行，只是写入受控）
- 不做 human_marks 自动解决（需要人工判断）
- 不修改已有 DB 数据（新增归档方法在运行时自动处理）

## 接口契约

```python
class ForeshadowingRepository:
    async def archive_overdue(self, project_id: str, current_chapter: int) -> int:
        """归档预期解析章节已逾期 20% 以上的活跃伏笔."""

class ContinuityAuditor:
    MAX_CONSTRAINTS_PER_CHAPTER = 20   # 每章写入上限
    MAX_CONSTRAINTS_GENERATED = 30     # 单次生成上限

    async def write_constraints(self, report: ContinuityReport) -> int:
        """写入约束，受输出预算限制."""

    def _compute_health_score(self, ..., chapter_number: int) -> float:
        """放宽系数。chapter_number > 30 时宽松因子 0.5，最低 2.0."""
```

## 数据模型

```python
# Phase1State 新增
_deferred_constraints: list[str] = []
_continuity_budget_exhausted: bool = False
```

## 测试要求

- [ ] archive_overdue 归档条件正确（20% 容忍窗口验证）
- [ ] 归档后 list_active_by_project 不返回已归档记录
- [ ] human_marks 时间窗口过滤：3 章外的 marks 被排除
- [ ] ContinuityAuditor 输出预算：已有 20 条未解决约束 → 跳过写入
- [ ] ContinuityAuditor 生成预算：已生成 30 条 → 停止生成
- [ ] health_score 放宽后：Ch50 时 score ≥ 2.0（Ch48 当前是 0.0）
- [ ] pytest tests/ -x -q 通过

## 验收标准

- [ ] Ch50 模拟：loaded_human_marks_count ≤ 20（当前 28）
- [ ] Ch50 模拟：continuity health score ≥ 2.0（当前 0.0）
- [ ] foreshadowing 归档不影响其他模块
- [ ] _deferred_constraints 正确记录了被执行预算跳过的约束
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 DONE 交接报告 + 更新 STATUS.md
