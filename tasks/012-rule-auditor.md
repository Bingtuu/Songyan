# Task 012: RuleAuditor Agent

> **Phase**: Phase 2 — 审查环节
> **优先级**: P0
> **依赖**: Task 017 (Quality Utils), Task 011 (Writer Agent)
> **预计工作量**: 小

---

## Goal

实现 RuleAuditor Agent —— 纯代码规则检测，复用 Task 017 的 Quality Utils，对 Writer 生成的章节进行 AI 腔、疲劳词、钩子、段落节奏、数值一致性等维度的自动检测。

## Context

RuleAuditor 是审查环节的第一个 Agent，特点是**不调用 LLM**，全部由代码执行，速度快（< 100ms），用于捕捉可自动检测的表层问题。检测结果写入 `RuleAuditResult`，后续与 LLMAuditor 的结果合并为 `MergedReviewReport`。

## In Scope（必须完成）

- [ ] `run_rule_audit()` 主入口 — 纯代码检测，无 LLM
- [ ] 复用 Quality Utils：
  - `detect_ai_tells()` → AI 腔命中
  - `detect_fatigue_words()` → 疲劳词命中（需 GenreRules.fatigue_words）
  - `check_opening_hook()` / `check_ending_hook()` → 钩子检测
  - `analyze_paragraph_rhythm()` → 段落节奏评分
  - `validate_numerical_updates()` → 数值公式验证（玄幻题材）
- [ ] 字数统计与目标对比
- [ ] 组装 `RuleAuditResult`
- [ ] 保存到 `review_reports` 表（通过 `ReviewReportRepository`）
- [ ] 测试：各检测维度 + 边界条件 + 集成测试

## Out of Scope（明确不做）

- 不调用 LLM（LLMAuditor 负责，Task 013）
- 不做文学性诊断（LiteraryAuditor 负责，Task 014）
- 不做合并报告逻辑（RevisionHandler 或编排层负责）

## 接口契约

```python
async def run_rule_audit(
    content: str,
    genre_rules: GenreRules | None = None,
    word_count_target: int = 3000,
    numerical_contexts: list[NumericalContext] | None = None,
) -> RuleAuditResult:
    """运行规则检测（纯代码，无 LLM）.

    Args:
        content: 章节正文
        genre_rules: 题材规则（含 fatigue_words）
        word_count_target: 目标字数
        numerical_contexts: 数值上下文（玄幻题材用）

    Returns:
        RuleAuditResult
    """

async def save_rule_audit(
    db: ReviewReportRepository,
    version_id: str,
    result: RuleAuditResult,
    report_id: str | None = None,
) -> None:
    """保存 RuleAuditResult 到 review_reports 表."""
```

## 数据模型

复用已有模型：
- `RuleAuditResult` — 检测结果
- `AiTellMatch` — AI 腔命中
- `FatigueWordMatch` — 疲劳词命中
- `NumericalContext` — 数值验证上下文

## 测试要求

### Layer 1: 各检测维度
- [ ] AI 腔检测：命中/未命中
- [ ] 疲劳词检测：命中/未命中
- [ ] 钩子检测：有/无
- [ ] 段落节奏：正常/异常
- [ ] 字数统计：达标/不达标

### Layer 2: 结果组装
- [ ] RuleAuditResult 字段完整性
- [ ] duration_ms > 0

### Layer 3: 保存验证
- [ ] Mock DB 保存调用

### Layer 4: 集成测试
- [ ] 端到端检测流程

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_rule_auditor.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范
- [ ] 全量测试通过，ruff 0 errors
- [ ] 生成了 tasks/012-rule-auditor-DONE.md 交接文件
