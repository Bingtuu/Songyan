# Task 116: Best-Version 质量选择策略复核与修复

> **Phase**: V5.0 Phase 4 — DG-2 条件通过收口
> **优先级**: P1
> **依赖**: Task 114c 完成；Task 115 完成或确认不影响版本选择
> **预计工作量**: 1-2 天

---

## Goal

复核 Task 114c 中 Ch147、Ch148 暴露的 best-version 质量选择风险，确保 rewrite fallback、revision rebound 和 QG 收敛失败路径不会让低质量版本覆盖更高质量的 QG 合格 best version。

## Context

Task 114c 已修复并验证过多项版本选择相关缺陷：

- rewrite 结构失败时优先回滚到 QG 合格 best version。
- 没有 best 时回滚到 rewrite 前 active version。
- best-version rollback 后清理旧失败状态，避免误跳过 settlement。
- human gate 保持已判定的 `_quality_gate_passed=True`。

但 Task 114c DONE 仍记录 P1 风险：Ch147、Ch148 曾出现 rewrite fallback 接受低于早先 best score 的版本。最终 JSONL 仍显示 QG 通过且 settlement/summary 成功，但需要确认质量选择策略没有偏向“最后一次 rewrite 结果”而牺牲更优版本。

## In Scope（必须完成）

- [ ] 复盘 Ch147、Ch148 的全部候选版本、score card、QG 状态和 head 切换顺序。
- [ ] 明确 best version 的选择规则和 tie-breaker。
- [ ] 修复低分 fallback 覆盖高分 QG 合格 best 的路径。
- [ ] 确保 abandoned、draft、QG failed 版本不能作为 settlement 前最终 best。
- [ ] 补充 regression tests，覆盖 rewrite fallback、revision rebound、QG best rollback。
- [ ] 复跑 Ch147、Ch148 或最小风险窗口。

## Out of Scope（明确不做）

- 不调整评分模型权重。
- 不放宽 QG 阈值。
- 不修改 Writer 生成策略。
- 不处理 ContextEmergency，该事项归 Task 115。
- 不重跑 Ch111-Ch150 全量窗口，除非 Task 117 要求。

## 实现方案

### 1. 候选版本审计

对 Ch147、Ch148 分别建立候选版本表：

| version_id | version_type | status | overall | QG | source | 是否可作为 best |
|------------|--------------|--------|---------|----|--------|----------------|

审计来源包括：

- `chapter_versions`
- `chapter_heads`
- `review_reports`
- `score cards`
- `logs/chapter_runs/*.jsonl`
- 相关 stdout/stderr

### 2. 版本选择规则固化

建议最终规则：

1. 只有 QG 通过版本可作为 settlement 前 best。
2. `abandoned` 版本永远不可作为最终 head。
3. rewrite fallback 只在没有 QG 合格 best 时使用。
4. 若存在多个 QG 合格版本，优先选择 overall 更高者。
5. overall 相同或缺失时，优先选择更新且结构完整的版本。
6. 状态字段必须同步：`current_version_id`、`_best_version_id`、`_score_card`、`_quality_gate_passed` 指向同一最终候选。

### 3. 代码关注点

重点检查：

- `src/songyan/workflows/_nodes.py`
  - `rewrite_node`
  - `review_merger_node`
  - `human_gate_node`
  - quality gate 状态字段
- `src/songyan/workflows/review_merger.py`
- `src/songyan/workflows/_run_logger.py`
- 与 best version 读取相关的 repository/helper

### 4. 最小修复路径

- 抽出或收敛现有 best 选择逻辑，避免多个节点各自判断。
- 在 rewrite 结构失败、revision rebound、QG 收敛失败三条路径中复用同一选择函数。
- 在选择完成后统一清理旧失败状态，防止高分 best 被旧状态阻断 settlement。

## 接口契约

```python
async def select_best_settlement_candidate(
    *,
    project_id: str,
    chapter_number: int,
    current_version_id: str | None,
) -> str | None:
    """选择可进入 settlement 的最佳 QG 合格版本."""
    ...
```

如果项目已有等价 helper，应优先复用并补充测试，不强制新增该接口。

## 数据模型

不新增持久化模型。测试中可使用轻量结构表达候选版本：

```python
class VersionCandidate(BaseModel):
    version_id: str
    status: str
    overall_score: float | None
    quality_gate_passed: bool
    structure_valid: bool = True
```

## 执行流程

1. **现场审计**
   - 导出 Ch147、Ch148 候选版本与 score card。
   - 还原 head 变化和 fallback 路径。

2. **规则确认**
   - 将“可作为 best”的条件写入任务记录。
   - 明确哪些版本必须被排除。

3. **代码修复**
   - 收敛 best candidate 选择逻辑。
   - 修复 rewrite fallback 覆盖高分 best 的路径。
   - 确保状态字段一致。

4. **测试补齐**
   - 构造高分 QG best + 低分 rewrite fallback。
   - 构造 revision rebound 后回滚 best。
   - 构造无 best 时 fallback 到 active version。

5. **业务回放**
   - 复跑 Ch147、Ch148。
   - 必要时复跑 Ch146-Ch148 或 Ch147-Ch150。

6. **文档收口**
   - 生成 `tasks/116-best-version-quality-selection-fix-DONE.md`。
   - 更新 V5 状态入口。

## 测试要求

### Layer 1: 选择规则测试

- [ ] QG failed 高分版本不能压过 QG passed 低分版本。
- [ ] QG passed 高分 best 不能被低分 rewrite fallback 覆盖。
- [ ] abandoned version 不能成为最终 head。
- [ ] 无 QG passed best 时，可按契约 fallback 到 active version 并进入人审或阻断。

### Layer 2: 节点状态测试

- [ ] `rewrite_node` 结构失败后回滚到正确 best。
- [ ] `review_merger_node` rollback 后清理旧失败状态。
- [ ] `human_gate_node` 不覆盖前序已通过的 QG 状态。

### Layer 3: 业务回放

- [ ] Ch147 完成 `accept + settlement + summary`，最终版本为可解释 best。
- [ ] Ch148 完成 `accept + settlement + summary`，最终版本为可解释 best。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| Ch147/Ch148 版本选择 | 最终 accepted 版本可追溯且符合 best 规则 |
| QG 合格限制 | settlement 前 best 100% 来自 QG passed 版本 |
| abandoned 防护 | 0 个 abandoned version 成为 final head |
| fallback 行为 | 低分 rewrite fallback 不覆盖高分 QG best |
| 测试 | 聚焦测试通过；`ruff check src/ tests/` 通过 |
| 业务链路 | Ch147/Ch148 回放均完成 `accept + settlement + summary` |

## 风险与应对

| 风险 | 应对 |
|------|------|
| 选择规则收紧导致更多章节进入人审 | 先在 Ch147/Ch148 聚焦验证，再进入 Task 117 小窗口复验 |
| 多节点状态字段再次分叉 | 使用统一 helper 或统一状态写入函数 |
| 历史数据难以还原 | 以 JSONL、DB 和 stdout/stderr 三方交叉确认 |

## 参考文档

- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `archive/v5/reports/report-task114c-dg2-ch111-ch150.md`
- `tasks/113-ch101-convergence-settlement-blocker-fix-DONE.md`
- `tasks/114b2-qg-convergence-settlement-window-DONE.md`
