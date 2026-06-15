# Task 086: 动态预算 + Genre 规则分组加载 — 交接报告

> **状态**: ✅ 已完成  
> **完成日期**: 2026-06-07  
> **提交**: `TBD`  
> **测试**: 13 passed, 0 failed  

---

## 变更摘要

### 1. 动态预算公式 (`src/songyan/agents/context_manager/_assemblers.py`)

将 `_dynamic_budget` 从分段函数改为线性增长公式：

```python
DEFAULT_BASE_BUDGET: int = 8000
BUDGET_INCREMENT_PER_CHAPTER: int = 80

def _dynamic_budget(chapter_number: int, base_budget: int = DEFAULT_BASE_BUDGET) -> int:
    return base_budget + chapter_number * BUDGET_INCREMENT_PER_CHAPTER
```

验证值：
| 章节 | 预算 |
|------|------|
| Ch1 | 8080 |
| Ch50 | 12000 |
| Ch70 | 13600 |
| Ch100 | 16000 |

旧的分段逻辑（Ch1-10=base, Ch11-50=1.2x, Ch51+=base）被替换，预算随章节线性增长，与数据增长率匹配。

### 2. Genre 规则分组加载

**`GenreProfile` 模型** (`src/songyan/models/genre.py`)：
- 新增 `writer_rules_by_type: dict[str, list[str]]` 字段
- 向后兼容：旧配置（无该字段）回退到 `writer_rules` 全量加载

**`_build_genre_rules`** (`src/songyan/agents/context_manager/_assemblers.py`)：
- 按 `chapter_goal.chapter_type` 查找 `writer_rules_by_type` 中的对应分组
- 大小写不敏感匹配（`.lower()`）
- 未匹配或分组为空时回退到 `writer_rules`

### 3. 常量注释更新

`src/songyan/agents/context_manager/__init__.py`：
- `DEFAULT_BUDGET_TOKENS` 注释更新，说明其作为动态预算基数的角色

---

## 测试

### 动态预算（7 个测试）
- `test_chapter_1` — 8080
- `test_chapter_50` — 12000
- `test_chapter_70` — 13600
- `test_chapter_100` — 16000
- `test_custom_base_budget` — 自定义基数公式正确
- `test_chapter_0` — 边界值
- `test_constants` — 常量验证

### Genre 分组（6 个测试）
- `test_grouped_rules_loaded` — chapter_type 匹配时加载分组规则
- `test_fallback_to_default_rules` — 未定义类型回退全量
- `test_empty_grouping_uses_default` — 空分组回退全量
- `test_no_chapter_type_uses_default` — 空 chapter_type 回退全量
- `test_case_insensitive_chapter_type` — 大小写不敏感
- `test_backward_compatibility_no_field` — 旧 GenreProfile 向后兼容

---

## 回归测试结果

```
全量: 212 passed, 4 skipped, 1 failed (pre-existing: test_mock_end_to_end)
新增: 13 passed, 0 failed
```

失败测试为 pre-existing，与本次修改无关。

---

## 已知限制

1. **Mode 规则未分组**：Task 086 规格中只要求 Genre 规则分组。CreativeModeProfile 的 `writer_rules` 字段不存在（Mode 规则通过 `revision_policy`、`tolerance` 等结构化字段表达），Mode 分组加载如需实现需后续 Task 定义。

2. **`writer_rules_by_type` 未在现有 genre JSON 中填充**：当前 `genres/*.json` 未添加 `writer_rules_by_type` 字段。V4.0 验证阶段（Task 109+）需要为验证用的 genre 配置添加分组规则。

3. **动态预算的硬断言阈值不变**：`HARD_ENFORCE_THRESHOLD = 1.3` 仍为固定比例。预算增大后，硬断言的绝对阈值也同步增大（Ch100: 16000*1.3=20800）。

---

## 下一步

- **Task 087**: LifecycleScheduler 集成 Phase1Graph（每章 accept 后触发 cleanup，串联 083-086 的所有 archive 方法）
