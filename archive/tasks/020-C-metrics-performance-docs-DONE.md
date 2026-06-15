# Task 020-C 交接报告：验收指标收集 + 性能测试 + 文档收尾

> **Phase**: Phase 4 — 评测与优化
> **状态**: ✅ 完成
> **日期**: 2026-05-27
> **测试增量**: +8 单元/集成测试 + 2 性能测试（641 → 643 total）

---

## 做了什么

在 020-B 的评测 runner 基础上实现了 10 项验收指标的自动计算逻辑，完成 mock 模式下的性能基准测试，更新项目文档标记 Phase 4 完成。

### 新增文件

| 文件 | 说明 |
|------|------|
| `evals/metrics.py` | `MetricsCollector` 类，实现 10 项验收指标计算 |
| `tests/test_eval_runner.py`（追加） | 8 个指标单元测试 + 2 个性能测试 + 1 个集成断言 |

### 10 项验收指标

| 指标键 | 计算逻辑 | 目标值 |
|--------|----------|--------|
| `pipeline_success` | 流程到达 done = 1 | 1 |
| `hard_errors` | critical world_consistency issue 数量 | 0 |
| `ai_tell_count` | `rule_audit.ai_tells_count` | < 2 |
| `fatigue_word_count` | `rule_audit.fatigue_words_count` | < 3 |
| `hook_opening_pass` | `has_opening_hook` 或 `narrative_hook >= 7` | 1 |
| `hook_closing_pass` | `has_ending_hook` 或 `narrative_hook >= 7` | 1 |
| `settlement_field_accuracy` | `old_value == db_current_value` 的比例 | > 0.9 |
| `setting_key_accuracy` | `setting_key` 唯一且 `source_quote in content` 的比例 | > 0.9 |
| `conceptual_idling_count` | `observation_type == "conceptual_idling"` 的数量 | 0 |
| `revision_new_issues` | 第 2 轮新 critical/major issue 数量 | 0 |

### 性能基准

| 测试项 | 目标 | 标记 |
|--------|------|------|
| 单章完整闭环（mock） | < 5000 ms | `@pytest.mark.performance` |
| resume + settlement（mock） | < 1000 ms | `@pytest.mark.performance` |

### 文档更新

- `docs/STATUS.md`：Phase 4 标记为已完成，追加 020-B / 020-C 到已完成列表
- `README.md`：更新项目状态为 "22/22 Task，643 个测试全部通过"，追加 Phase 4 行、快速开始命令、验证命令

---

## 验证命令

```bash
# 指标单元测试 + 集成断言
pytest tests/test_eval_runner.py -v
# Expected: 15 passed

# 不含性能测试的常规 CI
pytest -m "not performance" -q
# Expected: 641 passed

# 含性能测试
pytest -m "performance" -v
# Expected: 2 passed
```

---

## 已知限制

- mock 模式下部分指标恒成立（如 hard_errors = 0），重点验证**计算逻辑正确**
- 真实 LLM 评测阶段才是指标达标的最终验证
- settlement_field_accuracy 需要 DB IO，同步 collect() 返回 None，需使用 collect_async()

---

## 下游依赖

- V1.0 真实题材评测阶段（手动调用真实 LLM 跑种子项目）
