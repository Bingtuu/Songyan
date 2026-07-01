# Task 060: RuleAuditor 字数阈值验证与收紧

> **Phase**: V3.x Layer 3 — 系统化质量守卫
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 小（~30 分钟）

---

## Goal

验证 058c 新增的 `word_count_ratio` 能否真正触发 violation，确认阈值已从 130% 收紧到 120%，并补充边界条件测试。

## Context

058b 数据揭示了一个矛盾：RuleAuditor 平均得分 0.95（近乎完美），但实际章节有明显字数超标（Ch8: 6,465 字，超标 115%；Ch28: 6,366 字，超标 112%）。

058c 在 `RuleAuditResult` 中新增了 `word_count_ratio` 字段，并在 `run_rule_audit()` 中计算该值。但：

1. **当前阈值不确定**：代码中实际的 violation 阈值可能是 130%（原设定），导致 115% 和 112% 的超标不会被标记。
2. **violation 写入路径未验证**：`word_count_ratio` 被计算后是否被正确传入 `RuleAuditResult.violations` 列表，需要确认。
3. **无边界测试**：阈值边界（如 `word_count_ratio=1.19` vs `=1.20`）没有测试覆盖。

## In Scope（必须完成）

- [ ] 代码审查确认 `word_count_ratio` 的 violation 阈值当前值（130% 或 120%）
- [ ] 如果阈值是 130%，收紧到 120%
- [ ] 确认 `word_count_ratio >= threshold` 时 violation 被正确写入 `RuleAuditResult.violations`
- [ ] 新增参数化测试：`word_count_ratio=1.19` 不触发、`=1.20` 触发、`=1.30` 触发
- [ ] 如果 violation 写入路径有问题则修复

## Out of Scope（明确不做）

- 不改 Writer Prompt 或 LLMAuditor prompt
- 不新增审查维度
- 不调整 fatigue_words 或其他检测规则
- 不做跨章字数趋势分析

## 接口契约

```python
# 修改 run_rule_audit 中字数检测阈值
WORD_COUNT_VIOLATION_THRESHOLD: float = 1.20  # 从 1.30 收紧到 1.20

# 伪代码
if word_count_ratio >= WORD_COUNT_VIOLATION_THRESHOLD:
    violations.append(RuleViolation(
        rule_id="word_count_exceeded",
        severity="major",
        detail=f"字数超标 {word_count_ratio:.0%}，目标 {target_words}，实际 {actual_words}",
        ...
    ))
```

## 数据模型

```python
# 不新增字段，仅验证 RuleAuditResult.violations 包含字数违规
class RuleAuditResult(BaseModel):
    score: float
    violations: list[RuleViolation]
    word_count_ratio: float | None  # 058c 已新增
```

## 测试要求

### Layer 1: 模型测试
- [ ] `RuleAuditResult` 含 `word_count_ratio` 字段且可为 None

### Layer 2: 模块测试
- [ ] `word_count_ratio=1.19` 不产生字数 violation
- [ ] `word_count_ratio=1.20` 产生 1 个字数 violation（severity=major）
- [ ] `word_count_ratio=1.30` 产生 1 个字数 violation
- [ ] `word_count_ratio=None`（无目标字数）不抛异常
- [ ] `word_count_ratio=1.20` 且已有其他 violation 时合并正确

## 验收标准

- [ ] `pytest tests/test_rule_auditor.py -v` 全部通过 + 新增参数化测试通过
- [ ] 代码审查确认阈值从 130% → 120%（或确认已是 120%）
- [ ] 不违反 AGENTS.md 规则（V3.x 适用规则 60-67 代码规范 + Rule 70 不新增功能）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/060-word-count-threshold-DONE.md` 交接文件

## 参考文档

- `src/songyan/agents/rule_auditor.py` — `run_rule_audit()` 实现
- `src/songyan/models/review.py` — `RuleAuditResult` 模型
- `docs/review/v30_layer2_runlog.jsonl` — Ch8 (6465字) / Ch28 (6366字) 的 rule_audit_score