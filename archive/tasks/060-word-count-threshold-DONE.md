# Task 060: RuleAuditor 字数阈值验证与收紧 — DONE

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-05
> **实际工作量**: ~30 分钟

---

## 验证结论

### 阈值现状

- **阈值判断位置**: `src/songyan/workflows/review_merger.py::_convert_rule_to_issues()`
- **当前阈值**: `excess_ratio >= 1.20`（即 >= 120%）
- **058c 实现状态**: ✅ 已正确实现，阈值已从 130% 收紧到 120%

### 修复内容

1. **边界条件修复**: `> 1.2` → `>= 1.2`
   - 原代码使用 `> 1.2`，导致恰好 120% 时不触发 violation
   - 修复后 120% 恰好值正确触发

2. **浮点精度修复**: `int((excess_ratio - 1) * 100)` → `round((excess_ratio - 1) * 100)`
   - 原代码因浮点精度 `(1.2 - 1) * 100 = 19.999...` 导致 `int()` 截断为 19%
   - 修复后正确显示为 20%

### 新增测试

| 测试文件 | 测试类 | 测试数 | 覆盖场景 |
|----------|--------|--------|----------|
| `tests/test_rule_auditor.py` | `TestWordCountRatio` | 4 | ratio 计算正确性、零 target 不崩溃 |
| `tests/test_review_merger.py` | `TestWordCountThreshold` | 5 | 1.19 不触发、1.20 触发、1.30 触发、零 target、合并正确性 |

---

## 验收标准

- [x] `pytest tests/test_rule_auditor.py tests/test_review_merger.py -v` 全部通过（42/42）
- [x] 代码审查确认阈值从 130% → 120%（ReviewMerger 中 `>= 1.2`）
- [x] 不违反 AGENTS.md 规则
- [x] 更新了 `docs/STATUS.md`
- [x] 生成了本交接文件

---

## 参考

- `src/songyan/workflows/review_merger.py` — 阈值判断位置
- `src/songyan/agents/rule_auditor.py` — `word_count_ratio` 计算位置
