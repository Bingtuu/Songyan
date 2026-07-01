# Task 115 DONE: ContextEmergency 触发复核与校准

> **Phase**: V5.0 Phase 4 — DG-2 条件通过收口
> **状态**: ✅ 完成
> **完成日期**: 2026-06-20
> **诊断结论**: 合理降级（添加可观测性字段后验证通过）

---

## 结论

Ch115、Ch120 触发的 ContextEmergency 属于**合理降级**，无需修改 emergency 触发逻辑。emergency 在 `budget_used` 略超 1.0 时正确触发（Ch120 日志显示 `before_tokens=17612 > budget=17600`），清空后最终 `budget_used=0.31`。

本次 Task 为改善可观测性，新增 `budget_used_before_emergency` 字段，记录 emergency 触发前的 `budget_used` 值，用于未来区分"合理降级"与"误触发"。

---

## 诊断过程

### 1. 现场复盘

从 Task 114c 有效 run 记录中定位：

| 章节 | run_id | budget_used | char_states | soft_refs | emergency |
|------|--------|-------------|-------------|-----------|-----------|
| Ch114 | run-42aecdd6 | 0.849 | 2 | 3 | false |
| **Ch115** | run-42aecdd6 | **0.268** | **1** | **0** | **true** |
| Ch116 | run-42aecdd6 | 0.837 | 2 | 3 | false |
| Ch119 | run-f5566785 | 0.827 | 2 | 2 | false |
| **Ch120 (重跑)** | run-6e1fdace | **0.311** | **1** | **0** | **true** |

Ch115/Ch120 的 `budget_used` 极低（0.27/0.31），且 `character_states_loaded=1, soft_refs_loaded=0`，符合 emergency 后的裁剪特征。

### 2. 触发链路定位

从 `run-6e1fdace` 日志中找到 `context_emergency_triggered` 记录：

```
before_tokens=17612, budget=17600, budget_used=0.3113
```

触发原因：
- 初始 `before_tokens=17612` 略超 `budget=17600`（差值仅 12 tokens，约 0.007%）
- `budget_used = before_tokens / budget = 17612 / 17600 = 1.0007 > 1.0`
- `_context_emergency` 执行全面清空（soft_references, foreshadowing, character_states 裁剪至仅剩 1 个主角等）
- 清空后 `after_tokens=5479`，最终 `budget_used = 5479 / 17600 = 0.3113`

### 3. 根因分类

| 分类 | 依据 |
|------|------|
| **合理降级** | `before_tokens > budget` 确实超预算，emergency 触发条件 `budget_used > 1.0` 满足 |
| 非误判 | 日志中有明确的 `context_emergency_triggered` 记录 |
| 非采集缺失 | JSONL 中 `context_emergency=true` 正确记录 |
| 可观测性不足 | `budget_used` 字段记录的是裁剪后的值（0.31），而 emergency 触发时是裁剪前的值（1.0007），容易混淆 |

---

## 本次修改

### 新增字段

**`budget_used_before_emergency: float | None`**

记录 ContextEmergency 触发前的 `budget_used` 值（触发时的 `before_tokens / budget`），用于：
- 区分"真超预算触发"与"报告误判"
- 验证 emergency 是否在合理的 `budget_used > 1.0` 条件下触发
- 未来调优 emergency 触发阈值时的数据依据

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/songyan/models/context.py` | `ContextPackage` 和 `ContextSnapshot` 新增 `budget_used_before_emergency` 字段 |
| `src/songyan/agents/context_manager/__init__.py` | `_context_emergency()` 在触发时记录 `budget_used_before_emergency`，日志增加两个 budget 字段 |
| `src/songyan/workflows/_nodes.py` | `_extract_context_metrics()` 和 `_save_context_snapshot()` 传递新字段 |
| `src/songyan/models/run_log.py` | `ChapterRunLog` 新增 `budget_used_before_emergency` 字段 |
| `src/songyan/workflows/_run_logger.py` | `_query_context_metrics()` 和 `build_chapter_run_log()` 传递新字段 |
| `src/songyan/agents/writer.py` | `generation_metadata["context_snapshot"]` 包含新字段 |

### 日志变更

Emergency 触发日志新增两个字段：

```python
logger.warning(
    "context_manager.context_emergency_triggered",
    budget_used_before_emergency=ctx.budget_used_before_emergency,  # 新增
    budget_used_after_emergency=after / budget if budget > 0 else 0.0,  # 新增（原 budget_used）
    ...
)
```

---

## 验证结果

### ruff 检查

```bash
ruff check src/ tests/
All checks passed!
```

### 聚焦测试

```bash
pytest tests/test_context_manager.py tests/test_100c_context_pressure.py -q
91 passed in 15.77s
```

### 全量回归

```bash
pytest tests/ -q
1676 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings
```

### 新字段验证

测试项目 JSONL 输出验证：

```json
{
  "context_emergency": false,
  "budget_used_before_emergency": null,
  ...
}
```

新字段正确写入 JSONL，未触发 emergency 时为 `null`。

---

## DG-2 ContextEmergency 说明

当前 DG-2 要求 `ContextEmergency == 0`，但 Ch115/Ch120 的 emergency 属于**合理降级**：

- 触发条件：`budget_used > 1.0`（`before_tokens > budget`）
- 触发原因：初始组装时 context 略超预算（17612 vs 17600，仅差 12 tokens）
- 降级后状态：角色/设定/伏笔被清空至最小集，Writer 在精简 context 下完成写作
- 最终结果：两章均完成 `accept + settlement + summary`，QG 通过

**建议**：DG-2 可考虑增加"合理降级 emergency 不计入不达标"的豁免条件，或将 `ContextEmergency > 0` 改为 `ContextEmergency 次数` 单独统计，不作为硬门禁。

---

## 已知限制

1. **Windows 长跑进程不稳定**：Task 117 复跑时统一处理
2. **DG-2 emergency 口径**：当前仍计入 Ch115/Ch120 的 emergency，未来可考虑豁免合理降级

---

## 下一步

- **Task 116**: Best-Version 质量选择策略复核（Ch147/Ch148）
- **Task 117**: DG-2 风险章节窗口复验（Ch115/Ch120/Ch147/Ch148）
- **Task 118**: ContinuityAuditor health_low 治理策略
- **Task 119**: 长跑报告入口与 Windows Wrapper 加固
- **Task 120**: V5.0 Final Acceptance Package

---

## 参考文档

- `archive/v5/plans/115-context-emergency-review.md` — Task 115 历史规划稿
- `tasks/114-ch101-ch150-streaming-validation-DONE.md` — Task 114c DONE
- `archive/v5/reports/report-task114c-dg2-ch111-ch150.md` — DG-2 报告
