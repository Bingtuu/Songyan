# Task 080: 角色出场窗口 — 只加载当前 Arc 内出场角色 — 交接报告

> **状态**: ✅ 已完成  
> **完成日期**: 2026-06-07  
> **测试**: 6/6 通过  
> **回归**: 1353 passed, 5 预存失败（无新增失败）

---

## 做了什么

### 1. `_build_character_snapshots()` — Arc 出场窗口过滤

**文件**: `src/songyan/agents/context_manager/_assemblers.py`

- 新增参数 `arc_boundaries: list[tuple[int, int]] | None = None` 和 `current_chapter: int = 0`
- 当 `current_chapter > 0` 且 `arc_boundaries` 存在时，启用 arc 窗口模式：
  - 使用 `ArcBoundaryResolver` 确定当前 arc 的章节范围
  - 从 `recent_summaries` 中提取当前 arc 内出场的角色名
  - **Protagonist** 始终保留完整档案（无论是否在 arc 内出场）
  - **Arc 内出场角色** 保留完整档案（所有 fields + importance_score=0.8）
  - **非 arc 角色** 只保留 `character_id`, `name`, `importance_score=0.3`，其余字段为 None/[]
- 无 `arc_boundaries` 时回退到原有行为（基于 `recent_summaries` 的 `characters_appeared` 过滤）

### 2. `workflows/_helpers.py` — 传入 arc 边界信息

**文件**: `src/songyan/workflows/_helpers.py`

- 导入 `ArcBoundaryResolver`
- 从 `project.arc_boundaries` 解析 arc 范围
- 调用 `_assemble(..., arc_boundaries=arc_bounds, current_chapter=chapter_number)`

### 3. `ContextPackage` — 新增监控字段

**文件**: `src/songyan/models/context.py`

- 新增 `character_states_total: int = 0`（DB 中总角色状态数，用于监控）

---

## 验证

### 新增测试

**文件**: `tests/test_080_character_appearance_window.py`（6 tests）

| 测试 | 描述 |
|------|------|
| `test_arc_appeared_gets_full_profile` | arc 内出场角色获得完整档案 |
| `test_non_arc_gets_minimal_profile` | 非 arc 角色只保留 name + importance_score |
| `test_protagonist_always_full` | 主角始终完整，即使不在 arc 内出场 |
| `test_no_arc_boundaries_fallback` | 无 arc_boundaries 时回退到原有行为 |
| `test_arc_boundary_correctly_resolved` | ArcBoundaryResolver 正确解析当前 arc |
| `test_character_states_total_not_in_snapshot` | 监控字段不影响 snapshot 内容 |

### 回归测试

```bash
pytest tests/ -q
# 1353 passed, 5 failed（均为预存失败，无新增）
```

**预存失败（5 个，与 080 无关）**:
1. `tests/evals/test_embedding_benchmark.py::test_mock_end_to_end` — `AssertionError: 0 > 0`
2-4. `tests/test_load_layered_summaries.py::TestBuildRecentPlotSourceType` — truncation length 不匹配
5. `tests/test_writer.py::TestWriteChapter::test_empty_llm_response` — 期望值与实际行为不一致（077c 修改后）

---

## 已知限制

- `character_states_total` 字段已加入 `ContextPackage` 模型，但当前 `_assemble()` 函数中尚未实际写入该值（需要 DB 层提供 `COUNT(*)` 查询）。此字段为监控预留，不影响功能。
- Arc 窗口仅作用于 `_build_character_snapshots()` 的数据加载阶段；BudgetPruner 的 `_prune_character_states()` 仍会在 token 超标时进一步裁剪。
- 当角色池扩大到 40+ 人时，非 arc 角色的精简档案仍会被 BudgetPruner 视为可被丢弃的条目（importance_score=0.3），因此整体 character_states 分区占用将保持低位。

---

## 修改文件清单

| 文件 | 变更 |
|------|------|
| `src/songyan/agents/context_manager/_assemblers.py` | `_build_character_snapshots()` 增加 arc 窗口过滤逻辑 |
| `src/songyan/workflows/_helpers.py` | 传入 `arc_boundaries` 和 `current_chapter` |
| `src/songyan/models/context.py` | `ContextPackage` 新增 `character_states_total` |
| `tests/test_080_character_appearance_window.py` | 新增 6 个单元测试 |
| `docs/STATUS.md` | 更新 Task 080 状态为 ✅ 已完成 |

---

## 下一步

- **Task 081**: Ch51-Ch70 真实 LLM 验证，验证 Phase A+B 综合效果（字数截断 + BudgetPruner 硬断言 + arc 角色窗口）
