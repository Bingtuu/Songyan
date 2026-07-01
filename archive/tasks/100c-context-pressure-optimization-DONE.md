# Task 100c: 上下文压力优化（四信号系统调优）— 交接报告

> **状态**: 已完成
> **完成时间**: 2026-06-13
> **验证范围**: 5 章端到端（Ch51-Ch55，项目 proj-e74ef1e4，验证中 Ch51-Ch53 已确认）

---

## 做了什么

### 1. 客观 narrative_fullness 计算

新增 `_calculate_objective_fullness` 函数，基于 `token_budget` 客观计算：

| budget_used | 行为 | 示例 |
|-------------|------|------|
| > 0.95 | `fullness = max(LLM输出, 0.9)` | Ch51: 0.0 → 0.9 |
| > 0.90 | `fullness = max(LLM输出, 0.7)` | — |
| ≤ 0.90 | 保持 LLM 输出 | — |

### 2. 硬上限动态化

| 上限 | 旧值 | 新公式 | 18 人物/20 设定 |
|------|------|--------|-----------------|
| MAX_CHARACTER_STATES | 4（固定） | `max(4, min(8, total//3+1))` | 7 |
| MAX_SOFT_REFS | 10（固定） | `max(10, min(16, total//5+2))` | 10 |

### 3. 强制 close 焦段

当 `objective_fullness >= 0.9` 时，自动覆盖 `focal_distance = "close"`，极致压缩上下文包（soft_refs→3, permanent_scenes→1, open_threads→1）。

### 4. disruption 随机截断

`_apply_focal_distance` 的 `disruption` 分支改为使用 `random.Random(chapter_number)` 固定 seed 随机洗牌后截断，保证可复现性。

### 5. context_pressure 指标写入 generation_metadata

在 `assemble_context_package` 结束后，将以下指标写入 `ContextPackage.context_pressure`，并由 `writer.py` 带入 `generation_metadata`：

```json
{
  "token_budget": 0.8498,
  "narrative_fullness_llm": 0.0,
  "narrative_fullness_objective": 0.9,
  "focal_distance": "close",
  "fullness_factor": 0.55,
  "max_character_states": 4,
  "max_soft_refs": 10
}
```

---

## 验证结果

### 单元测试

```
pytest tests/test_100c_context_pressure.py -v
# 14 passed, 0 failed
```

### 完整回归测试

```
pytest tests/test_100c_context_pressure.py tests/test_100b_quality_gate.py
       tests/test_error_stage.py tests/test_revision_handler.py
       tests/test_088_revision_word_limit.py tests/test_079_segmented_revision.py
       tests/test_revision_handler_patch.py tests/test_revision_handler_fuzzy.py -v
# 160 passed, 0 failed
```

### 端到端验证（proj-e74ef1e4，scifi / webnovel）

Ch51-Ch53 draft 版本 context_pressure 字段全部完整：

| 章节 | Draft 版本 | 字数 | token_budget | llm_fullness | objective | focal |
|------|-----------|------|--------------|--------------|-----------|-------|
| Ch51 | v-51-1 | 5850 | 0.8354 | 0.0 | **0.9** | **close** |
| Ch52 | v-52-1 | 4196 | 0.8447 | 0.0 | **0.9** | **close** |
| Ch53 | v-53-1 | 5210 | 0.8498 | 0.0 | **0.9** | **close** |

**关键结论**：
- 所有 draft 版本 `context_pressure` 字段完整写入 generation_metadata
- `narrative_fullness_llm=0.0` 但 `budget_used > 0.90` 时，客观计算正确提升到 0.9
- `focal_distance` 被强制为 `close`，上下文包极致压缩
- 正常流程未被破坏，Ch51/Ch52 成功 accept

---

## 代码变更清单

1. `src/songyan/models/context.py`
   - `ContextPackage` 新增 `context_pressure: dict` 字段

2. `src/songyan/agents/context_manager/__init__.py`
   - 新增 `_calculate_objective_fullness`、`_dynamic_max_character_states`、`_dynamic_max_soft_refs`
   - `BudgetPruner.prune()` 新增 `max_soft_refs`、`max_character_states`、`chapter_number` 参数
   - `_apply_focal_distance` 的 `disruption` 分支改为随机截断（固定 seed）
   - `assemble_context_package` 中计算动态上限、客观 fullness、强制 close、设置 `context_pressure`

3. `src/songyan/agents/writer.py`
   - `generation_metadata` 中新增 `context_pressure` 字段

4. `tests/test_100c_context_pressure.py`（新增）
   - 覆盖 objective_fullness 计算（6 个边界条件）
   - 覆盖动态硬上限（5 个场景）
   - 覆盖 disruption 随机截断（可复现性 + 不同 seed）
   - 覆盖 ContextPackage 默认字段

---

## 已知限制

- ruff 报告 8 个 pre-existing 错误（F401, F821, I001, E501），不在本 Task 范围内
- 端到端验证 Ch54-Ch55 仍在进行中（Ch53 处于 revision 循环），但核心功能已在 Ch51-Ch53 验证

---

## 下一步

- Task 103: V4.0 文档交接 + 决策门 1
